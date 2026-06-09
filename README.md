# Amazing-Scam-Pro 防詐騙模擬與 RAG 廣告分析系統

本專案整合了基於 RAG 的廣告生成、高擬真釣魚網頁模板以及 Flask 後端教育宣導伺服器。

---

## 🛠️ 第一部分：ChromaDB RAG 文案生成與分析 (`rag-context-generator`)

### 環境架設與執行步驟

1. 複製 `.env.example` 並重新命名為 `.env`，將裡面的 `[PROJ_ROOT]` 與相關路徑配置為您本機的絕對路徑。
2. 安裝依賴套件：
   ```bash
   pip install -r requirements.txt
   ```
3. 建立 ChromaDB 本地向量資料庫：
   * 執行指令：
     ```bash
     python chroma_initiator/index_to_chromadb.py
     ```
   * *備註：此步驟需要 `chroma_initiator/dataset` 資料夾，該資料夾並未包含在 GitHub 上，請向團隊成員索取。*
4. 生成廣告文案與分析詐騙手法：
   * 執行指令：
     ```bash
     python rag_context_gen.py --query "你的廣告主題"
     ```
5. **產出結果**：自動寫入本地 SQLite3 資料庫（`scam_database.db` 的 `scams` 資料表），內容包含：
   * `id`: 隨機產生的 15 位數廣告唯一識別碼。
   * `context`: 生成的高擬真廣告文案。
   * `scam_type`: 分析出的詐騙手法。

### 運作原理簡述
1. 使用 Ollama (基本分類) + Gemini (進階分類與修正) 產生 `ad_labels_metadata.json`。
2. `index_to_chromadb.py` 使用 `sentence-transformers` 將廣告文案與分析轉換為向量，並存入 ChromaDB 向量資料庫。
3. `rag_context_gen.py` 透過語意檢索 ChromaDB 尋找相似案例作為 RAG 上下文，接著呼叫 Ollama 模型生成新廣告文案，最後分析其詐騙手法並記錄至 SQLite3。
---

## 🎨 第二部分：文案轉網頁分析工具 (`textToHtml`)

此部分使用大語言模型，將第一部分生成的詐騙廣告文案，轉換並分析生成為模擬的釣魚網站 HTML 頁面結構。

### 環境架設與執行步驟
1. 確保已安裝並啟動 **Ollama** 本地服務。
2. 安裝 `ollama` 套件：
   ```bash
   pip install ollama
   ```
3. 執行生成腳本：
   ```bash
   python text_to_web.py
   ```
4. **產出結果**：
   * **自訂模型**：系統會自動下載 `qwen2.5` 並建立一個專門用於詐騙網站分析與生成的自訂 Ollama 模型 `scamer`。
   * **模擬網頁**：讀取資料庫中的詐騙案例文案進行分析與生成後，自動注入美化的現代 CSS 樣式，並輸出至 **`beautiful_output.html`**。

> [!IMPORTANT]
> 這裡產出的 `beautiful_output.html` 相當於第三部分網頁伺服器實際運作時所使用的 `mock_scam.html` 樣式範本。

### 運作原理簡述
1. **模型客製化**：呼叫 `ollama.create` 建立名為 `scamer` 的自訂模型，並設定特定的 System Prompt，引導 AI 分析文案攻擊手法、生成假登入頁面並在跳轉時攜帶 `ad_id`。
2. **資料提取**：從本地 SQLite3 資料庫（`scam_database.db`）中撈取前三筆詐騙資料（`id`, `context`, `scam_type`）進行批次處理。
3. **網頁提取與 CSS 注入**：
   * 使用正則表達式從模型回應中提取被 ````html ... ```` 包覆的代碼。
   * 自動向 HTML 程式碼中注入一組現代化的 CSS 樣式（包含色彩變數、按鈕 Hover 效果、卡片陰影等）。
   * 若模型輸出的為非完整 HTML 片段，系統會自動補齊 `<!DOCTYPE html>`、`<head>`、`<body>` 及響應式容器，最後存為實體檔案。

---

## 🌐 第三部分：Web 伺服器與教育宣導系統 (`web-server`)

此部分為 Flask 後端網頁伺服器，負責處理模擬詐騙頁面分流與反詐教育網站的邏輯。

### 執行步驟
1. 啟動 Flask 伺服器：
   ```bash
   python app.py
   ```
2. 在瀏覽器打開首頁即可進入模擬測試：
   ```text
   http://127.0.0.1:5000/
   ```
   *(會自動跳轉至 `/mock_scam`)*

### 📝 網頁跳轉與參數開發規範

為確保網頁能正確讀取到資料庫中對應的詐騙廣告與手法，**所有跳轉連結與表單提交必須強制攜帶 `id` 參數**：

1. **入口模擬頁面 (`mock_scam.html`)**：
   此頁面為誘發點，按鈕引導使用者跳轉至各平台的登入分流頁面，並攜帶對應的廣告 `id` 參數：
   * Facebook 登入頁：`http://127.0.0.1:5000/fb?id={ad_id}`
   * LINE 登入頁：`http://127.0.0.1:5000/line?id={ad_id}`
   * Instagram 登入頁：`http://127.0.0.1:5000/ig?id={ad_id}`

2. **平台登入頁面 (各平台 login.html)**：
   * 當使用者在登入頁面點擊「登入」提交表單時，表單必須以 **`POST`** 方式提交 `id` 欄位至 **`/education`** 路由。
   * **表單結構範例**：
     ```html
     <form action="/education" method="POST">
         <!-- 強制攜帶廣告 ID 參數 -->
         <input type="hidden" name="id" value="{{ ad_id }}">
         
         <!-- 登入帳號與密碼輸入框 -->
         <input type="text" name="username" placeholder="帳號">
         <input type="password" name="password" placeholder="密碼">
         
         <button type="submit">登入</button>
     </form>
     ```

3. **教育宣導頁面 (`education.html`)**：
   * 後端會自動透過 `id` 查詢資料庫，並將該廣告的 `context` 與 `scam_type` 傳遞進來。
   * 頁面中必須展示：
     * 原廣告文案：`{{ context }}`
     * 詐騙手法說明：`{{ scam_type }}`
   * 頁面中的「更多資訊」按鈕會導向至 `/scammed_again`（二次受騙警告頁面），加強防詐宣導效果。
