"""
locales/ — 語系套件

每個語系是一個獨立模組，export 一個 LocaleStrings 物件。
"""
from .base import LocaleStrings
from .zh_TW import ZH_TW
from .en_US import EN_US
from .ja_JP import JA_JP

_REGISTRY = {
    "zh_TW": ZH_TW,
    "en_US": EN_US,
    "ja_JP": JA_JP,
}


def get_locale(lang: str) -> LocaleStrings:
    """取得語系物件，不認得的語系 fallback 到 zh_TW。"""
    return _REGISTRY.get(lang, ZH_TW)


__all__ = ["LocaleStrings", "get_locale", "ZH_TW", "EN_US", "JA_JP"]
