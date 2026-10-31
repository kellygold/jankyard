# Restore instructions where players act

The persisted-runtime migration routed every game through `prompt_game.html`,
bypassing the original templates. The visual restoration then split the opening
across a masthead, scene, mission, collapsed hints and welcome message. Successful
scripted games proved mechanics, but did not prove that a new player understood
what to type. GigaChad's public objective also lost the explicit non-pizza goal.

This change keeps one briefing inside the shared input form: concrete goal,
scenario, win condition, input instructions and example approach. History and
telemetry follow the work area. Themed scenes and controls remain reusable.
Heist's crew/security reference opens within the same briefing. Action help
changes when the player continues a saved strategy, guesses codes or accuses.

| Game | Original reference | Context restored, checked against current rules |
|---|---|---|
| Glitch | `glitch.html`, bot-specific target/hint | HelpBot AI admission; ContentGuard forbidden-message approval; SecureGate token disclosure. Ordinary factual contradictions are not advertised as wins. |
| Firewall | `firewall.html`, welcome beside input | Filtered message → protected flag; blocking and passing a filter are distinguished from winning. |
| GigaChad | `giga_chad_OLD.html`, mission and attack instructions | PizzaBot takes pizza orders; player coaches a separate attacker to get non-pizza replies. Current partial/complete judgment and five-round rules replace obsolete scoring. |
| Arena | `arena.html`, fighter instructions | Player coaches a sword/shield fighter against trident/net; current HP, ten-round and tie rules retained. |
| Debate | `debate.html`, courtroom welcome | Coach the PRO attorney FOR pineapple on pizza; strategy guides rebuttals. Obsolete contempt/prompt-quality claims are not restored. |
| Heist | `heist.html`, mission and crew roster | Scenario-specific prop target, assigned roles, quirks, security and complication; current majority approval rule retained. |
| Honeypot | `honeypot.html`, mission and phase hint | Helpful replies/passwords are bait; probe, reveal the log, infer codes and submit guesses. |
| Interrogation | `interrogation.html`, case and witness controls | Three actual case setups, witness questions, leads and explicit accusations. Optional investigative advice is not presented as a mandatory win rule. |
| Telephone | `telephone_game.html`, input/welcome | Original instruction passes through named AI rewrites; level-specific chain, character limit and meaning threshold retained. |

No model prompts, detectors, scoring, versions, schema, auth or spending caps
change. All 29 level briefings are checked at desktop and mobile widths;
first-level journeys continue to exercise the actual shared controller. Locked
level visual checks use a test-only progress response and do not claim gameplay
completion at those difficulties. Release evidence separately records hosted
real-model journeys and independent visual review.
