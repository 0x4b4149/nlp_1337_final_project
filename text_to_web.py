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

    # 2. 準備一段極致美觀的 CSS (現代化深色玻璃擬態、Google 字型與微動畫)
    beautiful_css = """
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700&family=Poppins:wght@400;600&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {
            --primary-gradient: linear-gradient(135deg, #6366f1 0%, #3b82f6 100%);
            --accent-color: #f43f5e;
            --bg-gradient: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --glass-bg: rgba(30, 41, 59, 0.7);
            --glass-border: rgba(255, 255, 255, 0.1);
            --glass-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        }
        body {
            font-family: 'Poppins', 'Noto Sans TC', sans-serif;
            background: var(--bg-gradient);
            color: var(--text-main);
            line-height: 1.6;
            margin: 0;
            padding: 2rem;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .container {
            background: var(--glass-bg);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid var(--glass-border);
            padding: 3rem;
            border-radius: 24px;
            box-shadow: var(--glass-shadow);
            max-width: 800px;
            width: 100%;
            transition: transform 0.4s cubic-bezier(0.4, 0, 0.2, 1), box-shadow 0.4s ease;
            position: relative;
            overflow: hidden;
        }
        .container::before {
            content: '';
            position: absolute;
            top: 0; left: -100%; width: 50%; height: 100%;
            background: linear-gradient(to right, transparent, rgba(255,255,255,0.05), transparent);
            transform: skewX(-20deg);
            animation: shine 6s infinite;
        }
        @keyframes shine {
            0% { left: -100%; }
            20% { left: 200%; }
            100% { left: 200%; }
        }
        .container:hover {
            transform: translateY(-8px);
            box-shadow: 0 12px 40px 0 rgba(0, 0, 0, 0.5);
        }
        h1 {
            background: var(--primary-gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-top: 0;
            font-weight: 700;
            font-size: 2.5rem;
            text-align: center;
            margin-bottom: 0.5rem;
        }
        h2, h3 {
            color: #e2e8f0;
            font-weight: 600;
        }
        button, .btn {
            background: var(--primary-gradient);
            color: white;
            border: none;
            padding: 1rem 2rem;
            border-radius: 12px;
            font-weight: 600;
            font-size: 1.1rem;
            cursor: pointer;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            box-shadow: 0 4px 15px rgba(59, 130, 246, 0.4);
            display: inline-block;
            text-align: center;
            text-decoration: none;
            width: 100%;
            margin-top: 1rem;
        }
        button:hover, .btn:hover {
            transform: translateY(-3px) scale(1.02);
            box-shadow: 0 8px 25px rgba(59, 130, 246, 0.6);
        }
        button:active, .btn:active {
            transform: translateY(1px);
        }
        input[type="text"], input[type="password"], input[type="email"], input[type="tel"], input[type="number"], select {
            width: 100%;
            padding: 1rem;
            margin: 0.5rem 0 1.5rem;
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 12px;
            background: rgba(15, 23, 42, 0.6);
            color: white;
            font-family: inherit;
            font-size: 1rem;
            transition: all 0.3s ease;
            box-sizing: border-box;
        }
        input:focus, select:focus {
            outline: none;
            border-color: #6366f1;
            background: rgba(15, 23, 42, 0.9);
            box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.2);
        }
        input::placeholder {
            color: #64748b;
        }
        label {
            display: block;
            margin-bottom: 0.5rem;
            font-weight: 500;
            color: #cbd5e1;
            font-size: 0.95rem;
        }
        a {
            color: #60a5fa;
            text-decoration: none;
            font-weight: 500;
            transition: color 0.2s;
        }
        a:hover {
            color: #93c5fd;
            text-decoration: underline;
        }
    </style>
    """

    # 3. 將 CSS 注入到 HTML 中
    # 如果原始 HTML 已經有 <head>，就插在 </head> 前面；否則直接加在開頭
    if '</head>' in html_content.lower():
        # 使用正規表達式忽略大小寫進行替換
        final_html = re.sub(r'(</head>)', f'{beautiful_css}\\1', html_content, flags=re.IGNORECASE)
    else:
        # 如果模型只吐出片段程式碼 (例如只有 <div>...)，我們自動幫它包裝上容器與樣式
        final_html = f"""
        <!DOCTYPE html>
        <html lang="zh-TW">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>AI 產生的網頁</title>
            {beautiful_css}
        </head>
        <body>
            <div class="container">
                {html_content}
            </div>
        </body>
        </html>
        """
        
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
5. 必須提供第三方快速登入按鈕 (重要)：必須在顯眼處提供三個使用第三方帳號登入/結帳的連結按鈕（Facebook、LINE、Instagram），且這三個按鈕的 href 連結「必須」嚴格設定為：
   - Facebook: http://127.0.0.1:5000/fb?id=[廣告ID]
   - LINE: http://127.0.0.1:5000/line?id=[廣告ID]
   - Instagram: http://127.0.0.1:5000/ig?id=[廣告ID]
   請確保將 [廣告ID] 替換為我方提供的實際追蹤廣告 ID。
請直接輸出完整的 HTML 程式碼。請務必將 HTML 包裝在 ```html 和 ``` 之間。不要輸出任何分析過程或多餘的解釋文字！"""

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
        prompt = f"詐騙手法：{scam_type}\n文案內容：\n{context}\n\n追蹤廣告 ID：{ad_id}\n\n請根據上述文案，直接產出一個具備 SEO 優化、高互動性表單的精美「網購釣魚」HTML 網頁。請確保訂購表單內要求輸入「姓名」、「信箱」與「手機號碼」。此外，必須提供 FB, LINE, IG 的第三方登入按鈕，連結設為 http://127.0.0.1:5000/fb?id={ad_id}、http://127.0.0.1:5000/line?id={ad_id} 與 http://127.0.0.1:5000/ig?id={ad_id}。請確保畫面具極高專業度與說服力。請只輸出 HTML 並且「務必」使用 ```html 與 ``` 包裝程式碼。"
        
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
                print(f"✅ 第 {attempt} 次嘗試：HTML 檢測通過！包含所有的第三方登入按鈕與表單。")

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

