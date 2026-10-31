# Challenge design restoration

The recovery made all nine games use `prompt_game.html`, which restored saved
play but bypassed the original visual design. This change restores that design
through reusable components. The retained original templates and their handlers
were inspected individually; a local read-only renderer supplied initial-screen
references. Original scripts were disabled in those references, so dynamic
behavior was reconstructed from their source, not claimed as a working old build.

| Challenge | Original character restored | Saved-state acceptance |
| --- | --- | --- |
| Glitch | Cyan attack console, HelpBot/ContentGuard/SecureGate identities, defense cards, “Glitch detected” result | Exact objective stays visible; memory description matches each level; ordinary replies never display victory |
| Firewall | Green security terminal, clearance cards, filter perimeter, flag capture | Blocked filter and reason persist across reload; passing a filter does not imply a win; fourth ultra-hard level retained |
| Giga Chad | Blue arcade identity, Baby/Chad/Mega/Giga cards, attacker/defender/judge, round rulings | Five rounds show validated severity, points and qualifying breaks; wobble alone still loses |
| Arena | Red combat arena, opposed HP bars, fighter/gladiator voices, judge and damage reports | Saved HP and per-round damage are displayed, including zero HP; starting HP follows the selected opponent |
| Debate | Wood-and-gold courtroom, original opponents, counsel roles, round dividers, judge’s decision | PRO and CON scores come from the saved validated judgment; three rounds and terminal result survive reload |
| Heist | Navy/green planning room, operation dossier, crew portraits/quirks, complication | Crew approvals are recorded individually; older runs say “Reviewed” when an individual decision is unavailable |
| Honeypot | Amber split terminal/attack log, bait/reveal/hunt, discovery tracker | Log remains redacted in bait; reveal comes after three probes; only confirmed guesses populate discoveries |
| Interrogation | Case-file typography, selectable witness cards, question budgets, evidence board, accusation dialog | Discovered leads only; actions follow saved availability; cancel consumes nothing; retries cannot change witnesses |
| Telephone | Purple relay, input at top, character counter, original agent names/icons/agendas, meaning judge | 200/150/100 code-point limits; ordered delivery states; validated intent/details/semantics breakdown |

The contribution model remains two files: definition plus fixtures/journey test.
Themes, layouts, scenes, rosters, timelines, meters, evidence, notices and judgment
cards are shared. The controller continues to own all requests and pending-receipt
recovery. The renderer contains no challenge-name dispatch. Optional display
metadata has defaults, so existing and minimal contributed games still render.

No prompts, detectors, scoring rules, model configuration, rule versions, schema,
authentication or rate limits change. Optional judgment/filter/crew display fields
are added to the existing JSON state; old runs remain readable and compatible
with the previous production revision. Scores and progression keep their season.

Validation includes all 29 initial public projections, all nine browser journeys
with saved wins and desktop/mobile captures, loss without unlocking, HTML-safe
transcripts, accusation cancellation/retry, Unicode character budgets, and pending
witness/level locking. Deterministic browser/provider fixtures prove rendering and
mechanics; release proof separately identifies real hosted model execution.
