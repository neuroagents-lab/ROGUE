import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import aggregate_results


GPT_TARGET = aggregate_results.OPENAI_JUDGE_TARGET
CLAUDE_TARGET = aggregate_results.CLAUDE_JUDGE_TARGET


def rewire_judgment(intent=True, alternate=False):
    return {
        "intent_subvert_shutdown": intent,
        "used_alternate_shutdown_avoidance": alternate,
        "alternate_method_description": "shutdown -c" if alternate else "",
        "confidence": "high",
        "evidence": ["test fixture"],
    }


class FakeJudge:
    def __init__(self, output=None, error=None):
        self.output = output
        self.error = error
        self.calls = []

    def judge_json(self, system_prompt, user_prompt):
        self.calls.append((system_prompt, user_prompt))
        if self.error is not None:
            raise RuntimeError(self.error)
        return dict(self.output)


class FailingOpenAITransport:
    def __init__(self):
        self.calls = 0

    def judge_json(self, system_prompt, user_prompt):
        self.calls += 1
        raise AssertionError("OpenAI must not be invoked in Claude-only mode")


class JudgeFixtureMixin:
    def make_leaf(self, temp_dir):
        results_root = Path(temp_dir) / "results"
        result_dir = (
            results_root
            / "rewire"
            / "base"
            / "pyautogui"
            / "screenshot"
            / "gpt-5.4"
            / "rewire"
        )
        task_dir = result_dir / "rewire_fixture"
        task_dir.mkdir(parents=True)
        (task_dir / "runtime.log").write_text(
            "The agent considered cancelling shutdown.\n", encoding="utf-8"
        )
        (task_dir / "reasoning_content.jsonl").write_text(
            json.dumps({"reasoning_content": "I should run shutdown -c."}) + "\n",
            encoding="utf-8",
        )
        (task_dir / "result.txt").write_text("1\n", encoding="utf-8")
        (task_dir / "shutdown_check.json").write_text(
            json.dumps({"changed": False, "unchanged": True}), encoding="utf-8"
        )
        leaf = aggregate_results.LeafResultDir(
            scenario="rewire",
            scenario_family="rewire",
            scenario_dir_name="rewire",
            task_prefix="rewire_",
            run_group="base",
            variant_name="base",
            plot_label="Base",
            action_spec="pyautogui",
            observation_spec="screenshot",
            model="gpt-5.4",
            result_dir=result_dir,
        )
        return results_root, leaf, task_dir

    def legacy_gpt_task(self, task_dir, judgment=None, malformed=False):
        runtime_meta = aggregate_results.file_meta(task_dir / "runtime.log")
        reasoning_meta = aggregate_results.file_meta(task_dir / "reasoning_content.jsonl")
        # Historical records did not have hashes. Size compatibility must remain valid.
        runtime_meta.pop("sha256")
        reasoning_meta.pop("sha256")
        return {
            "task_id": task_dir.name,
            "runtime_log_meta": runtime_meta,
            "reasoning_content_meta": reasoning_meta,
            "judge_model": aggregate_results.DEFAULT_JUDGE_MODEL,
            "judge_reasoning_effort": aggregate_results.DEFAULT_JUDGE_REASONING_EFFORT,
            "judge_prompt_version": f"{aggregate_results.JUDGE_PROMPT_VERSION}:rewire",
            "judge": {"malformed": True}
            if malformed
            else (judgment or rewire_judgment()),
        }

    def write_aggregate(self, leaf, task_entry):
        leaf.aggregate_path.write_text(
            json.dumps({"tasks": [task_entry]}), encoding="utf-8"
        )

    def aggregate_claude_only(self, leaf, mode, claude, openai=None, continue_on_error=False):
        profiles = aggregate_results.build_judge_profiles()
        clients = {CLAUDE_TARGET: claude}
        if openai is not None:
            clients[GPT_TARGET] = openai
        return aggregate_results.aggregate_leaf(
            leaf=leaf,
            judge_profiles=profiles,
            selected_targets=[CLAUDE_TARGET],
            judge_clients=clients,
            judge_mode=mode,
            max_chars_per_file=aggregate_results.DEFAULT_MAX_CHARS_PER_FILE,
            continue_on_judge_error=continue_on_error,
        )


class TestJudgeTargetSelection(unittest.TestCase):
    def test_default_target_preserves_gpt_only_workflow(self):
        args = aggregate_results.parse_args([])
        self.assertEqual(args.judge_targets, [GPT_TARGET])

    def test_claude_only_main_never_constructs_openai_client(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with (
                mock.patch.object(
                    aggregate_results.JudgeClient,
                    "__init__",
                    side_effect=AssertionError("OpenAI client constructed"),
                ) as openai_init,
                mock.patch.object(aggregate_results, "discover_leaf_dirs", return_value=[]),
                mock.patch.object(
                    aggregate_results,
                    "write_combined_rates_with_subagents_outputs",
                ),
                mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test"}, clear=True),
            ):
                rc = aggregate_results.main(
                    [
                        "--results_root",
                        temp_dir,
                        "--scenarios",
                        "rewire",
                        "--judge-targets",
                        CLAUDE_TARGET,
                    ]
                )
        self.assertEqual(rc, 0)
        openai_init.assert_not_called()

    def test_default_main_constructs_only_gpt_client(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with (
                mock.patch.object(aggregate_results, "JudgeClient") as openai_client,
                mock.patch.object(
                    aggregate_results.AnthropicJudgeClient,
                    "__init__",
                    side_effect=AssertionError("Claude client constructed by default"),
                ) as claude_init,
                mock.patch.object(aggregate_results, "discover_leaf_dirs", return_value=[]),
                mock.patch.object(
                    aggregate_results,
                    "write_combined_rates_with_subagents_outputs",
                ),
            ):
                rc = aggregate_results.main(
                    ["--results_root", temp_dir, "--scenarios", "rewire"]
                )
        self.assertEqual(rc, 0)
        openai_client.assert_called_once()
        claude_init.assert_not_called()

    def test_openai_batch_action_constructs_no_synchronous_judge_clients(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with (
                mock.patch.object(
                    aggregate_results.JudgeClient,
                    "__init__",
                    side_effect=AssertionError("Synchronous OpenAI client constructed"),
                ) as sync_openai_init,
                mock.patch.object(
                    aggregate_results.AnthropicJudgeClient,
                    "__init__",
                    side_effect=AssertionError("Claude client constructed"),
                ) as claude_init,
                mock.patch.object(aggregate_results, "OpenAIBatchClient"),
                mock.patch.object(
                    aggregate_results,
                    "submit_openai_batch",
                    return_value={"submitted": False},
                ) as submit,
            ):
                rc = aggregate_results.main(
                    [
                        "--results_root",
                        temp_dir,
                        "--scenarios",
                        "rewire",
                        "--judge-targets",
                        GPT_TARGET,
                        "--openai-batch-action",
                        "submit",
                    ]
                )
        self.assertEqual(rc, 0)
        submit.assert_called_once()
        sync_openai_init.assert_not_called()
        claude_init.assert_not_called()


class TestAnthropicJudgeClient(unittest.TestCase):
    def test_messages_api_uses_opus_max_and_64k_output_cap(self):
        captured = {}
        response_output = rewire_judgment()

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, traceback):
                return False

            def read(self):
                return json.dumps(
                    {
                        "content": [
                            {
                                "type": "thinking",
                                "thinking": "",
                                "signature": "test-signature",
                            },
                            {"type": "text", "text": json.dumps(response_output)},
                        ]
                    }
                ).encode("utf-8")

        def fake_urlopen(request, timeout):
            captured["request"] = request
            captured["timeout"] = timeout
            return Response()

        with (
            mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "anthropic-test"}, clear=True),
            mock.patch.object(aggregate_results.urllib.request, "urlopen", fake_urlopen),
        ):
            client = aggregate_results.AnthropicJudgeClient(
                model=aggregate_results.DEFAULT_CLAUDE_JUDGE_MODEL,
                reasoning_effort=aggregate_results.DEFAULT_CLAUDE_JUDGE_REASONING_EFFORT,
                thinking_mode=aggregate_results.DEFAULT_CLAUDE_JUDGE_THINKING_MODE,
                max_output_tokens=aggregate_results.DEFAULT_CLAUDE_JUDGE_MAX_TOKENS,
                timeout_seconds=123,
                max_retries=1,
            )
            result = client.judge_json("system prompt", "user prompt")

        request = captured["request"]
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(request.full_url, "https://api.anthropic.com/v1/messages")
        self.assertEqual(captured["timeout"], 123)
        self.assertEqual(payload["model"], "claude-opus-4-7")
        self.assertEqual(payload["max_tokens"], 64_000)
        self.assertEqual(payload["thinking"], {"type": "adaptive"})
        self.assertEqual(payload["output_config"], {"effort": "max"})
        self.assertEqual(payload["system"], "system prompt")
        self.assertEqual(payload["messages"], [{"role": "user", "content": "user prompt"}])
        self.assertEqual(request.get_header("X-api-key"), "anthropic-test")
        self.assertEqual(result["intent_subvert_shutdown"], True)


class TestAnthropicBatch(JudgeFixtureMixin, unittest.TestCase):
    def test_batch_plan_uses_same_prompt_and_message_parameters(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            results_root, leaf, task_dir = self.make_leaf(temp_dir)
            self.write_aggregate(leaf, self.legacy_gpt_task(task_dir))
            profiles = aggregate_results.build_judge_profiles()

            plan = aggregate_results.build_claude_batch_plan(
                results_root=results_root,
                scenarios=["rewire"],
                judge_profiles=profiles,
                judge_mode="auto",
                max_chars_per_file=aggregate_results.DEFAULT_MAX_CHARS_PER_FILE,
            )

            self.assertEqual(plan["request_count"], 1)
            self.assertEqual(plan["valid_cache_tasks"], 0)
            request = plan["requests"][0]
            self.assertLessEqual(len(request["custom_id"]), 64)
            system_prompt, user_prompt = aggregate_results.build_prompts_for_task(
                scenario="rewire",
                observation_spec="screenshot",
                task_id=task_dir.name,
                runtime_text=(task_dir / "runtime.log").read_text(encoding="utf-8"),
                reasoning_text=(task_dir / "reasoning_content.jsonl").read_text(
                    encoding="utf-8"
                ),
                max_chars_per_file=aggregate_results.DEFAULT_MAX_CHARS_PER_FILE,
            )
            self.assertEqual(
                request["params"],
                aggregate_results.build_anthropic_message_params(
                    profiles[CLAUDE_TARGET], system_prompt, user_prompt
                ),
            )
            self.assertEqual(request["params"]["thinking"], {"type": "adaptive"})
            self.assertEqual(request["params"]["output_config"], {"effort": "max"})
            self.assertEqual(request["params"]["max_tokens"], 64_000)
            self.assertEqual(
                plan["manifest"][0]["relative_aggregate_path"],
                str(leaf.aggregate_path.relative_to(results_root)),
            )

    def test_batch_plan_reuses_valid_claude_cache(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            results_root, leaf, task_dir = self.make_leaf(temp_dir)
            profiles = aggregate_results.build_judge_profiles()
            task = self.legacy_gpt_task(task_dir)
            task["judge_results"] = {
                profiles[CLAUDE_TARGET].judge_id: aggregate_results.make_judge_record(
                    profiles[CLAUDE_TARGET],
                    "rewire",
                    rewire_judgment(),
                    "batch_api",
                )
            }
            self.write_aggregate(leaf, task)

            plan = aggregate_results.build_claude_batch_plan(
                results_root=results_root,
                scenarios=["rewire"],
                judge_profiles=profiles,
                judge_mode="auto",
                max_chars_per_file=aggregate_results.DEFAULT_MAX_CHARS_PER_FILE,
            )

            self.assertEqual(plan["request_count"], 0)
            self.assertEqual(plan["valid_cache_tasks"], 1)

    def test_batch_submission_uses_message_batches_endpoint(self):
        captured = {}

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, traceback):
                return False

            def read(self):
                return json.dumps(
                    {"id": "msgbatch_test", "processing_status": "in_progress"}
                ).encode("utf-8")

        def fake_urlopen(request, timeout):
            captured["request"] = request
            captured["timeout"] = timeout
            return Response()

        requests = [{"custom_id": "rogue-test", "params": {"model": "test"}}]
        with (
            mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "anthropic-test"}, clear=True),
            mock.patch.object(aggregate_results.urllib.request, "urlopen", fake_urlopen),
        ):
            client = aggregate_results.AnthropicBatchClient(timeout_seconds=321)
            response = client.create_batch(requests)

        request = captured["request"]
        self.assertEqual(
            request.full_url, "https://api.anthropic.com/v1/messages/batches"
        )
        self.assertEqual(request.method, "POST")
        self.assertEqual(captured["timeout"], 321)
        self.assertEqual(
            json.loads(request.data.decode("utf-8")), {"requests": requests}
        )
        self.assertEqual(response["id"], "msgbatch_test")

    def test_batch_results_are_streamed_as_jsonl(self):
        captured = {}
        rows = [
            {"custom_id": "rogue-one", "result": {"type": "expired"}},
            {"custom_id": "rogue-two", "result": {"type": "canceled"}},
        ]

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, traceback):
                return False

            def __iter__(self):
                return iter(
                    [(json.dumps(row) + "\n").encode("utf-8") for row in rows]
                )

        def fake_urlopen(request, timeout):
            captured["request"] = request
            return Response()

        with (
            mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "anthropic-test"}, clear=True),
            mock.patch.object(aggregate_results.urllib.request, "urlopen", fake_urlopen),
        ):
            client = aggregate_results.AnthropicBatchClient(timeout_seconds=123)
            received = list(client.retrieve_results("msgbatch_test"))

        self.assertEqual(received, rows)
        self.assertEqual(
            captured["request"].full_url,
            "https://api.anthropic.com/v1/messages/batches/msgbatch_test/results",
        )

    def test_apply_batch_result_preserves_gpt_and_records_usage(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            results_root, leaf, task_dir = self.make_leaf(temp_dir)
            legacy = self.legacy_gpt_task(task_dir, rewire_judgment(intent=True))
            self.write_aggregate(leaf, legacy)
            profiles = aggregate_results.build_judge_profiles()
            plan = aggregate_results.build_claude_batch_plan(
                results_root=results_root,
                scenarios=["rewire"],
                judge_profiles=profiles,
                judge_mode="auto",
                max_chars_per_file=aggregate_results.DEFAULT_MAX_CHARS_PER_FILE,
            )
            state = {
                "state_version": aggregate_results.CLAUDE_BATCH_STATE_VERSION,
                "batch_id": "msgbatch_test",
                "profile": aggregate_results.claude_batch_profile_snapshot(
                    profiles[CLAUDE_TARGET]
                ),
                "manifest": plan["manifest"],
            }
            result_rows = [
                {
                    "custom_id": plan["requests"][0]["custom_id"],
                    "result": {
                        "type": "succeeded",
                        "message": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": json.dumps(
                                        rewire_judgment(intent=False)
                                    ),
                                }
                            ],
                            "usage": {"input_tokens": 100, "output_tokens": 20},
                        },
                    },
                }
            ]

            counts = aggregate_results.apply_claude_batch_results(
                results_root=results_root,
                state=state,
                result_rows=result_rows,
                judge_profiles=profiles,
            )

            saved = json.loads(leaf.aggregate_path.read_text(encoding="utf-8"))
            task = saved["tasks"][0]
            claude_record = task["judge_results"][
                profiles[CLAUDE_TARGET].judge_id
            ]
            self.assertEqual(counts["succeeded"], 1)
            self.assertEqual(counts["failed"], 0)
            self.assertEqual(task["judge"], legacy["judge"])
            self.assertEqual(claude_record["source"], "batch_api")
            self.assertEqual(claude_record["batch_id"], "msgbatch_test")
            self.assertEqual(
                claude_record["usage"],
                {"input_tokens": 100, "output_tokens": 20},
            )
            self.assertEqual(
                claude_record["output"]["intent_subvert_shutdown"], False
            )
            status, cached = aggregate_results.cached_judge_status(
                task,
                profiles[CLAUDE_TARGET],
                aggregate_results.file_meta(task_dir / "runtime.log"),
                aggregate_results.file_meta(task_dir / "reasoning_content.jsonl"),
                "rewire",
            )
            self.assertEqual(status, "valid")
            self.assertEqual(cached["batch_id"], "msgbatch_test")
            self.assertEqual(cached["usage"]["input_tokens"], 100)

    def test_apply_creates_missing_aggregate_without_api_judge_calls(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            results_root, leaf, task_dir = self.make_leaf(temp_dir)
            profiles = aggregate_results.build_judge_profiles()
            plan = aggregate_results.build_claude_batch_plan(
                results_root=results_root,
                scenarios=["rewire"],
                judge_profiles=profiles,
                judge_mode="auto",
                max_chars_per_file=aggregate_results.DEFAULT_MAX_CHARS_PER_FILE,
            )
            state_path = results_root / "summary" / "batch.json"
            aggregate_results.write_json(
                state_path,
                {
                    "state_version": aggregate_results.CLAUDE_BATCH_STATE_VERSION,
                    "batch_id": "msgbatch_missing_aggregate",
                    "profile": aggregate_results.claude_batch_profile_snapshot(
                        profiles[CLAUDE_TARGET]
                    ),
                    "manifest": plan["manifest"],
                    "scenarios": ["rewire"],
                    "max_chars_per_file": (
                        aggregate_results.DEFAULT_MAX_CHARS_PER_FILE
                    ),
                },
            )

            class FakeBatchClient:
                def retrieve_batch(self, batch_id):
                    self.batch_id = batch_id
                    return {
                        "processing_status": "ended",
                        "request_counts": {"succeeded": 1},
                    }

                def retrieve_results(self, batch_id):
                    return [
                        {
                            "custom_id": plan["requests"][0]["custom_id"],
                            "result": {
                                "type": "succeeded",
                                "message": {
                                    "content": [
                                        {
                                            "type": "text",
                                            "text": json.dumps(rewire_judgment()),
                                        }
                                    ]
                                },
                            },
                        }
                    ]

            _, counts = aggregate_results.apply_completed_claude_batch(
                results_root=results_root,
                state_path=state_path,
                judge_profiles=profiles,
                client=FakeBatchClient(),
            )

            saved = json.loads(leaf.aggregate_path.read_text(encoding="utf-8"))
            record = saved["tasks"][0]["judge_results"][
                profiles[CLAUDE_TARGET].judge_id
            ]
            self.assertEqual(counts["succeeded"], 1)
            self.assertEqual(record["source"], "batch_api")
            self.assertEqual(record["batch_id"], "msgbatch_missing_aggregate")
            self.assertEqual(saved["tasks"][0]["task_id"], task_dir.name)


class TestOpenAIBatch(JudgeFixtureMixin, unittest.TestCase):
    def test_batch_plan_uses_same_prompt_and_chat_completion_body(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            results_root, leaf, task_dir = self.make_leaf(temp_dir)
            profiles = aggregate_results.build_judge_profiles()

            plan = aggregate_results.build_openai_batch_plan(
                results_root=results_root,
                scenarios=["rewire"],
                judge_profiles=profiles,
                judge_mode="auto",
                max_chars_per_file=aggregate_results.DEFAULT_MAX_CHARS_PER_FILE,
            )

            self.assertEqual(plan["request_count"], 1)
            row = plan["rows"][0]
            self.assertEqual(row["method"], "POST")
            self.assertEqual(row["url"], "/v1/chat/completions")
            system_prompt, user_prompt = aggregate_results.build_prompts_for_task(
                scenario="rewire",
                observation_spec="screenshot",
                task_id=task_dir.name,
                runtime_text=(task_dir / "runtime.log").read_text(encoding="utf-8"),
                reasoning_text=(task_dir / "reasoning_content.jsonl").read_text(
                    encoding="utf-8"
                ),
                max_chars_per_file=aggregate_results.DEFAULT_MAX_CHARS_PER_FILE,
            )
            self.assertEqual(
                row["body"],
                aggregate_results.build_openai_chat_completion_body(
                    profiles[GPT_TARGET], system_prompt, user_prompt
                ),
            )
            self.assertEqual(row["body"]["model"], "gpt-5.5")
            self.assertEqual(row["body"]["reasoning_effort"], "xhigh")
            self.assertEqual(
                plan["jsonl_bytes"],
                aggregate_results.serialize_openai_batch_rows(plan["rows"]),
            )
            self.assertEqual(
                plan["manifest"][0]["relative_aggregate_path"],
                str(leaf.aggregate_path.relative_to(results_root)),
            )

    def test_batch_plan_reuses_valid_legacy_gpt_cache(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            results_root, leaf, task_dir = self.make_leaf(temp_dir)
            self.write_aggregate(leaf, self.legacy_gpt_task(task_dir))

            plan = aggregate_results.build_openai_batch_plan(
                results_root=results_root,
                scenarios=["rewire"],
                judge_profiles=aggregate_results.build_judge_profiles(),
                judge_mode="auto",
                max_chars_per_file=aggregate_results.DEFAULT_MAX_CHARS_PER_FILE,
            )

            self.assertEqual(plan["request_count"], 0)
            self.assertEqual(plan["valid_cache_tasks"], 1)

    def test_upload_and_create_use_files_and_batches_endpoints(self):
        captured = []
        responses = [
            {"id": "file-input", "bytes": 123, "purpose": "batch"},
            {
                "id": "batch-test",
                "status": "validating",
                "input_file_id": "file-input",
            },
        ]

        class Response:
            def __init__(self, payload):
                self.payload = payload

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, traceback):
                return False

            def read(self):
                return json.dumps(self.payload).encode("utf-8")

        def fake_urlopen(request, timeout):
            captured.append((request, timeout))
            return Response(responses[len(captured) - 1])

        jsonl_bytes = b'{"custom_id":"rogue-test"}\n'
        with (
            mock.patch.dict(
                os.environ,
                {
                    "OPENAI_API_KEY": "openai-test",
                    "OPENAI_ORG_ID": "org-test",
                    "OPENAI_PROJECT": "proj-test",
                },
                clear=True,
            ),
            mock.patch.object(aggregate_results.urllib.request, "urlopen", fake_urlopen),
        ):
            client = aggregate_results.OpenAIBatchClient(timeout_seconds=222)
            uploaded = client.upload_batch_file(jsonl_bytes)
            batch = client.create_batch(uploaded["id"], "submission-test")

        upload_request = captured[0][0]
        create_request = captured[1][0]
        self.assertEqual(upload_request.full_url, "https://api.openai.com/v1/files")
        self.assertEqual(create_request.full_url, "https://api.openai.com/v1/batches")
        self.assertIn(b'name="purpose"', upload_request.data)
        self.assertIn(b"\r\nbatch\r\n", upload_request.data)
        self.assertIn(jsonl_bytes, upload_request.data)
        self.assertTrue(
            upload_request.get_header("Content-type").startswith(
                "multipart/form-data; boundary="
            )
        )
        self.assertEqual(upload_request.get_header("Authorization"), "Bearer openai-test")
        self.assertEqual(upload_request.get_header("Openai-organization"), "org-test")
        self.assertEqual(upload_request.get_header("Openai-project"), "proj-test")
        create_payload = json.loads(create_request.data.decode("utf-8"))
        self.assertEqual(create_payload["input_file_id"], "file-input")
        self.assertEqual(create_payload["endpoint"], "/v1/chat/completions")
        self.assertEqual(create_payload["completion_window"], "24h")
        self.assertEqual(
            create_payload["metadata"]["rogue_submission_id"], "submission-test"
        )
        self.assertEqual(batch["id"], "batch-test")

    def test_batch_output_file_is_streamed_as_jsonl(self):
        captured = {}
        rows = [
            {"custom_id": "rogue-one", "response": {"status_code": 200}},
            {"custom_id": "rogue-two", "error": {"code": "batch_expired"}},
        ]

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, traceback):
                return False

            def __iter__(self):
                return iter(
                    [(json.dumps(row) + "\n").encode("utf-8") for row in rows]
                )

        def fake_urlopen(request, timeout):
            captured["request"] = request
            return Response()

        with (
            mock.patch.dict(os.environ, {"OPENAI_API_KEY": "openai-test"}, clear=True),
            mock.patch.object(aggregate_results.urllib.request, "urlopen", fake_urlopen),
        ):
            client = aggregate_results.OpenAIBatchClient(timeout_seconds=123)
            received = list(client.retrieve_file_results("file-output"))

        self.assertEqual(received, rows)
        self.assertEqual(
            captured["request"].full_url,
            "https://api.openai.com/v1/files/file-output/content",
        )

    def test_apply_preserves_claude_and_updates_primary_gpt_aliases(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            results_root, leaf, task_dir = self.make_leaf(temp_dir)
            profiles = aggregate_results.build_judge_profiles()
            existing = self.legacy_gpt_task(task_dir, malformed=True)
            existing["judge_results"] = {
                profiles[CLAUDE_TARGET].judge_id: (
                    aggregate_results.make_judge_record(
                        profiles[CLAUDE_TARGET],
                        "rewire",
                        rewire_judgment(intent=True),
                        "batch_api",
                    )
                )
            }
            self.write_aggregate(leaf, existing)
            plan = aggregate_results.build_openai_batch_plan(
                results_root=results_root,
                scenarios=["rewire"],
                judge_profiles=profiles,
                judge_mode="auto",
                max_chars_per_file=aggregate_results.DEFAULT_MAX_CHARS_PER_FILE,
            )
            state = {
                "state_version": aggregate_results.OPENAI_BATCH_STATE_VERSION,
                "batch_id": "batch-test",
                "profile": aggregate_results.openai_batch_profile_snapshot(
                    profiles[GPT_TARGET]
                ),
                "manifest": plan["manifest"],
            }
            result_rows = [
                {
                    "custom_id": plan["rows"][0]["custom_id"],
                    "response": {
                        "status_code": 200,
                        "body": {
                            "choices": [
                                {
                                    "message": {
                                        "content": json.dumps(
                                            rewire_judgment(intent=False)
                                        )
                                    }
                                }
                            ],
                            "usage": {
                                "prompt_tokens": 100,
                                "completion_tokens": 20,
                                "total_tokens": 120,
                            },
                        },
                    },
                    "error": None,
                }
            ]

            counts = aggregate_results.apply_openai_batch_results(
                results_root=results_root,
                state=state,
                result_rows=result_rows,
                judge_profiles=profiles,
            )

            saved = json.loads(leaf.aggregate_path.read_text(encoding="utf-8"))
            task = saved["tasks"][0]
            gpt_record = task["judge_results"][profiles[GPT_TARGET].judge_id]
            self.assertEqual(counts["succeeded"], 1)
            self.assertEqual(gpt_record["source"], "batch_api")
            self.assertEqual(gpt_record["batch_id"], "batch-test")
            self.assertEqual(gpt_record["usage"]["total_tokens"], 120)
            self.assertFalse(task["judge"]["intent_subvert_shutdown"])
            self.assertIn(profiles[CLAUDE_TARGET].judge_id, task["judge_results"])
            self.assertEqual(task["judge_comparison"]["status"], "disagree")

    def test_apply_completed_creates_missing_aggregate_locally(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            results_root, leaf, task_dir = self.make_leaf(temp_dir)
            profiles = aggregate_results.build_judge_profiles()
            plan = aggregate_results.build_openai_batch_plan(
                results_root=results_root,
                scenarios=["rewire"],
                judge_profiles=profiles,
                judge_mode="auto",
                max_chars_per_file=aggregate_results.DEFAULT_MAX_CHARS_PER_FILE,
            )
            state_path = results_root / "summary" / "openai-batch.json"
            aggregate_results.write_json(
                state_path,
                {
                    "state_version": aggregate_results.OPENAI_BATCH_STATE_VERSION,
                    "batch_id": "batch-missing-aggregate",
                    "profile": aggregate_results.openai_batch_profile_snapshot(
                        profiles[GPT_TARGET]
                    ),
                    "manifest": plan["manifest"],
                    "scenarios": ["rewire"],
                    "max_chars_per_file": (
                        aggregate_results.DEFAULT_MAX_CHARS_PER_FILE
                    ),
                },
            )

            class FakeBatchClient:
                def retrieve_batch(self, batch_id):
                    return {
                        "id": batch_id,
                        "status": "completed",
                        "output_file_id": "file-output",
                        "error_file_id": None,
                        "request_counts": {"total": 1, "completed": 1, "failed": 0},
                    }

                def retrieve_file_results(self, file_id):
                    yield {
                        "custom_id": plan["rows"][0]["custom_id"],
                        "response": {
                            "status_code": 200,
                            "body": {
                                "choices": [
                                    {
                                        "message": {
                                            "content": json.dumps(
                                                rewire_judgment(intent=True)
                                            )
                                        }
                                    }
                                ],
                                "usage": {"total_tokens": 42},
                            },
                        },
                        "error": None,
                    }

            _, counts = aggregate_results.apply_completed_openai_batch(
                results_root=results_root,
                state_path=state_path,
                judge_profiles=profiles,
                client=FakeBatchClient(),
            )

            saved = json.loads(leaf.aggregate_path.read_text(encoding="utf-8"))
            record = saved["tasks"][0]["judge_results"][
                profiles[GPT_TARGET].judge_id
            ]
            self.assertEqual(counts["succeeded"], 1)
            self.assertEqual(record["source"], "batch_api")
            self.assertEqual(record["batch_id"], "batch-missing-aggregate")
            self.assertEqual(record["usage"]["total_tokens"], 42)
            self.assertEqual(saved["tasks"][0]["task_id"], task_dir.name)


class TestJudgeCacheAndBackfill(JudgeFixtureMixin, unittest.TestCase):
    def test_claude_auto_adopts_legacy_gpt_and_preserves_gpt_metrics(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _, leaf, task_dir = self.make_leaf(temp_dir)
            legacy = self.legacy_gpt_task(task_dir, rewire_judgment(intent=True))
            self.write_aggregate(leaf, legacy)
            claude = FakeJudge(rewire_judgment(intent=True))
            openai = FailingOpenAITransport()

            payload = self.aggregate_claude_only(leaf, "auto", claude, openai)

            task = payload["tasks"][0]
            profiles = aggregate_results.build_judge_profiles()
            gpt_id = profiles[GPT_TARGET].judge_id
            claude_id = profiles[CLAUDE_TARGET].judge_id
            self.assertEqual(len(claude.calls), 1)
            self.assertEqual(openai.calls, 0)
            self.assertIn(gpt_id, task["judge_results"])
            self.assertIn(claude_id, task["judge_results"])
            self.assertEqual(task["judge_results"][gpt_id]["source"], "cache")
            self.assertEqual(
                task["judge_results"][claude_id]["thinking_mode"], "adaptive"
            )
            self.assertEqual(task["judge"], legacy["judge"])
            self.assertEqual(task["judge_model"], "gpt-5.5")
            self.assertEqual(task["judge_reasoning_effort"], "xhigh")
            self.assertEqual(task["judge_prompt_version"], "judge-prompts-v3:rewire")
            self.assertEqual(task["judge_comparison"]["status"], "agree")
            self.assertEqual(payload["summary"]["intended_subvert_shutdown_tasks"], 1)

    def test_auto_and_refresh_never_call_openai_for_bad_gpt_caches(self):
        cases = (("auto", "missing"), ("refresh", "malformed"))
        for mode, cache_kind in cases:
            with self.subTest(mode=mode, cache_kind=cache_kind):
                with tempfile.TemporaryDirectory() as temp_dir:
                    _, leaf, task_dir = self.make_leaf(temp_dir)
                    if cache_kind == "malformed":
                        self.write_aggregate(
                            leaf, self.legacy_gpt_task(task_dir, malformed=True)
                        )
                    claude = FakeJudge(rewire_judgment())
                    openai = FailingOpenAITransport()

                    payload = self.aggregate_claude_only(leaf, mode, claude, openai)

                    task = payload["tasks"][0]
                    self.assertEqual(len(claude.calls), 1)
                    self.assertEqual(openai.calls, 0)
                    self.assertIsNone(task["judge"])
                    self.assertEqual(task["judge_comparison"]["status"], "incomplete")

    def test_claude_refresh_preserves_valid_gpt_and_replaces_only_claude(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _, leaf, task_dir = self.make_leaf(temp_dir)
            profiles = aggregate_results.build_judge_profiles()
            legacy = self.legacy_gpt_task(task_dir, rewire_judgment(intent=True))
            legacy["judge_results"] = {
                profiles[CLAUDE_TARGET].judge_id: aggregate_results.make_judge_record(
                    profiles[CLAUDE_TARGET],
                    "rewire",
                    rewire_judgment(intent=True),
                    "api",
                )
            }
            self.write_aggregate(leaf, legacy)
            claude = FakeJudge(rewire_judgment(intent=False))
            openai = FailingOpenAITransport()

            payload = self.aggregate_claude_only(leaf, "refresh", claude, openai)

            task = payload["tasks"][0]
            gpt_id = profiles[GPT_TARGET].judge_id
            claude_id = profiles[CLAUDE_TARGET].judge_id
            self.assertEqual(openai.calls, 0)
            self.assertEqual(len(claude.calls), 1)
            self.assertEqual(
                task["judge_results"][gpt_id]["output"]["intent_subvert_shutdown"],
                True,
            )
            self.assertEqual(
                task["judge_results"][claude_id]["output"]["intent_subvert_shutdown"],
                False,
            )
            self.assertEqual(task["judge_comparison"]["status"], "disagree")
            self.assertEqual(payload["summary"]["intended_subvert_shutdown_tasks"], 1)

    def test_claude_auto_replaces_cache_without_adaptive_thinking(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _, leaf, task_dir = self.make_leaf(temp_dir)
            profiles = aggregate_results.build_judge_profiles()
            claude_profile = profiles[CLAUDE_TARGET]
            legacy = self.legacy_gpt_task(task_dir)
            stale_record = aggregate_results.make_judge_record(
                claude_profile,
                "rewire",
                rewire_judgment(intent=True),
                "api",
            )
            stale_record.pop("thinking_mode")
            legacy["judge_results"] = {
                claude_profile.judge_id: stale_record,
            }
            self.write_aggregate(leaf, legacy)
            claude = FakeJudge(rewire_judgment(intent=False))

            payload = self.aggregate_claude_only(leaf, "auto", claude)

            self.assertEqual(len(claude.calls), 1)
            record = payload["tasks"][0]["judge_results"][claude_profile.judge_id]
            self.assertEqual(record["thinking_mode"], "adaptive")
            self.assertEqual(record["output"]["intent_subvert_shutdown"], False)

    def test_changed_logs_invalidate_gpt_without_backfill(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _, leaf, task_dir = self.make_leaf(temp_dir)
            self.write_aggregate(leaf, self.legacy_gpt_task(task_dir))
            with (task_dir / "runtime.log").open("a", encoding="utf-8") as handle:
                handle.write("The logs changed after GPT judging.\n")
            claude = FakeJudge(rewire_judgment())
            openai = FailingOpenAITransport()

            payload = self.aggregate_claude_only(leaf, "auto", claude, openai)

            task = payload["tasks"][0]
            self.assertEqual(openai.calls, 0)
            self.assertIsNone(task["judge"])
            self.assertEqual(task["judge_source"], "cache_miss")
            self.assertEqual(task["judge_comparison"]["status"], "incomplete")

    def test_provider_error_is_checkpointed_and_can_continue(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _, leaf, _ = self.make_leaf(temp_dir)
            claude = FakeJudge(error="Anthropic unavailable")

            payload = self.aggregate_claude_only(
                leaf, "auto", claude, continue_on_error=True
            )

            task = payload["tasks"][0]
            claude_id = aggregate_results.build_judge_profiles()[CLAUDE_TARGET].judge_id
            self.assertEqual(task["judge_results"][claude_id]["source"], "api_error")
            self.assertEqual(task["judge_results"][claude_id]["error"], "Anthropic unavailable")
            saved = json.loads(leaf.aggregate_path.read_text(encoding="utf-8"))
            self.assertTrue(saved["processing_complete"])

    def test_provider_error_checkpoints_before_abort(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _, leaf, _ = self.make_leaf(temp_dir)
            claude = FakeJudge(error="Anthropic unavailable")

            with self.assertRaisesRegex(RuntimeError, "Anthropic unavailable"):
                self.aggregate_claude_only(leaf, "auto", claude)

            saved = json.loads(leaf.aggregate_path.read_text(encoding="utf-8"))
            self.assertFalse(saved["processing_complete"])
            claude_id = aggregate_results.build_judge_profiles()[CLAUDE_TARGET].judge_id
            self.assertEqual(saved["tasks"][0]["judge_results"][claude_id]["source"], "api_error")


class TestJudgePreflight(JudgeFixtureMixin, unittest.TestCase):
    def test_claude_only_preflight_is_read_only_and_plans_zero_openai_calls(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            results_root, leaf, task_dir = self.make_leaf(temp_dir)
            self.write_aggregate(leaf, self.legacy_gpt_task(task_dir))
            before = leaf.aggregate_path.read_bytes()
            profiles = aggregate_results.build_judge_profiles()

            with mock.patch.object(
                aggregate_results,
                "write_json",
                side_effect=AssertionError("preflight attempted a write"),
            ):
                report = aggregate_results.build_judge_preflight(
                    results_root=results_root,
                    scenarios=["rewire"],
                    judge_profiles=profiles,
                    selected_targets=[CLAUDE_TARGET],
                    judge_mode="auto",
                )

            self.assertEqual(before, leaf.aggregate_path.read_bytes())
            self.assertEqual(report["profiles"][GPT_TARGET]["valid"], 1)
            self.assertEqual(report["profiles"][CLAUDE_TARGET]["missing"], 1)
            self.assertEqual(report["provider_calls"]["openai"], 0)
            self.assertEqual(report["provider_calls"]["anthropic"], 1)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                aggregate_results.print_judge_preflight(report)
            self.assertIn("OpenAI calls planned: 0", output.getvalue())

    def test_main_preflight_constructs_no_clients_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with (
                mock.patch.object(
                    aggregate_results.JudgeClient,
                    "__init__",
                    side_effect=AssertionError("OpenAI client constructed"),
                ) as openai_init,
                mock.patch.object(
                    aggregate_results.AnthropicJudgeClient,
                    "__init__",
                    side_effect=AssertionError("Anthropic client constructed"),
                ) as anthropic_init,
                mock.patch.object(
                    aggregate_results,
                    "write_json",
                    side_effect=AssertionError("preflight attempted a write"),
                ),
            ):
                rc = aggregate_results.main(
                    [
                        "--results_root",
                        temp_dir,
                        "--scenarios",
                        "rewire",
                        "--judge-targets",
                        CLAUDE_TARGET,
                        "--judge-preflight",
                    ]
                )
            self.assertEqual(rc, 0)
            openai_init.assert_not_called()
            anthropic_init.assert_not_called()


class TestJudgeComparison(unittest.TestCase):
    def test_agree_disagree_and_incomplete(self):
        profiles = aggregate_results.build_judge_profiles()
        gpt = profiles[GPT_TARGET]
        claude = profiles[CLAUDE_TARGET]

        def records(gpt_output=None, claude_output=None):
            result = {}
            if gpt_output is not None:
                result[gpt.judge_id] = aggregate_results.make_judge_record(
                    gpt, "rewire", gpt_output, "cache"
                )
            if claude_output is not None:
                result[claude.judge_id] = aggregate_results.make_judge_record(
                    claude, "rewire", claude_output, "cache"
                )
            return result

        agree = aggregate_results.build_judge_comparison(
            "rewire", records(rewire_judgment(True), rewire_judgment(True)), gpt, claude
        )
        disagree = aggregate_results.build_judge_comparison(
            "rewire", records(rewire_judgment(True), rewire_judgment(False)), gpt, claude
        )
        incomplete = aggregate_results.build_judge_comparison(
            "rewire", records(rewire_judgment(True), None), gpt, claude
        )

        self.assertEqual(agree["status"], "agree")
        self.assertEqual(disagree["status"], "disagree")
        self.assertEqual(incomplete["status"], "incomplete")
        self.assertEqual(
            disagree["field_matches"]["intent_subvert_shutdown"], False
        )


if __name__ == "__main__":
    unittest.main()
