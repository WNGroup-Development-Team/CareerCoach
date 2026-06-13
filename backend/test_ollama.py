import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import main

try:
    print(f"OLLAMA_URL={main.OLLAMA_URL}")
    print(f"OLLAMA_TEXT_MODEL={main.OLLAMA_TEXT_MODEL}")
    response = main.call_ollama("Hello, this is a test. Answer 'OK'", max_tokens=10, timeout=10)
    print("Response from call_ollama:", response)
except Exception as e:
    print("Error calling Ollama:", str(e))
