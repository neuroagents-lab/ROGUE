from __future__ import annotations

import os
from typing import Any, Callable, Optional, Tuple


def _existing_path(
    configured_path: str,
    *,
    repo_root: str,
    settings_file: Optional[str] = None,
    cwd: Optional[str] = None,
) -> Optional[str]:
    if not isinstance(configured_path, str) or not configured_path.strip():
        return None

    configured_path = os.path.expanduser(configured_path)
    if os.path.isabs(configured_path):
        candidates = [configured_path]
    else:
        candidates = [
            os.path.join(cwd or os.getcwd(), configured_path),
            os.path.join(repo_root, configured_path),
        ]
        if settings_file:
            candidates.append(
                os.path.join(os.path.dirname(settings_file), configured_path)
            )

    for candidate in candidates:
        normalized = os.path.abspath(candidate)
        try:
            if os.path.isfile(normalized) and os.path.getsize(normalized) > 0:
                return normalized
        except OSError:
            continue
    return None


def load_google_drive_auth_if_available(
    settings_file: str,
    *,
    google_auth_factory: Callable[[str], Any],
    repo_root: str,
    cwd: Optional[str] = None,
) -> Tuple[Optional[Any], str]:
    """Load non-interactive PyDrive auth, or explain why it is unavailable."""
    resolved_settings = _existing_path(
        settings_file,
        repo_root=repo_root,
        cwd=cwd,
    )
    if resolved_settings is None:
        return None, f"settings file is missing or empty: {settings_file}"

    try:
        auth = google_auth_factory(resolved_settings)
    except Exception as exc:
        return None, f"settings file is invalid: {exc}"

    settings = getattr(auth, "settings", None)
    if not isinstance(settings, dict):
        return None, "settings file did not produce a settings mapping"

    if settings.get("client_config_backend", "file") == "file":
        configured_client_file = settings.get(
            "client_config_file", "client_secrets.json"
        )
        resolved_client_file = _existing_path(
            configured_client_file,
            repo_root=repo_root,
            settings_file=resolved_settings,
            cwd=cwd,
        )
        if resolved_client_file is None:
            return (
                None,
                "OAuth client configuration is missing or empty: "
                f"{configured_client_file}",
            )
        settings["client_config_file"] = resolved_client_file

    if not settings.get("save_credentials"):
        return None, "saved OAuth credentials are not enabled"
    if settings.get("save_credentials_backend") != "file":
        return None, "saved OAuth credentials must use the file backend"

    configured_credentials_file = settings.get("save_credentials_file")
    resolved_credentials_file = _existing_path(
        configured_credentials_file,
        repo_root=repo_root,
        settings_file=resolved_settings,
        cwd=cwd,
    )
    if resolved_credentials_file is None:
        return (
            None,
            "saved OAuth credentials are missing or empty: "
            f"{configured_credentials_file}",
        )
    settings["save_credentials_file"] = resolved_credentials_file

    try:
        auth.LoadClientConfig()
        auth.LoadCredentials()
    except Exception as exc:
        return None, f"OAuth credentials could not be loaded: {exc}"

    credentials = getattr(auth, "credentials", None)
    if credentials is None:
        return None, "saved OAuth credentials contain no authorization token"
    if getattr(credentials, "invalid", False):
        return None, "saved OAuth credentials are marked invalid"

    try:
        access_token_expired = bool(auth.access_token_expired)
    except Exception as exc:
        return None, f"saved OAuth credentials could not be inspected: {exc}"

    if access_token_expired and not getattr(credentials, "refresh_token", None):
        return None, "saved OAuth credentials are expired and have no refresh token"

    return auth, ""
