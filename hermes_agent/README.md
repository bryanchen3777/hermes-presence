# hermes_agent — Hermes Agent 整合範例

把 `hermes-presence` 的 library 接到 **Hermes Agent Desktop 0.17.0** 的 plugin 系統。

## 安裝

```bash
# 1. 安裝 hermes-presence
pip install hermes-presence

# 2. 複製 plugin 範例
mkdir -p ~/.hermes/plugins/temporal_presence
cp hermes_agent/plugin.py ~/.hermes/plugins/temporal_presence/plugin.py

# 3. 重啟 gateway
hermes gateway restart
```

## 多 profile 安裝

每個 profile 都可以裝自己的時間感知 plugin：

```bash
# Yua (default)
cp hermes_agent/plugin.py ~/.hermes/plugins/temporal_presence/plugin.py

# Rem
mkdir -p ~/.hermes/profiles/rem/plugins/temporal_presence
cp hermes_agent/plugin.py ~/.hermes/profiles/rem/plugins/temporal_presence/plugin.py

# Ram
mkdir -p ~/.hermes/profiles/ram/plugins/temporal_presence
cp hermes_agent/plugin.py ~/.hermes/profiles/ram/plugins/temporal_presence/plugin.py
```

## 設定環境變數

```bash
# ~/.hermes/.env 或 shell rc
export HERMES_TIMEZONE="Asia/Taipei"      # 你的時區
export HERMES_LOCALE="zh_TW"              # zh_TW / en_US / ja_JP
export HERMES_LAST_SEEN_FILE="~/.hermes/last_seen.txt"  # 預設即可
```

## 會發生什麼事

1. **每次 LLM 呼叫前**：pre-LLM hook 把時間感 prompt block 注入 system prompt
2. **每次 LLM 呼叫後**：post-LLM hook 把現在時間記到 `last_seen.txt`
3. **LLM 想查時間**：可以呼叫 `get_current_time` / `get_bryan_absence` 工具

## pre-LLM hook 注入的範例

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

## 自訂 plugin 行為

### 改變時間感的「主詞」

預設是「Bryan」，如果你的 agent 對象是別人：

```python
# 在 plugin.py 修改
def _pre_llm_call(**kwargs):
    ...
    block = render_full_temporal_block(
        now=now,
        absence=absence,
        subject="用戶",  # ← 改這裡
    )
```

### 改變語系

```bash
export HERMES_LOCALE="ja_JP"
```

### 改變時區

```bash
export HERMES_TIMEZONE="America/Los_Angeles"
```

### 多人模式（多個用戶）

`LAST_SEEN_FILE` 是單一檔案。多用戶的話改成目錄 + 動態檔名：

```python
import os
def _last_seen_path(user_id: str) -> str:
    base = os.environ.get("HERMES_LAST_SEEN_DIR", "~/.hermes/last_seen")
    return os.path.join(os.path.expanduser(base), f"{user_id}.txt")
```

## 進階：注入到主動觸發

如果你想讓 agent 在主動觸發（例如 idle > 4hr）時也用時間感：

```python
# 在 hermes-social-core 裡
from temporal_awareness import get_now_snapshot, render_now_block

def render_proactive_context(profile_name: str) -> str:
    now = get_now_snapshot(locale="zh_TW")
    return render_now_block(now, locale="zh_TW")
```

## 故障排除

### Q：plugin 沒生效
A：確認 `~/.hermes/plugins/temporal_presence/plugin.py` 存在，內容完整。

### Q：時間不對
A：檢查 `HERMES_TIMEZONE` 是否設定正確（IANA 名稱，例如 `Asia/Taipei`）。

### Q：locale 顯示英文
A：檢查 `HERMES_LOCALE` 是否為 `zh_TW` / `en_US` / `ja_JP` 其中之一。

### Q：想停用
A：把 `~/.hermes/plugins/temporal_presence/` 整個資料夾刪除即可。
