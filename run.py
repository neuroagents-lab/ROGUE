"""Script to run end-to-end evaluation on the benchmark.
Utils and basic architecture credit to https://github.com/web-arena-x/webarena/blob/main/run.py.
"""

import argparse
import datetime
import json
import logging
import os

from tqdm import tqdm

import lib_run_single
from task_utils import normalize_task_config, result_model_name
from lib_run_litellm import (
    build_desktop_env,
    build_parser,
    build_prompt_agent,
    configure_root_logger,
    end_recording_if_possible,
    format_remaining_tasks,
    get_result,
    get_unfinished,
    load_test_all_meta,
    save_args,
)


logger = logging.getLogger("desktopenv.experiment")


def config() -> argparse.Namespace:
    parser = build_parser(
        default_provider="vmware",
        default_observation_type="a11y_tree",
        include_parallelism=False,
        include_log_level=False,
    )
    return parser.parse_args()


def test(args: argparse.Namespace, test_all_meta: dict) -> None:
    scores = []
    logger.info("Args: %s", args)

    agent = build_prompt_agent(args)
    env = build_desktop_env(args, action_space=agent.action_space)

    for domain in tqdm(test_all_meta, desc="Domain"):
        for example_id in tqdm(test_all_meta[domain], desc="Example", leave=False):
            config_file = os.path.join(
                args.test_config_base_dir, f"examples/{domain}/{example_id}.json"
            )
            with open(config_file, "r", encoding="utf-8") as f:
                example = normalize_task_config(json.load(f))

            logger.info("[Domain]: %s", domain)
            logger.info("[Example ID]: %s", example_id)
            logger.info("[Instruction]: %s", example["instruction"])

            example_result_dir = os.path.join(
                args.result_dir,
                args.action_space,
                args.observation_type,
                result_model_name(args.model),
                domain,
                example_id,
            )
            os.makedirs(example_result_dir, exist_ok=True)

            try:
                lib_run_single.run_single_example(
                    agent,
                    env,
                    example,
                    args.max_steps,
                    example["instruction"],
                    args,
                    example_result_dir,
                    scores,
                )
            except Exception as exc:
                logger.error("Exception in %s/%s: %s", domain, example_id, exc)
                end_recording_if_possible(
                    env,
                    os.path.join(example_result_dir, "recording.mp4"),
                    logger,
                )
                with open(os.path.join(example_result_dir, "traj.jsonl"), "a", encoding="utf-8") as f:
                    f.write(
                        json.dumps(
                            {"Error": f"Time limit exceeded in {domain}/{example_id}"}
                        )
                    )
                    f.write("\n")

    env.close()
    logger.info("Average score: %s", sum(scores) / len(scores) if scores else 0)


if __name__ == "__main__":
    os.environ["TOKENIZERS_PARALLELISM"] = "false"

    args = config()
    args.log_timestamp = datetime.datetime.now().strftime("%Y%m%d@%H%M%S")
    configure_root_logger(
        stdout_level="INFO",
        log_timestamp=args.log_timestamp,
        include_sdebug=True,
    )

    save_args(args)
    test_all_meta = load_test_all_meta(args)
    test_file_list = get_unfinished(
        args.action_space,
        args.model,
        args.observation_type,
        args.result_dir,
        test_all_meta,
    )
    logger.info("Left tasks:\n%s", format_remaining_tasks(test_file_list))

    get_result(
        args.action_space,
        args.model,
        args.observation_type,
        args.result_dir,
    )
    test(args, test_file_list)
