# AliasDict - Technical Analysis

## Table of Contents

1. [Overview](#overview)
2. [Internal Structure](#internal-structure)
3. [Class Hierarchy](#class-hierarchy)
4. [Data Flow](#data-flow)
5. [Initialization](#initialization)
6. [Alias Management](#alias-management)
7. [Dictionary Operations](#dictionary-operations)
8. [Merge & Copy Semantics](#merge--copy-semantics)
9. [Iteration & Length](#iteration--length)
10. [Error Handling](#error-handling)
11. [Known Limitations](#known-limitations)

---

## Overview

`AliasDict` is a dictionary subclass that allows multiple keys (aliases) to reference the same value. It extends `collections.UserDict` and stores alias-to-key mappings in a separate internal dictionary. The library has zero production dependencies and targets Python 3.10+.

---

## Internal Structure

AliasDict maintains two parallel data stores:

```
+-------------------------------+
|          AliasDict            |
|-------------------------------|
|  self.data  (from UserDict)   |
|  {                            |
|    ".json": {...},            |
|    ".yaml": {...},            |
|    ".toml": {...}             |
|  }                            |
|-------------------------------|
|  self._alias_dict             |
|  {                            |
|    ".yml" : ".yaml"           |
|  }                            |
+-------------------------------+
```

- **`self.data`** - inherited from `UserDict`, holds the canonical key-value pairs.
- **`self._alias_dict`** - a plain `dict` mapping each alias to its origin key. This is a many-to-one mapping: multiple aliases can point to the same origin key.

### Relationship Model

```
  alias_1 ──┐
  alias_2 ──┤──> origin_key ──> value
  alias_3 ──┘
```

Aliases are indirection pointers; they never store values themselves. All reads and writes through an alias resolve to the origin key in `self.data`.

---

## Class Hierarchy

```
  dict
    │
    ▼
  UserDict
    │
    ▼
  AliasDict
    │
    ├── __init__(dict_=None, /, aliases=None)
    ├── Alias management: add_alias, remove_alias, clear_aliases, ...
    ├── Overridden dict protocol: __getitem__, __setitem__, __delitem__, ...
    ├── Merge operators: __or__, __ror__, __ior__
    └── __hash__ = None  (unhashable)
```

`AliasDict` inherits several methods unchanged from `UserDict`:
- `get()`, `pop()`, `popitem()`, `setdefault()`, `update()`

These work correctly because they internally delegate to `__getitem__`, `__setitem__`, `__delitem__`, and `__contains__`, all of which are overridden with alias-aware logic.

---

## Data Flow

### Read (key lookup)

```
  __getitem__(key)
       │
       ▼
  key in self.data? ──yes──> return self.data[key]
       │
       no
       │
       ▼
  __missing__(key)
       │
       ▼
  key in self._alias_dict? ──yes──> return self.data[self._alias_dict[key]]
       │
       no
       │
       ▼
  raise KeyError
```

### Write (key assignment)

```
  __setitem__(key, value)
       │
       ▼
  key in self._alias_dict? ──yes──> key = self._alias_dict[key]
       │                                     │
       no                                    │
       │                                     │
       ▼                                     ▼
  self.data[key] = value  <──────────────────┘
```

Setting a value through an alias transparently updates the origin key. If the key is neither in `data` nor `_alias_dict`, a new entry is created in `data`.

### Delete

```
  __delitem__(key)
       │
       ▼
  key in self.data? ──yes──> delete self.data[key]
       │                     + delete all aliases pointing to key
       no
       │
       ▼
  treat as alias ──> remove_alias(key)
       │
       ▼
  alias not found? ──> raise AliasError
```

Deleting an origin key cascades to remove all associated aliases. Deleting an alias only removes the alias mapping.

---

## Initialization

```python
AliasDict(dict_=None, /, aliases=None)
```

```
  __init__(dict_, aliases)
       │
       ▼
  dict_ is AliasDict? ──yes──> copy data + copy _alias_dict
       │
       no
       │
       ▼
  super().__init__(dict_)    # UserDict handles None, dict, kwargs
       │
       ▼
  aliases provided? ──yes──> for each key, alias_list:
       │                         add_alias(key, alias_list)
       no
       │
       ▼
  done
```

Accepted input forms:
- `AliasDict()` - empty
- `AliasDict(None)` - empty
- `AliasDict({"a": 1})` - from dict
- `AliasDict(another_alias_dict)` - copy constructor (preserves aliases)
- `AliasDict({"a": 1}, aliases={"a": ["x", "y"]})` - with inline aliases

The `fromkeys` classmethod also accepts an `aliases` parameter.

---

## Alias Management

### Adding Aliases

```python
add_alias(key, *aliases)
```

Accepts variadic args or a single list/tuple (resolved by `_unpack`):

```
  add_alias(key, *aliases)
       │
       ▼
  key in self.data? ──no──> raise KeyError
       │
       yes
       │
       ▼
  for each alias in _unpack(aliases):
       │
       ├── alias == key? ──yes──> raise AliasValueError
       │
       ├── alias in self.data? ──yes──> raise AliasValueError
       │
       └── self._alias_dict[alias] = key
```

The `_unpack` helper enables these calling conventions:
- `add_alias("k", "a1", "a2")` - variadic
- `add_alias("k", ["a1", "a2"])` - list
- `add_alias("k", ("a1", "a2"))` - tuple

### Updating an Alias

There is no dedicated method. To reassign an alias to a different key:
1. `remove_alias("old_alias")`
2. `add_alias("new_key", "old_alias")`

Or directly overwrite: `_alias_dict[alias] = new_key` (internal).

### Removing Aliases

```python
remove_alias(*aliases)   # raises AliasError if alias not found
clear_aliases()          # removes all aliases silently
```

### Query Methods

| Method               | Returns                                   |
| -------------------- | ----------------------------------------- |
| `aliases()`          | `dict_keys` view of all alias names       |
| `is_alias(key)`      | `bool` - whether key is an alias          |
| `has_aliases(key)`   | `bool` - whether key has any aliases      |
| `origin_key(alias)`  | origin key string, or `None`              |
| `keys_with_aliases()`| `dict_items` of `{key: [alias, ...]}`     |

---

## Dictionary Operations

### Supported Dict Protocol

| Operation            | Alias-Aware | Notes                                        |
| -------------------- | ----------- | -------------------------------------------- |
| `d[key]`             | Yes         | Resolves alias via `__missing__`             |
| `d[key] = val`       | Yes         | Writes through alias to origin key           |
| `del d[key]`         | Yes         | Cascading delete for keys; single for aliases|
| `key in d`           | Yes         | Checks both `data` and `_alias_dict`         |
| `d.get(key)`         | Yes         | Delegates to `__getitem__`                   |
| `d.pop(key)`         | Partial     | Popping alias removes alias only             |
| `d.popitem()`        | No          | Operates on `data` only, does not clean aliases |
| `d.setdefault(key)`  | Yes         | Resolves alias for existing keys             |
| `d.update(other)`    | Yes         | Writes go through `__setitem__`              |
| `d.keys()`           | Yes         | Returns origin keys + aliases                |
| `d.values()`         | No          | Returns only origin values (no duplicates)   |
| `d.items()`          | Yes         | Returns origin + alias pairs with values     |
| `d.origin_keys()`    | N/A         | Returns only origin keys                     |
| `d.origin_len()`     | N/A         | Count of origin keys only                    |

---

## Merge & Copy Semantics

### Merge Operators

```
  AliasDict | dict         -> new AliasDict (aliases from left preserved)
  AliasDict | AliasDict    -> new AliasDict (aliases from both merged)
  dict | AliasDict         -> new AliasDict (aliases from right preserved)
  AliasDict |= dict        -> in-place update
  AliasDict |= AliasDict   -> in-place update (merges aliases)
```

When merging two AliasDicts with `|`, right-side data and aliases overwrite left-side on conflicts.

### Copy

```python
d.copy()        # shallow copy via AliasDict(self)
copy.copy(d)    # shallow copy (same behavior)
copy.deepcopy(d)# deep copy of data and alias dict
```

`copy()` creates a new `AliasDict` using the copy-constructor path in `__init__`, which copies both `data` and `_alias_dict`.

### Serialization

Pickle is supported. The instance round-trips correctly through `pickle.dumps` / `pickle.loads`.

---

## Iteration & Length

### Iteration Order

```
  __iter__:     chain(self.data, self._alias_dict)
                origin keys first, then aliases

  __reversed__: chain(reversed(self._alias_dict), reversed(self.data))
                aliases first (reversed), then origin keys (reversed)
```

### Length

```
  len(d)         -> len(self.data) + len(self._alias_dict)
  d.origin_len() -> len(self.data)
```

`len()` counts every key and alias as a separate entry.

---

## Error Handling

### Exception Hierarchy

```
  builtins.KeyError
      │
      ▼
  AliasError          # alias-specific lookup/removal failures

  builtins.ValueError
      │
      ▼
  AliasValueError     # invalid alias values (alias == key, alias is existing key)
```

### Error Conditions

| Operation                            | Error            | Condition                          |
| ------------------------------------ | ---------------- | ---------------------------------- |
| `add_alias(missing_key, "a")`        | `KeyError`       | key not in `self.data`             |
| `add_alias("k", "k")`               | `AliasValueError`| alias equals its own key           |
| `add_alias("k", "existing_key")`    | `AliasValueError`| alias already exists as origin key |
| `remove_alias("nonexistent")`        | `AliasError`     | alias not in `_alias_dict`         |
| `d["nonexistent"]`                   | `KeyError`       | not in data or aliases             |
