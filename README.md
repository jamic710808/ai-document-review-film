# AI 文檔審核系統 · 動態介紹片

`index.html` 是以 `seek(t)` 純函數驅動的時間軸；`render.mjs` 逐格截圖並交給 ffmpeg；`mix.py` 做旁白＋配樂＋音效混音。
成片與播放頁在 `docs/`（GitHub Pages / Vercel 皆以此資料夾為網站根目錄）。

重新渲染需要自行補回未納入版本控制的素材：`assets/02_model_settings.png`（系統截圖）、`assets/music/ref-music.wav`（配樂來源）。
旁白由 `narration.json` 經 Gemini TTS（Kore）生成。專案展示片，畫面為實際系統截圖，示範文件為公開基金年報。
