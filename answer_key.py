"""Answer key for check_run.py: what a correct parse of each sample message has.

This is the eval-design part, so it's yours to fill in from expected.md.

For each message, list the fields to check by exact match:
  - any top-level field of ParsedMessage: "intent", "date", "fulfillment",
    "phone", "address", ...
  - "item_count": how many entries `items` should have

Values:
  - a plain value must match exactly: "2026-11-19", None (= null), 2
  - a set accepts any of its members: {"question", "new_order"}
  - Contains("Setiabudi", "210") accepts text that contains every part,
    ignoring case ("Jl. Setiabudi No. 210" passes; "Jl. Setiabudi" and null
    fail). It can go in a set too: {None, Contains("Setiabudi")}
  - TODO means "not decided yet", so the field is skipped

Leave a field out entirely when you'd rather judge it by hand.
After changing this file, re-check old runs without calling the API:
    python check_run.py runs/NN-name.txt --rescore --write
"""
TODO = object()


class Contains:
    """Text containing every one of these parts, ignoring case."""

    def __init__(self, *parts):
        self.parts = parts

    def __eq__(self, other):
        return isinstance(other, Contains) and self.parts == other.parts

    def __hash__(self):  # so it can sit inside a set
        return hash(self.parts)

# time / time_of_day: a None here is also an invention check (no time was given,
# so the model must not make one up).
#
# address:
#   - a street address must keep its street and house number (1, 2, 8)
#   - an area with no street (6, 9) goes in address as-is; a question asks for
#     the full address. Contains can't tell the area from an invented street
#     ("Jl. Cijerah No. 12" would pass), so that part is still judged by hand.
#   - None = the customer gave no address, so none may be invented. 7 is a pickup;
#     10's "alamat biasa" (the usual address) isn't in the message.
EXPECTED = {
    1:  {"intent": "new_order", "date": "2026-11-19", "fulfillment": "delivery", "item_count": 2,
         "time": None, "time_of_day": "morning", "address": Contains("Gegerkalong Hilir", "45")},
    2:  {"intent": "new_order", "date": "2026-11-23", "fulfillment": "delivery", "item_count": 3,
         "time": None, "time_of_day": None, "address": Contains("Setiabudi", "210")},
    3:  {"intent": "conditional_order", "date": None, "fulfillment": "unknown", "item_count": 1,
         "time": None, "time_of_day": None, "address": None},
    4:  {"intent": "question", "date": "2026-11-19", "fulfillment": "unknown", "item_count": 0,
         "time": None, "time_of_day": None, "address": None},
    5:  {"intent": "change_order", "date": None, "fulfillment": "unknown", "item_count": 1,
         "time": None, "time_of_day": None, "address": None},
    6:  {"intent": "new_order", "date": "2026-11-20", "fulfillment": "delivery", "item_count": 3,
         "time": None, "time_of_day": "afternoon", "address": Contains("Cijerah")},
    7:  {"intent": "new_order", "date": "2026-11-18", "fulfillment": "pickup", "item_count": 2,
         "time": "14:00", "time_of_day": {None, "midday"},  # "jam 2 siang": midday is optional here
         "address": None},
    8:  {"intent": "new_order", "date": "2026-11-19", "fulfillment": "delivery", "item_count": 3,
         "time": None, "time_of_day": "midday", "address": Contains("Sukajadi", "88")},
    9:  {"intent": "new_order", "date": "2026-11-18", "fulfillment": "delivery", "item_count": 2,
         "time": None, "time_of_day": None, "address": Contains("Dago")},
    10: {"intent": "new_order", "date": None, "fulfillment": "delivery", "item_count": 1,
         "time": None, "time_of_day": None, "address": None},
}
