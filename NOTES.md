# Project notes

Working notes kept section by section. These are the raw decisions and the
reasoning behind them — the README (Section 9) is written from this file.

Project: Smart Fitness Session Analyzer (Option A)
Author: Jonathan Christensen
Student number: jonathan4495
GitHub account: Jonnyyyc
Repository: https://github.com/Jonnyyyc/fitness-session-analyzer

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

**Resolved**

- `jonathan4495` is the student number, **not** the GitHub account name. The
  GitHub account is `Jonnyyyc`, so the clone URL used in the README (Section 9)
  and the push in Section 10 is
  `https://github.com/Jonnyyyc/fitness-session-analyzer.git`.

- Class code goes in its own module, `analyzer.py`, alongside the five required
  files. Approved. `main.py` stays a thin entry point that only builds the
  scenarios and prints reports, so `tests.py` can import the classes without
  pulling in the printing code.

**Environment note**

Git was not installed on this machine; installed it during this section.
Python on this machine is 3.14.3, and the command is `python` (not `python3`) —
`python3` in the assignment instructions is the macOS/Linux spelling. The README
will document both.

---

## Section 1 — Design plan

Approved with four changes (recorded under "Corrections" below). No code written
in this section.

### Classes

| Class | Responsibility |
| --- | --- |
| `Participant` | Who the person is, plus their reference values (resting heart rate, normal skin temperature). Converts a resting heart rate into the bands that count as elevated / high **for that person**. |
| `Athlete(Participant)` | Same role, different bands. Overrides `heart_rate_bands()`. |
| `Observation` | A single sensor reading — the six-field record from the brief. |
| `Session` | One recording: one `Participant` plus a list of `Observation`s. Separates usable from rejected readings and produces the result dictionary. |

Four classes, deliberately. A separate `Validator` or `Report` class was rejected:
each would hold no data and expose one method, which is a plain function with
extra ceremony around it.

### Where each required concept is demonstrated

| Concept | Location | Reasoning |
| --- | --- | --- |
| Composition | `Session` holds a `Participant` and a list of `Observation`s | A session is not a kind of participant; it *contains* one. |
| Private attribute + `@property` | `Participant._resting_heart_rate`, read via the `resting_heart_rate` property | Every comparison in the program divides by this value, so a zero or negative would break the arithmetic. The property is the checked gate that stops it. |
| Inheritance + overriding | `Athlete.heart_rate_bands()` overrides `Participant.heart_rate_bands()` | Same question, genuinely different answer — see "Athlete thresholds" below. |
| `@classmethod` | `Observation.from_dict(raw)` | An alternative constructor. The program's real input format is the dict from the brief, so building straight from one is the natural entry point. |

### Standalone functions (all in `analyzer.py`)

| Function | Kind | Purpose |
| --- | --- | --- |
| `validate_observation(raw)` | validation | The single place the rules live. Returns whether a raw record is acceptable and a plain-English reason when it is not. |
| `summarise(observations)` | calculation | Average, minimum, maximum per measurement. |
| `compare_to_reference(summary, participant)` | calculation | Distance from the participant's own normal values. |
| `detect_recovery(observations)` | calculation | Did heart rate **and** activity both fall near the end? |
| `format_report(result)` | presentation | Result dictionary → readable console text. |

Five, against a required minimum of four.

### Validation rules

Rejected (discarded, not counted as usable):

| Problem | Rule |
| --- | --- |
| Missing field | Any of the six keys absent |
| Not a number | Value is text, `None`, or a boolean |
| Impossible heart rate | Outside 20–250 bpm |
| Impossible activity level | Outside 0.0–1.0 |
| Impossible skin temperature | Outside 20–45 °C |
| Negative skin response or timestamp | Below 0 |
| Signal quality too low | Below 0.50 |

Flagged but still counted as usable:

| Problem | Rule |
| --- | --- |
| Weak signal | Signal quality 0.50 – 0.69 |

Why two tiers rather than one cutoff: a reading the sensor half-trusts is still
evidence, and discarding it can tip a session under the five-observation minimum
and produce "insufficient data" for no good reason. Below 0.50 the reading is
closer to noise than signal. The boundary is arbitrary in the sense that any
boundary is — the point is that it is stated and defensible rather than implicit.

### Classification

Two figures are derived from the usable observations:

- **HR ratio** = mean heart rate ÷ participant's resting heart rate
- **Mean activity** = mean of `activity_level`

Checks run in order; first match wins:

| # | Label | Condition |
| --- | --- | --- |
| 1 | insufficient data | Fewer than 5 usable observations |
| 2 | recovering | Recovery detected (below) |
| 3 | high activity | HR ratio ≥ 1.50 **or** mean activity ≥ 0.60 |
| 4 | moderate activity | HR ratio ≥ 1.15 **or** mean activity ≥ 0.20 |
| 5 | resting | Everything else |

Recovery requires all three, comparing the **final third** against the **peak third**:

1. Mean heart rate has fallen by ≥ 10%
2. Mean activity has fallen by ≥ 30%
3. The peak third reached HR ratio ≥ 1.30 — i.e. there was something to recover from

Condition 3 exists because without it, a person sitting still whose heart rate
drifts down by 10% would be labelled "recovering".

### Result dictionary

`Session.analyse()` returns keys: `participant`, `classification`, `explanation`,
`observations` (`total` / `usable` / `rejected` / `flagged`), `summary`,
`comparison`, `recovery`, `issues`.

---

### Corrections made during approval

**1. Athlete thresholds were backwards — raised, not lowered.**

The first draft lowered the athlete's bands (elevated 1.10×, high 1.35×) on the
reasoning that a trained person's heart rate "climbs proportionally less". That
reasoning was wrong. HR ratio divides by the resting heart rate, and a trained
person's resting rate is *lower* — a smaller denominator. For the same absolute
working heart rate the athlete's ratio therefore comes out **higher**, not lower.

Worked example: at a working rate of 140 bpm, an untrained person resting at
70 sits at ratio 2.00, while an athlete resting at 45 sits at 3.11 — the same
effort, a much larger ratio. Applying the untrained bands to the athlete would
mark them "high activity" during what is, for them, easy work.

Final athlete bands: **elevated 1.25×, high 1.70×** — raised relative to the
base class, to absorb the smaller denominator.

**2. `from_dict` no longer carries its own validation.**

The draft had `Observation.from_dict` returning "an `Observation` or a rejection
reason", which would have put a second copy of the rules inside the class.
`validate_observation()` is now the only place the rules live. `from_dict` calls
it and raises `ValueError(reason)` on failure; `Session` catches that and records
the reason in `issues`. One rule set, one place to change it.

**3. Unchanged after review:** minimum of 5 usable observations, the two
signal-quality tiers, and the `Athlete` subclass.

**4. Recovery is checked before high activity — deliberately.**

A hard workout that ends in a cooldown satisfies *both* tests: it contains a
genuinely high-intensity stretch, and it shows a decline at the end. The order
of checks decides which label it gets, and this program deliberately labels it
**"recovering"** rather than "high activity".

The reason is that "recovering" is the more specific statement. "High activity"
is true of any demanding session; "recovering" additionally says the session was
demanding *and* the participant has come back down from it. Reporting the less
specific label would throw away the more interesting half of the finding. The
explanation string names the peak intensity as well, so the demanding stretch is
never hidden from the reader — it is reported inside the recovery verdict rather
than instead of it.

The trade-off, stated plainly: a session labelled "recovering" cannot be found by
searching for "high activity", even though it contained high activity. For this
assignment that is acceptable, because each session is reported individually
rather than aggregated.
