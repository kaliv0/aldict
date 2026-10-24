# Performance notes (Python-level)

Status: the three Python-level items below are **implemented** on `main` working tree (`AliasDict(dict)`, resolve-first inlined `_alias_map.get`, lazy custom views). Keep this file as measured tradeoffs / what not to regress — not an open checklist.

Same public behavior, no C extensions.

Baseline (historical, 10k keys + 10k aliases, pre-change `UserDict` AliasDict):

| Operation | Relative cost vs `dict[key]` |
|---|---|
| `dict[key]` | 1× |
| `UserDict[key]` / old `AliasDict` origin key | ~2.8× |
| old `AliasDict` via alias (`__missing__`) | ~9× |
| old `AliasDict.keys()` / `.items()` | much worse (allocate full temporary dicts) |

---

## 1. Subclass `dict` instead of `UserDict` — done

Origin-key ops use the C dict directly; `_alias_map` / `_lookup_map` stay instance attrs.

### Watchouts (still apply)

- Non-exact `dict.copy` / `dict.update(dst, alias_dict)` walk `keys()` / `__getitem__` and **materialize aliases as real entries**. Always use `dict.items(other)` (or other unbound origin-only APIs) for origin transfer.
- Init maps before any `__setitem__`.
- Override `get` / `pop` / `setdefault` / `update` / `__ne__` / pickle — C dict bypasses subclass hooks; default pickle persists `items()` including aliases.

---

## 2. Resolve aliases without `__missing__` — done

```python
def __getitem__(self, key):
    # resolve-first, inlined (no _origin helper — skips an extra Python call)
    try:
        return dict.__getitem__(self, self._alias_map.get(key, key))
    except KeyError:
        raise KeyError(key) from None
```

Same pattern in `__setitem__` / `get`. Copy/init copies both maps; pickle restore rebuilds `_lookup_map` from `_alias_map` inline.

### Tradeoff (measured)

| Strategy | Origin get | Alias get |
|---|---|---|
| resolve-first (current) | pays `_alias_map.get` always | best |
| try-origin-first | closest to bare dict subclass | miss + exception + second lookup |

Do not switch to try-origin-first without re-benchmarking the alias path. Key/alias overlap remains impossible under validation, so `get(key, key)` is safe.

---

## 3. Lazy `keys()` / `items()` — done

Custom `_AliasKeysView` / `_AliasItemsView`: O(1) construct, mutate-reflecting, iterate origins then aliases.

**Do not** replace with `collections.abc.KeysView` / `ItemsView` — generator wrapping + per-alias `__getitem__` is several× slower on `list(keys)` / `list(items)`.

`iterkeys` / `iteritems` remain thin compat shims; `iteritems` uses `dict.items` + direct origin fetch (faster than `(k, self[k])`).

`values()` stays origin-only (inherited).

---

## Out of scope (for later)

- Cython / mypyc / C extension (only if Python-level work is not enough for a measured hot loop).
- Changing alias validation rules, merge semantics, or `values()` omitting alias duplicates.
- Removing `iterkeys` / `iteritems` — keep as compatibility wrappers.

---

## Verification

- [x] `pytest` full suite
- [x] Microbench: origin/alias get, `keys` / `items` vs pre-change `UserDict` path — see `docs/benchmarks.md` / `make bench`
- [x] Pickle / `copy` / merge / subclass `type(self)` covered by tests
- [x] No public API breaks intended
