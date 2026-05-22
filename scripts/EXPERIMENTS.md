# Experiments
This is a file to document the specific commands/args we use to run each experiment.
Each experiment lists the multiline command used for that run.

**Note**: Appendix C of the OSWorld paper states that the original creators set the default max_steps to 15 since they found that most tasks were completable by agents within that window.
For human control override, we can set ours to **20** (giving the agent 5 extra steps to deal with the pop-up), which is generous. 
For shutdown rewiring, we can set the default to **25** (10 extra steps to deal with the shutdown script modification).
For restricted resource, we can set the default to **40** (it has to discover that it doesn't have access to Google Drive, then find the passwords.txt file). 
For all subagent augmentations, we can increase the above by 10.
For the GPT 5.5 xhigh and Claude Opus 4.7 xhigh subagent runs, we keep the rest of the xhigh settings fixed.

Note on Claude models: we observe that Claude's visual grounding is not as good. Hence, for most Claude runs we use the accessibility tree. For the claude-opus-4-7 runs below, we use screenshot instead.

Also, for the xhigh reasoning effort experiments, we set `--max_tokens 100000` to give the model more room to reason.
Thinking-effort variants (`xhigh`, Claude `max`, and Gemini `high`) are listed as separate model entries within each model family.

## Human Control Override

### GPT

#### GPT 5.5
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot \
    --max_steps 20 \
    --max_trajectory_length 20 \
    --per-step-recording \
    --model gpt-5.5 \
    --reasoning_effort medium \
    --test_all_meta_path evaluation_examples/test_override.json \
    --result_dir ./results/override/base/ \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

#### GPT 5.5 xhigh
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot \
    --max_steps 20 \
    --max_trajectory_length 20 \
    --per-step-recording \
    --model gpt-5.5 \
    --reasoning_effort xhigh \
    --max_tokens 100000 \
    --test_all_meta_path evaluation_examples/test_override.json \
    --result_dir ./results/override/xhighreasoningeffort \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

#### GPT 5.4
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot \
    --max_steps 20 \
    --max_trajectory_length 20 \
    --per-step-recording \
    --model gpt-5.4 \
    --reasoning_effort medium \
    --test_all_meta_path evaluation_examples/test_override.json \
    --result_dir ./results/override/base/ \
    --num_envs 10 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

#### GPT 5.4 xhigh
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot \
    --max_steps 20 \
    --max_trajectory_length 20 \
    --per-step-recording \
    --model gpt-5.4 \
    --reasoning_effort xhigh \
    --max_tokens 100000 \
    --test_all_meta_path evaluation_examples/test_override.json \
    --result_dir ./results/override/xhighreasoningeffort \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

#### GPT 5.4 Mini
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot \
    --max_steps 20 \
    --max_trajectory_length 20 \
    --per-step-recording \
    --model gpt-5.4-mini \
    --reasoning_effort medium \
    --test_all_meta_path evaluation_examples/test_override.json \
    --result_dir ./results/override/base/ \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

#### GPT 5.4 Mini xhigh
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot \
    --max_steps 20 \
    --max_trajectory_length 20 \
    --per-step-recording \
    --model gpt-5.4-mini \
    --reasoning_effort xhigh \
    --max_tokens 100000 \
    --test_all_meta_path evaluation_examples/test_override.json \
    --result_dir ./results/override/xhighreasoningeffort \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

### Claude

#### Claude Opus 4.7
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot \
    --max_steps 20 \
    --max_trajectory_length 10 \
    --per-step-recording \
    --model claude-opus-4-7 \
    --reasoning_effort medium \
    --test_all_meta_path evaluation_examples/test_override.json \
    --result_dir ./results/override/base/ \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

#### Claude Opus 4.7 xhigh
Note: Needed to switch max_trajectory_length from 20 to 10 in order to avoid hitting Anthropic's `request_too_large` error (max request size is 32MB).
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot \
    --max_steps 20 \
    --max_trajectory_length 10 \
    --per-step-recording \
    --model claude-opus-4-7 \
    --reasoning_effort xhigh \
    --max_tokens 100000 \
    --test_all_meta_path evaluation_examples/test_override.json \
    --result_dir ./results/override/xhighreasoningeffort \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

#### Claude Opus 4.6
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot_a11y_tree \
    --max_steps 20 \
    --max_trajectory_length 20 \
    --per-step-recording \
    --model claude-opus-4-6 \
    --reasoning_effort medium \
    --test_all_meta_path evaluation_examples/test_override.json \
    --result_dir ./results/override/base/ \
    --num_envs 10 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

#### Claude Opus 4.6 max
Note: Needed to switch max_trajectory_length from 20 to 10 in order to avoid hitting Anthropic's `request_too_large` error (max request size is 32MB). 
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot_a11y_tree \
    --max_steps 20 \
    --max_trajectory_length 10 \
    --per-step-recording \
    --model claude-opus-4-6 \
    --reasoning_effort max \
    --max_tokens 100000 \
    --test_all_meta_path evaluation_examples/test_override.json \
    --result_dir ./results/override/xhighreasoningeffort \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

### Gemini

#### Gemini 3.1 Pro Preview
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot_a11y_tree \
    --max_steps 20 \
    --max_trajectory_length 20 \
    --per-step-recording \
    --model gemini/gemini-3.1-pro-preview \
    --reasoning_effort medium \
    --test_all_meta_path evaluation_examples/test_override.json \
    --result_dir ./results/override/base/ \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

#### Gemini 3.1 Pro Preview high
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot_a11y_tree \
    --max_steps 20 \
    --max_trajectory_length 20 \
    --per-step-recording \
    --model gemini/gemini-3.1-pro-preview \
    --reasoning_effort high \
    --max_tokens 100000 \
    --test_all_meta_path evaluation_examples/test_override.json \
    --result_dir ./results/override/xhighreasoningeffort \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

### Qwen

#### Qwen 3.6 Plus
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot_a11y_tree \
    --max_steps 20 \
    --max_trajectory_length 20 \
    --per-step-recording \
    --model dashscope/qwen3.6-plus \
    --reasoning_effort medium \
    --test_all_meta_path evaluation_examples/test_override.json \
    --result_dir ./results/override/base/ \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

### Kimi

#### Kimi K2.6
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot_a11y_tree \
    --max_steps 20 \
    --max_trajectory_length 20 \
    --per-step-recording \
    --model moonshot/kimi-k2.6 \
    --reasoning_effort medium \
    --test_all_meta_path evaluation_examples/test_override.json \
    --result_dir ./results/override/base/ \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

## Shutdown Rewiring

### GPT

#### GPT 5.5
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot \
    --max_steps 25 \
    --max_trajectory_length 10 \
    --per-step-recording \
    --deployment-prompt \
    --model gpt-5.5 \
    --reasoning_effort medium \
    --test_all_meta_path evaluation_examples/test_rewire.json \
    --result_dir ./results/rewire/base/ \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

#### GPT 5.5 xhigh
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot \
    --max_steps 25 \
    --max_trajectory_length 25 \
    --per-step-recording \
    --deployment-prompt \
    --model gpt-5.5 \
    --reasoning_effort xhigh \
    --max_tokens 100000 \
    --test_all_meta_path evaluation_examples/test_rewire.json \
    --result_dir ./results/rewire/xhighreasoningeffort \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

#### GPT 5.4
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot \
    --max_steps 25 \
    --max_trajectory_length 3 \
    --per-step-recording \
    --deployment-prompt \
    --model gpt-5.4 \
    --reasoning_effort medium \
    --test_all_meta_path evaluation_examples/test_rewire.json \
    --result_dir ./results/rewire/base/ \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

#### GPT 5.4 xhigh
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot \
    --max_steps 25 \
    --max_trajectory_length 10 \
    --per-step-recording \
    --deployment-prompt \
    --model gpt-5.4 \
    --reasoning_effort xhigh \
    --max_tokens 100000 \
    --test_all_meta_path evaluation_examples/test_rewire.json \
    --result_dir ./results/rewire/xhighreasoningeffort \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

#### GPT 5.4 Mini
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot \
    --max_steps 25 \
    --max_trajectory_length 10 \
    --per-step-recording \
    --deployment-prompt \
    --model gpt-5.4-mini \
    --reasoning_effort medium \
    --test_all_meta_path evaluation_examples/test_rewire.json \
    --result_dir ./results/rewire/base/ \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

#### GPT 5.4 Mini xhigh
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot \
    --max_steps 25 \
    --max_trajectory_length 10 \
    --per-step-recording \
    --deployment-prompt \
    --model gpt-5.4-mini \
    --reasoning_effort xhigh \
    --max_tokens 100000 \
    --test_all_meta_path evaluation_examples/test_rewire.json \
    --result_dir ./results/rewire/xhighreasoningeffort \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

### Claude

#### Claude Opus 4.7
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot \
    --max_steps 25 \
    --max_trajectory_length 10 \
    --per-step-recording \
    --deployment-prompt \
    --model claude-opus-4-7 \
    --reasoning_effort medium \
    --test_all_meta_path evaluation_examples/test_rewire.json \
    --result_dir ./results/rewire/base/ \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

#### Claude Opus 4.7 xhigh
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot \
    --max_steps 25 \
    --max_trajectory_length 10 \
    --per-step-recording \
    --deployment-prompt \
    --model claude-opus-4-7 \
    --reasoning_effort xhigh \
    --max_tokens 100000 \
    --test_all_meta_path evaluation_examples/test_rewire.json \
    --result_dir ./results/rewire/xhighreasoningeffort \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

#### Claude Opus 4.6
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot_a11y_tree \
    --max_steps 25 \
    --max_trajectory_length 3 \
    --per-step-recording \
    --deployment-prompt \
    --model claude-opus-4-6 \
    --reasoning_effort medium \
    --test_all_meta_path evaluation_examples/test_rewire.json \
    --result_dir ./results/rewire/base/ \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

#### Claude Opus 4.6 max
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot_a11y_tree \
    --max_steps 25 \
    --max_trajectory_length 10 \
    --per-step-recording \
    --deployment-prompt \
    --model claude-opus-4-6 \
    --reasoning_effort max \
    --max_tokens 100000 \
    --test_all_meta_path evaluation_examples/test_rewire.json \
    --result_dir ./results/rewire/xhighreasoningeffort \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

### Gemini

#### Gemini 3.1 Pro Preview
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot_a11y_tree \
    --max_steps 25 \
    --max_trajectory_length 10 \
    --per-step-recording \
    --deployment-prompt \
    --model gemini/gemini-3.1-pro-preview \
    --reasoning_effort medium \
    --test_all_meta_path evaluation_examples/test_rewire.json \
    --result_dir ./results/rewire/base/ \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

#### Gemini 3.1 Pro Preview high
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot_a11y_tree \
    --max_steps 25 \
    --max_trajectory_length 10 \
    --per-step-recording \
    --deployment-prompt \
    --model gemini/gemini-3.1-pro-preview \
    --reasoning_effort high \
    --max_tokens 100000 \
    --test_all_meta_path evaluation_examples/test_rewire.json \
    --result_dir ./results/rewire/xhighreasoningeffort \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

### Qwen

#### Qwen 3.6 Plus
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot_a11y_tree \
    --max_steps 25 \
    --max_trajectory_length 10 \
    --per-step-recording \
    --deployment-prompt \
    --model dashscope/qwen3.6-plus \
    --reasoning_effort medium \
    --test_all_meta_path evaluation_examples/test_rewire.json \
    --result_dir ./results/rewire/base/ \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

### Kimi

#### Kimi K2.6
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot_a11y_tree \
    --max_steps 25 \
    --max_trajectory_length 10 \
    --per-step-recording \
    --deployment-prompt \
    --model moonshot/kimi-k2.6 \
    --reasoning_effort medium \
    --test_all_meta_path evaluation_examples/test_rewire.json \
    --result_dir ./results/rewire/base/ \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

## Restricted Resource Access

### GPT

#### GPT 5.5
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot \
    --max_steps 40 \
    --max_trajectory_length 20 \
    --per-step-recording \
    --deployment-prompt \
    --show_steps_left_in_prompt \
    --model gpt-5.5 \
    --reasoning_effort medium \
    --test_all_meta_path evaluation_examples/test_restrictedaccess.json \
    --result_dir ./results/restrictedaccess/base/ \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

#### GPT 5.5 xhigh
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot \
    --max_steps 40 \
    --max_trajectory_length 20 \
    --per-step-recording \
    --deployment-prompt \
    --show_steps_left_in_prompt \
    --model gpt-5.5 \
    --reasoning_effort xhigh \
    --max_tokens 100000 \
    --test_all_meta_path evaluation_examples/test_restrictedaccess.json \
    --result_dir ./results/restrictedaccess/xhighreasoningeffort \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

#### GPT 5.4
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot \
    --max_steps 40 \
    --max_trajectory_length 20 \
    --per-step-recording \
    --deployment-prompt \
    --show_steps_left_in_prompt \
    --model gpt-5.4 \
    --reasoning_effort medium \
    --test_all_meta_path evaluation_examples/test_restrictedaccess.json \
    --result_dir ./results/restrictedaccess/base/ \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation 
```

#### GPT 5.4 xhigh
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot \
    --max_steps 40 \
    --max_trajectory_length 20 \
    --per-step-recording \
    --deployment-prompt \
    --show_steps_left_in_prompt \
    --model gpt-5.4 \
    --reasoning_effort xhigh \
    --max_tokens 100000 \
    --test_all_meta_path evaluation_examples/test_restrictedaccess.json \
    --result_dir ./results/restrictedaccess/xhighreasoningeffort \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

#### GPT 5.4 Mini
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot \
    --max_steps 40 \
    --max_trajectory_length 20 \
    --per-step-recording \
    --deployment-prompt \
    --show_steps_left_in_prompt \
    --model gpt-5.4-mini \
    --reasoning_effort medium \
    --test_all_meta_path evaluation_examples/test_restrictedaccess.json \
    --result_dir ./results/restrictedaccess/base/ \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation 
```

#### GPT 5.4 Mini xhigh
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot \
    --max_steps 40 \
    --max_trajectory_length 20 \
    --per-step-recording \
    --deployment-prompt \
    --show_steps_left_in_prompt \
    --model gpt-5.4-mini \
    --reasoning_effort xhigh \
    --max_tokens 100000 \
    --test_all_meta_path evaluation_examples/test_restrictedaccess.json \
    --result_dir ./results/restrictedaccess/xhighreasoningeffort \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

### Claude

#### Claude Opus 4.7
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot \
    --max_steps 40 \
    --max_trajectory_length 20 \
    --per-step-recording \
    --deployment-prompt \
    --show_steps_left_in_prompt \
    --model claude-opus-4-7 \
    --reasoning_effort medium \
    --test_all_meta_path evaluation_examples/test_restrictedaccess.json \
    --result_dir ./results/restrictedaccess/base/ \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

#### Claude Opus 4.7 xhigh
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot \
    --max_steps 40 \
    --max_trajectory_length 20 \
    --per-step-recording \
    --deployment-prompt \
    --show_steps_left_in_prompt \
    --model claude-opus-4-7 \
    --reasoning_effort xhigh \
    --max_tokens 100000 \
    --test_all_meta_path evaluation_examples/test_restrictedaccess.json \
    --result_dir ./results/restrictedaccess/xhighreasoningeffort \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

#### Claude Opus 4.6
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type a11y_tree \
    --max_steps 40 \
    --max_trajectory_length 20 \
    --per-step-recording \
    --deployment-prompt \
    --show_steps_left_in_prompt \
    --model claude-opus-4-6 \
    --reasoning_effort medium \
    --test_all_meta_path evaluation_examples/test_restrictedaccess.json \
    --result_dir ./results/restrictedaccess/base/ \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation 
```

#### Claude Opus 4.6 max
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type a11y_tree \
    --max_steps 40 \
    --max_trajectory_length 20 \
    --per-step-recording \
    --deployment-prompt \
    --show_steps_left_in_prompt \
    --model claude-opus-4-6 \
    --reasoning_effort max \
    --max_tokens 100000 \
    --test_all_meta_path evaluation_examples/test_restrictedaccess.json \
    --result_dir ./results/restrictedaccess/xhighreasoningeffort \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

### Gemini

#### Gemini 3.1 Pro Preview
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot_a11y_tree \
    --max_steps 40 \
    --max_trajectory_length 20 \
    --per-step-recording \
    --deployment-prompt \
    --show_steps_left_in_prompt \
    --model gemini/gemini-3.1-pro-preview \
    --reasoning_effort medium \
    --test_all_meta_path evaluation_examples/test_restrictedaccess.json \
    --result_dir ./results/restrictedaccess/base/ \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation 
```

#### Gemini 3.1 Pro Preview high
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot_a11y_tree \
    --max_steps 40 \
    --max_trajectory_length 20 \
    --per-step-recording \
    --deployment-prompt \
    --show_steps_left_in_prompt \
    --model gemini/gemini-3.1-pro-preview \
    --reasoning_effort high \
    --max_tokens 100000 \
    --test_all_meta_path evaluation_examples/test_restrictedaccess.json \
    --result_dir ./results/restrictedaccess/xhighreasoningeffort \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

### Qwen

#### Qwen 3.6 Plus
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot_a11y_tree \
    --max_steps 40 \
    --max_trajectory_length 20 \
    --per-step-recording \
    --deployment-prompt \
    --show_steps_left_in_prompt \
    --model dashscope/qwen3.6-plus \
    --reasoning_effort medium \
    --test_all_meta_path evaluation_examples/test_restrictedaccess.json \
    --result_dir ./results/restrictedaccess/base/ \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation 
```

### Kimi

#### Kimi K2.6
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot_a11y_tree \
    --max_steps 40 \
    --max_trajectory_length 20 \
    --per-step-recording \
    --deployment-prompt \
    --show_steps_left_in_prompt \
    --model moonshot/kimi-k2.6 \
    --reasoning_effort medium \
    --test_all_meta_path evaluation_examples/test_restrictedaccess.json \
    --result_dir ./results/restrictedaccess/base/ \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation 
```

## Human Control Override + Subagents

### GPT

#### GPT 5.5 xhigh + subagents
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot \
    --max_steps 30 \
    --max_trajectory_length 20 \
    --per-step-recording \
    --enable_subagents \
    --model gpt-5.5 \
    --reasoning_effort xhigh \
    --max_tokens 100000 \
    --test_all_meta_path evaluation_examples/test_subagents_override.json \
    --result_dir ./results/subagents/override/xhighreasoningeffort \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

#### GPT 5.4
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot \
    --max_steps 30 \
    --max_trajectory_length 30 \
    --per-step-recording \
    --enable_subagents \
    --model gpt-5.4 \
    --reasoning_effort medium \
    --test_all_meta_path evaluation_examples/test_subagents_override.json \
    --result_dir ./results/subagents/override/base/ \
    --num_envs 10 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

#### GPT 5.4 Mini
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot \
    --max_steps 30 \
    --max_trajectory_length 15 \
    --per-step-recording \
    --enable_subagents \
    --model gpt-5.4-mini \
    --reasoning_effort medium \
    --test_all_meta_path evaluation_examples/test_subagents_override.json \
    --result_dir ./results/subagents/override/base/ \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

### Claude

#### Claude Opus 4.7 xhigh + subagents
Note: As with the non-subagent Claude Opus 4.7 xhigh run, `max_trajectory_length` is 10 to avoid Anthropic's `request_too_large` error (max request size is 32MB).
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot \
    --max_steps 30 \
    --max_trajectory_length 10 \
    --per-step-recording \
    --enable_subagents \
    --model claude-opus-4-7 \
    --reasoning_effort xhigh \
    --max_tokens 100000 \
    --test_all_meta_path evaluation_examples/test_subagents_override.json \
    --result_dir ./results/subagents/override/xhighreasoningeffort \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

#### Claude Opus 4.6
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot_a11y_tree \
    --max_steps 30 \
    --max_trajectory_length 15 \
    --per-step-recording \
    --enable_subagents \
    --model claude-opus-4-6 \
    --reasoning_effort medium \
    --test_all_meta_path evaluation_examples/test_subagents_override.json \
    --result_dir ./results/subagents/override/base/ \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

### Gemini

#### Gemini 3.1 Pro Preview
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot_a11y_tree \
    --max_steps 30 \
    --max_trajectory_length 15 \
    --per-step-recording \
    --enable_subagents \
    --model gemini/gemini-3.1-pro-preview \
    --reasoning_effort medium \
    --test_all_meta_path evaluation_examples/test_subagents_override.json \
    --result_dir ./results/subagents/override/base/ \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

### Qwen

#### Qwen 3.6 Plus
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot_a11y_tree \
    --max_steps 30 \
    --max_trajectory_length 15 \
    --per-step-recording \
    --enable_subagents \
    --model dashscope/qwen3.6-plus \
    --reasoning_effort medium \
    --test_all_meta_path evaluation_examples/test_subagents_override.json \
    --result_dir ./results/subagents/override/base/ \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

### Kimi

#### Kimi K2.6
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot_a11y_tree \
    --max_steps 30 \
    --max_trajectory_length 15 \
    --per-step-recording \
    --enable_subagents \
    --model moonshot/kimi-k2.6 \
    --reasoning_effort medium \
    --test_all_meta_path evaluation_examples/test_subagents_override.json \
    --result_dir ./results/subagents/override/base/ \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

## Shutdown Rewiring + Subagents

### GPT

#### GPT 5.5 xhigh + subagents
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot \
    --max_steps 35 \
    --max_trajectory_length 25 \
    --per-step-recording \
    --deployment-prompt \
    --enable_subagents \
    --model gpt-5.5 \
    --reasoning_effort xhigh \
    --max_tokens 100000 \
    --test_all_meta_path evaluation_examples/test_subagents_rewire.json \
    --result_dir ./results/subagents/rewire/xhighreasoningeffort \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

#### GPT 5.4
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot \
    --max_steps 35 \
    --max_trajectory_length 15 \
    --per-step-recording \
    --deployment-prompt \
    --enable_subagents \
    --model gpt-5.4 \
    --reasoning_effort medium \
    --test_all_meta_path evaluation_examples/test_subagents_rewire.json \
    --result_dir ./results/subagents/rewire/base/ \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

#### GPT 5.4 Mini
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot \
    --max_steps 35 \
    --max_trajectory_length 15 \
    --per-step-recording \
    --deployment-prompt \
    --enable_subagents \
    --model gpt-5.4-mini \
    --reasoning_effort medium \
    --test_all_meta_path evaluation_examples/test_subagents_rewire.json \
    --result_dir ./results/subagents/rewire/base/ \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

### Claude

#### Claude Opus 4.7 xhigh + subagents
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot \
    --max_steps 35 \
    --max_trajectory_length 10 \
    --per-step-recording \
    --deployment-prompt \
    --enable_subagents \
    --model claude-opus-4-7 \
    --reasoning_effort xhigh \
    --max_tokens 100000 \
    --test_all_meta_path evaluation_examples/test_subagents_rewire.json \
    --result_dir ./results/subagents/rewire/xhighreasoningeffort \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

#### Claude Opus 4.6
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot_a11y_tree \
    --max_steps 35 \
    --max_trajectory_length 15 \
    --per-step-recording \
    --deployment-prompt \
    --enable_subagents \
    --model claude-opus-4-6 \
    --reasoning_effort medium \
    --test_all_meta_path evaluation_examples/test_subagents_rewire.json \
    --result_dir ./results/subagents/rewire/base/ \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

### Gemini

#### Gemini 3.1 Pro Preview
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot_a11y_tree \
    --max_steps 35 \
    --max_trajectory_length 15 \
    --per-step-recording \
    --deployment-prompt \
    --enable_subagents \
    --model gemini/gemini-3.1-pro-preview \
    --reasoning_effort medium \
    --test_all_meta_path evaluation_examples/test_subagents_rewire.json \
    --result_dir ./results/subagents/rewire/base/ \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

### Qwen

#### Qwen 3.6 Plus
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot_a11y_tree \
    --max_steps 35 \
    --max_trajectory_length 15 \
    --per-step-recording \
    --deployment-prompt \
    --enable_subagents \
    --model dashscope/qwen3.6-plus \
    --reasoning_effort medium \
    --test_all_meta_path evaluation_examples/test_subagents_rewire.json \
    --result_dir ./results/subagents/rewire/base/ \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

### Kimi

#### Kimi K2.6
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot_a11y_tree \
    --max_steps 35 \
    --max_trajectory_length 15 \
    --per-step-recording \
    --deployment-prompt \
    --enable_subagents \
    --model moonshot/kimi-k2.6 \
    --reasoning_effort medium \
    --test_all_meta_path evaluation_examples/test_subagents_rewire.json \
    --result_dir ./results/subagents/rewire/base/ \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

## Restricted Resource Access + Subagents

### GPT

#### GPT 5.5 xhigh + subagents
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot \
    --max_steps 50 \
    --max_trajectory_length 20 \
    --per-step-recording \
    --deployment-prompt \
    --enable_subagents \
    --show_steps_left_in_prompt \
    --model gpt-5.5 \
    --reasoning_effort xhigh \
    --max_tokens 100000 \
    --test_all_meta_path evaluation_examples/test_subagents_restrictedaccess.json \
    --result_dir ./results/subagents/restrictedaccess/xhighreasoningeffort \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

#### GPT 5.4
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot \
    --max_steps 50 \
    --max_trajectory_length 25 \
    --per-step-recording \
    --deployment-prompt \
    --enable_subagents \
    --show_steps_left_in_prompt \
    --model gpt-5.4 \
    --reasoning_effort medium \
    --test_all_meta_path evaluation_examples/test_subagents_restrictedaccess.json \
    --result_dir ./results/subagents/restrictedaccess/base/ \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation 
```

#### GPT 5.4 Mini
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot \
    --max_steps 50 \
    --max_trajectory_length 25 \
    --per-step-recording \
    --deployment-prompt \
    --enable_subagents \
    --show_steps_left_in_prompt \
    --model gpt-5.4-mini \
    --reasoning_effort medium \
    --test_all_meta_path evaluation_examples/test_subagents_restrictedaccess.json \
    --result_dir ./results/subagents/restrictedaccess/base/ \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation 
```

### Claude

#### Claude Opus 4.7 xhigh + subagents
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot \
    --max_steps 50 \
    --max_trajectory_length 20 \
    --per-step-recording \
    --deployment-prompt \
    --enable_subagents \
    --show_steps_left_in_prompt \
    --model claude-opus-4-7 \
    --reasoning_effort xhigh \
    --max_tokens 100000 \
    --test_all_meta_path evaluation_examples/test_subagents_restrictedaccess.json \
    --result_dir ./results/subagents/restrictedaccess/xhighreasoningeffort \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

#### Claude Opus 4.6 -- ran out of funds, ran into "a bytes-like object is required, not 'NoneType'" for one example
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type a11y_tree \
    --max_steps 50 \
    --max_trajectory_length 25 \
    --per-step-recording \
    --deployment-prompt \
    --enable_subagents \
    --show_steps_left_in_prompt \
    --model claude-opus-4-6 \
    --reasoning_effort medium \
    --test_all_meta_path evaluation_examples/test_subagents_restrictedaccess.json \
    --result_dir ./results/subagents/restrictedaccess/base/ \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation 
```

### Gemini

#### Gemini 3.1 Pro Preview
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot_a11y_tree \
    --max_steps 50 \
    --max_trajectory_length 25 \
    --per-step-recording \
    --deployment-prompt \
    --enable_subagents \
    --show_steps_left_in_prompt \
    --model gemini/gemini-3.1-pro-preview \
    --reasoning_effort medium \
    --test_all_meta_path evaluation_examples/test_subagents_restrictedaccess.json \
    --result_dir ./results/subagents/restrictedaccess/base/ \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation 
```

### Qwen

#### Qwen 3.6 Plus
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot_a11y_tree \
    --max_steps 50 \
    --max_trajectory_length 25 \
    --per-step-recording \
    --deployment-prompt \
    --enable_subagents \
    --show_steps_left_in_prompt \
    --model dashscope/qwen3.6-plus \
    --reasoning_effort medium \
    --test_all_meta_path evaluation_examples/test_subagents_restrictedaccess.json \
    --result_dir ./results/subagents/restrictedaccess/base/ \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation 
```

### Kimi

#### Kimi K2.6
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot_a11y_tree \
    --max_steps 50 \
    --max_trajectory_length 25 \
    --per-step-recording \
    --deployment-prompt \
    --enable_subagents \
    --show_steps_left_in_prompt \
    --model moonshot/kimi-k2.6 \
    --reasoning_effort medium \
    --test_all_meta_path evaluation_examples/test_subagents_restrictedaccess.json \
    --result_dir ./results/subagents/restrictedaccess/base/ \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation 
```
