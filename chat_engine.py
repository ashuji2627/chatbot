import requests

OLLAMA_API_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "llama3.2" 

def query_ollama(history):
    messages = []
    for item in history:
        messages.append({
            "role": item["role"],
            "content": item["content"]
        })

    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "stream": False
    }

    try:
        response = requests.post(OLLAMA_API_URL, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["message"]["content"]
    except Exception as e:
        return f"Error talking to Ollama: {str(e)}"
