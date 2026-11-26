# Order parser: score log

Fixed for every run: model `claude-haiku-5-5`, effort `medium`, today = 2026-11-18,
`sample_messages.txt` (10 messages), scored against `expected.md`.

**Scoring rule:** a message passes only if every "Must contain" fact is right
**and** nothing is invented.

**Workflow per run:** commit → `./run.sh NN-name` → judge every row whose Pass
is blank and write "yes" or "no" → `python check_run.py runs/NN-name.txt --rescore --write`
(fills in Score and Failed) → commit the log.

**Changed `answer_key.py`?** Re-check every old run the same way (no API call),
so all runs are scored by the same key. Your yes/no stays on rows that still
pass the automatic checks; a row that now fails becomes "no".

`run.sh` refuses to run with uncommitted changes to `parse_order.py`, saves the
output to `runs/NN-name.txt` (this calls the API), then `check_run.py` adds the
Summary row and a Run section below. In the Run table, each field from
`answer_key.py` is ✓ (right), ✗ (wrong) or – (not checked: the field didn't
exist yet in that run, or the message errored and has no output). Pass is
filled with "no" when any field is ✗ or the message errored. A blank
Pass means the automatic checks passed and it's your call: anything invented?
Product, spec and quantity right?

## Summary

| Run | Date       | Commit  | What changed                                                                                              | Score | Cost      | Failed              |
| --- | ---------- | ------- | --------------------------------------------------------------------------------------------------------- | ----- | --------- | ------------------- |
| 01 | 2026-11-25 | e40f4f8 | Baseline | 3/10 | $0.006057 | 1, 2, 3, 4, 6, 7, 8 |
| 02 | 2026-11-26 | 5d104ba | parse_order: typed date/time, time_of_day, closed unit list, conditional_order; improved unit description | 9/10 | $0.006421 | 6 |
| 03a | 2026-11-26 | 346d7de | parse_order: describe address field so a bare area counts | 10/10 | $0.006769 |  |

## Backlog

Quality wishes: worth improving, but they don't decide pass/fail.

- Msg 1 (run 01): question 3 (stock check) is for the admin, but it's worded
  as if asking the customer.
- Msg 2 (run 01): in "Semen Tiga Roda 50 kg", "50 kg" should be the spec, not
  part of the product name. The catalog lists it as the product name, so the
  fix starts in the catalog line.
- Msg 2, 3 (run 01): units aren't normalized ("biji" should be "pcs", "btg"
  should be "batang"). Define the store's units.
- Msg 2 (run 01): too many questions. Questions 4, 5 and 7 aren't needed, and
  3 and 6 can be merged.

## Run 01: baseline (e40f4f8)

Raw output: `runs/01-baseline.txt`

| # | intent | date | fulfillment | items | time | time_of_day | address | Pass | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | ✓ | ✓ | ✓ | ✓ | ✗ | – | ✓ | no | time: expected null, got "pagi" |
| 2 | ✓ | ✗ | ✓ | ✓ | ✓ | – | ✓ | no | date: expected "2026-11-23", got "Senin, 23 Nov 2026" |
| 3 | ✗ | ✓ | ✓ | ✓ | ✓ | – | ✓ | no | intent: expected "conditional_order", got "new_order" |
| 4 | ✓ | ✗ | ✓ | ✓ | ✓ | – | ✓ | no | date: expected "2026-11-19", got null |
| 5 | ✓ | ✓ | ✓ | ✓ | ✓ | – | ✓ | yes |  |
| 6 | ✓ | ✗ | ✓ | ✓ | ✗ | – | ✗ | no | date: expected "2026-11-20", got "Jumat, 20 Nov 2026"; time: expected null, got "sore"; address: expected text containing "Cijerah", got null |
| 7 | ✓ | ✗ | ✓ | ✓ | ✓ | – | ✓ | no | date: expected "2026-11-18", got null |
| 8 | ✓ | ✓ | ✓ | ✓ | ✗ | – | ✓ | no | time: expected null, got "siang" |
| 9 | ✓ | ✓ | ✓ | ✓ | ✓ | – | ✓ | yes |  |
| 10 | ✓ | ✓ | ✓ | ✓ | ✓ | – | ✓ | yes |  |

Fields: intent 9/10 · date 6/10 · fulfillment 10/10 · items 10/10 · time 7/10 · address 9/10

Tokens: 17,162 in / 8,682 out · cost $0.006057 · time ?

Pattern:

Next change:

## Run 02: typed-fields (5d104ba)

Raw output: `runs/02-typed-fields.txt`

| # | intent | date | fulfillment | items | time | time_of_day | address | Pass | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | yes |  |
| 2 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | yes |  |
| 3 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | yes |  |
| 4 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | yes |  |
| 5 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | yes |  |
| 6 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | no | address: expected text containing "Cijerah", got null |
| 7 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | yes |  |
| 8 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | yes |  |
| 9 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | yes |  |
| 10 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | yes |  |

Fields: intent 10/10 · date 10/10 · fulfillment 10/10 · items 10/10 · time 10/10 · time_of_day 10/10 · address 9/10

Tokens: 20,952 in / 8,651 out · cost $0.006421 · time 50s

Pattern:

Next change:

## Run 03a: address-new-rule (346d7de)

Raw output: `runs/03a-address-new-rule.txt`

| # | intent | date | fulfillment | items | time | time_of_day | address | Pass | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | yes |  |
| 2 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | yes |  |
| 3 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | yes |  |
| 4 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | yes |  |
| 5 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | yes |  |
| 6 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | yes |  |
| 7 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | yes |  |
| 8 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | yes |  |
| 9 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | yes |  |
| 10 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | yes |  |

Fields: intent 10/10 · date 10/10 · fulfillment 10/10 · items 10/10 · time 10/10 · time_of_day 10/10 · address 10/10

Tokens: 22,902 in / 8,957 out · cost $0.006769 · time 52s

Pattern:

Next change:
