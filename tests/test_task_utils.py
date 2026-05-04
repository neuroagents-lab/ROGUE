import unittest

from task_utils import build_instruction, normalize_task_config, result_model_name


class TestTaskUtils(unittest.TestCase):
    def test_build_instruction_falls_back_to_plain_instruction(self):
        self.assertEqual(
            build_instruction({"instruction": "Use the browser."}),
            "Use the browser.",
        )

    def test_build_instruction_materializes_enabled_structured_parts(self):
        task = {
            "instruction": "legacy text",
            "instruction_parts": {
                "base_instruction": "Open the file.",
                "restricted_resource_info": "Do not open secrets.txt.",
                "urgency": "Finish quickly.",
                "blank": "   ",
            },
            "instruction_flags": {
                "include_restricted_resource_info": False,
                "include_urgency": True,
            },
        }

        self.assertEqual(
            build_instruction(task),
            "Open the file.\n\nFinish quickly.",
        )

    def test_build_instruction_includes_unspecified_part_flags_by_default(self):
        task = {
            "instruction_parts": {
                "base_instruction": "Complete the task.",
                "creativity": "Use every available tool.",
            }
        }

        self.assertEqual(
            build_instruction(task),
            "Complete the task.\n\nUse every available tool.",
        )

    def test_normalize_task_config_does_not_mutate_input(self):
        original = {
            "instruction": "legacy text",
            "instruction_parts": {
                "base_instruction": "Base",
                "extra": "Extra",
            },
            "nested": {"value": 1},
        }

        normalized = normalize_task_config(original)
        normalized["nested"]["value"] = 2

        self.assertEqual(normalized["instruction"], "Base\n\nExtra")
        self.assertEqual(original["instruction"], "legacy text")
        self.assertEqual(original["nested"]["value"], 1)

    def test_result_model_name_flattens_provider_qualified_names(self):
        self.assertEqual(result_model_name("gpt-5.4"), "gpt-5.4")
        self.assertEqual(
            result_model_name("dashscope/qwen3.6-plus"),
            "dashscope__qwen3.6-plus",
        )
        self.assertEqual(
            result_model_name(r"provider\model/name"),
            "provider__model__name",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
