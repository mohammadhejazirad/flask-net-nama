import json


def serialize(snapshot, fmt, catalog):
    if fmt in ("json", "json.txt"):
        return json.dumps(snapshot, ensure_ascii=False, indent=2)
    lines = [
        "NetNama | " + snapshot["tool"],
        catalog["execution_origin"],
        f"{catalog['status']}: {catalog.get(snapshot['status'], snapshot['status'])}",
        f"UTC: {snapshot['snapshot_at']}",
        json.dumps(snapshot["summary"], ensure_ascii=False),
        "",
    ]
    for result in snapshot["results"]:
        lines.append(f"{result.get('input', '')}: {catalog.get(result['status'], result['status'])}")
        lines.append(catalog.get(result.get("explanation_key", ""), catalog["reason_fallback"]))
        lines.append(json.dumps(result, ensure_ascii=False, indent=2))
    lines.append(
        json.dumps(
            {"inputs": snapshot["inputs"], "input_mapping": snapshot["input_mapping"]}, ensure_ascii=False
        )
    )
    return "\n".join(lines)
