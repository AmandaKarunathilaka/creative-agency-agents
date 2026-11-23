import os
import base64
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
from agent_03 import load_scripts
from agent_01 import company_id

IMAGE_MODEL = "gpt-image-2.6-sunburst"
OUTPUT_DIR = "outputs"
load_dotenv(override=True)
openai_api_key = os.getenv("OPENAI_API_KEY")
openai = OpenAI(api_key=openai_api_key)

IMAGE_PROMPT_TEMPLATE = """Create a professional vertical marketing poster for {company_name}.

TEXT ON THE POSTER (spell exactly as written, nothing else):
- Headline: "{headline}"
- Subheadline: "{subheadline}"
- Call to action: "{cta}"

VISUAL: {visual}
LAYOUT: {layout}
TYPOGRAPHY: {typography}
BRAND COLOURS: {colours}

Requirements: clean, premium, eye-catching, ready to print or post.
Do not add prices, logos, extra words or watermarks that are not listed above.
"""

def create_poster(company_name, scripts_path):
    print(f"POSTER CREATE AGENT: creating poster for {company_name}", flush=True)
    poster = load_scripts(scripts_path)["poster"]
    colours = ", ".join(f"{c['name']} {c['hex']}" for c in poster["colour_palette"])

    prompt = IMAGE_PROMPT_TEMPLATE.format(
        company_name=company_name,
        headline=poster["headline"],
        subheadline=poster["subheadline"],
        cta=poster["call_to_action"],
        visual=poster["visual_description"],
        layout=poster["layout"],
        typography=poster["typography"],
        colours=colours,
    )

    result = openai.images.generate(model=IMAGE_MODEL, prompt=prompt, size="1024x1536")
    image_bytes = base64.b64decode(result.data[0].b64_json)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    poster_path = os.path.join(OUTPUT_DIR, f"{company_id(company_name)}_poster_{stamp}.png")
    with open(poster_path, "wb") as f:
        f.write(image_bytes)

    print(f"POSTER CREATE AGENT: saved {poster_path}", flush=True)
    return poster_path