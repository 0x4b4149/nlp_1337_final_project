# ChromaDB RAG 文案生成器

## 環境架設與執行簡述

1. `.env.example` 裡面的 `[PROJ_ROOT]` 改成你的專案根目錄
2. 安裝依賴套件：`pip install -r requirements.txt`
3. 執行 `python chroma_initiator/index_to_chromadb.py` 來建立 ChromaDB 本地向量資料庫
    * 這部分會需要有 `chroma_initiator/dataset` 沒有提供在 github 上，需要另外索取
4.  執行 `python main.py --query "你的廣告主題"` 來生成文案並進行詐騙手法分析
5. 產出: `scam_database.db`，包含 `id: 15位數ID`, `context: 廣告文案`, `scam_type: 詐騙手法`

## 運作概念

1. 使用 Ollama(基本分類) + Gemini(進階分類與修正) 生成 `ad_labels_metadata.json`
2. `index_to_chromadb.py` 裡會使用 sentence-transformers 將 `ad_labels_metadata.json` 的分析以及 `dataset` 中的廣告文案轉換成向量，並將向量和原始資料存入 ChromaDB 中
3. `main.py` 會透過先在 ChromaDB 中搜尋與廣告主題相似的文案，作為 RAG 的上下文，再透過 Ollama 根據查詢的廣告主題以及檢索到的文案生成廣告文案，最後再透過 Ollama 進行詐騙手法分析
