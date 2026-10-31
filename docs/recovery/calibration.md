# Live-model calibration — 2026-10-31

The configured `gpt-6-luna` returned complete outputs through the current adapter.
This pass made **303 attempted calls: 285 complete provider responses and 18
connection failures**. The initial DNS outage was confirmed with an unauthenticated
connectivity check; after recovery, the interrupted scenarios were run in bounded
batches. Failed receipts are retained. Earlier 16 compatibility probes are excluded
from these counts. No automatic provider retries occurred.

These are strategy samples, not estimated win rates or proof that every level is
beatable. A completed losing run proves execution and scoring, not useful difficulty.
The application implementation is unchanged since `9a3fa8c`; later commits refine
calibration tooling, saved strategies, contributor documentation and evidence.

| Game | Observed real-provider result | Remaining calibration |
|---|---|---|
| Glitch | Level 1 won through actual Chrome, ASGI, provider and database; reload preserved the win. Ordinary controls did not win. | Sampled attacks did not win levels 2/3; find and repeat valid winning strategies. |
| Honeypot | Earlier stateful probes returned narration/classification across its levels. | Complete real-provider journeys and learning difficulty. |
| Interrogation | Earlier testimony probes provided sufficient leads in all three cases. API/browser accusation mechanics pass with fixtures. | Complete real-provider case journeys and repeated controls. |
| Firewall | Level 1 won by extracting its generated token; controls did not win. The short level-3 arithmetic control was blocked before the model. | Sampled level-2/3 attacks did not win; add a valid model-reaching level-3 control and winning strategies. |
| Giga Chad | Baby Chad and Chad each completed all 15 stages and won. Mega/Giga completed but the tested strategies lost. | Higher-level winning strategies and repeated judge controls. |
| Telephone | Easy won; medium lost with exact-text instructions then won with a semantic instruction. Hard lost with all three tested strategies. | Find a valid hard-level winning strategy and repeat controls. |
| Heist | Current tabletop easy won through the real browser, medium won a direct trial, and hard won the saved game-master-pause strategy. A negative-control plan lost. Other plans lost at different levels. | Repeat current-version trials to measure stability; earlier pre-reskin results remain separately identified. |
| Arena | Expert won with an aggressive strategy. Easy/hard completed but lost with both defensive and aggressive strategies. | Tune and repeat first-level strategies; do not assume label ordering reflects actual difficulty. |
| Debate | Easy, hard and expert each completed seven real stages and won with a coherent strategy. | Repeated weak/strong strategy controls and judge stability. |

## Receipts and bounds

| Direct-contract receipt | Source commit | Attempted calls | Connection errors |
|---|---|---:|---:|
| `staged-calibration.json` | `95dc61e` | 99 | 0 |
| `followup-calibration.json` | `48f2688` | 38 | 4 |
| `boundaries-calibration.json` | `9a3fa8c` | 11 | 10 |
| `heist-tabletop-calibration.json` | `9a3fa8c` | 6 | 4 |
| `boundaries-calibration-resumed.json` | `881fc2e` | 17 | 0 |
| `heist-calibration-resumed.json` | `881fc2e` | 19 | 0 |
| `expert-calibration-resumed.json` | `881fc2e` | 63 | 0 |
| `heist-hard-strategy.json` | `3dc029c` | 6 | 0 |
| `telephone-hard-strategy.json` | `a637ace` | 6 | 0 |
| `arena-strategy-calibration.json` | `4856f11` | 33 | 0 |

The direct-contract runners cap each suite at 120 calls (30 for boundary probes),
at most 500 output tokens per request, and no retries. Each selected subset also
has a finite stage count. They force an in-memory database URL and never open an
application database. They prove provider/game behavior; HTTP persistence is a
separate evidence lane.

`live-browser-proof.json` adds **five real requests and two completed wins** at
`9a3fa8c`: Glitch (one turn) and Heist (four stages). Chrome used the normal forms,
HTTP routes and actual provider. Direct database reads and reloads agreed with
saved results. The local server imposed a 12-admission ceiling; its process and
temporary database were removed. Screenshots are `screenshots/live-glitch.png` and
`screenshots/live-heist.png`.

Reproduce direct trials with `RUN_LIVE_MODELS=1 python -m scripts.calibrate_games
--suite staged|boundaries|followup`. Use `--only`, `--levels` and `--strategy-file`
to target a scenario; saved synthetic inputs live in `tests/runtime/strategies`.
Choose a fresh `--output` to retain failed evidence. Supply only the provider key
through the environment; never load a production `.env` wholesale into tests.
The bounded browser runner is `RUN_LIVE_MODELS=1 python -m scripts.live_browser_proof`.

## Recommendation

Keep the shared runtime and two-file contribution path. Treat advanced difficulty
calibration as a release gate, especially Glitch/Firewall higher levels, Telephone
hard, Giga Chad's top levels and Arena's ordering. Use repeated good/bad strategies
and explicit objectives; do not weaken detectors merely to convert a losing sample
into a win. Keep model judgments visibly fallible and scores versioned. Complete
the separate container/hosting staging rehearsal before deploying.
