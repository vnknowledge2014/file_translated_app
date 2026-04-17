"""Japanese encoding detection and text file reading."""

import chardet


def read_text_file(file_path: str) -> str:
    """Read text file with automatic encoding detection.

    Handles common Japanese encodings: UTF-8, Shift_JIS, EUC-JP, CP932.
    Uses chardet for initial detection, then applies JP-specific fallbacks.

    Args:
        file_path: Absolute path to text file.

    Returns:
        Decoded text content as string.

    Raises:
        FileNotFoundError: If file doesn't exist.
    """
    with open(file_path, "rb") as f:
        raw = f.read()

    if not raw:
        return ""

    detected = chardet.detect(raw)
    encoding = detected["encoding"] or "utf-8"

    # Common JP encoding corrections:
    # chardet sometimes misidentifies Shift_JIS/EUC-JP as ASCII or Windows-1252
    # when the file has high bytes (non-ASCII Japanese characters).
    if encoding.lower() in ("ascii", "windows-1252") and any(b > 127 for b in raw):
        for try_enc in ["shift_jis", "euc-jp", "utf-8"]:
            try:
                return raw.decode(try_enc)
            except UnicodeDecodeError:
                continue

    return raw.decode(encoding, errors="replace")
