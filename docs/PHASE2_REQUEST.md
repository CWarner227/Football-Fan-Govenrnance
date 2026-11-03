# Codex Prompt — Phase 2: Synthetic Supporter Modeling, Voting Systems & Election Simulation

## Project Context

We are developing a modular, research-oriented simulation framework for a blockchain-supported fan ownership and governance system in professional football.

Our central research question is:

**Can a blockchain-supported fan governance system increase supporter influence and broaden club funding without concentrating control among wealthy participants?**

Phase 1 established the initial architecture, including synthetic supporter generation, configurable voting strategies, membership eligibility, election execution, experiment orchestration, and baseline metrics.

**Your task is to inspect the existing repository, determine what Phase 1 actually implemented, and extend it to satisfy the Phase 2 requirements below.**

Do not recreate existing functionality or assume Phase 1 is fully implemented without checking.

Preserve existing working code, tests, configuration formats, and public interfaces whenever practical. If architectural changes are necessary, explain and document them.

The priority is to create a scientifically useful simulation engine capable of comparing different fan governance mechanisms under controlled experimental conditions.

---

# 1. Phase 2 Objectives

Implement or extend the following capabilities:

1. Rich synthetic supporter modeling with behavioral, financial, and governance attributes.
2. Configurable statistical distributions and correlations between supporter characteristics.
3. Six interchangeable voting models.
4. Configurable membership eligibility and proposal-specific voting rules.
5. Realistic probabilistic participation and voting preferences.
6. Reproducible election simulations.
7. Controlled comparisons using the same supporter populations and underlying proposals.
8. Quantitative metrics measuring voting concentration, representation, and election outcomes.
9. Batch experiments using Monte Carlo trials.
10. Structured output datasets and visualizations.

All components must remain modular and independently replaceable.

Do not implement real blockchain integration, a web frontend, or actual financial transactions in this phase.

# 2. Repository Inspection and Compatibility

Before modifying anything:

- Inspect the existing source tree, `pyproject.toml`, configuration files, tests, and documentation.
- Identify existing implementations of supporter models, population generation, voting strategies, eligibility policies, participation models, election execution, and experiment runners.
- Run the existing test suite and record its baseline status.
- Identify any incomplete or duplicated functionality.
- Determine which Phase 2 features can be added through existing extension points.

Create a short implementation plan before making changes.

Do not overwrite or discard functional Phase 1 components.

Use the repository's existing Python version, dependency manager, naming conventions, and test framework unless there is a compelling reason to change them.

# 3. Expanded Supporter Model

Extend the existing supporter model to support these attributes:

| Attribute | Type | Description |
|---|---|---|
| `fan_id` | String | Unique synthetic person identifier |
| `wealth` | Float | Available financial resources |
| `contribution` | Float | Amount contributed to the supporters' trust |
| `loyalty` | Float | Latent modeled attachment to the club |
| `membership_age_days` | Integer | Time since membership began |
| `participation_rate` | Float | Probability of participating in an eligible vote |
| `knowledge_score` | Float | Latent modeled decision-relevant expertise |
| `forecast_accuracy` | Float or optional | Historical forecasting performance |
| `is_adversarial` | Boolean | Whether the supporter is modeled as hostile |
| `preferred_policy` | String or structured preference | Preferred governance outcome |

Preserve compatibility with existing `supporter_id` fields if they already exist. Avoid unnecessary renaming or duplicate identifiers.

## Attribute Constraints

- Wealth must be nonnegative.
- Contributions must be nonnegative.
- Loyalty must be between 0 and 1.
- Participation rate must be between 0 and 1.
- Knowledge score must be between 0 and 1.
- Forecast accuracy must be between 0 and 1 when available.
- Membership age must be nonnegative.
- Contributions must not exceed available wealth unless an explicit alternative financial model permits it.

Do not assume that wealth, loyalty, contribution, expertise, and turnout are inherently correlated.

These relationships must be configurable.

## Important Research Distinctions

Loyalty and expertise are latent simulation assumptions, not directly observable facts.

Financial contribution must not automatically imply greater loyalty or expertise.

Forecasting accuracy must not automatically imply good governance decisions.

The adversarial attribute is included for future research. Do not implement coordinated attacks or takeover strategies in this phase.

Keep supporter identity separate from club membership records.

Support multiple clubs in the domain model where practical, but do not build a multi-club economic simulation yet.

# 4. Modular Population Generation

Extend the synthetic population generator to support configurable distributions for every relevant attribute.

Required distributions:

- Uniform.
- Normal, with documented truncation or bounds.
- Lognormal.
- Beta.
- Constant values.
- Categorical distributions for policy preferences.

Example configuration:

```yaml
population:
  size: 10000
  seed: 42

  wealth:
    distribution: lognormal
    mean: 10.0
    sigma: 1.0

  loyalty:
    distribution: beta
    alpha: 4.0
    beta: 2.0

  participation_rate:
    distribution: beta
    alpha: 3.0
    beta: 4.0

  knowledge_score:
    distribution: beta
    alpha: 2.0
    beta: 3.0

  membership_age_days:
    distribution: uniform
    min: 0
    max: 1825

  contribution:
    model: wealth_fraction
    min_fraction: 0.001
    max_fraction: 0.05

  forecast_accuracy:
    distribution: beta
    alpha: 5.0
    beta: 4.0

  adversarial_fraction: 0.0
```

Document whether distribution parameters are underlying distribution parameters or actual output moments. For example, NumPy's lognormal parameters describe the underlying normal distribution.

## Correlated Attributes

Support optional configurable correlations.

Examples:

- Wealth and contribution.
- Loyalty and participation.
- Knowledge and forecast accuracy.
- Membership age and participation.

Use a statistically defensible approach, such as a Gaussian copula, if implementing correlations across non-normal marginal distributions.

Do not simply multiply generated values together and call the result a correlation model.

Validate correlation matrices for symmetry, unit diagonals, and positive semidefiniteness.

Provide independent sampling as the default.

## Population Profiles

Create example configurations for:

1. Small club: 2,000 supporters.
2. Medium club: 10,000 supporters.
3. Large club: 100,000 supporters.
4. Wealth-unequal population.
5. High-participation population.
6. Low-participation population.

These are synthetic research profiles, not claims about real football clubs.

# 5. Voting Strategy Interface

Reuse or improve the existing voting strategy abstraction.

Every strategy must implement the same interface and return nonnegative, finite voting weights.

Voting strategies must not determine membership eligibility or voter turnout.

These responsibilities belong to separate modules.

Implement six voting models.

## Model A — Equal Voting

Every eligible supporter receives one unit of voting power.

Formula:

`weight = 1`

This model is the primary democratic baseline.

## Model B — Proportional Stake Voting

Voting power increases linearly with financial contribution.

Example:

`weight = contribution / reference_contribution`

The reference contribution must be configurable and strictly positive.

Document how zero-contribution members are handled.

Do not assume that members with greater financial contributions are more knowledgeable or make better decisions.

## Model C — Capped Stake Voting

Voting power increases with financial contribution but cannot exceed a configurable cap.

Example:

`weight = min(max_weight, base_weight + contribution / reference_contribution)`

Make `max_weight`, `base_weight`, and `reference_contribution` configurable.

Validate that the cap is not below the baseline weight.

## Model D — Diminishing Returns Voting

Implement a logarithmic weighting model.

Default experimental formula:

`weight = min(5, 1 + log2(1 + contribution / reference_contribution))`

The cap of 5 is an experimental parameter, not a recommendation.

Allow researchers to change the cap, reference contribution, and baseline weight.

Ensure the implementation handles zero contributions correctly.

## Model E — Hybrid Voting

Hybrid voting combines equal membership voting with limited financial weighting depending on the type of proposal.

Examples:

- Constitutional changes: one verified member, one vote.
- Board elections: one verified member, one vote.
- Selected funding proposals: capped financial weighting.
- Fan-experience proposals: one verified member, one vote.

Implement this as a configurable routing strategy that delegates to existing voting strategies.

Do not duplicate the mathematical implementations.

Example:

```yaml
hybrid:
  default_strategy: equal

  proposal_rules:
    constitutional: equal
    board_election: equal
    funding: capped
    fan_experience: equal
```

A hybrid strategy must be able to select voting rules based on proposal category without requiring changes to the election engine.

## Model F — Expertise-Weighted Voting

Implement an optional research model where voting weight is partially influenced by historical forecasting performance.

Example experimental formula:

`weight = 1 + expertise_multiplier * reliability_score`

The reliability score should be derived from historical forecast performance when available.

Do not automatically treat raw forecasting accuracy as a reliable expertise measure.

Support:

- Configurable expertise multiplier.
- Minimum forecasting sample requirements.
- Neutral default weighting for members without sufficient history.
- Optional caps on expertise influence.
- Clear separation between knowledge score and observed forecasting performance.

If no historical forecasting dataset exists, use explicitly synthetic forecasting records and label the resulting expertise scores as simulated.

Do not claim this model measures real-world supporter expertise.

# 6. Proposal-Specific Governance Rules

Extend the proposal model to support:

- Proposal identifier.
- Proposal category.
- Available voting options.
- Quorum.
- Approval threshold.
- Eligibility policy.
- Voting strategy.
- Proposal-specific metadata.

Initial proposal categories:

- Constitutional.
- Board election.
- Funding.
- Fan experience.
- Recruitment advisory.

For Phase 2, binary voting is sufficient.

Do not implement actual board-seat allocation or player transfer decisions yet.

The architecture should allow those features to be added later.

# 7. Membership Eligibility

Reuse the Phase 1 membership eligibility system.

Verify that it supports:

- Active membership.
- Verified membership.
- Configurable waiting periods.
- One eligible membership per canonical supporter identity per club.
- Proposal-specific eligibility requirements.

Implement tests ensuring that members cannot gain additional voting power by creating duplicate membership records tied to the same canonical supporter identity.

Do not claim this solves real-world identity fraud. Actual identity verification is outside the scope of this phase.

# 8. Participation Models

Implement or extend modular participation models.

At minimum, support:

### Independent Probabilistic Turnout

Each eligible supporter votes according to their configured participation probability.

### Constant Turnout

Every eligible supporter uses a common configurable participation probability.

### Attribute-Based Turnout

Participation probability may depend on configured supporter attributes, such as loyalty or membership age.

Keep coefficients configurable and document how probabilities are bounded.

Do not assume these behavioral relationships are empirically established.

All participation models must share a common interface.

# 9. Voting Preference Models

Keep voting preference generation separate from participation and voting weight.

Support:

### Random Binary Preference

A configurable probability of supporting a proposal.

### Policy-Based Preference

Supporters vote according to their preferred policy and the proposal's policy alignment.

### Attribute-Based Preference

Preferences may depend on configurable characteristics, such as loyalty, knowledge, or contribution.

The model must support deterministic execution under fixed random seeds.

Do not automatically make knowledgeable supporters vote for the objectively correct outcome. Decision quality is a separate future research component.

# 10. Election Runner

Extend the election runner to execute the following process:

1. Load the club, supporters, memberships, proposal, and configuration.
2. Validate the configuration.
3. Determine eligible members.
4. Determine turnout using the selected participation model.
5. Generate voting preferences.
6. Select the voting strategy.
7. Calculate individual voting weights.
8. Aggregate weighted and unweighted votes.
9. Evaluate quorum.
10. Evaluate approval thresholds.
11. Calculate metrics.
12. Return structured results.

The election runner must not contain strategy-specific conditional logic.

Strategies should be selected through the existing registry or dependency-injection mechanism.

Handle abstentions, ties, zero eligible voters, and zero total voting weight explicitly.

# 11. Controlled Experimental Comparisons

This is one of the most important requirements.

When comparing voting strategies, all strategies should use:

- The same supporter population.
- The same membership records.
- The same proposal.
- The same eligibility state.
- The same realized turnout.
- The same underlying vote preferences.

Only voting power calculations should change when comparing voting strategies.

This prevents unrelated randomness from influencing comparisons.

Implement reusable election input snapshots or another mechanism that guarantees identical baseline conditions.

Use independent random-number streams for population generation, participation, and preference generation.

Store the random seeds and configuration used in each trial.

# 12. Monte Carlo Experiment Runner

Extend the existing experiment runner to support repeated trials.

Required capabilities:

- Configurable trial count.
- Configurable random seed.
- Multiple population profiles.
- Multiple voting models.
- Multiple participation models.
- Multiple proposal categories.
- Multiple membership waiting periods.
- Structured output for each trial.
- Aggregated statistics across trials.

Implement a comparison experiment that runs all six voting models on matched election inputs.

Support at least 100 trials with 10,000 supporters.

Design for eventual experiments with 100,000 supporters and thousands of trials.

Avoid unnecessary Python-level loops when NumPy vectorization provides a clear benefit.

Do not sacrifice modularity for premature optimization.

# 13. Research Metrics

Implement or verify the following metrics.

## Participation

- Total supporters.
- Active members.
- Eligible members.
- Votes cast.
- Turnout percentage.
- Total voting weight cast.

## Voting Concentration

- Gini coefficient of eligible voting power.
- Effective number of voters.
- Maximum individual voting power share.
- Top 1%, 5%, and 10% voting power shares.
- Voting power distribution by wealth percentile.

## Election Outcomes

- Weighted vote share for each option.
- Unweighted vote share for each option.
- Winning option.
- Proposal approval status.
- Quorum achievement.
- Difference between weighted and equal-vote outcomes.

## Representation

- Voting influence of the bottom 50% by wealth.
- Voting influence of the top 10% by wealth.
- Voting influence of the top 1% by wealth.
- Ratio between financial contribution share and voting power share.

Calculate potential voting power separately from realized voting power among participating members.

Handle zero denominators and undefined metrics explicitly.

# 14. Baseline Research Experiment

Create a reproducible baseline experiment with:

- 10,000 synthetic supporters.
- Lognormal wealth distribution.
- Configurable contribution rates.
- Beta-distributed loyalty.
- Beta-distributed participation.
- Configurable membership waiting period.
- One binary governance proposal.
- Six voting models.
- 100 Monte Carlo trials.

For the hybrid model, run at least two proposal categories so that the strategy actually demonstrates different routing behavior.

For expertise weighting, use synthetic forecasting histories or explicitly configured simulated reliability scores.

Compare the voting models on matched populations and election realizations.

Generate a baseline dataset containing trial-level metrics and summary statistics.

Export:

- `baseline_trials.csv`
- `baseline_summary.csv`
- `baseline_config.yaml`
- `baseline_metadata.json`

Where useful, also export Parquet versions.

Metadata should include the code version or Git commit, seed, configuration, and execution environment.

# 15. Visualization

Create optional visualizations showing:

1. Voting power concentration by model.
2. Effective number of voters by model.
3. Wealth percentile versus voting power.
4. Weighted versus unweighted election outcomes.
5. Turnout distributions.
6. Election outcome differences across models.

Use Plotly or Matplotlib according to existing project conventions.

Label all figures as synthetic simulation results.

Do not imply that results represent actual football clubs.

# 16. Testing and Validation

Add unit, integration, and statistical tests.

Required tests include:

- All supporter attributes satisfy validation constraints.
- Population generation is reproducible.
- Generated distributions have approximately expected statistical properties.
- Configured correlations are approximately reproduced within reasonable tolerances.
- Equal voting gives equal power to all eligible members.
- Proportional voting scales correctly.
- Capped voting never exceeds the cap.
- Diminishing returns follow the configured formula.
- Hybrid voting selects the correct strategy by proposal category.
- Expertise weighting handles missing or insufficient forecast histories.
- Eligibility rules are correctly enforced.
- Duplicate membership records do not create additional votes.
- Participation probabilities remain valid.
- Voting preferences are reproducible.
- Matched-model comparisons reuse the same election inputs.
- Quorum and approval thresholds behave correctly.
- Voting concentration metrics are mathematically correct.
- Batch experiments produce complete output files.
- Identical seeds and configurations produce identical substantive results.

Use analytical examples where possible to verify voting calculations.

Avoid flaky tests based on uncontrolled randomness.

# 17. Documentation

Update the existing documentation.

### ARCHITECTURE.md

Document the expanded architecture and model interfaces.

### EXTENDING_MODELS.md

Explain how to add or replace voting, population, participation, preference, and eligibility models.

### SIMULATION_ASSUMPTIONS.md

Document all assumptions about supporter behavior, wealth, loyalty, expertise, forecasting accuracy, and participation.

### EXPERIMENTS.md

Explain how controlled comparisons work, why matched election inputs matter, and how to reproduce the baseline experiment.

### README.md

Update installation, CLI usage, experiment execution, testing, and output interpretation.

# 18. Future Compatibility

Keep extension points for future phases.

### Phase 3 — Adversarial and Economic Simulation

Future additions will include:

- Coordinated rival supporter infiltration.
- Wealthy takeover attempts.
- Sybil attacks.
- Low-turnout capture.
- Vote buying and coercion.
- Long-term membership infiltration.
- Investor funding models.
- Club operating budgets.
- Economic shocks.
- Financial resilience.

### Phase 4 — Blockchain Governance

Future additions will include:

- Membership credentials.
- Smart-contract voting.
- On-chain auditability.
- Conventional versus blockchain voting comparisons.

### Phase 5 — Full-Stack Prototype

Future additions will include:

- Governance web application.
- Membership management.
- Elections and proposal interfaces.
- Simulation dashboard.

Do not implement these future features now.

Ensure their addition will not require rewriting the Phase 2 simulation engine.

# 19. Performance and Reproducibility

Benchmark:

- 10,000 supporters, one election.
- 10,000 supporters, 100 trials, six voting models.
- 100,000 supporters, one election.

Record runtime and peak memory usage where practical.

Optimize only demonstrated bottlenecks.

Every experiment must record sufficient configuration and random-state information to reproduce its results.

Avoid dependence on external APIs or live data.

# 20. Definition of Done

Phase 2 is complete when:

- The existing Phase 1 framework remains functional.
- The expanded supporter model is implemented.
- Synthetic population generation supports configurable distributions and correlations.
- All six voting models are implemented.
- Membership eligibility is enforced.
- Participation and preference models are interchangeable.
- Elections run through a common engine.
- Controlled comparisons use matched populations and election inputs.
- Monte Carlo experiments execute successfully.
- Voting concentration and representation metrics are calculated.
- Baseline results are exported.
- Visualizations are generated.
- Automated tests pass.
- Documentation is updated.

## Final Execution Instructions

Work incrementally and verify each major component.

Do not stop after creating architecture documents or skeleton classes. Implement the functionality and run the tests.

Do not replace existing functionality unnecessarily.

Do not hardcode experimental assumptions into the simulation engine.

Do not fabricate benchmark results or simulation outcomes.

If a requested capability conflicts with the existing architecture, choose the smallest maintainable change and document the tradeoff.

When finished, report:

1. Existing Phase 1 functionality discovered.
2. New Phase 2 functionality implemented.
3. Files created or modified.
4. Architectural changes and reasons.
5. Test results.
6. Baseline experiment results.
7. Performance benchmarks.
8. Known limitations.
9. Recommended implementation priorities for Phase 3.

**The final product must be a modular, reproducible research simulation engine that allows us to compare different fan governance systems by changing configurations rather than rewriting code.**
