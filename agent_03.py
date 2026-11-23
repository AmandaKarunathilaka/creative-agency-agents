import os
import json
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
from fpdf import FPDF

from agent_01 import company_id

MODEL = "gpt-5.4-nano"
output_folder = "outputs"
load_dotenv(override=True)
openai_api_key = os.getenv("OPENAI_API_KEY")
openai = OpenAI(api_key=openai_api_key)

text_field = {"type": "string"}

SCRIPT_SCHEMA = {
    "type": "object",
    "properties": {
        "campaign_overview": {
            "type": "object",
            "properties": {
                "campaign_name": text_field,
                "objective": text_field,
                "target_audience": text_field,
                "key_message": text_field,
                "tone_of_voice": text_field,
            },
            "required": ["campaign_name", "objective", "target_audience", "key_message", "tone_of_voice"],
            "additionalProperties": False,
        },
        "poster": {
            "type": "object",
            "properties": {
                "headline": text_field,
                "subheadline": text_field,
                "body_copy": text_field,
                "call_to_action": text_field,
                "visual_description": text_field,
                "layout": text_field,
                "typography": text_field,
                "colour_palette": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {"name": text_field, "hex": text_field},
                        "required": ["name", "hex"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["headline", "subheadline", "body_copy", "call_to_action",
                         "visual_description", "layout", "typography", "colour_palette"],
            "additionalProperties": False,
        },
        "storyboard": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "scene_number": {"type": "integer"},
                    "time": text_field,
                    "shot_type": text_field,
                    "visual": text_field,
                    "motion_prompt": text_field,
                    "on_screen_text": text_field,
                    "transition": text_field,
                },
                "required": ["scene_number", "time", "shot_type", "visual",
                             "motion_prompt", "on_screen_text", "transition"],
                "additionalProperties": False,
            },
        },
        "brand_notes": {"type": "array", "items": text_field},
    },
    "required": ["campaign_overview", "poster", "storyboard", "brand_notes"],
    "additionalProperties": False,
}

WRITER_PROMPT = """You are a senior copywriter and art director at an award-winning creative agency.
Turn the client's creative strategy into a polished, client-ready campaign script.

CAMPAIGN OVERVIEW
- Give the campaign a short, memorable name.
- State the objective, audience, single key message and tone of voice in one or two clear sentences each.

POSTER
- Headline: max 7 words, benefit-led, no clichés.
- Subheadline: one line that supports the headline.
- Body copy: max 25 words.
- Call to action: max 5 words, starts with a verb.
- Visual description, layout and typography: concrete enough for an image model to draw.
- Colour palette: 3 to 5 brand colours with names and hex codes (e.g. #1E90FF).

VIDEO STORYBOARD - exactly 5 scenes, 30 seconds, vertical 9:16:
- Scene 1 (0-5s): the hook. Scene 2 (5-10s) and Scene 3 (10-15s): build desire.
  For scenes 1-3, "visual" describes a single still image with NO text in it, and
  "motion_prompt" describes only camera and subject movement for an AI video model
  (e.g. "slow dolly-in, ice cubes dropping into the glass, warm bar lighting").
  Never put words or text in motion_prompt.
- Scene 4 (15-25s): the poster with a slow zoom, showing the key message.
- Scene 5 (25-30s): end card with the call to action.
- on_screen_text: max 6 words per scene. transition: e.g. cut, crossfade, zoom.

BRAND NOTES
- 3 to 5 short points explaining how the work follows the client's brand.

Rules:
- Follow the strategy's concept, audience, visual direction and tone exactly.
- Never invent prices, discounts, dates, addresses or facts not in the strategy.
- Use British/international English, correct spelling, no emojis.
"""

FONT = "Body"
FONT_REGULAR = r"C:\Windows\Fonts\arial.ttf"
FONT_BOLD = r"C:\Windows\Fonts\arialbd.ttf"

def hex_to_rgb(hex_code):
    h = hex_code.strip().lstrip("#")
    if len(h) != 6:
        return (200, 200, 200)
    try:
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return (200, 200, 200)

def section_title(pdf, text):
    pdf.ln(4)
    pdf.set_font(FONT, "B", 15)
    pdf.cell(0, 10, text, new_x="LMARGIN", new_y="NEXT")
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(3)

def label_value(pdf, label, value):
    pdf.set_font(FONT, "B", 11)
    pdf.cell(0, 6, label, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(FONT, "", 11)
    pdf.multi_cell(0, 6, value, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

def create_script_pdf(company_name, script, pdf_path):
    overview, poster = script["campaign_overview"], script["poster"]

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_font(FONT, "", FONT_REGULAR)
    pdf.add_font(FONT, "B", FONT_BOLD)

    # Title page
    pdf.add_page()
    pdf.ln(70)
    pdf.set_font(FONT, "B", 26)
    pdf.multi_cell(0, 12, overview["campaign_name"], align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(FONT, "", 14)
    pdf.cell(0, 10, f"Creative Campaign Script for {company_name}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, datetime.now().strftime("%d %B %Y"), align="C", new_x="LMARGIN", new_y="NEXT")

    # 1. Overview
    pdf.add_page()
    section_title(pdf, "1. Campaign Overview")
    label_value(pdf, "Objective", overview["objective"])
    label_value(pdf, "Target audience", overview["target_audience"])
    label_value(pdf, "Key message", overview["key_message"])
    label_value(pdf, "Tone of voice", overview["tone_of_voice"])

    # 2. Poster
    section_title(pdf, "2. Poster Script")
    label_value(pdf, "Headline", poster["headline"])
    label_value(pdf, "Subheadline", poster["subheadline"])
    label_value(pdf, "Body copy", poster["body_copy"])
    label_value(pdf, "Call to action", poster["call_to_action"])
    label_value(pdf, "Visual", poster["visual_description"])
    label_value(pdf, "Layout", poster["layout"])
    label_value(pdf, "Typography", poster["typography"])

    pdf.set_font(FONT, "B", 11)
    pdf.cell(0, 6, "Colour palette", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(FONT, "", 11)
    for colour in poster["colour_palette"]:
        pdf.set_fill_color(*hex_to_rgb(colour["hex"]))
        pdf.cell(8, 6, "", border=1, fill=True)
        pdf.cell(0, 6, f"  {colour['name']}  {colour['hex']}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)

    # 3. Storyboard
    pdf.add_page()
    section_title(pdf, "3. Video Storyboard (30s, 9:16)")
    pdf.set_font(FONT, "", 9)
    with pdf.table(col_widths=(12, 16, 22, 62, 46, 22), line_height=5, text_align="LEFT") as table:
        header = table.row()
        for title in ["Scene", "Time", "Shot", "Visual", "On-screen text", "Transition"]:
            header.cell(title)
        for scene in script["storyboard"]:
            row = table.row()
            row.cell(str(scene["scene_number"]))
            row.cell(scene["time"])
            row.cell(scene["shot_type"])
            row.cell(scene["visual"])
            row.cell(scene["on_screen_text"])
            row.cell(scene["transition"])

    # 4. Brand notes
    section_title(pdf, "4. Brand Notes")
    pdf.set_font(FONT, "", 11)
    for note in script["brand_notes"]:
        pdf.multi_cell(0, 6, f"•  {note}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)

    pdf.output(pdf_path)
    return pdf_path

def write_creative_scripts(company_name, strategy):
    print(f"CREATIVE WRITER AGENT: writing scripts for {company_name}", flush=True)

    prompt = f"Client: {company_name}\n\nCreative strategy:\n{strategy}"
    
    response = openai.responses.create(
        model=MODEL,
        instructions=WRITER_PROMPT,
        input=prompt,
        text={"format": {"type": "json_schema", "name": "campaign_script",
                         "schema": SCRIPT_SCHEMA, "strict": True}},
    )
    script = json.loads(response.output_text)

    os.makedirs(output_folder, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = os.path.join(output_folder, f"{company_id(company_name)}_scripts_{stamp}")
    scripts_path, pdf_path = base + ".json", base + ".pdf"

    with open(scripts_path, "w", encoding="utf-8") as f:
        json.dump(script, f, indent=2, ensure_ascii=False)
    create_script_pdf(company_name, script, pdf_path)

    print(f"CREATIVE WRITER AGENT: saved {scripts_path} and {pdf_path}", flush=True)
    return scripts_path, pdf_path

def load_scripts(scripts_path):
    # The poster, critic and animation agents use this to read the JSON
    with open(scripts_path, encoding="utf-8") as f:
        return json.load(f)

