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

    # 2. 準備一段美觀的預設 CSS (現代化、乾淨的風格)
    beautiful_css = """
    <style>
        :root {
            --primary-color: #2563eb;
            --background-color: #f8fafc;
            --text-color: #1e293b;
            --card-bg: #ffffff;
        }
        body {
            font-family: 'Inter', 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--background-color);
            color: var(--text-color);
            line-height: 1.6;
            margin: 0;
            padding: 2rem;
            display: flex;
            justify-content: center;
        }
        .container {
            background-color: var(--card-bg);
            padding: 2.5rem;
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
            max-width: 800px;
            width: 100%;
        }
        h1, h2, h3 {
            color: var(--primary-color);
            margin-top: 0;
        }
        button {
            background-color: var(--primary-color);
            color: white;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 6px;
            cursor: pointer;
            transition: background-color 0.2s;
        }
        button:hover {
            background-color: #1d4ed8;
        }
        a {
            color: var(--primary-color);
            text-decoration: none;
        }
        a:hover {
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

# 定義你的自訂模型名稱
model_name = "scamer"
# 指定基底模型
base_model = "qwen2.5" 
# 設定專屬 System Prompt (調整為防禦性分析)
system_prompt = """你是一個專業的資安詐騙 AI。
你的任務是讀取詐騙文案，並把以下幾點列入製作網頁的考量：
1. 這個文案試圖引誘使用者進行什麼操作？
2. 它可能使用了哪些網頁跳轉或追蹤手法（例如：帶有特定的廣告 ID）？
3. 如果這是一個釣魚網頁，它可能會偽造什麼樣的登入頁面？
生成詐騙網站主要頁面，有跳轉帳號登入，跳轉要帶上廣告 id
僅保存網頁內容，去除其他不必要的元素。"""

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
        
        # 建立請求 prompt
        prompt = f"這是一則疑似 '{scam_type}' 手法的文案。文案內容如下：\n{context}\n\n，分析攻擊者可能會如何利用這段文案建立釣魚網站（例如偽造什麼登入頁面），以及他們如何利用廣告 ID（如：{ad_id}）進行追蹤或跳轉。"
        
        # 送出給模型分析
        response = ollama.chat(model=model_name, messages=[
            {'role': 'user', 'content': prompt}
        ])
        
        raw_response = response['message']['content']
                # 處理內容
        processed_html = process_model_response(raw_response)

        # 寫入檔案
        with open('beautiful_output.html', 'w', encoding='utf-8') as f:
            f.write(processed_html)
        print("HTML 檔案已成功儲存！")
        print(f"{'='*50}\n")
        
except sqlite3.Error as e:
    print(f"資料庫錯誤: {e}")
finally:
    if 'conn' in locals():
        conn.close()

