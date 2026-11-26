"""Check a saved parse_order.py run against answer_key.py and add it to LOG.md.

No API call: this only reads the run file that parse_order.py already wrote.

    python check_run.py runs/02-dates.txt           # print the log entry
    python check_run.py runs/02-dates.txt --write   # also add it to LOG.md

It fills in the clerical parts of the log (date, commit, what changed, tokens,
cost, time) and marks every field in answer_key.py as passed or failed. A row
with a blank Pass column passed every automatic check and still needs your
judgment (anything invented? right product, spec and quantity?).
"""
import argparse
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

from answer_key import EXPECTED, TODO

PROJECT = Path(__file__).resolve().parent

MESSAGE_HEADER = re.compile(r"^===== message (\d+)/\d+ =====$", re.MULTILINE)
RUN_HEADER = re.compile(r"^commit: (\S+)\s+date: (\S+)$", re.MULTILINE)
ELAPSED = re.compile(r"^elapsed: (\d+)s$", re.MULTILINE)
TOTAL = re.compile(r"^TOTAL \(\d+ messages, (\d+) failed\): "
                   r"tokens: ([\d,]+) in / ([\d,]+) out\s+cost: \$([\d.]+)", re.MULTILINE)
UNCOUNTED = re.compile(r"^WARNING: total excludes (\d+) ", re.MULTILINE)
LABELS = {"item_count": "items"}           # shorter column names
MARKS = {True: "✓", False: "✗", None: "–"}  # – = not checked for this message


def read_messages(run_text):
    """Return {message number: (parsed dict or None, error text or None)}."""
    headers = list(MESSAGE_HEADER.finditer(run_text))
    results = {}
    for i, header in enumerate(headers):
        end = headers[i + 1].start() if i + 1 < len(headers) else len(run_text)
        block = run_text[header.end():end]
        number = int(header.group(1))
        json_start = re.search(r"^\{$", block, re.MULTILINE)
        if json_start:
            parsed, _ = json.JSONDecoder().raw_decode(block, json_start.start())
            results[number] = (parsed, None)
        else:
            error = re.search(r"^ERROR: (.*)$", block, re.MULTILINE)
            results[number] = (None, error.group(1) if error else "no JSON in the run file")
    return results


def cell(text):
    """Make text safe inside a markdown table cell."""
    return str(text).replace("|", "\\|")


def show(value):
    """A value written the way it appears in the JSON output."""
    if isinstance(value, set):
        return " or ".join(sorted(show(v) for v in value))
    return json.dumps(value, ensure_ascii=False)


def label(field):
    return LABELS.get(field, field)


def key_for(number):
    """The decided (non-TODO) part of one message's answer key."""
    return {field: want for field, want in EXPECTED.get(number, {}).items() if want is not TODO}


def columns():
    """Every field the answer key checks, in first-seen order."""
    fields = []
    for number in EXPECTED:
        fields += [field for field in key_for(number) if field not in fields]
    return fields


def check(number, parsed):
    """Compare one parsed message with its answer key.

    Returns ({field: True/False}, [notes on the failures]). A field missing from
    the output is skipped: the run was made before that field existed."""
    marks, notes = {}, []
    for field, want in key_for(number).items():
        if field == "item_count":
            got = len(parsed["items"])
        elif field in parsed:
            got = parsed[field]
        else:
            continue
        ok = got in want if isinstance(want, set) else got == want
        marks[field] = ok
        if not ok:
            notes.append(f"{label(field)}: expected {show(want)}, got {show(got)}")
    return marks, notes


def git(*args):
    """Run a git command in the project folder. Returns '' if it fails."""
    result = subprocess.run(["git", *args], cwd=PROJECT, capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else ""


def build_entry(run_path):
    """Return (summary table row, run section) as markdown."""
    text = run_path.read_text(encoding="utf-8")

    header = RUN_HEADER.search(text)
    if header:
        commit, run_date = header.groups()
    else:
        commit = git("rev-parse", "--short", "HEAD")
        run_date = date.fromtimestamp(run_path.stat().st_mtime).isoformat()
        print(f"note: {run_path.name} has no 'commit:' line, so assuming HEAD ({commit}) "
              f"and the file's date ({run_date})", file=sys.stderr)
    what_changed = git("log", "-1", "--format=%s", commit)

    fields = columns()
    passed = {field: 0 for field in fields}
    checked = {field: 0 for field in fields}
    rows, failed, errored = [], [], 0
    for number, (parsed, error) in sorted(read_messages(text).items()):
        if error:
            # No output to check: leave the fields out of the per-field totals,
            # so one bad reply doesn't look like an intent/date/... mistake.
            errored += 1
            marks = {}
            notes = [f"ERROR: {error}"]
        else:
            marks, notes = check(number, parsed)
        for field, ok in marks.items():
            checked[field] += 1
            passed[field] += ok
        if error or not all(marks.values()):
            failed.append(number)
            verdict = "no"
        else:
            verdict = ""
        cells = [MARKS[marks.get(field)] for field in fields]
        rows.append("| " + " | ".join([str(number), *cells, verdict, cell("; ".join(notes))]) + " |")

    total = TOTAL.search(text)
    if total:
        failed_calls, tokens_in, tokens_out, cost = total.groups()
        usage = f"Tokens: {tokens_in} in / {tokens_out} out · cost ${cost}"
        if failed_calls != "0":
            uncounted = UNCOUNTED.search(text)
            usage += (f" ({failed_calls} calls failed, see the run file"
                      + (f"; {uncounted.group(1)} of them billed but not in this total)"
                         if uncounted else ")"))
    else:
        cost = "?"
        usage = "Tokens: ? (no TOTAL line: did the run finish?)"
    elapsed = ELAPSED.search(text)
    usage += f" · time {elapsed.group(1)}s" if elapsed else " · time ?"

    totals = " · ".join(f"{label(field)} {passed[field]}/{checked[field]}"
                        for field in fields if checked[field])
    if errored:
        totals += f" · {errored} message(s) errored, not counted in these"

    run_number, _, run_name = run_path.stem.partition("-")
    failed_list = ", ".join(str(n) for n in failed)
    summary_row = (f"| {run_number} | {run_date} | {commit} | {cell(what_changed)} "
                   f"| ?/{len(rows)} | ${cost} | {failed_list} |")

    title = f"Run {run_number}: {run_name}" if run_name else f"Run {run_number}"
    names = [label(field) for field in fields]
    section = "\n".join([
        f"## {title} ({commit})",
        "",
        f"Raw output: `runs/{run_path.name}`",
        "",
        "| " + " | ".join(["#", *names, "Pass", "Notes"]) + " |",
        "| " + " | ".join(["---"] * (len(names) + 3)) + " |",
        *rows,
        "",
        f"Fields: {totals}",
        "",
        usage,
        "",
        "Pattern:",
        "",
        "Next change:",
        "",
    ])
    return summary_row, section


def write_to_log(log_path, run_path, summary_row, section):
    """Add the summary row to the Summary table and append the run section."""
    text = log_path.read_text(encoding="utf-8")
    if f"`runs/{run_path.name}`" in text:
        sys.exit(f"{log_path.name} already has an entry for runs/{run_path.name}; "
                 "not adding it twice.")

    lines = text.split("\n")
    try:
        i = lines.index("## Summary") + 1
    except ValueError:
        sys.exit(f"no '## Summary' heading in {log_path.name}")
    while i < len(lines) and not lines[i].startswith(("|", "## ")):
        i += 1
    if i == len(lines) or not lines[i].startswith("|"):
        sys.exit(f"no table under '## Summary' in {log_path.name}")
    while i < len(lines) and lines[i].startswith("|"):
        i += 1
    lines.insert(i, summary_row)

    log_path.write_text("\n".join(lines).rstrip("\n") + "\n\n" + section, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Check a saved run and log it")
    parser.add_argument("run_file", type=Path, help="e.g. runs/02-dates.txt")
    parser.add_argument("--write", action="store_true", help="add the entry to the log")
    parser.add_argument("--log", type=Path, default=PROJECT / "LOG.md", help="default: LOG.md")
    args = parser.parse_args()

    summary_row, section = build_entry(args.run_file)
    print("Summary row:\n" + summary_row + "\n\n" + section)
    if args.write:
        write_to_log(args.log, args.run_file, summary_row, section)
        print(f"Added to {args.log.name}.", file=sys.stderr)


if __name__ == "__main__":
    main()
