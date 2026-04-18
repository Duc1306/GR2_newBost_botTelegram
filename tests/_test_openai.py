from dotenv import load_dotenv
load_dotenv()
import os
try:
    from openai import OpenAI
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        print("OPENAI_API_KEY: CHUA SET trong .env")
    else:
        client = OpenAI(api_key=key)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "say OK"}],
            max_tokens=5
        )
        print("OpenAI HOAT DONG:", resp.choices[0].message.content)
except ImportError:
    print("Chua cai openai. Chay: pip install openai")
except Exception as e:
    print("LOI:", e)
