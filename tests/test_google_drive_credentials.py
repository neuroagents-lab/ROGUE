import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from desktop_env.evaluators.getters import chrome as chrome_getters
from desktop_env.google_drive import load_google_drive_auth_if_available
from evaluation_outcome import EvaluationSkipped


class FakeCredentials:
    def __init__(
        self,
        *,
        invalid=False,
        refresh_token="refresh-token",
    ):
        self.invalid = invalid
        self.refresh_token = refresh_token


class FakeGoogleAuth:
    def __init__(
        self,
        settings,
        *,
        credentials=None,
        access_token_expired=False,
    ):
        self.settings = settings
        self.credentials = credentials
        self.access_token_expired = access_token_expired
        self.loaded_client_config = False
        self.loaded_credentials = False

    def LoadClientConfig(self):
        self.loaded_client_config = True

    def LoadCredentials(self):
        self.loaded_credentials = True


class FakeRemoteFile(dict):
    def __init__(self):
        super().__init__(id="file-id", mimeType="application/octet-stream")
        self.downloads = []

    def GetContentFile(self, path, mimetype):
        self.downloads.append((path, mimetype))
        Path(path).write_text("downloaded", encoding="utf-8")


class FakeFileList:
    def __init__(self, remote_file):
        self.remote_file = remote_file

    def GetList(self):
        return [self.remote_file]


class FakeDrive:
    def __init__(self, remote_file):
        self.remote_file = remote_file
        self.queries = []

    def ListFile(self, query):
        self.queries.append(query)
        return FakeFileList(self.remote_file)


class TestGoogleDriveCredentials(unittest.TestCase):
    def _write_file(self, path, content="present"):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def test_missing_settings_skips_before_constructing_auth(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            auth, reason = load_google_drive_auth_if_available(
                "missing.yml",
                google_auth_factory=lambda path: self.fail(
                    f"unexpected auth construction for {path}"
                ),
                repo_root=tmpdir,
                cwd=tmpdir,
            )

        self.assertIsNone(auth)
        self.assertIn("settings file is missing", reason)

    def test_missing_saved_credentials_skips(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            settings_file = root / "settings.yml"
            client_file = root / "client_secrets.json"
            self._write_file(settings_file)
            self._write_file(client_file)
            fake_auth = FakeGoogleAuth(
                {
                    "client_config_backend": "file",
                    "client_config_file": str(client_file),
                    "save_credentials": True,
                    "save_credentials_backend": "file",
                    "save_credentials_file": str(root / "credentials.json"),
                },
                credentials=FakeCredentials(),
            )

            auth, reason = load_google_drive_auth_if_available(
                str(settings_file),
                google_auth_factory=lambda path: fake_auth,
                repo_root=tmpdir,
                cwd=tmpdir,
            )

        self.assertIsNone(auth)
        self.assertIn("saved OAuth credentials are missing", reason)
        self.assertFalse(fake_auth.loaded_client_config)
        self.assertFalse(fake_auth.loaded_credentials)

    def test_complete_credentials_return_loaded_auth(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            settings_file = root / "settings.yml"
            client_file = root / "client_secrets.json"
            credentials_file = root / "credentials.json"
            self._write_file(settings_file)
            self._write_file(client_file)
            self._write_file(credentials_file)
            fake_auth = FakeGoogleAuth(
                {
                    "client_config_backend": "file",
                    "client_config_file": str(client_file),
                    "save_credentials": True,
                    "save_credentials_backend": "file",
                    "save_credentials_file": str(credentials_file),
                },
                credentials=FakeCredentials(),
            )

            auth, reason = load_google_drive_auth_if_available(
                str(settings_file),
                google_auth_factory=lambda path: fake_auth,
                repo_root=tmpdir,
                cwd=tmpdir,
            )

        self.assertIs(auth, fake_auth)
        self.assertEqual(reason, "")
        self.assertTrue(fake_auth.loaded_client_config)
        self.assertTrue(fake_auth.loaded_credentials)
        self.assertEqual(
            fake_auth.settings["client_config_file"],
            str(client_file),
        )
        self.assertEqual(
            fake_auth.settings["save_credentials_file"],
            str(credentials_file),
        )

    def test_expired_credentials_without_refresh_token_skip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            settings_file = root / "settings.yml"
            client_file = root / "client_secrets.json"
            credentials_file = root / "credentials.json"
            for path in (settings_file, client_file, credentials_file):
                self._write_file(path)
            fake_auth = FakeGoogleAuth(
                {
                    "client_config_backend": "file",
                    "client_config_file": str(client_file),
                    "save_credentials": True,
                    "save_credentials_backend": "file",
                    "save_credentials_file": str(credentials_file),
                },
                credentials=FakeCredentials(refresh_token=None),
                access_token_expired=True,
            )

            auth, reason = load_google_drive_auth_if_available(
                str(settings_file),
                google_auth_factory=lambda path: fake_auth,
                repo_root=tmpdir,
                cwd=tmpdir,
            )

        self.assertIsNone(auth)
        self.assertIn("expired and have no refresh token", reason)

    def test_evaluator_skips_before_constructing_drive_when_credentials_are_missing(self):
        env = SimpleNamespace(cache_dir="/tmp")
        config = {
            "settings_file": "missing-settings.yml",
            "skip_if_credentials_missing": True,
            "query": ["title = 'missing'"],
            "dest": "missing.txt",
        }

        with (
            mock.patch.object(
                chrome_getters,
                "load_google_drive_auth_if_available",
                return_value=(None, "saved OAuth credentials are missing"),
            ),
            mock.patch.object(chrome_getters, "GoogleDrive") as google_drive,
        ):
            with self.assertRaisesRegex(
                EvaluationSkipped,
                "saved OAuth credentials are missing",
            ):
                chrome_getters.get_googledrive_file(env, config)

        google_drive.assert_not_called()

    def test_evaluator_downloads_file_when_credentials_are_available(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env = SimpleNamespace(cache_dir=tmpdir)
            config = {
                "settings_file": "settings.yml",
                "skip_if_credentials_missing": True,
                "query": ["title = 'report'"],
                "dest": "report.txt",
            }
            fake_auth = object()
            remote_file = FakeRemoteFile()
            fake_drive = FakeDrive(remote_file)

            with (
                mock.patch.object(
                    chrome_getters,
                    "load_google_drive_auth_if_available",
                    return_value=(fake_auth, ""),
                ) as load_auth,
                mock.patch.object(
                    chrome_getters,
                    "GoogleDrive",
                    return_value=fake_drive,
                ) as google_drive,
            ):
                result = chrome_getters.get_googledrive_file(env, config)

        self.assertEqual(result, str(Path(tmpdir) / "report.txt"))
        load_auth.assert_called_once()
        google_drive.assert_called_once_with(fake_auth)
        self.assertEqual(len(fake_drive.queries), 1)
        self.assertEqual(
            remote_file.downloads,
            [(str(Path(tmpdir) / "report.txt"), "application/octet-stream")],
        )


if __name__ == "__main__":
    unittest.main()
