# Aldict — agent notes

Multi-key dictionary library: aliases point at shared values. Public API is `AliasDict`, `AliasError`, `AliasValueError` (`aldict/`).

## Layout

- `aldict/alias_dict.py` — implementation (`AliasDict` subclasses `dict`)
- `tests/` — pytest; fixtures in `conftest.py`
- `TODO.md` — perf notes / measured tradeoffs (dict subclass, resolve-first, lazy views — implemented)
- `benchmarks/` + `docs/benchmarks.md` — microbenches vs frozen UserDict baseline (`make bench`)
- Packaging: PDM + `uv.lock`; Python `>=3.10`

## Conventions

- Keep changes API-compatible unless the user asks otherwise.
- Match existing style: concise, few helpers, no overengineering.
- Prefer `dict.__*` / `dict.keys(self)` when you need **origin-only** ops; `self`/`in self` includes aliases.
- Run `pytest` after behavior changes. Extend tests for new edge cases (views, pickle, merge, subclassing).

## Do not

- Reintroduce `UserDict` or allocate full merged dicts in `keys()` / `items()`.
- Let aliases become real dict entries (breaks `origin_len`, `|`, equality).
- Reach for C/Cython unless measured need after Python-level work in `TODO.md`.
