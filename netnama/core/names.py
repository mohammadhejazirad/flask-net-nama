"""Persian given names and domain-label combinations.

The name list is the MIT-licensed dataset from
https://github.com/mohammadhejazirad/persian-names (v2.0.0).
"""

import json
import re
from functools import cache
from pathlib import Path

from netnama.core.finglish import PLACES, normalize_fa, transliterate
from netnama.core.validation import ValidationError

_DATA = Path(__file__).resolve().parents[1] / "resources" / "persian_names.json"
_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
_TLD = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,22}[a-z0-9])?(?:\.[a-z]{2,12})?$")
_ROLES = {"name", "keyword", "place", "custom"}

MAX_TOKENS = 8
MAX_LABELS = 48
MAX_DOMAINS = 400


@cache
def catalog():
    payload = json.loads(_DATA.read_text(encoding="utf-8"))
    names = []
    index = {}
    for code in ("m", "f", "b"):
        for name in payload[code]:
            key = normalize_fa(name).replace(" ", "")
            if key in index:
                continue
            item = {"name": name, "key": key, "gender": code}
            names.append(item)
            index[key] = item
    return {"names": names, "index": index, "source": payload["source"], "count": len(names)}


def _record(name, gender):
    key = normalize_fa(name).replace(" ", "")
    return {"name": name, "gender": gender, "latin": transliterate(name), "key": key}


def _matched_names(query, gender):
    data = catalog()
    allowed = {gender} if gender in {"m", "f", "b"} else set()
    needle = normalize_fa(query).replace(" ", "")
    if len(needle) > 40:
        raise ValidationError("invalid_input")
    names = data["names"]
    if allowed:
        names = [item for item in names if item["gender"] in allowed]
    if not needle:
        return sorted(names, key=lambda item: item["key"]), data
    starts, contains = [], []
    for item in names:
        if item["key"].startswith(needle):
            starts.append(item)
        elif needle in item["key"]:
            contains.append(item)
    starts.sort(key=lambda item: (len(item["key"]), item["key"]))
    contains.sort(key=lambda item: (len(item["key"]), item["key"]))
    return starts + contains, data


def search(query="", gender="", limit=48, page=1):
    try:
        limit = int(limit)
        page = int(page)
    except (TypeError, ValueError):
        raise ValidationError("invalid_input") from None
    if limit < 1 or limit > 100 or page < 1 or page > 100000:
        raise ValidationError("invalid_input")
    matched, data = _matched_names(query, gender)
    total = len(matched)
    pages = max(1, (total + limit - 1) // limit)
    page = min(page, pages)
    start = (page - 1) * limit
    chosen = matched[start : start + limit]
    return {
        "items": [_record(item["name"], item["gender"]) for item in chosen],
        "total": total,
        "page": page,
        "pages": pages,
        "page_size": limit,
        "source": data["source"],
        "count": data["count"],
    }


def classify(text):
    key = normalize_fa(text).replace(" ", "")
    if not key:
        return "keyword"
    if key in PLACES:
        return "place"
    if key in catalog()["index"]:
        return "name"
    return "keyword"


def inspect_word(text):
    if not isinstance(text, str) or len(text) > 40:
        raise ValidationError("invalid_input")
    persian = normalize_fa(text)
    key = persian.replace(" ", "")
    if not key:
        raise ValidationError("empty_input")
    known = catalog()["index"].get(key)
    return {
        "fa": known["name"] if known else persian,
        "latin": transliterate(persian),
        "role": classify(persian),
        "gender": known["gender"] if known else None,
    }


def _label(value):
    value = re.sub(r"[^a-z0-9-]", "", str(value).strip().lower())
    value = re.sub(r"-{2,}", "-", value).strip("-")
    if not value or not _LABEL.fullmatch(value):
        return ""
    return value


def _clean_tokens(tokens):
    if not isinstance(tokens, list):
        raise ValidationError("invalid_input")
    if not tokens:
        raise ValidationError("empty_input")
    if len(tokens) > MAX_TOKENS:
        raise ValidationError("too_many_inputs")
    cleaned = []
    for token in tokens:
        if not isinstance(token, dict):
            raise ValidationError("invalid_input")
        raw_persian = token.get("fa", "")
        if not isinstance(raw_persian, str) or len(raw_persian) > 40:
            raise ValidationError("invalid_input")
        persian = normalize_fa(raw_persian)
        supplied = token.get("latin", "")
        if supplied is None:
            supplied = ""
        if not isinstance(supplied, str) or len(supplied) > 80:
            raise ValidationError("invalid_input")
        if supplied.strip() and not _LABEL.fullmatch(supplied.strip().lower()):
            raise ValidationError("studio_latin_invalid")
        latin = _label(supplied) or _label(transliterate(persian))
        role = token.get("role")
        if role not in _ROLES:
            role = classify(persian)
        if not latin and not persian:
            continue
        if not latin:
            raise ValidationError("invalid_input")
        cleaned.append({"fa": persian, "latin": latin, "role": role})
    if not cleaned:
        raise ValidationError("empty_input")
    return cleaned


def _tld(value):
    value = str(value).strip().lower().lstrip(".")
    if value.startswith("xn--"):
        return ""
    return value if _TLD.fullmatch(value) else ""


def _add(sequences, tokens):
    tokens = [token for token in tokens if token]
    if tokens and tokens not in sequences:
        sequences.append(tokens)


def compose(tokens, tlds, styles=None):
    cleaned = _clean_tokens(tokens)
    if styles is None:
        styles = ["joined", "hyphen"]
    if not isinstance(styles, list) or any(style not in {"joined", "hyphen"} for style in styles):
        raise ValidationError("invalid_options")
    use_joined = "joined" in styles
    use_hyphen = "hyphen" in styles
    if not use_joined and not use_hyphen:
        raise ValidationError("invalid_options")
    if not isinstance(tlds, list) or len(tlds) > 12:
        raise ValidationError("invalid_input")
    suffixes = []
    for tld in tlds:
        if not isinstance(tld, str):
            raise ValidationError("invalid_input")
        cleaned_tld = _tld(tld)
        if not cleaned_tld:
            raise ValidationError("studio_invalid_tld")
        if cleaned_tld not in suffixes:
            suffixes.append(cleaned_tld)
    if not suffixes:
        raise ValidationError("invalid_input")

    names = [token for token in cleaned if token["role"] == "name"]
    keywords = [token for token in cleaned if token["role"] in {"keyword", "custom"}]
    places = [token for token in cleaned if token["role"] == "place"]
    sequences = []
    _add(sequences, cleaned)
    if 2 <= len(cleaned) <= 4:
        _add(sequences, list(reversed(cleaned)))
    for name in names:
        for keyword in keywords:
            _add(sequences, [name, keyword])
            _add(sequences, [keyword, name])
            for place in places:
                _add(sequences, [name, keyword, place])
                _add(sequences, [keyword, name, place])
                _add(sequences, [name, place])
        if not keywords:
            for place in places:
                _add(sequences, [name, place])
                _add(sequences, [place, name])
    if not names:
        for keyword in keywords:
            for place in places:
                _add(sequences, [keyword, place])
                _add(sequences, [place, keyword])
    # Two business words should offer useful brands even without a given name or place.
    for first in keywords:
        for second in keywords:
            if first is not second:
                _add(sequences, [first, second])
    for token in cleaned:
        _add(sequences, [token])

    labels = []
    seen = set()
    for sequence in sequences:
        parts = [token["latin"] for token in sequence]
        persian = " ".join(token["fa"] for token in sequence if token["fa"])
        variants = []
        if use_joined:
            variants.append("".join(parts))
        if use_hyphen and len(parts) > 1:
            variants.append("-".join(parts))
        for label in variants:
            if not label or label in seen or len(label) > 63 or not _LABEL.fullmatch(label):
                continue
            seen.add(label)
            kind = "full" if len(sequence) == len(cleaned) else "brand" if len(sequence) > 1 else "short"
            labels.append({"label": label, "persian": persian, "parts": parts, "kind": kind})
            if len(labels) >= MAX_LABELS:
                break
        if len(labels) >= MAX_LABELS:
            break

    domains = []
    for item in labels:
        for suffix in suffixes:
            domains.append(
                {
                    "domain": f"{item['label']}.{suffix}",
                    "label": item["label"],
                    "tld": suffix,
                    "persian": item["persian"],
                    "kind": item["kind"],
                }
            )
            if len(domains) >= MAX_DOMAINS:
                break
        if len(domains) >= MAX_DOMAINS:
            break
    if not domains:
        raise ValidationError("invalid_domain")
    return {"tokens": cleaned, "labels": labels, "domains": domains}
