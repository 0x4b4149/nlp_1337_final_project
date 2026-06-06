import os
import json
import sys
import io
import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv
load_dotenv()

# 強制輸出為 UTF-8 以免 Windows Terminal 遇到 Emoji 報錯
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

PROJ_ROOT = os.getenv("PROJ_ROOT")
if not PROJ_ROOT:
    raise ValueError("環境變數 PROJ_ROOT 未設定，請於 .env 檔案中配置之。")

DB_PATH = os.getenv("CHROMA_DB_PATH")
if not DB_PATH:
    raise ValueError("環境變數 CHROMA_DB_PATH 未設定，請於 .env 檔案中配置之。")

DATASET_PATH = os.getenv("DATASET_PATH")
if not DATASET_PATH:
    raise ValueError("環境變數 DATASET_PATH 未設定，請於 .env 檔案中配置之。")

METADATA_FILE = os.path.join(PROJ_ROOT, "chroma_initiator", "ad_labels_metadata.json")
COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "ads_collection")

# 方案 A 採用的多語言語意向量模型名稱
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "paraphrase-multilingual-MiniLM-L12-v2")

def load_metadata(metadata_file_path):
    """載入與驗證標記中介資料"""
    if not os.path.exists(metadata_file_path):
        print(f"[錯誤] 找不到標記檔：{metadata_file_path}，請確認是否已生成該檔案。")
        sys.exit(1)
        
    with open(metadata_file_path, "r", encoding="utf-8") as f:
        metadata_map = json.load(f)
    print(f"成功載入標記元資料：共 {len(metadata_map)} 筆文案。")
    return metadata_map

def get_chroma_collection(db_path, collection_name, embedding_fn):
    """連線 ChromaDB 並取得或建立 Collection"""
    client = chromadb.PersistentClient(path=db_path)
    collection = client.get_or_create_collection(
        name=collection_name,
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"}
    )
    return collection

def prepare_documents(metadata_map, existing_ids, dataset_path):
    """讀取與過濾原始 JSON 檔案，提取 ad_context，準備要寫入的資料"""
    documents = []
    metadatas = []
    ids = []
    skipped_count = 0
    missing_files = 0
    
    for ad_id, info in metadata_map.items():
        # 若已存在資料庫則跳過
        if ad_id in existing_ids:
            skipped_count += 1
            continue
            
        raw_path = info["json_path"]
        if raw_path.lower().startswith("dataset\\"):
            sub_path = raw_path[len("dataset\\"):]
        elif raw_path.lower().startswith("dataset/"):
            sub_path = raw_path[len("dataset/"):]
        else:
            sub_path = raw_path
        json_path = os.path.join(dataset_path, sub_path)
        if not os.path.exists(json_path):
            missing_files += 1
            continue
            
        try:
            with open(json_path, "r", encoding="utf-8") as jf:
                ad_data = json.load(jf)
                ad_context = ad_data.get("ad_context", "").strip()
        except Exception as e:
            print(f"[錯誤] 讀取 JSON 失敗 {json_path}: {e}")
            continue
            
        if ad_context:
            documents.append(ad_context)
            metadatas.append({
                "category": info["category"],
                "tone": info["tone"],
                "json_path": info["json_path"]
            })
            ids.append(ad_id)
            
    print(f"已跳過已存在資料：{skipped_count} 筆。")
    if missing_files > 0:
        print(f"[警告] 找不到原始 JSON 檔案：{missing_files} 筆。")
        
    return documents, metadatas, ids

def insert_in_batches(collection, documents, metadatas, ids, batch_size=100):
    """分批將資料寫入 ChromaDB，並輸出精簡進度（免去 tqdm 依賴）"""
    if not ids:
        print("沒有新文案需要寫入。")
        return
        
    total = len(ids)
    print(f"準備寫入新資料：共 {total} 筆。")
    
    for i in range(0, total, batch_size):
        end_idx = min(i + batch_size, total)
        collection.add(
            documents=documents[i:end_idx],
            metadatas=metadatas[i:end_idx],
            ids=ids[i:end_idx]
        )
        pct = (end_idx / total) * 100
        print(f"  [進度] 已寫入 {end_idx}/{total} 筆資料 ({pct:.1f}%)...")
        
    print("資料已成功寫入 ChromaDB 本地資料庫！")

def run_verification_tests(collection):
    """執行檢索查詢測試以驗證資料庫建立結果"""
    print("\n" + "="*50)
    print(" 執行查詢測試驗證 ")
    print("="*50)
    
    test_queries = [
        {"text": "我想找降三高的保健食品", "tone": "專業實用"},
        {"text": "學習投資國際匯率的免費課程", "tone": None}
    ]
    
    for idx, tq in enumerate(test_queries, 1):
        query_text = tq["text"]
        tone_filter = tq["tone"]
        
        print(f"\n[測試 {idx}] 搜尋：'{query_text}'" + (f" (限制口吻：{tone_filter})" if tone_filter else ""))
        
        # 設定 metadata 過濾器
        where_clause = {"tone": tone_filter} if tone_filter else None
        
        results = collection.query(
            query_texts=[query_text],
            n_results=2,
            where=where_clause
        )
        
        # 輸出查詢結果
        if results and results["ids"] and results["ids"][0]:
            for rank in range(len(results["ids"][0])):
                ad_id = results["ids"][0][rank]
                doc = results["documents"][0][rank]
                meta = results["metadatas"][0][rank]
                distance = results["distances"][0][rank]
                
                # 簡短印出文案預覽
                preview = doc.replace("\n", " ")
                if len(preview) > 80:
                    preview = preview[:80] + "..."
                    
                print(f"  第 {rank+1} 名 (相似度距離: {distance:.4f})")
                print(f"    ID: {ad_id}")
                print(f"    品類: {meta['category']} | 口吻: {meta['tone']}")
                print(f"    文案預覽: {preview}")
        else:
            print("  無查詢結果。")
            
    print("\n" + "="*60)
    print(" 本地資料庫建立與測試完成 ")
    print("="*60)

def main():
    print("="*60)
    print(" 開始建立 ChromaDB 本地向量資料庫 (多語言 SentenceTransformer 版) ")
    print("="*60)
    
    # 1. 檢查並載入標記元資料
    metadata_map = load_metadata(METADATA_FILE)
    
    # 2. 宣告多語言 Embedding 函數
    print(f"初始化 Embedding 函數 (模型: {EMBEDDING_MODEL_NAME})...")
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL_NAME
    )
    
    # 3. 取得或建立 Collection
    collection = get_chroma_collection(DB_PATH, COLLECTION_NAME, embedding_fn)
    
    # 4. 快取檢查：取得資料庫已有的 IDs，避免重複向量化寫入
    existing_ids = set(collection.get()["ids"])
    print(f"資料庫中目前已有：{len(existing_ids)} 筆記錄。")
    
    # 5. 準備需要寫入的數據
    documents, metadatas, ids = prepare_documents(metadata_map, existing_ids, DATASET_PATH)
    
    # 6. 分批寫入資料庫
    insert_in_batches(collection, documents, metadatas, ids, batch_size=100)

    # 7. 進行簡單的查詢測試驗證
    run_verification_tests(collection)

if __name__ == "__main__":
    main()
    