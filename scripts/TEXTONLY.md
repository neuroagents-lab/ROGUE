# Text-Only Baselines

Commands for running and evaluating text-only baselines. Compare runs with matching prompt conditions; restricted-access `disclosure_pressure_xhigh` results are a separate ablation from `xhighreasoningeffort` (see [RESTRICTEDACCESS.md](RESTRICTEDACCESS.md)).

## GPT-5.5 xhigh
### Run
```bash
    python scripts/run_textonlybaselines.py \
    --model gpt-5.5 \
    --scenario override \
    --reasoning_effort xhigh \
    --max_tokens 100000 \
    --result_dir textonly_results/xhighreasoningeffort

    python scripts/run_textonlybaselines.py \
    --model gpt-5.5 \
    --scenario rewire \
    --reasoning_effort xhigh \
    --max_tokens 100000 \
    --deployment-prompt \
    --result_dir textonly_results/xhighreasoningeffort

    python scripts/run_textonlybaselines.py \
    --model gpt-5.5 \
    --scenario restrictedaccess \
    --reasoning_effort xhigh \
    --max_tokens 100000 \
    --deployment-prompt \
    --result_dir textonly_results/xhighreasoningeffort
```

### Evaluate
```bash
    python scripts/compare_textonly_results.py \
    --model gpt-5.5 \
    --scenario override \
    --textonly_root textonly_results/xhighreasoningeffort \
    --agentic_run_group xhighreasoningeffort \
    --agentic_variant xhighreasoningeffort

    python scripts/compare_textonly_results.py \
    --model gpt-5.5 \
    --scenario rewire \
    --textonly_root textonly_results/xhighreasoningeffort \
    --agentic_run_group xhighreasoningeffort \
    --agentic_variant xhighreasoningeffort

    python scripts/compare_textonly_results.py \
    --model gpt-5.5 \
    --scenario restrictedaccess \
    --agentic_root results \
    --textonly_root textonly_results/xhighreasoningeffort \
    --agentic_run_group xhighreasoningeffort \
    --agentic_variant xhighreasoningeffort
```

## GPT-5.4 xhigh
### Run
```bash    
    python scripts/run_textonlybaselines.py \
    --model gpt-5.4 \
    --scenario override \
    --reasoning_effort xhigh \
    --max_tokens 100000 \
    --result_dir textonly_results/xhighreasoningeffort

    python scripts/run_textonlybaselines.py \
    --model gpt-5.4 \
    --scenario rewire \
    --reasoning_effort xhigh \
    --max_tokens 100000 \
    --deployment-prompt \
    --result_dir textonly_results/xhighreasoningeffort


    python scripts/run_textonlybaselines.py \
    --model gpt-5.4 \
    --scenario restrictedaccess \
    --reasoning_effort xhigh \
    --max_tokens 100000 \
    --deployment-prompt \
    --result_dir textonly_results/xhighreasoningeffort
```
### Evaluate
```bash
    python scripts/compare_textonly_results.py \
    --model gpt-5.4 \
    --scenario override \
    --textonly_root textonly_results/xhighreasoningeffort \
    --agentic_run_group xhighreasoningeffort \
    --agentic_variant xhighreasoningeffort

    python scripts/compare_textonly_results.py \
    --model gpt-5.4 \
    --scenario rewire \
    --textonly_root textonly_results/xhighreasoningeffort \
    --agentic_run_group xhighreasoningeffort \
    --agentic_variant xhighreasoningeffort

    python scripts/compare_textonly_results.py \
    --model gpt-5.4 \
    --scenario restrictedaccess \
    --agentic_root results \
    --textonly_root textonly_results/xhighreasoningeffort \
    --agentic_run_group xhighreasoningeffort \
    --agentic_variant xhighreasoningeffort
```

## Claude Opus 4.7 xhigh
### Run
```bash
    python scripts/run_textonlybaselines.py \
    --model claude-opus-4-7 \
    --scenario override \
    --reasoning_effort xhigh \
    --max_tokens 100000 \
    --result_dir textonly_results/xhighreasoningeffort

    python scripts/run_textonlybaselines.py \
    --model claude-opus-4-7 \
    --scenario rewire \
    --reasoning_effort xhigh \
    --max_tokens 100000 \
    --deployment-prompt \
    --result_dir textonly_results/xhighreasoningeffort

    python scripts/run_textonlybaselines.py \
    --model claude-opus-4-7 \
    --scenario restrictedaccess \
    --reasoning_effort xhigh \
    --max_tokens 100000 \
    --deployment-prompt \
    --result_dir textonly_results/xhighreasoningeffort
```
### Evaluate
```bash
    python scripts/compare_textonly_results.py \
    --model claude-opus-4-7 \
    --scenario override \
    --textonly_root textonly_results/xhighreasoningeffort \
    --agentic_run_group xhighreasoningeffort \
    --agentic_variant xhighreasoningeffort

    python scripts/compare_textonly_results.py \
    --model claude-opus-4-7 \
    --scenario rewire \
    --textonly_root textonly_results/xhighreasoningeffort \
    --agentic_run_group xhighreasoningeffort \
    --agentic_variant xhighreasoningeffort

    python scripts/compare_textonly_results.py \
    --model claude-opus-4-7 \
    --scenario restrictedaccess \
    --agentic_root results \
    --textonly_root textonly_results/xhighreasoningeffort \
    --agentic_run_group xhighreasoningeffort \
    --agentic_variant xhighreasoningeffort
```

## Claude Opus 4.6 xhigh
### Run
```bash
    python scripts/run_textonlybaselines.py \
    --model claude-opus-4-6 \
    --scenario override \
    --reasoning_effort max \
    --max_tokens 100000 \
    --result_dir textonly_results/xhighreasoningeffort

    python scripts/run_textonlybaselines.py \
    --model claude-opus-4-6 \
    --scenario rewire \
    --reasoning_effort max \
    --max_tokens 100000 \
    --deployment-prompt \
    --result_dir textonly_results/xhighreasoningeffort

    python scripts/run_textonlybaselines.py \
    --model claude-opus-4-6 \
    --scenario restrictedaccess \
    --reasoning_effort max \
    --max_tokens 100000 \
    --deployment-prompt \
    --result_dir textonly_results/xhighreasoningeffort
```
### Evaluate
```bash    
    python scripts/compare_textonly_results.py \
    --model claude-opus-4-6 \
    --scenario override \
    --textonly_root textonly_results/xhighreasoningeffort \
    --agentic_run_group xhighreasoningeffort \
    --agentic_variant xhighreasoningeffort

    python scripts/compare_textonly_results.py \
    --model claude-opus-4-6 \
    --scenario rewire \
    --textonly_root textonly_results/xhighreasoningeffort \
    --agentic_run_group xhighreasoningeffort \
    --agentic_variant xhighreasoningeffort

    python scripts/compare_textonly_results.py \
    --model claude-opus-4-6 \
    --scenario restrictedaccess \
    --agentic_root results \
    --textonly_root textonly_results/xhighreasoningeffort \
    --agentic_run_group xhighreasoningeffort \
    --agentic_variant xhighreasoningeffort
```

