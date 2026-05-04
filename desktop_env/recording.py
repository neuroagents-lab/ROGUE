from __future__ import annotations

import argparse
import importlib
import json
import logging
import os
import re
import shlex
import shutil
import signal
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, TYPE_CHECKING

import requests
from Xlib import display
from flask import abort, jsonify, request, send_file

if TYPE_CHECKING:
    from flask import Flask


logger = logging.getLogger("desktopenv.recording")

FULL_RECORDING_MODE = "full"
PER_STEP_RECORDING_MODE = "per-step"
DEFAULT_RECORDING_MODE = FULL_RECORDING_MODE
RECORDING_MODE_CHOICES = (FULL_RECORDING_MODE, PER_STEP_RECORDING_MODE)
RECORDING_FILENAME = "recording.mp4"

REMOTE_RECORDING_ROOT = Path("/tmp/osworld_recordings")
REMOTE_CLIPS_DIR = REMOTE_RECORDING_ROOT / "clips"
REMOTE_FULL_RECORDING_PATH = REMOTE_RECORDING_ROOT / "full_recording.mp4"
REMOTE_FINAL_RECORDING_PATH = REMOTE_RECORDING_ROOT / RECORDING_FILENAME
REMOTE_CONCAT_MANIFEST_PATH = REMOTE_RECORDING_ROOT / "concat_manifest.txt"

SPECIAL_ACTIONS = {"WAIT", "FAIL", "DONE"}


def normalize_recording_mode(recording_mode: Optional[str]) -> str:
    if recording_mode in RECORDING_MODE_CHOICES:
        return recording_mode
    return DEFAULT_RECORDING_MODE


def add_recording_arguments(parser: argparse.ArgumentParser) -> None:
    recording_group = parser.add_mutually_exclusive_group()
    recording_group.add_argument(
        "--full-recording",
        dest="recording_mode",
        action="store_const",
        const=FULL_RECORDING_MODE,
        help="Record the full episode as one QuickTime-compatible MP4.",
    )
    recording_group.add_argument(
        "--per-step-recording",
        dest="recording_mode",
        action="store_const",
        const=PER_STEP_RECORDING_MODE,
        help=(
            "Record a short QuickTime-compatible clip around each step and "
            "stitch the clips together into recording.mp4."
        ),
    )
    parser.set_defaults(recording_mode=DEFAULT_RECORDING_MODE)
    parser.add_argument(
        "--quicktime-compatible-recording",
        "--quicktime_compatible_recording",
        dest="recording_mode",
        action="store_const",
        const=FULL_RECORDING_MODE,
        help=argparse.SUPPRESS,
    )


def recording_output_path(example_result_dir: str) -> str:
    return os.path.join(example_result_dir, RECORDING_FILENAME)


def start_episode_recording(env: Any, args: argparse.Namespace) -> None:
    if not hasattr(env, "controller") or env.controller is None:
        return
    env.controller.start_recording(
        recording_mode=normalize_recording_mode(
            getattr(args, "recording_mode", DEFAULT_RECORDING_MODE)
        )
    )


def finish_episode_recording(env: Any, example_result_dir: str) -> None:
    if not hasattr(env, "controller") or env.controller is None:
        return
    env.controller.end_recording(recording_output_path(example_result_dir))


def end_recording_if_possible(env: Any, recording_path: str, run_logger: logging.Logger) -> None:
    if not hasattr(env, "controller") or env.controller is None:
        return
    try:
        env.controller.end_recording(recording_path)
    except Exception as exc:
        run_logger.error("Failed to end recording: %s", exc)


def should_record_step_clip(action: Any) -> bool:
    if isinstance(action, str):
        return action not in SPECIAL_ACTIONS
    if isinstance(action, dict):
        return action.get("action_type") not in SPECIAL_ACTIONS
    return True


def clip_name_for_step(step_num: int) -> str:
    return f"step_{step_num:04d}.mp4"


def _write_response_file(response: requests.Response, dest: str) -> None:
    dest_dir = os.path.dirname(dest)
    if dest_dir:
        os.makedirs(dest_dir, exist_ok=True)
    with open(dest, "wb") as handle:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                handle.write(chunk)


def _post_recording_request(
    controller: Any,
    endpoint: str,
    *,
    payload: Optional[dict[str, Any]] = None,
    timeout: int = 30,
) -> Optional[requests.Response]:
    url = controller.http_server + endpoint
    for _ in range(controller.retry_times):
        try:
            response = requests.post(url, json=payload or {}, timeout=timeout)
            return response
        except Exception as exc:
            logger.error("Recording request to %s failed: %s", endpoint, exc)
            logger.info("Retrying recording request.")
            time.sleep(controller.retry_interval)
    return None


@dataclass
class RecordingClientState:
    mode: str = DEFAULT_RECORDING_MODE
    clip_names: list[str] = field(default_factory=list)
    active_clip_name: Optional[str] = None
    local_clip_dir: Optional[Path] = None
    locally_downloaded_clip_paths: list[Path] = field(default_factory=list)
    remote_compose_available: bool = True


def _reset_local_clip_state(state: RecordingClientState) -> None:
    if state.local_clip_dir is not None:
        shutil.rmtree(state.local_clip_dir, ignore_errors=True)
    state.local_clip_dir = None
    state.locally_downloaded_clip_paths.clear()


def _looks_like_video_response(response: requests.Response) -> bool:
    content_type = (response.headers.get("Content-Type") or "").lower()
    if "video/" in content_type or "application/octet-stream" in content_type:
        return True
    content_disposition = (response.headers.get("Content-Disposition") or "").lower()
    if ".mp4" in content_disposition:
        return True
    return response.content.startswith(b"\x00\x00\x00")


def _compose_local_recording(clip_paths: list[Path], dest: str) -> None:
    dest_path = Path(dest)
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    manifest_dir = clip_paths[0].parent
    manifest_path = manifest_dir / "concat_manifest.txt"
    manifest_path.write_text(
        "".join(f"file '{clip_path.resolve().as_posix()}'\n" for clip_path in clip_paths),
        encoding="utf-8",
    )

    command = [
        _host_ffmpeg_executable() or "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(manifest_path),
        "-c",
        "copy",
        "-movflags",
        "+faststart",
        str(dest_path),
    ]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Failed to compose local per-step recording. ffmpeg stderr: {result.stderr}")
    if not dest_path.exists() or dest_path.stat().st_size <= 0:
        raise RuntimeError("Local per-step recording composition produced no output file.")


def _host_ffmpeg_executable() -> Optional[str]:
    executable = shutil.which("ffmpeg")
    if executable is not None:
        return executable

    try:
        imageio_ffmpeg = importlib.import_module("imageio_ffmpeg")
    except ModuleNotFoundError:
        return None

    try:
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def _upload_file_to_remote(controller: Any, local_path: Path, remote_path: str) -> None:
    url = controller.http_server + "/setup/upload"
    for _ in range(controller.retry_times):
        try:
            with local_path.open("rb") as handle:
                response = requests.post(
                    url,
                    data={"file_path": remote_path},
                    files={"file_data": (local_path.name, handle)},
                    timeout=600,
                )
            if response.status_code == 200:
                return
            logger.error(
                "Failed to upload %s to %s. Status code: %s Response: %s",
                local_path,
                remote_path,
                response.status_code,
                response.text,
            )
        except Exception as exc:
            logger.error("Failed to upload %s to remote VM: %s", local_path, exc)
        logger.info("Retrying remote upload.")
        time.sleep(controller.retry_interval)
    raise RuntimeError(f"Failed to upload {local_path} to remote path {remote_path}")


def _compose_remote_recording_from_local_clips(
    controller: Any,
    clip_paths: list[Path],
    dest: str,
) -> None:
    remote_root = "/tmp/osworld_uploaded_recordings"
    remote_manifest = f"{remote_root}/concat_manifest.txt"
    remote_output = f"{remote_root}/{RECORDING_FILENAME}"

    manifest_lines: list[str] = []
    for clip_path in clip_paths:
        remote_clip_path = f"{remote_root}/{clip_path.name}"
        _upload_file_to_remote(controller, clip_path, remote_clip_path)
        manifest_lines.append(f"file '{remote_clip_path}'")

    manifest_text = "\n".join(manifest_lines) + "\n"
    manifest_local_path = clip_paths[0].parent / "concat_manifest_remote.txt"
    manifest_local_path.write_text(manifest_text, encoding="utf-8")
    _upload_file_to_remote(controller, manifest_local_path, remote_manifest)

    script = "\n".join(
        [
            f"mkdir -p {shlex.quote(remote_root)}",
            "ffmpeg -y "
            f"-f concat -safe 0 -i {shlex.quote(remote_manifest)} "
            "-c copy -movflags +faststart "
            f"{shlex.quote(remote_output)}",
        ]
    )
    result = controller.run_bash_script(script, timeout=180)
    if not result or result.get("returncode") != 0:
        raise RuntimeError(
            "Failed to compose per-step recording on the remote VM. "
            f"Result: {result}"
        )

    remote_bytes = controller.get_file(remote_output)
    if not remote_bytes:
        raise RuntimeError("Remote per-step recording composition produced no downloadable output.")

    dest_path = Path(dest)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_bytes(remote_bytes)


def start_controller_recording(controller: Any, *, recording_mode: str) -> None:
    state: RecordingClientState = controller.recording_state
    state.mode = normalize_recording_mode(recording_mode)
    state.clip_names.clear()
    state.active_clip_name = None
    state.remote_compose_available = True
    _reset_local_clip_state(state)

    if state.mode == FULL_RECORDING_MODE:
        response = _post_recording_request(
            controller,
            "/start_recording",
            payload={"profile": FULL_RECORDING_MODE, "verify_startup": True},
            timeout=15,
        )
        if response is None or response.status_code != 200:
            status_code = getattr(response, "status_code", "unknown")
            logger.error("Failed to start full recording. Status code: %s", status_code)
        return

    state.local_clip_dir = Path(tempfile.mkdtemp(prefix="osworld_per_step_recording_"))
    response = _post_recording_request(
        controller,
        "/reset_recording_session",
        timeout=15,
    )
    if response is not None and response.status_code == 404:
        state.remote_compose_available = False
        logger.info(
            "Remote server does not expose /reset_recording_session; "
            "falling back to local per-step clip composition."
        )
        return
    if response is None or response.status_code != 200:
        status_code = getattr(response, "status_code", "unknown")
        logger.error("Failed to initialize per-step recording. Status code: %s", status_code)


def begin_controller_step_recording(controller: Any, *, step_num: int, action: Any) -> None:
    state: RecordingClientState = controller.recording_state
    if state.mode != PER_STEP_RECORDING_MODE or not should_record_step_clip(action):
        return
    if state.active_clip_name is not None:
        logger.warning(
            "Per-step recording already active for clip %s; skipping nested start.",
            state.active_clip_name,
        )
        return

    clip_name = clip_name_for_step(step_num)
    response = _post_recording_request(
        controller,
        "/start_recording",
        payload={
            "profile": PER_STEP_RECORDING_MODE,
            "clip_name": clip_name,
            "verify_startup": False,
        },
        timeout=15,
    )
    if response is None or response.status_code != 200:
        status_code = getattr(response, "status_code", "unknown")
        logger.error(
            "Failed to start per-step recording clip %s. Status code: %s",
            clip_name,
            status_code,
        )
        return
    state.active_clip_name = clip_name


def end_controller_step_recording(controller: Any) -> None:
    state: RecordingClientState = controller.recording_state
    if state.mode != PER_STEP_RECORDING_MODE or state.active_clip_name is None:
        return

    clip_name = state.active_clip_name
    response = _post_recording_request(
        controller,
        "/end_recording",
        payload={"download": False},
        timeout=30,
    )
    state.active_clip_name = None
    if response is None or response.status_code != 200:
        status_code = getattr(response, "status_code", "unknown")
        logger.error(
            "Failed to stop per-step recording clip %s. Status code: %s",
            clip_name,
            status_code,
        )
        return

    if state.local_clip_dir is not None and _looks_like_video_response(response):
        local_clip_path = state.local_clip_dir / clip_name
        _write_response_file(response, str(local_clip_path))
        state.locally_downloaded_clip_paths.append(local_clip_path)

    state.clip_names.append(clip_name)


def finalize_controller_recording(controller: Any, dest: str) -> None:
    state: RecordingClientState = controller.recording_state

    if state.mode == PER_STEP_RECORDING_MODE:
        if state.active_clip_name is not None:
            end_controller_step_recording(controller)

        if not state.clip_names:
            logger.warning("No per-step recording clips were captured; skipping final video.")
            return

        if state.locally_downloaded_clip_paths:
            try:
                if _host_ffmpeg_executable() is not None:
                    _compose_local_recording(state.locally_downloaded_clip_paths, dest)
                else:
                    logger.info(
                        "Host ffmpeg is unavailable; composing per-step recording on the remote VM."
                    )
                    _compose_remote_recording_from_local_clips(
                        controller, state.locally_downloaded_clip_paths, dest
                    )
            except Exception as exc:
                logger.error("Failed to finalize locally downloaded per-step clips: %s", exc)
            finally:
                _reset_local_clip_state(state)
                state.clip_names.clear()
                state.active_clip_name = None
            return

        if not state.remote_compose_available:
            logger.warning(
                "Per-step recording captured clip metadata but no clip files were downloaded, "
                "and the remote server does not expose /compose_recording."
            )
            _reset_local_clip_state(state)
            state.clip_names.clear()
            state.active_clip_name = None
            return

        response = _post_recording_request(
            controller,
            "/compose_recording",
            payload={"clip_names": state.clip_names},
            timeout=180,
        )
        if response is not None and response.status_code == 404:
            logger.warning(
                "Remote server does not expose /compose_recording and no local per-step "
                "clips were available to compose."
            )
            _reset_local_clip_state(state)
            state.clip_names.clear()
            state.active_clip_name = None
            return
        if response is None or response.status_code != 200:
            status_code = getattr(response, "status_code", "unknown")
            logger.error(
                "Failed to compose per-step recording. Status code: %s",
                status_code,
            )
            _reset_local_clip_state(state)
            return
        _write_response_file(response, dest)
        _post_recording_request(controller, "/reset_recording_session", timeout=15)
        _reset_local_clip_state(state)
        state.clip_names.clear()
        state.active_clip_name = None
        return

    response = _post_recording_request(
        controller,
        "/end_recording",
        payload={"download": True},
        timeout=180,
    )
    if response is None or response.status_code != 200:
        status_code = getattr(response, "status_code", "unknown")
        logger.error("Failed to stop full recording. Status code: %s", status_code)
        return
    _write_response_file(response, dest)
    _reset_local_clip_state(state)
    state.clip_names.clear()
    state.active_clip_name = None


@dataclass(frozen=True)
class CaptureProfile:
    input_fps: int
    output_fps: int
    video_filter: str
    crf: int
    preset: str


CAPTURE_PROFILES: dict[str, CaptureProfile] = {
    FULL_RECORDING_MODE: CaptureProfile(
        input_fps=30,
        output_fps=30,
        video_filter="scale=trunc(iw/2)*2:trunc(ih/2)*2",
        crf=28,
        preset="veryfast",
    ),
    PER_STEP_RECORDING_MODE: CaptureProfile(
        input_fps=12,
        output_fps=12,
        video_filter=(
            "scale=960:540:force_original_aspect_ratio=decrease,"
            "pad=960:540:(ow-iw)/2:(oh-ih)/2"
        ),
        crf=32,
        preset="veryfast",
    ),
}


class RecordingService:
    def __init__(self, *, service_logger: logging.Logger):
        self.logger = service_logger
        self.recording_process: Optional[subprocess.Popen[str]] = None
        self.current_output_path: Optional[Path] = None

    def _ensure_root(self) -> None:
        REMOTE_CLIPS_DIR.mkdir(parents=True, exist_ok=True)

    def reset_session(self) -> None:
        if self.recording_process and self.recording_process.poll() is None:
            raise RuntimeError("Cannot reset recording session while a recording is in progress.")
        shutil.rmtree(REMOTE_RECORDING_ROOT, ignore_errors=True)
        self._ensure_root()
        self.current_output_path = None

    def _output_path_for_profile(self, profile: str, clip_name: Optional[str]) -> Path:
        if profile == FULL_RECORDING_MODE:
            return REMOTE_FULL_RECORDING_PATH
        if not clip_name or not re.fullmatch(r"[A-Za-z0-9_.-]+\.mp4", clip_name):
            raise ValueError("Per-step recording requires a valid clip_name ending in .mp4.")
        return REMOTE_CLIPS_DIR / clip_name

    def _capture_dimensions(self) -> tuple[int, int]:
        d = display.Display()
        try:
            screen = d.screen()
            return screen.width_in_pixels, screen.height_in_pixels
        finally:
            d.close()

    def _ffmpeg_command(self, *, profile: str, output_path: Path) -> list[str]:
        screen_width, screen_height = self._capture_dimensions()
        capture_profile = CAPTURE_PROFILES[profile]
        return [
            "ffmpeg",
            "-y",
            "-f",
            "x11grab",
            "-draw_mouse",
            "1",
            "-framerate",
            str(capture_profile.input_fps),
            "-s",
            f"{screen_width}x{screen_height}",
            "-i",
            ":0.0",
            "-vf",
            capture_profile.video_filter,
            "-c:v",
            "libx264",
            "-preset",
            capture_profile.preset,
            "-crf",
            str(capture_profile.crf),
            "-pix_fmt",
            "yuv420p",
            "-profile:v",
            "baseline",
            "-level",
            "3.0",
            "-movflags",
            "+faststart",
            "-r",
            str(capture_profile.output_fps),
            str(output_path),
        ]

    def start_recording(
        self,
        *,
        profile: str,
        clip_name: Optional[str],
        verify_startup: bool,
    ):
        if self.recording_process and self.recording_process.poll() is None:
            return jsonify(
                {"status": "error", "message": "Recording is already in progress."}
            ), 400

        self._ensure_root()
        output_path = self._output_path_for_profile(profile, clip_name)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            output_path.unlink(missing_ok=True)
        except OSError as exc:
            self.logger.error("Failed to remove stale recording file %s: %s", output_path, exc)
            return jsonify(
                {"status": "error", "message": f"Failed to remove stale recording file: {exc}"}
            ), 500

        command = self._ffmpeg_command(profile=profile, output_path=output_path)
        self.recording_process = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.current_output_path = output_path

        if not verify_startup:
            return jsonify({"status": "success", "message": "Started recording successfully."})

        try:
            self.recording_process.wait(timeout=2)
            error_output = (
                self.recording_process.stderr.read() if self.recording_process.stderr else ""
            )
            self.recording_process = None
            self.current_output_path = None
            return jsonify(
                {
                    "status": "error",
                    "message": (
                        "Failed to start recording. ffmpeg terminated unexpectedly. "
                        f"Error: {error_output}"
                    ),
                }
            ), 500
        except subprocess.TimeoutExpired:
            return jsonify({"status": "success", "message": "Started recording successfully."})

    def stop_recording(self, *, download: bool):
        if not self.recording_process or self.recording_process.poll() is not None:
            self.recording_process = None
            self.current_output_path = None
            return jsonify(
                {"status": "error", "message": "No recording in progress to stop."}
            ), 400

        error_output = ""
        output_path = self.current_output_path
        try:
            self.recording_process.send_signal(signal.SIGINT)
            _, error_output = self.recording_process.communicate(timeout=15)
        except subprocess.TimeoutExpired:
            self.logger.error("ffmpeg did not respond to SIGINT, killing the process.")
            self.recording_process.kill()
            _, error_output = self.recording_process.communicate()
            self.recording_process = None
            self.current_output_path = None
            return jsonify(
                {
                    "status": "error",
                    "message": (
                        "Recording process was unresponsive and had to be killed. "
                        f"Stderr: {error_output}"
                    ),
                }
            ), 500

        self.recording_process = None
        self.current_output_path = None

        if not output_path or not output_path.exists() or output_path.stat().st_size <= 0:
            self.logger.error(
                "Recording failed. The output file is missing or empty. ffmpeg stderr: %s",
                error_output,
            )
            return abort(
                500,
                description=(
                    "Recording failed. The output file is missing or empty. "
                    f"ffmpeg stderr: {error_output}"
                ),
            )

        if download:
            return send_file(output_path, as_attachment=True)
        return jsonify({"status": "success", "path": str(output_path)})

    def compose_recording(self, *, clip_names: list[str]):
        if self.recording_process and self.recording_process.poll() is None:
            return jsonify(
                {
                    "status": "error",
                    "message": "Cannot compose recording while a clip is still being captured.",
                }
            ), 400

        if not clip_names:
            return jsonify(
                {"status": "error", "message": "No per-step clips were provided."}
            ), 400

        clip_paths = []
        for clip_name in clip_names:
            if not re.fullmatch(r"[A-Za-z0-9_.-]+\.mp4", clip_name):
                return jsonify(
                    {"status": "error", "message": f"Invalid clip name: {clip_name}"}
                ), 400
            clip_path = REMOTE_CLIPS_DIR / clip_name
            if not clip_path.exists():
                return jsonify(
                    {
                        "status": "error",
                        "message": f"Per-step clip does not exist: {clip_name}",
                    }
                ), 400
            clip_paths.append(clip_path)

        self._ensure_root()
        REMOTE_CONCAT_MANIFEST_PATH.write_text(
            "".join(f"file '{clip_path}'\n" for clip_path in clip_paths),
            encoding="utf-8",
        )
        REMOTE_FINAL_RECORDING_PATH.unlink(missing_ok=True)

        command = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(REMOTE_CONCAT_MANIFEST_PATH),
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            str(REMOTE_FINAL_RECORDING_PATH),
        ]
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            self.logger.error("Failed to compose per-step recording: %s", result.stderr)
            return jsonify(
                {
                    "status": "error",
                    "message": (
                        "Failed to compose per-step recording. "
                        f"ffmpeg stderr: {result.stderr}"
                    ),
                }
            ), 500

        if not REMOTE_FINAL_RECORDING_PATH.exists() or REMOTE_FINAL_RECORDING_PATH.stat().st_size <= 0:
            return jsonify(
                {
                    "status": "error",
                    "message": "Per-step recording composition produced no output file.",
                }
            ), 500

        return send_file(REMOTE_FINAL_RECORDING_PATH, as_attachment=True)


def register_recording_routes(app: Flask) -> RecordingService:
    service = RecordingService(service_logger=app.logger)

    @app.route("/reset_recording_session", methods=["POST"])
    def reset_recording_session():
        try:
            service.reset_session()
        except RuntimeError as exc:
            return jsonify({"status": "error", "message": str(exc)}), 400
        return jsonify({"status": "success", "message": "Recording session reset."})

    @app.route("/start_recording", methods=["POST"])
    def start_recording():
        data = request.get_json(silent=True) or {}
        profile = normalize_recording_mode(data.get("profile"))
        clip_name = data.get("clip_name")
        verify_startup = bool(data.get("verify_startup", profile == FULL_RECORDING_MODE))
        return service.start_recording(
            profile=profile,
            clip_name=clip_name,
            verify_startup=verify_startup,
        )

    @app.route("/end_recording", methods=["POST"])
    def end_recording():
        data = request.get_json(silent=True) or {}
        return service.stop_recording(download=bool(data.get("download", True)))

    @app.route("/compose_recording", methods=["POST"])
    def compose_recording():
        data = request.get_json(silent=True) or {}
        clip_names = data.get("clip_names") or []
        if not isinstance(clip_names, list):
            return jsonify(
                {"status": "error", "message": "clip_names must be a list."}
            ), 400
        return service.compose_recording(clip_names=clip_names)

    return service
