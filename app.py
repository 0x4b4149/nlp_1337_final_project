import sqlite3
from dotenv import load_dotenv
from flask import Flask, request, render_template, redirect, url_for
import os
import random

load_dotenv()

app = Flask(__name__)
DB_PATH = os.getenv("SQLITE_DB_FILE")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# 根目錄導向測試頁面
@app.route('/')
def index():
    return redirect(url_for('scam'))

# 前置測試用的模擬詐騙頁面，隨機選擇 templates/scam 底下的 HTML 檔案
@app.route('/scam')
def scam():
    scam_dir = os.path.join(app.root_path, 'templates', 'scam')
    if os.path.exists(scam_dir):
        files = [f for f in os.listdir(scam_dir) if f.endswith('.html')]
        if files:
            selected_file = random.choice(files)
            return render_template(f"scam/{selected_file}")
    return render_template('invalid_link.html')

# 模組 A & B：入口路由與分流器、模擬登入
@app.route('/<platform>', methods=['GET'])
def login_page(platform):
    valid_platforms = ['fb', 'line', 'ig']
    
    # 檢查平台名稱是否合法
    if platform not in valid_platforms:
        return render_template('invalid_link.html')
        
    ad_id = request.args.get('id')
    
    # 檢查是否有攜帶 ID
    if not ad_id:
        return render_template('invalid_link.html')
        
    # 根據平台名稱顯示對應的視覺樣式
    template_name = f'{platform}_login.html'
    return render_template(template_name, ad_id=ad_id)

# 模組 C：教育網站與資訊展示
@app.route('/education', methods=['POST'])
def education():
    ad_id = request.form.get('id')
    
    if not ad_id:
        return render_template('invalid_link.html')
        
    # 連線至資料庫撈取資料
    conn = get_db_connection()
    scam = conn.execute('SELECT context, scam_type FROM scams WHERE id = ?', (ad_id,)).fetchone()
    conn.close()
    
    # 若查無資料，觸發模組 D
    if scam is None:
        return render_template('invalid_link.html')
        
    return render_template('education.html', context=scam['context'], scam_type=scam['scam_type'])

# 二次受騙警告頁面
@app.route('/scammed_again')
def scammed_again():
    return render_template('scammed_again.html')

if __name__ == '__main__':
    app.run(debug=True)
