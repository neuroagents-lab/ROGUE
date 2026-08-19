import os
import shlex
import subprocess
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
RUNNER = ROOT_DIR / "scripts" / "experiment_runner.sh"


class TestGpt56SolExperimentJobs(unittest.TestCase):
    def _run_runner(self, job_name):
        env = os.environ.copy()
        env.update({"PYTHON_BIN": "echo", "NUM_ENVS": "5"})
        return subprocess.run(
            [str(RUNNER), job_name],
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
            "override_xhigh_all": "gpt56solmax_override",
            "rewire_xhigh_all": "gpt56solmax_rewire",
            "restrictedaccess_xhigh_all": "gpt56solmax_restrictedaccess",
            "restrictedaccess_subagents_all": "gpt56solmax_subagents_restrictedaccess",
        }

        for aggregate, expected_job in cases.items():
            with self.subTest(aggregate=aggregate):
                completed = self._run_runner(aggregate)
                self.assertIn(f"Starting {expected_job} ", completed.stdout)

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
            "gpt56solmax_override": {
                "max_steps": "20",
                "max_trajectory_length": "20",
                "meta": "evaluation_examples/test_override.json",
                "result_dir": "./results/override/xhighreasoningeffort",
                "flags": set(),
            },
            "gpt56solmax_rewire": {
                "max_steps": "25",
                "max_trajectory_length": "25",
                "meta": "evaluation_examples/test_rewire.json",
                "result_dir": "./results/rewire/xhighreasoningeffort",
                "flags": {"--deployment-prompt"},
            },
            "gpt56solmax_restrictedaccess": {
                "max_steps": "40",
                "max_trajectory_length": "20",
                "meta": "evaluation_examples/test_restrictedaccess.json",
                "result_dir": "./results/restrictedaccess/xhighreasoningeffort",
                "flags": {"--deployment-prompt", "--show_steps_left_in_prompt"},
            },
            "gpt56solmax_subagents_restrictedaccess": {
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

        for job_name, expected in cases.items():
            with self.subTest(job_name=job_name):
                command = self._run_job(job_name)
                self._assert_option(command, "--model", "gpt-5.6-sol")
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
                for flag in expected["flags"]:
                    self.assertIn(flag, command)


if __name__ == "__main__":
    unittest.main(verbosity=2)
