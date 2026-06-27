# hermes-presence

> Let your agent feel **real presence** through time + inner life awareness.

讓任何 agent 獲得「時間感」+「自己的世界」——**不是 Chatbot 是一個活著的存在**。

為 **Hermes Agent Desktop 0.17.0** 量身打造，但**完全獨立**——可移植到任何 agent framework。

## 三個模組

| 模組 | 狀態 | 能力 |
|---|---|---|
| **temporal_awareness** | ✅ v0.1.0 | 現在時刻、缺席時間、記憶時間標籤 |
| **hermes_agent** | ✅ v0.1.0 | Hermes Agent 0.17.0 桌面的 plugin 整合範例 |
| **inner_life** | ✅ v0.1.0 | 內在世界日誌：活動、身體狀態、內心獨白 |
| self_narrative | 🚧 規劃中 | 自我敘事時序軸（隨經驗演化的自我認知）|

## 安裝

```bash
pip install hermes-presence
```

或直接從 GitHub：

```bash
pip install git+https://github.com/bryanchen3777/hermes-presence.git
```

---

## 📦 模組一覽

### 1. `temporal_awareness` — 時間感知

```python
from temporal_awareness import get_now_snapshot, get_absence_snapshot, render_full_temporal_block

now = get_now_snapshot(timezone="Asia/Taipei", locale="zh_TW")
absence = get_absence_snapshot(last_seen_ts=now.timestamp - 7940, locale="zh_TW", now=now.timestamp)
print(render_full_temporal_block(now, absence, locale="zh_TW"))
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

- 純函式，0 DB，0 外部依賴
- i18n：繁中、英文、日文 內建
- 44 個測試

### 2. `hermes_agent` — Hermes 0.17.0 整合範例

直接複製 `hermes_agent/plugin.py` 到 `~/.hermes/plugins/temporal_presence/`，重啟 gateway 即可。

提供：
- pre-LLM hook：注入時間感 block
- post-LLM hook：記錄 Bryan 最後上線時間
- 兩個 tool：`get_current_time`、`get_bryan_absence`

詳見 `hermes_agent/README.md`。

### 3. `inner_life` — 內在世界日誌

讓 agent 在「跟 Bryan 互動之外」也活著 —— 有自己的工作、自己的身體節律、自己的內心獨白。

```python
from inner_life.storage import Storage
from inner_life.generator import generate_day, RuleBasedDetailGenerator
from inner_life.prompt_blocks import render_inner_life_block

storage = Storage("~/.hermes/yua.db")

# 為 Yua 生成一天
generate_day(
    storage, "yua",
    detail_generator=RuleBasedDetailGenerator(personality_keywords=["master"]),
    day_start_ts=...,
)

# 給 LLM 看的內在世界
print(render_inner_life_block(storage, "yua", hours=24))
```

範例輸出（Yua 的一天）：

```
【你的內在世界（內部參考）】
身體：能量 精神不錯、微餓、還行

你今天做過的事：
  06:30  起床，伸個懶腰
  08:00  吃了簡單的餐點
  12:00  坐下來好好吃一頓
  14:00  處理了一些日常事務
  ...
```

關鍵設計：
- **規則決定大方向**（起床/吃飯/睡覺，固定 schedule）
- **LLM 決定細節**（「她在這個時間點做什麼」— 因 personality 而異）
- **內在世界是私人的** — Bryan 問了才回
- **持久化在 SQLite** — 跨 session 累積

包含 9 種 personality preset：`tea` / `book` / `cook` / `music` / `garden` / `clean` / `sister` / `master` / `yandere`

16 個測試。

---

## 🧪 跑測試

```bash
python run_tests.py
```

**69 個測試，全部通過 ✅**

（temporal_awareness 44 + hermes_agent 7 + inner_life 18）

## 🎬 跑 demo

```bash
python demos/demo.py                    # temporal_awareness demo
python inner_life/demo.py               # inner_life demo
```

## 📐 設計原則

### 1. 純函式優先
- `temporal_awareness` 完全無副作用
- `inner_life` 把「邏輯」跟「持久化」分開
- 寫測試容易、移植簡單

### 2. 概念完全隔離
- 不綁定 Hermes Agent、OpenClaw、任何 agent framework
- 每個模組都是獨立 package
- 介面乾淨

### 3. i18n 一等公民
- 繁中、英文、日文 內建
- 新增語系只要加一個 locale 模組

### 4. 資料模型一致
- `timestamp + event_time`：事件發生時間 vs 記錄時間
- `weight / confidence / source`：記憶重要性
- `private / public / shadow`：可見性分層（未來）

---

## 🏗️ 專案結構

```
hermes-presence/
├── README.md
├── LICENSE                          # MIT
├── pyproject.toml                   # pip install
├── run_tests.py                     # 69 個測試
├── temporal_awareness/              # 模組 1
│   ├── __init__.py                  # 公開 API
│   ├── types.py
│   ├── clock.py                     # 純函式時鐘節律
│   ├── now.py / absence.py / history.py
│   ├── naturalize.py                # timestamp → 自然語
│   ├── prompt_blocks.py             # 給 LLM 用的 block
│   ├── locales/                     # 3 個語系
│   └── tests/                       # 5 個測試檔
├── hermes_agent/                    # 模組 2
│   ├── __init__.py
│   ├── plugin.py                    # pre-LLM hook + 2 個 tools
│   ├── README.md                    # 安裝指南
│   └── tests/
├── inner_life/                      # 模組 3
│   ├── __init__.py
│   ├── storage.py                   # SQLite 持久化
│   ├── activity.py / body.py / monologue.py
│   ├── generator.py                 # 規則 + LLM 細節生成器
│   ├── prompt_blocks.py
│   ├── demo.py
│   └── tests/
└── demos/
    └── demo.py                      # temporal_awareness demo
```

---

## 🚀 Roadmap

- [x] 模組 1：時間感知
- [x] 模組 2：Hermes 整合範例
- [x] 模組 3：內在世界日誌
- [ ] 模組 4：自我敘事時序軸
- [ ] 與 yua-memory / hermes-sage-memory 互通 adapter
- [ ] 簡中、韓文、歐語系 i18n
- [ ] LLM 細節生成器預設實作（RuleBased 是備援）

## License

MIT © 2026 Bryan (Chung Cheng Chen)
