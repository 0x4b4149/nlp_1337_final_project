import os
import sys
import sqlite3
import base64
import tempfile
import argparse
from dotenv import load_dotenv
load_dotenv()

DB_FILE = os.getenv("SQLITE_DB_FILE")

def view_image(ad_id: str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT image_b64 FROM scams WHERE id = ?", (ad_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        print(f"[錯誤] 找不到 ID：{ad_id}")
        sys.exit(1)

    img_data = base64.b64decode(row[0])
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    tmp.write(img_data)
    tmp.close()
    os.startfile(tmp.name)
    print(f"已開啟圖片：{tmp.name}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="從 DB 讀取並顯示廣告配圖")
    parser.add_argument("id", type=str, help="廣告 ID")
    args = parser.parse_args()
    view_image(args.id)
