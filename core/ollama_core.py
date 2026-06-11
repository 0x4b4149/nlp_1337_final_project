import json
import urllib.request
import urllib.error
import os
from dotenv import load_dotenv
load_dotenv()

OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/chat")

def call_ollama(prompt, system_instruction, model_name="qwen2.5:7b", temperature=0.7):
    """通用的本地 Ollama Chat API 呼叫函式"""
    payload = {
        "model": model_name,
        "messages": [
            {
                "role": "system",
                "content": system_instruction
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "stream": False,
        "options": {
            "temperature": temperature
        }
    }
    
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_API_URL,
        data=data,
        headers={"Content-Type": "application/json"}
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            res_body = json.loads(response.read().decode("utf-8"))
            return res_body.get("message", {}).get("content", "")
    except urllib.error.URLError as e:
        return f"[錯誤] 無法連線至 Ollama 服務：{e}"
    except Exception as e:
        return f"[錯誤] 呼叫 Ollama 時發生異常：{e}"

def call_ollama_vision(prompt, image_base64_list, model_name="llava", temperature=0.7):
    """通用的本地 Ollama 多模態 (Vision) API 呼叫函式"""
    payload = {
        "model": model_name,
        "messages": [
            {
                "role": "user",
                "content": prompt,
                "images": image_base64_list
            }
        ],
        "stream": False,
        "options": {
            "temperature": temperature
        }
    }
    
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_API_URL,
        data=data,
        headers={"Content-Type": "application/json"}
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            res_body = json.loads(response.read().decode("utf-8"))
            return res_body.get("message", {}).get("content", "")
    except urllib.error.URLError as e:
        return f"[錯誤] 無法連線至 Ollama 服務：{e}"
    except Exception as e:
        return f"[錯誤] 呼叫 Ollama 多模態模型時發生異常：{e}"
