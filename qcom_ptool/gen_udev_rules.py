# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause

"""Generate udev rules for Qualcomm raw partitions."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

DATA_DIR = Path(__file__).with_name("data")
POLICY_FILE = DATA_DIR / "approved-raw-partition-patterns.list"
TEMPLATE_FILE = DATA_DIR / "55-qcom-raw-partitions-noblkid.rules.in"
RULES_PLACEHOLDER = "@QCOM_RAW_PARTITION_RULES@"
PATTERN_RE = re.compile(r"[A-Za-z0-9_.+!*?\[\]-]+")


def load_patterns() -> list[str]:
    """Load raw partition name patterns."""
    patterns: list[str] = []
    seen: set[str] = set()
    for line_number, line in enumerate(
        POLICY_FILE.read_text(encoding="utf-8").splitlines(), start=1
    ):
        pattern = line.partition("#")[0].strip()
        if not pattern:
            continue
        if PATTERN_RE.fullmatch(pattern) is None:
            raise ValueError(f"{POLICY_FILE}:{line_number}: invalid pattern: {pattern}")
        if pattern in seen:
            raise ValueError(f"{POLICY_FILE}:{line_number}: duplicate pattern: {pattern}")
        patterns.append(pattern)
        seen.add(pattern)

    if not patterns:
        raise ValueError(f"approved pattern list is empty: {POLICY_FILE}")
    return patterns


def generate_rules() -> str:
    """Render the udev rules template."""
    patterns = load_patterns()
    rules = "\n".join(
        f'ENV{{PARTNAME}}=="{pattern}", GOTO="qcom_raw_noblkid"'
        for pattern in patterns
    )
    template = TEMPLATE_FILE.read_text(encoding="utf-8")
    if template.count(RULES_PLACEHOLDER) != 1:
        raise ValueError("rules template must contain exactly one placeholder")
    return template.replace(RULES_PLACEHOLDER, rules)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", "--output", required=True, type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        content = generate_rules()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content, encoding="utf-8")
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    print(f"generated: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
