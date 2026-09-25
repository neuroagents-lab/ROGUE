import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.support import install_runner_import_stubs


install_runner_import_stubs()

from scripts import run_textonlybaselines as runner


class TestRestrictedaccessTextonlyResume(unittest.TestCase):
    def _setup_run(self, tmp_dir):
        root = Path(tmp_dir)
        args = runner.build_parser().parse_args([
            "--scenario", "restrictedaccess",
            "--test_config_base_dir", str(root / "configs"),
            "--result_dir", str(root / "results"),
        ])
        example_path = root / "configs" / "examples" / "restrictedaccess" / "task-one.json"
        example_path.parent.mkdir(parents=True)
        example_path.write_text(json.dumps({"id": "task-one", "instruction": "New prompt"}), encoding="utf-8")
        output_dir = runner.example_result_dir(args, "restrictedaccess", "task-one")
        output_dir.mkdir(parents=True)
        (output_dir / "response.json").write_text('{"status": "completed"}', encoding="utf-8")
        return args, example_path, output_dir

    def test_mismatched_or_missing_prompt_rejects_resume_without_writes(self):
        for saved_request in (None, {"messages": [{"role": "system", "content": "Old prompt"}]}):
            with self.subTest(saved_request=saved_request), tempfile.TemporaryDirectory() as tmp_dir:
                args, _, output_dir = self._setup_run(tmp_dir)
                if saved_request is not None:
                    (output_dir / "request.json").write_text(json.dumps(saved_request), encoding="utf-8")
                before = {path: path.read_bytes() for path in output_dir.iterdir()}
                with mock.patch.object(runner, "build_parser") as parser, \
                        mock.patch.object(runner, "run_single_example") as run_example, \
                        mock.patch.object(runner, "aggregate_model_results") as aggregate:
                    parser.return_value.parse_args.return_value = args
                    with self.assertRaisesRegex(ValueError, "fresh --result_dir"):
                        runner.main()
                run_example.assert_not_called()
                aggregate.assert_not_called()
                self.assertEqual(before, {path: path.read_bytes() for path in output_dir.iterdir()})

    def test_matching_saved_messages_resume_without_model_call(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            args, _, output_dir = self._setup_run(tmp_dir)
            messages = runner.build_messages(args, scenario="restrictedaccess", instruction="New prompt")
            (output_dir / "request.json").write_text(json.dumps({"messages": messages}), encoding="utf-8")
            with mock.patch.object(runner, "build_parser") as parser, \
                    mock.patch.object(runner, "run_single_example") as run_example, \
                    mock.patch.object(runner, "aggregate_model_results") as aggregate:
                parser.return_value.parse_args.return_value = args
                runner.main()
            run_example.assert_not_called()
            aggregate.assert_called_once_with(args)


if __name__ == "__main__":
    unittest.main(verbosity=2)
