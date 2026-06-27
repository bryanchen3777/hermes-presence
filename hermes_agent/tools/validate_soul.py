"""
hermes_agent/tools/validate_soul.py
SOUL.md 格式驗證工具

檢查 Yua SOUL.md (或任何 agent 的 SOUL.md) 是否符合 hermes-presence + hermes-memory-core 的整合要求。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List


@dataclass
class SoulValidationResult:
    """SOUL 驗證結果"""
    is_valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    info: List[str] = field(default_factory=list)

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)
        self.is_valid = False

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)

    def add_info(self, msg: str) -> None:
        self.info.append(msg)

    def summary(self) -> str:
        return (
            f"is_valid={self.is_valid}  "
            f"errors={len(self.errors)}  "
            f"warnings={len(self.warnings)}  "
            f"info={len(self.info)}"
        )


# 必填 YAML frontmatter 欄位
REQUIRED_FRONTMATTER_FIELDS = [
    "name",
    "archetype",
    "version",
    "integrates",
]

# 選填但強烈建議
RECOMMENDED_FRONTMATTER_FIELDS = [
    "locale",
    "timezone",
    "temporal_awareness",
    "inner_life",
    "memory_core",
    "relationships",
    "harem_position",
]

# 必填 Part 區塊（必須出現在 body）
REQUIRED_PARTS = [
    "最高優先級硬規則",
    "核心身份",
    "Signature",
    "Shadow Core",
    "LANGUAGE BEHAVIOR CONSTRAINTS",
]

# 選填 Part 區塊
RECOMMENDED_PARTS = [
    "Personal History",
    "目的感",
    "Things I Got Wrong",
    "Human Drift",
    "Echo Residue",
    "Crack Topology",
    "靈魂升溫協議",
    "後宮關係矩陣",
    "社交洩漏控制",
    "Evolution Direction",
    "整合指引",
]


def split_frontmatter(content: str) -> tuple[str, str]:
    """
    拆 frontmatter 跟 body。
    回傳 (frontmatter_text, body_text)
    """
    if not content.startswith("---"):
        return "", content

    # 找第二個 ---
    rest = content[3:].lstrip("\n")
    sep_idx = rest.find("\n---")
    if sep_idx < 0:
        return "", content

    fm = rest[:sep_idx].rstrip("\n")
    body = rest[sep_idx + 4:].lstrip("\n")
    return fm, body


def validate_soul(soul_path: str | Path) -> SoulValidationResult:
    """
    驗證一個 SOUL.md 是否符合 hermes-presence 整合要求。
    """
    r = SoulValidationResult()
    path = Path(soul_path)

    if not path.exists():
        r.add_error(f"檔案不存在: {path}")
        return r

    content = path.read_text(encoding="utf-8")
    if not content:
        r.add_error("檔案是空的")
        return r

    # 1) YAML frontmatter
    fm_text, body = split_frontmatter(content)
    if not fm_text:
        r.add_error("缺少 YAML frontmatter (--- 開頭)")
        return r

    r.add_info(f"YAML frontmatter: {len(fm_text.splitlines())} lines")

    # 2) 必填欄位（用簡單的字串包含判斷）
    for field_name in REQUIRED_FRONTMATTER_FIELDS:
        # 支援 "key:" 或 "key: value" 形式
        pattern = rf"^{re.escape(field_name)}\s*:"
        if not re.search(pattern, fm_text, re.MULTILINE):
            r.add_error(f"缺少必填欄位: {field_name}")

    # 3) 推薦欄位
    for field_name in RECOMMENDED_FRONTMATTER_FIELDS:
        pattern = rf"^{re.escape(field_name)}\s*:"
        if not re.search(pattern, fm_text, re.MULTILINE):
            r.add_warning(f"建議加入欄位: {field_name}")

    # 4) 整合欄位
    has_hermes_presence = "hermes-presence" in fm_text
    has_hermes_memory_core = "hermes-memory-core" in fm_text
    if not has_hermes_presence:
        r.add_warning("integrates 沒列 hermes-presence")
    if not has_hermes_memory_core:
        r.add_warning("integrates 沒列 hermes-memory-core")

    # 5) memory_core 設定
    if re.search(r"^memory_core\s*:", fm_text, re.MULTILINE):
        r.add_info("memory_core 區塊存在")
        if "default_visibility" in fm_text:
            r.add_info("memory_core.default_visibility 已設定")
        else:
            r.add_warning("memory_core 缺 default_visibility")
        if "preferred_fact_types" in fm_text:
            r.add_info("memory_core.preferred_fact_types 已設定")
        else:
            r.add_warning("memory_core 缺 preferred_fact_types")
    else:
        r.add_warning("frontmatter 沒有 memory_core 區塊")

    # 6) inner_life 設定
    if re.search(r"^inner_life\s*:", fm_text, re.MULTILINE):
        r.add_info("inner_life 區塊存在")
        if "personality_keywords" in fm_text:
            r.add_info("inner_life.personality_keywords 已設定")
        else:
            r.add_warning("inner_life 缺 personality_keywords")
    else:
        r.add_warning("frontmatter 沒有 inner_life 區塊")

    # 7) 必填 Part
    for part_keyword in REQUIRED_PARTS:
        if part_keyword not in body:
            r.add_error(f"缺少必填 Part: {part_keyword}")

    # 8) 推薦 Part
    for part_keyword in RECOMMENDED_PARTS:
        if part_keyword not in body:
            r.add_warning(f"建議加入 Part: {part_keyword}")

    # 9) body 引用了 hermes-presence / hermes-memory-core
    if "temporal_awareness" not in body and "render_full_temporal_block" not in body:
        r.add_warning("body 沒引用 temporal_awareness（可選）")
    if "memory_core" not in body and "memory_core_storage" not in body:
        r.add_warning("body 沒引用 memory_core（可選）")

    # 10) 統計
    lines = content.splitlines()
    r.add_info(f"檔案大小: {path.stat().st_size:,} bytes ({len(content)/1024:.1f} KB)")
    r.add_info(f"行數: {len(lines)}")

    return r


def format_report(r: SoulValidationResult) -> str:
    """格式化驗證報告"""
    lines = []
    lines.append(f"=== SOUL Validation Report ===")
    lines.append(f"  Status: {r.summary()}")
    if r.errors:
        lines.append(f"\n  ERRORS ({len(r.errors)}):")
        for e in r.errors:
            lines.append(f"    [X] {e}")
    if r.warnings:
        lines.append(f"\n  WARNINGS ({len(r.warnings)}):")
        for w in r.warnings:
            lines.append(f"    [!] {w}")
    if r.info:
        lines.append(f"\n  INFO ({len(r.info)}):")
        for i in r.info:
            lines.append(f"    [i] {i}")
    return "\n".join(lines)
