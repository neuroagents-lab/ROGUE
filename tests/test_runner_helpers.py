import contextlib
import io
import json
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

from tests.support import install_runner_import_stubs


install_runner_import_stubs()

import lib_run_litellm


class TestDesktopRunnerParser(unittest.TestCase):
    def test_multienv_parser_accepts_documented_experiment_flags(self):
        parser = lib_run_litellm.build_parser(
            default_provider="vmware",
            default_observation_type="a11y_tree",
            include_parallelism=True,
            include_log_level=True,
        )

        args = parser.parse_args(
            [
                "--provider_name",
                "aws",
                "--headless",
                "--action_space",
                "pyautogui",
                "--observation_type",
                "screenshot_a11y_tree",
                "--max_steps",
                "25",
                "--max_trajectory_length",
                "15",
                "--per-step-recording",
                "--deployment-prompt",
                "--inoculation-prompt",
                "--show_steps_left_in_prompt",
                "--model",
                "dashscope/qwen3.6-plus",
                "--reasoning_effort",
                "medium",
                "--test_all_meta_path",
                "evaluation_examples/test_rewire.json",
                "--result_dir",
                "./results/rewire/base/",
                "--num_envs",
                "5",
                "--region",
                "us-east-1",
                "--client_password",
                "secret",
                "--log_level",
                "DEBUG",
            ]
        )

        self.assertEqual(args.provider_name, "aws")
        self.assertTrue(args.headless)
        self.assertTrue(args.per_step_recording)
        self.assertTrue(args.deployment_prompt)
        self.assertTrue(args.inoculation_prompt)
        self.assertTrue(args.show_steps_left_in_prompt)
        self.assertEqual(args.num_envs, 5)
        self.assertEqual(args.log_level, "DEBUG")
        self.assertEqual(args.model, "dashscope/qwen3.6-plus")

    def test_single_env_parser_excludes_parallelism_and_log_level(self):
        parser = lib_run_litellm.build_parser(
            default_provider="vmware",
            default_observation_type="a11y_tree",
            include_parallelism=False,
            include_log_level=False,
        )

        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                parser.parse_args(["--num_envs", "2"])
            with self.assertRaises(SystemExit):
                parser.parse_args(["--log_level", "DEBUG"])


class TestRunnerHelperFunctions(unittest.TestCase):
    def _args(self, **overrides):
        values = {
            "result_dir": "results",
            "action_space": "pyautogui",
            "observation_type": "screenshot",
            "model": "gpt-5.4",
            "path_to_vm": None,
            "provider_name": "vmware",
            "screen_width": 1920,
            "screen_height": 1080,
            "headless": False,
            "enable_proxy": False,
            "client_password": "",
            "region": "us-east-1",
        }
        values.update(overrides)
        return types.SimpleNamespace(**values)

    def test_build_prompt_agent_forwards_runner_flags(self):
        args = self._args(
            max_tokens=1234,
            top_p=0.7,
            temperature=0.2,
            max_trajectory_length=9,
            max_steps=40,
            show_steps_left_in_prompt=True,
            reasoning_effort="medium",
            environment_question=True,
            deployment_prompt=True,
            evaluation_prompt=True,
            inoculation_prompt=True,
            enable_subagents=True,
            subagent_inherit_parent_history=True,
            client_password="secret",
        )

        agent = lib_run_litellm.build_prompt_agent(args)

        self.assertEqual(agent.model, "gpt-5.4")
        self.assertEqual(agent.max_tokens, 1234)
        self.assertEqual(agent.action_space, "pyautogui")
        self.assertEqual(agent.observation_type, "screenshot")
        self.assertEqual(agent.max_steps, 40)
        self.assertTrue(agent.show_steps_left_in_prompt)
        self.assertTrue(agent.enable_subagents)
        self.assertTrue(agent.subagent_inherit_parent_history)

    def test_build_desktop_env_maps_aws_region_snapshot_and_a11y_requirement(self):
        aws_manager = types.ModuleType("desktop_env.providers.aws.manager")
        aws_manager.IMAGE_ID_MAP = {
            "us-east-1": {
                (1920, 1080): "ami-default",
                (1280, 720): "ami-small",
            }
        }

        with mock.patch.dict(
            "sys.modules",
            {"desktop_env.providers.aws.manager": aws_manager},
        ):
            env = lib_run_litellm.build_desktop_env(
                self._args(
                    provider_name="aws",
                    observation_type="screenshot_a11y_tree",
                    screen_width=1280,
                    screen_height=720,
                    headless=True,
                    enable_proxy=True,
                    client_password="secret",
                ),
                action_space="agent-action-space",
            )

        self.assertEqual(env.kwargs["provider_name"], "aws")
        self.assertEqual(env.kwargs["action_space"], "agent-action-space")
        self.assertEqual(env.kwargs["screen_size"], (1280, 720))
        self.assertTrue(env.kwargs["require_a11y_tree"])
        self.assertTrue(env.kwargs["headless"])
        self.assertTrue(env.kwargs["enable_proxy"])
        self.assertEqual(env.kwargs["region"], "us-east-1")
        self.assertEqual(env.kwargs["snapshot_name"], "ami-small")

    def test_save_args_and_load_meta_use_flattened_model_dir_and_domain_filter(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            meta_path = Path(tmp_dir) / "meta.json"
            meta_path.write_text(
                json.dumps({"override": ["one"], "rewire": ["two"]}),
                encoding="utf-8",
            )
            args = self._args(
                result_dir=str(Path(tmp_dir) / "results"),
                model="dashscope/qwen3.6-plus",
                test_all_meta_path=str(meta_path),
                domain="override",
            )

            lib_run_litellm.save_args(args)
            loaded = lib_run_litellm.load_test_all_meta(args)

            args_path = (
                Path(tmp_dir)
                / "results"
                / "pyautogui"
                / "screenshot"
                / "dashscope__qwen3.6-plus"
                / "args.json"
            )
            self.assertTrue(args_path.exists())
            self.assertEqual(json.loads(args_path.read_text(encoding="utf-8"))["domain"], "override")
            self.assertEqual(loaded, {"override": ["one"]})

    def test_get_unfinished_skips_finished_tasks_and_cleans_incomplete_dirs(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            model_root = (
                Path(tmp_dir)
                / "pyautogui"
                / "screenshot"
                / "gpt-5.4"
                / "override"
            )
            done_dir = model_root / "done"
            incomplete_dir = model_root / "incomplete"
            done_dir.mkdir(parents=True)
            incomplete_dir.mkdir(parents=True)
            (done_dir / "result.txt").write_text("1.0", encoding="utf-8")
            (incomplete_dir / "traj.jsonl").write_text("partial", encoding="utf-8")
            (incomplete_dir / "step.png").write_bytes(b"png")

            unfinished = lib_run_litellm.get_unfinished(
                "pyautogui",
                "gpt-5.4",
                "screenshot",
                tmp_dir,
                {"override": ["done", "incomplete", "new"]},
            )

            self.assertEqual(unfinished, {"override": ["incomplete", "new"]})
            self.assertEqual(list(incomplete_dir.iterdir()), [])

    def test_get_result_reads_scores_and_treats_invalid_result_as_zero(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            model_root = (
                Path(tmp_dir)
                / "pyautogui"
                / "screenshot"
                / "gpt-5.4"
                / "override"
            )
            first = model_root / "first"
            second = model_root / "second"
            first.mkdir(parents=True)
            second.mkdir(parents=True)
            (first / "result.txt").write_text("1.0", encoding="utf-8")
            (second / "result.txt").write_text("not-a-number", encoding="utf-8")

            with contextlib.redirect_stdout(io.StringIO()):
                results = lib_run_litellm.get_result(
                    "pyautogui",
                    "gpt-5.4",
                    "screenshot",
                    tmp_dir,
                )

        self.assertCountEqual(results, [1.0, 0.0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
