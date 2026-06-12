import sys
import io
import argparse
import os
from dotenv import load_dotenv
load_dotenv()

from .ollama_core import call_ollama

ANALYZER_MODEL = os.getenv("ANALYZER_MODEL", "qwen2.5:7b")

def call_ollama_analyzer(context):
    """呼叫本地 Ollama API 分析文案詐騙手法"""
    system_instruction = (
        "你是一位專業的網路防詐騙與資安分析專家。請仔細閱讀使用者提供的廣告文案，"
        "並請務必一律使用繁體中文 (zh-TW) 輸出「一段簡短且具體的主動式繁體中文分析文字」（字數限制在 100 至 200 字之間）。"
        "該文字必須直接說明該廣告文案背後具體使用了何種詐騙手法（例如：假名師投顧、一頁式購物詐騙、釣魚個資收集等）、"
        "其運作流程以及受害者會面臨的具體危害。請直接輸出此分析段落，嚴禁包含任何「好的」、「以下是分析」等前導字，"
        "亦不准輸出任何標題、項目符號或換行區隔。必須是單一整段文字。"
    )
    
    prompt = f"請分析以下廣告文案：\n\n{context}"
    
    return call_ollama(
        prompt=prompt,
        system_instruction=system_instruction,
        model_name=ANALYZER_MODEL,
        temperature=0.3
    ).strip()

def main():
    # 強制輸出為 UTF-8 避免 Windows 終端機遇到 Emoji 與特殊字元編碼錯誤
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    parser = argparse.ArgumentParser(description="廣告文案詐騙手法分析 core.analyzer 模組")
    parser.add_argument("context", type=str,
                        help="要分析的廣告文案內容")
    
    args = parser.parse_args()
    
    # 執行分析
    result = call_ollama_analyzer(args.context)
    
    # 僅輸出最終簡述結果
    print(result)

if __name__ == "__main__":
    main()
