import unicodedata


def normalize_key(value: str | None) -> str:
    # Unify apostrophe variants and strip accents so the same name from
    # different sources compares equal, e.g. Deezer "L'indecis" vs Last.fm
    # "L’indécis".
    text = (value or "").replace("’", "'").replace("‘", "'").replace("`", "'")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(text.casefold().strip().split())


def text_close(a: str | None, b: str | None) -> bool:
    ka, kb = normalize_key(a), normalize_key(b)
    if not ka or not kb:
        return False
    if ka == kb or ka in kb or kb in ka:
        return True
    tokens_a, tokens_b = set(ka.split()), set(kb.split())
    if not tokens_a or not tokens_b:
        return False
    overlap = len(tokens_a & tokens_b) / min(len(tokens_a), len(tokens_b))
    return overlap >= 0.6
