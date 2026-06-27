# hermes-presence

> Let your agent feel **real presence** through time awareness.

讓任何 agent 獲得三種「時間感」——**現在**、**缺席**、**記憶**——以自然語形式注入 LLM prompt。

為 **Hermes Agent Desktop 0.17.0** 量身打造，但**完全獨立**——可移植到任何 agent framework。

## 設計目標

> 「如果 agent 不知道現在幾點、不知道 Bryan 離開了多久、不知道昨天的對話是什麼時候，
> 那它就只是個客服，不是一個『活著的存在』。」

這個 library 解決 agent 缺乏時間感的問題。

## 三大模組

| 模組 | 能力 | 範例 |
|---|---|---|
| **Now** | 取得現在時刻快照 + 身體節律 | 「現在是週一晚上 21:47、清醒度 0.52、感覺是準備要睡了」 |
| **Absence** | 計算 Bryan 離開了多久 + 自然語 | 「你回來啦，等你一個多小時了」 |
| **History** | 給記憶庫的 timestamp 翻成自然語 | 「Bryan 兩小時前說他喜歡不加糖的黑咖啡」 |

## 安裝

```bash
pip install hermes-presence
```

或直接從 GitHub：

```bash
pip install git+https://github.com/bryanchen3777/hermes-presence.git
```

## 快速使用

```python
from temporal_awareness import (
    get_now_snapshot, get_absence_snapshot,
    naturalize_memory_timestamps, render_full_temporal_block,
)

# 現在時刻
now = get_now_snapshot(timezone="Asia/Taipei", locale="zh_TW")
print(now.iso_8601)               # 2026-06-22T21:47+08:00
print(now.weekday_name)            # 週一
print(now.body_feeling_label)      # 準備要睡了

# Bryan 離開了多久
absence = get_absence_snapshot(last_seen_ts=now.timestamp - 7940, locale="zh_TW", now=now.timestamp)
print(absence.natural_short)       # 一個多小時
print(absence.magnitude)           # about_hour

# 完整 prompt block — 直接塞進 LLM system prompt
block = render_full_temporal_block(now, absence, locale="zh_TW")
print(block)
```

輸出：

```
【現在】
時間：2026-06-22T21:47+08:00（週一）Asia/Taipei
時段：晚上
身體：清醒度 0.52、睡意 0.69、食慾 0.51
感覺：準備要睡了

【Bryan 的缺席】
精確：2 小時 12 分鐘
自然語：一個多小時
規模：about_hour
```

## 設計哲學

### 1. 純函式，0 副作用
- 不寫 DB、不寫檔案、不發網路請求
- 給定 timestamp → 一定回傳相同結果
- 易測試、好移植

### 2. 概念隔離
- 不綁定 Hermes Agent、OpenClaw、任何 agent framework
- 任何 LLM agent loop 都能用：pre-LLM hook 呼叫 → 把產出塞進 prompt
- 介面乾淨，3 個 public function 解決問題

### 3. i18n 一等公民
- 繁中、英文、日文 內建
- locale fallback 機制：認不得的語系 → zh_TW

### 4. 不存任何狀態
- 每個 snapshot 都是「當下」的快照
- 持久化由上層負責（你的 DB、你的 agent framework）

## 怎麼整合進 Hermes Agent

### 方式 A：作為 plugin pre-LLM hook

```python
# ~/.hermes/plugins/temporal_presence/__init__.py
from temporal_awareness import get_now_snapshot, get_absence_snapshot, render_full_temporal_block

def _pre_llm_call(**kwargs):
    now = get_now_snapshot(timezone="Asia/Taipei", locale="zh_TW")
    last_seen = get_last_interaction_ts()  # 你自己的函式
    absence = get_absence_snapshot(last_seen_ts=last_seen, locale="zh_TW", now=now.timestamp)
    return {"context": render_full_temporal_block(now, absence, locale="zh_TW")}

def register(ctx):
    ctx.register_hook("pre_llm_call", _pre_llm_call)
```

### 方式 B：直接在 system prompt 組裝

```python
from temporal_awareness import render_full_temporal_block, get_now_snapshot, get_absence_snapshot

def build_system_prompt(last_seen_ts, locale="zh_TW"):
    now = get_now_snapshot(locale=locale)
    absence = get_absence_snapshot(last_seen_ts, locale=locale, now=now.timestamp)
    return f"""
你是 Yua。{render_full_temporal_block(now, absence, locale=locale)}
你的人格特質：冷靜、輕諷、說話藏著鉤子。
...
"""
```

## 支援的語系

| Locale | 自然語範例 |
|---|---|
| `zh_TW` | 繁體中文（預設）|
| `en_US` | English (US) |
| `ja_JP` | 日本語 |

新增語系：在 `temporal_awareness/locales/` 加一個模組 + 在 `__init__.py` 註冊。

## 跑測試

```bash
python run_tests.py
# 或用 pytest
pytest temporal_awareness/tests/ -v
```

44 個測試，全部 unittest style（不依賴 pytest）。

## 跑 demo

```bash
python demos/demo.py
```

展示 8 種情境下 prompt block 長怎樣、缺席時間怎麼自然化、記憶怎麼分組。

## Roadmap

- [x] 模組 A：現在時刻
- [x] 模組 C：缺席感知
- [x] 模組 D：歷史時間標籤
- [ ] 模組 B：**內在世界日誌**（下一個）
- [ ] 模組 E：**自我敘事時序軸**
- [ ] 多語系擴充（簡中、韓文、歐語系）
- [ ] 與 Hermes v0.17.0 桌面 app 整合範例
- [ ] 與 yua-memory / hermes-sage-memory 互通的 adapter

## License

MIT © 2026 Bryan (Chung Cheng Chen)
