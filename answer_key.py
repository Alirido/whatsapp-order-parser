"""Answer key for check_run.py: what a correct parse of each sample message has.

This is the eval-design part, so it's yours to fill in from expected.md.

For each message, list the fields to check by exact match:
  - any top-level field of ParsedMessage: "intent", "date", "fulfillment",
    "phone", "address", ...
  - "item_count": how many entries `items` should have

Values:
  - a plain value must match exactly: "2026-11-19", None (= null), 2
  - a set accepts any of its members: {"question", "new_order"}
  - TODO means "not decided yet", so the field is skipped

Leave a field out entirely when you'd rather judge it by hand.
"""

TODO = object()

# time / time_of_day: a None here is also an invention check (no time was given,
# so the model must not make one up).
EXPECTED = {
    1:  {"intent": "new_order", "date": "2026-11-19", "fulfillment": "delivery", "item_count": 2,
         "time": None, "time_of_day": "pagi"},
    2:  {"intent": "new_order", "date": "2026-11-23", "fulfillment": "delivery", "item_count": 3,
         "time": None, "time_of_day": None},
    3:  {"intent": "conditional_order", "date": None, "fulfillment": "unknown", "item_count": 1,
         "time": None, "time_of_day": None},
    4:  {"intent": "question", "date": None, "fulfillment": "unknown", "item_count": 0,
         "time": None, "time_of_day": None},
    5:  {"intent": "change_order", "date": None, "fulfillment": "unknown", "item_count": 1,
         "time": None, "time_of_day": None},
    6:  {"intent": "new_order", "date": "2026-11-20", "fulfillment": "delivery", "item_count": 3,
         "time": None, "time_of_day": "sore"},
    7:  {"intent": "new_order", "date": "2026-11-18", "fulfillment": "pickup", "item_count": 2,
         "time": "14:00", "time_of_day": {None, "siang"}},  # "jam 2 siang": siang is optional here
    8:  {"intent": "new_order", "date": "2026-11-19", "fulfillment": "delivery", "item_count": 3,
         "time": None, "time_of_day": "siang"},
    9:  {"intent": "new_order", "date": "2026-11-18", "fulfillment": "delivery", "item_count": 2,
         "time": None, "time_of_day": None},
    10: {"intent": "new_order", "date": None, "fulfillment": "delivery", "item_count": 1,
         "time": None, "time_of_day": None},
}
