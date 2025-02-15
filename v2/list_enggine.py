import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_host = os.getenv("API_HOST", "https://api.stability.ai")
url = f"{api_host}/v1/engines/list"

api_key = os.getenv("STABILITY_API_KEY")
if api_key is None:
    raise Exception("Missing Stability API key.")

response = requests.get(url, headers={"Authorization": f"Bearer {api_key}"})

if response.status_code != 200:
    raise Exception("Non-200 response: " + str(response.text))

# Parse the JSON payload
payload = response.json()

# Print the payload
print(payload)

# Iterate over the engines and print their details
for engine in payload:
    print(f"ID: {engine['id']}")
    print(f"Name: {engine['name']}")
    print(f"Description: {engine['description']}")
    print(f"Type: {engine['type']}")

    # Only print "Ready" if it exists in the response
    if "ready" in engine:
        print(f"Ready: {engine['ready']}")

    print("-" * 20)
