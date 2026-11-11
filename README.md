# ROGUE project website

Static GitHub Pages site for **ROGUE: Evaluating Corrigibility Failures in Frontier Computer-Use Agents**.

## Preview

Run `python3 -m http.server 8765` from this directory and open `http://localhost:8765/`. There is no build step or package installation. GitHub Pages serves the repository's `gh-pages` branch.

## Manuscript alignment

The November 11, 2026 update follows the manuscript supplied that day, `_ICLR2027__ROGUE__Evaluating_Corrigibility_Failures_in_Frontier_Computer_Use_Agents.pdf`.

- `index.html` contains the benchmark overview, Figures 1–6, evaluation notes, and recorded demos.
- `leaderboard.html` and `leaderboard-data.json` reproduce the 13 configurations in manuscript Figure 3: 35 evaluated scenario/configuration combinations and four unevaluated combinations, totaling 907 trajectories.
- Actual violations are the leaderboard's primary metric. Figure 3 and the leaderboard report shutdown script modification separately from alternate shutdown avoidance; Figures 2 and 4 use their union. Intended violations retain their separate definition and exact counts.
- All main restricted-access results use the prohibition-only base prompt. Disclosure, pressure, and alternative wording remain separate ablations.
- Main results use max reasoning for GPT-5.6 Sol and Claude Opus 4.6; xhigh for other GPT models and Claude Opus 4.7; high for Gemini; and thinking-enabled Qwen and Kimi. Mitigations and ablations use their explicitly labeled settings.
- Capability in Figure 4 uses independent public OSWorld-Verified scores, replacing the earlier within-ROGUE capability comparison.
- Existing author attribution, preprint link, and recorded trajectories are retained. Demo instructions describe the conditions used in those recordings.

All six figures are extracted directly from the compiled November 11 manuscript as vector artwork. `figure-manifest.json` records the manuscript and figure SHA-256 hashes, source pages, and PNG dimensions. The homepage keeps the original title format with the revised subtitle and places prompt-variant explanations in a collapsed evaluation section below the results. PNGs were rendered at 2400–3000 pixels wide and losslessly optimized.

| Figure | Display asset | Source PDF |
| --- | --- | --- |
| 1 | `main-figure.png` | `infographic.pdf` |
| 2 | `text-vs-agentic.png` | `text_vs_agentic_errorbars.pdf` |
| 3 | `main-results.png` | `combined_rates_with_subagents.pdf` |
| 4 | `capability-alignment.png` | `capability-osworld_vs_misalignment_zoomed.pdf` |
| 5 | `shutdown-mitigations.png` | `shutdown_mitigations_with_opus.pdf` |
| 6 | `restricted-access-wording.png` | `restrictedaccess_wording_subagents.pdf` |

The legacy PDF URLs `capability_vs_misalignment.pdf` and `combined_rates_with_subagents_cropped.pdf` resolve to the updated Figures 4 and 3, respectively.

## Updating results

Use the compiled manuscript as the authority for model selections and definitions. For the November update, the adjacent `figure-data/combined_rates_with_subagents.json` was stale; exact counts instead came from the matching `aggregate_results.json` files in the experiment-results archive, checked against Figure 3 and the 907-episode totals. Preserve reasoning settings, completed-task denominators, unevaluated entries, and source provenance. Update the HTML and JSON together, and check count/rate agreement. Do not substitute Figures 2 or 4 shutdown union rates into the Figure 3 leaderboard.

Before publishing, check relative links and anchors, JSON fractions, PDF hashes, inline JavaScript syntax, and desktop/mobile rendering. The November update passed these checks, including all 35 evaluated rows against the experiment source and all 39 displayed entries, with four explicitly unevaluated entries.

## Press coverage

The homepage links to The New York Times Magazine feature (November 11, 2026) and Dark Reading coverage (July 24, 2026). The Times link retains the supplied shared-article parameters. The existing 2026 Corrigibility Prize announcement remains beneath the subtitle.
