import os
from google import genai

api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    print("ERROR: GEMINI_API_KEY is not set.")
    exit()

print("API key found. Connecting to Gemini...")

try:
    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents="Give me 3 places to visit in Kyoto, Japan. Keep it short."
    )

    print("Gemini response:")
    print(response.text)

except Exception as e:
    print("GEMINI ERROR:")
    print(type(e).__name__)
    print(str(e))