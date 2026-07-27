from __future__ import annotations

import hashlib


def normalize_prose_result(value: str) -> str:
    text = (value or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip(" \t") for line in text.split("\n")]
    normalized_lines = [line if line.strip() else "" for line in lines]

    while normalized_lines and normalized_lines[0] == "":
        normalized_lines.pop(0)
    while normalized_lines and normalized_lines[-1] == "":
        normalized_lines.pop()

    collapsed: list[str] = []
    previous_blank = False
    for line in normalized_lines:
        if line == "":
            if previous_blank:
                continue
            previous_blank = True
            collapsed.append("")
            continue
        previous_blank = False
        collapsed.append(line)
    return "\n".join(collapsed)


def result_fingerprint(value: str) -> str:
    return hashlib.sha256((value or "").encode("utf-8")).hexdigest()
