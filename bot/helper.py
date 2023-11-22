import os
import base64
import requests

from dotenv import load_dotenv
load_dotenv()
api_key = os.getenv('STABILITY_API_KEY')

# Function to generate the image based on the provided prompt and style
def generate_image(prompt, style): 
    # Your existing code for generating the image goes here
    body = {
        "samples": 1,
        "height": 1024,
        "width": 1024,
        "steps": 45,
        "cfg_scale": 6,
        "style_preset": style,
        "text_prompts": [
            {
                "text": prompt,
                "weight": 0.85 # 0.1 to 1
            },
            {
                "text": "tiling, 2 heads, 2 faces, cropped image, out of frame, draft, deformed hands, signatures, twisted fingers, double image, long neck, malformed hands, multiple heads, extra limb, ugly, poorly drawn hands, missing limb, disfigured, cut-off, ugly, grain, low-res, Deformed, blurry, bad anatomy, disfigured, poorly drawn face, mutation, mutated, floating limbs, disconnected limbs, long body, disgusting, poorly drawn, mutilated, mangled, surreal, extra fingers, duplicate artefact, morbid, gross proportions, missing arms, mutated hands, mutilated hands, cloned face, malformed",
                "weight": -1 # -1 to -0.1 
            }
        ],
    }

    response = requests.post(
        "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image",  # 1024x1024
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        json=body,
    )

    if response.status_code != 200:
        raise Exception("Non-200 response: " + str(response.text))

    data = response.json()

    # Make sure the out directory exists
    if not os.path.exists("./out"):
        os.makedirs("./out")

    for i, image in enumerate(data["artifacts"]):
        with open(f'./out/txt2img_{image["seed"]}.png', "wb") as f:
            f.write(base64.b64decode(image["base64"]))

    # Return the path of the generated image
    return f'./out/txt2img_{data["artifacts"][0]["seed"]}.png'