# Architecture

Phase 2 extends the original standalone Python package. Population generation,
membership eligibility, participation, preferences, voting weight, election mechanics,
metrics and export remain separate, replaceable components. There are no persistent
service dependencies or real blockchain transactions.

```text
configs/                 YAML experiments, governance rules and synthetic profiles
src/fan_governance/
  core/                  validation, protocols, streams, registry, engine facade
  agents/                supporter traits, distributions, population generation
  clubs/                 club boundary, canonical identities and affordability
  membership/            club membership records and eligibility policy
  voting/                four formulas, hybrid routing, forecast-history expertise
  participation/         independent, constant and attribute-based turnout
  preferences/           random, policy-aligned and attribute-based binary choices
  elections/             proposal/results, frozen snapshots, injected runner
  metrics/               concentration, participation, outcomes, wealth representation
  experiments/           matched trials, scenario grids, summaries, subprocess benchmarks
  output/                structured exports, provenance, optional research figures
  cli.py                 simulate, experiment, baseline and model inventory
```

## Data flow

1. `load_config` normalizes compact/legacy population YAML and validates it with
   Pydantic. Unknown schema fields and conflicting aliases fail explicitly.
2. `ExperimentRunner` expands scenario axes and constructs registered components.
   `proposal_from_config` merges proposal-specific eligibility, waiting period,
   quorum and approval threshold into governance defaults. A proposal-specific
   `voting_strategy` replaces the comparison list with one strategy. Hybrid category
   routing is a separate strategy, not a runner branch.
3. `SyntheticPopulationGenerator` creates supporters and membership records using
   named streams. Numeric marginals, categorical policy preferences, financial modes
   and synthetic forecasting histories are configured independently.
4. `Club` validates canonical supporter identities, unique member record IDs and
   membership references. It checks authoritative membership contributions against
   supporter wealth unless that supporter explicitly permits unfunded contributions.
5. `ElectionRunner.prepare` freezes supporter/member copies, including supporter
   extension attributes, and evaluates eligibility once. A custom policy cannot return
   duplicate canonical people or unknown records. The default policy requires active,
   verified membership and sufficient membership age.
6. Preparation realizes behavior once per canonical person with a membership. Eligible
   people use the selected eligible record; other people use their lexically first
   member record. Both turnout and preferences are drawn even for nonparticipants
   and ineligible people, preserving stable common-random-number comparisons. Behavior
   receives a proposal with neutral `voting_method`/`voting_strategy`, so comparison
   order cannot choose its behavioral inputs.
7. The immutable `ElectionSnapshot` stores frozen people/records, eligible member IDs,
   serialized proposal, realized turnout/preferences, trial/seed and input digest.
   Every strategy in a matched comparison consumes this same snapshot. Mutating
   original club records afterward cannot change the prepared election.
8. `ElectionRunner.run` asks only the injected strategy for finite nonnegative weights,
   aggregates valid ballots, checks count quorum and weighted approval, and sends
   immutable ballot tuples to the injected metric calculator. Strategy-specific
   formulas stay outside the election loop.
9. Results separate scientific outputs from timing metadata. The experiment retains
   results, not populations from completed trials. Export and plotting consume results.

The `SimulationEngine` facade supports direct injection for a single election;
callers using it or the low-level runner are responsible for matching injected policy
parameters to proposal metadata. The configuration composition root is `ExperimentRunner`.
The CLI controls files and presentation, not voting policy.

## Domain and extension contracts

`core/interfaces.py` defines structural protocols; implementations need not inherit
from them. The registry constructs named voting, eligibility, participation and
preference models from parameter mappings. A custom population generator or metric
calculator is injected directly. YAML does not import arbitrary Python code.

`Supporter` represents a canonical person and synthetic traits. `fan_id`,
`participation_rate` and `knowledge_score` are aliases of the original fields.
`Membership` represents club membership; its age and contribution are authoritative
for eligibility and financial voting. Club IDs and independent membership records
support multiple club objects without implementing a multi-club economy.

`GovernanceProposal` carries category, binary options, thresholds, eligibility and
metadata. `VotingContext` supplies proposal category/metadata to routing strategies.
`HybridVoting` delegates to registered strategies; `ExpertiseVoting` derives reliability
from explicitly synthetic historical counts, separately from latent knowledge.

## Reproducibility and scenarios

Component seeds are the first 128 bits of SHA-256 of
`fan-governance-v1:{master_seed}:{trial_id}:{component_name}`, as a big-endian integer.
NumPy PCG64 uses these seeds. `RandomStreams.generator(name)` returns a fresh generator
at the component's initial state; retain that generator while sampling the component.

Population attributes, copula, adversarial labels, contribution fractions, policy,
forecast counts/history, turnout and preferences have named streams. A population
seed override affects population streams; the experiment seed still controls behavior.
Trial IDs provide independent streams. Scenarios in a trial share streams by design;
strategy order/count cannot alter prepared inputs. Population-size changes do not
guarantee a prefix for every marginal or copula. Plugins consuming extra variates
can change later people within their component, not unrelated streams.

Axes include population size or named full population profiles, wealth distributions,
waiting periods, participation levels, participation model specifications and proposal
categories. Profiles cannot be combined with size/wealth axes. Each profile is a full
`PopulationConfig`, not a partial overlay. Each scenario/trial has its own snapshot;
models within it share exactly the same inputs.

Results record configuration, component seeds, package/environment/source provenance,
a realization digest and complete input digest. Digests aid integrity checks; they
are not ballot ledgers or fairness proofs. Reproduction requires the same dependency
versions and source; retain `uv.lock` and use `uv sync --locked`. Timing is nondeterministic.

## Metrics, performance and future work

`StandardMetrics` reports potential eligible concentration, realized participating
concentration, equal-vote counterfactual outcomes and wealth representation. Wealth
rank groups are fixed on the eligible electorate for both potential and realized power.
Custom metric output cannot change the runner's quorum or approval result.

Sampling and concentration use NumPy. Validated records, snapshot copying and
per-person strategy calls favor clarity over maximal throughput. Canonical sorting
and wealth ranks require O(N log N) work; full results stay in memory. The benchmark
module measures three workloads in fresh subprocesses and labels absolute peak RSS.
It excludes configuration/import/export time from the timed runner call.

Future economic, adversarial or blockchain orchestration can compose these protocols.
There is no attack simulator, financial ledger, sporting-outcome model, event scheduler,
production identity system or on-chain adapter in Phase 2.
