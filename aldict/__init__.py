from .alias_dict import AliasDict as AliasDict
from .exception import AliasError as AliasError
from .exception import AliasValueError as AliasValueError
from .frozen_alias_dict import FrozenAliasDict as FrozenAliasDict

__version__ = "1.1.0"
__all__ = ["AliasDict", "FrozenAliasDict", "AliasError", "AliasValueError"]
