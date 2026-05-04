from __future__ import annotations

import argparse
import datetime
import json
import logging
import os
import signal
import sys
import time
from multiprocessing import Manager, Process, current_process
from typing import List

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

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


active_environments = []
processes = []
is_terminating = False
main_pid = None
logger = logging.getLogger("desktopenv.experiment")


if os.path.exists(".env"):
    from dotenv import load_dotenv

    load_dotenv()


def config() -> argparse.Namespace:
    parser = build_parser(
        default_provider="vmware",
        default_observation_type="a11y_tree",
        include_parallelism=True,
        include_log_level=True,
    )
    return parser.parse_args()


def distribute_tasks(test_all_meta: dict) -> List[tuple]:
    all_tasks = []
    for domain, examples in test_all_meta.items():
        for example_id in examples:
            all_tasks.append((domain, example_id))
    return all_tasks


def process_identity() -> str:
    return (
        f"pid={os.getpid()} "
        f"ppid={os.getppid()} "
        f"pgid={os.getpgid(0)} "
        f"sid={os.getsid(0)}"
    )


def worker_signal_handler(signum, frame):
    logger.info(
        "Worker received signal %s. %s. Exiting worker for cleanup...",
        signum,
        process_identity(),
    )
    raise SystemExit(128 + signum)


def run_env_tasks(task_queue, args: argparse.Namespace, shared_scores: list):
    configure_root_logger(
        stdout_level=args.log_level,
        log_timestamp=args.log_timestamp,
        include_sdebug=False,
    )
    signal.signal(signal.SIGINT, worker_signal_handler)
    signal.signal(signal.SIGTERM, worker_signal_handler)

    env = None
    try:
        env = build_desktop_env(args)
        agent = build_prompt_agent(args)

        logger.info(
            "Process %s started. %s",
            current_process().name,
            process_identity(),
        )
        while True:
            try:
                item = task_queue.get(timeout=5)
            except Exception:
                break

            domain, example_id = item
            try:
                config_file = os.path.join(
                    args.test_config_base_dir, f"examples/{domain}/{example_id}.json"
                )
                with open(config_file, "r", encoding="utf-8") as f:
                    example = normalize_task_config(json.load(f))

                logger.info("[%s][Domain]: %s", current_process().name, domain)
                logger.info("[%s][Example ID]: %s", current_process().name, example_id)
                logger.info(
                    "[%s][Instruction]: %s",
                    current_process().name,
                    example["instruction"],
                )

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
                        shared_scores,
                    )
                except Exception as exc:
                    import traceback

                    logger.error(
                        "Exception in %s %s/%s: %s",
                        current_process().name,
                        domain,
                        example_id,
                        exc,
                    )
                    logger.error(traceback.format_exc())
                    end_recording_if_possible(
                        env,
                        os.path.join(example_result_dir, "recording.mp4"),
                        logger,
                    )
                    with open(
                        os.path.join(example_result_dir, "traj.jsonl"),
                        "a",
                        encoding="utf-8",
                    ) as f:
                        f.write(json.dumps({"Error": f"{domain}/{example_id} - {exc}"}))
                        f.write("\n")
            except Exception as exc:
                import traceback

                logger.error("Task-level error in %s: %s", current_process().name, exc)
                logger.error(traceback.format_exc())
    except Exception as exc:
        import traceback

        logger.error("Process-level error in %s: %s", current_process().name, exc)
        logger.error(traceback.format_exc())
    finally:
        logger.info("%s cleaning up environment...", current_process().name)
        if env is not None:
            try:
                env.close()
                logger.info(
                    "%s environment closed successfully", current_process().name
                )
            except Exception as exc:
                logger.error(
                    "%s error during environment cleanup: %s",
                    current_process().name,
                    exc,
                )


def main_signal_handler(signum, frame):
    global is_terminating, active_environments, processes, main_pid

    if main_pid is not None and os.getpid() != main_pid:
        logger.info(
            "Non-main process received signal %s in main handler. %s",
            signum,
            process_identity(),
        )
        raise SystemExit(128 + signum)

    if is_terminating:
        return

    is_terminating = True
    logger.info(
        "Received signal %s in main process. Gracefully shutting down... %s",
        signum,
        process_identity(),
    )

    for env in active_environments:
        try:
            logger.info("Closing environment...")
            env.close()
            logger.info("Environment closed successfully")
        except Exception as exc:
            logger.error("Error closing environment: %s", exc)

    for process in processes:
        if process.is_alive():
            try:
                logger.info("Sending termination signal to process %s...", process.name)
                process.terminate()
            except Exception as exc:
                logger.error("Error sending termination signal to process: %s", exc)

    time.sleep(1)

    for process in processes:
        if process.is_alive():
            try:
                logger.info("Forcefully terminating process %s...", process.name)
                os.kill(process.pid, signal.SIGKILL)
            except Exception as exc:
                logger.error("Error forcefully terminating process: %s", exc)

    logger.info("Shutdown complete. Exiting.")
    sys.exit(0)


def test(args: argparse.Namespace, test_all_meta: dict) -> None:
    global processes

    logger.info("Args: %s", args)
    all_tasks = distribute_tasks(test_all_meta)
    logger.info("Total tasks: %s", len(all_tasks))

    with Manager() as manager:
        shared_scores = manager.list()
        task_queue = manager.Queue()
        for item in all_tasks:
            task_queue.put(item)

        processes = []
        for i in range(args.num_envs):
            process = Process(
                target=run_env_tasks,
                args=(task_queue, args, shared_scores),
                name=f"EnvProcess-{i + 1}",
            )
            process.daemon = True
            process.start()
            processes.append(process)
            logger.info("Started process %s with PID %s", process.name, process.pid)

        try:
            while True:
                if task_queue.empty():
                    if not any(process.is_alive() for process in processes):
                        logger.info("All tasks finished.")
                        break
                    time.sleep(1)
                    continue

                alive_count = 0
                for idx, process in enumerate(processes):
                    if not process.is_alive():
                        logger.warning("Process %s died, restarting...", process.name)
                        replacement = Process(
                            target=run_env_tasks,
                            args=(task_queue, args, shared_scores),
                            name=f"EnvProcess-Restart-{idx + 1}",
                        )
                        replacement.daemon = True
                        replacement.start()
                        processes[idx] = replacement
                        logger.info(
                            "Restarted process %s with PID %s",
                            replacement.name,
                            replacement.pid,
                        )
                    else:
                        alive_count += 1

                if alive_count == 0:
                    logger.error("All processes died, exiting.")
                    break
                time.sleep(5)

            for process in processes:
                process.join()
        except KeyboardInterrupt:
            logger.info(
                "Main process received KeyboardInterrupt. Initiating graceful shutdown..."
            )
            raise
        except Exception as exc:
            logger.error(
                "Unexpected error while waiting for processes: %s",
                exc,
                exc_info=True,
            )
            for process in processes:
                if process.is_alive():
                    try:
                        logger.info(
                            "Terminating process %s due to error...", process.name
                        )
                        process.terminate()
                    except Exception as term_exc:
                        logger.error(
                            "Error terminating process %s: %s",
                            process.name,
                            term_exc,
                        )
            raise

        scores = list(shared_scores)

    logger.info("Average score: %s", sum(scores) / len(scores) if scores else 0)


if __name__ == "__main__":
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    main_pid = os.getpid()

    args = config()
    args.log_timestamp = datetime.datetime.now().strftime("%Y%m%d@%H%M%S")
    configure_root_logger(
        stdout_level=args.log_level,
        log_timestamp=args.log_timestamp,
        include_sdebug=False,
    )

    logger.info("Main process starting. %s", process_identity())

    signal.signal(signal.SIGINT, main_signal_handler)
    signal.signal(signal.SIGTERM, main_signal_handler)

    try:
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
    except KeyboardInterrupt:
        logger.info("Main process received KeyboardInterrupt.")
    except Exception as exc:
        logger.error("Unexpected error in main process: %s", exc, exc_info=True)
        main_signal_handler(signal.SIGTERM, None)
    finally:
        logger.info("Main process final cleanup...")
        for env in active_environments:
            if env is not None:
                try:
                    logger.info("Closing environment in final cleanup...")
                    env.close()
                    logger.info("Environment closed successfully in final cleanup")
                except Exception as exc:
                    logger.error("Error during final environment cleanup: %s", exc)

        for process in processes:
            if process is not None and process.is_alive():
                try:
                    logger.info("Terminating process %s...", process.name)
                    process.terminate()
                except Exception as exc:
                    logger.error("Error terminating process: %s", exc)

        time.sleep(1)

        for process in processes:
            if process is not None and process.is_alive():
                try:
                    logger.info("Force killing process %s...", process.name)
                    os.kill(process.pid, signal.SIGKILL)
                    logger.info("Process %s force killed", process.name)
                except Exception as exc:
                    logger.error("Error force killing process: %s", exc)
