# 動態海浪影片安裝（上線前）

本版已加入真正的影片背景播放支援，**但 ZIP 不含 Pexels 影片檔**，須自行下載後上傳，以避免誤用未確認的素材網址。

1. 首選素材：https://www.pexels.com/video/aerial-view-of-turquoise-ocean-waves-30886101/
   備選素材：https://www.pexels.com/video/aerial-view-of-pristine-turquoise-ocean-waves-33840289/
2. 依 Pexels 網站顯示的授權條款下載免費 MP4；優先選 HD/1080p，必要時壓縮至短片。
3. 重新命名為 `ocean-waves.mp4`，放在專案的 `assets/ocean-waves.mp4`。
4. 上傳到 GitHub 的 `love-casting` repo，與本專案原有檔案一併提交。
5. 首頁播放成功會呈現實拍海浪；影片不存在、播放遭封鎖或使用者偏好減少動態效果時，會自動退回 CSS 海浪，不會黑畫面。

Pexels 授權：https://www.pexels.com/license/（請核對選定影片頁面的實際授權與限制）

---

# 戀愛 Casting：創造出屬於你的劇本

一個獨立的非官方二創小說網站。首頁有**免授權費的原創 CSS 海浪動畫**，可直接透過 GitHub + Cloudflare Pages 發布。已公開文章由 Notion 同步，未公開草稿**不輸出正文**。

> 初版使用 CSS 海浪動畫，不包含第三方影片：不用購買影片授權、也沒有外部素材依賴。未來可另外挑選已確認授權的免費海浪影片替換。

## 建站前先檢查 Notion

沿用既有的「📖 章節資料庫」，不要另外建立重複的資料庫。每篇文章需：

- **所屬作品** → 關聯「戀愛 Casting」的「📚 我的作品」頁面；作品識別碼 `love_casting`。
- **文章名稱** → 原本文章名稱。
- **網站章節識別碼** → 唯一的小寫英文、數字、底線或連字號，例如 `please_dont_stop_the_music`。
- **章節順序** → 整數 1、2、3 …… （可留空，但建議設定）。
- **原始劇本名稱** → 供網站分類使用。
- **閱讀分級** → `一般` 或 `18+`。
- **發布狀態** → `已發布`（或 `已發佈`）。
- **網站公開** → 需要勾選才會輸出。

**只有同時符合「所屬作品=戀愛 Casting」＋「發布狀態=已發布」＋「網站公開=勾選」的文章才會被輸出到 `data/chapters.json`。** 對其他作品的文章毫無影響。

**最後一篇《接觸不良，請抱緊》**：固定識別碼 `contact_error_hug_to_recharge`。沒有發布前請保持「草稿」＋「網站公開未勾選」；網站會自動顯示不含內文的預告卡片與「敬請期待」頁面。完成後設為已發布並勾選網站公開，再執行同步，網站就自動將預告頁替換為正文。

## 建立 GitHub 專案

1. 前往 https://github.com/new 建立新的 **Public** repository，例如 `love-casting`。**不要使用** `first-note-of-love` 或 `turbulence` 既有儲存庫。
2. 解壓本網站 ZIP，將**解壓後資料夾裡的所有檔案與資料夾**上傳至新 repository 的根目錄，包括隱藏的 `.github/workflows/sync-notion.yml`。
3. 在新儲存庫 **Settings → Secrets and variables → Actions** 建立下列 3 個 repository secrets：
   - `NOTION_TOKEN`: 有權讀取資料庫的 Notion integration token
   - `NOTION_DATABASE_ID`: 既有「📖 章節資料庫」的 database ID（不要填文章頁面 ID）
   - `NOTION_WORK_PAGE_ID`: 「📚 我的作品」裡《戀愛 Casting》那一筆資料的 **Notion page ID**（**不是** `love_casting` 字串）。
4. Notion 中將「📖 章節資料庫」分享給用於同步的 Notion integration。若已使用與先前作品相同的 integration，通常不必再建立一個。
5. 開啟 `https://github.com/<你的GitHub名稱>/love-casting/actions/workflows/sync-notion.yml`，按 **Run workflow → main → Run workflow**。
6. 執行成功後，開 `data/chapters.json` 檢查 `chapters` 包含想公開的文章，且**絕對沒有**《接觸不良，請抱緊》的未完成內文。

## Cloudflare Pages 上線

1. Cloudflare dashboard → Workers & Pages → Create application → Pages → Connect to Git。
2. 選取**新建的** `love-casting` repository。
3. Framework preset 選 **None**；Build command **留空**；Build output directory 選 **`.`（repo 根目錄）**，Production branch `main`。
4. Deploy。成功後 Cloudflare 會提供 `*.pages.dev` 的網站網址。
5. 測試章節、手機版、18+ 年齡確認與最後一篇預告。

> Cloudflare Pages 只部署 repository 內已生成的 `data/chapters.json`，不需要將任何 Notion token 提交到 GitHub。GitHub Actions 每天台灣時間約 10:00 自動檢查，也可以手動執行。

## 本機測試

在 repo 根目錄執行：

```bash
python3 -m http.server 8000
```

用瀏覽器開 http://localhost:8000 。第一次同步前，目錄會顯示「目前公開 0 篇」，但最終篇預告可正常預覽。為了避免誤曝草稿，專案**不附任何虛構的已公開文章正文**。

## 維護備註

- 所有正文來自 `data/chapters.json`，由 `scripts/sync_notion.py` 產生。絕不可把 `NOTION_TOKEN` 或其他 secrets 放入前端檔案。
- 網站讀者自行勾選的 18+ 確認不等於身分年齡驗證；如需強制驗證，必須另建後端機制。
- Notion 內的圖片如果是 Notion 暫存連結，腳本同步時會下載成靜態圖片至 `assets/notion/`；外部 HTTPS 圖片維持原始 URL。
- 如果上傳檔案時漏掉 `.github` 隱藏資料夾，GitHub Actions 頁面就不會出現同步工作流程。
- GitHub Pages 也可部署，但本專案以既有 Cloudflare Pages 工作方式為主。
