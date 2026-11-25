# Mini-project: WhatsApp order parser

Build a command-line tool that turns messy WhatsApp messages to a hardware
store into clean JSON an admin (or another program) can act on.

```
$ python parse_order.py "ko pesen besi polos 10 20 btg, kirim besok pagi ke jl gegerkalong 45"
{
  "intent": "new_order",
  "items": [{"product": "Besi beton polos", "spec": "10 mm", "quantity": 20, "unit": "batang", ...}],
  "date": "2026-11-19",
  ...
  "questions_to_ask": ["Atas nama siapa dan nomor HP berapa?"]
}
tokens: 1,412 in / 238 out   cost: $0.00026
```

This uses every lesson: an API call (1), a system prompt (2), cost tracking
(3), effort (4) and structured output (6). Write it yourself, without letting
Claude Code generate it. This is the part that makes the lessons stick.

## Requirements

1. Use `claude-haiku-5-5` and structured outputs (`client.messages.parse` with
   a Pydantic model).
2. **Never invent data.** Anything not in the message is `null`, and the tool
   adds a question for the admin to `questions_to_ask`.
3. Resolve relative dates ("besok", "lusa", "Senin") to real dates. The model
   doesn't know today's date unless you tell it, so put it in the system prompt.
4. Normalize product names using the store's catalog (below), but keep the
   customer's original words for each item so a human can double-check.
5. Two modes:
   - `python parse_order.py "message text"` parses one message
   - `python parse_order.py --file sample_messages.txt` parses every message
     in the file (they're separated by lines containing only `---`)
6. After each message, print the token counts and cost. In file mode, also
   print the total.

## Suggested schema (change it if you have better ideas)

```python
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
```

## Store catalog (for normalizing names)

Put this in your system prompt:

```
Besi beton polos (6, 8, 10, 12, 13, 16 mm), Besi beton ulir, Wiremesh (M6, M8, M10),
Hollow galvanis, Semen Tiga Roda 50 kg, Pasir, Bata merah, Kawat bendrat, Kawat duri,
Paku, Seng gelombang, Pipa PVC, Lem pipa, Plywood, Lem kayu
```

## Suggested steps

1. Write the Pydantic schema.
2. Write the system prompt: who the tool is, today's date and weekday, the
   catalog, the no-invention rule, and how to handle corrections like
   "25 eh 30".
3. Write `parse_message(text) -> (ParsedMessage, usage)`.
4. Add the CLI (`argparse` or plain `sys.argv`) and the `---` file splitting.
5. Run it on `sample_messages.txt` and score yourself against `expected.md`.
6. Improve the system prompt until you stop making progress. Keep a short log
   of what you changed and how the score moved.

## Done when

- All 10 samples parse without errors.
- Nothing is invented: every missing fact is `null` plus a question.
- Your score against `expected.md` is written down, along with the total cost
  of one full run.

## Stretch goals

- Compare `output_config={"effort": "low"}` against the default (medium):
  score, cost and speed. Then try `thinking={"type": "disabled"}`.
- Run the same file through `claude-sonnet-5-5`. Is the higher score worth
  the price difference for this job?
- Write a small script that checks 3 fields automatically (intent, item count,
  date) against expected values. That's your first automated eval, and it's
  exactly what Phase 5 builds on.
