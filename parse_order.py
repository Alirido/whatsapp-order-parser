import argparse
import re
import sys
from typing import Literal, Optional

import anthropic
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError

load_dotenv()
client = anthropic.Anthropic()

MODEL = "claude-haiku-5-5"
EFFORT = "medium"    # Haiku 5.5's default, set explicitly so it's easy to compare
MAX_TOKENS = 8000    # covers thinking + JSON; you only pay for tokens actually generated
SYSTEM = """You are an AI WhatsApp order parser who converts WhatsApp message into clean structured \
JSON an admin (or another program) can act on.

Store's catalog:
Besi beton polos (6, 8, 10, 12, 13, 16 mm), Besi beton ulir, Wiremesh (M6, M8, M10),
Hollow galvanis, Semen Tiga Roda 50 kg, Pasir, Bata merah, Kawat bendrat, Kawat duri,
Paku, Seng gelombang, Pipa PVC, Lem pipa, Plywood, Lem kayu


Rules:
- Never invent data. Anything not in the message is null. You can add it to `questions_to_ask`
- You do NOT know current prices or stock. Never guess a number. Instead you can ask it in `questions_to_ask`
- If there's any question for the admin, add it to `questions_to_ask`
- Today is Wednesday, 18 Nov 2026
- Normalize product names using the store's catalog.
- Use casual, polite Indonesian for `questions_to_ask`
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

def format_usage(input_tokens, output_tokens):
    """Token counts and cost. output_tokens already INCLUDES the thinking tokens."""
    cost = cost_usd(input_tokens, output_tokens)
    return (f"tokens: {input_tokens:,} in / {output_tokens:,} out   "
            f"cost: ${cost:.6f} (about Rp {cost * USD_TO_IDR:,.2f})")

def log(*args):
    """Everything except the JSON goes to stderr, so stdout stays pure JSON."""
    print(*args, file=sys.stderr)

class ParseError(Exception):
    """The model answered but gave no usable result (e.g. a refusal).

    Carries `usage` because the call was still billed."""

    def __init__(self, message, usage):
        super().__init__(message)
        self.usage = usage

def parse_message(text: str):
    """Parse one WhatsApp message. Returns (ParsedMessage, usage).

    Raises:
        ParseError: the model answered but there is no parsed result.
        pydantic.ValidationError: the reply didn't match the schema, usually
            because it was cut off at MAX_TOKENS. No usage is available.
        anthropic.APIError: the request itself failed (network, rate limit, ...).
    """
    response = client.messages.parse(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM,
        messages=[{"role": "user", "content": text}],
        output_format=ParsedMessage,
        output_config={"effort": EFFORT},
    )
    if response.parsed_output is None:
        raise ParseError(f"no parsed output (stop_reason: {response.stop_reason})",
                         response.usage)
    return response.parsed_output, response.usage

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
    failed = 0
    uncounted = 0  # failed calls that were billed but returned no usage

    for number, text in enumerate(messages, start=1):
        if args.file:
            log(f"\n===== message {number}/{len(messages)} =====")
            log(text)

        try:
            parsed, usage = parse_message(text)
            print(parsed.model_dump_json(indent=2))
        except ParseError as e:
            failed += 1
            usage = e.usage  # billed, so still count it below
            log(f"ERROR: {e}")
        except ValidationError as e:
            failed += 1
            uncounted += 1
            log(f"ERROR: reply didn't match the schema, probably cut off at "
                f"max_tokens={MAX_TOKENS} ({e.error_count()} validation errors). "
                f"This call was billed but its tokens are unknown.")
            continue
        except anthropic.APIError as e:
            failed += 1
            log(f"ERROR: API request failed: {e}")
            continue

        log(format_usage(usage.input_tokens, usage.output_tokens))
        total_input_tokens += usage.input_tokens
        total_output_tokens += usage.output_tokens

    if args.file:
        log(f"\nTOTAL ({len(messages)} messages, {failed} failed): "
            + format_usage(total_input_tokens, total_output_tokens))
        if uncounted:
            log(f"WARNING: total excludes {uncounted} cut-off call(s) whose tokens are unknown.")

    if failed:
        sys.exit(1)

if __name__ == "__main__":
    main()
