import pickle

import pytest

from aldict import AliasDict, FrozenAliasDict, AliasValueError


def test_hash_with_hashable_values():
    ad1 = AliasDict({"a": 1, "b": 2}, aliases={"a": ["aa"]})
    ad2 = AliasDict({"a": 1, "b": 2}, aliases={"a": ["aa"]})
    ad3 = AliasDict({"a": 1, "b": 3})

    frozen1 = FrozenAliasDict(ad1)
    frozen2 = FrozenAliasDict(ad2)
    frozen3 = FrozenAliasDict(ad3)

    assert hash(frozen1) == hash(frozen2)
    assert hash(frozen1) != hash(frozen3)


def test_raises_with_unhashable_values():
    ad = AliasDict({"a": {"nested": "dict"}})
    with pytest.raises(
        TypeError, match="FrozenAliasDict requires all keys and values to be hashable"
    ):
        FrozenAliasDict(ad)


def test_requires_aliasdict_or_dict():
    with pytest.raises(TypeError, match="FrozenAliasDict requires an AliasDict or dict instance"):
        FrozenAliasDict([("a", 1)])


def test_from_dict_with_aliases():
    frozen = FrozenAliasDict({"a": 1, "b": 2}, aliases={"a": ["aa"], "b": ["bb"]})
    assert frozen["a"] == frozen["aa"] == 1
    assert frozen["b"] == frozen["bb"] == 2
    assert list(frozen.aliases()) == ["aa", "bb"]


def test_from_dict_with_multiple_aliases_per_key():
    frozen = FrozenAliasDict({"a": 1, "b": 2}, aliases={"a": ["aa", "aaa"], "b": ["bb", "bbb"]})
    assert frozen["a"] == frozen["aa"] == frozen["aaa"] == 1
    assert frozen["b"] == frozen["bb"] == frozen["bbb"] == 2
    assert list(frozen.aliases()) == ["aa", "aaa", "bb", "bbb"]


def test_from_dict_without_aliases():
    frozen = FrozenAliasDict({"a": 1, "b": 2})
    assert frozen["a"] == 1
    assert frozen["b"] == 2
    assert list(frozen.aliases()) == []


def test_extend_aliases_from_aliasdict():
    ad = AliasDict({"a": 1, "b": 2})
    ad.add_alias("a", "aa")
    frozen = FrozenAliasDict(ad, aliases={"b": ["bb"]})

    assert frozen["aa"] == 1
    assert frozen["bb"] == 2
    assert list(frozen.aliases()) == ["aa", "bb"]


def test_from_aliasdict_preserves_aliases():
    ad = AliasDict({"a": 1, "b": 2})
    ad.add_alias("a", "aa", "aaa")
    ad.add_alias("b", "bb")
    frozen = FrozenAliasDict(ad)

    assert frozen["aa"] == frozen["aaa"] == 1
    assert frozen["bb"] == 2
    assert list(frozen.aliases()) == ["aa", "aaa", "bb"]


def test_override_existing_alias():
    ad = AliasDict({"a": 1, "b": 2})
    ad.add_alias("a", "x")
    frozen = FrozenAliasDict(ad, aliases={"b": ["x"]})
    assert frozen["x"] == 2


def test_empty_aliases_dict():
    ad = AliasDict({"a": 1})
    ad.add_alias("a", "aa")
    frozen1 = FrozenAliasDict(ad, aliases={})
    frozen2 = FrozenAliasDict(ad, aliases=None)
    frozen3 = FrozenAliasDict(ad)

    assert hash(frozen1) == hash(frozen2) == hash(frozen3)
    assert list(frozen1.aliases()) == ["aa"]


def test_independent_of_source():
    ad = AliasDict({"a": 1, "b": 2})
    ad.add_alias("a", "aa")
    frozen = FrozenAliasDict(ad)

    ad["a"] = 999
    ad.add_alias("b", "bb")
    ad.remove_alias("aa")

    assert frozen["a"] == frozen["aa"] == 1
    assert ad["a"] == 999

    assert "bb" not in frozen
    assert "aa" not in ad


def test_alias_validation():
    cases = [
        (KeyError, None, {"a": 1}, {"x": ["aa"]}),
        (
            AliasValueError,
            "Key and corresponding alias cannot be equal",
            {"a": 1},
            {"a": ["a"]},
        ),
        (AliasValueError, "already exists as a key", {"a": 1, "b": 2}, {"a": ["b"]}),
    ]
    for exc, match, data, aliases in cases:
        with pytest.raises(exc, match=match):
            FrozenAliasDict(data, aliases=aliases)


def test_is_immutable():
    ad = AliasDict({"a": 1, "b": 2})
    ad.add_alias("a", "aa")
    frozen = FrozenAliasDict(ad)

    mutations = [
        lambda: frozen.__setitem__("a", 99),
        lambda: frozen.__delitem__("a"),
        lambda: frozen.add_alias("b", "bb"),
        lambda: frozen.remove_alias("aa"),
        lambda: frozen.clear(),
        lambda: frozen.pop("a"),
    ]
    for mutation in mutations:
        with pytest.raises(TypeError, match="FrozenAliasDict is immutable"):
            mutation()


def test_readable():
    ad = AliasDict({"a": 1, "b": 2})
    ad.add_alias("a", "aa")
    frozen = FrozenAliasDict(ad)

    assert list(frozen.keys()) == ["a", "b", "aa"]
    assert list(frozen.values()) == [1, 2]


def test_usable_in_set():
    ad1 = AliasDict({"a": 1})
    ad2 = AliasDict({"a": 1})
    ad3 = AliasDict({"a": 2})

    frozen_set = {FrozenAliasDict(ad1), FrozenAliasDict(ad2), FrozenAliasDict(ad3)}
    assert len(frozen_set) == 2


def test_equality():
    frozen1 = FrozenAliasDict({"a": 1, "b": 2}, aliases={"a": ["aa"]})
    frozen2 = FrozenAliasDict({"a": 1, "b": 2}, aliases={"a": ["aa"]})
    frozen3 = FrozenAliasDict({"a": 1, "b": 2}, aliases={"a": ["aaa"]})
    frozen4 = FrozenAliasDict({"a": 1, "b": 3})

    assert frozen1 == frozen2
    assert frozen1 != frozen3
    assert frozen1 != frozen4


def test_repr():
    frozen = FrozenAliasDict({"a": 1, "b": 2}, aliases={"a": ["aa"]})
    assert str(frozen) == "FrozenAliasDict({'a': 1, 'b': 2, 'aa': 1})"


def test_pickle():
    frozen = FrozenAliasDict({"a": 1, "b": 2}, aliases={"a": ["aa"]})
    restored = pickle.loads(pickle.dumps(frozen))
    assert restored == frozen
    assert restored["aa"] == 1
    assert hash(restored) == hash(frozen)
