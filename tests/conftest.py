import pytest

from aldict.alias_dict import AliasDict


@pytest.fixture()
def aldict():
    return AliasDict({"a": 1, "b": 2}, aliases={"a": "aa"})


@pytest.fixture()
def single_aldict():
    return AliasDict({"c": 3}, aliases={"c": "cc"})


@pytest.fixture()
def multi_aldict():
    return AliasDict({"a": 1, "b": 2}, aliases={"a": ["aa", "aaa"]})


@pytest.fixture()
def plain_aldict():
    return AliasDict({"a": 1, "b": 2})


@pytest.fixture()
def ext_aldict():
    return AliasDict(
        {
            ".json": {
                "import_mod": "json",
                "callable": "load",
                "read_mode": "r",
            },
            ".yaml": {
                "import_mod": "yaml",
                "callable": "safe_load",
                "read_mode": "r",
            },
            ".toml": {
                "import_mod": "tomli",
                "callable": "load",
                "read_mode": "r",
            },
        },
        aliases={".yaml": [".yml"]},
    )
