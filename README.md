# TOEFL / GRE 備考學習系統

Phase 1: **GRE 字彙 SRS**（間隔重複背單字，SM-2 演算法，手機優先）。
後續階段再加寫作/口說批改器、閱讀/聽力檢討器，以及上雲與 PWA。

本階段先在你自己的電腦上跑起來，幾天內就能開始每天背。手機同步留到上雲階段。

---

## 目錄結構

```
toefl-gre-app/
  backend/        FastAPI + SQLAlchemy + SM-2 + Claude API 代理(後續)
    app/          程式碼
    requirements.txt
  frontend/       React + Vite(手機優先 RWD)
  seed/
    starter_words.csv     內建 50 字，首次啟動自動匯入，立刻可用
    generate_vocab.py     用 Claude 產生 1000 高頻字並匯入 DB
  .env.example    環境變數範本(複製成 backend/.env 填真值)
  .gitignore      已排除 .env / *.db / data/ / node_modules
```

> 安全：`backend/.env`、`*.db`、`data/` 都在 `.gitignore`，**絕不會** commit 進 GitHub。
> Claude API 金鑰只放後端 `.env`，前端永遠拿不到。

---

## 一、後端(先跑這個)

需求：Python 3.10+。

```powershell
cd toefl-gre-app\backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# 設定環境變數
copy ..\.env.example .env
# 用編輯器打開 .env，至少改 APP_PASSWORD 和 JWT_SECRET

# 啟動(0.0.0.0 讓同網路的手機也連得到)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

啟動後：
- API 文件：http://localhost:8000/docs
- 首次啟動會自動建立資料庫、建立登入帳號、匯入 50 個內建單字。

> macOS / Linux 對應指令：`python3 -m venv .venv && source .venv/bin/activate`，
> 複製用 `cp ../.env.example .env`。

---

## 二、前端

需求：Node 18+。

```powershell
cd toefl-gre-app\frontend
npm install
npm run dev
```

打開 http://localhost:5173 ，用 `.env` 裡的帳號密碼登入即可開始複習。
(dev server 已把 `/api` 代理到後端 8000 埠，不需處理 CORS。)

---

## 三、產生完整 1000 高頻字(選用)

內建 50 字夠你先試流程；要正式衝刺就跑這個一次性腳本，用 Claude 補滿到 1000：

```powershell
cd toefl-gre-app
# backend\.env 需已填 ANTHROPIC_API_KEY
python seed\generate_vocab.py --target 1000 --batch 25
```

- 在你電腦本機跑，金鑰不外流。
- 可隨時 Ctrl-C 中斷再重跑，已存的字會保留(自動去重、續傳)。
- 每日新卡上限由 `.env` 的 `DAILY_NEW_CARDS` 控制(預設 20)，所以 1000 字不會一天全湧出來。

---

## 四、手機怎麼用

**同一個 Wi-Fi(最簡單)**
1. 後端用 `--host 0.0.0.0` 啟動(上面已是)。
2. 查電腦區網 IP(Windows：`ipconfig` 看 IPv4，類似 `192.168.x.x`)。
3. 手機瀏覽器開 `http://192.168.x.x:5173`。
   - 若連得到頁面但登入失敗，多半是前端打 API 的位址問題；正式階段改用下面的 Tunnel 最省事。

**從外面也要連 / 想要 HTTPS** → 之後的上雲階段用 **Cloudflare Tunnel**：
免費、不必買網域、不必開防火牆 port，直接給你一個 https 網址，手機在任何網路都能開。
這部分等核心功能確定好用再做。

---

## SM-2 規則(對照 spec 3.1)

四個自評：忘記 / 勉強 / 記得 / 秒答(again / hard / good / easy)。

- 答對：`repetitions+1`；rep=1→1 天，rep=2→6 天，rep≥3→前次間隔 × ease_factor。
  「勉強」會縮短間隔、「秒答」會拉長。
- 答錯(忘記)：`repetitions` 歸 0，間隔回 1 天。
- `ease_factor` 每次依評等微調，下限 1.3。
- 每天只抽出到期卡 + 上限張數的新卡。

實作在 `backend/app/srs.py`，已用單元情境驗證過。

---

## 路線圖(後續階段)

- 上雲(Oracle Cloud Always Free + Cloudflare Tunnel)、跨裝置同步
- PWA(加到主畫面、離線背已下載的卡)
- 工具二：寫作/口說批改器(Claude API 依官方 rubric 評分 + 高分改寫 + 弱點儀表板)
- 工具三：閱讀/聽力錯題檢討器 + 題型弱點統計
- 每日自動備份 SQLite
```
