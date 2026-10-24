# Benchmarks

Microbenchmarks comparing the current `AliasDict` (`dict` subclass, resolve-first
lookups, lazy views) to the pre-rewrite design (`UserDict` + `__missing__` + eager
merged `keys()` / `items()`).

Run locally:

```bash
make bench
# or: uv run python benchmarks/bench.py
```

The legacy baseline lives in [`benchmarks/legacy.py`](../benchmarks/legacy.py) so
comparisons stay reproducible without git history. Absolute times vary by machine
and Python version; **ratios** are what matter.

Companion write-up of *why* these numbers moved:
[`performance-tutorial.md`](performance-tutorial.md).

---

## Sample results

Captured with `uv run python benchmarks/bench.py` on:

- Python 3.14.4
- Linux x86_64
- **N = 10 000** origins + **10 000** aliases

### Lookups

| Operation | time | vs `dict[origin]` |
|---|---:|---:|
| `dict[origin]` | 28 ns | 1.00× |
| `AliasDict origin get (current)` | 83 ns | 2.98× |
| `AliasDict alias get (current)` | 90 ns | 3.21× |
| `LegacyAliasDict origin get (UserDict)` | 71 ns | 2.54× |
| `LegacyAliasDict alias get (__missing__)` | 225 ns | 8.02× |
| `AliasDict get(origin)` | 102 ns | 3.65× |
| `AliasDict get(alias)` | 104 ns | 3.70× |

### Views (`keys` / `items`)

| Operation | time |
|---|---:|
| `AliasDict keys() construct (current)` | 103 ns |
| `LegacyAliasDict keys() construct (eager merge)` | 562.1 µs |
| `AliasDict items() construct (current)` | 104 ns |
| `LegacyAliasDict items() construct (eager merge)` | 1.69 ms |
| `AliasDict list(keys()) (current)` | 171.8 µs |
| `LegacyAliasDict list(keys()) (eager merge)` | 696.1 µs |
| `AliasDict list(items()) (current)` | 1.48 ms |
| `LegacyAliasDict list(items()) (eager merge)` | 2.23 ms |

### Speedup vs pre-rewrite (`UserDict`) design

| Hot path | Current vs legacy |
|---|---|
| origin get | ~1.2× slower (resolve-first always probes `_alias_map`) |
| alias get | ~2.5× faster |
| `keys()` / `items()` construct | ~5000–16000× faster (O(1) lazy view vs full merge) |
| `list(keys())` | ~4× faster |
| `list(items())` | ~1.5× faster |

Origin gets trade a little vs the old `UserDict` path so alias gets stay in the
same ballpark as origins. Do not flip to try-origin-first without re-running
these benches — see [`TODO.md`](../TODO.md).

Re-generate the tables above after meaningful lookup/view changes and paste the
script output here if the ratios shift.
