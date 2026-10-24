#!/usr/bin/env python3
"""Microbenchmarks: bare dict vs current AliasDict vs pre-rewrite UserDict design.

Usage:
    uv run python benchmarks/bench.py
    make bench

Numbers vary by machine/Python; relative ratios are what matter.
"""

from __future__ import annotations

import platform
import sys
import timeit
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aldict import AliasDict  # noqa: E402
from benchmarks.legacy import LegacyAliasDict  # noqa: E402

N = 10_000
REPEAT = 7
NUMBER_LOOKUP = 5
NUMBER_VIEW = 5
INNER_LOOKUP = 1000


def _build_maps(n: int = N):
    origins = {f"k{i}": i for i in range(n)}
    aliases = {f"k{i}": [f"a{i}"] for i in range(n)}
    return origins, aliases


def _setup():
    origins, aliases = _build_maps()
    d = dict(origins)
    ad = AliasDict(origins, aliases=aliases)
    legacy = LegacyAliasDict(origins, aliases=aliases)
    ok = f"k{N // 2}"
    ak = f"a{N // 2}"
    return d, ad, legacy, ok, ak


SETUP = "from benchmarks.bench import _setup\nd, ad, legacy, ok, ak = _setup()\n"


def _time(stmt: str, *, number: int) -> float:
    timer = timeit.Timer(stmt, setup=SETUP)
    timer.timeit(number=1)
    return min(timer.repeat(REPEAT, number)) / number


def _ns(seconds: float) -> float:
    return seconds * 1e9


def _fmt_time(seconds: float) -> str:
    ns = _ns(seconds)
    if ns >= 1_000_000:
        return f"{ns / 1_000_000:.2f} ms"
    if ns >= 1_000:
        return f"{ns / 1_000:.1f} µs"
    return f"{ns:.0f} ns"


def _rel(seconds: float, baseline: float) -> str:
    return f"{seconds / baseline:.2f}×"


def _ratio_label(old: float, new: float) -> str:
    r = old / new
    return f"{r:.1f}× faster" if r >= 1 else f"{1 / r:.1f}× slower"


def run_lookups() -> list[tuple[str, float]]:
    cases = [
        ("dict[origin]", "d[ok]"),
        ("AliasDict origin get (current)", "ad[ok]"),
        ("AliasDict alias get (current)", "ad[ak]"),
        ("LegacyAliasDict origin get (UserDict)", "legacy[ok]"),
        ("LegacyAliasDict alias get (__missing__)", "legacy[ak]"),
        ("AliasDict get(origin)", "ad.get(ok)"),
        ("AliasDict get(alias)", "ad.get(ak)"),
    ]
    out: list[tuple[str, float]] = []
    for name, stmt in cases:
        looped = f"for _ in range({INNER_LOOKUP}):\n    {stmt}"
        out.append((name, _time(looped, number=NUMBER_LOOKUP) / INNER_LOOKUP))
    return out


def run_views() -> list[tuple[str, float]]:
    cases = [
        ("AliasDict keys() construct (current)", "ad.keys()"),
        ("LegacyAliasDict keys() construct (eager merge)", "legacy.keys()"),
        ("AliasDict items() construct (current)", "ad.items()"),
        ("LegacyAliasDict items() construct (eager merge)", "legacy.items()"),
        ("AliasDict list(keys()) (current)", "list(ad.keys())"),
        ("LegacyAliasDict list(keys()) (eager merge)", "list(legacy.keys())"),
        ("AliasDict list(items()) (current)", "list(ad.items())"),
        ("LegacyAliasDict list(items()) (eager merge)", "list(legacy.items())"),
    ]
    # Construct of the lazy view is tiny; loop it. Eager/list stay single-shot.
    out: list[tuple[str, float]] = []
    for name, stmt in cases:
        if "current" in name and "construct" in name:
            looped = f"for _ in range({INNER_LOOKUP}):\n    {stmt}"
            out.append((name, _time(looped, number=NUMBER_VIEW) / INNER_LOOKUP))
        else:
            out.append((name, _time(stmt, number=NUMBER_VIEW)))
    return out


def format_lookup_table(results: list[tuple[str, float]]) -> str:
    baseline = results[0][1]
    lines = [
        "| Operation | time | vs `dict[origin]` |",
        "|---|---:|---:|",
    ]
    for name, seconds in results:
        lines.append(f"| `{name}` | {_fmt_time(seconds)} | {_rel(seconds, baseline)} |")
    return "\n".join(lines)


def format_view_table(results: list[tuple[str, float]]) -> str:
    lines = [
        "| Operation | time |",
        "|---|---:|",
    ]
    for name, seconds in results:
        lines.append(f"| `{name}` | {_fmt_time(seconds)} |")
    return "\n".join(lines)


def speedup_summary(
    lookups: list[tuple[str, float]],
    views: list[tuple[str, float]],
) -> str:
    by_name = {name: sec for name, sec in lookups + views}
    rows = [
        ("origin get", "LegacyAliasDict origin get (UserDict)", "AliasDict origin get (current)"),
        ("alias get", "LegacyAliasDict alias get (__missing__)", "AliasDict alias get (current)"),
        (
            "keys() construct",
            "LegacyAliasDict keys() construct (eager merge)",
            "AliasDict keys() construct (current)",
        ),
        (
            "items() construct",
            "LegacyAliasDict items() construct (eager merge)",
            "AliasDict items() construct (current)",
        ),
        ("list(keys())", "LegacyAliasDict list(keys()) (eager merge)", "AliasDict list(keys()) (current)"),
        ("list(items())", "LegacyAliasDict list(items()) (eager merge)", "AliasDict list(items()) (current)"),
    ]
    lines = [
        "| Hot path | Current vs legacy (`UserDict`) |",
        "|---|---|",
    ]
    for label, old, new in rows:
        lines.append(f"| {label} | {_ratio_label(by_name[old], by_name[new])} |")
    return "\n".join(lines)


def main() -> None:
    print(f"Python {sys.version.split()[0]} on {platform.platform()}")
    print(f"N={N:,} origins + {N:,} aliases; best of {REPEAT} (lower is better)\n")
    lookups = run_lookups()
    views = run_views()
    print("### Lookups\n")
    print(format_lookup_table(lookups))
    print("\n### Views (`keys` / `items`)\n")
    print(format_view_table(views))
    print("\n### Speedup vs pre-rewrite (`UserDict`) design\n")
    print(speedup_summary(lookups, views))


if __name__ == "__main__":
    main()
