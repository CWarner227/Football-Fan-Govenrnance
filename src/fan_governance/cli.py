"""CLI adapter; library consumers need neither argparse nor plotting."""

import argparse
import json
import sys
from pathlib import Path
from time import perf_counter

import yaml
from pydantic import ValidationError

from fan_governance.core.config import load_config
from fan_governance.core.engine import effective_voting_specs
from fan_governance.core.registry import default_registry
from fan_governance.experiments.comparison import comparison_summary
from fan_governance.experiments.runner import ExperimentRunner
from fan_governance.output.exporters import export_results


def _scenario_configs(args):
    from fan_governance.scenarios.config import load_scenario

    if args.command == "scenario":
        configs = [load_scenario(args.config)]
    else:
        suite_path = Path(args.config).resolve()
        raw = yaml.safe_load(suite_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or set(raw) != {"experiments"}:
            raise ValueError("Scenario suite must contain only an experiments list of YAML paths")
        paths = raw["experiments"]
        if (
            not isinstance(paths, list)
            or not paths
            or any(not isinstance(p, str) or not p for p in paths)
        ):
            raise ValueError("Scenario suite experiments must be a nonempty list of YAML paths")
        config_root = (
            suite_path.parent.parent
            if suite_path.parent.name == "experiments"
            else suite_path.parent
        )
        configs = []
        for entry in paths:
            relative = Path(entry)
            path = (suite_path.parent / relative).resolve()
            if (
                relative.is_absolute()
                or not path.is_relative_to(config_root)
                or path.suffix.lower() not in {".yaml", ".yml"}
            ):
                raise ValueError(
                    "Suite entries must be relative YAML paths within the configuration directory"
                )
            configs.append(load_scenario(path))
        if len({config.name for config in configs}) != len(configs):
            raise ValueError("Scenario suite names must be unique")
    for config in configs:
        if args.output:
            config.output.directory = (
                Path(args.output) / config.name
                if args.command == "scenario-suite"
                else Path(args.output)
            )
    if len({config.output.directory.resolve() for config in configs}) != len(configs):
        raise ValueError("Scenario suite output directories must be unique")
    return configs


def _run_scenarios(args):
    from fan_governance.scenarios.output import export_scenario, plot_scenario
    from fan_governance.scenarios.runner import run_scenario

    for config in _scenario_configs(args):
        started = perf_counter()
        result = run_scenario(config)
        destination = export_scenario(
            config,
            result.summary,
            result.elections,
            result.timeseries,
            result.events,
            result.metadata,
        )
        if args.plot:
            plot_scenario(
                result.summary, result.elections, result.timeseries, destination / "figures"
            )
        print(
            f"Synthetic scenario: {config.name}; trials={config.experiment.trials}; seed={config.experiment.seed}; elections={len(result.elections)}; elapsed={perf_counter() - started:.3f}s"
        )
        print(f"Results: {destination.resolve()}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Synthetic fan governance research simulator")
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("models", help="List registered models")
    for command in ("simulate", "experiment", "baseline", "scenario", "scenario-suite"):
        command_parser = subcommands.add_parser(command)
        command_parser.add_argument("--config", required=True)
        command_parser.add_argument("--output", help="Override configured output directory")
        command_parser.add_argument(
            "--plot", action="store_true", help="Write optional summary plot"
        )
    args = parser.parse_args(argv)
    if args.command == "models":
        print(json.dumps(default_registry().names(), indent=2))
        return 0
    started = perf_counter()
    try:
        if args.command in {"scenario", "scenario-suite"}:
            return _run_scenarios(args)
        config = load_config(args.config)
        if args.output:
            config.output.directory = args.output
        if args.command == "simulate":
            if len(effective_voting_specs(config)) != 1:
                raise ValueError(
                    "simulate requires one voting strategy; use experiment for comparisons"
                )
            if config.experiment.trials != 1 or any(
                getattr(config.experiment, key) is not None
                for key in (
                    "population_sizes",
                    "waiting_periods",
                    "participation_levels",
                    "wealth_distributions",
                    "population_profiles",
                    "participation_models",
                    "proposal_categories",
                )
            ):
                raise ValueError(
                    "simulate requires a single trial without grid axes; use experiment"
                )
        experiment = ExperimentRunner()

        def report_progress(scenario, completed, total):
            if total > 1 and (completed == 1 or completed % 10 == 0 or completed == total):
                print(f"Scenario {scenario}: {completed}/{total} trials complete", flush=True)

        results = experiment.run(config, progress=report_progress)
        summary = comparison_summary(results)
        if args.command == "baseline":
            from fan_governance.output.baseline import export_baseline

            paths = export_baseline(
                results, config, config.output.directory, elapsed_seconds=experiment.elapsed_seconds
            )
        else:
            paths = export_results(results, config.output.directory, config.output.formats)
            summary.to_csv(config.output.directory / "summary.csv", index=False)
        manifest = {
            "configuration": config.model_dump(mode="json"),
            "simulation_seconds": experiment.elapsed_seconds,
            "total_seconds_before_manifest": perf_counter() - started,
            "result_count": len(results),
            "versions": {
                k: results[0].execution_metadata[k]
                for k in (
                    "python",
                    "numpy",
                    "pandas",
                    "pydantic",
                    "fan_governance",
                    "rng",
                    "stream_scheme",
                )
            },
        }
        (config.output.directory / "manifest.json").write_text(
            json.dumps(manifest, indent=2, allow_nan=False), encoding="utf-8"
        )
        if args.plot:
            if args.command == "baseline":
                from fan_governance.output.research_plotting import plot_research_results

                plot_research_results(results, config.output.directory / "figures")
            else:
                from fan_governance.output.plotting import plot_results

                plot_results(results, config.output.directory / "comparison.png")
        print(
            f"Experiment: {config.experiment.name}; population={','.join(str(n) for n in sorted({r.population_size for r in results}))}; models={','.join(sorted({r.voting_model for r in results}))}; trials={config.experiment.trials}; seed={config.experiment.seed}"
        )
        print(
            f"Completed {len(results)} elections in {experiment.elapsed_seconds:.3f}s simulation / {perf_counter() - started:.3f}s total"
        )
        print(summary.to_string(index=False))
        print("Results: " + ", ".join(str(path.resolve()) for path in paths.values()))
    except (
        OSError,
        ValueError,
        ValidationError,
        yaml.YAMLError,
        OverflowError,
        FloatingPointError,
    ) as error:
        print(f"Configuration or execution error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
