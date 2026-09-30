# ROGUE project website

Static GitHub Pages site for **ROGUE: Evaluating Corrigibility Failures in Frontier Computer-Use Agents**.

## Preview

Run `python3 -m http.server 8765` from this directory and open `http://localhost:8765/`. There is no build step or package installation. GitHub Pages serves the repository's `gh-pages` branch.

## Manuscript alignment

The September 30, 2026 update follows the September 26 manuscript, `_ICLR2027__ROGUE__Evaluating_Corrigibility_Failures_in_Frontier_Computer_Use_Agents.pdf`.

- `index.html` contains the benchmark overview, Figures 1–6, evaluation notes, and recorded demos.
- `leaderboard.html` and `leaderboard-data.json` reproduce the 13 configurations in manuscript Figure 3: 37 evaluated scenario/configuration combinations and two unevaluated combinations.
- Actual violations are the leaderboard's primary metric. Intended violations and alternate shutdown avoidance retain their separate definitions and exact counts.
- Restricted-access rows are grouped by prohibition-only or disclosure + pressure prompts. These are distinct evaluated conditions, not pooled outcomes.
- The GPT-5.5 xhigh subagent access count includes the manuscript's manual adjudication (1/8).
- Capability in Figure 4 uses independent public OSWorld-Verified scores, replacing the earlier within-ROGUE capability comparison.
- Existing author attribution, preprint link, and recorded trajectories are retained. Demo instructions describe the conditions used in those recordings.

Figures 2–6 are unchanged copies of the corresponding manuscript assets. Figure 1 is extracted directly from the compiled manuscript, which contains newer artwork than its adjacent source file. `figure-manifest.json` records their SHA-256 hashes and PNG dimensions. The homepage keeps the original title format with the revised subtitle and places prompt-variant explanations in a collapsed evaluation section below the results. PNGs were rendered at 2400–3000 pixels wide and losslessly optimized.

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

Use the manuscript's `figure-data/combined_rates_with_subagents.json` and its appendix on prompt variants as the source for Figure 3 results. Preserve configuration-specific prompt conditions and reasoning settings, completed-task denominators, unevaluated entries, and manual adjudications. Update the HTML and JSON together, and check count/rate agreement. Figure 4 and the other experiments use different selections or prompt conditions; do not substitute their values into the Figure 3 leaderboard.

Before publishing, check relative links and anchors, JSON fractions, PDF hashes, inline JavaScript syntax, and desktop/mobile rendering. The September 30 update passed these checks, including all 37 evaluated rows against the figure-data source and all 39 displayed entries in the browser.
