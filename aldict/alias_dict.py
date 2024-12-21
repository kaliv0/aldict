from collections import UserDict, defaultdict

from aldict.exception import AliasError, AliasValueError


class AliasDict(UserDict):
    """Custom Dict class supporting key-aliases pointing to shared values"""

    def __init__(self, dict_):
        self._alias_dict = {}
        super().__init__(**dict_)

    def add_alias(self, key, *aliases):
        """Adds one or more aliases to specified key in the dictionary"""
        if key not in self.data.keys():
            raise KeyError(key)
        for alias in aliases:
            if alias == key:
                raise AliasValueError(f"Key and corresponding alias cannot be equal: '{key}'")
            self._alias_dict[alias] = key

    def remove_alias(self, *aliases):
        """Removes one or more aliases"""
        for alias in aliases:
            try:
                self._alias_dict.__delitem__(alias)
            except KeyError as e:
                raise AliasError(alias) from e

    def clear_aliases(self):
        """Removes all aliases"""
        self._alias_dict.clear()

    def aliases(self):
        """Returns all aliases present in the dictionary"""
        return self._alias_dict.keys()

    def aliased_keys(self):
        """Returns a dictview of all keys with their corresponding aliases"""
        result = defaultdict(list)
        for alias, key in self._alias_dict.items():
            result[key].append(alias)
        return result.items()

    def origin_keys(self):
        """Returns all keys"""
        return self.data.keys()

    def keys(self):
        """Returns all keys and aliases"""
        return dict(**self.data, **self._alias_dict).keys()

    def values(self):
        """Returns all values"""
        return self.data.values()

    def items(self):
        """Returns a dictview with all items (including alias/value tuples)"""
        return dict(**self.data, **{k: self.data[v] for k, v in self._alias_dict.items()}).items()

    def origin_len(self):
        """Returns the length of the original dictionary (without aliases)"""
        return len(self.data)

    def __len__(self):
        return len(self.keys())

    def __missing__(self, key):
        try:
            return super().__getitem__(self._alias_dict[key])
        except AttributeError as e:
            raise KeyError(key) from e

    def __setitem__(self, key, value):
        try:
            key = self._alias_dict[key]
        except KeyError:
            pass
        super().__setitem__(key, value)

    def __delitem__(self, key):
        try:
            self.data.__delitem__(key)
            self._alias_dict = {k: v for k, v in self._alias_dict.items() if v != key}
        except KeyError:
            # in case we try to delete alias via pop() or del
            return self.remove_alias(key)

    def __contains__(self, item):
        return item in set(self.keys())

    def __iter__(self):
        for item in self.keys():
            yield item

    def __repr__(self):
        return f"AliasDict({self.items()})"

    def __eq__(self, other):
        if not isinstance(other, AliasDict):
            raise TypeError(f"{other} is not an AliasDict")
        return self.data == other.data and self._alias_dict == other._alias_dict

    def __hash__(self):
        return hash((self.data, self._alias_dict))
