const LT_PATTERN = /^LT\s*([1-7])$/i;
const EXEMPT = 'exempt';

/** Quote-aware CSV parser (handles "quoted,fields" and "escaped ""quotes""").
 *  Returns array of rows, each row an array of field strings. */
function parseCSV(text) {
  const rows = [];
  let row = [];
  let field = '';
  let inQuotes = false;
  let rowStart = 0;

  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (inQuotes) {
      if (c === '"') {
        if (text[i + 1] === '"') { field += '"'; i++; }
        else inQuotes = false;
      } else {
        field += c;
      }
    } else if (c === '"') {
      inQuotes = true;
    } else if (c === ',') {
      row.push(field);
      field = '';
    } else if (c === '\n' || c === '\r') {
      const raw = text.slice(rowStart, i);
      if (c === '\r' && text[i + 1] === '\n') i++;
      row.push(field);
      rows.push({ fields: row, raw });
      row = [];
      field = '';
      rowStart = i + 1;
    } else {
      field += c;
    }
  }
  if (field !== '' || row.length) {
    row.push(field);
    rows.push({ fields: row, raw: text.slice(rowStart) });
  }
  return rows.filter(r => r.fields.length > 1 || r.fields[0] !== '');
}

/** CSV text -> { students: Map<"first\u0000last", {1..7: rawGradeStr}>,
 *                lineText: Map<"first\u0000last", {1..7: rawCsvLineStr}> } */
function parseScores(csvText) {
  const rows = parseCSV(csvText);
  const header = rows[0].fields;
  const col = name => header.indexOf(name);
  const titleCol = col('Assignment Title');
  const firstCol = col('First Name');
  const lastCol = col('Last Name');
  const gradeCol = col('Grade');

  const students = new Map();
  const lineText = new Map();
  for (let i = 1; i < rows.length; i++) {
    const { fields: r, raw } = rows[i];
    const match = LT_PATTERN.exec((r[titleCol] || '').trim());
    if (!match) continue;
    const key = `${r[firstCol]}\u0000${r[lastCol]}`;
    if (!students.has(key)) {
      students.set(key, {});
      lineText.set(key, {});
    }
    const lt = Number(match[1]);
    students.get(key)[lt] = (r[gradeCol] || '').trim();
    lineText.get(key)[lt] = raw;
  }
  return { students, lineText };
}

/** raw grade string (or undefined if the LT row is missing) -> number 0-4, or EXEMPT */
function normalizeScore(raw) {
  if (!raw || raw.toLowerCase() === EXEMPT) return EXEMPT;
  const n = parseFloat(raw);
  if (Number.isNaN(n)) throw new Error(`could not convert grade to a number: '${raw}'`);
  return n;
}

/** scores: 7 values (number or EXEMPT) in LT1..LT7 order -> 'A'-'F', or null if all exempt */
function letterGrade(scores) {
  const graded = scores.filter(s => s !== EXEMPT);
  if (!graded.length) return null;
  const pct2 = graded.filter(s => s >= 2).length / graded.length;
  const pct3 = graded.filter(s => s >= 3).length / graded.length;
  if (pct2 === 1 && pct3 >= 0.66) return 'A';
  if (pct2 === 1 && pct3 >= 0.5) return 'B';
  if (pct2 >= 0.66) return 'C';
  if (pct2 >= 0.5) return 'D';
  return 'F';
}

/** Matches Python's f'{s:g}': shortest round-trip representation, no trailing zeros. */
function formatNumber(n) {
  return String(n);
}

/** ltScores: {1..7: raw grade str}, missing keys allowed -> one formatted output line.
 *  lineText: {1..7: raw csv line str}, included in the error if a grade won't parse. */
function formatStudentLine(first, last, ltScores, lineText = {}) {
  const scores = [];
  for (let i = 1; i <= 7; i++) {
    try {
      scores.push(normalizeScore(ltScores[i]));
    } catch (err) {
      const text = lineText[i];
      const suffix = text ? `\n  CSV line: ${text}` : '';
      throw new Error(`${first} ${last}, LT ${i}: ${err.message}${suffix}`);
    }
  }
  const display = scores.map(s => (s === EXEMPT ? '-' : formatNumber(s)));
  const grade = letterGrade(scores) || 'N/A';
  return `${first} ${last}: ${display.join(', ')} -> ${grade}`;
}

/** Self-check mirroring test_gradebook_grader.py. Run via index.html?test=1. */
function runSelfTests() {
  console.assert(normalizeScore('') === EXEMPT, 'normalizeScore empty');
  console.assert(normalizeScore('Exempt') === EXEMPT, 'normalizeScore Exempt');
  console.assert(normalizeScore('exempt') === EXEMPT, 'normalizeScore exempt');
  console.assert(normalizeScore('3') === 3, 'normalizeScore 3');
  console.assert(normalizeScore('2.5') === 2.5, 'normalizeScore 2.5');

  const cases = [
    [[2.0, 2.5, 3.0, EXEMPT, EXEMPT, EXEMPT, EXEMPT], 'C'],
    [[2.5, 3.0, 3.0, EXEMPT, EXEMPT, EXEMPT, EXEMPT], 'A'],
    [[3.0, 3.0, 3.0, EXEMPT, EXEMPT, EXEMPT, EXEMPT], 'A'],
    [[2, 2, 0, EXEMPT, EXEMPT, EXEMPT, EXEMPT], 'C'],
    [[2, 0, 0, EXEMPT, EXEMPT, EXEMPT, EXEMPT], 'F'],
    [[2, 2, 0, 0, EXEMPT, EXEMPT, EXEMPT], 'D'],
    [[0.0, 0.0, 0.0, EXEMPT, EXEMPT, EXEMPT, EXEMPT], 'F'],
    [[EXEMPT, EXEMPT, EXEMPT, EXEMPT, EXEMPT, EXEMPT, EXEMPT], null],
  ];
  for (const [scores, expected] of cases) {
    console.assert(letterGrade(scores) === expected, 'letterGrade', scores, 'expected', expected);
  }

  console.assert(
    formatStudentLine('Amelia', 'Earhart', {1: '2', 3: '2.5', 4: '3'})
      === 'Amelia Earhart: 2, -, 2.5, 3, -, -, - -> C',
    'formatStudentLine missing LTs'
  );
  console.assert(
    formatStudentLine('New', 'Student', {}) === 'New Student: -, -, -, -, -, -, - -> N/A',
    'formatStudentLine no grades'
  );

  const csv = [
    'Unique User ID,First Name,Last Name,Email,Course Name,Course Code,Department Code,Section Name,Section Code,Assignment Title,Assignment Due Date,Max Points,Grade,Grading Category,Username,Accommodations Offered/Received,Collected,Count in Grade',
    'id,Amelia,Earhart,e@x.com,COURSE,C1,,SEC,,Initial Sea Otter Model LT 1,,4,3,LT,user,False,False,True',
    'id,Amelia,Earhart,e@x.com,COURSE,C1,,SEC,,LT 1,,4,2,LT,user,False,False,True',
    'id,Amelia,Earhart,e@x.com,COURSE,C1,,SEC,,Lt 7,,4,4,LT,user,False,False,True',
  ].join('\n');
  const { students } = parseScores(csv);
  const parsed = students.get('Amelia\u0000Earhart');
  console.assert(
    parsed && parsed[1] === '2' && parsed[7] === '4' && Object.keys(parsed).length === 2,
    'parseScores ignores non-exact LT-n rows', parsed
  );

  try {
    formatStudentLine('Amelia', 'Earhart', {1: 'Missing'}, {1: 'the,raw,row'});
    console.assert(false, 'formatStudentLine should have thrown on unparseable grade');
  } catch (err) {
    console.assert(
      /Amelia Earhart, LT 1:/.test(err.message) && /CSV line: the,raw,row/.test(err.message),
      'formatStudentLine error should name the student/LT and include the CSV line', err.message
    );
  }

  console.log('grader.js self-tests done (see any assertion failures above)');
}

/** CSV text -> full plain-text report, same output as gradebook_grader.py */
function gradeCSV(csvText) {
  const { students, lineText } = parseScores(csvText);
  const keys = [...students.keys()];
  keys.sort((ka, kb) => {
    const [fa, la] = ka.split('\u0000');
    const [fb, lb] = kb.split('\u0000');
    return la !== lb ? la.localeCompare(lb) : fa.localeCompare(fb);
  });
  return keys
    .map(key => {
      const [first, last] = key.split('\u0000');
      return formatStudentLine(first, last, students.get(key), lineText.get(key)) + '\n';
    })
    .join('');
}
