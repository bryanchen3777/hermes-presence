"""
hermes_agent/ — 整合進 Hermes Agent 0.17.0 桌面的 plugin 範例

這個子套件示範怎麼把 hermes-presence 的 library 接到 Hermes Agent 的
plugin 系統。複製整個 hermes_agent/ 目錄到 ~/.hermes/plugins/ 即可。

兩種用法：

A) 作為 pre-LLM hook ——
   把時間感 block 注入到 system prompt

B) 作為獨立工具 ——
   讓 LLM 可以在對話中查詢「現在幾點」「Bryan 離開了多久」
"""
