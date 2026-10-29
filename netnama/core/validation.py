import ipaddress
import re
from dataclasses import asdict, dataclass

import idna


class ValidationError(ValueError):
    pass


@dataclass
class Domain:
    input: str
    unicode: str
    ascii: str
    registrable: str

    def dict(self):
        return asdict(self)


def hostname(value):
    value = str(value).strip()
    if not value or any(c in value for c in "/:@\\?#") or any(ord(c) < 33 for c in value):
        raise ValidationError("invalid_target")
    try:
        return str(ipaddress.ip_address(value))
    except ValueError:
        pass
    try:
        result = idna.encode(value.removesuffix("."), uts46=True, std3_rules=True).decode().lower()
    except idna.IDNAError as exc:
        raise ValidationError("invalid_domain") from exc
    if len(result) > 253 or result.startswith("-"):
        raise ValidationError("invalid_domain")
    return result


def domain(value, resources):
    ascii_name = hostname(value)
    try:
        ipaddress.ip_address(ascii_name)
    except ValueError:
        pass
    else:
        raise ValidationError("invalid_domain")
    if "." not in ascii_name or ascii_name.rsplit(".", 1)[1].upper() not in resources.tlds:
        raise ValidationError("unknown_tld")
    suffix = resources.psl.get_tld(ascii_name, strict=True)
    registrable = resources.psl.get_sld(ascii_name, strict=True)
    if not registrable or suffix == ascii_name:
        raise ValidationError("invalid_domain")
    return Domain(str(value).strip(), idna.decode(ascii_name), ascii_name, registrable)


def dns_name(value):
    value = str(value).strip()
    trailing = value.endswith(".")
    labels = value.rstrip(".").split(".")
    encoded = []
    for label in labels:
        if label.startswith("_"):
            if not re.fullmatch(r"_[a-zA-Z0-9-]{1,62}", label):
                raise ValidationError("invalid_domain")
            encoded.append(label.lower())
        else:
            encoded.append(hostname(label))
    result = ".".join(encoded) + ("." if trailing else "")
    if len(result) > 254:
        raise ValidationError("invalid_domain")
    return result


def parse_lines(text):
    if len(text.encode("utf-8")) > 1024 * 1024:
        raise ValidationError("input_too_large")
    lines = []
    for number, line in enumerate(text.removeprefix("\ufeff").splitlines(), 1):
        value = line.strip()
        if value and not value.startswith("#"):
            lines.append({"line": number, "input": value})
    if len(lines) > 5000:
        raise ValidationError("too_many_inputs")
    return lines


def prepare_inputs(text, resources):
    lines = parse_lines(text)
    targets = {}
    for line in lines:
        try:
            item = domain(line["input"], resources).dict()
            if item["ascii"] != item["registrable"]:
                item.update(status="invalid", reason_code="subdomain", suggestion=item["registrable"])
        except ValidationError as exc:
            item = {"input": line["input"], "status": "invalid", "reason_code": str(exc)}
        key = item.get("ascii", item["input"].lower())
        targets.setdefault(key, item)
        line["target"] = key
    if not targets:
        raise ValidationError("empty_input")
    if len(targets) > 1000:
        raise ValidationError("too_many_inputs")
    return list(targets.values()), lines
