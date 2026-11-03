# Extending models

The engine uses structural protocols in `core/interfaces.py`; inheritance is optional.
Validate constructor parameters and keep models deterministic given their inputs and
supplied RNG. Avoid global random state and mutable plugin state across elections.

## Voting strategies and routing

Implement `calculate_weight(supporter, membership, context) -> float`, returning finite
nonnegative potential power. Eligibility and turnout belong to other components.
Register a constructor, select its name, and inject that registry:

```python
from dataclasses import dataclass
from math import sqrt
from fan_governance.core.config import SimulationConfig
from fan_governance.core.registry import default_registry
from fan_governance.experiments.runner import ExperimentRunner

@dataclass(frozen=True)
class SquareRootVoting:
    def calculate_weight(self, supporter, membership, context):
        return sqrt(membership.contribution)

registry = default_registry()
registry.register("voting", "square_root", SquareRootVoting)
config = SimulationConfig.model_validate({
    "population": {"size": 1000},
    "voting": {"strategies": ["equal", "square_root"]},
})
results = ExperimentRunner(registry=registry).run(config)
```

YAML specifications accept `{name: square_root, parameters: {...}}` when the constructor
accepts those parameters. `ModelSpec.parameters` supports nested mappings, so hybrid
routes can name a strategy or supply a complete specification:

```yaml
voting:
  strategies:
    - name: hybrid
      parameters:
        default_strategy: equal
        proposal_rules:
          constitutional: equal
          funding:
            name: capped
            parameters: {reference_contribution: 100, base_weight: 1, max_weight: 5}
```

`VotingContext.proposal_category` selects the route. Missing categories use `default_strategy`;
recursive hybrid routes are rejected. Default funding routing uses the existing
`capped` constructor defaults; explicitly configure Phase 2 financial parameters
when desired. See the assumptions guide for legacy versus Phase 2 formulas.

`expertise` accepts `expertise_multiplier`, `minimum_samples`, optional `max_weight`,
`confidence_z` and `chance_accuracy`. It consumes supporter correct/total history,
not latent knowledge or raw accuracy. Replace the reliability model with a new
registered strategy if the experiment requires a different statistical assumption.

For CLI plugins, create an application composition root or extend `default_registry`.
The stock CLI deliberately does not load arbitrary Python code from YAML.

## Participation and preferences

A turnout plugin implements
`participates(supporter, membership, context, rng) -> bool`; register it under
`participation`. Built-ins are `probabilistic` (supporter probability unless overridden),
`constant` (common probability, default 0.6), and `attribute_based`.

A preference plugin implements
`choose(supporter, membership, proposal, context, rng) -> str | None`; register under
`preference`. Return a proposal option or `None` for abstention. Unknown options are
invalid ballots. Built-ins are `synthetic`, `policy` and `attribute_based`.

Attribute models use `logistic(intercept + sum(coefficient * attribute / scale))`.
Scales default to 1 and must be positive. Configure assumptions explicitly:

```yaml
participation:
  name: attribute_based
  parameters:
    intercept: -1.0
    coefficients: {loyalty: 2.0, membership_age_days: 0.5}
    scales: {membership_age_days: 365}
preference:
  name: attribute_based
  parameters:
    intercept: 0.0
    coefficients: {knowledge_score: 0.5, contribution: 0.1}
    scales: {contribution: 100}
    abstention_probability: 0.05
```

Attributes are approved numeric supporter traits; contribution here is the supporter
trait, whereas financial voting uses the membership record. Optional absent forecast
accuracy is treated as 0.5. Coefficients have no empirical standing by default.

For `policy`, set `proposal.metadata.policy_alignment` to a favored policy string or
a mapping from policy label to first-option probability. For string alignment,
`alignment_probability`/`mismatch_probability` apply; neutral supporters, missing
alignment and unlisted mapping labels use `neutral_probability`. Abstention is
separately configurable. This models preference, not objectively correct decisions.

Preparation draws both behavior components for every canonical person with membership,
including ineligible people and nonparticipants. Eligible people receive the selected
eligible record; other people receive their lexically first record. Behavior sees
neutral strategy metadata and frozen people/records. Do not mutate these inputs.

## Eligibility and proposal overrides

Implement `eligible(supporters, memberships) -> Sequence[Membership]`, returning existing
records, at most one per canonical supporter. Register under `eligibility` and select
`governance.eligibility`. Configured construction passes `waiting_period_days`; accept
it or use an adapter. The runner rejects unknown records and duplicate people even
when using a custom policy. Eligibility executes once when preparing a matched snapshot.

Under `proposal`, optional `quorum`, `approval_threshold`, `waiting_period_days` and
`eligibility` override governance defaults. A single `proposal.voting_strategy` replaces
the comparison strategy list. Leave it unset when comparing multiple models; use
`hybrid` when category-specific delegation is the research question. The low-level
runner uses injected policies, so direct callers must align them with proposal metadata.

## Distributions and population generation

Built-in numeric distributions are `uniform`, `normal`, `lognormal`, `beta` and
`constant`; policy preferences use `categorical` with categories and optional
probabilities. Both population formats are accepted:

```yaml
population:
  wealth_distribution:
    type: lognormal
    parameters: {mean: 10, sigma: 1}
    lower: 0
  participation_rate: {distribution: beta, alpha: 3, beta: 4}
  contribution_model: wealth_fraction
  contribution_fraction_distribution:
    type: uniform
    parameters: {low: 0.001, high: 0.05}
```

Compact `contribution: {model: wealth_fraction, min_fraction: ..., max_fraction: ...}`
is equivalent. Independent contributions are clipped to wealth by default. Set
`allow_unfunded_contributions: true` (or `financial_mode: allow_unfunded`) only when
intentionally modeling contributions beyond available wealth. Club validation also
checks every authoritative member amount against that person's wealth.

A numeric sampler has signature `(distribution_config, size, rng) -> numpy.ndarray`
and returns shape `(size,)` with finite output. Inject custom names, for example:

```python
import numpy as np
from fan_governance.agents.generator import SyntheticPopulationGenerator

def triangular(config, size, rng):
    if set(config.parameters) != {"low", "mode", "high"}:
        raise ValueError("triangular requires low, mode, high")
    p = config.parameters
    return rng.triangular(p["low"], p["mode"], p["high"], size)

generator = SyntheticPopulationGenerator(distributions={"triangular": triangular})
# ExperimentRunner(population_generator=generator).run(config)
```

Custom distribution names are permitted; their sampler owns parameter validation.
Configured/domain bounds still apply. The numeric sampler injection does not replace
the built-in categorical policy path. For a different population process, implement
`generate(config, streams)` and return `Population(supporters, memberships)`.

Correlations accept pair mappings or an explicit attribute list and matrix. The
Gaussian copula operates on numeric marginals; affordability/fraction transforms
can change realized marginal and correlation properties. See the assumptions guide.

## Metrics and experiments

Implement `calculate(ElectionData) -> dict` or compose `StandardMetrics().calculate(data)`
with additional finite JSON-serializable values (`None` for undefined metrics).
CLI summaries/plots expect standard keys; retain them for those adapters. Metric
plugins cannot alter core quorum/approval. `ElectionData` includes eligible identities,
wealth, membership contributions and cast identities for representation calculations.

Experiment axes form a Cartesian product: `population_sizes`, `waiting_periods`,
`participation_levels`, `wealth_distributions`, `participation_models`, and
`proposal_categories`. Alternatively, `population_profiles` maps names to complete
`PopulationConfig` objects; do not combine profiles with size/wealth axes. Omitted
axes use scalar configuration. Each trial/scenario has one snapshot shared by its
voting models; scenarios in a trial share named streams, while trial IDs differ.

Use `ElectionRunner.prepare` and pass the returned `snapshot` to `run` for explicit
low-level matched comparisons. Snapshot seed, trial and club must match. Register
models before running trials, and preserve configuration/source/dependency provenance.
See [Experiments](EXPERIMENTS.md) for the baseline and benchmark commands.
