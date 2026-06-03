import os
import litellm

# Set API base for local Qwen
os.environ["OPENAI_API_BASE"] = "http://localhost:8001/v1"

print("Testing local Qwen connection...")
try:
    response = litellm.completion(
        model="openai/Qwen/Qwen2.5-72B-Instruct",
        messages=[{"role": "user", "content": "Hello! Say test."}],
        max_tokens=10
    )
    print("Success!")
    print(response.choices[0].message.content)
except Exception as e:
    print(f"Error connecting to local Qwen: {e}")
