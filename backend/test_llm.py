import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import main

try:
    print(f"LLM_PROVIDER={main.LLM_PROVIDER}")
    print(f"GROQ_MODEL={main.GROQ_MODEL}")
    
    response = main._call_groq_impl("Hello, this is a test. Answer 'OK'", max_tokens=10)
    print("Response from _call_groq_impl:", response)
except Exception as e:
    print("Error calling Groq:", str(e))
