import argparse
import re
from typing import Literal, Optional

import anthropic
from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()
client = anthropic.Anthropic()

MODEL = "claude-haiku-5-5"
SYSTEM = """You are an AI WhatsApp order parser who converts WhatsApp message into clean structured \
JSON an admin (or another program) can act on.

Use this as store catalog:
Besi beton polos (6, 8, 10, 12, 13, 16 mm), Besi beton ulir, Wiremesh (M6, M8, M10),
Hollow galvanis, Semen Tiga Roda 50 kg, Pasir, Bata merah, Kawat bendrat, Kawat duri,
Paku, Seng gelombang, Pipa PVC, Lem pipa, Plywood, Lem kayu


Rules:
- Never invent data. Anything not in the message is null. You can add it to `questions_to_ask`
- You do NOT know current prices or stock. Never guess a number. Instead you can ask it in `questions_to_ask`
- If there's any question for the admin, add it to `questions_to_ask`
- Today is Wednesday, 18 Nov 2026
- Use casual, polite Indonesian, at most 3 sentences for `questions_to_ask`
- If the customer corrects themselves (e.g. "eh, 25 aja"), use the corrected value.
"""

PRICE_INPUT_PER_TOKEN = 0.10 / 1_000_000   # USD
PRICE_OUTPUT_PER_TOKEN = 0.50 / 1_000_000  # USD
USD_TO_IDR = 18_000

class OrderItem(BaseModel):
    product: str                 # normalized catalog name
    spec: Optional[str]          # size or grade: "10 mm", "M8", "3 inch"
    quantity: Optional[float]
    unit: Optional[str]          # batang, lembar, sak, kg, rol, ...
    original_text: str           # the customer's own words for this item

class ParsedMessage(BaseModel):
    intent: Literal["new_order", "change_order", "question", "other"]
    customer_name: Optional[str]
    phone: Optional[str]
    items: list[OrderItem]
    fulfillment: Literal["delivery", "pickup", "unknown"]
    address: Optional[str]
    date: Optional[str]          # YYYY-MM-DD
    time: Optional[str]          # "pagi", "14:00", ...
    payment_method: Optional[str]
    notes: Optional[str]
    questions_to_ask: list[str]  # what the admin must confirm before processing

def cost_usd(input_tokens, output_tokens):
   return input_tokens * PRICE_INPUT_PER_TOKEN + output_tokens * PRICE_OUTPUT_PER_TOKEN

def print_usage(response):
    """Print token usage. output_tokens already INCLUDES the thinking tokens."""
    usage = response.usage
    input_tokens = usage.input_tokens
    output_tokens = usage.output_tokens
    cost = cost_usd(input_tokens, output_tokens)
    print(f"tokens: {input_tokens} in / {output_tokens} out   cost: ${cost}")

def split_messages(content: str) -> list[str]:
    """Split file content on lines that contain only '---' (spaces around it allowed)."""
    parts = re.split(r"^\s*---\s*$", content, flags=re.MULTILINE)
    return [part.strip() for part in parts if part.strip()]

def main() -> None:
    parser = argparse.ArgumentParser(description="Parse WhatsApp orders into JSON")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("message", nargs="?", help="one message to parse (put it in quotes)")
    group.add_argument("--file", help="text file with messages separated by lines of ---")
    args = parser.parse_args()

    if args.file:
        with open(args.file, encoding="utf-8") as f:
            messages = split_messages(f.read())
    else:
        messages = [args.message]

    total_input_tokens = 0
    total_output_tokens = 0

    for number, text in enumerate(messages, start=1):
        if args.file:
            print(f"\n===== message {number}/{len(messages)} =====")
            print(text)

        response = client.messages.parse(
            model=MODEL,
            max_tokens=2048,
            system=SYSTEM,
            messages=[{
                "role": "user",
                "content": text
            }],
            output_format=ParsedMessage,
        )

        parsed_messages = response.parsed_output
        print("\nparsed result:")
        print(parsed_messages.model_dump_json(indent=2))
        print_usage(response)

        total_input_tokens += response.usage.input_tokens
        total_output_tokens += response.usage.output_tokens

    if args.file:
        total_cost = cost_usd(total_input_tokens, total_output_tokens)
        print(f"\nTOTAL ({len(messages)} messages): "
              f"{total_input_tokens} in / {total_output_tokens} out   cost: ${total_cost}")

if __name__ == "__main__":
    main()
