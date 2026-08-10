# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import annotations

from pathlib import Path

import pytest

from qcom_ptool import gen_udev_rules


def test_generate_rules_uses_generic_patterns() -> None:
    rules = gen_udev_rules.generate_rules()

    assert 'ENV{PARTNAME}=="xbl_[ab]"' in rules
    assert 'ENV{PARTNAME}=="ALIGN_TO_128K_*"' in rules
    assert "rootfs" not in rules


def test_generate_rules_supports_negated_character_class(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    policy = tmp_path / "patterns.list"
    policy.write_text("xbl_[!b]\n", encoding="utf-8")
    monkeypatch.setattr(gen_udev_rules, "POLICY_FILE", policy)
    rules = gen_udev_rules.generate_rules()

    assert 'ENV{PARTNAME}=="xbl_[!b]"' in rules


def test_generate_rules_preserves_persistent_links() -> None:
    rules = gen_udev_rules.generate_rules()

    assert 'ENV{PARTNAME}=="", GOTO="qcom_raw_links"' in rules
    assert 'ENV{UDEV_DISABLE_PERSISTENT_STORAGE_BLKID_FLAG}="1"' in rules
    assert "UDEV_DISABLE_PERSISTENT_STORAGE_RULES_FLAG" not in rules
    assert 'SYMLINK+="disk/by-partuuid/$env{PARTUUID}"' in rules
    assert 'SYMLINK+="disk/by-partlabel/$env{PARTNAME}"' in rules


def test_load_patterns_rejects_unsafe_pattern(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    policy = tmp_path / "patterns.list"
    policy.write_text('xbl_[ab]\nxbl_", RUN+="/bin/true\n', encoding="utf-8")
    monkeypatch.setattr(gen_udev_rules, "POLICY_FILE", policy)

    with pytest.raises(ValueError, match="invalid pattern") as error:
        gen_udev_rules.load_patterns()

    assert f"{policy}:2:" in str(error.value)


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("xbl_a\nxbl_a\n", "duplicate pattern"),
        ("# comments only\n", "approved pattern list is empty"),
    ],
)
def test_load_patterns_rejects_invalid_policy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    content: str,
    message: str,
) -> None:
    policy = tmp_path / "patterns.list"
    policy.write_text(content, encoding="utf-8")
    monkeypatch.setattr(gen_udev_rules, "POLICY_FILE", policy)

    with pytest.raises(ValueError, match=message):
        gen_udev_rules.load_patterns()


def test_main_writes_rules(tmp_path: Path) -> None:
    output = tmp_path / "rules.d" / "55-qcom.rules"

    assert gen_udev_rules.main(["-o", str(output)]) == 0
    assert 'ENV{PARTNAME}=="cdt"' in output.read_text(encoding="utf-8")


def test_main_rejects_layout_input(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as error:
        gen_udev_rules.main(
            ["-i", "platforms/example/partitions.conf", "-o", str(tmp_path / "rules")]
        )

    assert error.value.code == 2
