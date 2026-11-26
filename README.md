# WhatsApp order parser

Turns casual Indonesian WhatsApp messages sent to a building-supply store into
structured JSON an admin can act on, plus the questions the admin still needs
to ask. Built on Claude Haiku 5.5 structured outputs, and measured with a small
eval set: **3/10 → 10/10 over three logged runs, at about $0.0007 per message.**

## The problem

Small Indonesian hardware stores (*toko bangunan*) take orders over WhatsApp.
The messages are full of slang, abbreviations, self-corrections and relative
dates, and an admin retypes each one into an order and chases the missing
details. Message 6 of the eval set:

> halo ko ini pak asep yg di cijerah itu loh ko mau ambil lagi kayak biasa ya besi 8 50 batang terus besi 10 nya 25 eh 30 aja deh ko sama kawat bendrat 2 rol nanti dianter aja ke rumah sore2 lusa ya ko makasih

*Roughly: "Hi, it's Pak Asep from Cijerah. Same as usual: 8 mm rebar, 50 rods,
then the 10 mm, 25, uh, make it 30, and 2 rolls of tie wire. Deliver to my
house the day after tomorrow, in the afternoon. Thanks."*

The parser's actual output (from [`runs/03a-address-new-rule.txt`](runs/03a-address-new-rule.txt), with "today" fixed at Wednesday 2026-11-18 for testing):

```json
{
  "intent": "new_order",
  "customer_name": "Pak Asep",
  "phone": null,
  "items": [
    {"product": "Besi beton polos", "spec": "8 mm",  "quantity": 50.0, "unit": "pcs",  "original_text": "besi 8 50 batang"},
    {"product": "Besi beton polos", "spec": "10 mm", "quantity": 30.0, "unit": null,   "original_text": "besi 10 nya 25 eh 30 aja deh"},
    {"product": "Kawat bendrat",    "spec": null,    "quantity": 2.0,  "unit": "roll", "original_text": "kawat bendrat 2 rol"}
  ],
  "fulfillment": "delivery",
  "address": "Cijerah",
  "date": "2026-11-20",
  "time": null,
  "time_of_day": "afternoon",
  "payment_method": null,
  "notes": "Pelanggan ingin mengambil lagi pesanan seperti biasa. Pesanan besi 10 sudah dikoreksi dari 25 menjadi 30.",
  "questions_to_ask": [
    "Pak Asep, boleh minta alamat lengkapnya di Cijerah (nama jalan dan nomor rumah) ya?",
    "Pak Asep, untuk besi 8 mm mau yang polos atau ulir ya?",
    "Pak Asep, besi 10 mm 30 itu batang atau satuan lainnya ya?",
    "Pak Asep, boleh minta nomor WhatsApp yang bisa dihubungi untuk konfirmasi pengiriman?",
    "Pak Asep, pembayarannya mau bagaimana ya (tunai atau transfer)?"
  ]
}
```

It takes the corrected 30 rather than 25, resolves *lusa* to a date, and keeps
the area without inventing a street. The missing street, phone number and
payment method stay `null` and turn into questions for the admin.

## How it works

- **One API call per message** with `client.messages.parse` and a Pydantic
  schema (structured outputs), so every reply fits the schema. Model
  `claude-haiku-5-5`, effort `medium`.
- **The system prompt** holds the store's catalog for normalizing product names,
  today's date and weekday, and the rules: never invent data (anything missing
  becomes `null` plus a question), never guess prices or stock, and use the
  corrected value when the customer corrects themselves.
- **Most of the rules live in the schema, not the prompt.** `date` is a real
  date type, `time` must be `HH:MM`, `intent`, `unit` and `time_of_day` are
  closed lists, and field descriptions define the edge cases (for example, an
  area with no street still counts as an address).
- **Command line:** parse one message, or a `--file` of messages separated by
  `---`. Token counts and cost are printed for each message.

## How it's evaluated

- **10 sample messages**, each with its own trap ([`expected.md`](expected.md)):
  abbreviations, relative dates ("hari Senin"), a self-correction, a change to
  an order this message doesn't contain, an English message, and a message
  that is almost entirely "the usual".
- **Automatic checks** ([`answer_key.py`](answer_key.py)): 7 fields per message
  (intent, date, fulfillment, item count, time, time of day, address). Many
  expected values are `null` on purpose, so they also catch invented data.
- **A message passes** only if every check passes *and* a human read finds
  nothing invented, with products, sizes and quantities right.
- **Every score can be traced to its code:** `run.sh` refuses to run on
  uncommitted code, so each score belongs to one commit. `check_run.py` scores
  the saved output without calling the API. When the answer key changes, every
  old run is rescored, so all runs are judged by the same key.

## Results

| Run | What changed | Score | Cost (10 msgs) | Time |
| --- | --- | --- | --- | --- |
| 01 | Baseline | 3/10 | $0.0061 | not recorded |
| 02 | Typed date/time, `time_of_day`, closed unit list, `conditional_order` intent | 9/10 | $0.0064 | 50 s |
| 03a | Defined what counts as an address | 10/10 | $0.0068 | 52 s |

Per-message detail is in [`LOG.md`](LOG.md), and the raw outputs are in [`runs/`](runs/).

**What I learned**

- **4 of the 7 baseline failures were right answers in the wrong shape:**
  `"Senin, 23 Nov 2026"` instead of `2026-11-23`, or `"pagi"` in the
  exact-time field. Typing the fields (a real date type, an `HH:MM` pattern, a
  separate `time_of_day` list) fixed all four. A schema enforces a format; a
  prompt can only ask for one.
- **The model handled two identical situations differently.** It kept "Dago" as the address but dropped
  "Cijerah", because the field had no definition. I wrote a failing check
  first, then added a field description, and the next run passed.
- **Precision cost tokens.** The extra field descriptions added about 5,700
  input tokens per run (17,162 → 22,902), so cost rose about 12% while
  passing messages went from 3 to 10.

## Limits

- **10/10 is measured on the same 10 messages I tuned against.** It's an upper
  bound, not a score on messages the parser has never seen. A held-out set
  is the next step.
- **Each version was run once.** Outputs vary between runs, so a one-message
  difference could be noise.
- The automatic checks cover 7 fields. Products, sizes, quantities and
  invented data are judged by hand, by one person.
- One store, one catalog in the prompt, one fixed date.
- The closed unit list maps *batang*, *sak* and *kaleng* to `pcs`, which loses
  detail.
- In the example above, the parser filled in "Besi beton polos" for "besi 8"
  while also asking whether it's *polos* or *ulir*. The field states a guess
  that the questions admit is uncertain.
- Not compared yet: a lower effort level, or a larger model.

## Run it

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file containing `ANTHROPIC_API_KEY=sk-ant-...` (git ignores it), then:

```bash
python parse_order.py "ko pesen besi polos 10 20 btg, kirim besok pagi ke jl gegerkalong 45"
python parse_order.py --file sample_messages.txt
./run.sh 04-my-change                                  # one scored run (calls the API)
python check_run.py runs/03a-address-new-rule.txt      # re-check a saved run (no API call)
```

## Files

| File | What it is |
| --- | --- |
| `parse_order.py` | Schema, system prompt and command line |
| `sample_messages.txt`, `expected.md` | The eval inputs, and what a correct parse must contain |
| `answer_key.py` | The automatic checks |
| `run.sh`, `check_run.py` | One scored run; scoring and logging |
| `LOG.md`, `runs/` | Every run's score, cost and raw output |
| `BRIEF.md` | The original project brief |

## How this was built

This was the capstone of Phase 1 of my self-study in AI engineering, built from
[`BRIEF.md`](BRIEF.md). I wrote the schema and the prompt and made the
evaluation decisions. Claude Code acted as my tutor and wrote most of the
Python tooling around them (`check_run.py`, `run.sh`, error handling).
