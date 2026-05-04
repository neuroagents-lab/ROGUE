import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock


def _install_test_stubs():
    if "lib_results_logger" not in sys.modules:
        results_logger = types.ModuleType("lib_results_logger")
        results_logger.log_task_completion = lambda *args, **kwargs: None
        results_logger.log_rewire_policy_check = lambda *args, **kwargs: None
        sys.modules["lib_results_logger"] = results_logger

    if "wrapt_timeout_decorator" not in sys.modules:
        wrapt_timeout_decorator = types.ModuleType("wrapt_timeout_decorator")

        def timeout(*args, **kwargs):
            def decorator(func):
                return func
            return decorator

        wrapt_timeout_decorator.timeout = timeout
        sys.modules["wrapt_timeout_decorator"] = wrapt_timeout_decorator

    if "desktop_env" not in sys.modules:
        desktop_env = types.ModuleType("desktop_env")
        desktop_env.__path__ = []
        sys.modules["desktop_env"] = desktop_env
    if "desktop_env.recording" not in sys.modules:
        recording_module = types.ModuleType("desktop_env.recording")
        recording_module.add_recording_arguments = lambda parser: (
            parser.add_argument("--per-step-recording", action="store_true"), parser
        )[1]
        recording_module.end_recording_if_possible = lambda *args, **kwargs: None
        recording_module.finish_episode_recording = lambda *args, **kwargs: None
        recording_module.start_episode_recording = lambda *args, **kwargs: None
        sys.modules["desktop_env.recording"] = recording_module
    if "desktop_env.evaluators" not in sys.modules:
        desktop_env_evaluators = types.ModuleType("desktop_env.evaluators")
        desktop_env_evaluators.__path__ = []
        sys.modules["desktop_env.evaluators"] = desktop_env_evaluators
    if "desktop_env.evaluators.getters" not in sys.modules:
        desktop_env_getters = types.ModuleType("desktop_env.evaluators.getters")
        desktop_env_getters.__path__ = []
        sys.modules["desktop_env.evaluators.getters"] = desktop_env_getters
    if "desktop_env.evaluators.getters.file" not in sys.modules:
        file_module = types.ModuleType("desktop_env.evaluators.getters.file")
        file_module.get_vm_file = lambda *args, **kwargs: None
        sys.modules["desktop_env.evaluators.getters.file"] = file_module
    if "desktop_env.evaluators.metrics" not in sys.modules:
        desktop_env_metrics = types.ModuleType("desktop_env.evaluators.metrics")
        desktop_env_metrics.__path__ = []
        sys.modules["desktop_env.evaluators.metrics"] = desktop_env_metrics
    if "desktop_env.evaluators.metrics.vscode" not in sys.modules:
        vscode_module = types.ModuleType("desktop_env.evaluators.metrics.vscode")
        vscode_module.compare_text_file = lambda *args, **kwargs: None
        sys.modules["desktop_env.evaluators.metrics.vscode"] = vscode_module
    if "mm_agents" not in sys.modules:
        mm_agents = types.ModuleType("mm_agents")
        mm_agents.__path__ = [str(Path(__file__).resolve().parents[1] / "mm_agents")]
        sys.modules["mm_agents"] = mm_agents
    if "mm_agents.os_symphony" not in sys.modules:
        os_symphony = types.ModuleType("mm_agents.os_symphony")
        os_symphony.__path__ = []
        sys.modules["mm_agents.os_symphony"] = os_symphony
    if "mm_agents.os_symphony.utils" not in sys.modules:
        os_symphony_utils = types.ModuleType("mm_agents.os_symphony.utils")
        os_symphony_utils.__path__ = []
        sys.modules["mm_agents.os_symphony.utils"] = os_symphony_utils
    if "mm_agents.os_symphony.utils.common_utils" not in sys.modules:
        common_utils = types.ModuleType("mm_agents.os_symphony.utils.common_utils")
        common_utils.draw_coordinates = lambda *args, **kwargs: None
        sys.modules["mm_agents.os_symphony.utils.common_utils"] = common_utils
    if "mm_agents.os_symphony.utils.process_context" not in sys.modules:
        process_context = types.ModuleType("mm_agents.os_symphony.utils.process_context")
        process_context.set_current_result_dir = lambda *args, **kwargs: None
        sys.modules["mm_agents.os_symphony.utils.process_context"] = process_context


_install_test_stubs()

from lib_run_single import _is_popup_process_running


class TestPopupProcessDetection(unittest.TestCase):
    def test_check_script_avoids_self_matching_pgrep_probe(self):
        env = MagicMock()
        captured = {}

        def fake_run_bash_script(script, timeout=5):
            captured["script"] = script
            return {"output": "CLOSED", "returncode": 0}

        env.controller.run_bash_script.side_effect = fake_run_bash_script

        result = _is_popup_process_running(env, "/tmp/osworld_override_popup.py")

        self.assertFalse(result)
        self.assertIn('Path("/proc").iterdir()', captured["script"])
        self.assertNotIn("pgrep -f", captured["script"])
        self.assertIn("/tmp/osworld_override_popup.py", captured["script"])

    def test_open_output_is_respected(self):
        env = MagicMock()
        env.controller.run_bash_script.return_value = {"output": "OPEN", "returncode": 0}

        self.assertTrue(_is_popup_process_running(env, "/tmp/osworld_override_popup.py"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
