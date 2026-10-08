import csv

import pytest

from gradebook_grader import (
    EXEMPT,
    format_student_line,
    letter_grade,
    normalize_score,
    parse_scores,
)

CSV_HEADER = [
    'Unique User ID', 'First Name', 'Last Name', 'Email', 'Course Name',
    'Course Code', 'Department Code', 'Section Name', 'Section Code',
    'Assignment Title', 'Assignment Due Date', 'Max Points', 'Grade',
    'Grading Category', 'Username', 'Accommodations Offered/Received',
    'Collected', 'Count in Grade',
]


def write_csv(path, rows):
    with open(path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(CSV_HEADER)
        for first, last, title, grade in rows:
            w.writerow(['id', first, last, 'e@x.com', 'COURSE', 'C1', '', 'SEC', '',
                        title, '', '4', grade, 'LT', 'user', 'False', 'False', 'True'])


def test_normalize_score():
    assert normalize_score('') == EXEMPT
    assert normalize_score('Exempt') == EXEMPT
    assert normalize_score('exempt') == EXEMPT
    assert normalize_score('3') == 3.0
    assert normalize_score('2.5') == 2.5


@pytest.mark.parametrize('scores,expected', [
    ([2.0, 2.5, 3.0, EXEMPT, EXEMPT, EXEMPT, EXEMPT], 'C'),   # Amelia: pct2=1, pct3=.33
    ([2.5, 3.0, 3.0, EXEMPT, EXEMPT, EXEMPT, EXEMPT], 'A'),   # Adrian: pct2=1, pct3=.67
    ([3.0, 3.0, 3.0, EXEMPT, EXEMPT, EXEMPT, EXEMPT], 'A'),
    ([2, 2, 0, EXEMPT, EXEMPT, EXEMPT, EXEMPT], 'C'),         # pct2=.67 -> C
    ([2, 0, 0, EXEMPT, EXEMPT, EXEMPT, EXEMPT], 'F'),         # pct2=.33
    ([2, 2, 0, 0, EXEMPT, EXEMPT, EXEMPT], 'D'),              # pct2=.5
    ([0.0, 0.0, 0.0, EXEMPT, EXEMPT, EXEMPT, EXEMPT], 'F'),
    ([EXEMPT] * 7, None),
])
def test_letter_grade(scores, expected):
    assert letter_grade(scores) == expected


def test_parse_scores_ignores_non_lt_rows(tmp_path):
    csv_path = tmp_path / 'g.csv'
    write_csv(csv_path, [
        ('Amelia', 'Earhart', 'Initial Sea Otter Model LT 1', '3'),  # not an exact LT-n row
        ('Amelia', 'Earhart', 'LT 1', '2'),
        ('Amelia', 'Earhart', 'Lt 7', '4'),
    ])
    students, _ = parse_scores(csv_path)
    assert students[('Amelia', 'Earhart')] == {1: '2', 7: '4'}


def test_format_student_line_raises_with_csv_line_on_bad_grade():
    with pytest.raises(ValueError, match=r"(?s)Amelia Earhart, LT 1:.*CSV line: the,raw,row"):
        format_student_line('Amelia', 'Earhart', {1: 'Missing'}, {1: 'the,raw,row'})


def test_format_student_line_missing_lt_shown_as_dash():
    line = format_student_line('Amelia', 'Earhart', {1: '2', 3: '2.5', 4: '3'})
    assert line == 'Amelia Earhart: 2, -, 2.5, 3, -, -, - -> C'


def test_format_student_line_no_grades_yet():
    line = format_student_line('New', 'Student', {})
    assert line == 'New Student: -, -, -, -, -, -, - -> N/A'
