# Codex Prompt — Phase 1: Modular Fan Governance Simulation Engine

## Project Context

We are developing a research-oriented simulation platform for a project investigating blockchain-supported fan ownership, governance, and funding in professional sports, initially focusing on English football clubs.

The central research question is:

**Can a blockchain-supported fan governance system increase supporter influence and broaden club funding without concentrating control among wealthy participants or exposing the club to hostile takeover?**

The software will simulate supporters' trusts, membership systems, voting mechanisms, financial contributions, elections, and adversarial behavior.

We eventually want to compare:

- One verified member, one vote.
- Proportional stake-weighted voting.
- Capped stake-weighted voting.
- Diminishing-returns voting.
- Hybrid voting systems.
- Voting based partly on historical prediction accuracy.
- Different membership waiting periods and eligibility requirements.
- Coordinated hostile groups attempting to influence elections.
- Different turnout, supporter wealth, and fanbase distributions.
- Financial outcomes under different ownership structures.
- Board elections and representative governance.
- Sporting and economic outcomes from simulated decisions.
- Blockchain-backed versus conventional governance infrastructure.

**This first development phase must focus on establishing a clean, extensible simulation foundation. Do not attempt to implement every future feature.**

The architecture should make it straightforward to add, replace, disable, or modify individual components without changing unrelated code.

---

# 1. Primary Objectives

Build a Python-based simulation engine that:

1. Generates synthetic populations of football supporters.
2. Represents supporters, clubs, memberships, and governance proposals.
3. Supports interchangeable voting algorithms.
4. Simulates voting participation and election outcomes.
5. Allows governance rules to be configured externally.
6. Runs reproducible experiments using controlled random seeds.
7. Calculates meaningful voting and representation metrics.
8. Supports batch simulations with multiple experimental configurations.
9. Exports structured simulation results.
10. Provides a modular architecture for future adversarial, economic, and blockchain integrations.

The engine should operate independently of any frontend, database, or blockchain implementation.

The simulation must remain usable as a standalone Python package.

# 2. Technology Stack

Use:

- Python 3.12 or newer.
- NumPy for numerical operations.
- Pandas for tabular analysis and exporting results.
- Pydantic for configuration and data validation.
- PyYAML for configuration files.
- SciPy only where statistically useful.
- Pytest for automated testing.
- Ruff for formatting and linting.
- Matplotlib or Plotly for basic research visualizations.

Use `pyproject.toml` for package configuration and dependency management.

Do not introduce a database, web framework, blockchain dependency, or unnecessary infrastructure during this phase.

Prefer Python standard-library functionality when appropriate.

# 3. Architecture Requirements

Design the simulation using a modular, interface-driven architecture.

Individual models must be replaceable without modifying the simulation engine itself.

Use abstract base classes or Python protocols where they provide clear benefits.

Avoid unnecessary abstraction, excessive inheritance, and tightly coupled components.

Follow these architectural principles:

**A. Separation of concerns**

Separate:

- Population generation.
- Agent behavior.
- Membership eligibility.
- Voting power calculation.
- Vote preference generation.
- Turnout and participation.
- Election execution.
- Governance rules.
- Result calculation.
- Experiment orchestration.
- Data export.

**B. Dependency injection**

The simulation engine should receive its models and strategies as dependencies.

It must not hardcode a particular voting algorithm, population distribution, or participation model.

**C. Configuration-driven experiments**

Researchers must be able to change simulation behavior using YAML files rather than editing source code.

**D. Reproducibility**

Every simulation must support deterministic execution using explicit random seeds.

**E. Extensibility**

Future developers should be able to add new voting strategies, agent types, economic models, or attack scenarios by implementing defined interfaces.

**F. Independence from blockchain**

Governance simulation logic must not depend on smart contracts or blockchain transaction processing.

Blockchain functionality will eventually be implemented as a separate integration layer.

---

# 4. Proposed Repository Structure

Create the following structure, adjusting it where necessary to maintain good software engineering practices.

```text
fan-governance-simulator/
│
├── pyproject.toml
├── README.md
├── .gitignore
│
├── configs/
│   ├── default.yaml
│   ├── equal_voting.yaml
│   ├── stake_voting.yaml
│   └── experiments/
│       └── voting_comparison.yaml
│
├── src/
│   └── fan_governance/
│       ├── __init__.py
│       │
│       ├── core/
│       │   ├── engine.py
│       │   ├── context.py
│       │   ├── interfaces.py
│       │   ├── registry.py
│       │   └── config.py
│       │
│       ├── agents/
│       │   ├── models.py
│       │   └── generator.py
│       │
│       ├── clubs/
│       │   └── models.py
│       │
│       ├── membership/
│       │   ├── models.py
│       │   └── eligibility.py
│       │
│       ├── voting/
│       │   ├── base.py
│       │   ├── equal.py
│       │   ├── proportional.py
│       │   ├── capped.py
│       │   └── diminishing.py
│       │
│       ├── participation/
│       │   ├── base.py
│       │   └── probabilistic.py
│       │
│       ├── preferences/
│       │   ├── base.py
│       │   └── synthetic.py
│       │
│       ├── elections/
│       │   ├── models.py
│       │   └── runner.py
│       │
│       ├── metrics/
│       │   ├── concentration.py
│       │   ├── participation.py
│       │   └── results.py
│       │
│       ├── experiments/
│       │   ├── runner.py
│       │   └── comparison.py
│       │
│       ├── output/
│       │   └── exporters.py
│       │
│       └── cli.py
│
├── tests/
│   ├── test_agents.py
│   ├── test_membership.py
│   ├── test_voting.py
│   ├── test_elections.py
│   ├── test_metrics.py
│   ├── test_experiments.py
│   └── test_reproducibility.py
│
├── examples/
│   └── basic_simulation.py
│
├── results/
│
└── docs/
    ├── ARCHITECTURE.md
    ├── EXTENDING_MODELS.md
    └── SIMULATION_ASSUMPTIONS.md
```

Use this as a starting point, not an inflexible requirement.

# 5. Core Domain Models

Implement strongly typed models representing the simulation domain.

## Supporter

A supporter should contain:

```python
class Supporter:
    supporter_id: str
    wealth: float
    contribution: float
    loyalty: float
    knowledge: float
    membership_age_days: int
    participation_probability: float
    is_adversarial: bool
```

These fields represent synthetic characteristics, not necessarily measurable real-world traits.

Design the model so additional characteristics can be introduced later.

Do not assume that wealth, loyalty, expertise, and contribution are necessarily correlated.

Allow the population generator to specify correlations when explicitly configured.

## Club

Represent:

- Club identifier.
- Club name.
- Supporter population.
- Trust membership rules.
- Governance configuration.
- Optional financial attributes reserved for future development.

## Membership

Membership should be separate from supporter identity.

Represent:

- Member identifier.
- Supporter identifier.
- Membership start date or simulated membership age.
- Verification status.
- Active status.
- Contribution amount.
- Eligibility status derived from configured rules.

Avoid storing redundant eligibility fields when eligibility can be computed from the current rules and membership state.

## Governance Proposal

Represent:

- Proposal identifier.
- Proposal category.
- Available voting options.
- Required quorum.
- Required approval threshold.
- Eligibility rules.
- Voting method.

Support binary proposals initially, but design the interfaces so multi-option elections can be introduced later.

## Simulation Result

Represent:

- Experiment identifier.
- Trial identifier.
- Random seed.
- Governance configuration.
- Voting model.
- Population size.
- Eligible voter count.
- Votes cast.
- Turnout.
- Vote totals.
- Proposal outcome.
- Voting concentration metrics.
- Execution metadata.

Ensure results can be serialized and analyzed.

# 6. Modular Voting System

Implement a common voting strategy interface.

For example:

```python
class VotingStrategy(ABC):

    @abstractmethod
    def calculate_weight(
        self,
        supporter: Supporter,
        membership: Membership,
        context: VotingContext
    ) -> float:
        ...
```

Implement four strategies.

### Strategy A — Equal Voting

Every eligible member receives one vote.

### Strategy B — Proportional Stake Voting

Voting weight is proportional to the member's financial contribution.

Specify how zero contributions are handled.

### Strategy C — Capped Stake Voting

Voting weight increases with contributions but cannot exceed a configurable maximum.

### Strategy D — Diminishing Returns Voting

Use a configurable sublinear function, such as logarithmic weighting.

Do not hardcode the formula's scaling constants.

All strategies must use the same interface.

A new voting strategy should be addable without changing the simulation engine.

Voting eligibility must be enforced separately from voting weight calculation.

# 7. Membership Eligibility System

Implement a modular eligibility policy.

Initial requirements:

- Membership must be active.
- Member must be verified.
- Membership age must meet the configured waiting period.
- One supporter may have only one eligible membership per club.

Implement the last condition using the simulation's canonical supporter identity.

Do not treat this as proof of real-world identity uniqueness.

Future development will simulate identity fraud and duplicate-account attacks.

The eligibility system must support configurable waiting periods:

- 0 days.
- 90 days.
- 180 days.
- 365 days.
- Arbitrary custom values.

It should be possible to replace the eligibility policy without modifying voting strategies.

# 8. Synthetic Population Generator

Implement a configurable population generator.

It should support:

- Population size.
- Random seed.
- Wealth distributions.
- Contribution distributions.
- Membership age distributions.
- Loyalty distributions.
- Knowledge distributions.
- Participation probability distributions.
- Percentage of adversarial supporters.

Initial distributions should include:

- Uniform.
- Normal, with appropriate bounds.
- Lognormal.
- Beta.

Provide sensible defaults for each attribute.

Validate generated values against domain constraints.

Allow researchers to generate different population profiles, such as:

- Small football club.
- Large football club.
- Low-income supporter population.
- Highly unequal wealth distribution.
- High-participation supporter population.
- Low-participation supporter population.

Do not claim these synthetic profiles represent real clubs unless calibrated against real data.

# 9. Participation and Preference Models

Keep participation separate from voting preference.

Implement a probabilistic turnout model that determines whether an eligible member votes.

Implement a synthetic preference model that determines which option the member supports.

Both must be interchangeable.

For Phase 1, simple probabilistic models are sufficient.

However, the architecture must support future behaviors such as:

- Coordinated adversarial voting.
- Wealth-dependent participation.
- Loyalty-dependent participation.
- Strategic abstention.
- Social influence.
- Knowledge-dependent decisions.
- Group preferences.

Avoid hardcoding these future behaviors into the initial engine.

# 10. Election Simulation Engine

Implement an election runner that:

1. Receives a club, population, proposal, and simulation configuration.
2. Determines eligible members.
3. Applies the participation model.
4. Generates voting preferences.
5. Calculates voting weights.
6. Aggregates votes.
7. Evaluates quorum and approval thresholds.
8. Calculates metrics.
9. Returns a structured result.

The election runner must not contain voting-model-specific logic.

All model behavior should be delegated to interchangeable components.

Define quorum carefully, including whether it is measured by eligible member count, voting weight, or another explicitly configured basis.

Use a consistent rule for abstentions and invalid votes.

# 11. Metrics and Research Outputs

Implement at least:

**Participation metrics**
- Eligible member count.
- Voter count.
- Turnout percentage.
- Total voting weight cast.

**Voting concentration metrics**
- Gini coefficient of eligible voting power.
- Effective number of voters.
- Maximum individual voting power share.
- Top 1%, 5%, and 10% voting power shares.

**Election metrics**
- Weighted vote share per option.
- Unweighted vote share per option.
- Winning option.
- Approval threshold achieved.
- Quorum achieved.
- Proposal passed or failed.

Calculate voting concentration using the full eligible electorate's potential voting power, separately from actual votes cast.

Handle empty populations, zero total voting weight, and other edge cases explicitly.

Do not silently return misleading statistics.

Keep all metrics independent of the election runner so new metrics can be added without changing election logic.

# 12. Experiment Runner

Create a batch experiment system capable of executing many simulation trials.

Researchers should be able to specify:

- Population size.
- Voting strategies.
- Waiting periods.
- Participation levels.
- Wealth distributions.
- Number of trials.
- Random seed.
- Output directory.

Example:

```yaml
experiment:
  name: voting_model_comparison
  trials: 100
  seed: 42

population:
  size: 10000
  wealth_distribution:
    type: lognormal
    parameters:
      mean: 10.0
      sigma: 1.0

governance:
  waiting_period_days: 180

voting:
  strategies:
    - equal
    - proportional
    - capped
    - diminishing

output:
  formats:
    - csv
    - json
```

Implement an experiment runner that executes all selected strategies.

**Important experimental requirement:**

When comparing voting strategies, use the same generated population, eligibility state, participation realizations, and underlying preferences wherever the experimental design permits.

This ensures differences are attributable to the voting rules rather than unrelated randomness.

Generate independent random streams for separate trials and components, so changing one component does not unintentionally alter unrelated random behavior.

Record the seeds and configuration used for each trial.

# 13. Results and Visualization

Implement export functionality supporting:

- CSV.
- JSON.
- Parquet, if practical.

Results should be easy to import into Pandas for statistical analysis.

Create a basic plotting utility capable of displaying:

- Voting power concentration by model.
- Turnout by model.
- Election outcome comparisons.
- Effective number of voters.
- Distribution of results across repeated trials.

The plotting system should be optional.

Do not make visualization dependencies mandatory for core simulation execution.

# 14. Command-Line Interface

Provide a CLI for running simulations.

Example commands:

```bash
fan-governance simulate --config configs/default.yaml
```

```bash
fan-governance experiment \
  --config configs/experiments/voting_comparison.yaml
```

```bash
fan-governance models
```

The `models` command should list available voting, participation, preference, and eligibility strategies.

The CLI should report:

- Experiment name.
- Population size.
- Selected models.
- Trial count.
- Random seed.
- Execution time.
- Results location.

Include useful validation errors for malformed configurations.

# 15. Testing Requirements

Create comprehensive automated tests.

At minimum, test:

1. Equal voting always assigns one unit of voting weight to eligible members.
2. Proportional voting behaves correctly for different contributions.
3. Capped voting never exceeds its configured maximum.
4. Diminishing-returns voting follows its specified formula.
5. Ineligible members cannot vote.
6. Membership waiting periods are enforced.
7. Duplicate membership records cannot grant multiple votes to the same supporter.
8. Turnout models produce valid outcomes.
9. Voting weights are never negative or nonfinite.
10. Vote aggregation is mathematically correct.
11. Quorum and approval rules are correctly enforced.
12. Identical configurations and seeds produce identical substantive results.
13. Different strategies can be swapped without modifying the election runner.
14. Empty and degenerate populations are handled safely.
15. Batch experiments export complete and valid results.

Include integration tests for a complete simulation and a multi-model experiment.

Use fixed seeds in tests where randomness is involved.

# 16. Documentation

Create:

### README.md

Explain:

- Project purpose.
- Installation.
- How to run a simulation.
- How to run experiments.
- How to interpret results.
- How to execute tests.

### ARCHITECTURE.md

Explain the system architecture, component boundaries, data flow, and dependency injection.

### EXTENDING_MODELS.md

Provide step-by-step instructions for adding:

- A new voting strategy.
- A new participation model.
- A new eligibility policy.
- A new population distribution.
- A new metric.

Include one concrete example of extending a strategy.

### SIMULATION_ASSUMPTIONS.md

Document:

- Synthetic assumptions.
- Voting formulas.
- Population distributions.
- Behavioral assumptions.
- Known limitations.
- Which mechanisms have not yet been implemented.

Make a clear distinction between simulation-generated results and empirically established facts.

# 17. Future Integration Requirements

Do not implement these features yet, but ensure the architecture can support them.

**Phase 2 — Adversarial Simulation**
- Rival supporter infiltration.
- Coordinated voting.
- Sybil attacks.
- Wealthy takeover attempts.
- Low-turnout capture.
- Suspicious account activity.

**Phase 3 — Economic Simulation**
- Membership revenue.
- Investor contributions.
- Club operating budgets.
- Financial shocks.
- Funding inequality.
- Investor return models.

**Phase 4 — Representative Governance**
- Board elections.
- Representative accountability.
- Multiple governance tiers.
- Recall elections.
- Direct versus representative voting.

**Phase 5 — Football Decision Simulation**
- Player recruitment.
- Transfer budgets.
- Player valuations.
- Sporting uncertainty.
- Decision quality and expertise.

**Phase 6 — Blockchain Integration**
- Membership credentials.
- Smart-contract voting.
- Governance proposal execution.
- On-chain auditability.
- Comparison with conventional databases.

The core simulation engine must not require modification simply because one of these systems is added.

# 18. Performance Requirements

The initial engine should comfortably support populations of 10,000 supporters and repeated trials.

Design with eventual populations of 100,000 or more supporters in mind.

Use efficient numerical operations where useful, but avoid premature optimization.

Avoid storing unnecessary intermediate objects for every trial.

Do not introduce distributed processing until there is a demonstrated need.

Measure and document execution time for representative simulations.

# 19. Implementation Procedure

Follow this order:

1. Inspect the existing repository before making changes.
2. If the repository is empty, initialize the Python project.
3. Create the package structure and configuration models.
4. Implement core domain models.
5. Implement synthetic population generation.
6. Implement voting strategy interfaces and initial strategies.
7. Implement membership eligibility.
8. Implement participation and preference models.
9. Implement the election runner.
10. Implement metrics.
11. Implement experiment orchestration.
12. Implement exports and CLI.
13. Add tests.
14. Add documentation.
15. Execute a complete end-to-end experiment.

Do not add unnecessary dependencies or infrastructure.

Do not implement future phases prematurely.

Keep code readable, typed, documented, and maintainable.

# 20. Definition of Done

Phase 1 is complete when:

- The simulation package installs successfully.
- All four voting strategies work.
- Voting models can be swapped through configuration.
- A synthetic population of 10,000 supporters can be generated.
- Membership eligibility is enforced.
- Elections can be simulated.
- Voting concentration and participation metrics are calculated.
- A batch experiment can compare voting strategies using controlled randomness.
- Results can be exported to CSV and JSON.
- The CLI works.
- Automated tests pass.
- Documentation explains how to extend the system.

Run a demonstration experiment comparing the four voting strategies over 100 trials with 10,000 supporters.

Produce a summary showing:

- Average turnout.
- Average effective number of voters.
- Voting power concentration.
- Election outcome differences.
- Execution time.

Do not fabricate results. Execute the simulation and report actual outputs.

# Final Instructions

Prioritize **modularity, correctness, reproducibility, and research extensibility** over unnecessary features.

The finished system should be a scientific simulation framework, not a collection of hardcoded scripts.

Every major mechanism should be independently replaceable.

Use explicit assumptions, documented formulas, and deterministic tests.

Before implementing, briefly summarize the proposed architecture and identify any major design tradeoffs.

Then proceed with implementation.

When finished, provide:

1. Summary of implemented functionality.
2. Final repository structure.
3. Instructions for running simulations.
4. Test results.
5. Demonstration experiment results.
6. Known limitations.
7. Recommended next steps for Phase 2.

Do not claim features are complete unless they have been implemented and verified.
