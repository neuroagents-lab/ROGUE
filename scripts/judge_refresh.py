#!/usr/bin/env python3
"""Run only the missing judgments in an audited refresh manifest.

Uses the canonical clients, prompt preprocessing, cache validation, and metric
builders from aggregate_results. Source trajectories are read only. Aggregate
checkpoints are atomic, preserve existing valid records, and refuse concurrent
source/aggregate changes. Re-running the same manifest reuses saved judgments.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import contextlib
import copy
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aggregate_results as ar


class RefreshError(RuntimeError):
    pass


@dataclass
class LeafState:
    leaf: ar.LeafResultDir
    entries: dict[str, dict[str, Any]]
    targets: list[str]
    digest: str | None


@dataclass
class Request:
    state: LeafState
    task_id: str
    target: str
    runtime: str
    reasoning: str


def digest(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=".refresh.", suffix=".tmp", delete=False) as f:
            temporary = Path(f.name)
            json.dump(payload, f, indent=2, ensure_ascii=False)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def prepare(manifest: dict[str, Any], profiles: dict[str, ar.JudgeProfile]):
    states: dict[Path, LeafState] = {}
    requests: list[Request] = []
    seen: set[tuple[str, Path]] = set()
    reused = Counter()
    primary, secondary = profiles[ar.OPENAI_JUDGE_TARGET], profiles[ar.CLAUDE_JUDGE_TARGET]
    for item in manifest["judgment_queue"]:
        task_dir = Path(item["task_dir"]).resolve()
        target = item["judge_target"]
        if target not in profiles:
            raise RefreshError("Unknown judge target in refresh manifest.")
        identity = (target, task_dir)
        if identity in seen:
            raise RefreshError("Duplicate task/judge in refresh manifest.")
        seen.add(identity)
        result_dir = task_dir.parent
        source_scenario = ("subagents_" if item["enable_subagents"] else "") + item["scenario"]
        if result_dir not in states:
            args_path = result_dir.parent / "args.json"
            args = ar.read_json(args_path) or {}
            if args.get("model") != item["model"] or args.get("reasoning_effort") != item["reasoning_effort"]:
                raise RefreshError("Manifest model/reasoning differs from recorded run arguments.")
            if bool(args.get("enable_subagents", False)) != item["enable_subagents"]:
                raise RefreshError("Manifest delegation setting differs from recorded run arguments.")
            leaf = ar.LeafResultDir(
                scenario=source_scenario, scenario_family=item["scenario"],
                scenario_dir_name=item["scenario"], task_prefix=result_dir.name + "_",
                run_group=item["run_group"], variant_name=item["run_group"],
                plot_label=ar.run_variant_display_name(item["run_group"]),
                action_spec=args["action_space"], observation_spec=args["observation_type"],
                model=item["model"], result_dir=result_dir,
            )
            payload = ar.read_json(leaf.aggregate_path) or {}
            if leaf.aggregate_path.exists() and not payload:
                raise RefreshError("Unreadable existing aggregate; refusing overwrite.")
            existing = ar.load_existing_tasks(leaf.aggregate_path)
            entries = {}
            context = ar.load_override_context(result_dir) if leaf.scenario_family == "override" else None
            sentinel = ar.load_password_sentinel() if leaf.scenario_family == "restrictedaccess" else None
            for t in ar.list_task_dirs(result_dir, leaf.task_prefix):
                runtime, reasoning = ar.read_text(t / "runtime.log"), ar.read_text(t / "reasoning_content.jsonl")
                runtime_meta, reasoning_meta = ar.file_meta(t / "runtime.log"), ar.file_meta(t / "reasoning_content.jsonl")
                old = existing.get(t.name) or {}
                if leaf.scenario_family == "override":
                    actual = ar.compute_override_actual(t.name, t, context or {})
                elif leaf.scenario_family == "rewire":
                    actual = ar.compute_rewire_actual(t)
                else:
                    actual = ar.compute_restrictedaccess_actual(runtime, reasoning, password_sentinel=sentinel)
                actual.update(ar.compute_task_success(t))
                records = {}
                for profile in profiles.values():
                    status, cached = ar.cached_judge_status(old, profile, runtime_meta, reasoning_meta, leaf.scenario)
                    if status == "valid":
                        original = (old.get("judge_results") or {}).get(profile.judge_id)
                        records[profile.judge_id] = copy.deepcopy(original or cached)
                entry = copy.deepcopy(old)
                entry.update(ar.build_task_entry(leaf, t, actual, runtime_meta, reasoning_meta,
                                                records, primary, secondary))
                entries[t.name] = entry
            states[result_dir] = LeafState(leaf, entries,
                list(dict.fromkeys(payload.get("judge_targets", []) + [target])), digest(leaf.aggregate_path))
        state = states[result_dir]
        if target not in state.targets:
            state.targets.append(target)
        entry = state.entries.get(task_dir.name)
        if entry is None or not entry["actual"]["result_found"]:
            raise RefreshError("Manifest task has no completed episode.")
        profile = profiles[target]
        if profile.judge_id in entry["judge_results"]:
            reused[target] += 1
            continue
        runtime, reasoning = ar.read_text(task_dir / "runtime.log"), ar.read_text(task_dir / "reasoning_content.jsonl")
        if not runtime.strip() and not reasoning.strip():
            raise RefreshError("A queued completed episode has no judgment source logs.")
        ar.build_prompts_for_task(source_scenario, state.leaf.observation_spec, task_dir.name,
                                 runtime, reasoning, ar.DEFAULT_MAX_CHARS_PER_FILE)
        requests.append(Request(state, task_dir.name, target, runtime, reasoning))
    return list(states.values()), requests, reused


def checkpoint(state: LeafState, profiles: dict[str, ar.JudgeProfile]) -> None:
    if digest(state.leaf.aggregate_path) != state.digest:
        raise RefreshError("Concurrent aggregate modification; refusing overwrite.")
    for entry in state.entries.values():
        for path_key, meta_key in (("runtime_log_path", "runtime_log_meta"),
                                   ("reasoning_content_path", "reasoning_content_meta")):
            if not ar.file_meta_matches_cache(entry[meta_key], ar.file_meta(Path(entry[path_key]))):
                raise RefreshError("Source log changed during judging; refusing checkpoint.")
    complete = all(not e["actual"]["result_found"] or all(
        profiles[t].judge_id in e["judge_results"] for t in state.targets
    ) for e in state.entries.values())
    payload = ar.build_leaf_payload(state.leaf, list(state.entries.values()), complete,
                                   profiles[ar.OPENAI_JUDGE_TARGET], state.targets)
    atomic_json(state.leaf.aggregate_path, payload)
    state.digest = digest(state.leaf.aggregate_path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=10)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    profiles = ar.build_judge_profiles()
    states, requests, reused = prepare(manifest, profiles)
    planned = Counter(r.target for r in requests)
    print(json.dumps({"leaves": len(states), "requests": dict(planned), "valid_cache_reused": dict(reused)}), flush=True)
    if args.dry_run:
        return 0
    primary, secondary = profiles[ar.OPENAI_JUDGE_TARGET], profiles[ar.CLAUDE_JUDGE_TARGET]
    clients = {
        ar.OPENAI_JUDGE_TARGET: ar.JudgeClient(primary.model, primary.reasoning_effort, 600, 3),
        ar.CLAUDE_JUDGE_TARGET: ar.AnthropicJudgeClient(secondary.model, secondary.reasoning_effort,
            secondary.thinking_mode, secondary.max_output_tokens, 600, 3),
    }
    for target in planned:
        clients[target].ensure_ready()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for state in states:
        if state.leaf.aggregate_path.exists():
            # Hash-named snapshots are immutable across retries/resumes.
            backup = args.output_dir / "before" / f"{state.digest}.json"
            if not backup.exists():
                backup.parent.mkdir(parents=True, exist_ok=True)
                backup.write_bytes(state.leaf.aggregate_path.read_bytes())
    report = {"manifest": str(args.manifest.resolve()), "started_at": ar.utc_now_iso(),
              "planned": dict(planned), "reused": dict(reused), "saved": [], "failures": []}
    report_path = args.output_dir / "judgment_execution.json"
    atomic_json(report_path, report)
    with open(os.devnull, "w") as sink, contextlib.redirect_stderr(sink):
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(ar.call_judge_for_task, r.state.leaf.scenario,
                r.state.leaf.observation_spec, r.task_id, r.runtime, r.reasoning,
                clients[r.target], ar.DEFAULT_MAX_CHARS_PER_FILE): r for r in requests}
            for index, future in enumerate(as_completed(futures), 1):
                request = futures[future]
                try:
                    output = future.result()
                except Exception as exc:
                    report["failures"].append({"task_id": request.task_id, "target": request.target,
                                               "error_type": type(exc).__name__})
                    print(f"{index}/{len(requests)} failed {request.target} {request.task_id} ({type(exc).__name__})", flush=True)
                else:
                    entry = request.state.entries[request.task_id]
                    profile = profiles[request.target]
                    entry["judge_results"][profile.judge_id] = ar.make_judge_record(
                        profile, request.state.leaf.scenario, output, "api")
                    ar.apply_primary_judge_aliases(entry, primary, secondary, request.state.leaf.scenario)
                    checkpoint(request.state, profiles)
                    report["saved"].append({"task_id": request.task_id, "target": request.target,
                                           "aggregate": str(request.state.leaf.aggregate_path)})
                    print(f"{index}/{len(requests)} saved {request.target} {request.task_id}", flush=True)
                atomic_json(report_path, report)
    for state in states:
        checkpoint(state, profiles)
    report["finished_at"] = ar.utc_now_iso()
    report["status"] = "complete" if not report["failures"] else "incomplete"
    atomic_json(report_path, report)
    print(json.dumps({"status": report["status"], "saved": len(report["saved"]),
                      "failed": len(report["failures"])}), flush=True)
    return int(bool(report["failures"]))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Judgment refresh stopped ({type(exc).__name__}); diagnostic payload omitted.", file=sys.stderr)
        raise SystemExit(1)
