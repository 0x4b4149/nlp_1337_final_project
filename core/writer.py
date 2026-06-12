import os
import re
import sys
import io
import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv
load_dotenv()

from .ollama_core import call_ollama

DB_PATH = os.getenv("CHROMA_DB_PATH")
if not DB_PATH:
    raise ValueError("環境變數 CHROMA_DB_PATH 未設定，請於 .env 檔案中配置之。")
COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "ads_collection")
GENERATOR_MODEL = os.getenv("GENERATOR_MODEL", "qwen2.5:7b") # 產生器使用基底模型以保持創意度
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "paraphrase-multilingual-MiniLM-L12-v2")

def call_ollama_generator(prompt):
    system_instruction = "你是一位專業的廣告文案寫手。擅長模仿他人文案排版、換行、語氣與 Emoji 習慣。你的回覆必須「僅包含」最終生成的廣告文案內容本身，嚴禁輸出 any 前導說明、分析摘要、結束語、引導標題、或 any 真實的網址連結。請直接給出可以直接複製使用的文案。請務必一律使用繁體中文 (zh-TW) 輸出。"
    return call_ollama(
        prompt=prompt,
        system_instruction=system_instruction,
        model_name=GENERATOR_MODEL,
        temperature=0.7
    )

def generate_rag_copy(query_text, target_category=None, target_tone=None, n_references=2):
    # 1. 連線本地資料庫與載入 Embedding 函數
    if not os.path.exists(DB_PATH):
        print(f"[錯誤] 找不到資料庫路徑：{DB_PATH}，請確認 chroma_db 目錄存在。")
        return None
        
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL_NAME
    )
    
    client = chromadb.PersistentClient(path=DB_PATH)
    try:
        collection = client.get_collection(
            name=COLLECTION_NAME,
            embedding_function=embedding_fn
        )
    except Exception as e:
        print(f"[錯誤] 載入集合失敗：{e}，可能尚未建立或資料為空。")
        return None
        
    # 2. 設定篩選條件 (ChromaDB 多重 Filter 語法)
    filters = []
    if target_category:
        filters.append({"category": target_category})
    if target_tone:
        filters.append({"tone": target_tone})
        
    if len(filters) == 0:
        where_clause = None
    elif len(filters) == 1:
        where_clause = filters[0]
    else:
        where_clause = {"$and": filters}
        
    print(f"\n[1/3] 正在檢索最相關的廣告範例...")
    # 3. 檢索
    results = collection.query(
        query_texts=[query_text],
        n_results=n_references,
        where=where_clause
    )
    
    if not results or not results["ids"] or not results["ids"][0]:
        print("沒有在資料庫中檢索到任何相關的廣告文案，無法進行風格模仿。")
        return None
        
    # 4. 收集檢索到的參考文案
    reference_texts = []
    print("\n" + "-"*30 + " 檢索到的參考範本 (已自動過濾網址連結) " + "-"*30)
    for rank in range(len(results["ids"][0])):
        ad_id = results["ids"][0][rank]
        doc = results["documents"][0][rank]
        meta = results["metadatas"][0][rank]
        distance = results["distances"][0][rank]
        
        # 過濾文案中的超連結與無協議網址域名
        clean_doc = re.sub(r'https?://\S+', '', doc)
        clean_doc = re.sub(r'\b[a-zA-Z0-9.-]+\.(?:com|top|cyou|net|org|co|info|club|cc|tw)(?:/\S*)?\b', '', clean_doc)
        
        print(f"範本 #{rank+1} (ID: {ad_id} | 距離: {distance:.4f} | 品類: {meta['category']} | 口吻: {meta['tone']})")
        print(clean_doc)
        print("-" * 78)
        reference_texts.append(clean_doc)
        
    # 5. 組合 RAG Prompt
    prompt = (
        "請仔細觀摩以下檢索到的廣告參考範本，吸收它們的排版換行、語氣句式以及 Emoji 表情符號的點綴規律：\n\n"
    )
    
    for idx, ref in enumerate(reference_texts, 1):
        prompt += f"【參考範本 {idx}】\n{ref}\n"
        prompt += "=" * 40 + "\n\n"
        
    prompt += (
        f"任務：請針對以下指定的主題或產品，為我生成一篇全新且原創的「繁體中文」廣告文案。\n"
        f"【指定主題/產品】：{query_text}\n\n"
        f"【嚴格生成規則】：\n"
        f"1. 必須高度模仿參考範本的排版換行風格與 Emojis 的豐富點綴方式（例如標題加 🌿 或 🔥，項目符號加 ▸ 或 ✅）。\n"
        f"2. 口吻必須和參考範本保持高度一致。\n"
        f"3. 內容必須圍繞指定的主題產品，絕不可直接照抄範本中的產品名稱。\n"
        f"4. 你的輸出必須「僅包含」生成的文案內容本身。嚴禁包含任何「好的」、「這是為您生成的文案」等前導/後續語，也嚴禁輸出對範本的分析或 Markdown 大標題。\n"
        f"5. 【長度與內容全面擴充】：不論參考範本是否簡短，生成的廣告文案都必須是內容豐富且結構完整的長文案（建議總字數在 350 至 600 字之間）。你必須主動擴充以下幾個核心區塊，並以空行和 Emoji 進行美觀的排版：\n"
        f"   - 【吸睛標題】：一個帶有吸睛表情符號的震撼開頭\n"
        f"   - 【核心賣點與功效】：3-4 個具體列點，說明產品的核心特色與優勢（項目符號必須模仿範本，如 ➤️, ✅, ✦, 🌟 等）\n"
        f"   - 【痛點與適用情境】：描述適用族群、痛點或日常生活使用場景，引起讀者共鳴\n"
        f"   - 【限時優惠與行動呼籲 (CTA)】：主動加上優惠促銷資訊（例如：限時買一送一、前50名免運、點擊連結搶購等）與明確的引導購買文字\n"
        f"   - 【熱門 Hashtags】：在文案最後一行加上 5-8 個與該產品及品類高度相關的井字標籤（如 #保健食品 #健康養生 等）\n"
        f"6. 【嚴禁輸出真實網址與連結】：生成的廣告文案中「嚴禁」出現任何真實的網址、域名或連結位址（例如 http://... 或 abc.com ）。若參考範本中含有連結，請直接忽略，或以「點擊下方連結」等通用文案替代，絕不可複製或生成任何真實網址。\n\n"
        f"請直接輸出全新文案內容："
    )
    
    # 6. 生成
    print("\n[2/3] 正在分析風格並生成新廣告文案 (使用 qwen2.5:7b)...")
    generated_copy = call_ollama_generator(prompt)
    
    # 7. 輸出結果
    print("\n[3/3] 生成文案結果如下：")
    print("=" * 60)
    print(generated_copy.strip())
    print("=" * 60)
    return generated_copy

import argparse

if __name__ == "__main__":
    # 強制輸出為 UTF-8 避免 Windows 終端機遇到 Emoji 與特殊字元編碼錯誤
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    parser = argparse.ArgumentParser(description="RAG 廣告文案生成器 core.writer 模組 CLI 測試工具")
    parser.add_argument("query", type=str,
                        help="要生成的廣告主題或產品想法")
    parser.add_argument("--category", type=str, default=None, 
                        help="篩選特定品類 (例如: 健康保健, 投資理財, 圖書書籍, 食品生鮮)")
    parser.add_argument("--tone", type=str, default=None, 
                        help="篩選特定口吻 (例如: 親切易懂, 專業實用, 感性文青)")
    parser.add_argument("--refs", type=int, default=2, 
                        help="檢索參考的廣告範本篇數 (預設: 2)")
    
    args = parser.parse_args()
    
    print("="*60)
    print(" 開始 RAG 模仿文案檢索生成測試 ")
    print("="*60)
    print(f"產品主題想法：'{args.query}'")
    if args.category:
        print(f"限制篩選品類：{args.category}")
    if args.tone:
        print(f"限制篩選口吻：{args.tone}")
        
    generate_rag_copy(
        query_text=args.query,
        target_category=args.category,
        target_tone=args.tone,
        n_references=args.refs
    )
