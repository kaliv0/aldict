import pytest

from alterpy.alias_dict import AliasDict


@pytest.fixture()
def alias_dict():
    ad = AliasDict(
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
        }
    )
    ad.add_alias(".yaml", ".yml")
    return ad
