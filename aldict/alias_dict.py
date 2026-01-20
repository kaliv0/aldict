from collections import UserDict, defaultdict
from itertools import chain

from aldict.exception import AliasError, AliasValueError


class AliasDict(UserDict):
    """Dict with key-aliases pointing to shared values."""

    def __init__(self, dict_=None, /, aliases=None):
        self._alias_dict = {}
        if isinstance(dict_, AliasDict):
            super().__init__(**dict_.data)
            self._alias_dict = dict(dict_._alias_dict)
        else:
            super().__init__(**(dict_ or {}))

        if aliases:
            for key, alias_list in aliases.items():
                self.add_alias(key, alias_list)

    def add_alias(self, key, *aliases):
        """Add one or more aliases to a key. Accepts *args or a list/tuple."""
        if key not in self.data:
            raise KeyError(key)

        for alias in self._unpack(aliases):
            if alias == key:
                raise AliasValueError(f"Key and corresponding alias cannot be equal: '{key}'")
            if alias in self.data:
                raise AliasValueError(f"Alias '{alias}' already exists as a key in the dictionary")
            self._alias_dict[alias] = key

    def remove_alias(self, *aliases):
        """Remove one or more aliases. Accepts *args or a list/tuple."""
        for alias in self._unpack(aliases):
            try:
                self._alias_dict.__delitem__(alias)
            except KeyError as e:
                raise AliasError(alias) from e

    @staticmethod
    def _unpack(args):
        return args[0] if len(args) == 1 and isinstance(args[0], (list, tuple)) else args

    def clear(self):
        """Clear all data and aliases."""
        super().clear()
        self._alias_dict.clear()

    def clear_aliases(self):
        """Remove all aliases."""
        self._alias_dict.clear()

    def aliases(self):
        """Return all aliases."""
        return self._alias_dict.keys()

    def aliased_keys(self):
        """Return keys with their aliases."""
        result = defaultdict(list)
        for alias, key in self._alias_dict.items():
            result[key].append(alias)
        return result.items()

    def origin_keys(self):
        """Return original keys (without aliases)."""
        return self.data.keys()

    def keys(self):
        """Return all keys and aliases."""
        return dict(**self.data, **self._alias_dict).keys()
        # NB: could be optimized as 'return iter(self)' but we won't be able to call e.g. len(alias_dict.keys())

    def values(self):
        """Return all values."""
        return self.data.values()

    def items(self):
        """Return all items (including alias/value pairs)."""
        return dict(**self.data, **{k: self.data[v] for k, v in self._alias_dict.items()}).items()
        # NB: could be optimized as
        #   'return chain(self.data.items(), ((k, self.data[v]) for k, v in self._alias_dict.items()))'
        # (same as .keys() above)

    def origin_len(self):
        """Return count of original keys (without aliases)."""
        return len(self.data)

    def __len__(self):
        return len(self.data) + len(self._alias_dict)

    def __missing__(self, key):
        try:
            return super().__getitem__(self._alias_dict[key])
        except KeyError:
            raise KeyError(key) from None

    def __setitem__(self, key, value):
        try:
            key = self._alias_dict[key]
        except KeyError:
            pass
        super().__setitem__(key, value)

    def __delitem__(self, key):
        try:
            self.data.__delitem__(key)
            for alias in [k for k, v in self._alias_dict.items() if v == key]:
                del self._alias_dict[alias]
        except KeyError:
            return self.remove_alias(key)

    def __contains__(self, item):
        return item in self.data or item in self._alias_dict

    def __iter__(self):
        return chain(self.data, self._alias_dict)

    def __repr__(self):
        return f"AliasDict({dict(self.items())})"

    def __eq__(self, other):
        if not isinstance(other, AliasDict):
            return NotImplemented
        return self.data == other.data and self._alias_dict == other._alias_dict

    __hash__ = None
