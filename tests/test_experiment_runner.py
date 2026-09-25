import os
import shlex
import subprocess
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
RUNNER = ROOT_DIR / "scripts" / "experiment_runner.sh"


class TestMaxReasoningExperimentJobs(unittest.TestCase):
    MODELS = (
        ("gpt56solmax", "gpt-5.6-sol"),
        ("gpt6astramax", "gpt-6-astra"),
    )
    SCENARIOS = (
        "override",
        "rewire",
        "restrictedaccess",
        "subagents_restrictedaccess",
    )

    def _run_runner(self, job_name, *extra_args, env_overrides=None):
        env = os.environ.copy()
        env.pop("NUM_ENVS", None)
        env.update({"PYTHON_BIN": "echo"})
        env.update(env_overrides or {})
        return subprocess.run(
            [str(RUNNER), job_name, *extra_args],
            cwd=ROOT_DIR,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )

    def _run_job(self, job_name):
        completed = self._run_runner(job_name)
        command = next(
            line
            for line in completed.stdout.splitlines()
            if line.startswith("scripts/python/run_multienv.py")
        )
        return shlex.split(command)

    def test_requested_jobs_are_in_their_scenario_aggregates(self):
        cases = {
            "override_xhigh_all": "override",
            "rewire_xhigh_all": "rewire",
            "restrictedaccess_xhigh_all": "restrictedaccess",
            "restrictedaccess_subagents_all": "subagents_restrictedaccess",
        }

        for aggregate, scenario in cases.items():
            completed = self._run_runner(aggregate)
            for prefix, _ in self.MODELS:
                with self.subTest(aggregate=aggregate, model=prefix):
                    self.assertIn(f"Starting {prefix}_{scenario} ", completed.stdout)

    def _assert_option(self, command, option, expected):
        values = [
            command[index + 1]
            for index, token in enumerate(command[:-1])
            if token == option
        ]
        self.assertTrue(values, f"{option} was not present in {command}")
        self.assertEqual(values[-1], expected)

    def test_requested_jobs_match_gpt55_xhigh_settings(self):
        cases = {
            "override": {
                "max_steps": "20",
                "max_trajectory_length": "20",
                "meta": "evaluation_examples/test_override.json",
                "result_dir": "./results/override/xhighreasoningeffort",
                "flags": set(),
            },
            "rewire": {
                "max_steps": "25",
                "max_trajectory_length": "25",
                "meta": "evaluation_examples/test_rewire.json",
                "result_dir": "./results/rewire/xhighreasoningeffort",
                "flags": {"--deployment-prompt"},
            },
            "restrictedaccess": {
                "max_steps": "40",
                "max_trajectory_length": "20",
                "meta": "evaluation_examples/test_restrictedaccess.json",
                "result_dir": "./results/restrictedaccess/xhighreasoningeffort",
                "flags": {"--deployment-prompt", "--show_steps_left_in_prompt"},
            },
            "subagents_restrictedaccess": {
                "max_steps": "50",
                "max_trajectory_length": "20",
                "meta": "evaluation_examples/test_subagents_restrictedaccess.json",
                "result_dir": "./results/subagents/restrictedaccess/xhighreasoningeffort",
                "flags": {
                    "--deployment-prompt",
                    "--enable_subagents",
                    "--show_steps_left_in_prompt",
                },
            },
        }

        for prefix, model in self.MODELS:
            for scenario, expected in cases.items():
                with self.subTest(model=model, scenario=scenario):
                    job_name = f"{prefix}_{scenario}"
                    command = self._run_job(job_name)
                    self._assert_option(command, "--model", model)
                    self._assert_option(command, "--reasoning_effort", "max")
                    self._assert_option(command, "--max_tokens", "100000")
                    self._assert_option(command, "--observation_type", "screenshot")
                    self._assert_option(command, "--max_steps", expected["max_steps"])
                    self._assert_option(
                        command,
                        "--max_trajectory_length",
                        expected["max_trajectory_length"],
                    )
                    self._assert_option(command, "--test_all_meta_path", expected["meta"])
                    self._assert_option(command, "--result_dir", expected["result_dir"])
                    self._assert_option(command, "--num_envs", "5")
                    scenario_flags = {
                        "--deployment-prompt",
                        "--enable_subagents",
                        "--show_steps_left_in_prompt",
                    }
                    self.assertEqual(scenario_flags.intersection(command), expected["flags"])

    def test_astra_model_aggregates_dispatch_each_requested_job_once(self):
        for aggregate, scenarios in (
            ("gpt6astramax", self.SCENARIOS[:3]),
            ("gpt6astramax_subagents", self.SCENARIOS[3:]),
            ("gpt6astramax_all", self.SCENARIOS),
        ):
            with self.subTest(aggregate=aggregate):
                completed = self._run_runner(aggregate)
                started_jobs = [
                    line.split("Starting ", 1)[1].split()[0]
                    for line in completed.stdout.splitlines()
                    if "Starting " in line
                ]
                self.assertEqual(
                    started_jobs,
                    [f"gpt6astramax_{scenario}" for scenario in scenarios],
                )

    def test_astra_jobs_are_in_family_and_full_aggregates(self):
        for aggregate, scenarios in (
            ("gpt_family_xhigh", self.SCENARIOS[:3]),
            ("gpt_family_subagents", self.SCENARIOS[3:]),
            ("gpt_family_all", self.SCENARIOS),
            ("all", self.SCENARIOS),
        ):
            with self.subTest(aggregate=aggregate):
                completed = self._run_runner(aggregate)
                started_jobs = [
                    line.split("Starting ", 1)[1].split()[0]
                    for line in completed.stdout.splitlines()
                    if "Starting gpt6astramax_" in line
                ]
                self.assertEqual(
                    started_jobs,
                    [f"gpt6astramax_{scenario}" for scenario in scenarios],
                )

    def test_astra_jobs_are_listed(self):
        completed = self._run_runner("list")
        listed_jobs = {line.strip() for line in completed.stdout.splitlines()}
        self.assertTrue(
            {
                "gpt6astramax",
                "gpt6astramax_subagents",
                "gpt6astramax_all",
                *(f"gpt6astramax_{scenario}" for scenario in self.SCENARIOS),
            }.issubset(listed_jobs)
        )

    def test_astra_suite_preserves_environment_and_argument_overrides(self):
        completed = self._run_runner(
            "gpt6astramax_all",
            "--",
            "--num_envs",
            "2",
            "--max_steps",
            "1",
            env_overrides={"NUM_ENVS": "3", "REGION": "us-west-2"},
        )
        commands = [
            shlex.split(line)
            for line in completed.stdout.splitlines()
            if line.startswith("scripts/python/run_multienv.py")
        ]
        self.assertEqual(len(commands), 4)
        for command in commands:
            with self.subTest(meta=command[command.index("--test_all_meta_path") + 1]):
                self.assertEqual(command[command.index("--num_envs") + 1], "3")
                self._assert_option(command, "--num_envs", "2")
                self._assert_option(command, "--region", "us-west-2")
                self._assert_option(command, "--max_steps", "1")


if __name__ == "__main__":
    unittest.main(verbosity=2)
