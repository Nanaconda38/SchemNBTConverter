from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .errors import ConversionError
from .writer import convert_file

SUPPORTED_SUFFIXES = {".schem", ".litematic"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="schem-nbt-converter",
        description="Convert Minecraft .schem and .litematic files into vanilla .nbt structures.",
    )
    parser.add_argument("files", nargs="*", help="Files or folders containing .schem/.litematic files")
    parser.add_argument("-o", "--output", type=Path, help="Output directory")
    parser.add_argument("--max-size", type=int, default=48, help="Maximum chunk size (default: 48)")
    parser.add_argument("--no-split", action="store_true", help="Do not split oversized structures")
    parser.add_argument("--exclude-air", action="store_true", help="Do not export air blocks")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing output files")
    parser.add_argument(
        "--flatten",
        action="store_true",
        help="Do not reproduce subdirectories from imported folders",
    )
    parser.add_argument("--gui", action="store_true", help="Open the graphical interface")
    return parser


def collect_jobs(inputs: list[str]) -> list[tuple[Path, Path | None]]:
    jobs: list[tuple[Path, Path | None]] = []
    seen: set[Path] = set()

    for raw in inputs:
        path = Path(raw).expanduser().resolve()
        if path.is_dir():
            for candidate in sorted(path.rglob("*")):
                if candidate.is_file() and candidate.suffix.lower() in SUPPORTED_SUFFIXES:
                    resolved = candidate.resolve()
                    if resolved not in seen:
                        jobs.append((resolved, path))
                        seen.add(resolved)
        elif path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES:
            if path not in seen:
                jobs.append((path, None))
                seen.add(path)
        else:
            print(f"Skipped: {raw} (not found or unsupported format)", file=sys.stderr)

    return jobs


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.gui or not args.files:
        from .gui import run_gui

        run_gui()
        return 0
    if args.output is None:
        print("Error: --output is required in command-line mode.", file=sys.stderr)
        return 2
    if args.max_size < 1:
        print("Error: --max-size must be a positive integer.", file=sys.stderr)
        return 2

    jobs = collect_jobs(args.files)
    if not jobs:
        print("Error: no .schem or .litematic files were found.", file=sys.stderr)
        return 2

    failures = 0
    for filename, source_root in jobs:
        try:
            outputs = convert_file(
                filename,
                args.output,
                max_size=args.max_size,
                split_large=not args.no_split,
                include_air=not args.exclude_air,
                overwrite=args.overwrite,
                source_root=None if args.flatten else source_root,
                progress=print,
            )
            print(f"OK: {filename} -> {len(outputs)} file(s) in {outputs[0].parent}")
        except (ConversionError, OSError, ValueError) as exc:
            failures += 1
            print(f"ERROR: {filename}: {exc}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
