# Phase 3 scenario guide

The scenario library is synthetic and is not calibrated to a real club. Its default 200-person populations and three trials prioritize a quick reproducible smoke comparison. Income, wealth, costs, risk probabilities, and shock severities are assumptions specified in YAML, not estimated real-world quantities.

## Configuration layout

Each YAML in `configs/scenarios` is a complete scenario. `simulation` embeds the existing Phase 2 population, governance, proposal, participation, preference, and six voting strategies. The outer level adds `timeline`, `elections`, `attacks`, `defenses`, `economics`, `experiment`, `metrics`, and `output`. The outer experiment seed and trial count control Phase 3 runs. Avoid nested Phase 2 grid axes; use outer `experiment.grid`.

The six configured voting models are equal, proportional, capped, diminishing returns, hybrid, and expertise. Hybrid uses capped voting for funding and equal voting for constitutional questions. These differences concern voting weight, not an automatic grant of economic ownership.

The named examples are wealthy takeover, coordinated infiltration, Sybil attack, low-turnout capture, vote influence, account compromise, long-term infiltration, economic downturn, stadium closure, poor recruitment, and combined crisis. The long-term example spans 24 months, waits 365 days, and activates hostile voting at day 540. The combined example applies revenue loss and downturn shocks, includes protected outside capital without voting rights, and models economic turnout sensitivity.

## Reproducible comparisons

Run one complete scenario from the repository root:

```powershell
.venv\Scripts\python.exe -m fan_governance scenario --config configs/scenarios/sybil_attack.yaml
```

Run all seven baseline experiments and generate their optional figures:

```powershell
.venv\Scripts\python.exe -m fan_governance scenario-suite --config configs/phase3_experiments/suite.yaml --plot
```

`--output` overrides the destination; suite runs create a separate scenario subdirectory. Plotting requires the optional plotting dependency. Suite entries resolve relative to the suite YAML directory.

Every scenario requires three variants: `control`, `unprotected`, and `defended`. Control disables attacks and shocks. Unprotected retains attacks and shocks with weak identity and without configured defenses. Defended applies the configured defenses. Consequently, defended versus control includes the attack and shock effects; defended versus unprotected isolates the configured defensive intervention within that modeled crisis.

All outputs should retain the scenario configuration, seed, grid values, model name, trial, and variant. Capture concerns the configured simulated objective, such as an attacker majority of votes cast. Always inspect quorum and eligible-power shares separately. A lower capture rate can coincide with lower legitimate participation or lower funding.

## Parameters and extension

An attacker entry specifies its registry `name`, `attacker_id`, financial and operational budgets, objective, and strategy-specific `parameters`. Strategy names are `wealthy_takeover`, `coordinated_infiltration`, `sybil`, `low_turnout`, `vote_influence`, `account_compromise`, and `long_term_infiltration`.

Defense entries specify a registry `name` and `parameters`. Identity parameters include strength, false acceptance, legitimate rejection, and verification cost. Waiting periods use `days`; caps use `cap`; quorum uses `threshold` and `basis` (`eligible_members` or `eligible_weight`). Participation uses `boost`, `success_probability`, and `cost_per_member`. Monitoring supports risk weights, review policies, investigation error, finite restriction duration, review costs, and appeal probability. Multiple quorum policies must use the same basis.

Economic cash inputs and expenses are monthly amounts in a common synthetic currency unit. Membership fees, renewal, investor capital, debt, and contributions are tracked separately. Shocks use a start month, duration, severity, and optional recovery period. Repeated shock types should have distinct `shock_id` values. See [ECONOMIC_MODEL.md](ECONOMIC_MODEL.md) for accounting and overlapping-shock conventions.

## Baseline experiment library

`configs/phase3_experiments/suite.yaml` lists seven standalone scenario experiment files:

| Experiment | Variation |
| --- | --- |
| A | Wealthy contribution budgets across six voting models |
| B | Hostile joining share, waiting period, and ordinary turnout |
| C | Identity strength and fraudulent identity attempts |
| D | Ordinary turnout, hostile turnout, and quorum |
| E | Individual and combined defenses |
| F | Membership fee, population size, shock severity, outside capital |
| G | Revenue-loss severity and wealthy attacker contributions |

`experiment.grid` forms a Cartesian product. Dotted paths can address indexed lists, for example `defenses.0.parameters.strength: [0, 0.8, 1]`. To compare defense packages, supply a list of complete `defenses` lists as grid values. Defaults are 100–300 people, three trials, monthly ticks, and CSV/JSON exports; enable Parquet only with its optional dependency installed. More trials improve Monte Carlo precision and increase runtime linearly with trial count; grid dimensions multiply runtime.

Three trials do not establish a reliable real-world probability. Report Monte Carlo uncertainty, the denominator used for error rates, and all modeled assumptions. Compare administrative cost, legitimate restrictions, funding, cash, and capture together. Source requirements and limitations are recorded in [PHASE3_REQUEST.md](PHASE3_REQUEST.md) and [THREAT_MODEL.md](THREAT_MODEL.md).
