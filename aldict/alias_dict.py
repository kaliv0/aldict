from collections import UserDict
from collections.abc import Mapping
from itertools import chain

from aldict.exception import AliasError, AliasValueError


class AliasDict(UserDict):
    """Dict with key-aliases pointing to shared values."""

    def __init__(self, dict_=None, /, aliases=None):
        self._lookup_map = {}  # key -> set(aliases)
        self._alias_map = {}  # alias -> key

        if isinstance(dict_, AliasDict):
            super().__init__(dict_.data)
            self._lookup_map = self._copy_lookup_map(dict_._lookup_map)
            self._alias_map = dict_._alias_map.copy()
        else:
            super().__init__(dict_)

        if aliases:
            for key, alias_list in aliases.items():
                self.add_alias(key, alias_list)

    def add_alias(self, key, *aliases, strict=False):
        """Add one or more aliases to a key. Accepts *args or a list/tuple.
        If strict=True, raises AliasValueError when an alias is already assigned to a different key."""
        if key not in self.data:
            raise KeyError(key)

        for alias in self._unpack(aliases):
            if alias == key:
                raise AliasValueError(f"Key and corresponding alias cannot be equal: '{key}'")
            if alias in self.data:
                raise AliasValueError(f"Alias '{alias}' already exists as a key in the dictionary")
            if strict and (old_key := self._alias_map.get(alias)) is not None and old_key != key:
                raise AliasValueError(f"Alias '{alias}' already assigned to key '{old_key}'")

            self._lookup_map.setdefault(key, set()).add(alias)
            self._alias_map[alias] = key

    def remove_alias(self, *aliases):
        """Remove one or more aliases. Accepts *args or a list/tuple."""
        for alias in self._unpack(aliases):
            try:
                key = self._alias_map.pop(alias)
            except KeyError as e:
                raise AliasError(f"Alias '{alias}' not found") from e

            aliases_set = self._lookup_map[key]
            aliases_set.discard(alias)
            if not aliases_set:
                del self._lookup_map[key]

    @staticmethod
    def _copy_lookup_map(source):
        return {k: v.copy() for k, v in source.items()}

    @staticmethod
    def _unpack(args):
        return args[0] if len(args) == 1 and isinstance(args[0], (list, tuple)) else args

    @classmethod
    def fromkeys(cls, iterable, value=None, aliases=None):
        """Create an AliasDict from an iterable of keys with optional aliases."""
        return cls(dict.fromkeys(iterable, value), aliases=aliases)

    def clear(self):
        """Clear all data and aliases."""
        super().clear()
        self._lookup_map.clear()
        self._alias_map.clear()

    def clear_aliases(self):
        """Remove all aliases."""
        self._lookup_map.clear()
        self._alias_map.clear()

    def aliases(self):
        """Return all aliases."""
        return self._alias_map.keys()

    def is_alias(self, key):
        """Return True if the key is an alias, False otherwise."""
        return key in self._alias_map

    def has_aliases(self, key):
        """Return True if the key has any aliases, False otherwise."""
        return key in self._lookup_map

    def keys_with_aliases(self):
        """Return keys with their aliases."""
        return self._lookup_map.items()

    def origin_keys(self):
        """Return original keys (without aliases)."""
        return self.data.keys()

    def origin_key(self, alias):
        """Return the original key for an alias, or None if not an alias."""
        return self._alias_map.get(alias)

    def keys(self):
        """Return all keys and aliases."""
        return (self.data | self._alias_map).keys()

    def values(self):
        """Return all values."""
        return self.data.values()

    def items(self):
        """Return all items (including alias/value pairs)."""
        return (self.data | {k: self.data[v] for k, v in self._alias_map.items()}).items()

    def iterkeys(self):
        """Return a lazy iterator over all keys and aliases."""
        return iter(self)

    def iteritems(self):
        """Return a lazy iterator over all items (including alias/value pairs)."""
        return chain(self.data.items(), ((k, self.data[v]) for k, v in self._alias_map.items()))

    def origin_len(self):
        """Return count of original keys (without aliases)."""
        return len(self.data)

    def __len__(self):
        return len(self.data) + len(self._alias_map)

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

    def __delitem__(self, key):
        try:
            del self.data[key]
            for alias in self._lookup_map.pop(key, ()):
                del self._alias_map[alias]
        except KeyError:
            return self.remove_alias(key)

    def __contains__(self, item):
        return item in self.data or item in self._alias_map

    def __iter__(self):
        return chain(self.data, self._alias_map)

    def __reversed__(self):
        return chain(reversed(self._alias_map), reversed(self.data))

    def copy(self):
        """Return a shallow copy of the AliasDict."""
        return type(self)(self)

    def __repr__(self):
        return f"AliasDict({dict(self.items())})"

    def __eq__(self, other):
        if not isinstance(other, AliasDict):
            return NotImplemented
        # _lookup_map is derived from _alias_map, so comparing it is redundant
        return self.data == other.data and self._alias_map == other._alias_map

    def __or__(self, other):
        if not isinstance(other, Mapping):
            return NotImplemented
        new = self.copy()
        if isinstance(other, AliasDict):
            new.update(other.data)
            self._validate_merge_aliases(new, other)
            new._alias_map.update(other._alias_map)
            new._lookup_map.update(self._copy_lookup_map(other._lookup_map))
        else:
            new.update(other)
        return new

    def __ror__(self, other):
        if not isinstance(other, Mapping):
            return NotImplemented
        new = type(self)(other)
        new.update(self.data)
        self._validate_merge_aliases(new, self)
        new._alias_map.update(self._alias_map)
        new._lookup_map.update(self._copy_lookup_map(self._lookup_map))
        return new

    def __ior__(self, other):
        if isinstance(other, AliasDict):
            self._validate_merge_aliases(self, other)
            self.update(other.data)
            self._alias_map.update(other._alias_map)
            for k, v in other._lookup_map.items():
                self._lookup_map[k] = v.copy()
        else:
            self.update(other)
        return self

    @staticmethod
    def _validate_merge_aliases(target, other):
        """Check that other's aliases don't collide with target's keys and vice versa."""
        for alias in other._alias_map:  # noqa
            if alias in target.data:
                raise AliasValueError(f"Alias '{alias}' already exists as a key in the dictionary")
        for key in other.data:
            if key in target._alias_map:  # noqa
                raise AliasValueError(f"Key '{key}' already exists as an alias in the dictionary")

    __hash__ = None
