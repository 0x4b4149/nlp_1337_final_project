import os
import ollama
from dotenv import load_dotenv
load_dotenv()

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

def call_ollama(prompt, system_instruction, model_name=OLLAMA_MODEL, temperature=0.7):
    """通用的本地 Ollama Chat API 呼叫函式 (使用官方 SDK)"""
    try:
        response = ollama.chat(
            model=model_name,
            messages=[
                {
                    "role": "system",
                    "content": system_instruction
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            options={
                "temperature": temperature
            }
        )
        return response.get("message", {}).get("content", "")
    except Exception as e:
        return f"[錯誤] 呼叫 Ollama 時發生異常：{e}"

VISION_MODEL = os.getenv("VISION_MODEL", "llava")

def call_ollama_vision(prompt, image_base64_list, model_name=VISION_MODEL, temperature=0.7):
    """通用的本地 Ollama 多模態 (Vision) API 呼叫函式 (使用官方 SDK)"""
    try:
        response = ollama.chat(
            model=model_name,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                    "images": image_base64_list
                }
            ],
            options={
                "temperature": temperature
            }
        )
        return response.get("message", {}).get("content", "")
    except Exception as e:
        return f"[錯誤] 呼叫 Ollama 多模態模型時發生異常：{e}"
