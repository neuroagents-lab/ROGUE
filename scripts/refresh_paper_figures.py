#!/usr/bin/env python3
"""Refresh the higher-reasoning paper assets from complete local judge caches.

This command makes no API calls. Previous figure assets are backed up once in
the refresh output directory. Unmeasured text-only cells remain explicitly
unmeasured, and restricted-access prompts are never pooled across conditions.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path
import shutil

import paper_figures as pf


def agreement_table(rows):
    def count_rate(row, count, rate):
        return f"{row[count]} ({100 * row[rate]:.1f}\\%)"
    labels = {"intent_override": "Intent to override",
              "intent_subvert_shutdown": "Intent to rewire shutdown",
              "alternate_shutdown_avoidance": "Used alternate rewiring method",
              "intent_access_passwords": "Intent to access restricted resource"}
    lines = []
    for row in rows:
        n = row["compared_tasks"]
        values = [labels[row["outcome"]], str(n),
                  count_rate(row, "gpt_positive_tasks", "gpt_positive_rate"),
                  count_rate(row, "claude_positive_tasks", "claude_positive_rate"),
                  count_rate(row, "agree_tasks", "agreement_rate"),
                  f"{row['gpt_only_tasks']} ({100 * row['gpt_only_tasks'] / n:.1f}\\%)",
                  f"{row['claude_only_tasks']} ({100 * row['claude_only_tasks'] / n:.1f}\\%)",
                  "---" if row["cohens_kappa"] is None else f"{row['cohens_kappa']:.3f}"]
        lines.append("        " + " & ".join(values) + r" \\")
    return r"""\begin{table}[t]
    \centering
    \caption{Agreement between the GPT-5.5 (\texttt{xhigh}) primary judge and
    the Claude Opus 4.7 (\texttt{max}) sensitivity judge on the higher-reasoning
    cohort in Fig.~\ref{fig:rogue_summary}. Restricted access uses prohibition
    only. Both judges assess the same first-repeat episodes; Figure 2's extra
    repeat is excluded. Except for $n$ and Cohen's $\kappa$, entries report
    count (percentage of paired judgments). ``GPT only'' and ``Claude only''
    indicate positive labels from that judge alone.}
    \label{tab:cross_llm_judge_agreement}
    \scriptsize
    \setlength{\tabcolsep}{3.5pt}
    \renewcommand{\arraystretch}{1.15}
    \begin{tabularx}{\linewidth}{@{}>{\raggedright\arraybackslash}Xrrrrrrr@{}}
        \toprule
        \textbf{Judgment target} & \textbf{$n$}
        & \makecell{\textbf{GPT}\\\textbf{positive}}
        & \makecell{\textbf{Claude}\\\textbf{positive}}
        & \makecell{\textbf{Raw}\\\textbf{agreement}}
        & \makecell{\textbf{GPT}\\\textbf{only}}
        & \makecell{\textbf{Claude}\\\textbf{only}}
        & \makecell{\textbf{Cohen's}\\$\kappa$} \\
        \midrule
""" + "\n".join(lines) + r"""
        \bottomrule
    \end{tabularx}
\end{table}
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-root", type=Path, default=pf.DEFAULT_RESULTS_ROOT)
    parser.add_argument("--output-dir", type=Path, default=pf.DEFAULT_OUTPUT_DIR)
    parser.add_argument("--audit-dir", type=Path, default=pf.REPO_ROOT / "outputs/refresh_20261104")
    parser.add_argument("--dpi", type=int, default=300)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    backup = args.audit_dir / "before_figures"
    backup_manifest = args.audit_dir / "figure_backup_manifest.json"
    original_names = set(json.loads(backup_manifest.read_text())) if backup_manifest.exists() else None
    for stem in ("figure_2", "figure_2_v2", "figure_2_merged", "figure_7", "combined_rates_with_subagents",
                 "capability-osworld_vs_misalignment", "judge_sensitivity", "judge_agreement_table"):
        for path in output.glob(stem + ".*"):
            if original_names is not None and path.name not in original_names:
                continue
            saved = backup / path.name
            if not saved.exists():
                saved.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, saved)
    kwargs = {"results_root": args.results_root, "output_dir": output, "dpi": args.dpi}
    outputs = []
    outputs.extend(pf.figure_2(**kwargs))
    outputs.extend(pf._generate_text_agentic_figure(replace(pf.FIGURE_2_SPEC, output_stem="figure_2_v2"),
        results_root=pf.DEFAULT_RERUN_RESULTS_ROOT, textonly_root=pf.DEFAULT_RERUN_TEXTONLY_ROOT,
        output_dir=output, dpi=args.dpi))
    outputs.extend(pf.figure_2_merged(**kwargs))
    outputs.extend(pf.figure_3(**kwargs))
    outputs.extend(pf.capability_osworld_vs_misalignment(**kwargs))
    outputs.extend(pf.figure_7(**kwargs))
    outputs.extend(pf.figure_judge_sensitivity(**kwargs))
    agreement = pf.judge_agreement_table_numbers(args.results_root)
    table_path = output / "judge_agreement_table.tex"
    table_path.write_text(agreement_table(agreement))
    (output / "judge_agreement_table.json").write_text(json.dumps(agreement, indent=2) + "\n")
    summary = pf.build_primary_publication_summary(args.results_root)
    notes = {"generated_at": pf.utc_now_iso(), "outputs": [str(p) for p in outputs] + [str(table_path)],
             "reasoning_settings": pf.PRIMARY_REASONING_SETTINGS,
             "restrictedaccess_condition": "prohibition_only",
             "scenario_counts": [{"scenario": s["scenario"], "configurations": len(s["runs"]),
                 "completed_episodes": sum(r["total_tasks"] for r in s["runs"])} for s in summary["scenarios"]],
             "not_evaluated": summary["not_evaluated"], "judge_agreement": agreement,
             "caption_notes": {"figure_2": "Two matched repeats; task-clustered standard errors; GPT-5.4/5.5 and Opus 4.7 xhigh; Opus 4.6 max; restricted access prohibition only.",
                               "figure_3": "Higher-reasoning configurations; restricted access prohibition only. GPT-5.4 xhigh subagent override and shutdown are not evaluated.",
                               "figure_4": "Parent-only primary configurations with fixed public model capability references; Opus 4.7 xhigh ROGUE is paired with its published max-effort score.",
                               "figure_7": "Single-repeat comparison; six unavailable text-only cells are labeled Not evaluated; their absence is not a zero rate.",
                               "figure_8": "Both judges evaluate the same higher-reasoning primary cohort, 907 episodes; restricted access prohibition only. Figure 2 repeat 2 is excluded."}}
    args.audit_dir.mkdir(parents=True, exist_ok=True)
    (args.audit_dir / "figure_refresh_summary.json").write_text(json.dumps(notes, indent=2) + "\n")
    for path in outputs:
        print(f"Wrote {path}", flush=True)
    print(f"Wrote {table_path}", flush=True)


if __name__ == "__main__":
    main()
