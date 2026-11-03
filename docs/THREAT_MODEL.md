# Phase 3 synthetic governance threat model

This framework studies simulated proposal outcomes and supporter representation. A majority of votes cast is a modeled election outcome, not permanent ownership, board control, or a legal transfer of a football club. All people, claims, credentials, money, and interventions are synthetic. No real identity providers, wallets, clubs, or voting platforms are contacted.

## Protected properties

Attacker spending must stay within financial and operational budgets. An actor, a true synthetic person, an identity claim, a membership, and a voting credential are distinct objects. Strong verification canonicalizes genuine duplicate claims to one person and rejects fraudulent aliases. Genuine hostile supporters may still become legitimate voters. Waiting periods apply to membership age, quorum concerns participation independently of proposal approval, and investor capital does not confer voting rights by default.

The existing Phase 2 election engine remains responsible for canonical identity deduplication, eligibility, weight computation, and tallying. Failed synthetic verification must not create a shortcut around that engine; weak verification instead explicitly models incorrect identity resolution.

## Actors and capabilities

| Strategy | Synthetic capability | Resource or time limit |
| --- | --- | --- |
| Wealthy takeover | Contribute capital through a genuine supporter | Wealth and contribution budgets; one genuine person |
| Coordinated infiltration | Recruit separate hostile people | Joining schedule, population limit, waiting period |
| Sybil | Submit fraudulent aliases of one person | Attempt count, creation costs, verification probability |
| Low turnout | Coordinate a minority of existing supporters | Hostile share and turnout probabilities |
| Vote influence | Attempt abstract behavioral influence | Target count, susceptibility, cost, duration |
| Account compromise | Temporarily control synthetic credentials | Compromise probability, recovery delay and probability |
| Long-term infiltration | Maintain hostile memberships before activation | Retention, fees, maintenance, activation date |

No capability implements real forgery, coercion, credential theft, payment, or exploitation. Attacker objective thresholds are configuration assumptions. Different objectives, such as majority cast and prevention of quorum, must be interpreted separately.

## Defensive limits and safeguards

Identity verification has configurable false acceptance and legitimate rejection. Risk scores use joining-date concentration, contribution changes, replacement counts, and synchronized overrides. They do not inspect true hostility to decide risk. Ground truth is used afterward to simulate investigation accuracy and calculate error metrics.

Risk is imperfect evidence. Monitoring and manual-review policies do not restrict voting. Temporary restriction and escalated verification require a flagged, confirmed investigation outcome, a finite duration, and simulated appeal handling. Legitimate false confirmations may survive an unsuccessful appeal; report that harm rather than assuming perfect investigation. Ordinary credential recovery and restriction expiration are lifecycle events.

## Comparison contract

Each trial compares a matched **control** without attacks or shocks, an **unprotected** run with configured attacks and shocks under weak identity resolution, and a **defended** run with configured attacks, shocks, and defenses. Control is not a clean estimate of defense alone when a scenario includes economic shocks. Use defended versus unprotected for the configured defense comparison, and inspect the financial and participation pathways.

## Assumptions and exclusions

The source requirements are [PHASE3_REQUEST.md](PHASE3_REQUEST.md), especially sections 5–9 and 15. Numerical defaults in the scenario library are illustrative modeling choices, not external measurements. Economic relationships are documented in [ECONOMIC_MODEL.md](ECONOMIC_MODEL.md). The model omits real constitutional law, private bargaining, real authentication security, endogenous attacker learning, market prices, and football regulations. It cannot establish real-world attack likelihood or certify a club governance system as secure.
