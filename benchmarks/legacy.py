"""Frozen pre-rewrite AliasDict (UserDict + __missing__ + eager keys/items).

Kept only so benchmarks can compare the old design to the current dict subclass
without depending on git history. Not part of the public package.
"""

from collections import UserDict
from itertools import chain


class LegacyAliasDict(UserDict):
    """Historical hot-path behavior from the UserDict-based AliasDict."""

    def __init__(self, data=None, /, aliases=None):
        self._lookup_map = {}
        self._alias_map = {}
        if isinstance(data, LegacyAliasDict):
            super().__init__(data.data)
            self._lookup_map = {k: v.copy() for k, v in data._lookup_map.items()}
            self._alias_map = data._alias_map.copy()
        else:
            super().__init__(data)
        if aliases:
            for key, alias_list in aliases.items():
                self.add_alias(key, alias_list)

    def add_alias(self, key, *aliases):
        if key not in self.data:
            raise KeyError(key)
        unpacked = aliases[0] if len(aliases) == 1 and isinstance(aliases[0], (list, tuple)) else aliases
        for alias in unpacked:
            self._lookup_map.setdefault(key, set()).add(alias)
            self._alias_map[alias] = key

    def keys(self):
        return (self.data | self._alias_map).keys()

    def items(self):
        return (self.data | {k: self.data[v] for k, v in self._alias_map.items()}).items()

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

    def __contains__(self, item):
        return item in self.data or item in self._alias_map

    def __iter__(self):
        return chain(self.data, self._alias_map)

    def __len__(self):
        return len(self.data) + len(self._alias_map)
