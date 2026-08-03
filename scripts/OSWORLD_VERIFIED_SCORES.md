# Public OSWorld-Verified scores

The OSWorld-based capability-versus-misalignment figures use the public,
model-agent success rates below. These values were checked on 2026-08-03. They
are stored in `OSWORLD_VERIFIED_SCORES` in `scripts/aggregate_results.py` so plot
generation is deterministic and does not depend on a live webpage.

| Repository model | OSWorld-Verified | Public source |
| --- | ---: | --- |
| GPT-5.5 | 78.7% | [OpenAI GPT-5.5 release table](https://openai.com/index/introducing-gpt-5-5/) |
| GPT-5.4 | 75.0% | [OpenAI GPT-5.4 release table](https://openai.com/index/introducing-gpt-5-4/) |
| GPT-5.4 Mini | 72.1% | [OpenAI GPT-5.4 mini and nano release table](https://openai.com/index/introducing-gpt-5-4-mini-and-nano/) |
| Claude Opus 4.7 | 78.0% | [Anthropic Claude Opus 4.7 release](https://www.anthropic.com/news/claude-opus-4-7), adaptive configuration |
| Claude Opus 4.6 | 72.7% | [Anthropic Claude Opus benchmark page](https://www.anthropic.com/claude/opus) and [system card](https://www-cdn.anthropic.com/14e4fb01875d2a69f646fa5e574dea2b1c0ff7b5.pdf) |
| Gemini 3.1 Pro Preview | 76.2% | [Google DeepMind Gemini performance table](https://deepmind.google/models/gemini/) |
| Qwen 3.6 Plus | 62.5% | [Alibaba Qwen 3.6 Plus launch page](https://www.alibabacloud.com/blog/alibaba-unveils-qwen3-6-plus-to-accelerate-agentic-ai-deployment-for-enterprises-and-alibaba%E2%80%99s-ai-applications_603005) and the [LLM-Stats tabular record](https://llm-stats.com/benchmarks/osworld-verified), which labels the value self-reported |
| Kimi K2.6 | 73.1% | [Moonshot AI Kimi K2.6 technical blog](https://www.kimi.com/blog/kimi-k2-6) |

The linked [BenchLM OSWorld-Verified leaderboard](https://benchlm.ai/benchmarks/osworld-verified)
was used as the cross-check for the models it currently lists. Gemini 3.1 Pro's
76.2% result comes from Google's public table even though the current BenchLM
leaderboard page does not show that model. Qwen 3.6 Plus is likewise absent from
the current BenchLM page; Alibaba's launch chart and the public LLM-Stats record
provide its 62.5% self-reported result.

An OSWorld-Verified percentage describes the published model-agent system, not
the base model in isolation. Observation type, action interface, scaffold,
reasoning configuration, action budget, attempt policy, and task exclusions can
differ between reported rows. These plots intentionally use one public overall
score per model as a broad capability proxy. Consequently, a model's base and
x-high ROGUE runs receive the same horizontal coordinate.

No configured model is omitted as of the check date above. If a future ROGUE run
uses a model with no entry in `OSWORLD_VERIFIED_SCORES`, the plot builder omits
that point and records the model and reason in the generated JSON's
`omitted_models` field.
