"""Check a saved parse_order.py run against answer_key.py and record it in LOG.md.

No API call: this only reads the run file that parse_order.py already wrote.

    python check_run.py runs/02-dates.txt                     # print the log entry
    python check_run.py runs/02-dates.txt --write             # also add it to LOG.md
    python check_run.py runs/02-dates.txt --rescore           # preview a re-check
    python check_run.py runs/02-dates.txt --rescore --write   # apply it to LOG.md

It fills in the clerical parts of the log (date, commit, what changed, tokens,
cost, time) and marks every field in answer_key.py as passed or failed. A row
with a blank Pass column passed every automatic check and still needs your
judgment (anything invented? right product, spec and quantity?): write "yes"
or "no" there.

--rescore re-checks a run that is already in the log, for when answer_key.py
changed. On rows that still pass every automatic check it keeps your Pass
verdict and Notes. Then it recomputes that run's Score and Failed in the
Summary table (Score stays "?" until every row has a yes or no), so it is also
how you fill those two in after judging the rows. What changed, Pattern and
Next change are left as you wrote them.
"""
import argparse
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

from answer_key import EXPECTED, TODO, Contains

PROJECT = Path(__file__).resolve().parent
CODE_FILES = ("parse_order.py", "sample_messages.txt")  # the files that decide a run's output

MESSAGE_HEADER = re.compile(r"^===== message (\d+)/\d+ =====$", re.MULTILINE)
RUN_HEADER = re.compile(r"^commit: (\S+)\s+date: (\S+)$", re.MULTILINE)
ELAPSED = re.compile(r"^elapsed: (\d+)s$", re.MULTILINE)
TOTAL = re.compile(r"^TOTAL \(\d+ messages, (\d+) failed\): "
                   r"tokens: ([\d,]+) in / ([\d,]+) out\s+cost: \$([\d.]+)", re.MULTILINE)
UNCOUNTED = re.compile(r"^WARNING: total excludes (\d+) ", re.MULTILINE)
CELL_BORDER = re.compile(r"(?<!\\)\|")      # a | that isn't escaped as \| inside a cell
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


def row(cells):
    """One markdown table row."""
    return "| " + " | ".join(cells) + " |"


def split_row(line):
    """The cells of a markdown table row, as written (escaped pipes kept)."""
    return [c.strip() for c in CELL_BORDER.split(line.strip())[1:-1]]


def show(value):
    """A value written the way it appears in the JSON output."""
    if isinstance(value, set):
        return " or ".join(sorted(show(v) for v in value))
    if isinstance(value, Contains):
        return "text containing " + " and ".join(json.dumps(p, ensure_ascii=False)
                                                 for p in value.parts)
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


def matches(got, want):
    """Does one value from the output satisfy one answer-key value?"""
    if isinstance(want, set):
        return any(matches(got, option) for option in want)
    if isinstance(want, Contains):
        return isinstance(got, str) and all(p.lower() in got.lower() for p in want.parts)
    return got == want


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
        ok = matches(got, want)
        marks[field] = ok
        if not ok:
            notes.append(f"{label(field)}: expected {show(want)}, got {show(got)}")
    return marks, notes


def git(*args):
    """Run a git command in the project folder. Returns '' if it fails."""
    result = subprocess.run(["git", *args], cwd=PROJECT, capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else ""


def describe_changes(run_path, commit):
    """The subjects of the commits that changed the code since the previous run.

    The previous run is the last file in the same folder that sorts before this
    one and has a 'commit:' line. Only commits touching CODE_FILES count: an
    answer-key or log change doesn't change what the model produced."""
    earlier = sorted(p for p in run_path.parent.glob("*.txt") if p.name < run_path.name)
    for previous in reversed(earlier):
        header = RUN_HEADER.search(previous.read_text(encoding="utf-8"))
        if header:
            break
    else:
        return "Baseline"
    previous_commit, previous_number = header.group(1), previous.stem.partition("-")[0]
    for c in (previous_commit, commit):
        if not git("rev-parse", "--verify", "--quiet", f"{c}^{{commit}}"):
            return f"? (commit {c} not found)"
    subjects = git("log", "--reverse", "--format=%s", f"{previous_commit}..{commit}",
                   "--", *CODE_FILES)
    if not subjects:
        return f"No code change since run {previous_number} (repeat run)"
    return "; ".join(subjects.splitlines())


def score_run(run_path):
    """Check every message in a run file against the answer key."""
    text = run_path.read_text(encoding="utf-8")

    header = RUN_HEADER.search(text)
    if header:
        commit, run_date = header.groups()
    else:
        commit = git("rev-parse", "--short", "HEAD")
        run_date = date.fromtimestamp(run_path.stat().st_mtime).isoformat()
        print(f"note: {run_path.name} has no 'commit:' line, so assuming HEAD ({commit}) "
              f"and the file's date ({run_date})", file=sys.stderr)

    fields = columns()
    passed = {field: 0 for field in fields}
    checked = {field: 0 for field in fields}
    rows, errored = [], 0
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
        rows.append({
            "number": str(number),
            "marks": [MARKS[marks.get(field)] for field in fields],
            "pass": "no" if error or not all(marks.values()) else "",
            "notes": cell("; ".join(notes)),
        })

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
    return {"commit": commit, "date": run_date, "fields": fields, "rows": rows,
            "totals": totals, "usage": usage, "cost": cost,
            "number": run_number, "name": run_name}


def results_lines(run):
    """The results table, Fields line and Tokens line of a Run section."""
    names = [label(field) for field in run["fields"]]
    return [
        row(["#", *names, "Pass", "Notes"]),
        row(["---"] * (len(names) + 3)),
        *(row([r["number"], *r["marks"], r["pass"], r["notes"]]) for r in run["rows"]),
        "",
        f"Fields: {run['totals']}",
        "",
        run["usage"],
    ]


def score_and_failed(rows):
    """Score ("7/10", or "?/10" while a row has no yes/no) and the Failed list."""
    verdicts = [r["pass"].strip().lower() for r in rows]
    failed = ", ".join(r["number"] for r, v in zip(rows, verdicts) if v == "no")
    decided = all(v in ("yes", "no") for v in verdicts)
    score = f"{verdicts.count('yes')}/{len(rows)}" if decided else f"?/{len(rows)}"
    return score, failed


def build_entry(run_path):
    """Return (summary table row, run section) as markdown for a new run."""
    run = score_run(run_path)
    score, failed = score_and_failed(run["rows"])
    summary_row = row([run["number"], run["date"], run["commit"],
                       cell(describe_changes(run_path, run["commit"])),
                       score, f"${run['cost']}", failed])

    title = f"Run {run['number']}: {run['name']}" if run["name"] else f"Run {run['number']}"
    section = "\n".join([
        f"## {title} ({run['commit']})",
        "",
        f"Raw output: `runs/{run_path.name}`",
        "",
        *results_lines(run),
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
                 "not adding it twice (use --rescore to re-check it).")

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


def section_bounds(lines, start):
    """Index of the next '## ' heading after start, or the end of the file."""
    return next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")),
                len(lines))


def rescore(log_path, run_path):
    """Re-check a run that is already in the log. Returns (new log text, report)."""
    run = score_run(run_path)
    lines = log_path.read_text(encoding="utf-8").split("\n")

    marker = f"Raw output: `runs/{run_path.name}`"
    if marker not in lines:
        sys.exit(f"{log_path.name} has no entry for runs/{run_path.name}; "
                 "run without --rescore to add it.")
    start = lines.index(marker)
    end = section_bounds(lines, start)
    table = [i for i in range(start, end) if lines[i].startswith("|")]
    usage = [i for i in range(start, end) if lines[i].startswith("Tokens:")]
    if len(table) < 2 or not usage or usage[0] < table[0]:
        sys.exit(f"can't find the results table and Tokens line for "
                 f"runs/{run_path.name} in {log_path.name}")

    # What the log said before. A row with a ✗ or an ERROR got its "no" from this
    # script; any other row's Pass and Notes are yours.
    header = split_row(lines[table[0]])
    pass_col, notes_col = header.index("Pass"), header.index("Notes")
    before = {}
    for i in table[2:]:
        cells = split_row(lines[i])
        auto_failed = "✗" in cells[1:pass_col] or cells[notes_col].startswith("ERROR:")
        before[cells[0]] = (auto_failed, cells[pass_col], cells[notes_col])

    changes = []
    for r in run["rows"]:
        if r["number"] not in before:
            continue
        was_failed, old_pass, old_notes = before[r["number"]]
        now_failed = r["pass"] == "no"
        if not was_failed and not now_failed:
            r["pass"], r["notes"] = old_pass, old_notes
        elif not was_failed and now_failed:
            if old_notes:
                r["notes"] = f"{r['notes']}; {old_notes}"
            changes.append(f"message {r['number']} now fails: {r['notes']}")
        elif was_failed and not now_failed:
            changes.append(f"message {r['number']} now passes the automatic checks: "
                           "judge it and fill in Pass")

    lines[table[0]:usage[0] + 1] = results_lines(run)

    try:
        summary = lines.index("## Summary")
    except ValueError:
        sys.exit(f"no '## Summary' heading in {log_path.name}")
    summary_table = [i for i in range(summary, section_bounds(lines, summary))
                     if lines[i].startswith("|")]
    header = split_row(lines[summary_table[0]])
    score_col, failed_col = header.index("Score"), header.index("Failed")
    score, failed = score_and_failed(run["rows"])
    for i in summary_table[2:]:
        cells = split_row(lines[i])
        if cells[0] == run["number"]:
            changes.append(f"Score {cells[score_col] or '(blank)'} -> {score}, "
                           f"Failed {cells[failed_col] or '(none)'} -> {failed or '(none)'}")
            cells[score_col], cells[failed_col] = score, failed
            lines[i] = row(cells)
            break
    else:
        sys.exit(f"no row for run {run['number']} in the Summary table of {log_path.name}")

    report = "\n".join([f"Run {run['number']} ({run_path.name}):",
                        *(f"  {c}" for c in changes), "", *results_lines(run)])
    return "\n".join(lines), report


def main():
    parser = argparse.ArgumentParser(description="Check a saved run and log it")
    parser.add_argument("run_file", type=Path, help="e.g. runs/02-dates.txt")
    parser.add_argument("--write", action="store_true", help="change LOG.md (otherwise just print)")
    parser.add_argument("--rescore", action="store_true",
                        help="re-check a run that is already in the log (after changing answer_key.py)")
    parser.add_argument("--log", type=Path, default=PROJECT / "LOG.md", help="default: LOG.md")
    args = parser.parse_args()

    if args.rescore:
        new_text, report = rescore(args.log, args.run_file)
        print(report)
        if args.write:
            args.log.write_text(new_text, encoding="utf-8")
            print(f"Updated {args.log.name}.", file=sys.stderr)
        else:
            print("(preview only: add --write to update the log)", file=sys.stderr)
        return

    summary_row, section = build_entry(args.run_file)
    print("Summary row:\n" + summary_row + "\n\n" + section)
    if args.write:
        write_to_log(args.log, args.run_file, summary_row, section)
        print(f"Added to {args.log.name}.", file=sys.stderr)


if __name__ == "__main__":
    main()
