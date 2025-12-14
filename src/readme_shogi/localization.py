"""
Localization utilities for Readme Shogi.

Uses i18nice for translations management.
"""

from pathlib import Path
from typing import Any

import i18n

from readme_shogi.constants import ASSETS_DIR

# Configure i18nice
LOCALES_DIR = ASSETS_DIR / "locales"
i18n.load_path.append(str(LOCALES_DIR))
i18n.set("file_format", "yml")
i18n.set("filename_format", "{namespace}.{format}")
i18n.set("skip_locale_root_data", True)
i18n.set("use_locale_dirs", True)
i18n.set("fallback", "en")

# Default locale
DEFAULT_LOCALE = "en"

# Available locales
AVAILABLE_LOCALES = ["en", "ja", "zh-CN"]

# Locale display names
LOCALE_NAMES = {
    "en": "English",
    "ja": "日本語",
    "zh-CN": "简体中文",
}


def set_locale(locale: str) -> None:
    """Set the current locale for translations."""
    if locale in AVAILABLE_LOCALES:
        i18n.set("locale", locale)
    else:
        i18n.set("locale", DEFAULT_LOCALE)


def get_locale() -> str:
    """Get the current locale."""
    return i18n.get("locale") or DEFAULT_LOCALE


def t(key: str, **kwargs: Any) -> str:
    """Translate a key with optional interpolation."""
    result: str = i18n.t(f"translations.{key}", **kwargs)
    return result


def get_readme_filename(locale: str) -> str:
    """Get the README filename for a given locale."""
    if locale == DEFAULT_LOCALE:
        return "README.md"
    return f"README.{locale}.md"


def get_template_path(locale: str) -> Path:
    """Get the path to the README template for a given locale."""
    return LOCALES_DIR / locale / "README.template.md"


def generate_language_links(current_locale: str, readme_dir: str = ".") -> str:
    """
    Generate markdown links to other language versions.

    Args:
        current_locale: The current locale being rendered
        readme_dir: The directory where README files are stored (for relative links)

    Returns:
        Markdown string with language links
    """
    links = []
    for locale in AVAILABLE_LOCALES:
        name = LOCALE_NAMES.get(locale, locale)
        filename = get_readme_filename(locale)
        if locale == current_locale:
            links.append(f"**{name}**")
        else:
            links.append(f"[{name}]({filename})")
    return " | ".join(links)


def is_kanji_locale(locale: str) -> bool:
    """Check if the locale uses kanji rank labels (一二三...) instead of latin (a-i)."""
    return locale in ("ja", "zh-CN")


def uses_ki2_notation(locale: str) -> bool:
    """Check if the locale uses KI2 notation instead of USI."""
    return locale in ("ja", "zh-CN")
