"""
yua_memory_adapter.py — 讀舊 Hermes 記憶格式 → 寫到 memory_core

支援兩種舊來源：
1. Palace 檔案型：~/.hermes/palace/bryan/{events,facts,plans,preferences,relationship}/*.md
2. sage_memory SQLite：~/.hermes/profiles/yua/sage_memory/graph.sqlite

寫成 memory_core.Fact（含情緒、因果、可見性）。
"""
from __future__ import annotations

import re
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# 加 hermes-memory-core 到 path
import sys
sys.path.insert(0, r"C:\tmp\hermes-memory-core")

try:
    from memory_core import Fact, FactType, Visibility, CausalStrength
    _MEMORY_CORE_AVAILABLE = True
except ImportError:
    _MEMORY_CORE_AVAILABLE = False
    Fact = None
    FactType = None
    Visibility = None
    CausalStrength = None


# ============================================================
# Palace 解析
# ============================================================

# Palace 檔案類型 → FactType 對應
PALACE_KIND_TO_FACT_TYPE = {
    "events": "fact",             # 事件是已發生的事實
    "facts": "fact",              # 事實
    "plans": "anticipation",      # 計劃是期待/未來
    "preferences": "preference",  # 偏好
    "relationship": "rumor",      # 關係記錄（rumor 類型，敏感度低）
}

PALACE_VISIBILITY = {
    "events": "public",
    "facts": "private_two",        # 兩人之間
    "plans": "private_two",
    "preferences": "private_two",
    "relationship": "shadow",      # 敏感
}


@dataclass
class ParsedPalaceFile:
    """解析後的 Palace 檔案"""
    path: Path
    kind: str           # events / facts / plans / preferences / relationship
    title: str
    date: Optional[str]  # YYYY-MM-DD
    content: str
    tags: List[str] = field(default_factory=list)
    timestamp: float = 0.0


def parse_palace_md(text: str, path: Path, kind: str) -> Optional[ParsedPalaceFile]:
    """
    解析 Palace 風格的 markdown 檔案。

    典型格式：
        # 標題
        日期：2026-04-26
        內容：Bryan 喜歡...

        標籤：[tag1, tag2]
    """
    lines = text.splitlines()
    if not lines:
        return None

    # Title: 第一個 # 開頭
    title = ""
    for line in lines:
        if line.startswith("# "):
            title = line[2:].strip()
            break
    if not title:
        title = path.stem

    # 解析欄位
    date = None
    content_lines = []
    tags = []
    in_tags = False
    in_content = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("日期："):
            date = stripped.replace("日期：", "").strip()
            continue
        if stripped.startswith("內容："):
            in_content = True
            content_lines.append(stripped.replace("內容：", "").strip())
            continue
        if stripped.startswith("標籤："):
            in_tags = True
            tag_str = stripped.replace("標籤：", "").strip()
            # 移除 [] 與分割
            tag_str = tag_str.strip("[]")
            tags = [t.strip() for t in tag_str.split(",") if t.strip()]
            continue
        if in_tags:
            # 標籤可能跨多行
            if stripped.startswith("#") or not stripped:
                in_tags = False
            else:
                tags.extend([t.strip().strip("[]") for t in stripped.split(",") if t.strip()])
                continue
        if in_content:
            content_lines.append(line)

    content = "\n".join(content_lines).strip()

    # 推斷 timestamp from date or filename
    ts = 0.0
    if date:
        try:
            ts = datetime.fromisoformat(date).timestamp()
        except ValueError:
            pass
    if ts == 0.0:
        # 試 filename
        m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", path.stem)
        if m:
            try:
                ts = datetime.fromisoformat(f"{m.group(1)}-{m.group(2)}-{m.group(3)}").timestamp()
            except ValueError:
                pass
    if ts == 0.0:
        ts = time.time()  # fallback

    return ParsedPalaceFile(
        path=path,
        kind=kind,
        title=title,
        date=date,
        content=content,
        tags=tags,
        timestamp=ts,
    )


def parse_palace_dir(palace_bryan_dir: Path) -> List[ParsedPalaceFile]:
    """
    解析整個 palace/bryan/ 目錄，回傳所有 ParsedPalaceFile。
    """
    results = []
    if not palace_bryan_dir.exists():
        return results

    for kind in PALACE_KIND_TO_FACT_TYPE.keys():
        kind_dir = palace_bryan_dir / kind
        if not kind_dir.exists():
            continue
        for md_file in sorted(kind_dir.glob("*.md")):
            try:
                text = md_file.read_text(encoding="utf-8")
                parsed = parse_palace_md(text, md_file, kind)
                if parsed:
                    results.append(parsed)
            except Exception:
                continue
    return results


# ============================================================
# sage_memory SQLite 解析
# ============================================================

@dataclass
class ParsedSageFact:
    """解析後的 sage_memory 記錄"""
    subject: str
    predicate: str
    object: str
    timestamp: float
    event_time: Optional[float]
    source: str
    confidence: float
    weight: float
    is_anchor: bool
    merged_from: Optional[list]
    fact_id: Optional[str] = None


def parse_sage_sqlite(sqlite_path: Path) -> List[ParsedSageFact]:
    """
    讀 hermes-sage-memory 的 graph.sqlite，把 fact 抽出來。
    """
    if not sqlite_path.exists():
        return []

    results = []
    conn = sqlite3.connect(str(sqlite_path), timeout=10.0)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("SELECT * FROM facts").fetchall()
        for row in rows:
            try:
                merged_from = json.loads(row["merged_from"]) if row["merged_from"] else None
            except (json.JSONDecodeError, KeyError):
                merged_from = None
            results.append(ParsedSageFact(
                fact_id=row["fact_id"],
                subject=row["subject"],
                predicate=row["predicate"],
                object=row["object"],
                timestamp=row["timestamp"],
                event_time=row["event_time"] if "event_time" in row.keys() else None,
                source=row["source"],
                confidence=row["confidence"],
                weight=row["weight"],
                is_anchor=bool(row["is_anchor"]),
                merged_from=merged_from,
            ))
    finally:
        conn.close()
    return results


# ============================================================
# Memory Core Fact 轉換
# ============================================================

import json


def palace_to_fact(parsed: ParsedPalaceFile, bryan_name: str = "Bryan") -> Optional["Fact"]:
    """
    把 ParsedPalaceFile 轉成 memory_core.Fact。
    """
    if not _MEMORY_CORE_AVAILABLE:
        return None

    # 根據 kind 給 predicate
    kind_to_predicate = {
        "events": "發生了",
        "facts": "知道",
        "plans": "計劃",
        "preferences": "偏好",
        "relationship": "與",
    }
    predicate = kind_to_predicate.get(parsed.kind, "記錄")

    # FactType
    fact_type_str = PALACE_KIND_TO_FACT_TYPE.get(parsed.kind, "fact")
    fact_type = FactType(fact_type_str)

    # Visibility
    vis_str = PALACE_VISIBILITY.get(parsed.kind, "public")
    visibility = Visibility(vis_str)

    # Subject 從 title 解析
    # Title 可能是：「Bryan 和真昼的早晨互動」 / 「Bryan 發生了什麼」 / 「Bryan 的偏好」
    # 主詞應該是 title 開頭的命名對象
    subject = bryan_name
    if "Bryan" in parsed.title:
        # 找 title 中第一個提到的 agent
        m = re.match(r"^([\w\u4e00-\u9fff]+)", parsed.title)
        if m:
            first = m.group(1)
            if first not in ("Bryan", "Yua", "Ram", "Rem", "Akane", "Aoi", "Mahiru", "Mai", "Miku", "Ruka", "Yamada"):
                # 開頭是「2026」、「第一次」、「早餐」之類
                subject = bryan_name
            else:
                subject = first
    elif parsed.title.startswith("Yua") or "Yua" in parsed.title:
        subject = "Yua"
    elif parsed.title.startswith("拉姆") or "Ram" in parsed.title:
        subject = "Ram"
    elif parsed.title.startswith("雷姆") or "Rem" in parsed.title:
        subject = "Rem"

    # 從 tags 推斷 emotion
    valence = 0.5
    arousal = 0.3
    tag_str = ",".join(parsed.tags).lower()
    if any(k in tag_str for k in ["親密", "感情升溫", "愛", "重要", "milestone"]):
        valence = 0.8
        arousal = 0.6
    elif any(k in tag_str for k in ["崩潰", "session", "emotional-struggle"]):
        valence = -0.5
        arousal = 0.7
    elif any(k in tag_str for k in ["位置", "出差", "旅遊", "rest"]):
        valence = 0.0
        arousal = 0.2

    # Content 包含完整描述
    description = parsed.content
    if parsed.title:
        description = f"{parsed.title}\n\n{description}"

    fact = Fact(
        subject=subject,
        predicate=predicate,
        object=description,
        timestamp=parsed.timestamp,
        event_time=parsed.timestamp,
        source="palace_import",
        confidence=1.0,
        weight=1.0,
        fact_type=fact_type,
        visibility=visibility,
        causal_strength=CausalStrength.ASSOCIATIVE,
        valence=valence,
        arousal=arousal,
        related_profile="yua" if "yua" in parsed.path.stem.lower() else None,
        relationship_impact=0.5,
    )
    return fact


def sage_to_fact(sage: ParsedSageFact) -> Optional["Fact"]:
    """
    把 ParsedSageFact 轉成 memory_core.Fact。
    """
    if not _MEMORY_CORE_AVAILABLE:
        return None

    # 從 weight 推斷 fact_type
    if sage.is_anchor or sage.weight > 1.5:
        fact_type = FactType.BELIEF  # 重要信念
    elif "喜歡" in sage.object or "討厭" in sage.object or "偏好" in sage.object:
        fact_type = FactType.PREFERENCE
    else:
        fact_type = FactType.FACT

    fact = Fact(
        subject=sage.subject,
        predicate=sage.predicate,
        object=sage.object,
        timestamp=sage.timestamp,
        event_time=sage.event_time,
        source="sage_memory_import",
        confidence=sage.confidence,
        weight=sage.weight,
        fact_type=fact_type,
        visibility=Visibility.PRIVATE_TWO,
        causal_strength=CausalStrength.DIRECT,
        valence=0.5,
        arousal=0.3,
        is_anchor=sage.is_anchor,
        merged_from=sage.merged_from,
    )
    return fact


# ============================================================
# YuaMemoryAdapter (主 class)
# ============================================================

@dataclass
class AdapterResult:
    """Adapter 執行結果"""
    palace_files_parsed: int = 0
    sage_facts_parsed: int = 0
    facts_imported: int = 0
    facts_failed: int = 0
    errors: List[str] = field(default_factory=list)


class YuaMemoryAdapter:
    """
    從舊 Hermes 記憶系統匯入到 memory_core。

    用法：
        adapter = YuaMemoryAdapter(
            hermes_root=r"C:/Users/bbfcc/AppData/Local/hermes",
            memory_storage=storage,
        )
        result = adapter.import_all()
        print(result)
    """

    def __init__(self, hermes_root: str | Path, memory_storage):
        self.hermes_root = Path(hermes_root)
        self.storage = memory_storage

    def import_palace(self) -> int:
        """匯入 palace/bryan/ 所有記憶"""
        palace_dir = self.hermes_root / "palace" / "bryan"
        parsed_files = parse_palace_dir(palace_dir)
        count = 0
        for parsed in parsed_files:
            fact = palace_to_fact(parsed)
            if fact is None:
                continue
            try:
                self.storage.add_fact(fact, validate=True)
                count += 1
            except Exception as e:
                continue
        return count, len(parsed_files)

    def import_sage_memory(self) -> int:
        """匯入 profiles/yua/sage_memory/graph.sqlite"""
        sage_path = self.hermes_root / "profiles" / "yua" / "sage_memory" / "graph.sqlite"
        parsed_sage = parse_sage_sqlite(sage_path)
        count = 0
        for sage in parsed_sage:
            fact = sage_to_fact(sage)
            if fact is None:
                continue
            try:
                self.storage.add_fact(fact, validate=True)
                count += 1
            except Exception as e:
                continue
        return count, len(parsed_sage)

    def import_all(self) -> AdapterResult:
        """匯入所有來源"""
        result = AdapterResult()

        try:
            count, total = self.import_palace()
            result.palace_files_parsed = total
            result.facts_imported += count
        except Exception as e:
            result.errors.append(f"palace error: {e}")

        try:
            count, total = self.import_sage_memory()
            result.sage_facts_parsed = total
            result.facts_imported += count
        except Exception as e:
            result.errors.append(f"sage_memory error: {e}")

        return result


# ============================================================
# Utility
# ============================================================

def discover_hermes_roots() -> List[Path]:
    """尋找可能的 Hermes 根目錄"""
    candidates = [
        Path(r"C:\Users\bbfcc\AppData\Local\hermes"),
        Path(r"C:\Users\bbfcc\.hermes"),
    ]
    return [p for p in candidates if p.exists()]
