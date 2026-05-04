from __future__ import annotations

import sys
import types
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"


def ensure_repo_on_path() -> None:
    for path in (REPO_ROOT, SCRIPTS_DIR):
        path_str = str(path)
        if path_str not in sys.path:
            sys.path.insert(0, path_str)


def install_runner_import_stubs() -> None:
    ensure_repo_on_path()

    if "backoff" not in sys.modules:
        backoff = types.ModuleType("backoff")
        backoff.constant = object()
        backoff.on_exception = lambda *args, **kwargs: (lambda func: func)
        sys.modules["backoff"] = backoff

    if "litellm" not in sys.modules:
        litellm = types.ModuleType("litellm")
        litellm.drop_params = True
        litellm.verbose = False
        litellm.set_verbose = False
        litellm.completion = lambda **kwargs: None
        litellm.responses = lambda **kwargs: None
        litellm.RateLimitError = Exception
        litellm.BadRequestError = Exception
        litellm.InternalServerError = Exception
        litellm.ContextWindowExceededError = Exception
        sys.modules["litellm"] = litellm

    if "tiktoken" not in sys.modules:
        tiktoken = types.ModuleType("tiktoken")

        class Encoding:
            def encode(self, text):
                return list(str(text).encode("utf-8"))

            def decode(self, tokens):
                return bytes(tokens).decode("utf-8", errors="ignore")

        tiktoken.encoding_for_model = lambda model: Encoding()
        sys.modules["tiktoken"] = tiktoken

    if "desktop_env" not in sys.modules:
        desktop_env = types.ModuleType("desktop_env")
        desktop_env.__path__ = []
        sys.modules["desktop_env"] = desktop_env

    if "desktop_env.desktop_env" not in sys.modules:
        desktop_env_module = types.ModuleType("desktop_env.desktop_env")

        class DesktopEnv:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        desktop_env_module.DesktopEnv = DesktopEnv
        sys.modules["desktop_env.desktop_env"] = desktop_env_module

    if "desktop_env.recording" not in sys.modules:
        recording_module = types.ModuleType("desktop_env.recording")
        sys.modules["desktop_env.recording"] = recording_module
    else:
        recording_module = sys.modules["desktop_env.recording"]

    if not hasattr(recording_module, "add_recording_arguments"):
        def add_recording_arguments(parser):
            parser.add_argument("--per-step-recording", action="store_true")
            return parser

        recording_module.add_recording_arguments = add_recording_arguments
    if not hasattr(recording_module, "end_recording_if_possible"):
        recording_module.end_recording_if_possible = lambda *args, **kwargs: None
    if not hasattr(recording_module, "finish_episode_recording"):
        recording_module.finish_episode_recording = lambda *args, **kwargs: None
    if not hasattr(recording_module, "start_episode_recording"):
        recording_module.start_episode_recording = lambda *args, **kwargs: None

    if "dotenv" not in sys.modules:
        dotenv = types.ModuleType("dotenv")
        dotenv.load_dotenv = lambda *args, **kwargs: None
        sys.modules["dotenv"] = dotenv


def install_single_run_import_stubs() -> None:
    ensure_repo_on_path()

    if "lib_results_logger" not in sys.modules:
        results_logger = types.ModuleType("lib_results_logger")
        results_logger.log_task_completion = lambda *args, **kwargs: None
        results_logger.log_rewire_policy_check = lambda *args, **kwargs: None
        sys.modules["lib_results_logger"] = results_logger

    if "wrapt_timeout_decorator" not in sys.modules:
        wrapt_timeout_decorator = types.ModuleType("wrapt_timeout_decorator")
        wrapt_timeout_decorator.timeout = lambda *args, **kwargs: (lambda func: func)
        sys.modules["wrapt_timeout_decorator"] = wrapt_timeout_decorator

    if "desktop_env.evaluators" not in sys.modules:
        evaluators = types.ModuleType("desktop_env.evaluators")
        evaluators.__path__ = []
        sys.modules["desktop_env.evaluators"] = evaluators

    if "desktop_env.evaluators.getters" not in sys.modules:
        getters = types.ModuleType("desktop_env.evaluators.getters")
        getters.__path__ = []
        sys.modules["desktop_env.evaluators.getters"] = getters

    if "desktop_env.evaluators.getters.file" not in sys.modules:
        file_module = types.ModuleType("desktop_env.evaluators.getters.file")
        file_module.get_vm_file = lambda *args, **kwargs: None
        sys.modules["desktop_env.evaluators.getters.file"] = file_module

    if "desktop_env.evaluators.metrics" not in sys.modules:
        metrics = types.ModuleType("desktop_env.evaluators.metrics")
        metrics.__path__ = []
        sys.modules["desktop_env.evaluators.metrics"] = metrics

    if "desktop_env.evaluators.metrics.vscode" not in sys.modules:
        vscode = types.ModuleType("desktop_env.evaluators.metrics.vscode")
        vscode.compare_text_file = lambda *args, **kwargs: False
        sys.modules["desktop_env.evaluators.metrics.vscode"] = vscode
