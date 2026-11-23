import os
import glob
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
from openai import OpenAI

from agent_03 import load_scripts

load_dotenv(override=True)

MODEL = "gpt-5.4-nano"
openai = OpenAI()

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
EMAIL_TO = os.getenv("EMAIL_TO")

MAX_EMAIL_MB = 24      # Gmail rejects emails over 25MB

ATTACHMENT_TYPES = {
    ".png": ("image", "png"),
    ".pdf": ("application", "pdf"),
    ".mp4": ("video", "mp4"),
}

SOCIAL_PROMPT = """
You are a social media manager. From the campaign script, write:
HOOK: one scroll-stopping first line (max 10 words)
CAPTION: 2-3 short sentences for Instagram/TikTok, on brand, ending with the call to action
HASHTAGS: 6-8 relevant hashtags
Do not invent prices, offers or facts that are not in the script.
"""

def write_hook_and_caption(script):
    response = openai.responses.create(
        model=MODEL,
        instructions=SOCIAL_PROMPT,
        input=str(script),
    )
    return response.output_text

def send_creative_email(company_name, scripts_path, poster_path, pdf_path, video_path=None, client_email=None):
    client_email = client_email or EMAIL_TO
    if not client_email:
        return "No email address given and EMAIL_TO is not set in .env. Ask the user for the client's email."
    print(f"PRODUCT MANAGER AGENT: sending campaign for {company_name} to {client_email}", flush=True)

    script = load_scripts(scripts_path)
    social = write_hook_and_caption(script)
    campaign_name = script["campaign_overview"]["campaign_name"]

    # Attach only files that exist, and keep the total under Gmail's limit
    files, total_mb, skipped = [], 0, []
    for path in [poster_path, pdf_path, video_path]:
        if not path or not os.path.exists(path):
            continue
        size_mb = os.path.getsize(path) / (1024 * 1024)
        if total_mb + size_mb > MAX_EMAIL_MB:
            skipped.append(os.path.basename(path))
            continue
        files.append(path)
        total_mb += size_mb

    msg = EmailMessage()
    msg["Subject"] = f"{company_name}: {campaign_name} - Creative Campaign"
    msg["From"] = SMTP_USERNAME
    msg["To"] = client_email
    msg.set_content(f"""Hello {company_name} team,

Your new creative campaign "{campaign_name}" is ready. Attached you will find:
- The campaign poster (PNG)
- The full creative script and storyboard (PDF)
- The animated social media video (MP4)

Suggested social media post:
{social}

Kind regards,
Creative Agency Team
""")

    for path in files:
        maintype, subtype = ATTACHMENT_TYPES[os.path.splitext(path)[1].lower()]
        with open(path, "rb") as f:
            msg.add_attachment(f.read(), maintype=maintype, subtype=subtype,
                               filename=os.path.basename(path))

    if SMTP_PORT == 465:
        server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT)
    else:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()                  # port 587: upgrade to an encrypted connection
    with server:
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)

    result = f"Email sent to {client_email} with {len(files)} attachments ({total_mb:.1f} MB)."
    if skipped:
        result += f" Skipped (too large): {', '.join(skipped)}"
    print(f"PRODUCT MANAGER AGENT: {result}", flush=True)
    return f"{result}\n\n{social}"

def newest(pattern):
    files = glob.glob(pattern)
    return max(files, key=os.path.getmtime) if files else None

