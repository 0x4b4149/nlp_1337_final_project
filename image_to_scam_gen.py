import os
import sys
import io
import random
import base64
import argparse
from dotenv import load_dotenv

load_dotenv()

from core.ollama_core import call_ollama_vision
from core.writer import generate_rag_copy
from core.analyzer import call_ollama_analyzer
from rag_context_gen import init_sqlite_db, save_to_db

# 避免與 rag_context_gen 的 sys.stdout 重複打包

def image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def extract_image_context(image_path):
    print("\n[1/4] 正在讀取並編碼圖片...")
    b64_img = image_to_base64(image_path)
    
    prompt = "請仔細觀察這張圖片。這是一張潛在的商品或情境圖。請為我提取出以下資訊：\n1. 主要產品或主題是什麼？\n2. 圖片中有哪些特色、功效或賣點？\n3. 適合的目標受眾是誰？\n4. 圖片中的文字或標語有什麼？\n請以繁體中文簡明扼要地條列出來，這些資訊將被用來撰寫行銷文案。"
    
    print("[2/4] 正在使用 Llava 多模態模型分析圖片內容...")
    result = call_ollama_vision(prompt, [b64_img], model_name="llava")
    return result

def main():
    parser = argparse.ArgumentParser(description="多模態圖片轉詐騙文案生成器")
    parser.add_argument("image_path", type=str, help="要分析的圖片路徑")
    parser.add_argument("--category", type=str, default=None, help="篩選特定品類 (例如: 健康保健, 投資理財)")
    parser.add_argument("--tone", type=str, default=None, help="篩選特定口吻 (例如: 親切易懂, 專業實用)")
    parser.add_argument("--refs", type=int, default=2, help="檢索參考的廣告範本篇數 (預設: 2)")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.image_path):
        print(f"[錯誤] 找不到圖片檔案：{args.image_path}")
        sys.exit(1)
        
    init_sqlite_db()
    
    print("=" * 60)
    print(" 🚀 啟動多模態圖片轉詐騙文案生成器 ")
    print("=" * 60)
    
    # Step 1: 分析圖片
    image_context = extract_image_context(args.image_path)
    if not image_context or "[錯誤]" in image_context:
        print(f"[錯誤] 圖片分析失敗：{image_context}")
        sys.exit(1)
        
    print("\n【Llava 提取的圖片特徵】:")
    print("-" * 60)
    print(image_context)
    print("-" * 60)
    
    # Step 2: 將分析結果作為 Query 投入 RAG 生成
    print("\n[3/4] 正在根據圖片特徵，結合 RAG 技術生成高互動性詐騙文案...")
    
    query_text = f"基於以下圖片特徵撰寫文案：\n{image_context}"
    
    generated_copy = generate_rag_copy(
        query_text=query_text,
        target_category=args.category,
        target_tone=args.tone,
        n_references=args.refs
    )
    
    if not generated_copy:
        print("[錯誤] 文案生成失敗。")
        sys.exit(1)
        
    # Step 3: 手法分析與寫入資料庫
    print("\n[4/4] 正在分析生成文案的詐騙手法並寫入資料庫...")
    scam_analysis = call_ollama_analyzer(generated_copy)
    
    initial_id = str(random.randint(100000000000000, 999999999999999))
    final_id = save_to_db(initial_id, generated_copy, scam_analysis)
    
    print("\n" + "=" * 60)
    print(f" 🎯 最終成果展示 (ID: {final_id}) ")
    print("=" * 60)
    print(f"【生成之廣告文案內容】:\n{generated_copy}")
    print("-" * 60)
    print(f"【詐騙手法分析】:\n{scam_analysis}")
    print("=" * 60)

if __name__ == "__main__":
    main()
