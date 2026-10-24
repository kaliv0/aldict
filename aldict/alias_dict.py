from collections.abc import Mapping
from itertools import chain

KEY_EXISTS_AS_ALIAS = "Key '{key}' already exists as an alias in the dictionary"
ALIAS_EXISTS_AS_KEY = "Alias '{alias}' already exists as a key in the dictionary"
KEY_ALIAS_CANNOT_BE_EQUAL = "Key and corresponding alias cannot be equal: '{key}'"
ALIAS_ALREADY_ASSIGNED = "Alias '{alias}' already assigned to key '{key}'"
ALIAS_NOT_FOUND = "Alias '{alias}' not found"

UNSUPPORTED_OPERAND_TYPES = "Unsupported operand type(s) for |=: '{target}' and '{other}'"


class AliasError(KeyError):
    """Key alias not found"""

    pass


class AliasValueError(ValueError):
    """Inappropriate alias value"""

    pass


# Custom views (not collections.abc.*): return iter(...) / dict.items — abc
# KeysView uses yield-from and ItemsView re-resolves aliases via __getitem__.


class _AliasView:
    __slots__ = ("_m",)

    def __init__(self, mapping):
        self._m = mapping

    def __len__(self):
        return len(self._m)


class _AliasKeysView(_AliasView):
    __slots__ = ()

    def __iter__(self):
        return iter(self._m)

    def __contains__(self, key):
        return key in self._m

    def __repr__(self):
        return f"alias_keys({list(self)!r})"


class _AliasItemsView(_AliasView):
    __slots__ = ()

    def __iter__(self):
        m = self._m
        return chain(dict.items(m), ((k, dict.__getitem__(m, v)) for k, v in m._alias_map.items()))

    def __contains__(self, item):
        if not isinstance(item, tuple) or len(item) != 2:
            return False
        key, value = item
        try:
            return self._m[key] == value
        except KeyError:
            return False

    def __repr__(self):
        return f"alias_items({list(self)!r})"


class AliasDict(dict):
    """Dict with key-aliases pointing to shared values."""

    def __init__(self, data=None, /, aliases=None):
        # Maps must exist before any __setitem__ (init update + pickle restore).
        self._lookup_map = {}  # key -> set(aliases); derived from _alias_map
        self._alias_map = {}  # alias -> key
        dict.__init__(self)

        if isinstance(data, AliasDict):
            # Origins only — dict.update(self, alias_dict) would materialize aliases.
            dict.update(self, dict.items(data))
            self._alias_map = data._alias_map.copy()
            self._lookup_map = {k: v.copy() for k, v in data._lookup_map.items()}
        elif data is not None:
            self.update(data)

        if aliases:
            for key, alias_list in aliases.items():
                self.add_alias(key, alias_list)

    def add_alias(self, key, *aliases, strict=False):
        """Add one or more aliases to a key. Accepts *args or a list/tuple.
        If strict=True, raises AliasValueError when an alias is already assigned to a different key."""
        # dict.__contains__: `key in self` is also True for existing aliases.
        if not dict.__contains__(self, key):
            raise KeyError(key)

        for alias in self._unpack(aliases):
            if alias == key:
                raise AliasValueError(KEY_ALIAS_CANNOT_BE_EQUAL.format(key=key))
            if dict.__contains__(self, alias):
                raise AliasValueError(ALIAS_EXISTS_AS_KEY.format(alias=alias))

            if (old_key := self._alias_map.get(alias)) is not None and old_key != key:
                if strict:
                    raise AliasValueError(ALIAS_ALREADY_ASSIGNED.format(alias=alias, key=old_key))
                self._remove_from_lookup_map(old_key, alias)

            self._lookup_map.setdefault(key, set()).add(alias)
            self._alias_map[alias] = key

    def remove_alias(self, *aliases):
        """Remove one or more aliases. Accepts *args or a list/tuple."""
        for alias in self._unpack(aliases):
            try:
                key = self._alias_map.pop(alias)
            except KeyError as e:
                raise AliasError(ALIAS_NOT_FOUND.format(alias=alias)) from e

            self._remove_from_lookup_map(key, alias)

    def _remove_from_lookup_map(self, key, alias):
        aliases_set = self._lookup_map[key]
        aliases_set.discard(alias)
        if not aliases_set:
            del self._lookup_map[key]

    @staticmethod
    def _unpack(args):
        return args[0] if len(args) == 1 and isinstance(args[0], (list, tuple)) else args

    @classmethod
    def fromkeys(cls, iterable, value=None, aliases=None):
        """Create an AliasDict from an iterable of keys with optional aliases."""
        return cls(dict.fromkeys(iterable, value), aliases=aliases)

    def clear(self):
        """Clear all data and aliases."""
        dict.clear(self)
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
        return dict.keys(self)

    def origin_key(self, alias):
        """Return the original key for an alias, or None if not an alias."""
        return self._alias_map.get(alias)

    def keys(self):
        """Return a view of all keys and aliases."""
        return _AliasKeysView(self)

    def items(self):
        """Return a view of all items (including alias/value pairs)."""
        return _AliasItemsView(self)

    # values() inherited — origin values only (aliases share storage).

    def iterkeys(self):
        """Return an iterator over all keys and aliases."""
        return iter(self)

    def iteritems(self):
        """Return an iterator over all items (including alias/value pairs)."""
        return iter(self.items())

    def origin_len(self):
        """Return count of original keys (without aliases)."""
        return dict.__len__(self)

    def __len__(self):
        return dict.__len__(self) + len(self._alias_map)

    def __getitem__(self, key):
        try:
            return dict.__getitem__(self, self._alias_map.get(key, key))
        except KeyError:
            raise KeyError(key) from None

    def __setitem__(self, key, value):
        dict.__setitem__(self, self._alias_map.get(key, key), value)

    def __delitem__(self, key):
        try:
            dict.__delitem__(self, key)
        except KeyError:
            self.remove_alias(key)
            return
        for alias in self._lookup_map.pop(key, ()):
            del self._alias_map[alias]

    def __contains__(self, key):
        return dict.__contains__(self, key) or key in self._alias_map

    def __iter__(self):
        return chain(dict.__iter__(self), self._alias_map)

    def __reversed__(self):
        return chain(reversed(self._alias_map), dict.__reversed__(self))

    # C dict.get/pop/setdefault/update bypass subclass hooks — keep aliases working.

    def get(self, key, default=None):
        return dict.get(self, self._alias_map.get(key, key), default)

    def pop(self, key, *args):
        try:
            value = self[key]
        except KeyError:
            if args:
                return args[0]
            raise
        del self[key]
        return value

    def setdefault(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            self[key] = default
            return default

    def popitem(self):
        # FIFO via __iter__ (origins then aliases); bare dict.popitem is LIFO.
        try:
            key = next(iter(self))
        except StopIteration:
            raise KeyError("dictionary is empty") from None
        return key, self.pop(key)

    def update(self, other=(), /, **kwargs):
        # Route through self[k]=v (C update skips __setitem__). AliasDict: origins
        # only — items() would rewrite each origin once per alias.
        if isinstance(other, AliasDict):
            items = dict.items(other)
        elif isinstance(other, Mapping):
            items = other.items()
        elif hasattr(other, "keys"):
            items = ((k, other[k]) for k in other.keys())
        else:
            items = other
        for k, v in items:
            self[k] = v
        for k, v in kwargs.items():
            self[k] = v

    def copy(self):
        """Return a shallow copy of the AliasDict."""
        return type(self)(self)

    def __reduce_ex__(self, protocol):
        # Default dict pickling walks items() and would persist aliases as keys.
        return (self.__class__, (), self.__getstate__())

    def __getstate__(self):
        # Origins + alias_map; _lookup_map rebuilt on restore (copy path copies both).
        return (dict(dict.items(self)), self._alias_map.copy())

    def __setstate__(self, state):
        # (data, alias_map) or legacy (data, alias_map, lookup_map).
        data, alias_map = state[0], state[1]
        self._alias_map = alias_map
        lookup = {}
        for alias, key in alias_map.items():
            lookup.setdefault(key, set()).add(alias)
        self._lookup_map = lookup
        dict.update(self, data)

    def __repr__(self):
        return f"AliasDict({dict(self.items())})"

    def __eq__(self, other):
        if not isinstance(other, AliasDict):
            return NotImplemented
        # _lookup_map is derived from _alias_map
        return dict.__eq__(self, other) and self._alias_map == other._alias_map

    def __ne__(self, other):
        # dict.__ne__ ignores subclass __eq__
        eq = self.__eq__(other)
        return NotImplemented if eq is NotImplemented else not eq

    def __or__(self, other):
        if not isinstance(other, Mapping):
            return NotImplemented
        return self._merge_into(self.copy(), other)

    def __ror__(self, other):
        if not isinstance(other, Mapping):
            return NotImplemented
        return type(self)(other) | self

    def __ior__(self, other):
        if not isinstance(other, Mapping):
            raise TypeError(
                UNSUPPORTED_OPERAND_TYPES.format(target=type(self).__name__, other=type(other).__name__)
            )
        return self._merge_into(self, other)

    def _merge_into(self, target, other):
        if isinstance(other, AliasDict):
            target._validate_merge_aliases(other)
            dict.update(target, dict.items(other))
            target._alias_map.update(other._alias_map)
            for k, v in other._lookup_map.items():
                target._lookup_map.setdefault(k, set()).update(v)
        else:
            target.update(other)
        return target

    def _validate_merge_aliases(self, other):
        for alias, key in other._alias_map.items():
            if dict.__contains__(self, alias):
                raise AliasValueError(ALIAS_EXISTS_AS_KEY.format(alias=alias))
            if (existing := self._alias_map.get(alias)) is not None and existing != key:
                raise AliasValueError(ALIAS_ALREADY_ASSIGNED.format(alias=alias, key=existing))

        for key in dict.__iter__(other):
            if key in self._alias_map:
                raise AliasValueError(KEY_EXISTS_AS_ALIAS.format(key=key))

    __hash__ = None
