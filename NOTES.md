# Project notes

Working notes kept section by section. These are the raw decisions and the
reasoning behind them — the README (Section 9) is written from this file.

Project: Smart Fitness Session Analyzer (Option A)
Author: Jonathan Christensen
Student number: jonathan4495
Repository: https://github.com/jonathan4495/fitness-session-analyzer
  (GitHub account name to be confirmed — see Section 0 open questions)

---

## Section 0 — Setup

**What was done**

Created the repository folder `fitness-session-analyzer` with the five files
the assignment asks for (`README.md`, `main.py`, `sample_data.py`, `tests.py`,
`requirements.txt`), plus this notes file and a `.gitignore`. Initialised git.
No program logic written yet.

**Decisions and why**

| Decision | Why |
| --- | --- |
| Files contain a short docstring placeholder rather than being truly empty | An empty `tests.py` makes `python -m unittest tests.py` fail, and an empty `main.py` gives no sign the project runs. Placeholders mean both commands work from day one, so a broken run always means *my* bug, not a missing file. |
| `requirements.txt` states "standard library only" as a comment | The assignment allows this. A comment explains *why* the file is otherwise empty, which an empty file does not. |
| Added `.gitignore` even though it is not in the required file list | Stops `__pycache__/` and editor files being committed. Without it the repository fills with generated files that are not my work. |
| Class code will live in its own module, not inside `main.py` | Proposed in Section 1 — `main.py` stays a thin entry point that only runs scenarios and prints. Keeps the "run with `python3 main.py`" requirement clean. **Still to be approved.** |

**Alternatives rejected**

- *Putting every class in `main.py`* — would satisfy the file list, but mixes
  the program's logic with the code that runs it, and makes `tests.py` import
  the file whose whole job is to print reports. Rejected in favour of a
  separate module (to confirm in Section 1).
- *Creating truly empty files* — matches "empty files" literally, but see above.

**Open questions**

- `jonathan4495` is the student number. Whether the GitHub account uses the
  same name is not yet confirmed — the clone URL in the README (Section 9) and
  the push in Section 10 both depend on the answer.
- Whether class code may live in its own module alongside the five required
  files. Assumed yes; to be approved in Section 1.

**Environment note**

Git was not installed on this machine; installed it during this section.
Python on this machine is 3.14.3, and the command is `python` (not `python3`) —
`python3` in the assignment instructions is the macOS/Linux spelling. The README
will document both.
