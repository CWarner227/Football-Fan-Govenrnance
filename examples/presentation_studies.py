"""Generate and optionally import matched, dashboard-bounded presentation studies.

Run from the repository root with --import-url http://127.0.0.1:8000 to populate
Saved configurations. This prepares configurations; it never starts simulations.
"""

import argparse
import json
from copy import deepcopy
from pathlib import Path

import yaml

from fan_governance.api.validation import validate_configuration

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENTS = ROOT / "configs" / "phase3_experiments"
DESTINATION = ROOT / "configs" / "presentation_studies"
SEEDS = (11001, 11002, 11003, 11004)


def source(letter):
    path = next(EXPERIMENTS.glob(f"{letter}_*.yaml"))
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    raw["simulation"]["population"]["seed"] = None
    raw["economics"]["record_individual_transactions"] = False
    raw["experiment"]["grid"] = {}
    return raw


def study_groups():
    groups = []

    def add(key, title, raw, description):
        groups.append((key, title, raw, description))

    baseline = source("A")
    baseline.update(attacks=[], defenses=[], honest_turnout=None)
    baseline["economics"] = {"enabled": False}
    baseline["timeline"]["duration_months"] = 1
    baseline["elections"]["interval_months"] = 1
    ordinary = deepcopy(baseline["simulation"]["population"])
    ordinary["size"] = 10000
    unequal = deepcopy(ordinary)
    unequal["wealth"] = {"distribution": "lognormal", "mean": 10, "sigma": 2}
    low = deepcopy(ordinary)
    low["participation_rate"] = {"distribution": "constant", "value": 0.15}
    baseline["simulation"]["population"] = ordinary
    baseline["experiment"]["grid"] = {
        "simulation.population": [ordinary, unequal, low],
        "simulation.proposal.category": ["constitutional", "funding"],
    }
    add(
        "01-baseline",
        "01 Voting baseline",
        baseline,
        "10,000 supporters; ordinary/wealth-unequal/low-participation profiles x two proposal categories. "
        "Use CONTROL for baseline plots; the other required variants are redundant matched references, not extra samples. "
        "Honest turnout uses the population participation model; economics disabled.",
    )

    wealthy = source("A")
    wealthy["attacks"][0]["operational_budget"] = 1
    wealthy["experiment"]["grid"] = {
        "attacks.0.parameters.contribution_budget": [5000, 50000, 250000],
        "attacks.0.financial_budget": [300000],
    }
    add(
        "02-wealthy",
        "02 Wealthy capture",
        wealthy,
        "200 supporters; attacker contributions 5k/50k/250k; 300k financial budget; "
        "one operation permits the specified single lump-sum join. Compare matched variants.",
    )

    for strength in (0, 0.8, 1):
        sybil = source("C")
        sybil["defenses"][0]["parameters"]["strength"] = strength
        actors = []
        for number in (50, 200, 400):
            actor = deepcopy(sybil["attacks"][0])
            actor["operational_budget"] = number
            actor["parameters"]["attempted_identities"] = number
            actors.append([actor])
        sybil["experiment"]["grid"] = {"attacks": actors}
        add(
            f"03-sybil-v{strength}",
            f"03 Sybil verification {strength}",
            sybil,
            "200 supporters; 50/200/400 attempted aliases (0.25/1/2 per honest supporter). "
            f"Verification strength {strength}; operational budget equals attempted identities. "
            "Base false-acceptance probability 0.5 and genuine rejection 0.01 are synthetic assumptions.",
        )

    for turnout in (0.2, 0.6):
        for share in (0.1, 0.3):
            infiltration = source("B")
            infiltration["timeline"]["duration_months"] = 12
            infiltration["elections"]["interval_months"] = 3
            infiltration["honest_turnout"] = turnout
            actor = infiltration["attacks"][0]
            actor["parameters"]["hostile_share"] = share
            actor["operational_budget"] = 100
            infiltration["experiment"]["grid"] = {"defenses.1.parameters.days": [0, 90, 180]}
            add(
                f"04-infiltration-t{turnout}-h{share}",
                f"04 Infiltration turnout {turnout} hostile {share}",
                infiltration,
                "200 ordinary supporters; genuine hostile joins on day zero, no aliases. "
                "100 operations cover the maximum 86 intended joins. Quarterly elections expose "
                "90/180-day waiting periods before and after expiry; read election/time-series rows.",
            )

    quorum = {"name": "quorum", "parameters": {"threshold": 0.4, "basis": "eligible_members"}}
    incentive = {
        "name": "participation_incentive",
        "parameters": {"boost": 0.2, "success_probability": 0.8, "cost_per_member": 0.1},
    }
    verification = {"name": "identity_verification", "parameters": {"strength": 1}}
    for honest in (0.2, 0.6):
        for hostile in (0.5, 1.0):
            turnout = source("D")
            turnout["honest_turnout"] = honest
            turnout["attacks"][0]["operational_budget"] = 30
            turnout["attacks"][0]["parameters"]["hostile_turnout"] = hostile
            turnout["experiment"]["grid"] = {
                "defenses": [
                    [verification],
                    [verification, quorum],
                    [verification, incentive],
                    [verification, quorum, incentive],
                ]
            }
            add(
                f"05-turnout-h{honest}-a{hostile}",
                f"05 Turnout honest {honest} hostile {hostile}",
                turnout,
                "200 supporters; 15% recruited, 30 operations. Four defense packages: verification "
                "alone, +quorum, +incentive, +both. Separate cast-weight capture from proposal passage.",
            )

    defense = source("E")
    policies = yaml.safe_load(next(EXPERIMENTS.glob("E_*.yaml")).read_text())["experiment"]["grid"][
        "defenses"
    ]
    defense["attacks"][0]["parameters"]["attempted_identities"] = 200
    defense["attacks"][0]["operational_budget"] = 200
    defense["elections"]["interval_months"] = 3
    for index, start in enumerate(range(0, len(policies), 3), 1):
        subset = deepcopy(defense)
        subset["experiment"]["grid"] = {"defenses": policies[start : start + 3]}
        add(
            f"06-defenses-set{index}",
            f"06 Defense policies set {index}",
            subset,
            f"Policies {start + 1}-{min(start + 3, len(policies))} of the existing ten-policy study, "
            "against 200 attempted aliases in a 200-supporter population. Quarterly elections; "
            "matched seeds across sets. Compare cost, capture, and restrictions; do not pool duplicate controls.",
        )

    economics = source("F")
    economics["experiment"]["grid"] = yaml.safe_load(
        next(EXPERIMENTS.glob("F_*.yaml")).read_text()
    )["experiment"]["grid"]
    add(
        "07-economics",
        "07 Economic resilience",
        economics,
        "16 cells: fees 0/30 x population 100/300 x downturn severity 0.3/0.7 x no capital/30k capital. "
        "Outside capital has ownership but no voting rights. Report cash/runway/retention by cell; "
        "population and club budgets are explicit assumptions, not per-capita matched funding.",
    )

    combined = source("G")
    combined["attacks"][0]["operational_budget"] = 1
    combined["experiment"]["grid"] = yaml.safe_load(next(EXPERIMENTS.glob("G_*.yaml")).read_text())[
        "experiment"
    ]["grid"]
    add(
        "07-combined",
        "07 Combined crisis extension",
        combined,
        "200 supporters; four cells: revenue-loss severity 0.3/0.7 x contribution budget 10k/100k. "
        "Downturn severity stays 0.5. One lump-sum attack operation; retain matched shock/defense references.",
    )
    return groups


def build_bundle():
    records = []
    for key, title, raw, notes in study_groups():
        for stage, seed, trials in [
            ("pilot", 99001, 10),
            *[(f"batch{index:02d}", seed, 25) for index, seed in enumerate(SEEDS, 1)],
        ]:
            config = deepcopy(raw)
            config["name"] = f"presentation_v1_{key}_{stage}".replace(".", "p")
            config["experiment"].update(trials=trials, seed=seed)
            config["output"]["directory"] = f"results/presentation/{key}/{stage}"
            normalized, workload = validate_configuration(config)
            label = "PILOT 10 trials" if stage == "pilot" else f"B{stage[-2:]} of 04 - 25 trials"
            records.append(
                {
                    "group": key,
                    "stage": stage,
                    "name": f"Study {title} | {label}",
                    "description": f"Presentation v1; seed {seed}. {notes} "
                    "Pilot is separate from the 100-trial presentation dataset. Run each B01-B04 once.",
                    "configuration": portable_configuration(normalized.model_dump(mode="json")),
                    "workload": workload,
                    "file": normalized.name + ".yaml",
                }
            )
    return records


def portable_configuration(configuration):
    """Compare output destinations portably; scientific parameters retain exact equality."""
    result = deepcopy(configuration)
    for section in (result, result.get("simulation", {})):
        output = section.get("output", {})
        if isinstance(output.get("directory"), str):
            output["directory"] = output["directory"].replace("\\", "/")
    return result


def import_bundle(records, client):
    """Validate the entire bundle before writes; preserve existing records and reject conflicts."""
    normalized = []
    for record in records:
        response = client.post(
            "/api/v1/configurations/validate", json={"configuration": record["configuration"]}
        )
        response.raise_for_status()
        normalized.append(dict(record, configuration=response.json()["configuration"]))
    existing = {}
    offset = 0
    while True:
        response = client.get(f"/api/v1/configurations?limit=500&offset={offset}")
        response.raise_for_status()
        page = response.json()
        for item in page["items"]:
            existing.setdefault(item["name"], []).append(item)
        offset += len(page["items"])
        if offset >= page["total"]:
            break
    for record in normalized:
        matches = existing.get(record["name"], [])
        if matches and (
            len(matches) != 1
            or matches[0]["description"] != record["description"]
            or portable_configuration(matches[0]["configuration"])
            != portable_configuration(record["configuration"])
        ):
            raise ValueError(
                f"Configuration name already exists with different content: {record['name']}"
            )
    created = 0
    for record in normalized:
        if record["name"] in existing:
            continue
        response = client.post(
            "/api/v1/configurations/save",
            json={key: record[key] for key in ("name", "description", "configuration")},
        )
        response.raise_for_status()
        created += 1
    return {"created": created, "existing": len(records) - created}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--import-url", help="Running dashboard URL; otherwise generate files only")
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="Import without writing source files (container mode)",
    )
    args = parser.parse_args()
    records = build_bundle()
    if not args.no_write:
        DESTINATION.mkdir(parents=True, exist_ok=True)
        for record in records:
            (DESTINATION / record["file"]).write_text(
                "# "
                + record["name"]
                + "\n# "
                + record["description"]
                + "\n"
                + yaml.safe_dump(record["configuration"], sort_keys=False),
                encoding="utf-8",
            )
        (DESTINATION / "manifest.json").write_text(
            json.dumps(
                [
                    {key: value for key, value in record.items() if key != "configuration"}
                    for record in records
                ],
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    print(f"Prepared {len(records)} configurations across 19 study groups.")
    if args.import_url:
        import httpx

        with httpx.Client(base_url=args.import_url.rstrip("/"), timeout=60) as client:
            print(json.dumps(import_bundle(records, client)))


if __name__ == "__main__":
    main()
