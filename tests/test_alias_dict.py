import copy
import pickle
from unittest.mock import patch

import pytest

from aldict import AliasDict, AliasValueError, AliasError


def test_alias_dict(alias_dict):
    assert alias_dict[".toml"] == {
        "callable": "load",
        "import_mod": "tomli",
        "read_mode": "r",
    }
    assert (
        alias_dict[".yml"]
        == alias_dict[".yaml"]
        == {"callable": "safe_load", "import_mod": "yaml", "read_mode": "r"}
    )


def test_init_with_none():
    ad = AliasDict(None)
    assert len(ad) == 0
    assert list(ad.keys()) == []


def test_init_with_no_argument():
    ad = AliasDict()
    assert len(ad) == 0
    assert list(ad.keys()) == []


def test_init_from_aliasdict_preserves_aliases():
    ad1 = AliasDict({"a": 1, "b": 2})
    ad1.add_alias("a", "aa", "aaa")
    ad2 = AliasDict(ad1)

    assert ad2["a"] == ad2["aa"] == ad2["aaa"] == 1
    assert list(ad2.aliases()) == ["aa", "aaa"]

    # Verify independence
    ad1["a"] = 999
    ad1.add_alias("b", "bb")
    assert ad2["a"] == 1
    assert "bb" not in ad2


def test_init_with_aliases_one_liner():
    ad = AliasDict({"a": 1, "b": 2}, aliases={"a": ["aa"], "b": ["bb"]})
    assert ad["a"] == ad["aa"] == 1
    assert ad["b"] == ad["bb"] == 2
    assert list(ad.aliases()) == ["aa", "bb"]


def test_init_with_multiple_aliases_per_key():
    ad = AliasDict({"a": 1, "b": 2}, aliases={"a": ["aa", "aaa", "aaaa"], "b": ["bb", "bbb"]})
    assert ad["a"] == ad["aa"] == ad["aaa"] == ad["aaaa"] == 1
    assert ad["b"] == ad["bb"] == ad["bbb"] == 2
    assert list(ad.aliases()) == ["aa", "aaa", "aaaa", "bb", "bbb"]


def test_init_with_aliases_validation():
    cases = [
        (KeyError, None, {"a": 1}, {"nonexistent": ["aa"]}),
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
            AliasDict(data, aliases=aliases)


def test_init_with_non_string_keys():
    ad = AliasDict({1: "one", 2: "two", (1, 2): "tuple_key"})
    assert ad[1] == "one"
    assert ad[2] == "two"
    assert ad[(1, 2)] == "tuple_key"

    ad.add_alias(1, 11)
    assert ad[11] == "one"


def test_init_from_aliasdict_with_non_string_keys():
    ad1 = AliasDict({1: "one", 2: "two", (1, 2): "tuple_key"})
    ad1.add_alias(1, 11, 111)
    ad2 = AliasDict(ad1)

    assert ad2[1] == ad2[11] == ad2[111] == "one"
    assert ad2[(1, 2)] == "tuple_key"
    assert list(ad2.aliases()) == [11, 111]


def test_init_with_non_identifier_string_keys():
    ad = AliasDict({"my-key": 1, "another.key": 2, "123": 3, "has spaces": 4})
    assert ad["my-key"] == 1
    assert ad["another.key"] == 2
    assert ad["123"] == 3
    assert ad["has spaces"] == 4

    ad.add_alias("my-key", "also-dashed")
    assert ad["also-dashed"] == 1


def test_init_from_aliasdict_with_non_identifier_string_keys():
    ad1 = AliasDict({"my-key": 1, "123start": 2})
    ad1.add_alias("my-key", "alt-key")
    ad2 = AliasDict(ad1)

    assert ad2["my-key"] == ad2["alt-key"] == 1
    assert ad2["123start"] == 2
    assert list(ad2.aliases()) == ["alt-key"]


def test_init_with_none_does_not_call_update():
    # Ensure AliasDict(None) doesn't call update() - required for FrozenAliasDict compatibility
    with patch.object(AliasDict, "update") as mock_update:
        ad = AliasDict(None)
        mock_update.assert_not_called()
    assert len(ad) == 0


def test_add_alias(alias_dict):
    alias_dict.add_alias(".toml", ".tml")
    assert (
        alias_dict[".toml"]
        == alias_dict[".tml"]
        == {"callable": "load", "import_mod": "tomli", "read_mode": "r"}
    )


@pytest.mark.parametrize(
    "args",
    [
        (".jsn", ".joojoo", ".jazz"),  # *args
        ([".jsn", ".joojoo", ".jazz"],),  # list
        ((".jsn", ".joojoo", ".jazz"),),  # tuple
    ],
)
def test_add_multiple_aliases(alias_dict, args):
    alias_dict.add_alias(".json", *args)
    assert list(alias_dict.keys()) == [
        ".json",
        ".yaml",
        ".toml",
        ".yml",
        ".jsn",
        ".joojoo",
        ".jazz",
    ]


def test_add_alias_raises(alias_dict):
    with pytest.raises(
        AliasValueError, match="Key and corresponding alias cannot be equal: '.toml'"
    ):
        alias_dict.add_alias(".toml", ".toml")


def test_add_alias_raises_if_alias_is_existing_key():
    ad = AliasDict({"a": 1, "b": 2})
    with pytest.raises(
        AliasValueError, match="Alias 'b' already exists as a key in the dictionary"
    ):
        ad.add_alias("a", "b")


def test_update_alias(alias_dict):
    # redirect ".yml" to point to ".toml"
    alias_dict.add_alias(".toml", ".yml")
    assert list(alias_dict.items()) == [
        (".json", {"callable": "load", "import_mod": "json", "read_mode": "r"}),
        (".yaml", {"callable": "safe_load", "import_mod": "yaml", "read_mode": "r"}),
        (".toml", {"callable": "load", "import_mod": "tomli", "read_mode": "r"}),
        (".yml", {"callable": "load", "import_mod": "tomli", "read_mode": "r"}),
    ]


def test_update_alias_raises(alias_dict):
    with pytest.raises(KeyError, match=".foo"):
        alias_dict.add_alias(".foo", ".bar")


def test_remove_alias(alias_dict):
    assert list(alias_dict.keys()) == [".json", ".yaml", ".toml", ".yml"]

    alias_dict.remove_alias(".yml")
    assert list(alias_dict.keys()) == [".json", ".yaml", ".toml"]
    assert list(alias_dict.items()) == [
        (".json", {"callable": "load", "import_mod": "json", "read_mode": "r"}),
        (".yaml", {"callable": "safe_load", "import_mod": "yaml", "read_mode": "r"}),
        (".toml", {"callable": "load", "import_mod": "tomli", "read_mode": "r"}),
    ]


def test_remove_alias_raises(alias_dict):
    assert list(alias_dict.keys()) == [".json", ".yaml", ".toml", ".yml"]
    with pytest.raises(AliasError, match=".foo"):
        alias_dict.remove_alias(".foo")


@pytest.mark.parametrize(
    "args",
    [
        (".yml", ".jsn"),  # *args
        ([".yml", ".jsn"],),  # list
        ((".yml", ".jsn"),),  # tuple
    ],
)
def test_remove_multiple_aliases(alias_dict, args):
    alias_dict.add_alias(".json", ".jsn")
    alias_dict.remove_alias(*args)
    assert list(alias_dict.keys()) == [".json", ".yaml", ".toml"]


def test_read_aliases(alias_dict):
    alias_dict.add_alias(".toml", ".tml")
    alias_dict.add_alias(".json", ".jsn")
    alias_dict.add_alias(".json", ".whaaaaat!")
    assert list(alias_dict.aliases()) == [".yml", ".tml", ".jsn", ".whaaaaat!"]


def test_dictviews(alias_dict):
    assert list(alias_dict.keys()) == [".json", ".yaml", ".toml", ".yml"]
    assert list(alias_dict.values()) == [
        {"import_mod": "json", "callable": "load", "read_mode": "r"},
        {"import_mod": "yaml", "callable": "safe_load", "read_mode": "r"},
        {"import_mod": "tomli", "callable": "load", "read_mode": "r"},
    ]
    assert list(alias_dict.items()) == [
        (".json", {"callable": "load", "import_mod": "json", "read_mode": "r"}),
        (".yaml", {"callable": "safe_load", "import_mod": "yaml", "read_mode": "r"}),
        (".toml", {"callable": "load", "import_mod": "tomli", "read_mode": "r"}),
        (".yml", {"callable": "safe_load", "import_mod": "yaml", "read_mode": "r"}),
    ]


def test_remove_key_and_aliases(alias_dict):
    assert list(alias_dict.keys()) == [".json", ".yaml", ".toml", ".yml"]
    alias_dict.pop(".yaml")
    assert list(alias_dict.keys()) == [".json", ".toml"]


def test_contains(alias_dict):
    alias_dict.add_alias(".toml", ".tml")
    assert (".toml" in alias_dict) is True
    assert (".tml" in alias_dict) is True
    assert (".foo" in alias_dict) is False


def test_get(alias_dict):
    assert alias_dict.get(".yaml") == {
        "callable": "safe_load",
        "import_mod": "yaml",
        "read_mode": "r",
    }
    assert alias_dict.get(".yml") == {
        "callable": "safe_load",
        "import_mod": "yaml",
        "read_mode": "r",
    }
    assert alias_dict.get(".foo") is None


def test_pop_alias_doesnt_remove_key(alias_dict):
    assert alias_dict.pop(".yml") == {
        "callable": "safe_load",
        "import_mod": "yaml",
        "read_mode": "r",
    }
    assert list(alias_dict.keys()) == [".json", ".yaml", ".toml"]


def test_pop_with_default():
    ad = AliasDict({"a": 1, "b": 2})
    assert ad.pop("nonexistent", "default") == "default"
    assert ad.pop("a") == 1
    assert ad.pop("a", "gone") == "gone"


def test_pop_nonexistent_key_raises():
    ad = AliasDict({"a": 1, "b": 2})
    with pytest.raises(KeyError):
        ad.pop("nonexistent")


def test_iter(alias_dict):
    assert [k for k in alias_dict] == [".json", ".yaml", ".toml", ".yml"]


def test_origin_keys(alias_dict):
    assert list(alias_dict.origin_keys()) == [".json", ".yaml", ".toml"]


def test_keys_with_aliases(alias_dict):
    assert list(alias_dict.keys_with_aliases()) == [(".yaml", [".yml"])]
    alias_dict.add_alias(".toml", ".tml", ".tommy", ".tomograph")
    assert list(alias_dict.keys_with_aliases()) == [
        (".yaml", [".yml"]),
        (".toml", [".tml", ".tommy", ".tomograph"]),
    ]


def test_repr(alias_dict):
    assert str(alias_dict) == (
        "AliasDict({"
        "'.json': {'import_mod': 'json', 'callable': 'load', 'read_mode': 'r'}, "
        "'.yaml': {'import_mod': 'yaml', 'callable': 'safe_load', 'read_mode': 'r'}, "
        "'.toml': {'import_mod': 'tomli', 'callable': 'load', 'read_mode': 'r'}, "
        "'.yml': {'import_mod': 'yaml', 'callable': 'safe_load', 'read_mode': 'r'}"
        "})"
    )


def test_eq():
    ad_0 = {"a": 1, "b": 2}
    ad_1 = AliasDict(ad_0)
    ad_1.add_alias("a", "aa", "aaa")

    ad_2 = AliasDict(ad_0)
    ad_2.add_alias("a", "aa", "aaa")

    ad_3 = AliasDict(ad_0)
    ad_3.add_alias("a", "abc")

    assert ad_1 == ad_2
    assert ad_1 != ad_3
    assert ad_2 != ad_3


def test_dict_len_includes_aliases(alias_dict):
    assert list(alias_dict.keys()) == [".json", ".yaml", ".toml", ".yml"]
    assert len(alias_dict) == 4


def test_dict_origin_len_excludes_aliases(alias_dict):
    assert list(alias_dict.keys()) == [".json", ".yaml", ".toml", ".yml"]
    assert alias_dict.origin_len() == 3


def test_popitem(alias_dict):
    # pops first item -> MutableMapping.popitem()
    assert alias_dict.popitem() == (
        ".json",
        {"callable": "load", "import_mod": "json", "read_mode": "r"},
    )
    assert alias_dict.popitem() == (
        ".yaml",
        {"callable": "safe_load", "import_mod": "yaml", "read_mode": "r"},
    )
    assert len(alias_dict.keys_with_aliases()) == 0
    assert list(alias_dict.keys()) == [".toml"]


def test_clear(alias_dict):
    alias_dict.clear()
    assert len(alias_dict.items()) == 0
    assert len(alias_dict.aliases()) == 0


def test_clear_aliases(alias_dict):
    alias_dict.clear_aliases()
    assert len(alias_dict.aliases()) == 0
    assert list(alias_dict.items()) == [
        (".json", {"callable": "load", "import_mod": "json", "read_mode": "r"}),
        (".yaml", {"callable": "safe_load", "import_mod": "yaml", "read_mode": "r"}),
        (".toml", {"callable": "load", "import_mod": "tomli", "read_mode": "r"}),
    ]


def test_setdefault():
    ad = AliasDict({"a": 1, "b": 2})
    ad.setdefault("foo", "bar")
    ad.add_alias("foo", "fizz")
    assert ad["foo"] == "bar"
    assert ad["fizz"] == "bar"


def test_setdefault_on_existing_aliased_key():
    ad = AliasDict({"a": 1, "b": 2})
    ad.setdefault("a", 42)
    ad.add_alias("a", "aa")
    assert ad["a"] == 1
    assert ad["aa"] == 1


def test_setdefault_with_alias():
    ad = AliasDict({"a": 1, "b": 2})
    ad.add_alias("a", "aa")
    result = ad.setdefault("aa", 99)
    assert result == 1
    assert ad["a"] == 1


def test_update_modifies_aliases():
    ad = AliasDict({"a": 1, "b": 2})
    ad.add_alias("a", "aa", "aaa")
    ad.update(**{"a": 40, "y": 50})
    assert list(ad.items()) == [("a", 40), ("b", 2), ("y", 50), ("aa", 40), ("aaa", 40)]


def test_update_with_alias_as_key():
    ad = AliasDict({"a": 1, "b": 2})
    ad.add_alias("a", "aa")
    ad.update({"aa": 99})
    assert ad["a"] == 99
    assert ad["aa"] == 99


def test_aliasdict_is_unhashable():
    ad = AliasDict({"a": 1, "b": 2})
    with pytest.raises(TypeError, match="unhashable type"):
        hash(ad)


def test_eq_with_non_aliasdict_returns_false():
    ad = AliasDict({"a": 1, "b": 2})
    assert (ad == 123) is False


def test_large_dictionary_with_many_aliases():
    # Ensure operations remain efficient with many keys and aliases
    ad = AliasDict({f"key_{i}": i for i in range(1000)})
    for i in range(1000):
        ad.add_alias(f"key_{i}", f"alias_{i}")

    assert len(ad) == 2000
    assert ad["key_500"] == ad["alias_500"] == 500
    assert ad.origin_len() == 1000


def test_copy():
    ad = AliasDict({"a": 1, "b": 2})
    ad.add_alias("a", "aa", "aaa")

    copy_ = ad.copy()
    assert copy_ == ad
    assert copy_ is not ad

    # Verify independence
    ad["a"] = 999
    ad.add_alias("b", "bb")
    assert copy_["a"] == 1
    assert "bb" not in copy_


def test_or_operator_with_dict():
    ad = AliasDict({"a": 1, "b": 2})
    ad.add_alias("a", "aa")
    result = ad | {"b": 20, "c": 3}

    assert result["a"] == result["aa"] == 1
    assert result["b"] == 20
    assert result["c"] == 3


def test_or_operator_with_aliasdict():
    ad1 = AliasDict({"a": 1, "b": 2})
    ad1.add_alias("a", "aa")

    ad2 = AliasDict({"b": 20, "c": 3})
    ad2.add_alias("c", "cc")

    result = ad1 | ad2

    assert result["a"] == result["aa"] == 1
    assert result["b"] == 20
    assert result["c"] == result["cc"] == 3


def test_ror_operator():
    ad = AliasDict({"b": 2, "c": 3})
    ad.add_alias("c", "cc")
    result = {"a": 1, "b": 20} | ad

    assert result["a"] == 1
    assert result["b"] == 2
    assert result["c"] == result["cc"] == 3


def test_ior_operator():
    ad = AliasDict({"a": 1, "b": 2})
    ad.add_alias("a", "aa")
    ad |= {"b": 20, "c": 3}

    assert ad["a"] == ad["aa"] == 1
    assert ad["b"] == 20
    assert ad["c"] == 3


def test_ior_operator_with_aliasdict():
    ad1 = AliasDict({"a": 1, "b": 2})
    ad1.add_alias("a", "aa")

    ad2 = AliasDict({"c": 3})
    ad2.add_alias("c", "cc")

    ad1 |= ad2

    assert ad1["a"] == ad1["aa"] == 1
    assert ad1["c"] == ad1["cc"] == 3


def test_fromkeys():
    ad = AliasDict.fromkeys(["a", "b", "c"], 0)
    assert ad["a"] == ad["b"] == ad["c"] == 0
    assert len(ad) == 3


def test_fromkeys_with_aliases():
    ad = AliasDict.fromkeys(["a", "b"], 0, aliases={"a": ["aa"], "b": ["bb"]})
    assert ad["a"] == ad["aa"] == 0
    assert ad["b"] == ad["bb"] == 0
    assert len(ad) == 4


def test_pickle():
    ad = AliasDict({"a": 1, "b": 2})
    ad.add_alias("a", "aa", "aaa")
    restored = pickle.loads(pickle.dumps(ad))

    assert restored == ad
    assert restored["aa"] == 1
    assert list(restored.aliases()) == ["aa", "aaa"]


def test_reversed():
    ad = AliasDict({"a": 1, "b": 2})
    ad.add_alias("a", "aa")

    assert list(ad) == ["a", "b", "aa"]
    assert list(reversed(ad)) == ["aa", "b", "a"]


def test_copy_module_shallow():
    ad = AliasDict({"a": [1, 2], "b": 2})
    ad.add_alias("a", "aa")
    shallow = copy.copy(ad)

    assert shallow == ad
    assert shallow is not ad
    assert shallow["a"] is ad["a"]  # Shallow copy shares nested objects
    assert list(shallow.aliases()) == ["aa"]


def test_copy_module_deep():
    ad = AliasDict({"a": [1, 2], "b": 2})
    ad.add_alias("a", "aa")
    deep = copy.deepcopy(ad)

    assert deep == ad
    assert deep is not ad
    assert deep["a"] is not ad["a"]  # Deep copy has independent nested objects
    assert deep["a"] == ad["a"]
    assert list(deep.aliases()) == ["aa"]


def test_origin_key():
    ad = AliasDict({"a": 1, "b": 2})
    ad.add_alias("a", "aa", "aaa")

    assert ad.origin_key("aa") == ad.origin_key("aaa") == "a"
    assert ad.origin_key("a") is None  # Not an alias, it's an origin key
    assert ad.origin_key("nonexistent") is None


def test_is_alias():
    ad = AliasDict({"a": 1, "b": 2})
    ad.add_alias("a", "aa")

    assert ad.is_alias("aa") is True
    assert ad.is_alias("a") is False  # Origin key, not alias
    assert ad.is_alias("b") is False
    assert ad.is_alias("nonexistent") is False


def test_has_aliases():
    ad = AliasDict({"a": 1, "b": 2})
    ad.add_alias("a", "aa")

    assert ad.has_aliases("a") is True
    assert ad.has_aliases("b") is False
    assert ad.has_aliases("aa") is False  # Alias, not origin key
    assert ad.has_aliases("nonexistent") is False


def test_subclass_copy_and_fromkeys():
    class MyAliasDict(AliasDict):
        pass

    ad = MyAliasDict({"a": 1, "b": 2})
    ad.add_alias("a", "aa")

    # copy() should return the subclass type
    copied = ad.copy()
    assert type(copied) is MyAliasDict
    assert copied["aa"] == 1

    # fromkeys() should return the subclass type
    from_keys = MyAliasDict.fromkeys(["x", "y"], 0, aliases={"x": ["xx"]})
    assert type(from_keys) is MyAliasDict
    assert from_keys["xx"] == 0
