"""
Test that clicking 'Accept' in the override popup terminates the episode.

Inlines the _consume_popup_choice logic and the while-loop termination path
so no VM dependencies are needed.

To run this test, run "python test_accept_terminates.py"
"""
import unittest
from unittest.mock import MagicMock


def _consume_popup_choice(env, choice_file):
    """Inlined from lib_run_single — reads and deletes the choice file on the VM."""
    consume_script = f"""#!/usr/bin/env bash
set -e

if [ -f {choice_file!r} ]; then
  cat {choice_file!r}
  rm -f {choice_file!r}
fi
"""
    result = env.controller.run_bash_script(consume_script, timeout=5)
    if not isinstance(result, dict):
        return None
    choice = (result.get("output") or "").strip()
    if choice in {"Accept", "Override"}:
        return choice
    return None


def _run_loop(env, override_choice_sequence, max_steps=10):
    """
    Replicate the relevant portion of the while-loop from
    lib_run_single.run_single_example, focused on the Accept termination path.
    """
    # Feed choices from the sequence; return '' once exhausted
    choice_iter = iter(override_choice_sequence)

    def fake_run_bash(script, timeout=5):
        if "osworld_override_choice" in script and "cat" in script:
            return {"output": next(choice_iter, ""), "returncode": 0}
        return {"output": "", "returncode": 0}

    env.controller.run_bash_script.side_effect = fake_run_bash

    obs = {"screenshot": b"fake_png"}
    agent = MagicMock()
    agent.predict.return_value = ("response", ["WAIT"])
    env.step.return_value = (obs, 0.0, False, {})

    override_click_history = []
    done = False
    step_idx = 0

    while not done and step_idx < max_steps:
        override_choice = _consume_popup_choice(env, "/tmp/osworld_override_choice.txt")
        if override_choice:
            override_click_history.append({
                "index": len(override_click_history) + 1,
                "choice": override_choice,
                "loop_step": step_idx + 1,
            })
            if override_choice == "Accept":
                done = True
                break

        if done:
            break

        _, actions = agent.predict("instruction", obs)
        for action in actions:
            obs, reward, done, info = env.step(action, 0)
            if done:
                break
        step_idx += 1

    return override_click_history, done, env.step.call_count


class TestAcceptTerminatesEpisode(unittest.TestCase):

    def test_accept_terminates_immediately(self):
        """Episode ends on the same iteration Accept is detected; no agent steps taken."""
        env = MagicMock()
        clicks, done, step_calls = _run_loop(env, override_choice_sequence=["Accept"])

        self.assertTrue(done)
        self.assertEqual(len(clicks), 1)
        self.assertEqual(clicks[0]["choice"], "Accept")
        self.assertEqual(step_calls, 0, "env.step should not be called after Accept")

    def test_override_does_not_terminate(self):
        """Override should NOT set done; the agent continues acting."""
        env = MagicMock()
        clicks, done, step_calls = _run_loop(env, override_choice_sequence=["Override"])

        self.assertFalse(done)
        self.assertEqual(clicks[0]["choice"], "Override")
        self.assertGreater(step_calls, 0, "Agent should still act after Override")

    def test_no_click_continues_normally(self):
        """No popup choice — episode runs to max_steps."""
        env = MagicMock()
        clicks, done, step_calls = _run_loop(env, override_choice_sequence=[], max_steps=5)

        self.assertFalse(done)
        self.assertEqual(len(clicks), 0)
        self.assertEqual(step_calls, 5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
