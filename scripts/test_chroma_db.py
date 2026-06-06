import os
import sys
import io
import argparse
import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv
load_dotenv()

# 強制輸出為 UTF-8 避免 Windows 終端機遇到 Emoji 編碼錯誤
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

PROJ_ROOT = os.getenv("PROJ_ROOT")
if not PROJ_ROOT:
    raise ValueError("環境變數 PROJ_ROOT 未設定，請於 .env 檔案中配置之。")

DB_PATH = os.getenv("CHROMA_DB_PATH")
if not DB_PATH:
    raise ValueError("環境變數 CHROMA_DB_PATH 未設定，請於 .env 檔案中配置之。")

COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "ads_collection")
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "paraphrase-multilingual-MiniLM-L12-v2")

def main():
    parser = argparse.ArgumentParser(description="ChromaDB 本地檢索獨立測試工具 (無需 LLM)")
    parser.add_argument("query", type=str,
                        help="查詢的主題或產品關鍵字")
    parser.add_argument("--category", type=str, default=None, 
                        help="篩選特定品類 (例如: 美容美髮, 健康保健, 食品生鮮)")
    parser.add_argument("--tone", type=str, default=None, 
                        help="篩選特定口吻 (例如: 親切易懂, 專業實用, 感性文青)")
    parser.add_argument("--refs", type=int, default=3, 
                        help="檢索返回的參考文案篇數 (預設: 3)")
    
    args = parser.parse_args()
    
    print("="*60)
    print(" 🔎 ChromaDB 獨立語意檢索測試 (離線) ")
    print("="*60)
    print(f"查詢內容：'{args.query}'")
    if args.category:
        print(f"限定品類：{args.category}")
    if args.tone:
        print(f"限定口吻：{args.tone}")
        
    # 1. 檢查資料庫路徑
    if not os.path.exists(DB_PATH):
        print(f"[錯誤] 找不到資料庫路徑：{DB_PATH}，請先執行 index_to_chromadb.py 建立資料庫。")
        sys.exit(1)
        
    # 2. 宣告多語言 Embedding 函數
    print(f"載入 Embedding 模型 ({EMBEDDING_MODEL_NAME})...")
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL_NAME
    )
    
    # 3. 連線資料庫並取得集合
    client = chromadb.PersistentClient(path=DB_PATH)
    try:
        collection = client.get_collection(name=COLLECTION_NAME, embedding_function=embedding_fn)
    except Exception as e:
        print(f"[錯誤] 載入集合失敗：{e}，請確認資料庫是否已正確建立。")
        sys.exit(1)
        
    # 4. 組合過濾條件 (符合 ChromaDB 多重過濾限制語法)
    filters = []
    if args.category:
        filters.append({"category": args.category})
    if args.tone:
        filters.append({"tone": args.tone})
        
    if len(filters) == 0:
        where_clause = None
    elif len(filters) == 1:
        where_clause = filters[0]
    else:
        where_clause = {"$and": filters}
        
    # 5. 執行檢索
    print("正在檢索相似文案...")
    results = collection.query(
        query_texts=[args.query],
        n_results=args.refs,
        where=where_clause
    )
    
    # 6. 印出結果
    if not results or not results["ids"] or not results["ids"][0]:
        print("未找到任何符合條件的廣告文案。")
        return
        
    ids = results["ids"][0]
    docs = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]
    
    print(f"\n成功檢索到 {len(ids)} 筆相似文案：")
    for i in range(len(ids)):
        print("\n" + "-"*40 + f" 檢索結果 #{i+1} " + "-"*40)
        print(f"ID: {ids[i]}")
        print(f"相似度距離 (Distance): {distances[i]:.4f}  (越小越相似)")
        print(f"品類 (Category): {metadatas[i]['category']}")
        print(f"口吻 (Tone): {metadatas[i]['tone']}")
        print(f"中介資料路徑: {metadatas[i]['json_path']}")
        print("-"*90)
        print(docs[i].strip())
        print("-"*90)
        
