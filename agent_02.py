import os
from datetime import date
from dotenv import load_dotenv
from openai import OpenAI

from agent_01 import ask_company

MODEL = "gpt-5.4-nano"
db_name = "vector_db"
knowledge_base = "knowledge-base"   
load_dotenv(override=True)
openai_api_key = os.getenv("OPENAI_API_KEY")

openai = OpenAI(api_key=openai_api_key)

STRATEGY_PROMPT = f"""You are a senior creative strategist at a digital marketing agency.
Today is {date.today().strftime("%B %d, %Y")}.
Use the web search tool to find what is trending RIGHT NOW in the client's industry and
with their audience. Recommend exactly ONE poster concept and reply with:

CONCEPT: 3-5 sentences with the idea, the message, and what is trending now (with sources)
AUDIENCE: who we are speaking to
KEY MESSAGE: the single thing the poster must say
VISUAL DIRECTION: colours, typography, layout, imagery (stay on brand)
TRENDS USED: which trends you applied and why
TONE OF VOICE: how the text should sound

Keep it simple, practical and attractive.
Rules: stay true to the client's brand. Do not invent facts about the company.
"""

def plan_creative_strategy(company_name, goal):
    print(f"STRATEGY AGENT: Planning for {company_name} - {goal}", flush=True)

    profile = ask_company(company_name, "Describe this company: profile/services, target audience, brand voice and brand color and unique selling points.")

    prompt = f"""
        Client: {company_name}
        Client Goal: {goal}
        What we know about the company (from their documents): {profile}
    """
    response = openai.responses.create(
        model=MODEL,
        instructions=STRATEGY_PROMPT,
        input=prompt,
        tools=[{"type": "web_search"}],
    )
    
    return response.output_text
