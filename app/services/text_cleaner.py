"""
app/services/text_cleaner.py

Sanitizes raw PDF-extracted text before it is sent to any LLM.
Handles common OCR artifacts without destroying meaningful content.
"""
import re
import unicodedata


def clean_contract_text(text: str) -> str:
    """
    Clean OCR-extracted contract text.
    - Normalise unicode (NFC)
    - Replace non-ASCII chars that are clearly OCR noise with ASCII equivalents
    - Collapse runs of garbage characters
    - Fix common OCR misreads in legal text
    - Normalise whitespace without destroying paragraph structure
    """
    if not text:
        return text

    # 1. Unicode normalisation
    text = unicodedata.normalize("NFC", text)

    # 2. Replace known OCR substitutions common in scanned legal docs
    OCR_FIXES = {
        "\u2018": "'",   # left single quote
        "\u2019": "'",   # right single quote
        "\u201c": '"',   # left double quote
        "\u201d": '"',   # right double quote
        "\u2013": "-",   # en dash
        "\u2014": "-",   # em dash
        "\u2022": "-",   # bullet
        "\u00a7": "S.",  # section sign §
        "\u00b6": "P.",  # pilcrow ¶
        "\u2026": "...", # ellipsis
        "\u00a0": " ",   # non-breaking space
        "\u00ad": "",    # soft hyphen
        "\ufeff": "",    # BOM
        "\ufbff": "",    # private use area (common OCR artifact)
    }
    for bad, good in OCR_FIXES.items():
        text = text.replace(bad, good)

    # 3. Replace any remaining non-ASCII non-printable chars with a space
    #    Keep: standard ASCII printable (0x20-0x7e), newline (0x0a), tab (0x09)
    text = re.sub(r'[^\x09\x0a\x20-\x7e]', ' ', text)

    # 4. Fix common OCR digit/letter confusions in legal section numbers
    #    e.g. "l.I" → "1.1", "I.I" → "1.1" at line start
    text = re.sub(r'(?m)^([lI])\.([lI1])\s', r'1.\2 ', text)
    text = re.sub(r'(?m)^([lI])\.\s', r'1. ', text)

    # 5. Fix OCR space insertion inside words (e.g. "perfo1111ance" → "performance")
    #    Collapse sequences of repeated digits that look like OCR fill
    text = re.sub(r'(\w)1{3,}(\w)', r'\1\2', text)  # "perfo1111ance" → "performance"

    # 6. Collapse runs of 4+ identical non-word chars (pure garbage sequences)
    text = re.sub(r'([^\w\s])\1{4,}', r'\1\1', text)

    # 7. Normalise whitespace: collapse multiple spaces to one,
    #    but preserve paragraph breaks (double newlines)
    text = re.sub(r'[ \t]+', ' ', text)                # multiple spaces → one
    text = re.sub(r'\n{3,}', '\n\n', text)             # 3+ newlines → 2
    text = re.sub(r' \n', '\n', text)                   # trailing space before newline
    text = re.sub(r'\n ', '\n', text)                   # leading space after newline

    return text.strip()


def truncate_for_llm(text: str, max_chars: int, label: str = "text") -> str:
    """
    Truncate text to max_chars at a paragraph boundary.
    Logs a warning if truncation occurs.
    """
    if len(text) <= max_chars:
        return text

    import logging
    logger = logging.getLogger(__name__)
    truncated = text[:max_chars]
    # Try to break at paragraph boundary
    last_para = truncated.rfind("\n\n")
    if last_para > max_chars * 0.8:
        truncated = truncated[:last_para]
    logger.warning(
        f"truncate_for_llm: {label} truncated from {len(text)} to {len(truncated)} chars"
    )
    return truncated

# Made with Bob
