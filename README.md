# Gradebook Grader

A very simple single-page app: drop a gradebook export CSV onto `index.html`
and it prints each student's LT1-LT7 scores and A-F grade. All parsing and
grading happens locally in the browser (`grader.js`) — nothing is uploaded.

`gradebook_grader.py` is the original Python CLI the SPA was ported from; the
two implementations produce identical output. One test file,
`test_gradebook_grader.py`, covers the Python version's grading logic; the
JS port has its own copy of those same checks built into `grader.js`.

## Run the SPA locally

Open `index.html` directly in a browser (no server or build step needed),
or run the built-in self-tests by opening it with `?test=1` and checking
the browser console:

```
open index.html
open "index.html?test=1"
```

The same `?test=1` self-tests also run on the deployed GitHub Pages site —
open it and check the browser console for any assertion failures:

```
https://simple-kind.github.io/egi-gradebook-to-grades/?test=1
```

## Run the Python CLI locally

```
python gradebook_grader.py path/to/gradebook-export.csv
```

## Run the Python test

```
pip install pytest
pytest test_gradebook_grader.py
```
