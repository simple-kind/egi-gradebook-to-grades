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
    """Return {(first, last): {lt_num: raw_grade_str}} from the LT1-LT7 summary rows."""
    students = defaultdict(dict)
    with open(csv_path, newline='') as f:
        for row in csv.DictReader(f):
            match = LT_PATTERN.match(row['Assignment Title'].strip())
            if not match:
                continue
            key = (row['First Name'], row['Last Name'])
            students[key][int(match.group(1))] = row['Grade'].strip()
    return students


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


def format_student_line(first, last, lt_scores):
    """lt_scores: {1..7: raw grade str}, missing keys allowed. One formatted output line."""
    scores = [normalize_score(lt_scores.get(i)) for i in range(1, 8)]
    display = [f'{s:g}' if s != EXEMPT else '-' for s in scores]
    grade = letter_grade(scores) or 'N/A'
    return f"{first} {last}: {', '.join(display)} -> {grade}"


def main(csv_path):
    students = parse_scores(csv_path)
    for first, last in sorted(students, key=lambda key: (key[1], key[0])):
        print(format_student_line(first, last, students[(first, last)]))


if __name__ == '__main__':
    main(sys.argv[1])
