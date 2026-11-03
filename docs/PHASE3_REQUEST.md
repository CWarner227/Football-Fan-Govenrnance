# Codex Prompt — Phase 3: Adversarial Governance, Hostile Takeovers & Economic Simulation

## Project Context

We are developing a modular research simulation framework investigating blockchain-supported fan ownership, voting, governance, and funding in professional football clubs.

Our central research question is:

**Can a blockchain-supported fan governance system increase supporter influence and broaden club funding without concentrating control among wealthy participants or exposing clubs to hostile takeovers?**

Phase 1 established the simulation architecture, population generation, membership eligibility, voting strategies, election execution, and experiment orchestration.

Phase 2 expanded the framework with richer supporter attributes, six voting models, configurable participation and preferences, controlled Monte Carlo comparisons, and representation metrics.

**Phase 3 will introduce adversarial behavior, defensive governance mechanisms, and club economics.**

The objective is to determine which governance structures remain resilient when wealthy individuals, rival supporters, or coordinated groups attempt to influence elections, and how different governance structures perform under financial constraints and economic shocks.

This is a research simulation. Do not interact with real football clubs, identity systems, wallets, or voting platforms.

All attackers, supporters, financial transactions, and governance decisions must exist entirely within the synthetic simulation environment.

---

# 1. Primary Objectives

Implement the following capabilities:

1. Modular adversarial agents capable of pursuing different governance capture strategies.
2. Seven configurable attack scenarios.
3. Defensive governance policies that can be enabled, disabled, and combined.
4. Multi-period simulation supporting membership aging and long-term infiltration.
5. Explicit modeling of identity verification and its limitations.
6. Economic models for supporter income, membership revenue, investor contributions, and club expenses.
7. Financial shocks and uncertain sporting outcomes.
8. Combined governance and economic simulations.
9. Monte Carlo experiments comparing attacks, defenses, and voting models.
10. Research metrics measuring capture probability, voting concentration, economic resilience, and defensive effectiveness.

All new components must integrate with the existing Phase 1 and Phase 2 framework without unnecessary rewrites.

# 2. Repository Inspection and Compatibility

Before making changes:

- Inspect the repository structure and existing architecture.
- Read the README, architecture documentation, experiment documentation, and simulation assumptions.
- Identify current agent models, voting strategies, eligibility policies, participation models, election runner, metrics, and experiment runner.
- Run the existing tests and record baseline results.
- Identify existing extension points suitable for adversarial and economic modeling.
- Prepare a brief implementation plan describing the new modules and how they connect to existing components.

Do not assume the repository exactly matches the previous development prompts.

Preserve existing public interfaces where practical.

If modifications are necessary, explain the reasoning and provide compatibility tests.

# 3. Architectural Requirements

Use a modular architecture with interchangeable strategies and policies.

Separate the following concerns:

- Attacker objectives.
- Attacker resources.
- Adversarial strategies.
- Attack execution.
- Defensive policies.
- Identity and credential modeling.
- Membership lifecycle.
- Election participation.
- Voting behavior.
- Financial behavior.
- Club economic state.
- Economic shocks.
- Detection and investigation.
- Metrics and reporting.

The simulation engine must not contain hardcoded logic for specific attacks or defenses.

Attack strategies and defensive policies should be injected through existing interfaces or registries.

Multiple attacks and defenses should be composable where their effects are compatible.

Define explicit execution ordering and conflict resolution.

Avoid implementing a large collection of attack-specific conditional statements inside the election runner.

# 4. Proposed Repository Extensions

Extend the existing repository with modules similar to:

```text
src/fan_governance/
│
├── adversarial/
│   ├── base.py
│   ├── objectives.py
│   ├── resources.py
│   ├── wealthy_takeover.py
│   ├── coordinated_infiltration.py
│   ├── sybil.py
│   ├── low_turnout.py
│   ├── vote_influence.py
│   ├── account_compromise.py
│   └── long_term_infiltration.py
│
├── defenses/
│   ├── base.py
│   ├── identity_verification.py
│   ├── waiting_period.py
│   ├── vote_caps.py
│   ├── quorum.py
│   ├── participation.py
│   └── suspicious_activity.py
│
├── economics/
│   ├── models.py
│   ├── supporters.py
│   ├── membership_revenue.py
│   ├── investors.py
│   ├── club_finances.py
│   ├── sporting_performance.py
│   └── shocks.py
│
├── lifecycle/
│   ├── clock.py
│   ├── membership.py
│   └── scheduler.py
│
├── scenarios/
│   ├── registry.py
│   ├── loader.py
│   └── validation.py
│
├── metrics/
│   ├── capture.py
│   ├── defensive_effectiveness.py
│   └── financial_resilience.py
│
└── experiments/
    ├── adversarial_runner.py
    ├── economic_runner.py
    └── scenario_comparison.py
```

Adapt this structure to the existing architecture rather than creating unnecessary duplicate modules.

# 5. Adversarial Agent Model

Extend the existing supporter and agent system to represent adversarial behavior.

An adversarial actor may control one or more synthetic supporter identities, memberships, or credentials.

Represent attacker characteristics such as:

- `attacker_id`
- `attacker_type`
- `objective`
- `financial_budget`
- `operational_budget`
- `controlled_supporters`
- `controlled_credentials`
- `coordination_level`
- `risk_tolerance`
- `time_horizon`
- `strategy`
- `resources_remaining`

Separate the attacker from the identities or credentials they control.

This distinction is essential for modeling Sybil attacks and compromised accounts.

## Attacker Objectives

Support configurable objectives such as:

- Achieve more than 50% of votes cast.
- Achieve a specified voting-power threshold.
- Cause a targeted proposal to pass.
- Block a targeted proposal.
- Prevent quorum.
- Gain a specified number of simulated board seats in a future extension.
- Increase governance disruption.
- Maximize influence relative to financial expenditure.

Define capture precisely for each experiment.

Do not treat obtaining a majority of votes cast as equivalent to gaining permanent legal control of the club.

For this phase, governance capture refers to a measurable simulated voting or proposal outcome.

# 6. Adversarial Strategy Interface

Implement a common interface for adversarial strategies.

For example:

```python
class AdversarialStrategy(Protocol):

    def plan(
        self,
        context: SimulationContext
    ) -> AttackPlan:
        ...

    def execute(
        self,
        plan: AttackPlan,
        context: SimulationContext
    ) -> AttackOutcome:
        ...
```

Use the existing project conventions if suitable interfaces already exist.

Strategies should receive:

- Current simulation state.
- Attacker resources.
- Governance configuration.
- Membership state.
- Election schedule.
- Economic conditions.
- Random-number generator.

Strategies must not directly mutate unrelated simulation components.

Use explicit state transitions or event records.

Support deterministic execution using controlled random seeds.

# 7. Implement Seven Attack Strategies

## Attack A — Wealthy Takeover

Model an attacker with substantially greater financial resources than ordinary supporters.

The attacker attempts to gain voting influence through financial contributions.

Configurable parameters:

- Attacker wealth.
- Contribution budget.
- Contribution strategy.
- Voting model.
- Maximum voting weight.
- Membership eligibility.
- Time horizon.

Compare equal voting, proportional stake voting, capped voting, diminishing returns, and hybrid voting.

Measure:

- Attacker voting-power share.
- Financial cost of influence.
- Whether the attack reaches its objective.
- Effectiveness of voting caps.
- Effect on funding.

A single wealthy attacker must not automatically control multiple verified identities.

## Attack B — Coordinated Infiltration

Model a group of rival supporters who join the supporters' trust with the intention of influencing future elections.

Configurable parameters:

- Number of hostile supporters.
- Joining schedule.
- Coordination effectiveness.
- Membership waiting period.
- Hostile turnout probability.
- Honest supporter turnout.
- Attack target.

Members should age through the simulation timeline.

They become eligible only after satisfying membership requirements.

Measure:

- Time required to become eligible.
- Percentage of eligible members controlled by the group.
- Voting influence.
- Probability of achieving the target outcome.

## Attack C — Sybil Attack

Model an attacker attempting to create multiple synthetic identities or membership accounts.

Important distinctions:

- Real synthetic persons.
- Claimed identities.
- Membership records.
- Voting credentials.

An attacker may control multiple claimed identities, but a strong identity-verification policy should prevent duplicate identities from obtaining legitimate voting rights.

Configurable parameters:

- Number of attempted identities.
- Verification strength.
- False acceptance probability.
- Verification cost.
- Account creation cost.
- Detection probability.
- Attacker budget.

Do not implement actual identity forgery or methods for bypassing real verification providers.

Use abstract probabilities and simulated verification outcomes.

Measure:

- Attempted identities.
- Accepted fraudulent identities.
- Rejected identities.
- Voting power gained.
- Detection rate.
- False positive rate.
- Cost per successful fraudulent vote.

## Attack D — Low-Turnout Capture

Model a highly organized minority participating in elections while ordinary supporters participate at lower rates.

Configurable parameters:

- Honest turnout.
- Hostile turnout.
- Hostile population share.
- Quorum requirements.
- Participation incentives.
- Voting model.

Measure:

- Hostile share of votes cast.
- Hostile share of eligible voting power.
- Proposal outcomes.
- Quorum achievement.
- Capture probability.

Distinguish majority of votes cast from majority of the eligible electorate.

## Attack E — Vote Buying and Coercion

Model an attacker attempting to influence legitimate supporters.

Use abstract behavioral probabilities rather than real-world coercion instructions.

Configurable parameters:

- Attacker budget.
- Cost per attempted influence.
- Probability of acceptance.
- Probability of detection.
- Supporter susceptibility distribution.
- Influence duration.
- Defensive monitoring strength.

Support both:

- Financial inducement.
- Abstract coercive influence.

Do not implement actual payment mechanisms or real-world targeting procedures.

Measure:

- Attempted influence.
- Successful influence.
- Votes shifted.
- Cost per shifted vote.
- Detection rate.
- Capture probability.

## Attack F — Account Compromise

Model an attacker gaining control of some legitimate voting credentials.

Use abstract compromise probabilities and simulated credential ownership.

Do not implement credential theft, phishing, or authentication exploitation.

Configurable parameters:

- Compromise probability.
- Number of targeted simulated accounts.
- Credential recovery probability.
- Detection probability.
- Time before election.
- Account recovery delay.

Measure:

- Credentials compromised.
- Credentials recovered.
- Unauthorized votes attempted.
- Unauthorized votes accepted.
- Election outcome changes.

## Attack G — Long-Term Infiltration

Model adversarial supporters joining a trust well before attempting influence.

This attack should use the multi-period simulation system.

Configurable parameters:

- Infiltration start date.
- Number of hostile members.
- Membership waiting period.
- Membership retention probability.
- Financial cost of maintaining memberships.
- Election schedule.
- Attack activation time.

Measure:

- Membership survival.
- Total infiltration cost.
- Time to eligibility.
- Influence at election time.
- Capture probability.

Compare short-term and long-term infiltration under the same governance rules.

# 8. Defensive Governance Policies

Implement independently configurable defenses.

## Identity Verification

Support different abstract verification strengths.

Measure both fraudulent acceptance and legitimate rejection.

## Membership Waiting Periods

Support arbitrary waiting periods.

Members should age naturally through the simulation timeline.

## Voting Caps

Use the existing capped and diminishing-returns voting models.

Do not duplicate their implementations.

## Quorum Requirements

Support:

- Minimum eligible-member turnout.
- Minimum eligible voting-weight participation.
- Configurable thresholds.

Quorum should be evaluated independently from proposal approval.

## Participation Incentives

Model abstract interventions that increase legitimate turnout.

Examples:

- Reminder campaigns.
- Easier remote participation.
- Membership engagement programs.

Use configurable turnout effects rather than assuming interventions always succeed.

## Suspicious Activity Detection

Implement a configurable simulated risk-scoring system.

Possible synthetic signals:

- Unusual membership creation volume.
- High concentrations of coordinated joining dates.
- Sudden changes in contribution patterns.
- Unusual voting synchronization.
- Repeated credential replacement events.

These signals are imperfect and may also describe legitimate behavior.

Track false positives and false negatives.

Do not assume suspicious activity proves malicious intent.

Support different review policies:

- Monitoring only.
- Manual-review simulation.
- Temporary credential restriction.
- Escalated identity verification.

Include procedural safeguards so legitimate supporters are not automatically disenfranchised by uncertain risk scores.

# 9. Multi-Period Simulation

Implement a simulation clock and event scheduler.

Support:

- Days.
- Months.
- Years.
- Membership joining.
- Membership aging.
- Membership renewal.
- Membership expiration.
- Contribution events.
- Elections.
- Economic updates.
- Attack activation.
- Defensive review events.

The simulation should be able to run for several years.

Example:

```yaml
timeline:
  start_date: "2027-01-01"
  duration_months: 36
  timestep: monthly

elections:
  interval_months: 12
```

Avoid coupling simulation logic to actual wall-clock time.

All events must be reproducible.

Define the ordering of events that occur on the same simulated date.

# 10. Economic Simulation Models

Introduce modular financial models for supporters, investors, and clubs.

## Supporter Economics

Model:

- Income.
- Wealth.
- Disposable income.
- Membership affordability.
- Contribution willingness.
- Membership renewal.
- Economic sensitivity.

Do not equate income with wealth.

Allow income and wealth to be correlated but independently configurable.

Support multiple income and wealth distributions.

## Membership Revenue

Model:

- Membership fees.
- Renewal rates.
- Membership growth.
- Membership attrition.
- Contribution revenue.
- Administrative costs.

Track revenue over time.

## Investor Contributions

Model:

- Investor capital contributions.
- Investor financial expectations.
- Investor ownership rights.
- Investor voting rights.
- Investor concentration.
- Investment timing.

Separate economic ownership from governance voting control.

Do not assume investment contributions automatically create voting rights.

Support scenarios where supporters retain protected voting control while outside investors provide capital.

## Club Financial State

Represent:

- Starting cash.
- Operating revenue.
- Operating expenses.
- Wage expenses.
- Transfer spending.
- Membership revenue.
- Investor contributions.
- Debt obligations.
- Financial reserves.

Use explicit accounting conventions.

Avoid double-counting contributions or confusing revenue with financing cash inflows.

Track cash balances separately from profitability.

## Sporting Performance

Implement a simple stochastic sporting-performance model.

Possible factors:

- Squad quality.
- Recruitment effectiveness.
- Injuries.
- Random performance variation.
- Management quality.

Use sporting performance to influence selected financial variables, such as ticket revenue, sponsorship, and prize money.

Do not assume sporting success guarantees financial success.

Document all modeled relationships.

# 11. Economic Shock Models

Implement interchangeable economic shock strategies.

Required scenarios:

### Revenue Loss

Simulate an unexpected decline in ticketing, sponsorship, or commercial revenue.

### Poor Recruitment

Simulate transfer expenditure that produces lower-than-expected sporting value.

### Stadium Closure

Simulate temporary loss of matchday revenue with optional continued operating costs.

### Economic Downturn

Simulate reduced supporter disposable income, membership renewal, merchandise revenue, and investor willingness.

Each shock should support:

- Start time.
- Duration.
- Severity.
- Recovery behavior.
- Affected financial variables.

Shocks should be independently configurable and composable.

Avoid double-applying effects to the same financial variable.

# 12. Combined Governance and Economic Simulation

Support experiments where governance and economic conditions interact.

Examples:

- A wealthy investor offers substantial funding in exchange for greater voting influence.
- A financial downturn reduces ordinary supporter participation.
- Membership fees increase club funding but exclude lower-income supporters.
- A stadium closure reduces club revenue and membership renewal.
- Voting caps reduce investor influence while preserving some financial incentives.
- Long-term infiltration becomes more expensive when membership fees increase.

Implement these interactions through explicit policies and shared simulation state.

Do not hardcode economic behavior into voting strategies.

# 13. Scenario Library

Create reusable YAML scenario configurations.

At minimum:

```text
configs/scenarios/
├── wealthy_takeover.yaml
├── coordinated_infiltration.yaml
├── sybil_attack.yaml
├── low_turnout_capture.yaml
├── vote_influence.yaml
├── account_compromise.yaml
├── long_term_infiltration.yaml
├── economic_downturn.yaml
├── stadium_closure.yaml
├── poor_recruitment.yaml
└── combined_crisis.yaml
```

Every scenario should specify:

- Population profile.
- Governance model.
- Attacker strategy.
- Attacker resources.
- Defensive policies.
- Economic conditions.
- Simulation duration.
- Trial count.
- Random seed.
- Metrics.
- Output directory.

Validate incompatible configurations and report meaningful errors.

# 14. Monte Carlo Experiment Runner

Extend the existing experiment runner.

Support experiments varying:

- Voting model.
- Hostile supporter percentage.
- Attacker wealth.
- Identity-verification effectiveness.
- Waiting period.
- Quorum.
- Honest turnout.
- Hostile turnout.
- Membership fees.
- Economic shock severity.
- Investor concentration.

Use matched baseline populations and common random numbers wherever appropriate.

Avoid regenerating unrelated random inputs between governance comparisons.

Record all configurations and seeds.

Support multiple attack strategies and defenses in the same experiment when their interactions are defined.

# 15. Research Metrics

Implement metrics for:

## Governance Capture

- Capture probability.
- Attacker voting-power share.
- Attacker share of votes cast.
- Percentage of proposals influenced.
- Election outcome changes.
- Time to capture.
- Financial cost of capture.

## Defensive Effectiveness

- Attack success rate with and without defense.
- Relative reduction in capture probability.
- Fraudulent identities detected.
- False positive rate.
- False negative rate.
- Legitimate supporters incorrectly restricted.
- Administrative cost.
- Participation impact.

## Economic Outcomes

- Membership revenue.
- Investor capital raised.
- Operating surplus or deficit.
- Cash balance.
- Financial runway.
- Membership affordability.
- Membership retention.
- Investor concentration.
- Recovery time after shocks.

## Combined Outcomes

- Capture probability under economic stress.
- Funding versus voting concentration.
- Participation versus membership fees.
- Financial resilience versus governance restrictions.

Calculate uncertainty intervals or Monte Carlo quantiles.

Do not report deterministic scenario outputs as empirical real-world probabilities.

# 16. Required Baseline Experiments

Implement the following experiments.

### Experiment A — Wealthy Investor Capture

Compare all six voting models under increasing attacker wealth.

Measure attacker voting power and capture probability.

### Experiment B — Coordinated Rival Infiltration

Vary hostile membership share, waiting periods, and turnout.

Measure election capture probability.

### Experiment C — Sybil Resistance

Vary verification effectiveness and attempted duplicate identities.

Measure fraudulent voting influence and false positives.

### Experiment D — Low-Turnout Capture

Vary ordinary supporter turnout and hostile participation.

Measure the effectiveness of quorum and participation incentives.

### Experiment E — Defensive Policy Comparison

Compare individual defenses and selected combinations.

Measure effectiveness, cost, and legitimate participation impact.

### Experiment F — Economic Resilience

Compare clubs with different membership fees, fanbase sizes, and investor structures under economic shocks.

### Experiment G — Combined Governance and Financial Crisis

Simulate a club experiencing declining revenue while an attacker attempts to increase governance influence.

Measure both capture risk and financial survival.

Use a manageable default trial count and allow larger experiments through configuration.

# 17. Results and Visualization

Export:

- Trial-level results.
- Scenario-level summaries.
- Time-series financial data.
- Attack event histories.
- Defensive event histories.
- Experiment metadata.
- Configuration snapshots.

Support CSV, JSON, and Parquet where appropriate.

Generate visualizations for:

- Capture probability versus attacker population share.
- Capture probability versus turnout.
- Voting concentration versus investor contribution.
- Defense effectiveness.
- False positive versus detection tradeoffs.
- Financial runway under different shocks.
- Membership revenue versus affordability.
- Governance resilience versus funding capacity.

Label all figures as synthetic simulation results.

# 18. Testing Requirements

Add automated tests covering:

- Each adversarial strategy.
- Attacker resource limits.
- Membership aging.
- Eligibility timing.
- Identity verification outcomes.
- Duplicate identity handling.
- Voting caps.
- Quorum enforcement.
- Defensive policy composition.
- Suspicious-activity detection.
- False positive handling.
- Economic accounting consistency.
- Financial shock application.
- Multi-period event ordering.
- Reproducibility.
- Combined attack and economic scenarios.
- Experiment exports.

Include analytical test cases where expected outcomes can be calculated exactly.

Ensure financial balances reconcile.

Test that attacks cannot create resources or voting rights outside the modeled rules.

Test that disabling a defense restores the expected unprotected behavior.

# 19. Documentation

Create or update:

### THREAT_MODEL.md

Document attacker objectives, capabilities, assumptions, attack surfaces, and limitations.

### ADVERSARIAL_ARCHITECTURE.md

Explain attack strategy interfaces, execution ordering, and state changes.

### ECONOMIC_MODEL.md

Document accounting rules, economic assumptions, financial flows, and shock models.

### SCENARIO_GUIDE.md

Explain how to create, configure, and run attack and economic scenarios.

### EXPERIMENTS.md

Document the baseline experiments and how to reproduce them.

### SIMULATION_ASSUMPTIONS.md

Distinguish synthetic assumptions from empirically validated relationships.

### README.md

Update setup, CLI commands, testing, and example workflows.

# 20. Performance Requirements

The simulation should support:

- 10,000 supporters.
- Multiple elections.
- Multi-year timelines.
- Hundreds of Monte Carlo trials.
- Multiple attack and defense combinations.

Design for eventual 100,000-supporter simulations.

Benchmark representative scenarios.

Avoid unnecessary full-population copies.

Optimize only demonstrated bottlenecks.

# 21. Implementation Order

Implement in this sequence:

1. Inspect the existing repository and run tests.
2. Define adversarial agent models and strategy interfaces.
3. Implement the multi-period simulation clock.
4. Implement membership lifecycle transitions.
5. Implement wealthy takeover and coordinated infiltration.
6. Implement low-turnout capture.
7. Implement abstract Sybil and credential-compromise models.
8. Implement vote influence and long-term infiltration.
9. Implement defensive policies.
10. Implement attacker and defense metrics.
11. Implement supporter and club economic models.
12. Implement investor contributions and membership revenue.
13. Implement economic shocks.
14. Integrate governance and economics.
15. Create the scenario library.
16. Extend Monte Carlo experiments.
17. Implement exports and visualizations.
18. Add comprehensive tests.
19. Update documentation.
20. Run and validate baseline experiments.

Work incrementally and keep the project runnable throughout development.

# 22. Definition of Done

Phase 3 is complete when:

- All seven adversarial strategies are implemented.
- Attackers have configurable objectives and resource constraints.
- Defensive policies can be independently enabled and combined.
- Membership aging and multi-period elections work.
- Identity verification and duplicate-account behavior can be simulated.
- Club financial models are operational.
- Membership and investor funding are tracked separately.
- Economic shocks can be applied.
- Governance and economic simulations interact correctly.
- All seven baseline experiments execute successfully.
- Monte Carlo results are reproducible.
- Capture, defense, and financial metrics are calculated.
- Results and visualizations are exported.
- Automated tests pass.
- Documentation is complete.

# 23. Final Execution Instructions

Do not stop at architecture planning or placeholder implementations.

Implement the working Phase 3 functionality and verify it.

Preserve the existing modular architecture.

Do not implement actual attacks against real systems.

Do not introduce real identity verification, real financial transactions, blockchain deployment, or a frontend.

Do not fabricate simulation results or benchmarks.

If a requested feature requires a major architectural change, explain the tradeoff and choose the smallest maintainable solution.

When finished, report:

1. Existing functionality discovered.
2. New Phase 3 modules implemented.
3. Files created and modified.
4. Architectural changes.
5. Test results.
6. Results of the seven baseline experiments.
7. Performance benchmarks.
8. Known limitations.
9. Research observations supported by the actual simulation outputs.
10. Recommended priorities for Phase 4.

**The finished Phase 3 engine must allow researchers to compare hostile takeover strategies, governance defenses, and financial conditions by changing configuration files rather than rewriting simulation code.**
