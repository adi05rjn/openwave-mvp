"""Human CLI compatibility plus a JSON-only agent command surface."""
from __future__ import annotations

import argparse
import json
import sys

from .experiment import ExperimentError, experiment_schema, load_experiment


def build_parser() -> argparse.ArgumentParser:
    """Historical options remain available without a subcommand."""
    parser = argparse.ArgumentParser(description="OpenWave rectangular-waveguide modal solver")
    parser.add_argument("--width-mm", type=float, default=22.86, help="Waveguide width in millimetres")
    parser.add_argument("--height-mm", type=float, default=10.16, help="Waveguide height in millimetres")
    parser.add_argument("--nx", type=int, default=81)
    parser.add_argument("--ny", type=int, default=41)
    parser.add_argument("--modes", type=int, default=4)
    parser.add_argument("--plot", default="artifacts/mode1.png")
    parser.epilog = "Agent commands: openwave schema; openwave validate FILE; openwave run FILE --output DIR"
    return parser


class AgentParser(argparse.ArgumentParser):
    def error(self, message):
        raise ExperimentError(message)


def _emit(value, *, error=False):
    print(json.dumps(value, sort_keys=True, allow_nan=False), file=sys.stderr if error else sys.stdout)


def _agent_main(argv: list[str]) -> int:
    parser = AgentParser(description="Headless OpenWave experiments")
    commands = parser.add_subparsers(dest="command", required=True, parser_class=AgentParser)
    commands.add_parser("schema", help="Print the experiment JSON Schema")
    commands.add_parser("validate", help="Validate an experiment without solving").add_argument("experiment")
    run = commands.add_parser("run", help="Solve an experiment into a new artifact directory")
    run.add_argument("experiment")
    run.add_argument("--output", required=True)
    try:
        args = parser.parse_args(argv)
        if args.command == "schema":
            _emit(experiment_schema())
        elif args.command == "validate":
            experiment = load_experiment(args.experiment)
            _emit({"status": "valid", "schema_version": experiment["schema_version"]})
        else:
            from .runner import run_experiment
            _emit(run_experiment(load_experiment(args.experiment), args.output))
        return 0
    except (ExperimentError, OSError) as exc:
        _emit({"status": "error", "error": {"code": "invalid_input" if isinstance(exc, ExperimentError) else "io_error", "message": str(exc)}}, error=True)
        return 2
    except (RuntimeError, ValueError, ArithmeticError) as exc:
        _emit({"status": "error", "error": {"code": "execution_failed", "message": str(exc)}}, error=True)
        return 1


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv and not argv[0].startswith("-"):
        return _agent_main(argv)
    args = build_parser().parse_args(argv)
    from .plotting import save_mode_plot
    from .waveguide import RectangularWaveguide
    guide = RectangularWaveguide(args.width_mm * 1e-3, args.height_mm * 1e-3, args.nx, args.ny)
    modes = guide.solve_te_modes(args.modes)
    print("mode, cutoff_GHz")
    for mode in modes:
        print(f"{mode.index}, {mode.cutoff_frequency_hz / 1e9:.6f}")
    save_mode_plot(guide.grid, modes[0], args.plot)
    print(f"Saved first-mode field plot to {args.plot}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
