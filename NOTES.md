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

> **Revised during Section 2.** The heart-rate-ratio approach described here was
> replaced by heart rate reserve, and the `Athlete` override moved from
> `heart_rate_bands()` to `recovery_thresholds()`. The tables below have been
> updated to the current design; see "Section 2 revision — heart rate reserve"
> for what changed and why.

### Classes

| Class | Responsibility |
| --- | --- |
| `Participant` | Who the person is, plus their reference values (resting heart rate, maximum heart rate, normal skin temperature). Owns the two methods that turn those into thresholds: `heart_rate_bands()` and `recovery_thresholds()`. |
| `Athlete(Participant)` | Same role, stricter recovery. Overrides `recovery_thresholds()` and `describe()`. |
| `Observation` | A single sensor reading — the six-field record from the brief. |
| `Session` | One recording: one `Participant` plus a list of `Observation`s. Separates usable from rejected readings and produces the result dictionary. |

Four classes, deliberately. A separate `Validator` or `Report` class was rejected:
each would hold no data and expose one method, which is a plain function with
extra ceremony around it.

### Where each required concept is demonstrated

| Concept | Location | Reasoning |
| --- | --- | --- |
| Composition | `Session` holds a `Participant` and a list of `Observation`s | A session is not a kind of participant; it *contains* one. |
| Private attribute + `@property` | `Participant._resting_heart_rate` and `_max_heart_rate`, read via properties | Both anchor every threshold the program produces. The setters additionally cross-check each other, so a participant can never exist with a resting rate at or above their maximum — which would make the reserve zero or negative and the bands meaningless. |
| Inheritance + overriding | `Athlete.recovery_thresholds()` and `Athlete.describe()` override `Participant`'s | Same question, genuinely different answer — see "Section 2 revision" below. |
| `@classmethod` | `Observation.from_dict(raw)` | An alternative constructor. The program's real input format is the dict from the brief, so building straight from one is the natural entry point. |

### Standalone functions (all in `analyzer.py`)

| Function | Kind | Purpose |
| --- | --- | --- |
| `validate_observation(raw)` | validation | The single place the rules live. Returns whether a raw record is acceptable and a plain-English reason when it is not. |
| `summarise(observations)` | calculation | Average, minimum, maximum per measurement. |
| `compare_to_reference(summary, participant)` | calculation | Distance from the participant's own normal values. |
| `detect_recovery(observations, participant)` | calculation | Did heart rate **and** activity both fall near the end? Takes the participant so it can ask for `recovery_thresholds()` rather than holding numbers of its own. |
| `format_report(result)` | presentation | Result dictionary → readable console text. |

Plus `require_number(label, value)`, a one-line helper shared by the property
setters and `validate_observation()`, so "is this a number, and not a boolean"
is written once rather than in five places.

Six, against a required minimum of four.

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

- **Mean heart rate**, in bpm, compared against `participant.heart_rate_bands()`
- **Mean activity** = mean of `activity_level`

The bands come from heart rate reserve, the span between a person's resting and
maximum rate:

```
reserve  = max_heart_rate - resting_heart_rate
elevated = resting_heart_rate + 0.20 * reserve
high     = resting_heart_rate + 0.50 * reserve
```

`max_heart_rate` defaults to 190 and can be passed per participant.

Checks run in order; first match wins:

| # | Label | Condition |
| --- | --- | --- |
| 1 | insufficient data | Fewer than 5 usable observations |
| 2 | recovering | Recovery detected (below) |
| 3 | high activity | Mean HR ≥ the **high** band **or** mean activity ≥ 0.60 |
| 4 | moderate activity | Mean HR ≥ the **elevated** band **or** mean activity ≥ 0.20 |
| 5 | resting | Everything else |

Recovery requires all three, comparing the **final third** against the **peak third**:

1. Mean heart rate has fallen by at least `recovery_thresholds()["heart_rate_drop"]`
2. Mean activity has fallen by at least `recovery_thresholds()["activity_drop"]`
3. The peak third's mean heart rate reached the **elevated** band — i.e. there
   was something to recover from

Condition 3 exists because without it, a person sitting still whose heart rate
drifts down by 10% would be labelled "recovering".

**No threshold is written anywhere outside `heart_rate_bands()` and
`recovery_thresholds()`.** `classify_session()` and `detect_recovery()` ask the
participant for its numbers rather than carrying copies, which is what lets
`Athlete` change the behaviour by overriding one method.

### Result dictionary

`Session.analyse()` returns keys: `participant`, `classification`, `explanation`,
`observations` (`total` / `usable` / `rejected` / `flagged`), `summary`,
`comparison`, `recovery`, `issues`.

---

### Corrections made during approval

**1. Athlete thresholds were backwards — raised, not lowered.** *(Superseded —
see "Section 2 revision" below. Kept because it is the reasoning that led there.)*

The first draft lowered the athlete's bands (elevated 1.10×, high 1.35×) on the
reasoning that a trained person's heart rate "climbs proportionally less". That
reasoning was wrong. HR ratio divides by the resting heart rate, and a trained
person's resting rate is *lower* — a smaller denominator. For the same absolute
working heart rate the athlete's ratio therefore comes out **higher**, not lower.

Worked example: at a working rate of 140 bpm, an untrained person resting at
70 sits at ratio 2.00, while an athlete resting at 45 sits at 3.11 — the same
effort, a much larger ratio. Applying the untrained bands to the athlete would
mark them "high activity" during what is, for them, easy work.

Corrected athlete bands: **elevated 1.25×, high 1.70×** — raised relative to the
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

---

## Section 2 — Core classes

**What was built**

`analyzer.py`, holding all four classes from the Section 1 plan — `Participant`,
`Athlete`, `Observation`, `Session` — plus the structural half of
`validate_observation()`. No summaries, comparisons or classification yet.

**Decisions and why**

| Decision | Why |
| --- | --- |
| `heart_rate_bands()` repeats the literal multipliers in both classes instead of reading class constants | With constants (`ELEVATED_RATIO = 1.15`), `Athlete` could change its bands by reassigning them and would never need to override a method — the inheritance requirement would be met only on paper. Writing the method out in both classes makes the override real: the same call, answered differently. The cost is two numbers in two places, which is acceptable for four literals that the README documents anyway. |
| `Athlete` overrides two methods, `heart_rate_bands()` and `describe()` | One override could be read as decoration. Two show the subclass genuinely behaves differently in more than one respect. |
| The property setter runs at construction, not just on later assignment | `__init__` assigns to `self.resting_heart_rate` (no underscore), so the checks apply to the object's first value too. Assigning to `self._resting_heart_rate` directly would have left construction unchecked — the most likely place for a bad value to enter. |
| Booleans are rejected explicitly everywhere a number is expected | In Python `bool` is a subclass of `int`, so `True` passes an `isinstance(value, int)` test and would silently become the number 1. A heart rate of `True` should be an error, not 1 bpm. |
| `Session.add_observation()` returns True/False and records the reason, rather than raising | A session is expected to contain some bad records — that is the point of the assignment. Making the caller handle an exception per record would put try/except around every append in `main.py`. The exception is raised where the rule is broken (`from_dict`) and caught where the bookkeeping lives (`Session`). |
| Rejection reasons are numbered by arrival order (`record 3: ...`) | Rejected records are not stored, so without a number the report can say *what* was wrong but not *which* reading. The count is of records offered, not accepted, so the numbering still points at the input. |
| `ordered_observations()` sorts on demand rather than keeping the list sorted | Recovery detection is the only part that needs time order. Sorting once when asked is simpler than keeping an invariant on every insert, and the input is small. |

**Alternatives rejected**

- *A `Report` class and a `Validator` class* — both would hold no data and expose
  a single method. That is a function with extra ceremony, and the brief
  explicitly says more classes is not better.
- *Storing rejected records as objects* — would allow richer reporting, but an
  `Observation` that failed validation is an object whose fields cannot be
  trusted. A reason string carries everything the report actually needs.

**Known cosmetic issue**

`heart_rate_bands()` returns values like `78.19999999999999` — ordinary binary
floating point, not a bug. Rounding is a presentation concern and is handled in
the report (Section 6) rather than by rounding the stored values, so no precision
is lost from the intermediate maths.

---

## Section 2 revision — heart rate reserve

Reviewed after Section 2 was committed, and the threshold model was replaced.
This supersedes Correction 1 above.

### Why the ratio approach was wrong

Both the original plan and its correction measured effort as
`mean heart rate ÷ resting heart rate`. Correcting the *direction* of the
athlete adjustment did not fix the underlying problem: **a ratio to resting
heart rate is not a measure of effort.**

A ratio treats the resting rate as the only thing that varies between people,
and silently assumes everyone has the same ceiling. They do not. The quantity a
person actually has available is the span between their resting rate and their
maximum — the **heart rate reserve**. Two people with the same resting rate but
different maxima have different amounts of room to work with, and a ratio cannot
see that difference at all.

The ratio model also produced the absurdity that a low resting heart rate — a
sign of *fitness* — inflated the effort score. That is what forced the
`Athlete` subclass to exist: it was a patch compensating for a distortion the
formula itself introduced. A special case whose only job is to undo the base
formula's error is a sign the base formula is wrong, not a sign the subclass is
needed.

### What replaces it

Heart rate reserve, the standard approach (the Karvonen method):

```
reserve  = max_heart_rate - resting_heart_rate
elevated = resting_heart_rate + 0.20 * reserve
high     = resting_heart_rate + 0.50 * reserve
```

`heart_rate_bands()` now returns **absolute bpm**, not multipliers, and
`Participant` takes `max_heart_rate=190` as an optional argument.

Worked comparison at 140 bpm, both with max 190:

| | Untrained, resting 70 | Athlete, resting 45 |
| --- | --- | --- |
| Reserve | 120 bpm | 145 bpm |
| Elevated band | 94.0 bpm | 74.0 bpm |
| High band | 130.0 bpm | 117.5 bpm |
| At 140 bpm | above high | above high |
| Old ratio | 2.00 | 3.11 |

Both are correctly placed above their high band, using one formula and no
special case. The athlete's bands come out *lower* in absolute bpm, which is
right: a larger reserve means each beat above resting represents a smaller
share of what they have available, so they cross into a given effort zone at a
lower absolute rate than the ratio model implied.

**`Athlete` no longer overrides `heart_rate_bands()`.** The reserve formula
already accounts for a low resting rate, so the override would be redundant —
and a redundant override is worse than none, because it hides that the base
formula is doing the work.

### Where the Athlete override moved

`Participant.recovery_thresholds()` returns
`{"heart_rate_drop": 0.10, "activity_drop": 0.30}`. `Athlete` overrides it,
raising `heart_rate_drop` to **0.15**.

The justification is about a genuinely different physiological behaviour rather
than a units artefact. A trained person's heart rate falls faster and more
steeply once effort stops. A 10% dip that means a real cooldown in an untrained
person is within ordinary fluctuation for an athlete, so requiring 15% stops
the program reading normal variation as a recovery phase. The parent's
`activity_drop` is kept unchanged via `super()`, because how quickly someone
stops *moving* is not a function of fitness.

This is a better override than the one it replaces: it survives the question
"would this still be needed if the formula were right?" — which the old one
did not.

### Consequence for Sections 4 and 5

`classify_session()` compares mean heart rate against
`participant.heart_rate_bands()`. `detect_recovery()` takes the participant and
reads `participant.recovery_thresholds()`. The "something to recover from"
check becomes: *the peak third's mean heart rate reached the elevated band*.

No threshold is hard-coded outside those two methods. That rule is what makes
the subclass work — if `detect_recovery()` held its own copy of 0.10, an
`Athlete` would silently be judged by the untrained numbers.

---

## Section 3 — Validation

**What was built**

`validate_observation()` completed: structural checks, impossible-value ranges,
and the two signal-quality tiers. Flags now travel from the validator through
`Observation.from_dict()` into `Session`, which counts them separately from
rejections.

### Rejected vs flagged — the rule and the reason

The split is **"could this have happened?"** versus **"do we trust the sensor
that reported it?"** These are different questions and they get different
answers.

**Rejected — the reading describes something that cannot have occurred.**
There is no partial credit here. A heart rate of −40 is not a poor measurement
of a real heart rate; it is not a measurement at all. Averaging it in would
corrupt every figure downstream, and no warning label makes that safe.

| Rejected | Rule |
| --- | --- |
| Not a dictionary | The record is not a record |
| Missing field | Any of the six keys absent |
| Not a number | Value is text, `None`, or a boolean |
| Heart rate | Outside 20–250 bpm |
| Skin response | Outside 0–30 µS |
| Temperature | Outside 20–45 °C |
| Activity level | Outside 0.0–1.0 |
| Signal quality | Outside 0.0–1.0 |
| Timestamp | Below 0 |
| Signal quality too low | Below 0.50 |

**Flagged — the reading is possible, but the sensor was not confident.**

| Flagged, still counted | Rule |
| --- | --- |
| Weak signal | Signal quality 0.50 – 0.69 |

A reading the sensor half-trusts is still evidence. Discarding it can push a
session below the five-observation minimum and produce "insufficient data" for a
session that was in fact recorded — a worse outcome than including a slightly
noisy reading and saying so. Below 0.50 the reading is closer to noise than
signal, and including it would move the averages more than it informs them.

The honest caveat: 0.50 and 0.70 are judgement calls. Any cutoff is. What
matters for defending this is that they are named constants
(`SIGNAL_QUALITY_REJECT`, `SIGNAL_QUALITY_FLAG`) with the reasoning written
down, rather than numbers buried in an `if`.

**Decisions and why**

| Decision | Why |
| --- | --- |
| `validate_observation()` returns a dictionary (`ok` / `reason` / `flags`) instead of the planned `(ok, reason)` tuple | Section 3 introduced a third outcome — accepted *with a warning*. A tuple that grew to `(ok, reason, flags)` would force every caller to unpack a value it may not care about, and the meaning of position 3 would not be self-evident. The dictionary names its parts. This is a change from the Section 1 plan. |
| Checks run in three ordered stages, stopping at the first failure | Structure, then plausibility, then trust — cheapest and most fundamental first. A record missing `heart_rate` reports exactly that, rather than a confusing complaint about a field it does happen to have. One record yields one reason, which keeps the report readable. |
| Signal quality is checked twice, in two different senses | A quality of 1.3 is *impossible* (rejected as out of range); a quality of 0.31 is possible but *untrustworthy* (rejected as below the usable cutoff). Different problems, different messages. Collapsing them would produce "signal quality 1.3 is below the cutoff", which is nonsense. |
| `timestamp` has a lower bound but no upper bound | A session can last any length of time, so any ceiling would be invented. A negative timestamp is still impossible, so the lower bound is real. `None` in `VALUE_RANGES` means "no bound". |
| `skin_response` gained an upper bound of 30 µS, which the Section 1 plan did not have | The plan only rejected negatives. But skin conductance during exercise sits in roughly 1–20 µS, and a reading of, say, 800 is a sensor fault rather than an extreme person — exactly the kind of impossible value the section is meant to catch. Leaving it unbounded would have let one broken reading dominate the average. Flagged here as a deliberate deviation from the approved plan, not an oversight. |
| Flags are recorded in `Session.issues` alongside rejections, tagged `flagged:` vs `rejected:` | The report has to show both, and they read naturally as one ordered list of what happened to the input. The prefix keeps them distinguishable; `flagged_count` and `rejected_count` keep them countable separately. |
| Rejected records are still counted in `total_count` | `usable + rejected == total` must hold, otherwise the report cannot honestly say how many observations were received. Verified as an invariant in testing. |

**Alternatives rejected**

- *Flagging impossible values instead of rejecting them* — would keep more data,
  but a value that cannot occur carries no information. Including it with a
  warning shifts the averages while pretending to be cautious.
- *A single signal-quality cutoff* — simpler to explain, but forces a choice
  between discarding usable evidence and accepting noise. Two tiers cost one
  extra constant and one extra branch.
- *Collecting every problem with a record rather than stopping at the first* —
  more thorough, but a record with a missing field cannot be range-checked
  anyway, so most of the extra output would be noise about consequences of the
  first failure.

**Verified**

All fifteen rejection paths produce a distinct readable message; the
signal-quality boundary behaves exactly as specified (0.49 rejected, 0.50 and
0.69 flagged, 0.70 clean); a mixed session reports `total=5 usable=2 flagged=1
rejected=3` with both invariants holding.
