import os
import sys
import io
import base64
import argparse
from dotenv import load_dotenv
load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
IMAGEN_MODEL   = os.getenv("IMAGEN_MODEL", "imagen-4.0-generate-001")


def generate_image_base64(prompt: str) -> str:
    """
    呼叫 Google GenAI SDK (Imagen 4) 生成圖片，回傳 base64 字串。
    """
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=GOOGLE_API_KEY)
    response = client.models.generate_images(
        model=IMAGEN_MODEL,
        prompt=prompt,
        config=types.GenerateImagesConfig(
            number_of_images=1,
        )
    )

    img_bytes = response.generated_images[0].image.image_bytes
    return base64.b64encode(img_bytes).decode("utf-8")


if __name__ == "__main__":
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    parser = argparse.ArgumentParser(description="Imagen 4 圖片生成模組 CLI 測試工具")
    parser.add_argument("prompt", type=str, help="圖片生成提示詞")
    parser.add_argument("--output", type=str, default="test_output.png",
                        help="輸出圖片路徑 (預設: test_output.png)")
    args = parser.parse_args()

    print(f"🚀 正在呼叫 {IMAGEN_MODEL} 生成圖片...")
    b64_str = generate_image_base64(args.prompt)

    img_data = base64.b64decode(b64_str)
    with open(args.output, "wb") as f:
        f.write(img_data)
    print(f"✅ 已儲存至：{args.output}")
