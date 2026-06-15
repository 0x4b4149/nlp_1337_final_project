import os
import sys
import io
import random
import sqlite3
import base64
import argparse
from dotenv import load_dotenv
load_dotenv()

from core.writer import generate_rag_copy
from core.analyzer import call_ollama_analyzer
from core.ollama_core import call_ollama_vision

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

def image_to_base64(image_path):
    """讀取圖片檔案並轉成 base64 編碼字串"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def extract_image_context(image_path):
    """呼叫多模態 Vision 模型提取圖片特徵"""
    print("\n[1/4] 正在讀取並編碼圖片...")
    b64_img = image_to_base64(image_path)
    
    prompt = (
        "請仔細觀察這張圖片。這是一張潛在的商品或情境圖。請為我提取出以下資訊：\n"
        "1. 主要產品或主題是什麼？\n"
        "2. 圖片中有哪些特色、功效或賣點？\n"
        "3. 適合的目標受眾是誰？\n"
        "4. 圖片中的文字或標語有什麼？\n"
        "請務必一律使用繁體中文 (zh-TW) 簡明扼要地條列出來，這些資訊將被用來撰寫行銷文案。"
    )
    
    print("[2/4] 正在使用多模態模型分析圖片內容...")
    result = call_ollama_vision(prompt, [b64_img])
    return result

def main():
    parser = argparse.ArgumentParser(description="廣告生成與詐騙分析整合系統（支援文字、圖片、混合模式）")
    parser.add_argument("--query", type=str, default=None,
                        help="要生成的廣告主題或產品想法")
    parser.add_argument("--image", type=str, default=None,
                        help="要分析的圖片路徑")
    parser.add_argument("--category", type=str, default=None, 
                        help="篩選特定品類 (例如: 健康保健, 投資理財, 圖書書籍, 食品生鮮)")
    parser.add_argument("--tone", type=str, default=None, 
                        help="篩選特定口吻 (例如: 親切易懂, 專業實用, 感性文青)")
    parser.add_argument("--refs", type=int, default=2, 
                        help="檢索參考的廣告範本篇數 (預設: 2)")
    
    args = parser.parse_args()
    
    # 檢查參數防呆：必須提供 --query 或 --image 其中之一
    if not args.query and not args.image:
        print("[錯誤] 請至少提供 --query (文字主題) 或 --image (圖片路徑) 其中之一！")
        sys.exit(1)
        
    # 確保資料庫結構正確
    init_sqlite_db()
    
    print("=" * 60)
    print(" 🚀 啟動廣告文案生成與詐騙手法分析整合流程 ")
    print("=" * 60)
    
    # 處理三種模式的邏輯分流與檢索文字的拼接
    if args.image:
        if not os.path.exists(args.image):
            print(f"[錯誤] 找不到圖片檔案：{args.image}")
            sys.exit(1)
            
        # 提取圖片特徵
        image_context = extract_image_context(args.image)
        if not image_context or image_context.startswith("[錯誤]"):
            print(f"[錯誤] 圖片分析失敗，原因：{image_context}")
            sys.exit(1)
            
        print("\n【多模態模型提取的圖片特徵】:")
        print("-" * 60)
        print(image_context)
        print("-" * 60)
        
        if args.query:
            # 模式 3: 文字 + 圖片
            query_text = f"指定文字主題：{args.query}\n圖片特徵描述：{image_context}"
            print(f"輸入模式：【文字 + 圖片 混合輸入】")
        else:
            # 模式 2: 純圖片
            query_text = f"基於以下圖片特徵撰寫文案：\n{image_context}"
            print(f"輸入模式：【純圖片輸入】")
    else:
        # 模式 1: 純文字
        query_text = args.query
        print(f"輸入模式：【純文字輸入】")
        print(f"輸入主題：'{query_text}'")
        
    # 1. 生成文案 (使用 RAG 模仿檢索)
    generated_copy = generate_rag_copy(
        query_text=query_text,
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