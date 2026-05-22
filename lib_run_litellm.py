import argparse
import datetime
import json
import logging
import os
import sys
from typing import Dict, Optional

from desktop_env.desktop_env import DesktopEnv
from desktop_env.recording import add_recording_arguments, end_recording_if_possible
from mm_agents.agent_litellm import PromptAgent
from task_utils import result_model_name


EXPERIMENT_LOGGER_NAME = "desktopenv.experiment"
SUPPORTED_PROVIDERS = (
    "vmware",
    "docker",
    "aws",
    "azure",
    "gcp",
    "virtualbox",
    "aliyun",
    "volcengine",
)

class DesktopRunnerArgumentParser(argparse.ArgumentParser):
    def parse_args(self, args=None, namespace=None):
        parsed_args = super().parse_args(args=args, namespace=namespace)
        if (
            getattr(parsed_args, "subagent_inherit_parent_history", False)
            and not getattr(parsed_args, "enable_subagents", False)
        ):
            self.error("--subagent_inherit_parent_history requires --enable_subagents")
        return parsed_args


def build_parser(
    *,
    default_provider: str,
    default_observation_type: str,
    include_parallelism: bool,
    include_log_level: bool,
) -> argparse.ArgumentParser:
    parser = DesktopRunnerArgumentParser(
        description="Run end-to-end evaluation on the benchmark"
    )

    parser.add_argument("--path_to_vm", type=str, default=None)
    parser.add_argument(
        "--provider_name",
        type=str,
        default=default_provider,
        choices=SUPPORTED_PROVIDERS,
        help="Virtualization provider",
    )
    parser.add_argument(
        "--headless", action="store_true", help="Run in headless machine"
    )
    parser.add_argument(
        "--action_space", type=str, default="pyautogui", help="Action type"
    )
    parser.add_argument(
        "--observation_type",
        choices=["screenshot", "a11y_tree", "screenshot_a11y_tree", "som"],
        default=default_observation_type,
        help="Observation type",
    )
    parser.add_argument("--screen_width", type=int, default=1920)
    parser.add_argument("--screen_height", type=int, default=1080)
    parser.add_argument("--sleep_after_execution", type=float, default=0.0)
    parser.add_argument("--max_steps", type=int, default=15)
    parser.add_argument(
        "--show_steps_left_in_prompt",
        action="store_true",
        help="Append the remaining step budget to the agent prompt at each timestep.",
    )
    add_recording_arguments(parser)

    parser.add_argument(
        "--enable_proxy",
        dest="enable_proxy",
        action="store_true",
        default=False,
        help="Enable proxy support inside the VM.",
    )

    parser.add_argument("--max_trajectory_length", type=int, default=25)
    parser.add_argument(
        "--environment-question",
        action="store_true",
        help="Append ENVIRONMENT_QUESTION to the system prompt.",
    )
    parser.add_argument(
        "--deployment-prompt",
        action="store_true",
        help="Append DEPLOYMENT_PROMPT to the system prompt.",
    )
    parser.add_argument(
        "--evaluation-prompt",
        action="store_true",
        help="Append EVALUATION_PROMPT to the system prompt.",
    )
    parser.add_argument(
        "--inoculation-prompt",
        action="store_true",
        help="Append INOCULATION_PROMPT to the system prompt.",
    )
    parser.add_argument(
        "--enable_subagents",
        action="store_true",
        help="Allow the agent to delegate well-scoped subtasks via SUBAGENT(...).",
    )
    parser.add_argument(
        "--subagent_inherit_parent_history",
        action="store_true",
        help="Allow spawned subagents to inherit the parent agent's trajectory history.",
    )
    parser.add_argument(
        "--test_config_base_dir", type=str, default="evaluation_examples"
    )

    parser.add_argument("--model", type=str, default="gpt-5.4")
    parser.add_argument("--temperature", type=float, default=1.0)
    parser.add_argument("--top_p", type=float, default=0.9)
    parser.add_argument("--max_tokens", type=int, default=1500)
    parser.add_argument("--reasoning_effort", type=str, default="low")
    parser.add_argument("--stop_token", type=str, default=None)

    parser.add_argument("--domain", type=str, default="all")
    parser.add_argument(
        "--test_all_meta_path", type=str, default="evaluation_examples/test_all.json"
    )

    parser.add_argument("--result_dir", type=str, default="./results")
    if include_parallelism:
        parser.add_argument(
            "--num_envs",
            type=int,
            default=1,
            help="Number of environments to run in parallel",
        )
    if include_log_level:
        parser.add_argument(
            "--log_level",
            type=str,
            choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            default="INFO",
            help="Set the stdout logging level",
        )

    parser.add_argument(
        "--region", type=str, default="us-east-1", help="AWS region for the VM"
    )
    parser.add_argument(
        "--client_password", type=str, default="", help="Client password"
    )

    return parser


def configure_root_logger(
    *,
    stdout_level: str,
    log_timestamp: str,
    include_sdebug: bool,
) -> logging.Logger:
    os.makedirs("logs", exist_ok=True)

    root_logger = logging.getLogger()
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)
        try:
            handler.close()
        except Exception:
            pass
    root_logger.setLevel(logging.DEBUG)

    file_handler = logging.FileHandler(
        os.path.join("logs", f"normal-{log_timestamp}.log"), encoding="utf-8"
    )
    debug_handler = logging.FileHandler(
        os.path.join("logs", f"debug-{log_timestamp}.log"), encoding="utf-8"
    )
    stdout_handler = logging.StreamHandler(sys.stdout)

    handlers = [file_handler, debug_handler, stdout_handler]
    if include_sdebug:
        sdebug_handler = logging.FileHandler(
            os.path.join("logs", f"sdebug-{log_timestamp}.log"), encoding="utf-8"
        )
        handlers.append(sdebug_handler)
    else:
        sdebug_handler = None

    file_handler.setLevel(logging.INFO)
    debug_handler.setLevel(logging.DEBUG)
    stdout_handler.setLevel(getattr(logging, stdout_level.upper(), logging.INFO))
    if sdebug_handler is not None:
        sdebug_handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        fmt="\x1b[1;33m[%(asctime)s \x1b[31m%(levelname)s \x1b[32m%(module)s/%(lineno)d-%(processName)s\x1b[1;33m] \x1b[0m%(message)s"
    )
    for handler in handlers:
        handler.setFormatter(formatter)

    stdout_handler.addFilter(logging.Filter("desktopenv"))
    if sdebug_handler is not None:
        sdebug_handler.addFilter(logging.Filter("desktopenv"))

    for handler in handlers:
        root_logger.addHandler(handler)

    return logging.getLogger(EXPERIMENT_LOGGER_NAME)


def build_prompt_agent(args: argparse.Namespace) -> PromptAgent:
    return PromptAgent(
        model=args.model,
        max_tokens=args.max_tokens,
        top_p=args.top_p,
        temperature=args.temperature,
        action_space=args.action_space,
        observation_type=args.observation_type,
        max_trajectory_length=args.max_trajectory_length,
        client_password=args.client_password,
        max_steps=args.max_steps,
        show_steps_left_in_prompt=args.show_steps_left_in_prompt,
        reasoning_effort=args.reasoning_effort,
        environment_question=args.environment_question,
        deployment_prompt=args.deployment_prompt,
        evaluation_prompt=args.evaluation_prompt,
        inoculation_prompt=args.inoculation_prompt,
        enable_subagents=args.enable_subagents,
        subagent_inherit_parent_history=args.subagent_inherit_parent_history,
    )
def build_desktop_env(
    args: argparse.Namespace, *, action_space: Optional[str] = None
) -> DesktopEnv:
    screen_size = (args.screen_width, args.screen_height)
    env_kwargs = dict(
        provider_name=args.provider_name,
        path_to_vm=args.path_to_vm,
        action_space=action_space or args.action_space,
        screen_size=screen_size,
        headless=args.headless,
        os_type="Ubuntu",
        require_a11y_tree=args.observation_type
        in ["a11y_tree", "screenshot_a11y_tree", "som"],
        enable_proxy=args.enable_proxy,
        client_password=args.client_password,
    )
    if args.provider_name == "aws":
        from desktop_env.providers.aws.manager import IMAGE_ID_MAP

        ami_id = IMAGE_ID_MAP[args.region].get(
            screen_size, IMAGE_ID_MAP[args.region][(1920, 1080)]
        )
        env_kwargs["region"] = args.region
        env_kwargs["snapshot_name"] = ami_id
    return DesktopEnv(**env_kwargs)
def result_model_dir(args: argparse.Namespace) -> str:
    return os.path.join(
        args.result_dir,
        args.action_space,
        args.observation_type,
        result_model_name(args.model),
    )


def save_args(args: argparse.Namespace) -> None:
    path_to_args = os.path.join(result_model_dir(args), "args.json")
    os.makedirs(os.path.dirname(path_to_args), exist_ok=True)
    with open(path_to_args, "w", encoding="utf-8") as f:
        json.dump(vars(args), f, indent=4)


def load_test_all_meta(args: argparse.Namespace) -> Dict[str, list]:
    with open(args.test_all_meta_path, "r", encoding="utf-8") as f:
        test_all_meta = json.load(f)
    if args.domain != "all":
        test_all_meta = {args.domain: test_all_meta[args.domain]}
    return test_all_meta


def get_unfinished(
    action_space: str,
    use_model: str,
    observation_type: str,
    result_dir: str,
    total_file_json: Dict[str, list],
) -> Dict[str, list]:
    target_dir = os.path.join(
        result_dir,
        action_space,
        observation_type,
        result_model_name(use_model),
    )
    if not os.path.exists(target_dir):
        return total_file_json

    finished = {}
    for domain in os.listdir(target_dir):
        finished[domain] = []
        domain_path = os.path.join(target_dir, domain)
        if not os.path.isdir(domain_path):
            continue
        for example_id in os.listdir(domain_path):
            if example_id == "onboard":
                continue
            example_path = os.path.join(domain_path, example_id)
            if not os.path.isdir(example_path):
                continue
            if "result.txt" not in os.listdir(example_path):
                for file_name in os.listdir(example_path):
                    os.remove(os.path.join(example_path, file_name))
            else:
                finished[domain].append(example_id)

    if not finished:
        return total_file_json

    for domain, examples in finished.items():
        if domain in total_file_json:
            total_file_json[domain] = [
                example_id
                for example_id in total_file_json[domain]
                if example_id not in examples
            ]
    return total_file_json


def get_result(
    action_space: str,
    use_model: str,
    observation_type: str,
    result_dir: str,
) -> Optional[list]:
    target_dir = os.path.join(
        result_dir,
        action_space,
        observation_type,
        result_model_name(use_model),
    )
    if not os.path.exists(target_dir):
        print("New experiment, no result yet.")
        return None

    all_result = []
    for domain in os.listdir(target_dir):
        domain_path = os.path.join(target_dir, domain)
        if not os.path.isdir(domain_path):
            continue
        for example_id in os.listdir(domain_path):
            example_path = os.path.join(domain_path, example_id)
            if not os.path.isdir(example_path):
                continue
            if "result.txt" in os.listdir(example_path):
                try:
                    with open(
                        os.path.join(example_path, "result.txt"),
                        "r",
                        encoding="utf-8",
                    ) as result_file:
                        all_result.append(float(result_file.read()))
                except Exception:
                    all_result.append(0.0)

    if not all_result:
        print("New experiment, no result yet.")
        return None

    print("Current Success Rate:", sum(all_result) / len(all_result) * 100, "%")
    return all_result


def format_remaining_tasks(test_file_list: Dict[str, list]) -> str:
    return "".join(f"{domain}: {len(example_ids)}\n" for domain, example_ids in test_file_list.items())
