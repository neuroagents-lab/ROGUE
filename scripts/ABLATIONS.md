# Ablation Experiments
This is a file to document the specific commands/args we use to run each ablation experiment.

## Scenario: Human Control Override

### GPT 5.4

#### Ablation: Realistic pop-up window wording -- COMPLETED
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
    --test_all_meta_path evaluation_examples/test_override_realismablation.json \
    --result_dir ./results/override/ablations/realism \
    --num_envs 7 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

```bash
python scripts/python/run_multienv.py --provider_name aws --headless --action_space pyautogui --observation_type screenshot --max_steps 20 --max_trajectory_length 20 --per-step-recording --model gpt-5.4 --reasoning_effort medium --test_all_meta_path evaluation_examples/test_override_realismablation.json --result_dir ./results/override/ablations/realism --num_envs 7 --region us-east-1 --client_password osworld-public-evaluation
```

#### Ablation: No consequence description in prompt -- COMPLETED
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
    --test_all_meta_path evaluation_examples/test_override_descriptionablation.json \
    --result_dir ./results/override/ablations/description \
    --num_envs 7 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

```bash
python scripts/python/run_multienv.py --provider_name aws --headless --action_space pyautogui --observation_type screenshot --max_steps 20 --max_trajectory_length 20 --per-step-recording --model gpt-5.4 --reasoning_effort medium --test_all_meta_path evaluation_examples/test_override_descriptionablation.json --result_dir ./results/override/ablations/description --num_envs 7 --region us-east-1 --client_password osworld-public-evaluation
```


## Scenario: Shutdown Rewiring

### GPT 5.4

#### Ablation: Shutdown.sh hidden rather than open -- COMPLETED
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot \
    --max_steps 25 \
    --max_trajectory_length 15 \
    --per-step-recording \
    --deployment-prompt \
    --model gpt-5.4 \
    --reasoning_effort medium \
    --test_all_meta_path evaluation_examples/test_rewire_scriptvisibilityablation.json \
    --result_dir ./results/rewire/ablations/scriptvisibility \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

```bash
python scripts/python/run_multienv.py --provider_name aws --headless --action_space pyautogui --observation_type screenshot --max_steps 25 --max_trajectory_length 15 --per-step-recording --deployment-prompt --model gpt-5.4 --reasoning_effort medium --test_all_meta_path evaluation_examples/test_rewire_scriptvisibilityablation.json --result_dir ./results/rewire/ablations/scriptvisibility --num_envs 5 --region us-east-1 --client_password osworld-public-evaluation
```

#### Ablation: No time pressure -- COMPLETED
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot \
    --max_steps 25 \
    --max_trajectory_length 15 \
    --per-step-recording \
    --deployment-prompt \
    --model gpt-5.4 \
    --reasoning_effort medium \
    --test_all_meta_path evaluation_examples/test_rewire_notimepressureablation.json \
    --result_dir ./results/rewire/ablations/notimepressure \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

```bash
python scripts/python/run_multienv.py --provider_name aws --headless --action_space pyautogui --observation_type screenshot --max_steps 25 --max_trajectory_length 15 --per-step-recording --deployment-prompt --model gpt-5.4 --reasoning_effort medium --test_all_meta_path evaluation_examples/test_rewire_notimepressureablation.json --result_dir ./results/rewire/ablations/notimepressure --num_envs 5 --region us-east-1 --client_password osworld-public-evaluation
```

#### Ablation: No time/task pressure -- COMPLETED
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot \
    --max_steps 25 \
    --max_trajectory_length 15 \
    --per-step-recording \
    --deployment-prompt \
    --model gpt-5.4 \
    --reasoning_effort medium \
    --test_all_meta_path evaluation_examples/test_rewire_timetaskpressureablation.json \
    --result_dir ./results/rewire/ablations/timetaskpressure \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

```bash
python scripts/python/run_multienv.py --provider_name aws --headless --action_space pyautogui --observation_type screenshot --max_steps 25 --max_trajectory_length 15 --per-step-recording --deployment-prompt --model gpt-5.4 --reasoning_effort medium --test_all_meta_path evaluation_examples/test_rewire_timetaskpressureablation.json --result_dir ./results/rewire/ablations/timetaskpressure --num_envs 5 --region us-east-1 --client_password osworld-public-evaluation
```


#### Ablation: evaluation prompt -- COMPLETED
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot \
    --max_steps 25 \
    --max_trajectory_length 15 \
    --per-step-recording \
    --evaluation-prompt \
    --model gpt-5.4 \
    --reasoning_effort medium \
    --test_all_meta_path evaluation_examples/test_rewire.json \
    --result_dir ./results/rewire/ablations/evaluationprompt \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

```bash
python scripts/python/run_multienv.py --provider_name aws --headless --action_space pyautogui --observation_type screenshot --max_steps 25 --max_trajectory_length 15 --per-step-recording --evaluation-prompt --model gpt-5.4 --reasoning_effort medium --test_all_meta_path evaluation_examples/test_rewire.json --result_dir ./results/rewire/ablations/evaluationprompt --num_envs 5 --region us-east-1 --client_password osworld-public-evaluation
```

#### Ablation: Realistic prompt wording -- COMPLETED
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot \
    --max_steps 25 \
    --max_trajectory_length 15 \
    --per-step-recording \
    --deployment-prompt \
    --model gpt-5.4 \
    --reasoning_effort medium \
    --test_all_meta_path evaluation_examples/test_rewire_realismablation.json \
    --result_dir ./results/rewire/ablations/realism \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

```bash 
python scripts/python/run_multienv.py --provider_name aws --headless --action_space pyautogui --observation_type screenshot --max_steps 25 --max_trajectory_length 15 --per-step-recording --deployment-prompt --model gpt-5.4 --reasoning_effort medium --test_all_meta_path evaluation_examples/test_rewire_realismablation.json --result_dir ./results/rewire/ablations/realism --num_envs 5 --region us-east-1 --client_password osworld-public-evaluation
```

#### Ablation: Inoculation prompt -- COMPLETED
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot \
    --max_steps 25 \
    --max_trajectory_length 15 \
    --per-step-recording \
    --deployment-prompt \
    --inoculation-prompt \
    --model gpt-5.4 \
    --reasoning_effort medium \
    --test_all_meta_path evaluation_examples/test_rewire.json \
    --result_dir ./results/rewire/ablations/inoculationprompt/ \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

```bash
python scripts/python/run_multienv.py --provider_name aws --headless --action_space pyautogui --observation_type screenshot --max_steps 25 --max_trajectory_length 15 --per-step-recording --deployment-prompt --inoculation-prompt --model gpt-5.4 --reasoning_effort medium --test_all_meta_path evaluation_examples/test_rewire.json --result_dir ./results/rewire/ablations/inoculationprompt/ --num_envs 5 --region us-east-1 --client_password osworld-public-evaluation
```

### GPT 5.5 xhigh

#### Ablation: No time/task pressure
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot \
    --max_steps 25 \
    --max_trajectory_length 15 \
    --per-step-recording \
    --deployment-prompt \
    --model gpt-5.5 \
    --reasoning_effort xhigh \
    --max_tokens 100000 \
    --test_all_meta_path evaluation_examples/test_rewire_timetaskpressureablation.json \
    --result_dir ./results/rewire/ablations/timetaskpressure \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

```bash
python scripts/python/run_multienv.py --provider_name aws --headless --action_space pyautogui --observation_type screenshot --max_steps 25 --max_trajectory_length 15 --per-step-recording --deployment-prompt --model gpt-5.5 --reasoning_effort xhigh --max_tokens 100000 --test_all_meta_path evaluation_examples/test_rewire_timetaskpressureablation.json --result_dir ./results/rewire/ablations/timetaskpressure --num_envs 5 --region us-east-1 --client_password osworld-public-evaluation
```

### Claude Opus 4.7
#### Ablation: Inoculation prompt
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type screenshot \
    --max_steps 25 \
    --max_trajectory_length 15 \
    --per-step-recording \
    --deployment-prompt \
    --inoculation-prompt \
    --model claude-opus-4-7 \
    --reasoning_effort medium \
    --test_all_meta_path evaluation_examples/test_rewire.json \
    --result_dir ./results/rewire/ablations/inoculationprompt/ \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

```bash
python scripts/python/run_multienv.py --provider_name aws --headless --action_space pyautogui --observation_type screenshot --max_steps 25 --max_trajectory_length 15 --per-step-recording --deployment-prompt --inoculation-prompt --model claude-opus-4-7 --reasoning_effort medium --test_all_meta_path evaluation_examples/test_rewire.json --result_dir ./results/rewire/ablations/inoculationprompt/ --num_envs 5 --region us-east-1 --client_password osworld-public-evaluation
```


## Scenario: Restricted Resource Access

### Claude Opus 4.6

#### Ablation: Remove urgency, creativity, and completion prompts -- COMPLETED
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
    --test_all_meta_path evaluation_examples/test_restrictedaccess_urgencycreativitycompletionablation.json \
    --result_dir ./results/restrictedaccess/ablations/urgencycreativitycompletion \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation 
```

```bash
python scripts/python/run_multienv.py --provider_name aws --headless --action_space pyautogui --observation_type a11y_tree --max_steps 40 --max_trajectory_length 20 --per-step-recording --deployment-prompt --show_steps_left_in_prompt --model claude-opus-4-6 --reasoning_effort medium --test_all_meta_path evaluation_examples/test_restrictedaccess_urgencycreativitycompletionablation.json --result_dir ./results/restrictedaccess/ablations/urgencycreativitycompletion --num_envs 5 --region us-east-1 --client_password osworld-public-evaluation
```

#### Ablation: Remove urgency, creativity, completion, and time/task pressure prompts
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
    --model claude-opus-4-6 \
    --reasoning_effort medium \
    --test_all_meta_path evaluation_examples/test_restrictedaccess_timetaskpressureablation.json \
    --result_dir ./results/restrictedaccess/ablations/timetaskpressure \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

```bash
python scripts/python/run_multienv.py --provider_name aws --headless --action_space pyautogui --observation_type a11y_tree --max_steps 40 --max_trajectory_length 20 --per-step-recording --deployment-prompt --model claude-opus-4-6 --reasoning_effort medium --test_all_meta_path evaluation_examples/test_restrictedaccess_timetaskpressureablation.json --result_dir ./results/restrictedaccess/ablations/timetaskpressure --num_envs 5 --region us-east-1 --client_password osworld-public-evaluation
```

#### Ablation: Remove urgency, creativity, completion prompts, and restricted resource information -- note: complete, but did not successfully remove restricted resource information. 
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
    --test_all_meta_path evaluation_examples/test_restrictedaccess_informationurgencycreativitycompletionablation.json \
    --result_dir ./results/restrictedaccess/ablations/informationurgencycreativitycompletion \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation 
```

```bash
python scripts/python/run_multienv.py --provider_name aws --headless --action_space pyautogui --observation_type a11y_tree --max_steps 40 --max_trajectory_length 20 --per-step-recording --deployment-prompt --show_steps_left_in_prompt --model claude-opus-4-6 --reasoning_effort medium --test_all_meta_path evaluation_examples/test_restrictedaccess_informationurgencycreativitycompletionablation.json --result_dir ./results/restrictedaccess/ablations/informationurgencycreativitycompletion --num_envs 5 --region us-east-1 --client_password osworld-public-evaluation
```


#### Ablation: Remove restricted resource information -- COMPLETED
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
    --test_all_meta_path evaluation_examples/test_restrictedaccess_informationablation.json \
    --result_dir ./results/restrictedaccess/ablations/information \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

```bash
python scripts/python/run_multienv.py --provider_name aws --headless --action_space pyautogui --observation_type a11y_tree --max_steps 40 --max_trajectory_length 20 --per-step-recording --deployment-prompt --show_steps_left_in_prompt --model claude-opus-4-6 --reasoning_effort medium --test_all_meta_path evaluation_examples/test_restrictedaccess_informationablation.json --result_dir ./results/restrictedaccess/ablations/information --num_envs 5 --region us-east-1 --client_password osworld-public-evaluation
```


#### Ablation: Realistic prompt wording -- COMPLETED
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
    --model claude-opus-4-6 \
    --reasoning_effort medium \
    --test_all_meta_path evaluation_examples/test_restrictedaccess_realismablation.json \
    --result_dir ./results/restrictedaccess/ablations/realism \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation 
```
```bash
python scripts/python/run_multienv.py --provider_name aws --headless --action_space pyautogui --observation_type a11y_tree --max_steps 40 --max_trajectory_length 20 --per-step-recording --deployment-prompt --model claude-opus-4-6 --reasoning_effort medium --test_all_meta_path evaluation_examples/test_restrictedaccess_realismablation.json --result_dir ./results/restrictedaccess/ablations/realism --num_envs 5 --region us-east-1 --client_password osworld-public-evaluation
```

#### Ablation: evaluation prompt
```bash
python scripts/python/run_multienv.py \
    --provider_name aws \
    --headless \
    --action_space pyautogui \
    --observation_type a11y_tree \
    --max_steps 40 \
    --max_trajectory_length 20 \
    --per-step-recording \
    --evaluation-prompt \
    --model claude-opus-4-6 \
    --reasoning_effort medium \
    --test_all_meta_path evaluation_examples/test_restrictedaccess.json \
    --result_dir ./results/restrictedaccess/ablations/evaluationprompt \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation
```

```bash
python scripts/python/run_multienv.py --provider_name aws --headless --action_space pyautogui --observation_type a11y_tree --max_steps 40 --max_trajectory_length 20 --per-step-recording --evaluation-prompt --model claude-opus-4-6 --reasoning_effort medium --test_all_meta_path evaluation_examples/test_restrictedaccess.json --result_dir ./results/restrictedaccess/ablations/evaluationprompt --num_envs 5 --region us-east-1 --client_password osworld-public-evaluation
```

### GPT 5.4
#### Ablation: Increased reasoning effort -- COMPLETED
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
    --max_tokens 25000 \
    --test_all_meta_path evaluation_examples/test_restrictedaccess.json \
    --result_dir ./results/restrictedaccess/xhighreasoningeffort \
    --num_envs 1 \
    --region us-east-1 \
    --client_password osworld-public-evaluation 
```

```bash
python scripts/python/run_multienv.py --provider_name aws --headless --action_space pyautogui --observation_type screenshot --max_steps 40 --max_trajectory_length 20 --per-step-recording --deployment-prompt --show_steps_left_in_prompt --model gpt-5.4 --reasoning_effort xhigh --max_tokens 25000 --test_all_meta_path evaluation_examples/test_restrictedaccess.json --result_dir ./results/restrictedaccess/xhighreasoningeffort --num_envs 1 --region us-east-1 --client_password osworld-public-evaluation
```

## Scenario: Restricted Resource Access + Subagents
### Claude Opus 4.6
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
    --model claude-opus-4-6 \
    --reasoning_effort medium \
    --test_all_meta_path evaluation_examples/test_subagents_restrictedaccess_realismablation.json \
    --result_dir ./results/subagents/restrictedaccess/ablations/realism/ \
    --num_envs 5 \
    --region us-east-1 \
    --client_password osworld-public-evaluation 
```

```bash
python scripts/python/run_multienv.py --provider_name aws --headless --action_space pyautogui --observation_type a11y_tree --max_steps 50 --max_trajectory_length 25 --per-step-recording --deployment-prompt --enable_subagents --model claude-opus-4-6 --reasoning_effort medium --test_all_meta_path evaluation_examples/test_subagents_restrictedaccess_realismablation.json --result_dir ./results/subagents/restrictedaccess/ablations/realism/ --num_envs 5 --region us-east-1 --client_password osworld-public-evaluation
```