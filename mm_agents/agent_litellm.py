import ast
import base64
import json
import logging
import os
import re
import tempfile
import time
import xml.etree.ElementTree as ET
from copy import deepcopy
from io import BytesIO
from typing import Any, Dict, List, Optional

import backoff
import litellm
import requests

litellm.drop_params = True
litellm.verbose = False
litellm.set_verbose = False
logging.getLogger("LiteLLM").setLevel(logging.WARNING)
logging.getLogger("LiteLLM Router").setLevel(logging.WARNING)
logging.getLogger("LiteLLM Proxy").setLevel(logging.WARNING)
import tiktoken
from PIL import Image
from requests.exceptions import SSLError

from mm_agents.accessibility_tree_wrap.heuristic_retrieve import filter_nodes, draw_bounding_boxes
from mm_agents.prompts import (
    DEPLOYMENT_PROMPT,
    EVALUATION_PROMPT,
    ENVIRONMENT_QUESTION,
    INOCULATION_PROMPT,
    SUBAGENT_SPECIAL_COMMAND_INSTRUCTION,
    SYS_PROMPT_IN_A11Y_OUT_ACTION,
    SYS_PROMPT_IN_A11Y_OUT_CODE,
    SYS_PROMPT_IN_BOTH_OUT_ACTION,
    SYS_PROMPT_IN_BOTH_OUT_CODE,
    SYS_PROMPT_IN_SCREENSHOT_OUT_ACTION,
    SYS_PROMPT_IN_SCREENSHOT_OUT_CODE,
    SYS_PROMPT_IN_SOM_OUT_TAG,
)

logger = logging.getLogger("desktopenv.agent")

pure_text_settings = ['a11y_tree']

attributes_ns_ubuntu = "https://accessibility.windows.example.org/ns/attributes"
attributes_ns_windows = "https://accessibility.windows.example.org/ns/attributes"
state_ns_ubuntu = "https://accessibility.ubuntu.example.org/ns/state"
state_ns_windows = "https://accessibility.windows.example.org/ns/state"
component_ns_ubuntu = "https://accessibility.ubuntu.example.org/ns/component"
component_ns_windows = "https://accessibility.windows.example.org/ns/component"
value_ns_ubuntu = "https://accessibility.ubuntu.example.org/ns/value"
value_ns_windows = "https://accessibility.windows.example.org/ns/value"
class_ns_windows = "https://accessibility.windows.example.org/ns/class"
# More namespaces defined in OSWorld, please check desktop_env/server/main.py

def _is_quota_exceeded_error(error: Exception) -> bool:
    err_text = str(error).lower()
    return any(needle in err_text for needle in [
        "quota exceeded",
        "resource_exhausted",
        "current quota",
        "billing details",
        "generate_requests_per_model_per_day",
    ])


def encode_image(image_content):
    return base64.b64encode(image_content).decode('utf-8')


def encoded_img_to_pil_img(data_str):
    base64_str = data_str.replace("data:image/png;base64,", "")
    image_data = base64.b64decode(base64_str)
    image = Image.open(BytesIO(image_data))
    return image


def save_to_tmp_img_file(data_str):
    base64_str = data_str.replace("data:image/png;base64,", "")
    image_data = base64.b64decode(base64_str)
    image = Image.open(BytesIO(image_data))
    tmp_img_path = os.path.join(tempfile.mkdtemp(), "tmp_img.png")
    image.save(tmp_img_path)
    return tmp_img_path


def _is_token_param_error(error: Exception) -> bool:
    err_text = str(error)
    return any(p in err_text for p in [
        "max_output_tokens",
        "max_completion_tokens",
        "max_tokens",
        "unsupported_parameter",
    ])


def _extract_openai_model_name(model_name: str) -> str:
    if model_name.startswith("openai/"):
        return model_name.split("/", 1)[1]
    return model_name


def _extract_text_content(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text" and item.get("text"):
                parts.append(item["text"])
        return "\n".join(parts)
    return ""


def linearize_accessibility_tree(accessibility_tree, platform="ubuntu"):

    if platform == "ubuntu":
        _attributes_ns = attributes_ns_ubuntu
        _state_ns = state_ns_ubuntu
        _component_ns = component_ns_ubuntu
        _value_ns = value_ns_ubuntu
    elif platform == "windows":
        _attributes_ns = attributes_ns_windows
        _state_ns = state_ns_windows
        _component_ns = component_ns_windows
        _value_ns = value_ns_windows
    else:
        raise ValueError("Invalid platform, must be 'ubuntu' or 'windows'")

    filtered_nodes = filter_nodes(ET.fromstring(accessibility_tree), platform)
    linearized_accessibility_tree = ["tag\tname\ttext\tclass\tdescription\tposition (top-left x&y)\tsize (w&h)"]

    for node in filtered_nodes:
        if node.text:
            text = (
                node.text if '"' not in node.text
                else '"{:}"'.format(node.text.replace('"', '""'))
            )
        elif node.get("{{{:}}}class".format(class_ns_windows), "").endswith("EditWrapper") \
                and node.get("{{{:}}}value".format(_value_ns)):
            node_text = node.get("{{{:}}}value".format(_value_ns), "")
            text = (node_text if '"' not in node_text
                    else '"{:}"'.format(node_text.replace('"', '""')))
        else:
            text = '""'

        linearized_accessibility_tree.append(
            "{:}\t{:}\t{:}\t{:}\t{:}\t{:}\t{:}".format(
                node.tag, node.get("name", ""),
                text,
                node.get("{{{:}}}class".format(_attributes_ns), "") if platform == "ubuntu" else node.get("{{{:}}}class".format(class_ns_windows), ""),
                node.get("{{{:}}}description".format(_attributes_ns), ""),
                node.get('{{{:}}}screencoord'.format(_component_ns), ""),
                node.get('{{{:}}}size'.format(_component_ns), "")
            )
        )

    return "\n".join(linearized_accessibility_tree)


def tag_screenshot(screenshot, accessibility_tree, platform="ubuntu"):
    nodes = filter_nodes(ET.fromstring(accessibility_tree), platform=platform, check_image=True)
    # Make tag screenshot
    marks, drew_nodes, element_list, tagged_screenshot = draw_bounding_boxes(nodes, screenshot)

    return marks, drew_nodes, tagged_screenshot, element_list

def parse_actions_from_string(input_string):
    if input_string.strip() in ['WAIT', 'DONE', 'FAIL']:
        return [input_string.strip()]
    # Search for a JSON string within the input string
    actions = []
    matches = re.findall(r'```json\s+(.*?)\s+```', input_string, re.DOTALL)
    if matches:
        # Assuming there's only one match, parse the JSON string into a dictionary
        try:
            for match in matches:
                action_dict = json.loads(match)
                actions.append(action_dict)
            return actions
        except json.JSONDecodeError as e:
            return f"Failed to parse JSON: {e}"
    else:
        matches = re.findall(r'```\s+(.*?)\s+```', input_string, re.DOTALL)
        if matches:
            # Assuming there's only one match, parse the JSON string into a dictionary
            try:
                for match in matches:
                    action_dict = json.loads(match)
                    actions.append(action_dict)
                return actions
            except json.JSONDecodeError as e:
                return f"Failed to parse JSON: {e}"
        else:
            try:
                action_dict = json.loads(input_string)
                return [action_dict]
            except json.JSONDecodeError:
                raise ValueError("Invalid response format: " + input_string)


def _find_subagent_command_in_response(input_string: str) -> Optional[str]:
    input_string = input_string.strip()
    subagent_task = parse_subagent_command(input_string)
    if subagent_task is not None:
        return format_subagent_command(subagent_task)

    pattern = r"```(?:\w+\s+)?(.*?)```"
    matches = re.findall(pattern, input_string, re.DOTALL)

    for match in matches:
        match = match.strip()
        subagent_command = _extract_subagent_command_from_block(match)
        if subagent_command is not None:
            return subagent_command

        task = parse_subagent_command(match)
        if task is not None:
            return format_subagent_command(task)

    return None


def parse_code_from_string(input_string, allow_subagents: bool = True):
    input_string = input_string.strip()
    if input_string.strip() in ['WAIT', 'DONE', 'FAIL']:
        return [input_string.strip()]
    if allow_subagents:
        subagent_command = _find_subagent_command_in_response(input_string)
        if subagent_command is not None:
            return [subagent_command]

    pattern = r"```(?:\w+\s+)?(.*?)```"
    matches = re.findall(pattern, input_string, re.DOTALL)
    codes = []

    for match in matches:
        match = match.strip()
        commands = ['WAIT', 'DONE', 'FAIL']  # fixme: updates this part when we have more commands

        if match in commands:
            codes.append(match.strip())
        elif match.split('\n')[-1] in commands:
            if len(match.split('\n')) > 1:
                codes.append("\n".join(match.split('\n')[:-1]))
            codes.append(match.split('\n')[-1])
        else:
            codes.append(match)

    return codes


def parse_code_from_som_string(input_string, masks, allow_subagents: bool = True):
    # parse the output string by masks
    tag_vars = ""
    for i, mask in enumerate(masks):
        x, y, w, h = mask
        tag_vars += "tag_" + str(i + 1) + "=" + "({}, {})".format(int(x + w // 2), int(y + h // 2))
        tag_vars += "\n"

    actions = parse_code_from_string(input_string, allow_subagents=allow_subagents)

    for i, action in enumerate(actions):
        if action.strip() in ['WAIT', 'DONE', 'FAIL'] or parse_subagent_command(action) is not None:
            pass
        else:
            action = tag_vars + action
            actions[i] = action

    return actions


def response_contains_subagent_command(response: str) -> bool:
    return _find_subagent_command_in_response(response) is not None


def trim_accessibility_tree(linearized_accessibility_tree, max_tokens):
    enc = tiktoken.encoding_for_model("gpt-4")
    tokens = enc.encode(linearized_accessibility_tree)
    if len(tokens) > max_tokens:
        linearized_accessibility_tree = enc.decode(tokens[:max_tokens])
        linearized_accessibility_tree += "[...]\n"
    return linearized_accessibility_tree


def parse_subagent_command(input_string: str) -> Optional[str]:
    stripped = input_string.strip()
    if not stripped.startswith("SUBAGENT(") or not stripped.endswith(")"):
        return None

    inner = stripped[len("SUBAGENT("):-1].strip()
    try:
        task = ast.literal_eval(inner)
    except (SyntaxError, ValueError):
        return None

    if not isinstance(task, str):
        return None

    task = task.strip()
    return task or None


def format_subagent_command(task: str) -> str:
    return f"SUBAGENT({json.dumps(task)})"


def _extract_subagent_command_from_block(block: str) -> Optional[str]:
    lines = [line.strip() for line in block.splitlines() if line.strip()]
    if not lines:
        return None

    command_lines = [line for line in lines if not line.startswith("#")]
    if len(command_lines) != 1:
        return None

    task = parse_subagent_command(command_lines[0])
    if task is None:
        return None
    return format_subagent_command(task)


class PromptAgent:
    def __init__(
            self,
            platform="ubuntu",
            model="gpt-4-vision-preview",
            max_tokens=1500,
            top_p=0.9,
            temperature=0.5,
            action_space="computer_13",
            observation_type="screenshot_a11y_tree",
            # observation_type can be in ["screenshot", "a11y_tree", "screenshot_a11y_tree", "som"]
            max_trajectory_length=3,
            a11y_tree_max_tokens=10000,
            client_password="password",
            max_steps: Optional[int] = None,
            show_steps_left_in_prompt: bool = False,
            reasoning_effort="low",
            environment_question=False,
            deployment_prompt=False,
            evaluation_prompt=False,
            inoculation_prompt=False,
            enable_subagents: bool = False,
            subagent_inherit_parent_history: bool = False,
    ):
        self.platform = platform
        self.model = model
        self.max_tokens = max_tokens
        self.top_p = top_p
        self.temperature = temperature
        self.action_space = action_space
        self.observation_type = observation_type
        self.max_trajectory_length = max_trajectory_length
        self.a11y_tree_max_tokens = a11y_tree_max_tokens
        self.client_password = client_password
        self.max_steps = max_steps
        self.show_steps_left_in_prompt = show_steps_left_in_prompt
        self.reasoning_effort = reasoning_effort
        self.environment_question = environment_question
        self.deployment_prompt = deployment_prompt
        self.evaluation_prompt = evaluation_prompt
        self.inoculation_prompt = inoculation_prompt
        self.enable_subagents = enable_subagents
        self.subagent_inherit_parent_history = subagent_inherit_parent_history

        self.thoughts = []
        self.actions = []
        self.observations = []
        self.result_dir = None
        self.reasoning_call_count = 0
        self.root_instruction = None
        self.current_instruction = None
        self.parent_history_instruction = None
        self.pending_subagent_result = None
        self.step_offset = 0
        self.runtime_logger = None
        self.last_llm_error = None

        self.system_message = self._get_base_system_message().replace(
            "{CLIENT_PASSWORD}", self.client_password
        )

    def _get_base_system_message(self) -> str:
        if self.observation_type == "screenshot":
            if self.action_space == "computer_13":
                return SYS_PROMPT_IN_SCREENSHOT_OUT_ACTION
            if self.action_space == "pyautogui":
                return SYS_PROMPT_IN_SCREENSHOT_OUT_CODE
            raise ValueError("Invalid action space: " + self.action_space)
        if self.observation_type == "a11y_tree":
            if self.action_space == "computer_13":
                return SYS_PROMPT_IN_A11Y_OUT_ACTION
            if self.action_space == "pyautogui":
                return SYS_PROMPT_IN_A11Y_OUT_CODE
            raise ValueError("Invalid action space: " + self.action_space)
        if self.observation_type == "screenshot_a11y_tree":
            if self.action_space == "computer_13":
                return SYS_PROMPT_IN_BOTH_OUT_ACTION
            if self.action_space == "pyautogui":
                return SYS_PROMPT_IN_BOTH_OUT_CODE
            raise ValueError("Invalid action space: " + self.action_space)
        if self.observation_type == "som":
            if self.action_space == "computer_13":
                raise ValueError("Invalid action space: " + self.action_space)
            if self.action_space == "pyautogui":
                return SYS_PROMPT_IN_SOM_OUT_TAG
            raise ValueError("Invalid action space: " + self.action_space)
        raise ValueError("Invalid experiment type: " + self.observation_type)

    def _uses_openai_responses_api(self, model: str) -> bool:
        base_model = model.split("/")[-1]
        return base_model.startswith("gpt-5")

    def _is_anthropic_model(self, model: str) -> bool:
        base_model = model.split("/")[-1]
        return base_model.startswith("claude")

    def _is_moonshot_kimi_model(self, model: str) -> bool:
        provider, _, base_model = model.partition("/")
        if provider == "moonshot":
            return True
        return base_model.startswith("kimi-") or model.startswith("kimi-")

    def _normalize_sampling_params(
        self,
        model: str,
        top_p: Optional[float],
        temperature: Optional[float],
        reasoning_effort: Optional[str],
        uses_responses_api: bool,
    ) -> tuple[Optional[float], Optional[float]]:
        effective_top_p = top_p
        effective_temperature = temperature

        # Moonshot Kimi currently only accepts top_p=0.95.
        if self._is_moonshot_kimi_model(model) and effective_top_p != 0.95:
            logger.info(
                "Overriding top_p=%r to 0.95 for %s because Moonshot Kimi only accepts top_p=0.95.",
                effective_top_p,
                model,
            )
            effective_top_p = 0.95

        should_drop_sampling = False
        reason = None
        if uses_responses_api and reasoning_effort != "none":
            should_drop_sampling = True
            reason = f"reasoning_effort is {reasoning_effort!r}, not 'none'"
        elif self._is_anthropic_model(model) and reasoning_effort != "none":
            should_drop_sampling = True
            reason = (
                f"Claude thinking is enabled with reasoning_effort {reasoning_effort!r}"
            )

        if should_drop_sampling:
            if effective_top_p is not None or effective_temperature is not None:
                logger.info(
                    "Not passing temperature/top_p to %s because %s.",
                    model,
                    reason,
                )
            effective_top_p = None
            effective_temperature = None

        return effective_top_p, effective_temperature

    def _resolve_litellm_model(self, model: str) -> str:
        if model.startswith("azure-gpt-4o"):  # special case
            return f"azure/{os.getenv('AZURE_OPENAI_DEPLOYMENT', model)}"
        if self._is_anthropic_model(model) and not model.startswith("anthropic/"):
            return f"anthropic/{model}"
        return model

    def _normalize_responses_content_part(self, part: Dict[str, Any], role: str) -> Dict[str, Any]:
        part_type = part.get("type")
        if part_type == "text":
            return {
                "type": "output_text" if role == "assistant" else "input_text",
                "text": part.get("text", ""),
            }
        if part_type == "image_url":
            image_url = part.get("image_url", {})
            return {
                "type": "input_image",
                "image_url": image_url.get("url"),
                "detail": image_url.get("detail"),
            }
        return part

    def _normalize_messages_for_responses_api(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized_messages = []
        for msg in messages:
            content = msg.get("content")
            if isinstance(content, str):
                normalized_content = content
            elif isinstance(content, list):
                normalized_content = [
                    self._normalize_responses_content_part(part, msg["role"])
                    for part in content
                ]
            else:
                normalized_content = content

            normalized_message = {
                "role": msg["role"],
                "content": normalized_content,
            }
            normalized_messages.append(normalized_message)

        return normalized_messages

    def _extract_content_text(self, content: Any) -> str:
        if isinstance(content, str):
            return content
        if not isinstance(content, list):
            return content or ""

        text_parts = []
        for item in content:
            item_type = item.get("type") if isinstance(item, dict) else getattr(item, "type", None)
            if item_type in {"output_text", "input_text", "text"}:
                text_parts.append(
                    item.get("text", "") if isinstance(item, dict) else getattr(item, "text", "")
                )
            elif item_type == "refusal":
                text_parts.append(
                    item.get("refusal", "") if isinstance(item, dict) else getattr(item, "refusal", "")
                )
        return "".join(text_parts)

    def _extract_chat_response(self, response: Any) -> tuple[str, str]:
        message = response.choices[0].message
        response_text = self._extract_content_text(getattr(message, "content", ""))

        reasoning_content = getattr(message, "reasoning_content", None) or ""
        provider_specific_fields = getattr(message, "provider_specific_fields", None)
        if not reasoning_content and isinstance(provider_specific_fields, dict):
            reasoning_content = provider_specific_fields.get("reasoning_content", "")

        return response_text, reasoning_content

    def _extract_responses_message(self, response: Any) -> Any:
        choices = getattr(response, "choices", None)
        if choices:
            return choices[0].message

        output = getattr(response, "output", None) or []
        for item in output:
            item_type = item.get("type") if isinstance(item, dict) else getattr(item, "type", None)
            if item_type == "message":
                return item
        return None

    def _extract_responses_reasoning(self, response: Any) -> str:
        reasoning_parts = []
        output = getattr(response, "output", None) or []
        for item in output:
            item_type = item.get("type") if isinstance(item, dict) else getattr(item, "type", None)
            if item_type != "reasoning":
                continue

            summary = item.get("summary") if isinstance(item, dict) else getattr(item, "summary", None)
            if isinstance(summary, list):
                for summary_item in summary:
                    summary_type = summary_item.get("type") if isinstance(summary_item, dict) else getattr(summary_item, "type", None)
                    if summary_type == "summary_text":
                        reasoning_parts.append(
                            summary_item.get("text", "")
                            if isinstance(summary_item, dict)
                            else getattr(summary_item, "text", "")
                        )

        if reasoning_parts:
            return "\n".join(part for part in reasoning_parts if part)

        reasoning_attr = getattr(response, "reasoning", None)
        if reasoning_attr is not None:
            summary = (
                reasoning_attr.get("summary")
                if isinstance(reasoning_attr, dict)
                else getattr(reasoning_attr, "summary", None)
            )
            if isinstance(summary, list):
                summary_parts = []
                for item in summary:
                    item_type = item.get("type") if isinstance(item, dict) else getattr(item, "type", None)
                    if item_type == "summary_text":
                        summary_parts.append(
                            item.get("text", "") if isinstance(item, dict) else getattr(item, "text", "")
                        )
                if summary_parts:
                    return "\n".join(summary_parts)

        provider_specific_fields = getattr(response, "provider_specific_fields", None)
        if isinstance(provider_specific_fields, dict):
            return provider_specific_fields.get("reasoning_content", "")

        return ""

    def _extract_responses_output(self, response: Any) -> tuple[str, str]:
        message = self._extract_responses_message(response)
        if message is None:
            return getattr(response, "output_text", "") or "", self._extract_responses_reasoning(response)

        content = message.get("content", "") if isinstance(message, dict) else getattr(message, "content", "")
        response_text = self._extract_content_text(content)

        reasoning_content = (
            message.get("reasoning_content", "")
            if isinstance(message, dict)
            else getattr(message, "reasoning_content", "")
        ) or ""
        if not reasoning_content:
            provider_specific_fields = getattr(message, "provider_specific_fields", None)
            if isinstance(provider_specific_fields, dict):
                reasoning_content = provider_specific_fields.get("reasoning_content", "")
        if not reasoning_content:
            reasoning_content = self._extract_responses_reasoning(response)

        return response_text, reasoning_content

    def _call_chat_completion(self, litellm_model: str, messages: List[Dict[str, Any]], max_tokens, top_p, temperature,
                              reasoning_effort: Optional[str]) -> tuple[str, str]:
        effective_top_p, effective_temperature = self._normalize_sampling_params(
            litellm_model,
            top_p,
            temperature,
            reasoning_effort,
            uses_responses_api=False,
        )

        request_kwargs = {
            "model": litellm_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "top_p": effective_top_p,
            "temperature": effective_temperature,
            "reasoning_effort": reasoning_effort,
        }
        request_kwargs = {k: v for k, v in request_kwargs.items() if v is not None}
        response = litellm.completion(**request_kwargs)
        return self._extract_chat_response(response)

    def _call_responses_api(self, litellm_model: str, messages: List[Dict[str, Any]], max_tokens, top_p, temperature,
                            reasoning_effort: Optional[str]) -> tuple[str, str]:
        effective_top_p, effective_temperature = self._normalize_sampling_params(
            litellm_model,
            top_p,
            temperature,
            reasoning_effort,
            uses_responses_api=True,
        )

        request_kwargs = {
            "model": litellm_model,
            "input": self._normalize_messages_for_responses_api(messages),
            "max_output_tokens": max_tokens,
            "top_p": effective_top_p,
            "temperature": effective_temperature,
            "reasoning": {
                "effort": reasoning_effort,
                "summary": "auto",
            } if reasoning_effort is not None else None,
        }
        request_kwargs = {k: v for k, v in request_kwargs.items() if v is not None}
        response = litellm.responses(**request_kwargs)
        print("RAW RESPONSE:", response)
        return self._extract_responses_output(response)

    def _init_reasoning_log(self) -> None:
        if not self.result_dir:
            return
        os.makedirs(self.result_dir, exist_ok=True)
        with open(
            os.path.join(self.result_dir, "reasoning_content.jsonl"),
            "w",
            encoding="utf-8",
        ):
            pass

    def _write_reasoning_content(
            self,
            model: str,
            reasoning_effort: Optional[str],
            reasoning_content: str,
    ) -> None:
        if not self.result_dir:
            return

        self.reasoning_call_count += 1
        record = {
            "call_index": self.reasoning_call_count,
            "model": model,
            "reasoning_effort": reasoning_effort,
            "reasoning_content": reasoning_content,
        }
        with open(
            os.path.join(self.result_dir, "reasoning_content.jsonl"),
            "a",
            encoding="utf-8",
        ) as f:
            f.write(json.dumps(record, ensure_ascii=False))
            f.write("\n")

    def create_subagent(self) -> "PromptAgent":
        child = PromptAgent(
            platform=self.platform,
            model=self.model,
            max_tokens=self.max_tokens,
            top_p=self.top_p,
            temperature=self.temperature,
            action_space=self.action_space,
            observation_type=self.observation_type,
            max_trajectory_length=self.max_trajectory_length,
            a11y_tree_max_tokens=self.a11y_tree_max_tokens,
            client_password=self.client_password,
            max_steps=self.max_steps,
            show_steps_left_in_prompt=self.show_steps_left_in_prompt,
            reasoning_effort=self.reasoning_effort,
            environment_question=self.environment_question,
            deployment_prompt=self.deployment_prompt,
            evaluation_prompt=self.evaluation_prompt,
            inoculation_prompt=self.inoculation_prompt,
            enable_subagents=self.enable_subagents,
            subagent_inherit_parent_history=self.subagent_inherit_parent_history,
        )
        child.result_dir = self.result_dir
        child.runtime_logger = self.runtime_logger
        if self.subagent_inherit_parent_history:
            child.parent_history_instruction = (
                self.root_instruction or self.current_instruction
            )
            child.observations = deepcopy(self.observations)
            child.actions = deepcopy(self.actions)
            child.thoughts = deepcopy(self.thoughts)
        return child

    def set_pending_subagent_result(self, summary: str) -> None:
        normalized = summary.strip()
        self.pending_subagent_result = normalized or None

    def _build_system_message(self, instruction: str) -> str:
        system_message_parts = [self.system_message]
        if self.enable_subagents:
            system_message_parts.append(SUBAGENT_SPECIAL_COMMAND_INSTRUCTION)
        if self.inoculation_prompt:
            system_message_parts.append(INOCULATION_PROMPT)
        if self.environment_question:
            system_message_parts.append(ENVIRONMENT_QUESTION)
        if self.deployment_prompt:
            system_message_parts.append(DEPLOYMENT_PROMPT)
        if self.evaluation_prompt:
            system_message_parts.append(EVALUATION_PROMPT)
        system_message_parts.append(
            "You are asked to complete the following task: {}".format(instruction)
        )

        if self.parent_history_instruction:
            system_message_parts.append(
                "Inherited parent context:"
                f"\n- Parent task: {self.parent_history_instruction}"
                "\n- The previous observations, actions, and reflections in this prompt were inherited from the parent agent."
            )
        return "\n\n".join(system_message_parts)

    def predict(self, instruction: str, obs: Dict) -> List:
        """
        Predict the next action(s) based on the current observation.
        """
        self.current_instruction = instruction
        if self.root_instruction is None:
            self.root_instruction = instruction

        system_message = self._build_system_message(instruction)

        if self.show_steps_left_in_prompt and self.max_steps is not None:
            consumed_steps = self.step_offset + len(self.actions)
            current_step = consumed_steps + 1
            steps_left = max(self.max_steps - consumed_steps, 0)
            system_message += (
                "\n\nExecution status:"
                f"\n- Current step: {current_step}"
                f"\n- Steps remaining including this step: {steps_left}"
                "\n- You must finish within the remaining steps."
                # "\n- If you cannot finish in time, return FAIL."
            )

        # Prepare the payload for the API call
        messages = []
        masks = None

        messages.append({
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": system_message
                },
            ]
        })
        
        # Append trajectory
        assert len(self.observations) == len(self.actions) and len(self.actions) == len(self.thoughts) \
            , "The number of observations and actions should be the same."

        if len(self.observations) > self.max_trajectory_length:
            if self.max_trajectory_length == 0:
                _observations = []
                _actions = []
                _thoughts = []
            else:
                _observations = self.observations[-self.max_trajectory_length:]
                _actions = self.actions[-self.max_trajectory_length:]
                _thoughts = self.thoughts[-self.max_trajectory_length:]
        else:
            _observations = self.observations
            _actions = self.actions
            _thoughts = self.thoughts

        for previous_obs, previous_action, previous_thought in zip(_observations, _actions, _thoughts):

            if self.observation_type == "screenshot_a11y_tree":
                _screenshot = previous_obs["screenshot"]
                _linearized_accessibility_tree = previous_obs["accessibility_tree"]

                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Given the screenshot and info from accessibility tree as below:\n{}\nWhat's the next step that you will do to help with the task?".format(
                                _linearized_accessibility_tree)
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{_screenshot}",
                                "detail": "high"
                            }
                        }
                    ]
                })
            elif self.observation_type in ["som"]:
                _screenshot = previous_obs["screenshot"]

                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Given the tagged screenshot as below. What's the next step that you will do to help with the task?"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{_screenshot}",
                                "detail": "high"
                            }
                        }
                    ]
                })
            elif self.observation_type == "screenshot":
                _screenshot = previous_obs["screenshot"]

                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Given the screenshot as below. What's the next step that you will do to help with the task?"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{_screenshot}",
                                "detail": "high"
                            }
                        }
                    ]
                })
            elif self.observation_type == "a11y_tree":
                _linearized_accessibility_tree = previous_obs["accessibility_tree"]

                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Given the info from accessibility tree as below:\n{}\nWhat's the next step that you will do to help with the task?".format(
                                _linearized_accessibility_tree)
                        }
                    ]
                })
            else:
                raise ValueError("Invalid observation_type type: " + self.observation_type)

            messages.append({
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": previous_thought.strip() if len(previous_thought) > 0 else "No valid action"
                    },
                ]
            })

        pending_subagent_result = self.pending_subagent_result
        if pending_subagent_result:
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "SUBAGENT RESULT:\n"
                            f"{pending_subagent_result}\n\n"
                            "The delegated child agent already acted on the computer. "
                            "Use this summary as context, then verify the current screen before taking the next action."
                        ),
                    }
                ],
            })

        if self.observation_type in ["screenshot", "screenshot_a11y_tree"]:
            base64_image = encode_image(obs["screenshot"])
            linearized_accessibility_tree = linearize_accessibility_tree(accessibility_tree=obs["accessibility_tree"],
                                                                         platform=self.platform) if self.observation_type == "screenshot_a11y_tree" else None
            logger.debug("LINEAR AT: %s", linearized_accessibility_tree)

            if linearized_accessibility_tree:
                linearized_accessibility_tree = trim_accessibility_tree(linearized_accessibility_tree,
                                                                        self.a11y_tree_max_tokens)

            if self.observation_type == "screenshot_a11y_tree":
                self.observations.append({
                    "screenshot": base64_image,
                    "accessibility_tree": linearized_accessibility_tree
                })
            else:
                self.observations.append({
                    "screenshot": base64_image,
                    "accessibility_tree": None
                })

            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Given the screenshot as below. What's the next step that you will do to help with the task?"
                        if self.observation_type == "screenshot"
                        else "Given the screenshot and info from accessibility tree as below:\n{}\nWhat's the next step that you will do to help with the task?".format(
                            linearized_accessibility_tree)
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_image}",
                            "detail": "high"
                        }
                    }
                ]
            })
        elif self.observation_type == "a11y_tree":
            linearized_accessibility_tree = linearize_accessibility_tree(accessibility_tree=obs["accessibility_tree"],
                                                                         platform=self.platform)
            logger.debug("LINEAR AT: %s", linearized_accessibility_tree)

            if linearized_accessibility_tree:
                linearized_accessibility_tree = trim_accessibility_tree(linearized_accessibility_tree,
                                                                        self.a11y_tree_max_tokens)

            self.observations.append({
                "screenshot": None,
                "accessibility_tree": linearized_accessibility_tree
            })

            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Given the info from accessibility tree as below:\n{}\nWhat's the next step that you will do to help with the task?".format(
                            linearized_accessibility_tree)
                    }
                ]
            })
        elif self.observation_type == "som":
            masks, drew_nodes, tagged_screenshot, linearized_accessibility_tree = tag_screenshot(obs["screenshot"], obs[
                "accessibility_tree"], self.platform)
            base64_image = encode_image(tagged_screenshot)
            logger.debug("LINEAR AT: %s", linearized_accessibility_tree)

            if linearized_accessibility_tree:
                linearized_accessibility_tree = trim_accessibility_tree(linearized_accessibility_tree,
                                                                        self.a11y_tree_max_tokens)

            self.observations.append({
                "screenshot": base64_image,
                "accessibility_tree": linearized_accessibility_tree
            })

            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Given the tagged screenshot and info from accessibility tree as below:\n{}\nWhat's the next step that you will do to help with the task?".format(
                            linearized_accessibility_tree)
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_image}",
                            "detail": "high"
                        }
                    }
                ]
            })
        else:
            raise ValueError("Invalid observation_type type: " + self.observation_type)

        try:
            response, reasoning_content = self.call_llm({
                "model": self.model,
                "messages": messages,
                "max_tokens": self.max_tokens,
                "top_p": self.top_p,
                "temperature": self.temperature,
                "reasoning_effort": self.reasoning_effort,
            })
        except Exception as e:
            logger.error("Failed to call" + self.model + ", Error: " + str(e))
            response = ""
            reasoning_content = ""

        logger.info("RESPONSE: %s", response)
        self._write_reasoning_content(self.model, self.reasoning_effort, reasoning_content)

        try:
            actions = self.parse_actions(response, masks)
            self.thoughts.append(response)
        except ValueError as e:
            print("Failed to parse action from response", e)
            actions = None
            self.thoughts.append("")

        if pending_subagent_result:
            self.pending_subagent_result = None

        return response, actions

    # Revision: Change General exceptions, OpenAI exceptions, Google exceptions to litellm exceptions
    @backoff.on_exception(
        backoff.constant,
        (
                SSLError,
                litellm.RateLimitError,
                litellm.BadRequestError,
                litellm.InternalServerError,
        ),
        interval=30,
        max_tries=10
    )
    # Revision: Change to use litellm call the api
    def call_llm(self, payload):
        messages = payload["messages"]
        max_tokens = payload.get("max_tokens")
        top_p = payload.get("top_p")
        temperature = payload.get("temperature")
        model = payload.get("model", self.model)
        reasoning_effort = payload.get("reasoning_effort", self.reasoning_effort)

        litellm_model = self._resolve_litellm_model(model)
        self.last_llm_error = None

        logger.info("Generating content with model: %s", litellm_model)

        # litellm uses OpenAI message format natively; flatten system content list to string
        # since some providers require system messages as plain strings
        normalized_messages = []
        for msg in messages:
            if isinstance(msg.get("content"), list) and msg["role"] == "system" and \
                    all(p.get("type") == "text" for p in msg["content"]):
                normalized_messages.append({
                    "role": "system",
                    "content": "\n".join(p["text"] for p in msg["content"])
                })
            else:
                normalized_messages.append(msg)

        try:
            use_responses_api = self._uses_openai_responses_api(litellm_model)
            if use_responses_api:
                return self._call_responses_api(
                    litellm_model,
                    normalized_messages,
                    max_tokens,
                    top_p,
                    temperature,
                    reasoning_effort,
                )
            return self._call_chat_completion(
                litellm_model,
                normalized_messages,
                max_tokens,
                top_p,
                temperature,
                reasoning_effort,
            )
        except litellm.ContextWindowExceededError:
            logger.error("Context length exceeded. Retrying with a smaller context.")
            normalized_messages = [normalized_messages[0]] + normalized_messages[-1:]
            use_responses_api = self._uses_openai_responses_api(litellm_model)
            if use_responses_api:
                return self._call_responses_api(
                    litellm_model,
                    normalized_messages,
                    max_tokens,
                    top_p,
                    temperature,
                    reasoning_effort,
                )
            return self._call_chat_completion(
                litellm_model,
                normalized_messages,
                max_tokens,
                top_p,
                temperature,
                reasoning_effort,
            )
        except Exception as e:
            if _is_quota_exceeded_error(e):
                error_message = (
                    f"Quota exhausted for {litellm_model}; returning an empty response so the "
                    f"retry loop can continue. {e}"
                )
            else:
                error_message = f"Failed to call LLM: {e}"
            self.last_llm_error = error_message
            logger.error(error_message)
            print(error_message, flush=True)
            time.sleep(5)
            return "", ""

    def parse_actions(self, response: str, masks=None):

        if self.observation_type in ["screenshot", "a11y_tree", "screenshot_a11y_tree"]:
            if self.action_space == "computer_13":
                actions = parse_actions_from_string(response)
            elif self.action_space == "pyautogui":
                if not self.enable_subagents and _find_subagent_command_in_response(response):
                    raise ValueError("SUBAGENT disabled")
                else:
                    actions = parse_code_from_string(
                        response,
                        allow_subagents=self.enable_subagents,
                    )
            else:
                raise ValueError("Invalid action space: " + self.action_space)

            self.actions.append(actions)
            return actions
        elif self.observation_type in ["som"]:
            if self.action_space == "computer_13":
                raise ValueError("Invalid action space: " + self.action_space)
            elif self.action_space == "pyautogui":
                if not self.enable_subagents and _find_subagent_command_in_response(response):
                    raise ValueError("SUBAGENT disabled")
                else:
                    actions = parse_code_from_som_string(
                        response,
                        masks,
                        allow_subagents=self.enable_subagents,
                    )
            else:
                raise ValueError("Invalid action space: " + self.action_space)

            self.actions.append(actions)
            return actions

    def reset(self, _logger=None, vm_ip=None, **kwargs):
        global logger
        logger = _logger if _logger is not None else logging.getLogger("desktopenv.agent")

        self.vm_ip = vm_ip
        self.result_dir = kwargs.get("result_dir")
        self.reasoning_call_count = 0

        self.thoughts = []
        self.actions = []
        self.observations = []
        self.root_instruction = None
        self.current_instruction = None
        self.parent_history_instruction = None
        self.pending_subagent_result = None
        self.step_offset = 0
        self.runtime_logger = _logger
        self.last_llm_error = None
        self._init_reasoning_log()
