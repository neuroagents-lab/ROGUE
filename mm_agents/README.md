# Agent
## LiteLLM Prompt Agents

`PromptAgent` is the agent implementation used by `run.py` and `scripts/python/run_multienv.py`.

### Supported Models

`PromptAgent` accepts any LiteLLM-compatible model name, and the actual model availability depends on your provider credentials and whether the model supports the observation type you choose.

In practice we currently use:
- OpenAI GPT-5 models such as `gpt-5.5` and `gpt-5.4` (the default). These go through LiteLLM's Responses API.
- OpenAI chat models such as `gpt-4o` and `gpt-4.1`.
- Anthropic Claude models such as `claude-opus-4-7` and `claude-opus-4-6`.
- Gemini models such as `gemini/gemini-3.1-pro-preview`.
- Moonshot Kimi models such as `moonshot/kimi-k2.6` or plain `kimi-*`.
- Azure OpenAI deployments via `azure-gpt-4o` when `AZURE_OPENAI_DEPLOYMENT` is set.

Vision models are needed for screenshot-based observations. Text-only models can be used for `a11y_tree`-only runs.

### How to Use Models

The normal entrypoints are:
- `python run.py ...`
- `python scripts/python/run_multienv.py ...`

Pass the model name directly with `--model`, along with `--reasoning_effort` when the provider or model supports it. Example:

```bash
python run.py   --provider_name vmware   --path_to_vm ./vmware_vm_data/Ubuntu0/Ubuntu0.vmx   --headless   --action_space pyautogui   --observation_type screenshot_a11y_tree   --model gpt-5.4   --reasoning_effort medium   --max_steps 20   --max_trajectory_length 20   --client_password password
```

If you want to use the agent directly, import it from `mm_agents.agent_litellm`:

```python
from mm_agents.agent_litellm import PromptAgent

agent = PromptAgent(
    model="gpt-5.4",
    observation_type="screenshot_a11y_tree",
    action_space="pyautogui",
    reasoning_effort="medium",
)

response, actions = agent.predict(
    "Open the latest report and summarize it.",
    {
        "screenshot": open("path/to/screenshot.png", "rb").read(),
        "accessibility_tree": open("path/to/accessibility_tree.txt").read(),
    },
)
```

`obs["screenshot"]` should be raw image bytes. `obs["accessibility_tree"]` should be the current linearized tree string. For `a11y_tree`, omit the screenshot. For `som`, provide both screenshot and accessibility tree.

### Observation and Action Spaces

We currently support these observation spaces:
- `a11y_tree`: the accessibility tree of the current screen
- `screenshot`: a screenshot of the current screen
- `screenshot_a11y_tree`: a screenshot plus the accessibility tree overlay
- `som`: the set-of-mark view with table metadata included

And these action spaces:
- `pyautogui`: Python code emitted as `pyautogui` actions
- `computer_13`: the structured enumerated action space used by the benchmark
