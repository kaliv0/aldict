## Known Limitations

### 1. No Alias-to-Alias Chaining (Probably not needed)

Aliases can only point to origin keys, not to other aliases. There is no transitive resolution.

```python
d = AliasDict({"a": 1})
d.add_alias("a", "b")
# Cannot make "c" an alias of "b" expecting it to resolve to "a"
# d.add_alias("b", "c")  -> KeyError, "b" is not in self.data
```

### 3. No Validation of Alias Conflicts Across Merges

When merging two AliasDicts with `|` or `|=`, alias dictionaries are merged with a simple `dict.update()`. There is no validation that merged aliases still point to valid keys or that they don't conflict with existing origin keys.

### 11. `has_aliases()` Is O(n)

`has_aliases(key)` checks `key in self._alias_dict.values()`, which performs a linear scan over all alias entries. For dictionaries with many aliases this becomes a bottleneck. A reverse mapping (`origin_key -> set(aliases)`) would make this O(1).

### 12. `__delitem__` Alias Cleanup Is O(n)

When deleting an origin key, `__delitem__` scans all entries in `_alias_dict` to find aliases pointing to the deleted key:

```python
for alias in [k for k, v in self._alias_dict.items() if v == key]:
    del self._alias_dict[alias]
```

This is O(total aliases), not O(aliases for that key). A reverse index would reduce this to O(aliases for the deleted key).

### 14. No Explicit Pickle Support

Pickle works by coincidence — `UserDict`'s default behavior captures `__dict__`, which includes `_alias_dict`. However, there is no `__reduce__` or `__getstate__`/`__setstate__` implementation. If the internal attribute name changes (e.g., renaming `_alias_dict`), previously pickled instances would fail to deserialize without a migration path.

### 15. No Thread Safety

There is no synchronization on `self.data` or `self._alias_dict`. Concurrent reads and writes from multiple threads can lead to inconsistent state.
