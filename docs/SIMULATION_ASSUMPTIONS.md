# Simulation assumptions

All outputs are synthetic. No population is calibrated to a real club, latent traits
have no empirical standing, and results do not establish whether blockchain increases
participation or prevents capture. Monetary values use arbitrary consistent units.

## People, marginals and financial constraints

`supporter_id` is canonical; `fan_id` is its constructor/read alias. `knowledge_score`
and `participation_rate` alias `knowledge` and `participation_probability`. No duplicate
trait state is stored. Loyalty/knowledge are latent assumptions; financial contribution
does not imply attachment, expertise or willingness to vote.

Default marginals are lognormal wealth (`mean=10`, `sigma=1`), independently lognormal
contribution (`mean=4`, `sigma=1.5`), uniform membership age `[0,1826)` floored to days,
Beta(3,2) loyalty/participation propensity and Beta(2,2) knowledge. Policy defaults to
`neutral`, forecasting ability is absent and forecast counts default to zero.
Adversarial labels are independent Bernoulli draws, default probability zero; they
cause no hostile behavior in Phase 2.

Supported numeric families are uniform(low,high), normal(mean,std),
lognormal(mean,sigma), beta(alpha,beta) and constant(value). Parameters describe the
underlying distribution, not realized output moments. Lognormal mean/sigma describe
the underlying natural-log normal distribution. Bounds clip sampled values, rather
than reject/resample. Domain clipping enforces nonnegative wealth/contribution/age
and [0,1] loyalty, knowledge, participation and forecast accuracy. Normal clipping
can create boundary point masses. Nonfinite draws and malformed plugin output fail.
Categorical policy probabilities must match unique categories and sum to one;
omitting probabilities uses equal category probabilities.

Default independent contribution draws are clipped to wealth. This changes their
output marginal when affordability binds. `contribution_model: wealth_fraction`
instead multiplies wealth by a separately sampled fraction in [0,1]. The default
fraction marginal is uniform [0.001,0.05); compact min/max fractions are supported.
`allow_unfunded_contributions: true`, also accepted through
`financial_mode: allow_unfunded`, explicitly permits an alternative unfunded model.
The supporter validates its trait amount; Club also validates every authoritative
membership contribution against supporter wealth unless that person's override is set.
Membership amounts may differ from the initial supporter contribution and are the
financial voting input. There is no club budget, payment ledger or currency calibration.

## Correlations

Independent sampling is the default. A Gaussian copula creates correlated latent
normal scores and reorders numeric marginal samples by rank. Configure pairs such
as `correlations: {"loyalty:participation_rate": 0.6}` or a matrix:

```yaml
correlations:
  attributes: [knowledge_score, forecast_accuracy]
  matrix: [[1, 0.7], [0.7, 1]]
```

Matrices must be finite, symmetric, unit-diagonal and positive semidefinite; names
must be distinct numeric traits. Pair mappings cannot repeat/reverse the same pair.
Coefficients describe latent Gaussian correlation, not exact output Pearson correlation.
Domain bounds, count/age flooring, affordability and wealth-fraction transformation
can introduce ties and change correlations. In fraction mode the contribution formula
replaces its independent marginal, so a requested contribution copula coefficient
should not be interpreted as the final wealth/contribution correlation.

## Forecast histories and expertise

If configured, `forecast_accuracy` is underlying synthetic success probability p.
A nonnegative floored `forecast_sample_count` draw supplies n, and correct count is
Binomial(n,p) on a separate stream. Nonempty generated histories require configured
accuracy. Counts satisfy 0 <= correct <= total, and records carry
`forecast_history_source: synthetic`. Realized correct/total need not equal p.
Raw accuracy, latent knowledge and observed counts are separate quantities.

Expertise weighting uses the Wilson lower confidence bound L for correct/total and
`reliability = max(0, min(1, (L-chance_accuracy)/(1-chance_accuracy)))`.
Default `confidence_z=1.96`, `chance_accuracy=0.5`, and `minimum_samples=20` are research
parameters. Missing/insufficient history gives reliability zero and neutral weight 1.
Weight is `1 + expertise_multiplier * reliability`, optionally capped by `max_weight`.
The default multiplier is 1. An expertise cap cannot be below 1. Neither synthetic
forecast performance nor this reliability calculation establishes governance quality.

## Membership, identity and matched behavior

Generated people start with one active, verified membership. Eligibility uses the
membership age, never the copied supporter age; equality with the waiting period
qualifies. The standard policy filters inactive/unverified/underage records and then
selects the lexically smallest eligible member ID per person. Duplicate records never
supply extra eligible votes. Canonical identity is assumed, not verified against real
people, and separate Club objects do not form a multi-club economic simulation.

Preparation evaluates eligibility once. Behavior for an eligible person uses the
selected eligible record; behavior for an ineligible person uses their lexically
first record. Turnout and preferences are drawn for every canonical person with a
membership, including nonparticipants/ineligible people, to preserve stable common
random numbers. The same frozen supporter/member records, eligibility, proposal and
realization are reused across strategies. Behavior sees neutral strategy metadata.

Default turnout is independent Bernoulli with supporter propensity, optionally replaced
by `participation.parameters.probability`. The `constant` model uses a common probability,
default 0.6. Attribute-based turnout/preference use
`logistic(intercept + sum(coefficient * supporter_attribute / scale))`, bounded to [0,1]
with stable saturation. Scales default to 1 and must be positive. Missing optional
forecast accuracy is 0.5 in these behavioral models. Coefficients are assumptions,
not estimated causal relationships. Attribute contribution uses the supporter trait.

Default synthetic binary preference uses approval probability 0.5 and abstention
probability zero; both preference variates are drawn for everyone. Policy preferences
use `proposal.metadata.policy_alignment`: a favored label, or label-to-approval-probability
mapping. String matches/mismatches default to 0.9/0.1; neutral/missing/unlisted labels
use 0.5. Abstention remains separately configurable. Knowledge never implies an
objectively correct choice; adversarial labels do not change default behavior.

## Voting formulas and compatibility

Let c be authoritative membership contribution, r the positive reference amount,
b the nonnegative baseline and M the cap. All returned weights must be finite and
nonnegative. Eligibility and turnout are separate from weight.

| Strategy | Formula and defaults |
|---|---|
| Equal | w = 1 |
| Proportional | w = c/r, default r=1 (preserves Phase 1 w=c) |
| Capped | w = min(M, b+c/r); legacy defaults M=cap=100, b=0, r=1 |
| Diminishing, legacy | w = multiplier*ln(1+c/scale), defaults multiplier=1, scale=10 |
| Diminishing, Phase 2 | w = min(M, b+log2(1+c/r)); opt-in defaults M=5, b=1, r=1 |
| Hybrid | Delegate by proposal category, otherwise default strategy |
| Expertise | w = 1 + multiplier*reliability, optionally capped |

Capped `max_weight` takes precedence over legacy `cap`; set baseline/reference/cap
explicitly for a Phase 2 experiment. For diminishing, supplying any of
`reference_contribution`, `base_weight`, `max_weight` selects the Phase 2 formula;
legacy `scale`/`multiplier` affect only the legacy formula. Caps cannot be below
baseline. Unlike legacy zero-baseline formulas, positive-baseline formulas give
zero contributors positive power. These are experimental parameters, not recommendations.

Default hybrid routes constitutional, board-election and fan-experience categories
to equal; funding routes to capped with that constructor's legacy defaults. Other
categories use equal by default. Explicit nested specifications configure other
routes/parameters. Expertise uses only historical evidence as described above.

## Ballots and proposal decisions

Proposals support two distinct options. Optional proposal quorum, approval threshold,
waiting period and eligibility override governance defaults. A single proposal voting
strategy replaces the experiment's comparison list; it is not hybrid routing.

A valid cast ballot chooses a configured option. `None` is abstention; unknown options
are invalid. Both are counted separately and excluded from votes cast, turnout,
quorum and option denominators. Zero-weight valid ballots count toward turnout,
quorum and unweighted shares but add no weighted approval power.

Quorum is valid ballots / eligible canonical people, inclusively compared to the
configured quorum. An empty electorate fails quorum even at setting zero. Approval
requires positive total valid cast weight and first-option share >= threshold.
An exact tie has no winning option but can pass at threshold 0.5 with quorum. Set a
threshold above 0.5 for more than half. Plurality winner and threshold passage differ.

## Metrics and representation

For sorted eligible weights w_i, normalized shares p_i and N eligible people:

- Gini is `2*sum((i/N)*p_i)-(N+1)/N`, i starting at 1; no small-sample correction.
- Effective voters is `1/sum(p_i^2)`, not participant headcount.
- Maximum and top 1/5/10% shares describe the largest voting weights. Top groups use
  `ceil(N*percentage/100)` whole people, including zero-power members in N.
- Top-level concentration is potential eligible power; `realized_concentration`
  uses valid participating power. Weighted/unweighted option shares use valid ballots.
- Equal-vote counterfactuals reuse the same ballots/quorum/threshold. Reported share
  difference is weighted first-option share minus equal share; outcome difference
  compares proposal passage, not just plurality winner.

Wealth representation ranks eligible people by wealth ascending, breaking ties by
canonical ID. Bottom 50% uses floor(N/2); top 10/1% use ceil(N*percentage/100).
Deciles assign zero-based rank i to floor(10*i/N). Small electorates may have empty
deciles and overlapping top groups. These ranks remain fixed for realized metrics;
participants are not reranked.

`representation.potential` normalizes eligible power and eligible member contributions.
`representation.realized` normalizes valid cast power and contributions of valid
participating members only. Group `contribution_to_power_ratio` is financial contribution
share divided by voting power share. Zero/undefined denominators return null. Wealth
rank groups are distinct from the concentration metrics' groups ranked by power.

Empty/all-zero concentration, zero weighted-share denominators and empty unweighted
ballots are undefined (JSON null/blank CSV), not zero inequality. Summary means skip
missing values; inspect degenerate trials before interpreting aggregate comparisons.
Paired models and common-random-number scenarios are not independent samples.

## Limits and reproduction

Phase 2's standalone election interface uses binary direct proposals. Phase 3 adds
abstract attacks, coordination, influence, stochastic sporting performance, and
financial resilience through the separate scenario layer. There is no real identity
verification, credential exploitation, payment processing, or blockchain interaction. No causal
inference, real-club forecasts, production authentication, privacy guarantees or automatic
inferential claims from trial means. Concentration alone does not establish legitimacy
or takeover resistance. Sequential experiment execution is deliberate.

Retain configuration, source provenance, component seeds, dependency versions and
`uv.lock`. `population.seed` optionally replaces the experiment seed for population
streams only. Runtime/absolute peak process memory are machine-dependent measurements;
see [Experiments](EXPERIMENTS.md) and [Phase 2 results](PHASE2_RESULTS.md) for reproduction
and measured evidence.

## Phase 3 assumptions

All people, identity claims, credentials, budgets, and financial amounts are synthetic.
Probabilities and monetary units are configurable assumptions without empirical
calibration. Capture means the configured operational objective succeeds in at least
one scheduled election; it does not mean permanent legal control. A majority of cast
weight differs from a majority of all eligible potential weight. Approval and quorum
are independent, and valid ballots alone contribute to quorum.

Matched trials share the initial population, ordinary true-person ballot streams,
economic calendar, and named random streams. Control disables attacks and shocks.
Attack outcome changes use an additional no-attack counterfactual with the same
shocks and the same defenses as the compared variant, preventing defense-only or
shock-only changes from being credited to attackers. Economic comparisons use the
unstressed control. Internal counterfactual runs are not exported as extra trials.

Income is distinct from wealth. Historical contributions establish voting stakes and
are not fresh club cash. Club contributions and investor capital are financing inflows;
membership fees are operating revenue. Cash and profit are separate. Financial flows
use elapsed days divided by 30, while elections and membership ages use calendar
dates. Monthly economic boundaries remain present for yearly observation steps.
Off-grid recovery events only update the lifecycle and do not redraw finances.

Identity verification is sampled once per new claim. Strong verification can reject
fraudulent claims and incorrectly reject legitimate ones; genuine hostile supporters
are not fraudulent identities. Temporary restrictions require simulated confirmation
and an unsuccessful appeal. Risk scores alone do not prove malicious intent.

Voting rights for investors require an explicit offer and an accepted funded grant;
ownership alone creates no vote. Simultaneous investor offers conservatively price
all due eligible grants in their denominator. Changes in voting caps may change
funding acceptance. Direct proposals do not model board seats or legal ownership rules.

Summary financial flows are cumulative; cash, debt, affordability, retention, runway,
and concentration are final observations. Shock recovery is the first observation
after the latest shock's active end with operating revenue at least 95% of matched
unstressed revenue; it is not restoration of cumulative lost cash. Missing recovery
or zero-denominator metrics are null. Trial quantiles and Wilson intervals describe
these synthetic experiments, not real-world takeover probabilities.
