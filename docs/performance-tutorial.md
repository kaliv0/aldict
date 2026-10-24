# From `UserDict` to `dict`: performance changes explained

This tutorial walks through the Python-level rewrite of `AliasDict`: what the old code did, what replaced it, and **why** — including measured tradeoffs you should not regress.

Public API and alias semantics stay the same. No C extensions.

Companion notes (short “do not regress” checklist): [`TODO.md`](../TODO.md).  
Measured before/after numbers: [`benchmarks.md`](benchmarks.md) (`make bench`).

---

## Mental model (unchanged)

```
origins  →  stored in the dict body (the real key/value pairs)
aliases  →  live only in instance attrs, never as real entries

_alias_map:   alias → origin key
_lookup_map:  origin key → set(aliases)   # derived reverse index
```

`ad["aa"]` and `ad["a"]` read the **same** stored value when `"aa"` aliases `"a"`.

---

## Baseline cost (old `UserDict` design)

Rough relative cost vs bare `dict[key]` (≈10k origins + 10k aliases):

| Operation | Relative cost |
|---|---|
| `dict[key]` | 1× |
| Old `AliasDict` origin get (`UserDict`) | ~2.8× |
| Old `AliasDict` alias get (`__missing__`) | ~9× |
| Old `keys()` / `items()` | Much worse — built full temporary dicts |

Three changes addressed that: subclass `dict`, resolve aliases without `__missing__`, and lazy custom views.

---

## Change 1 — Subclass `dict` instead of `UserDict`

### Before

```python
from collections import UserDict

class AliasDict(UserDict):
    def __init__(self, data=None, /, aliases=None):
        self._lookup_map = {}
        self._alias_map = {}
        if isinstance(data, AliasDict):
            super().__init__(data.data)           # values live in self.data
            ...
        else:
            super().__init__(data)
```

`UserDict` stores entries in a plain `self.data` dict and wraps every access in Python. Even an origin hit paid that wrapper.

### After

```python
class AliasDict(dict):
    def __init__(self, data=None, /, aliases=None):
        self._lookup_map = {}
        self._alias_map = {}
        dict.__init__(self)                       # values live in the instance itself

        if isinstance(data, AliasDict):
            dict.update(self, dict.items(data))   # origins only — see below
            self._alias_map = data._alias_map.copy()
            self._lookup_map = {k: v.copy() for k, v in data._lookup_map.items()}
        elif data is not None:
            self.update(data)
```

### Reason / gain

- Origin storage uses the **C** `dict` implementation directly.
- `_alias_map` / `_lookup_map` remain ordinary instance attributes — they are **not** keys in the dict.
- That removes most of the ~2.8× tax on origin gets.

### New traps (the cost of the win)

Subclassing `dict` is sharper than `UserDict`. Several C-level APIs **bypass** subclass overrides and/or walk `keys()` + `__getitem__`, which would turn aliases into real entries.

| Trap | Wrong | Right |
|---|---|---|
| Copy / merge origins | `dict.update(dst, alias_dict)` or `dict.copy(alias_dict)` | `dict.update(dst, dict.items(alias_dict))` |
| “Is this an origin?” | `key in self` (True for aliases too) | `dict.__contains__(self, key)` |
| Origin length / keys | `len(self)` / `self.keys()` | `dict.__len__(self)` / `dict.keys(self)` |

Also: init the alias maps **before** any `__setitem__` (constructor update and pickle restore both set items).

---

## Change 2 — Resolve aliases without `__missing__`

### Before

```python
def __missing__(self, key):
    try:
        return super().__getitem__(self._alias_map[key])
    except KeyError:
        raise KeyError(key) from None

def __setitem__(self, key, value):
    try:
        key = self._alias_map[key]
    except KeyError:
        pass
    super().__setitem__(key, value)
```

Origin path: normal `UserDict` get.  
Alias path: miss → `__missing__` → second lookup. That miss/exception path is why alias gets were ~9×.

### After

```python
def __getitem__(self, key):
    try:
        return dict.__getitem__(self, self._alias_map.get(key, key))
    except KeyError:
        raise KeyError(key) from None

def __setitem__(self, key, value):
    dict.__setitem__(self, self._alias_map.get(key, key), value)

def get(self, key, default=None):
    return dict.get(self, self._alias_map.get(key, key), default)
```

Resolve **first**: treat `key` as an alias if present in `_alias_map`, otherwise as an origin (`get(key, key)`). Overlap is forbidden by `add_alias` / merge validation, so this is safe.

Inlined on purpose — a tiny `_origin(key)` helper adds an extra Python call (~20 ns in microbenches).

### Reason / gain

| Strategy | Origin get | Alias get |
|---|---|---|
| **resolve-first (current)** | always pays `_alias_map.get` | best |
| try-origin-first | closest to bare dict | miss + exception + second lookup (~3× worse on aliases) |

We optimize for **both** origins and aliases being hot. Do not switch to try-origin-first without re-benchmarking the alias path.

`KeyError` still reports the **requested** key (alias or origin), not only the resolved origin.

---

## Change 3 — Lazy `keys()` / `items()` views

### Before

```python
def keys(self):
    return (self.data | self._alias_map).keys()

def items(self):
    return (self.data | {k: self.data[v] for k, v in self._alias_map.items()}).items()
```

Every call **allocated** a full merged dict (and for `items()`, a second dict of alias→value), then returned a view of that temporary. Fine for tiny maps; brutal at 10k+ aliases. The views also did not reflect later mutations of the original.

(`iterkeys` / `iteritems` were already lazy via `chain` — the inconsistency was part of the smell.)

### After

```python
def keys(self):
    return _AliasKeysView(self)

def items(self):
    return _AliasItemsView(self)

# values() inherited from dict — origin values only (aliases share storage)
```

Custom views:

- **O(1)** to construct (hold a reference to the mapping)
- Reflect mutations
- Iterate origins then aliases without building a merged dict

```python
class _AliasKeysView(_AliasView):
    def __iter__(self):
        return iter(self._m)   # AliasDict.__iter__ → chain(origins, aliases)

class _AliasItemsView(_AliasView):
    def __iter__(self):
        m = self._m
        return chain(
            dict.items(m),
            ((k, dict.__getitem__(m, v)) for k, v in m._alias_map.items()),
        )
```

Items fetch alias values with `dict.__getitem__(m, origin)` — not `m[alias]` — so they skip another resolve round-trip.

### Why not `collections.abc.KeysView` / `ItemsView`?

| Approach | `list(keys)` / `list(items)` |
|---|---|
| Custom views (`return iter(...)` / `dict.items` + direct origin fetch) | Fast path |
| `abc.KeysView` | ~2–2.5× slower — `__iter__` uses `yield from` (extra generator layer) |
| Default `abc.ItemsView` | ~2–2.5× slower — yields `(k, mapping[k])` and re-resolves every alias |

Keep the small custom classes; they are load-bearing, not style.

`iterkeys` / `iteritems` remain thin compatibility wrappers around `iter(self)` / `iter(self.items())`.

---

## Fallout — APIs that must be overridden on a `dict` subclass

With `UserDict`, `get` / `pop` / `setdefault` / `update` went through your `__getitem__` / `__setitem__` / `__delitem__`.  
With a real `dict` subclass, the **C** implementations ignore those hooks unless you override them.

### `get` / `pop` / `setdefault`

```python
def get(self, key, default=None):
    return dict.get(self, self._alias_map.get(key, key), default)

def pop(self, key, *args):
    value = self[key]      # resolve + read
    del self[key]          # origin delete or remove_alias
    return value
```

Without this, `ad.get("aa")` would miss aliases (C `dict.get` only sees origins).

### `update`

```python
def update(self, other=(), /, **kwargs):
    if isinstance(other, AliasDict):
        items = dict.items(other)    # origins once — not other.items()
    elif isinstance(other, Mapping):
        items = other.items()
    elif hasattr(other, "keys"):
        items = ((k, other[k]) for k in other.keys())
    else:
        items = other
    for k, v in items:
        self[k] = v                  # goes through resolve-first __setitem__
```

- Must not call C `dict.update(self, ...)` for user data (skips `__setitem__`).
- For another `AliasDict`, use **origins only**. Using `other.items()` would write the same origin once per alias and still would **not** copy alias maps (use `|` / `|=` to merge aliases).

### `__eq__` / `__ne__`

```python
def __eq__(self, other):
    if not isinstance(other, AliasDict):
        return NotImplemented
    return dict.__eq__(self, other) and self._alias_map == other._alias_map

def __ne__(self, other):
    # dict.__ne__ ignores subclass __eq__ — without this, != only compares origins
    eq = self.__eq__(other)
    return NotImplemented if eq is NotImplemented else not eq
```

### Pickle

Default `dict` pickling walks `items()`, so aliases would be restored as **real keys**.

```python
def __reduce_ex__(self, protocol):
    return (self.__class__, (), self.__getstate__())

def __getstate__(self):
    return (dict(dict.items(self)), self._alias_map.copy())  # origins + alias_map

def __setstate__(self, state):
    data, alias_map = state[0], state[1]
    self._alias_map = alias_map
    # rebuild _lookup_map from alias_map
    ...
    dict.update(self, data)
```

Copy still copies **both** maps (faster than rebuilding lookup on every `copy()`). Pickle stores only `alias_map` and rebuilds `_lookup_map` on load.

### `popitem` stays FIFO

`UserDict` / `MutableMapping` popped the first key from `__iter__` (origins then aliases). Bare `dict.popitem` is LIFO. The override preserves the old FIFO behavior:

```python
def popitem(self):
    key = next(iter(self))
    return key, self.pop(key)
```

---

## Copy and merge — origins first, then alias maps

### Before

```python
target.update(other.data)           # UserDict: plain origins
target._alias_map.update(other._alias_map)
# merge _lookup_map sets ...
```

### After

```python
dict.update(target, dict.items(other))   # unbound: origins only, C-fast
target._alias_map.update(other._alias_map)
for k, v in other._lookup_map.items():
    target._lookup_map.setdefault(k, set()).update(v)
```

Same idea, new spelling: never feed an `AliasDict` to APIs that iterate `keys()`/`items()` if you only want origins.

---

## What we deliberately did **not** change

| Idea | Why not |
|---|---|
| Cython / mypyc / C extension | Only if Python-level work is not enough for a measured hot loop |
| Try-origin-first lookups | Faster origins, much slower aliases |
| `collections.abc` views | Measurably slower iteration |
| `_origin()` helper on the hot path | Extra Python call |
| Drop `iterkeys` / `iteritems` | Kept as compatibility shims |
| Make `values()` include one entry per alias | Aliases share storage; origin-only `values()` is intentional |

---

## Quick “before vs after” map

| Area | Old (`UserDict`) | New (`dict` subclass) |
|---|---|---|
| Storage | `self.data` | instance dict body |
| Origin get | Python wrapper ~2.8× | C dict + one `_alias_map.get` |
| Alias get | `__missing__` ~9× | resolve-first, same order as origin |
| `keys()` / `items()` | Allocate merged dicts | Lazy custom views |
| `get` / `pop` / `update` | Inherited via `UserDict` | Explicit overrides |
| Pickle | Mostly fine via `UserDict` | Custom state (origins + `alias_map`) |
| `isinstance(ad, dict)` | `False` | `True` |

---

## How to verify

```bash
pytest
```

Worth re-checking after any edit to lookup or views:

- Origin and alias `__getitem__` / `get`
- `list(keys())` / `list(items())` (no full-dict allocation)
- `copy`, `pickle`, `|` / `|=`, and subclassing via `type(self)`

If a “simplification” reintroduces `UserDict`, `__missing__`, abc views, or merged-dict `keys()`/`items()`, expect the old costs to come back.
