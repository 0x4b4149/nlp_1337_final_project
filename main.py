import os
import sys
import io
import random
import sqlite3
import argparse
from dotenv import load_dotenv
load_dotenv()

from core.writer import generate_rag_copy
from core.analyzer import call_ollama_analyzer

# 強制輸出為 UTF-8 避免 Windows 終端機遇到 Emoji 與特殊字元編碼錯誤
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# SQLite3 資料庫儲存路徑
DB_FILE = os.getenv("SQLITE_DB_FILE")
if not DB_FILE:
    raise ValueError("環境變數 SQLITE_DB_FILE 未設定，請於 .env 檔案中配置之。")

def init_sqlite_db():
    """初始化 SQLite3 資料表"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scams (
                id TEXT PRIMARY KEY,
                context TEXT,
                scam_type TEXT
            );
        """)
        conn.commit()
        return conn
    except Exception as e:
        print(f"[錯誤] 無法初始化 SQLite3 資料庫：{e}")
        sys.exit(1)

def save_to_db(ad_id, context, scam_type):
    """將生成與分析結果寫入 SQLite3 資料庫"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 防止 ID 重複（雖然 15 位數機率極低，但基於強健性做循環檢查與重新生成）
        while True:
            cursor.execute("SELECT 1 FROM scams WHERE id = ?", (ad_id,))
            if not cursor.fetchone():
                break
            ad_id = str(random.randint(100000000000000, 999999999999999))

        cursor.execute(
            "INSERT INTO scams (id, context, scam_type) VALUES (?, ?, ?)",
            (ad_id, context, scam_type)
        )
        conn.commit()
        conn.close()
        print(f"\n[資料庫] 已成功將記錄寫入資料庫：ID={ad_id}")
        return ad_id
    except Exception as e:
        print(f"[錯誤] 寫入資料庫失敗：{e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="廣告生成與詐騙分析整合系統")
    parser.add_argument("--query", type=str,
                        help="要生成的廣告主題或產品想法")
    parser.add_argument("--category", type=str, default=None, 
                        help="篩選特定品類 (例如: 健康保健, 投資理財, 圖書書籍, 食品生鮮)")
    parser.add_argument("--tone", type=str, default=None, 
                        help="篩選特定口吻 (例如: 親切易懂, 專業實用, 感性文青)")
    parser.add_argument("--refs", type=int, default=2, 
                        help="檢索參考的廣告範本篇數 (預設: 2)")
    
    args = parser.parse_args()
    
    # 確保資料庫結構正確
    init_sqlite_db()
    
    print("=" * 60)
    print(" 🚀 啟動廣告文案生成與詐騙手法分析整合流程 ")
    print("=" * 60)
    print(f"輸入主題：'{args.query}'")
    
    # 1. 生成文案 (使用 RAG 模仿檢索)
    generated_copy = generate_rag_copy(
        query_text=args.query,
        target_category=args.category,
        target_tone=args.tone,
        n_references=args.refs
    )
    
    if not generated_copy:
        print("[錯誤] 文案生成失敗，中止後續分析流程。")
        sys.exit(1)
        
    # 2. 分析文案詐騙手法
    print("\n正在針對生成的文案進行詐騙手法分析...")
    scam_analysis = call_ollama_analyzer(generated_copy)
    
    if not scam_analysis or scam_analysis.startswith("[錯誤]"):
        print(f"[錯誤] 手法分析失敗，原因：{scam_analysis}")
        sys.exit(1)
        
    # 3. 隨機生成 15 位數 ID 廣告識別碼
    initial_id = str(random.randint(100000000000000, 999999999999999))
    
    # 4. 寫入 SQLite3 資料庫
    final_id = save_to_db(initial_id, generated_copy, scam_analysis)
    
    # 5. 印出最終分析成果
    print("\n" + "=" * 60)
    print(f" 🎯 執行成果展示 (ID: {final_id}) ")
    print("=" * 60)
    print(f"【廣告文案內容】:\n{generated_copy}")
    print("-" * 60)
    print(f"【詐騙手法分析】:\n{scam_analysis}")
    print("=" * 60)

if __name__ == "__main__":
    main()