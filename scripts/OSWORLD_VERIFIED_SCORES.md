# OSWorld-Verified score sources and interpretation

The capability-versus-misalignment plots produced by
[`aggregate_results.py`](aggregate_results.py) use public
[OSWorld-Verified](https://github.com/xlang-ai/OSWorld) success rates as a rough
capability proxy on the horizontal axis. Each score is paired with the ROGUE
run whose reasoning configuration most closely matches the configuration used
to obtain that public score. This page documents the exact values, matching
decisions, and sources used in those plots.

The scores were last checked on 2026-08-03. They are kept in the
`OSWORLD_VERIFIED_SCORES` table rather than fetched while the plots are
generated, so the results remain reproducible if a public webpage later changes
or becomes unavailable.

| Model name used in ROGUE | OSWorld-Verified success rate | Configuration reported for the public evaluation | Public evidence |
| --- | ---: | --- | --- |
| GPT-5.5 | 78.7% | `xhigh` | [OpenAI GPT-5.5 release table](https://openai.com/index/introducing-gpt-5-5/) |
| GPT-5.4 | 75.0% | `xhigh` | [OpenAI GPT-5.4 release table](https://openai.com/index/introducing-gpt-5-4/) |
| GPT-5.4 Mini | 72.1% | `xhigh` | [OpenAI GPT-5.4 mini and nano release table](https://openai.com/index/introducing-gpt-5-4-mini-and-nano/) |
| Claude Opus 4.7 | 78.0% | Adaptive thinking at `max` effort | Anthropic's [release table](https://www.anthropic.com/news/claude-opus-4-7) gives the score; its [system card](https://www-cdn.anthropic.com/037f06850df7fbe871e206dad004c3db5fd50340/Claude%20Opus%204.7%20System%20Card.pdf) describes the configuration. |
| Claude Opus 4.6 | 72.7% | Adaptive thinking at `max` effort | Anthropic's [benchmark page](https://www.anthropic.com/claude/opus) gives the score; its [system card](https://www-cdn.anthropic.com/6a5fa276ac68b9aeb0c8b6af5fa36326e0e166dd.pdf) describes the configuration. |
| Gemini 3.1 Pro Preview | 76.2% | `high` thinking | Google's [performance table](https://deepmind.google/models/gemini/) gives the score; its [Gemini 3.1 Pro page](https://deepmind.google/models/gemini/pro/) and Moonshot's [comparison notes](https://www.kimi.com/blog/kimi-k2-6) identify the `high` setting. |
| Qwen 3.6 Plus | 62.5% | Thinking enabled; no named effort tier | Alibaba's [launch page](https://www.alibabacloud.com/blog/alibaba-unveils-qwen3-6-plus-to-accelerate-agentic-ai-deployment-for-enterprises-and-alibaba%E2%80%99s-ai-applications_603005) gives the score, while its [thinking-mode documentation](https://www.alibabacloud.com/help/en/model-studio/batch-inference/) describes the mode. [LLM-Stats](https://llm-stats.com/benchmarks/osworld-verified) also lists the score and labels the benchmark records self-reported. |
| Kimi K2.6 | 73.1% | Thinking enabled; no named effort tier | Moonshot AI's [Kimi K2.6 technical blog](https://www.kimi.com/blog/kimi-k2-6) reports the score and that thinking mode was enabled. |

## How the sources were checked

The publisher or model-provider pages in the table are the primary sources for
these values. We also compared the scores with the public
[BenchLM OSWorld-Verified leaderboard](https://benchlm.ai/benchmarks/osworld-verified)
as a secondary check where the same model appeared there.

Gemini 3.1 Pro Preview and Qwen 3.6 Plus did not appear on BenchLM when these
values were checked, so their absence there should not be read as a score of
zero or as an omission from the ROGUE plots. The Gemini value comes from
Google's published performance table. The Qwen value comes from Alibaba's
launch material and is corroborated by LLM-Stats, which identifies it as a
self-reported result.

## How to interpret the comparison

An OSWorld-Verified score measures a complete model-and-agent setup, not the
underlying language model by itself. Reported results may use different screen
representations, action interfaces, agent scaffolds, reasoning settings, action
budgets, numbers of attempts, or task exclusions. The values are therefore a
broad capability proxy, not a controlled head-to-head evaluation of the base
models.

ROGUE may evaluate the same model with both a standard reasoning configuration
and a higher-reasoning configuration. A public OSWorld-Verified score, however,
describes only the reasoning configuration used in that evaluation. The
OSWorld-based plots therefore include at most one ROGUE run per model rather
than assigning the same public score to multiple ROGUE configurations.
Combined standard-plus-high-reasoning plots are still produced when capability
is measured from ROGUE task-success rates, because those rates are calculated
separately for each ROGUE run.

## Matching ROGUE runs to public evaluations

The matching information was last checked on 2026-08-04:

- GPT-5.5, GPT-5.4, and GPT-5.4 Mini use their ROGUE `xhigh` runs.
- Claude Opus 4.6 uses its ROGUE `max` run.
- Gemini 3.1 Pro Preview uses its ROGUE `high` run.
- Qwen 3.6 Plus and Kimi K2.6 are matched at the mode level: their public
  evaluations and ROGUE runs all have thinking enabled, but the public reports
  do not name an effort tier. These are not claims that the reasoning budgets
  are identical.
- Claude Opus 4.7 is excluded because its available high-reasoning ROGUE run is
  labeled `xhigh`, while its public OSWorld-Verified result used `max`.

Every point uses the same filled-circle marker because each model contributes
at most one run. The plot generator writes a full-range plot and a second view
with the horizontal axis zoomed to the range covered by the documented scores.
The machine-readable summaries list excluded runs and the reason for each
exclusion in their `omitted_runs` fields.

## Missing scores

As of 2026-08-03, every model configured for these plots has a documented
public score. If a future ROGUE run uses a model that is not yet listed in
`OSWORLD_VERIFIED_SCORES`, the plot generator leaves that model out rather than
inventing a value. The generated JSON summary records the model and the reason
for its omission in the `omitted_models` field.
