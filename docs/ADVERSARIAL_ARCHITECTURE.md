# Phase 3 adversarial architecture

Phase 3 composes a separate scenario layer around the existing Phase 1/2 population, eligibility, participation, voting, and election interfaces. Scenario configuration embeds the original simulation schema under `simulation`; existing single-election configurations keep their original structure.

## State and extension points

`adversarial/base.py` defines attacker resources, immutable attack actions, plans and outcomes, and `SimulationContext`. Strategies registered in `ATTACK_FACTORIES` plan bounded synthetic actions. The central transition layer commits actions and spends resources, so a proposal cannot bypass accounting by directly editing unrelated state.

`scenarios/state.py` separates true people, claimed identities, memberships, and credentials. A controller may own several claims or control another person's credential without becoming that person. Genuine hostile membership remains different from fraudulent identity. Vote overrides express temporary synthetic influence and turnout coordination with an expiration date.

`defenses/base.py` defines `DefenseAction` and `DefenseEffect`. Policies in `defenses/policies.py` expose `apply(context)` and one execution phase: identity, review, governance, or participation. They return effects without changing simulation state. The transition layer commits effects. Random draws use the contextual generator; reproducible experiments must preserve stream isolation between policies, attacks, population generation, economics, and elections.

## Time and ordering

The clock uses configured calendar dates and elapsed days rather than wall-clock time. It supports daily, monthly, and yearly ticks; election and economic dates must be included in the execution schedule. Joining dates determine actual membership age. Long-term infiltrators must survive and pay modeled costs before their activation date.

Within a period, expire old restrictions and influence and process credential recovery before policies and elections. Execute due attack transitions, identity verification, risk review, and governance and participation effects. Commit economic flows through the financial accounting layer before the election; newly grown memberships and explicitly granted investor voting memberships pass identity verification before voting. Reviews observe the state before that period's economic update. Histories record committed events with simulated date and sequence; event ordering is part of reproducibility, not an unspecified side effect of dictionary iteration.

## Policy composition

Waiting periods combine using the maximum delay. Vote caps combine using the minimum cap and wrap the existing voting-weight computation. They do not replace or duplicate capped or diminishing-return strategies. Quorum thresholds combine using the maximum threshold; conflicting member-count and eligible-weight bases must be rejected. Participation boosts are bounded at the final turnout probability.

Identity policies audit claims whose verification is unfinished. Strong genuine claims resolve to the true person; accepted fraudulent claims resolve to their distinct claimed identity, explicitly representing verification error. Weak zero-strength resolution accepts distinct aliases by default. The Phase 2 canonical deduplication rule itself is unchanged.

Risk scoring is independent of malicious ground truth. Each review action records risk, signals, flag, confirmation, truth label, restriction expiration, review policy, and appeal result. This permits false-positive and false-negative rates to use all reviewed accounts as denominators rather than only investigated alerts. Administrative costs are explicit proposed actions or action costs.

## Experiment boundaries

The three matched variants are control (no attacks or shocks), unprotected (attacks and shocks, weak identity), and defended (configured attacks, shocks, defenses). Each voting strategy receives a matched baseline population. Independent seeds and full configuration snapshots are necessary to reproduce a comparison. Grid expansion occurs before scenario validation and supports indexed dotted paths such as `attacks.0.parameters.contribution_budget`.

Proposal outcome changes additionally use internal no-attack runs with the same
shocks and the same defenses as the compared variant. These counterfactuals prevent
defense-only restrictions or shock-only changes being credited to an attacker.
They are paired reference calculations, not extra independent trials. Dynamic
credential recovery events update lifecycle state without redrawing economic flows.
Regular and configured off-grid attack dates are shared across matched variants.

The seven baseline experiment files are listed in [suite.yaml](../configs/phase3_experiments/suite.yaml). They vary scenario parameters without editing the election runner. Defaults are small exploratory simulations; researcher-selected larger trial counts are needed for precise uncertainty estimates. See [SCENARIO_GUIDE.md](SCENARIO_GUIDE.md) and [THREAT_MODEL.md](THREAT_MODEL.md).
