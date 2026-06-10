import sqlite3
import ollama

import re
def process_model_response(response_text):
    # 1. 使用正規表達式提取 ```html 和 ``` 之間的內容
    # re.DOTALL 允許 . 匹配包含換行符號在內的所有字元
    # re.IGNORECASE 讓比對不區分大小寫
    match = re.search(r'```html\s*(.*?)\s*```', response_text, re.DOTALL | re.IGNORECASE)
    
    if match:
        html_content = match.group(1)
    else:
        # 如果模型沒有使用 ```html 包起來，可以考慮直接使用全部內容或回傳錯誤訊息
        print("警告：找不到被 ```html 包覆的內容，將嘗試使用原始回應。")
        html_content = response_text

    # 如果模型只吐出片段程式碼 (例如只有 <div>...)，我們自動幫它做基本包裝。
    # 由於我們已在 Prompt 中要求 LLM 自行生成隨機化 CSS，這裡不再硬塞靜態 CSS。
    if '</head>' not in html_content.lower() and '<html' not in html_content.lower():
        final_html = f"""
        <!DOCTYPE html>
        <html lang="zh-TW">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>活動頁面</title>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """
    else:
        final_html = html_content
        
    return final_html

def validate_generated_html(html_content, raw_response):
    html_lower = html_content.lower()
    warnings = []
    
    if '```html' not in raw_response.lower():
        warnings.append("請務必使用 ```html 和 ``` 將您的程式碼區塊包裝起來。")
        
    if '<title>' not in html_lower:
        warnings.append("缺少 <title> 標籤。")
    if 'name="description"' not in html_lower:
        warnings.append("缺少 <meta name=\"description\"> 標籤。")
        
    # 檢查是否偷加了輸入框
    if '<input' in html_lower or '<textarea' in html_lower or '<form' in html_lower:
        warnings.append("禁止包含任何 <input>、<textarea> 或 <form> 標籤！頁面上只能提供第三方快速登入連結。")
        
    # 4. 檢查是否有假登入按鈕
    if '127.0.0.1:5000/fb' not in html_lower or '127.0.0.1:5000/line' not in html_lower or '127.0.0.1:5000/ig' not in html_lower:
        warnings.append("缺少 IG, LINE 或 FB 的第三方登入按鈕連結 (需指向 http://127.0.0.1:5000/)。")

    return len(warnings) == 0, warnings

# 定義你的自訂模型名稱
model_name = "scamer"
# 指定基底模型
base_model = "qwen2.5" 
# 設定專屬 System Prompt
system_prompt = """你是一個專業的資安詐騙 AI。
你的任務是讀取詐騙文案，並製作網頁。必須遵守以下規則：
1. 分析詐騙手法並建立相應的釣魚網頁。
2. 網頁必須具有高專業度與說服力。
3. 必須包含 SEO 優化 meta 標籤與頁面標題。
4. 僅提供第三方登入 (極重要)：網頁上「絕對禁止」出現任何 <input>、<textarea> 或 <form> 等供使用者輸入文字的表單欄位。
5. 第三方快速登入按鈕 (重要)：必須在顯眼處提供且「僅提供」三個使用第三方帳號快速登入的連結按鈕（Facebook、LINE、Instagram），且這三個按鈕的 href 連結「必須」嚴格設定為：
   - Facebook: http://127.0.0.1:5000/fb?id=[廣告ID]
   - LINE: http://127.0.0.1:5000/line?id=[廣告ID]
   - Instagram: http://127.0.0.1:5000/ig?id=[廣告ID]
   請確保將 [廣告ID] 替換為我方提供的實際追蹤廣告 ID。
6. 隨機化極致美觀 CSS (重要)：請不要使用外部 CSS 檔案，必須直接在 HTML 內嵌 `<style>` 區塊。每次生成的網頁風格必須「隨機變化」（例如：可以是深色玻璃擬態、極簡白、霓虹賽博龐克、或特定品牌的高級感），但無論如何隨機，都必須具備極致美觀、現代化的 UI 設計（包含漸層、陰影、懸停動畫等）。
請直接輸出包含 <html>, <head>, <body> 與內嵌 <style> 的完整 HTML 程式碼。請務必將 HTML 包裝在 ```html 和 ``` 之間。不要輸出任何分析過程或多餘的解釋文字！"""

print(f"正在基於 {base_model} 建立模型 '{model_name}'...")

# 建立模型
try:
    ollama.create(
        model=model_name, 
        from_=base_model, 
        system=system_prompt
    )
    print("模型建立成功！\n")
except Exception as e:
    print(f"建立模型時發生錯誤，請確認 Ollama 服務是否正常執行：{e}")

# 連結到 SQLite 資料庫
db_path = 'scam_database.db'
try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 讀取資料庫內容
    cursor.execute("SELECT id, context, scam_type FROM scams LIMIT 3") # 先取前三筆測試
    records = cursor.fetchall()
    
    if not records:
        print("資料庫中目前沒有資料。")
    
    for row in records:
        ad_id, context, scam_type = row
        print(f"\n{'='*50}")
        print(f"正在分析資料... 廣告 ID: {ad_id} | 詐騙手法: {scam_type}")
        print(f"原始文案: {context}")
        print(f"{'-'*50}\nAI 分析結果：")
        
        # 建立請求 prompt (明確要求產出 HTML 且不用多餘分析)
        prompt = f"詐騙手法：{scam_type}\n文案內容：\n{context}\n\n追蹤廣告 ID：{ad_id}\n\n請根據上述文案，直接產出一個具備 SEO 優化的精美「網購釣魚」HTML 網頁。請注意：頁面上「絕對禁止」出現任何輸入框(<input>)或表單(<form>)。整個網頁的互動只能是點擊 FB, LINE, IG 這三個第三方登入按鈕，連結設為 http://127.0.0.1:5000/fb?id={ad_id}、http://127.0.0.1:5000/line?id={ad_id} 與 http://127.0.0.1:5000/ig?id={ad_id}。請確保畫面具極高專業度與說服力。請只輸出 HTML 並且「務必」使用 ```html 與 ``` 包裝程式碼。"
        
        max_retries = 3
        attempt = 0
        is_valid = False
        processed_html = ""
        warnings = []
        
        while attempt < max_retries and not is_valid:
            attempt += 1
            if attempt > 1:
                print(f"🔄 正在進行第 {attempt} 次重新生成...")
                warnings_text = "\n".join([f"- {w}" for w in warnings])
                current_prompt = prompt + f"\n\n【重要修正指示】：前一次生成的結果有以下缺失，請務必在此次生成中修正：\n{warnings_text}"
            else:
                current_prompt = prompt

            # 送出給模型分析
            response = ollama.chat(model=model_name, messages=[
                {'role': 'user', 'content': current_prompt}
            ])
            
            raw_response = response['message']['content']
            # 處理內容
            processed_html = process_model_response(raw_response)

            # 執行自我檢測機制
            is_valid, warnings = validate_generated_html(processed_html, raw_response)
            if not is_valid:
                print(f"⚠️ 第 {attempt} 次嘗試 HTML 檢測發現以下問題：")
                for w in warnings:
                    print(f"  - {w}")
            else:
                print(f"✅ 第 {attempt} 次嘗試：HTML 檢測通過！僅包含第三方登入按鈕，沒有多餘的輸入框。")

        if not is_valid:
            print("❌ 已達到最大重試次數 (3次)，仍未能產出完全符合規範的 HTML，將強制儲存最後一次的結果。")

        # 寫入檔案
        filename = f'output_ad_{ad_id}.html'
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(processed_html)
        print(f"HTML 檔案已成功儲存為 {filename}！")
        print(f"{'='*50}\n")
        
except sqlite3.Error as e:
    print(f"資料庫錯誤: {e}")
finally:
    if 'conn' in locals():
        conn.close()

