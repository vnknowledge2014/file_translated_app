"""Language Registry — profiles for all supported languages.

Each LanguageProfile defines the linguistic characteristics needed by
the translation pipeline: character detection ranges, script type,
spacing rules, sentence boundaries, and encoding support.

Usage:
    from app.languages import get_language, get_language_name, SUPPORTED_LANGUAGES

    profile = get_language("ja")
    print(profile.name)         # "Japanese"
    print(profile.has_spaces)   # False
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class LanguageProfile:
    """Linguistic profile for a single language.

    Attributes:
        code: ISO 639-1 code (e.g., "ja", "vi", "en").
        name: English name.
        native_name: Name in the language itself.
        script: Script family ("cjk", "latin", "cyrillic", "arabic", etc.).
        has_spaces: Whether the language uses spaces to separate words.
        char_ranges: Unicode codepoint ranges for character detection.
                     Each tuple is (start, end) inclusive.
        encodings: Common file encodings for this language.
        sentence_enders: Characters that mark sentence boundaries.
        example_terms: Example source→target pairs for prompt engineering.
        flag_emoji: Flag emoji for UI display.
    """

    code: str
    name: str
    native_name: str
    script: str
    has_spaces: bool
    char_ranges: tuple[tuple[int, int], ...] = ()
    encodings: tuple[str, ...] = ("utf-8",)
    sentence_enders: str = ".!?"
    example_terms: dict[str, str] = field(default_factory=dict)
    flag_emoji: str = "🌐"


# ── Language Profiles ──────────────────────────────────────────────────────────

JAPANESE = LanguageProfile(
    code="ja",
    name="Japanese",
    native_name="日本語",
    script="cjk",
    has_spaces=False,
    char_ranges=(
        (0x3040, 0x309F),  # Hiragana
        (0x30A0, 0x30FF),  # Katakana
        (0x4E00, 0x9FFF),  # CJK Unified Ideographs
        (0x3400, 0x4DBF),  # CJK Extension A
        (0xFF10, 0xFF19),  # Fullwidth digits
        (0xFF21, 0xFF5A),  # Fullwidth latin
        (0xFF65, 0xFF9F),  # Halfwidth katakana
    ),
    encodings=("utf-8", "shift_jis", "euc-jp", "cp932", "iso-2022-jp"),
    sentence_enders="。！？",
    example_terms={"管理": "Management", "設定": "Settings"},
    flag_emoji="🇯🇵",
)

VIETNAMESE = LanguageProfile(
    code="vi",
    name="Vietnamese",
    native_name="Tiếng Việt",
    script="latin",
    has_spaces=True,
    char_ranges=(
        # Vietnamese-specific diacritics (Latin Extended Additional)
        (0x1EA0, 0x1EF9),
        # Latin Extended-B (Ơ, Ư)
        (0x01A0, 0x01B4),
    ),
    encodings=("utf-8", "cp1258"),
    sentence_enders=".!?",
    example_terms={"Quản lý": "Management", "Cài đặt": "Settings"},
    flag_emoji="🇻🇳",
)

CHINESE_SIMPLIFIED = LanguageProfile(
    code="zh",
    name="Chinese (Simplified)",
    native_name="简体中文",
    script="cjk",
    has_spaces=False,
    char_ranges=(
        (0x4E00, 0x9FFF),  # CJK Unified Ideographs
        (0x3400, 0x4DBF),  # CJK Extension A
        (0x20000, 0x2A6DF),  # CJK Extension B
        (0x3000, 0x303F),  # CJK Symbols and Punctuation
    ),
    encodings=("utf-8", "gb2312", "gbk", "gb18030"),
    sentence_enders="。！？",
    example_terms={"管理": "Management", "设置": "Settings"},
    flag_emoji="🇨🇳",
)

CHINESE_TRADITIONAL = LanguageProfile(
    code="zh-TW",
    name="Chinese (Traditional)",
    native_name="繁體中文",
    script="cjk",
    has_spaces=False,
    char_ranges=(
        (0x4E00, 0x9FFF),
        (0x3400, 0x4DBF),
        (0x20000, 0x2A6DF),
        (0x3000, 0x303F),
    ),
    encodings=("utf-8", "big5", "big5hkscs"),
    sentence_enders="。！？",
    example_terms={"管理": "Management", "設定": "Settings"},
    flag_emoji="🇹🇼",
)

KOREAN = LanguageProfile(
    code="ko",
    name="Korean",
    native_name="한국어",
    script="hangul",
    has_spaces=True,
    char_ranges=(
        (0xAC00, 0xD7AF),  # Hangul Syllables
        (0x1100, 0x11FF),  # Hangul Jamo
        (0x3130, 0x318F),  # Hangul Compatibility Jamo
    ),
    encodings=("utf-8", "euc-kr", "cp949"),
    sentence_enders=".!?。",
    example_terms={"관리": "Management", "설정": "Settings"},
    flag_emoji="🇰🇷",
)

ENGLISH = LanguageProfile(
    code="en",
    name="English",
    native_name="English",
    script="latin",
    has_spaces=True,
    char_ranges=(
        (0x0041, 0x005A),  # A-Z
        (0x0061, 0x007A),  # a-z
    ),
    encodings=("utf-8", "ascii", "latin-1"),
    sentence_enders=".!?",
    example_terms={"Management": "Quản lý"},
    flag_emoji="🇬🇧",
)

FRENCH = LanguageProfile(
    code="fr",
    name="French",
    native_name="Français",
    script="latin",
    has_spaces=True,
    char_ranges=(
        (0x00C0, 0x00FF),  # Latin-1 Supplement (À-ÿ)
        (0x0152, 0x0153),  # Œ, œ
    ),
    encodings=("utf-8", "latin-1", "cp1252"),
    sentence_enders=".!?",
    flag_emoji="🇫🇷",
)

GERMAN = LanguageProfile(
    code="de",
    name="German",
    native_name="Deutsch",
    script="latin",
    has_spaces=True,
    char_ranges=(
        (0x00C0, 0x00FF),  # Latin-1 Supplement (ä, ö, ü, ß)
    ),
    encodings=("utf-8", "latin-1", "cp1252"),
    sentence_enders=".!?",
    flag_emoji="🇩🇪",
)

SPANISH = LanguageProfile(
    code="es",
    name="Spanish",
    native_name="Español",
    script="latin",
    has_spaces=True,
    char_ranges=(
        (0x00C0, 0x00FF),  # Latin-1 Supplement
        (0x00D1, 0x00D1),  # Ñ
        (0x00F1, 0x00F1),  # ñ
    ),
    encodings=("utf-8", "latin-1", "cp1252"),
    sentence_enders=".!?¡¿",
    flag_emoji="🇪🇸",
)

THAI = LanguageProfile(
    code="th",
    name="Thai",
    native_name="ภาษาไทย",
    script="thai",
    has_spaces=False,
    char_ranges=(
        (0x0E00, 0x0E7F),  # Thai block
    ),
    encodings=("utf-8", "cp874", "tis-620"),
    sentence_enders=".",
    flag_emoji="🇹🇭",
)

INDONESIAN = LanguageProfile(
    code="id",
    name="Indonesian",
    native_name="Bahasa Indonesia",
    script="latin",
    has_spaces=True,
    char_ranges=(
        (0x0041, 0x005A),
        (0x0061, 0x007A),
    ),
    encodings=("utf-8",),
    sentence_enders=".!?",
    flag_emoji="🇮🇩",
)

RUSSIAN = LanguageProfile(
    code="ru",
    name="Russian",
    native_name="Русский",
    script="cyrillic",
    has_spaces=True,
    char_ranges=(
        (0x0400, 0x04FF),  # Cyrillic
        (0x0500, 0x052F),  # Cyrillic Supplement
    ),
    encodings=("utf-8", "cp1251", "koi8-r"),
    sentence_enders=".!?",
    flag_emoji="🇷🇺",
)

PORTUGUESE = LanguageProfile(
    code="pt",
    name="Portuguese",
    native_name="Português",
    script="latin",
    has_spaces=True,
    char_ranges=((0x00C0, 0x00FF),),
    encodings=("utf-8", "latin-1", "cp1252"),
    sentence_enders=".!?",
    flag_emoji="🇵🇹",
)

ARABIC = LanguageProfile(
    code="ar",
    name="Arabic",
    native_name="العربية",
    script="arabic",
    has_spaces=True,
    char_ranges=(
        (0x0600, 0x06FF),  # Arabic
        (0x0750, 0x077F),  # Arabic Supplement
        (0xFB50, 0xFDFF),  # Arabic Presentation Forms-A
        (0xFE70, 0xFEFF),  # Arabic Presentation Forms-B
    ),
    encodings=("utf-8", "cp1256"),
    sentence_enders=".!?。",
    flag_emoji="🇸🇦",
)

HINDI = LanguageProfile(
    code="hi",
    name="Hindi",
    native_name="हिन्दी",
    script="devanagari",
    has_spaces=True,
    char_ranges=(
        (0x0900, 0x097F),  # Devanagari
        (0xA8E0, 0xA8FF),  # Devanagari Extended
    ),
    encodings=("utf-8",),
    sentence_enders="।.!?",
    flag_emoji="🇮🇳",
)


# ── Registry ──────────────────────────────────────────────────────────────────

_ALL_LANGUAGES: dict[str, LanguageProfile] = {}


def _register(*profiles: LanguageProfile) -> None:
    for p in profiles:
        _ALL_LANGUAGES[p.code] = p


_register(
    JAPANESE,
    VIETNAMESE,
    CHINESE_SIMPLIFIED,
    CHINESE_TRADITIONAL,
    KOREAN,
    ENGLISH,
    FRENCH,
    GERMAN,
    SPANISH,
    THAI,
    INDONESIAN,
    RUSSIAN,
    PORTUGUESE,
    ARABIC,
    HINDI,
)

# Public API

SUPPORTED_LANGUAGES: dict[str, LanguageProfile] = _ALL_LANGUAGES


def get_language(code: str) -> LanguageProfile:
    """Get a language profile by ISO 639-1 code.

    Args:
        code: Language code (e.g., "ja", "vi", "en").

    Returns:
        LanguageProfile for the requested language.

    Raises:
        ValueError: If the language code is not supported.
    """
    profile = _ALL_LANGUAGES.get(code)
    if profile is None:
        raise ValueError(
            f"Unsupported language: '{code}'. "
            f"Supported: {sorted(_ALL_LANGUAGES.keys())}"
        )
    return profile


def get_language_name(code: str) -> str:
    """Get the English name of a language by code.

    Args:
        code: Language code.

    Returns:
        English name (e.g., "Japanese").
    """
    return get_language(code).name


def list_languages() -> list[dict]:
    """List all supported languages for API/UI consumption.

    Returns:
        List of dicts with code, name, native_name, flag_emoji.
        Includes 'auto' as the first entry for Auto Detect.
    """
    auto_entry = {
        "code": "auto",
        "name": "Auto Detect",
        "native_name": "Auto",
        "flag": "",
    }
    langs = [
        {
            "code": p.code,
            "name": p.name,
            "native_name": p.native_name,
            "flag": p.flag_emoji,
        }
        for p in sorted(_ALL_LANGUAGES.values(), key=lambda p: p.name)
    ]
    return [auto_entry] + langs
