# 上雲部署指南 — Oracle Cloud Always Free VM

目標:讓 App 跑在雲端,**電腦關機也能用**,手機在任何網路都連得到、有 HTTPS、固定網址。

整個 App 已經 Docker 化:前端打包 + 後端服務在同一個容器,SQLite 資料庫用 volume 保存。
你在 VM 上只要 `docker compose up -d --build` 一行就會自己建好。

> 先決:你會在「全部弄完、上傳 GitHub 之後」才做這步。下面的 `git clone` 假設你的 repo
> 已經推上 GitHub。若還沒上 GitHub,也可以用 `scp` 把整個資料夾複製到 VM(見最後一節)。

---

## 1. 開一台 Always Free VM

1. 登入 Oracle Cloud → Compute → Instances → Create Instance。
2. Image 選 **Ubuntu 22.04**。
3. Shape 選 Always Free 額度內的:
   - **VM.Standard.A1.Flex（Ampere ARM）** 最佳,免費可到 4 核 / 24GB,給 1 核 / 6GB 就綽綽有餘;
   - 或 **VM.Standard.E2.1.Micro（x86）**。
   - 兩種架構都沒問題,映像會在 VM 上自己依架構編譯。
4. 下載/保存 SSH 私鑰。
5. 建立後記下 VM 的 **Public IP**。

## 2. 連線並安裝 Docker

```bash
ssh -i 你的私鑰 ubuntu@你的VM_IP

# 安裝 Docker + compose plugin
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
# 重新登入讓群組生效
exit
ssh -i 你的私鑰 ubuntu@你的VM_IP
docker --version && docker compose version
```

## 3. 取得程式碼

```bash
# 上傳 GitHub 之後:
git clone https://github.com/你的帳號/toefl-gre-app.git
cd toefl-gre-app
```

## 4. 填入密鑰

```bash
cp .env.example backend/.env
nano backend/.env
```
至少填：
- `APP_PASSWORD`（你的登入密碼）
- `JWT_SECRET`（一長串隨機字串）
- `ANTHROPIC_API_KEY`（你的 Claude 金鑰，批改/補字要用）

`backend/.env` 已在 `.gitignore`,不會進版控。

## 5. 啟動

```bash
docker compose up -d --build
```
第一次會花幾分鐘建映像。完成後容器會常駐、開機自動重啟（`restart: unless-stopped`）。

健康檢查：`curl http://localhost:8000/api/health` 應回 `{"status":"ok"}`。

---

## 6. 對外連線：二選一

### 方式 A（推薦）Cloudflare Tunnel — 有 HTTPS、固定網址、不用動防火牆

好處:不必在 Oracle 開任何 port、不必設憑證,連線是「VM 主動往外」,最安全省事。
需要一個掛在 Cloudflare 上的網域（便宜網域即可,或把現有網域 NS 轉到 Cloudflare）。

1. Cloudflare 控制台 → **Zero Trust** → Networks → **Tunnels** → Create a tunnel（Cloudflared）。
2. 複製它給的 **Tunnel Token**，貼到 `backend/.env` 的 `TUNNEL_TOKEN=`。
3. 在該 tunnel 設一個 **Public Hostname**：
   - Subdomain/Domain 自己選（例如 `gre.你的網域.com`）
   - Service 填 **`http://app:8000`**（容器名 app）
4. 啟動含 tunnel 的服務：
   ```bash
   docker compose --profile tunnel up -d --build
   ```
5. 手機/電腦開 `https://gre.你的網域.com` 就能用,網址固定、可加到主畫面。

### 方式 B 直接開 8000 埠（無網域時的快速法,無 HTTPS）

要同時放行 **Oracle 雲端防火牆** 與 **VM 內 iptables**：

1. Oracle 控制台 → 該 VM 的 VCN → Security List → 加 Ingress：來源 `0.0.0.0/0`、TCP、Port `8000`。
2. VM 內：
   ```bash
   sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 8000 -j ACCEPT
   sudo netfilter-persistent save   # 若無此指令: sudo apt install iptables-persistent
   ```
3. 瀏覽器開 `http://你的VM_IP:8000`。

---

## 7. 每日備份

```bash
# 測試一次
./backup.sh
# 設每天 03:00 自動備份(保留最近 14 份到 ./backups)
crontab -e
# 加這行(路徑換成你的):
0 3 * * * /home/ubuntu/toefl-gre-app/backup.sh
```
（進階:可再把 `backups/` 同步到 Oracle Object Storage 免費額度。）

## 8. 之後要更新程式

```bash
cd toefl-gre-app
git pull
docker compose up -d --build           # 有用 tunnel 就加 --profile tunnel
```
資料庫在 `./data`,不受重建影響。

---

## 沒有 GitHub 時：用 scp 上傳

```bash
# 在你電腦(專案外層)執行,排除大資料夾
scp -i 你的私鑰 -r toefl-gre-app ubuntu@你的VM_IP:~/
# 上去後一樣 cp .env、docker compose up -d --build
```
（記得別把本機的 `backend/.venv`、`frontend/node_modules`、`data/` 一起傳。）
