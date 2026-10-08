"""Convert a gradebook CSV export into per-student LT1-LT7 proficiency lines with an A-F grade.

Reads each student's "LT 1".."LT 7" summary-assignment grades and reproduces the
weighting formula from the "far right" formula block in GP 2 2026-2027.xlsx:
    pct_2 = fraction of graded LTs scoring >= 2
    pct_3 = fraction of graded LTs scoring >= 3
    A: pct_2 == 1 and pct_3 >= .66   B: pct_2 == 1 and pct_3 >= .5
    C: pct_2 >= .66                 D: pct_2 >= .5                F: otherwise
Blank grades and LTs with no row at all are "exempt" (excluded from the denominator),
same as the manual "exempt" entries in the existing spreadsheet.
"""
import csv
import re
import sys
from collections import defaultdict

LT_PATTERN = re.compile(r'^LT\s*([1-7])$', re.IGNORECASE)
EXEMPT = 'exempt'


def parse_scores(csv_path):
    """Return (students, line_text) from the LT1-LT7 summary rows.

    students: {(first, last): {lt_num: raw_grade_str}}
    line_text: {(first, last): {lt_num: raw_csv_line_str}}, for error messages.
    """
    students = defaultdict(dict)
    line_text = defaultdict(dict)
    with open(csv_path, newline='') as f:
        raw_lines = f.readlines()
        f.seek(0)
        reader = csv.DictReader(f)
        for row in reader:
            match = LT_PATTERN.match(row['Assignment Title'].strip())
            if not match:
                continue
            key = (row['First Name'], row['Last Name'])
            lt = int(match.group(1))
            students[key][lt] = row['Grade'].strip()
            # ponytail: assumes one physical line per CSV row (true for this export);
            # a quoted multi-line field would desync this lookup from reader.line_num.
            line_text[key][lt] = raw_lines[reader.line_num - 1].rstrip('\n')
    return students, line_text


def normalize_score(raw):
    """raw grade string (or None if the LT row is missing) -> float 0-4, or EXEMPT."""
    if not raw or raw.lower() == EXEMPT:
        return EXEMPT
    return float(raw)


def letter_grade(scores):
    """scores: 7 values (float or EXEMPT) in LT1..LT7 order -> 'A'-'F', or None if all exempt."""
    graded = [s for s in scores if s != EXEMPT]
    if not graded:
        return None
    pct_2 = sum(s >= 2 for s in graded) / len(graded)
    pct_3 = sum(s >= 3 for s in graded) / len(graded)
    if pct_2 == 1 and pct_3 >= 0.66:
        return 'A'
    if pct_2 == 1 and pct_3 >= 0.5:
        return 'B'
    if pct_2 >= 0.66:
        return 'C'
    if pct_2 >= 0.5:
        return 'D'
    return 'F'


def format_student_line(first, last, lt_scores, line_text=None):
    """lt_scores: {1..7: raw grade str}, missing keys allowed. One formatted output line.

    line_text: {1..7: raw csv line str}, included in the error if a grade won't parse.
    """
    line_text = line_text or {}
    scores = []
    for i in range(1, 8):
        try:
            scores.append(normalize_score(lt_scores.get(i)))
        except ValueError as e:
            text = line_text.get(i)
            suffix = f'\n  CSV line: {text}' if text else ''
            raise ValueError(f'{first} {last}, LT {i}: {e}{suffix}') from e
    display = [f'{s:g}' if s != EXEMPT else '-' for s in scores]
    grade = letter_grade(scores) or 'N/A'
    return f"{first} {last}: {', '.join(display)} -> {grade}"


def main(csv_path):
    students, line_text = parse_scores(csv_path)
    for first, last in sorted(students, key=lambda key: (key[1], key[0])):
        key = (first, last)
        print(format_student_line(first, last, students[key], line_text.get(key)))


if __name__ == '__main__':
    main(sys.argv[1])
