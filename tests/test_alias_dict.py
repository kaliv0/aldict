import copy
import pickle

import pytest

from aldict import AliasDict, AliasError, AliasValueError
from aldict.alias_dict import (
    ALIAS_ALREADY_ASSIGNED,
    ALIAS_EXISTS_AS_KEY,
    ALIAS_NOT_FOUND,
    KEY_ALIAS_CANNOT_BE_EQUAL,
    KEY_EXISTS_AS_ALIAS,
    UNSUPPORTED_OPERAND_TYPES,
)


def test_alias_map(ext_aldict):
    assert ext_aldict[".toml"] == {
        "callable": "load",
        "import_mod": "tomli",
        "read_mode": "r",
    }
    assert (
        ext_aldict[".yml"]
        == ext_aldict[".yaml"]
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


def test_init_from_aliasdict_preserves_aliases(multi_aldict):
    ad2 = AliasDict(multi_aldict)

    assert ad2["a"] == ad2["aa"] == ad2["aaa"] == 1
    assert list(ad2.aliases()) == ["aa", "aaa"]

    # Verify independence (data, aliases and lookup_map)
    multi_aldict["a"] = 999
    multi_aldict.add_alias("b", "bb")
    assert ad2["a"] == 1
    assert "bb" not in ad2
    assert dict(ad2._lookup_map) == {"a": {"aa", "aaa"}}


def test_init_with_aliases_one_liner(plain_aldict):
    ad = AliasDict(plain_aldict, aliases={"a": "aa", "b": "bb"})
    assert ad["a"] == ad["aa"] == 1
    assert ad["b"] == ad["bb"] == 2
    assert list(ad.aliases()) == ["aa", "bb"]


def test_init_with_multiple_aliases_per_key(plain_aldict):
    ad = AliasDict(plain_aldict, aliases={"a": ["aa", "aaa", "aaaa"], "b": ["bb", "bbb"]})
    assert ad["a"] == ad["aa"] == ad["aaa"] == ad["aaaa"] == 1
    assert ad["b"] == ad["bb"] == ad["bbb"] == 2
    assert list(ad.aliases()) == ["aa", "aaa", "aaaa", "bb", "bbb"]


def test_init_with_aliases_validation():
    cases = [
        (KeyError, "nonexistent", {"a": 1}, {"nonexistent": ["aa"]}),
        (
            AliasValueError,
            KEY_ALIAS_CANNOT_BE_EQUAL.format(key="a"),
            {"a": 1},
            {"a": ["a"]},
        ),
        (
            AliasValueError,
            ALIAS_EXISTS_AS_KEY.format(alias="b"),
            {"a": 1, "b": 2},
            {"a": ["b"]},
        ),
    ]
    for exc, exc_msg, data, aliases in cases:
        with pytest.raises(exc, match=exc_msg):
            AliasDict(data, aliases=aliases)


def test_init_with_non_string_keys():
    ad = AliasDict({1: "one", 2: "two", (1, 2): "tuple_key"})
    assert ad[1] == "one"
    assert ad[2] == "two"
    assert ad[(1, 2)] == "tuple_key"

    ad.add_alias(1, 11)
    assert ad[11] == "one"


def test_init_from_aliasdict_with_non_string_keys():
    ad1 = AliasDict({1: "one", 2: "two", (1, 2): "tuple_key"}, aliases={1: [11, 111]})
    ad2 = AliasDict(ad1)

    assert ad2[1] == ad2[11] == ad2[111] == "one"
    assert ad2[(1, 2)] == "tuple_key"
    assert list(ad2.aliases()) == [11, 111]


def test_init_with_non_identifier_string_keys():
    ad = AliasDict({"my_key": 1, "other_key": 2, "123": 3, "has spaces": 4})
    assert ad["my_key"] == 1
    assert ad["other_key"] == 2
    assert ad["123"] == 3
    assert ad["has spaces"] == 4

    ad.add_alias("my_key", "also_dashed")
    assert ad["also_dashed"] == 1


def test_init_from_aliasdict_with_non_identifier_string_keys():
    ad1 = AliasDict({"my_key": 1, "123start": 2}, aliases={"my_key": "alt_key"})
    ad2 = AliasDict(ad1)

    assert ad2["my_key"] == ad2["alt_key"] == 1
    assert ad2["123start"] == 2
    assert list(ad2.aliases()) == ["alt_key"]


def test_add_alias(ext_aldict):
    ext_aldict.add_alias(".toml", ".tml")
    assert (
        ext_aldict[".toml"]
        == ext_aldict[".tml"]
        == {"callable": "load", "import_mod": "tomli", "read_mode": "r"}
    )


def test_add_alias_already_assigned_in_strict_mode_raises(aldict):
    with pytest.raises(AliasValueError, match=ALIAS_ALREADY_ASSIGNED.format(alias="aa", key="a")):
        aldict.add_alias("b", "aa", strict=True)


def test_add_alias_already_assigned_with_strict_false(aldict):
    assert list(aldict.items()) == [("a", 1), ("b", 2), ("aa", 1)]

    aldict.add_alias("b", "aa", strict=False)
    assert list(aldict.items()) == [("a", 1), ("b", 2), ("aa", 2)]


@pytest.mark.parametrize(
    "args",
    [
        (".jsn", ".joojoo", ".jazz"),  # *args
        ([".jsn", ".joojoo", ".jazz"],),  # list
        ((".jsn", ".joojoo", ".jazz"),),  # tuple
    ],
)
def test_add_multiple_aliases(ext_aldict, args):
    ext_aldict.add_alias(".json", *args)
    assert list(ext_aldict.keys()) == [
        ".json",
        ".yaml",
        ".toml",
        ".yml",
        ".jsn",
        ".joojoo",
        ".jazz",
    ]


def test_add_alias_raises(ext_aldict):
    with pytest.raises(AliasValueError, match=KEY_ALIAS_CANNOT_BE_EQUAL.format(key=".toml")):
        ext_aldict.add_alias(".toml", ".toml")


def test_add_alias_raises_if_alias_is_existing_key(plain_aldict):
    with pytest.raises(AliasValueError, match=ALIAS_EXISTS_AS_KEY.format(alias="b")):
        plain_aldict.add_alias("a", "b")


def test_update_alias(ext_aldict):
    # redirect ".yml" to point to ".toml"
    ext_aldict.add_alias(".toml", ".yml")
    assert list(ext_aldict.items()) == [
        (".json", {"callable": "load", "import_mod": "json", "read_mode": "r"}),
        (".yaml", {"callable": "safe_load", "import_mod": "yaml", "read_mode": "r"}),
        (".toml", {"callable": "load", "import_mod": "tomli", "read_mode": "r"}),
        (".yml", {"callable": "load", "import_mod": "tomli", "read_mode": "r"}),
    ]


def test_update_alias_raises(ext_aldict):
    with pytest.raises(KeyError, match=".foo"):
        ext_aldict.add_alias(".foo", ".bar")


def test_remove_alias(ext_aldict):
    assert list(ext_aldict.keys()) == [".json", ".yaml", ".toml", ".yml"]

    ext_aldict.remove_alias(".yml")
    assert list(ext_aldict.keys()) == [".json", ".yaml", ".toml"]
    assert list(ext_aldict.items()) == [
        (".json", {"callable": "load", "import_mod": "json", "read_mode": "r"}),
        (".yaml", {"callable": "safe_load", "import_mod": "yaml", "read_mode": "r"}),
        (".toml", {"callable": "load", "import_mod": "tomli", "read_mode": "r"}),
    ]


def test_remove_alias_raises(ext_aldict):
    assert list(ext_aldict.keys()) == [".json", ".yaml", ".toml", ".yml"]
    with pytest.raises(AliasError, match=ALIAS_NOT_FOUND.format(alias=".foo")):
        ext_aldict.remove_alias(".foo")


@pytest.mark.parametrize(
    "args",
    [
        (".yml", ".jsn"),  # *args
        ([".yml", ".jsn"],),  # list
        ((".yml", ".jsn"),),  # tuple
    ],
)
def test_remove_multiple_aliases(ext_aldict, args):
    ext_aldict.add_alias(".json", ".jsn")
    ext_aldict.remove_alias(*args)
    assert list(ext_aldict.keys()) == [".json", ".yaml", ".toml"]


def test_read_aliases(ext_aldict):
    ext_aldict.add_alias(".toml", ".tml")
    ext_aldict.add_alias(".json", ".jsn")
    ext_aldict.add_alias(".json", ".whaaaaat!")
    assert list(ext_aldict.aliases()) == [".yml", ".tml", ".jsn", ".whaaaaat!"]


def test_dictviews(ext_aldict):
    assert list(ext_aldict.keys()) == [".json", ".yaml", ".toml", ".yml"]
    assert list(ext_aldict.values()) == [
        {"import_mod": "json", "callable": "load", "read_mode": "r"},
        {"import_mod": "yaml", "callable": "safe_load", "read_mode": "r"},
        {"import_mod": "tomli", "callable": "load", "read_mode": "r"},
    ]
    assert list(ext_aldict.items()) == [
        (".json", {"callable": "load", "import_mod": "json", "read_mode": "r"}),
        (".yaml", {"callable": "safe_load", "import_mod": "yaml", "read_mode": "r"}),
        (".toml", {"callable": "load", "import_mod": "tomli", "read_mode": "r"}),
        (".yml", {"callable": "safe_load", "import_mod": "yaml", "read_mode": "r"}),
    ]


def test_dictviews_with_non_string_keys():
    ad = AliasDict({1: "one", 2: "two"}, aliases={1: 3})
    assert list(ad.keys()) == [1, 2, 3]
    assert list(ad.items()) == [(1, "one"), (2, "two"), (3, "one")]


def test_iterkeys(ext_aldict):
    it = ext_aldict.iterkeys()
    assert list(it) == [".json", ".yaml", ".toml", ".yml"]


def test_iterkeys_is_lazy(ext_aldict):
    it = ext_aldict.iterkeys()
    assert next(it) == ".json"
    assert next(it) == ".yaml"


def test_iterkeys_reflects_mutations(aldict):
    keys = list(aldict.iterkeys())
    assert keys == ["a", "b", "aa"]

    aldict.add_alias("b", "y")
    assert list(aldict.iterkeys()) == ["a", "b", "aa", "y"]


def test_iteritems(ext_aldict):
    it = ext_aldict.iteritems()
    result = list(it)
    assert result == [
        (".json", {"import_mod": "json", "callable": "load", "read_mode": "r"}),
        (".yaml", {"import_mod": "yaml", "callable": "safe_load", "read_mode": "r"}),
        (".toml", {"import_mod": "tomli", "callable": "load", "read_mode": "r"}),
        (".yml", {"import_mod": "yaml", "callable": "safe_load", "read_mode": "r"}),
    ]


def test_iteritems_is_lazy(ext_aldict):
    it = ext_aldict.iteritems()
    assert next(it) == (".json", {"import_mod": "json", "callable": "load", "read_mode": "r"})
    assert next(it) == (".yaml", {"import_mod": "yaml", "callable": "safe_load", "read_mode": "r"})


def test_iteritems_reflects_mutations(aldict):
    assert list(aldict.iteritems()) == [("a", 1), ("b", 2), ("aa", 1)]

    aldict.add_alias("b", "y")
    assert list(aldict.iteritems()) == [("a", 1), ("b", 2), ("aa", 1), ("y", 2)]


def test_remove_key_and_aliases(ext_aldict):
    assert list(ext_aldict.keys()) == [".json", ".yaml", ".toml", ".yml"]

    ext_aldict.pop(".yaml")

    assert list(ext_aldict.keys()) == [".json", ".toml"]
    assert dict(ext_aldict._lookup_map) == {}


def test_contains(ext_aldict):
    ext_aldict.add_alias(".toml", ".tml")
    assert (".toml" in ext_aldict) is True
    assert (".tml" in ext_aldict) is True
    assert (".foo" in ext_aldict) is False


def test_get(ext_aldict):
    assert ext_aldict.get(".yaml") == {
        "callable": "safe_load",
        "import_mod": "yaml",
        "read_mode": "r",
    }
    assert ext_aldict.get(".yml") == {
        "callable": "safe_load",
        "import_mod": "yaml",
        "read_mode": "r",
    }
    assert ext_aldict.get(".foo") is None


def test_pop_alias_doesnt_remove_key(ext_aldict):
    assert ext_aldict.pop(".yml") == {
        "callable": "safe_load",
        "import_mod": "yaml",
        "read_mode": "r",
    }
    assert list(ext_aldict.keys()) == [".json", ".yaml", ".toml"]


def test_pop_with_default(plain_aldict):
    assert plain_aldict.pop("nonexistent", "default") == "default"
    assert plain_aldict.pop("a") == 1
    assert plain_aldict.pop("a", "gone") == "gone"


def test_pop_nonexistent_key_raises(plain_aldict):
    with pytest.raises(KeyError):
        plain_aldict.pop("nonexistent")


def test_iter(ext_aldict):
    assert [k for k in ext_aldict] == [".json", ".yaml", ".toml", ".yml"]


def test_origin_keys(ext_aldict):
    assert list(ext_aldict.origin_keys()) == [".json", ".yaml", ".toml"]


def test_keys_with_aliases(ext_aldict):
    assert list(ext_aldict.keys_with_aliases()) == [(".yaml", {".yml"})]

    ext_aldict.add_alias(".toml", ".tml", ".tommy", ".tomograph")
    assert list(ext_aldict.keys_with_aliases()) == [
        (".yaml", {".yml"}),
        (".toml", {".tml", ".tommy", ".tomograph"}),
    ]


def test_repr(ext_aldict):
    assert str(ext_aldict) == (
        "AliasDict({"
        "'.json': {'import_mod': 'json', 'callable': 'load', 'read_mode': 'r'}, "
        "'.yaml': {'import_mod': 'yaml', 'callable': 'safe_load', 'read_mode': 'r'}, "
        "'.toml': {'import_mod': 'tomli', 'callable': 'load', 'read_mode': 'r'}, "
        "'.yml': {'import_mod': 'yaml', 'callable': 'safe_load', 'read_mode': 'r'}"
        "})"
    )


def test_eq(multi_aldict, plain_aldict):
    ad_1 = multi_aldict
    ad_2 = AliasDict(multi_aldict)
    ad_3 = AliasDict(plain_aldict, aliases={"a": "abc"})

    assert ad_1 == ad_2
    assert ad_1 != ad_3
    assert ad_2 != ad_3


def test_dict_len_includes_aliases(ext_aldict):
    assert list(ext_aldict.keys()) == [".json", ".yaml", ".toml", ".yml"]
    assert len(ext_aldict) == 4


def test_dict_origin_len_excludes_aliases(ext_aldict):
    assert list(ext_aldict.keys()) == [".json", ".yaml", ".toml", ".yml"]
    assert ext_aldict.origin_len() == 3


def test_popitem(ext_aldict):
    # pops first item -> MutableMapping.popitem()
    assert ext_aldict.popitem() == (
        ".json",
        {"callable": "load", "import_mod": "json", "read_mode": "r"},
    )
    assert ext_aldict.popitem() == (
        ".yaml",
        {"callable": "safe_load", "import_mod": "yaml", "read_mode": "r"},
    )
    assert len(ext_aldict.keys_with_aliases()) == 0
    assert list(ext_aldict.keys()) == [".toml"]


def test_clear(ext_aldict):
    ext_aldict.clear()
    assert len(ext_aldict.items()) == 0
    assert len(ext_aldict.aliases()) == 0
    assert len(ext_aldict._lookup_map) == 0


def test_clear_aliases(ext_aldict):
    ext_aldict.clear_aliases()
    assert len(ext_aldict.aliases()) == 0
    assert len(ext_aldict._lookup_map) == 0
    assert list(ext_aldict.items()) == [
        (".json", {"callable": "load", "import_mod": "json", "read_mode": "r"}),
        (".yaml", {"callable": "safe_load", "import_mod": "yaml", "read_mode": "r"}),
        (".toml", {"callable": "load", "import_mod": "tomli", "read_mode": "r"}),
    ]


def test_setdefault(plain_aldict):
    plain_aldict.setdefault("foo", "bar")
    plain_aldict.add_alias("foo", "fizz")
    assert plain_aldict["foo"] == "bar"
    assert plain_aldict["fizz"] == "bar"


def test_setdefault_on_existing_aliased_key(plain_aldict):
    plain_aldict.setdefault("a", 42)
    plain_aldict.add_alias("a", "aa")
    assert plain_aldict["a"] == 1
    assert plain_aldict["aa"] == 1


def test_setdefault_with_alias(aldict):
    result = aldict.setdefault("aa", 99)
    assert result == 1
    assert aldict["a"] == 1


def test_update_modifies_aliases(multi_aldict):
    multi_aldict.update(**{"a": 40, "y": 50})
    assert list(multi_aldict.items()) == [
        ("a", 40),
        ("b", 2),
        ("y", 50),
        ("aa", 40),
        ("aaa", 40),
    ]


def test_update_with_alias_as_key(aldict):
    aldict.update({"aa": 99})
    assert aldict["a"] == 99
    assert aldict["aa"] == 99


def test_aliasdict_is_unhashable(plain_aldict):
    with pytest.raises(TypeError, match="unhashable type: 'AliasDict'"):
        hash(plain_aldict)


def test_eq_with_non_aliasdict_returns_false(plain_aldict):
    assert (plain_aldict == 123) is False


def test_large_dictionary_with_many_aliases():
    # Ensure operations remain efficient with many keys and aliases
    ad = AliasDict({f"key_{i}": i for i in range(1000)})
    for i in range(1000):
        ad.add_alias(f"key_{i}", f"alias_{i}")

    assert len(ad) == 2000
    assert ad["key_500"] == ad["alias_500"] == 500
    assert ad.origin_len() == 1000


def test_or_operator_with_dict(aldict):
    result = aldict | {"b": 20, "c": 3}

    assert result["a"] == result["aa"] == 1
    assert result["b"] == 20
    assert result["c"] == 3

    assert result.origin_len() == 3
    assert len(result.aliases()) == 1
    assert len(result.keys()) == 4


def test_or_operator_with_aliasdict(aldict, single_aldict):
    single_aldict["b"] = 20
    result = aldict | single_aldict

    assert result["a"] == result["aa"] == 1
    assert result["b"] == 20
    assert result["c"] == result["cc"] == 3

    assert result.origin_len() == 3
    assert len(result.aliases()) == 2
    assert len(result.keys()) == 5


def test_ror_operator(single_aldict):
    single_aldict["b"] = 2
    result = {"a": 1, "b": 20} | single_aldict

    assert result["a"] == 1
    assert result["b"] == 2
    assert result["c"] == result["cc"] == 3

    assert result.origin_len() == 3
    assert len(result.aliases()) == 1
    assert len(result.keys()) == 4


def test_ior_operator(aldict):
    aldict |= {"b": 20, "c": 3}

    assert aldict["a"] == aldict["aa"] == 1
    assert aldict["b"] == 20
    assert aldict["c"] == 3

    assert aldict.origin_len() == 3
    assert len(aldict.aliases()) == 1
    assert len(aldict.keys()) == 4


def test_ior_operator_with_aliasdict(aldict, single_aldict):
    aldict |= single_aldict

    assert aldict["a"] == aldict["aa"] == 1
    assert aldict["c"] == aldict["cc"] == 3

    assert aldict.origin_len() == 3
    assert len(aldict.aliases()) == 2
    assert len(aldict.keys()) == 5


def test_ior_operator_unsupported_opernad_type(aldict):
    with pytest.raises(TypeError, match=UNSUPPORTED_OPERAND_TYPES.format(target="AliasDict", other="list")):
        aldict |= [1, 2, 3]


def test_fromkeys():
    ad = AliasDict.fromkeys(["a", "b", "c"], 0)
    assert ad["a"] == ad["b"] == ad["c"] == 0
    assert len(ad) == 3


def test_fromkeys_with_aliases():
    ad = AliasDict.fromkeys(["a", "b"], 0, aliases={"a": ["aa"], "b": ["bb"]})
    assert ad["a"] == ad["aa"] == 0
    assert ad["b"] == ad["bb"] == 0
    assert len(ad) == 4


def test_pickle(multi_aldict):
    restored = pickle.loads(pickle.dumps(multi_aldict))

    assert restored == multi_aldict
    assert restored["aa"] == 1
    assert list(restored.aliases()) == ["aa", "aaa"]
    assert dict(restored._lookup_map) == {"a": {"aa", "aaa"}}


def test_reversed(aldict):
    assert list(aldict) == ["a", "b", "aa"]
    assert list(reversed(aldict)) == ["aa", "b", "a"]


def test_copy(multi_aldict):
    cp = multi_aldict.copy()
    assert cp == multi_aldict
    assert cp is not multi_aldict

    # Verify independence (data, aliases and lookup_map)
    multi_aldict["a"] = 999
    assert cp["a"] == 1

    multi_aldict.add_alias("b", "bb")
    assert "bb" not in cp
    assert dict(cp._lookup_map) == {"a": {"aa", "aaa"}}


def test_copy_module_shallow(aldict):
    aldict["a"] = [1, 2]
    shallow = copy.copy(aldict)

    assert shallow == aldict
    assert shallow is not aldict
    assert shallow["a"] is aldict["a"]  # Shallow copy shares nested objects
    assert list(shallow.aliases()) == ["aa"]


def test_copy_module_deep(aldict):
    aldict["a"] = [1, 2]
    deep = copy.deepcopy(aldict)

    assert deep == aldict
    assert deep is not aldict
    assert deep["a"] is not aldict["a"]  # Deep copy has independent nested objects
    assert deep["a"] == aldict["a"]
    assert list(deep.aliases()) == ["aa"]

    # Verify lookup_map independence
    deep.add_alias("a", "z")
    assert "z" not in aldict
    assert dict(aldict._lookup_map) == {"a": {"aa"}}


def test_origin_key(multi_aldict):
    assert multi_aldict.origin_key("aa") == multi_aldict.origin_key("aaa") == "a"
    assert multi_aldict.origin_key("a") is None  # Not an alias, it's an origin key
    assert multi_aldict.origin_key("nonexistent") is None


def test_is_alias(aldict):
    assert aldict.is_alias("aa") is True
    assert aldict.is_alias("a") is False  # Origin key, not alias
    assert aldict.is_alias("b") is False
    assert aldict.is_alias("nonexistent") is False


def test_has_aliases(aldict):
    assert aldict.has_aliases("a") is True
    assert aldict.has_aliases("b") is False
    assert aldict.has_aliases("aa") is False  # Alias, not origin key
    assert aldict.has_aliases("nonexistent") is False


def test_subclass_shows_correct_type(aldict):
    class MyAliasDict(AliasDict):
        pass

    ad = MyAliasDict(aldict)
    copied = ad.copy()
    assert type(copied) is MyAliasDict
    assert copied["aa"] == 1

    from_keys = MyAliasDict.fromkeys(["x", "y"], 0, aliases={"x": "xx"})
    assert type(from_keys) is MyAliasDict
    assert from_keys["xx"] == 0

    result = {"a": 1} | MyAliasDict({"b": 2}, aliases={"b": "bb"})
    assert type(result) is MyAliasDict


def test_add_alias_updates_lookup_map(plain_aldict):
    plain_aldict.add_alias("a", "x", "y")
    assert dict(plain_aldict._lookup_map) == {"a": {"x", "y"}}


def test_remove_alias_updates_lookup_map(multi_aldict):
    multi_aldict.remove_alias("aa")
    assert dict(multi_aldict._lookup_map) == {"a": {"aaa"}}


def test_remove_last_alias_cleans_lookup_map(aldict):
    aldict.remove_alias("aa")
    assert dict(aldict._lookup_map) == {}
    assert "a" not in aldict._lookup_map


def test_delitem_key_cleans_lookup_map(multi_aldict):
    del multi_aldict["a"]
    assert dict(multi_aldict._lookup_map) == {}
    assert "aa" not in multi_aldict
    assert "aaa" not in multi_aldict


def test_delitem_alias_updates_lookup_map(multi_aldict):
    del multi_aldict["aa"]
    assert dict(multi_aldict._lookup_map) == {"a": {"aaa"}}


def test_delitem_last_alias_cleans_lookup_map(aldict):
    del aldict["aa"]
    assert dict(aldict._lookup_map) == {}


def test_pop_alias_updates_lookup_map(multi_aldict):
    multi_aldict.pop("aa")
    assert dict(multi_aldict._lookup_map) == {"a": {"aaa"}}


def test_popitem_cleans_lookup_map(aldict):
    aldict.add_alias("b", "bb")
    aldict.popitem()  # pops "a"
    assert dict(aldict._lookup_map) == {"b": {"bb"}}
    assert "aa" not in aldict


def test_delitem_key_without_aliases(aldict):
    del aldict["b"]
    assert "b" not in aldict
    assert dict(aldict._lookup_map) == {"a": {"aa"}}


def test_pop_key_without_aliases(aldict):
    aldict.pop("b")
    assert "b" not in aldict
    assert dict(aldict._lookup_map) == {"a": {"aa"}}


def test_reassign_alias_non_strict_updates_lookup_map(aldict):
    aldict.add_alias("b", "aa")  # reassign aa from a to b
    assert dict(aldict._lookup_map) == {"b": {"aa"}}
    # _alias_map points to the latest key
    assert aldict.origin_key("aa") == "b"


def test_or_lookup_map_independence(aldict, single_aldict):
    result = aldict | single_aldict
    result.add_alias("a", "z")
    assert "z" not in aldict
    assert "z" not in single_aldict


def test_or_preserves_both_lookup_maps(aldict, single_aldict):
    result = aldict | single_aldict
    assert dict(result._lookup_map) == {"a": {"aa"}, "c": {"cc"}}


def test_ror_lookup_map_independence():
    ad = AliasDict({"b": 2}, aliases={"b": "y"})
    result = {"a": 1} | ad
    result.add_alias("b", "z")
    assert "z" not in ad
    assert dict(ad._lookup_map) == {"b": {"y"}}


def test_ior_lookup_map_independence(aldict, single_aldict):
    aldict |= single_aldict
    aldict.add_alias("c", "z")
    assert "z" not in single_aldict
    assert dict(single_aldict._lookup_map) == {"c": {"cc"}}


def test_eq_different_lookup_maps(aldict, plain_aldict):
    ad2 = AliasDict(plain_aldict, aliases={"b": "aa"})
    assert aldict != ad2


def test_or_raises_when_other_alias_collides_with_self_key(plain_aldict):
    ad1 = AliasDict(plain_aldict)
    ad1["x"] = 2
    ad2 = AliasDict({"c": 3}, aliases={"c": "x"})
    with pytest.raises(AliasValueError, match=ALIAS_EXISTS_AS_KEY.format(alias="x")):
        ad1 | ad2


def test_or_raises_when_other_key_collides_with_self_alias(aldict):
    ad2 = AliasDict({"aa": 2})
    with pytest.raises(AliasValueError, match=KEY_EXISTS_AS_ALIAS.format(key="aa")):
        aldict | ad2


def test_ror_raises_when_alias_collides_with_key():
    ad = AliasDict({"b": 2}, aliases={"b": "a"})
    with pytest.raises(AliasValueError, match=ALIAS_EXISTS_AS_KEY.format(alias="a")):
        {"a": 1} | ad


def test_ror_raises_when_other_key_collides_with_self_alias():
    ad = AliasDict({"a": 2}, aliases={"a": "y"})
    with pytest.raises(AliasValueError, match=ALIAS_EXISTS_AS_KEY.format(alias="y")):
        {"y": 1} | ad


def test_ior_raises_when_other_alias_collides_with_self_key(plain_aldict):
    ad1 = AliasDict(plain_aldict)
    ad1["x"] = 2
    ad2 = AliasDict({"c": 3}, aliases={"c": "x"})
    with pytest.raises(AliasValueError, match=ALIAS_EXISTS_AS_KEY.format(alias="x")):
        ad1 |= ad2


def test_ior_raises_when_other_key_collides_with_self_alias(aldict):
    ad2 = AliasDict({"aa": 2})
    with pytest.raises(AliasValueError, match=KEY_EXISTS_AS_ALIAS.format(key="aa")):
        aldict |= ad2


def test_eq_same_aliases_different_grouping(multi_aldict, plain_aldict):
    ad2 = AliasDict(plain_aldict, aliases={"a": "aa", "b": "aaa"})
    assert multi_aldict != ad2


def test_or_merges_lookup_map_sets_for_shared_key(aldict):
    ad2 = AliasDict({"a": 2}, aliases={"a": "aaa"})
    result = aldict | ad2

    assert result._lookup_map["a"] == {"aa", "aaa"}
    assert result._alias_map["aa"] == result._alias_map["aaa"] == "a"
    assert result.has_aliases("a")
    assert dict(result.keys_with_aliases()) == {"a": {"aa", "aaa"}}


def test_ior_merges_lookup_map_sets_for_shared_key(aldict):
    ad2 = AliasDict({"a": 2}, aliases={"a": "aaa"})
    aldict |= ad2

    assert aldict._lookup_map["a"] == {"aa", "aaa"}
    assert aldict._alias_map["aa"] == aldict._alias_map["aaa"] == "a"


def test_or_raises_when_same_alias_maps_to_different_keys(aldict):
    ad2 = AliasDict({"c": 3}, aliases={"c": "aa"})
    with pytest.raises(AliasValueError, match=ALIAS_ALREADY_ASSIGNED.format(alias="aa", key="a")):
        aldict | ad2


def test_ior_raises_when_same_alias_maps_to_different_keys(aldict):
    ad2 = AliasDict({"c": 3}, aliases={"c": "aa"})
    with pytest.raises(AliasValueError, match=ALIAS_ALREADY_ASSIGNED.format(alias="aa", key="a")):
        aldict |= ad2


def test_ror_raises_when_same_alias_maps_to_different_keys(aldict):
    ad2 = AliasDict({"b": 3}, aliases={"b": "aa"})
    with pytest.raises(AliasValueError, match=ALIAS_ALREADY_ASSIGNED.format(alias="aa", key="b")):
        ad2 | aldict
