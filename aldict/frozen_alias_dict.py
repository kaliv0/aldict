from aldict.alias_dict import AliasDict


def immutable(*methods):
    """Class decorator that makes specified methods raise TypeError."""

    def decorator(cls):
        def raise_immutable(self, *args, **kwargs):
            raise TypeError(f"{cls.__name__} is immutable")

        for method in methods:
            setattr(cls, method, raise_immutable)
        return cls

    return decorator


@immutable(
    "__setitem__",
    "__delitem__",
    "add_alias",
    "remove_alias",
    "clear_aliases",
    "clear",
    "pop",
    "popitem",
    "setdefault",
    "update",
)
class FrozenAliasDict(AliasDict):
    """Immutable, hashable version of AliasDict."""

    def __init__(self, data, /, aliases=None):
        if isinstance(data, AliasDict):
            # Copy existing AliasDict, then add any extra aliases
            source = AliasDict(dict(data.data))
            source._alias_dict = dict(data._alias_dict)
            if aliases:
                for key, alias_list in aliases.items():
                    source.add_alias(key, alias_list)
        elif isinstance(data, dict):
            source = AliasDict(data, aliases=aliases)
        else:
            raise TypeError("FrozenAliasDict requires an AliasDict or dict instance")

        super().__init__()  # Call with no args to avoid triggering blocked UserDict.update()
        self.data = source.data
        self._alias_dict = source._alias_dict

        try:
            self._hash = hash((frozenset(self.data.items()), frozenset(self._alias_dict.items())))
        except TypeError as e:
            raise TypeError(
                f"FrozenAliasDict requires all keys and values to be hashable: {e}"
            ) from None

    def __hash__(self):
        return self._hash

    def __repr__(self):
        return f"FrozenAliasDict({dict(self.items())})"
