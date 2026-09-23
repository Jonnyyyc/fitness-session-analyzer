# Project notes

Working notes kept section by section. These are the raw decisions and the
reasoning behind them. The README (Section 9) is written from this file.

Project: Smart Fitness Session Analyzer (Option A)
Author: Jonathan Christensen
Student number: jonathan4495
GitHub account: Jonnyyyc
Repository: https://github.com/Jonnyyyc/fitness-session-analyzer

---

## Section 0: Setup

### What was done

Created the repository folder `fitness-session-analyzer` with the five files the
assignment asks for (`README.md`, `main.py`, `sample_data.py`, `tests.py`,
`requirements.txt`), plus this notes file and a `.gitignore`. Initialised git. No
program logic written yet.

### Decisions and why

| Decision | Why |
| --- | --- |
| Files contain a short docstring placeholder rather than being truly empty | An empty `tests.py` makes `python -m unittest tests.py` fail, and an empty `main.py` gives no sign the project runs. Placeholders mean both commands work from day one, so a broken run always means *my* bug rather than a missing file. |
| `requirements.txt` states "standard library only" as a comment | The assignment allows this. A comment explains *why* the file is otherwise empty, which an empty file does not. |
| Added `.gitignore` even though it is not in the required file list | Stops `__pycache__/` and editor files being committed. Without it the repository fills with generated files that are not my work. |
| Class code will live in its own module, not inside `main.py` | Proposed in Section 1. `main.py` stays a thin entry point that only runs scenarios and prints. Keeps the "run with `python3 main.py`" requirement clean. **Still to be approved.** |

### Alternatives rejected

- *Putting every class in `main.py`.* This would satisfy the file list, but it
  mixes the program's logic with the code that runs it, and makes `tests.py`
  import the file whose whole job is to print reports. Rejected in favour of a
  separate module, to confirm in Section 1.
- *Creating truly empty files.* Matches "empty files" literally, but see above.

### Resolved

`jonathan4495` is the student number, **not** the GitHub account name. The GitHub
account is `Jonnyyyc`, so the clone URL used in the README (Section 9) and the
push in Section 10 is
`https://github.com/Jonnyyyc/fitness-session-analyzer.git`.

Class code goes in its own module, `analyzer.py`, alongside the five required
files. Approved. `main.py` stays a thin entry point that only builds the
scenarios and prints reports, so `tests.py` can import the classes without
pulling in the printing code.

### Environment note

Git was not installed on this machine, so it was installed during this section.
Python here is 3.14.3 and the command is `python` rather than `python3`. The
`python3` spelling in the assignment instructions is the macOS and Linux one.
The README documents both.

---

## Section 1: Design plan

Approved with four changes, recorded under "Corrections" below. No code written
in this section.

> **Revised during Section 2.** The heart-rate-ratio approach described here was
> replaced by heart rate reserve, and the `Athlete` override moved from
> `heart_rate_bands()` to `recovery_thresholds()`. The tables below have been
> updated to the current design. See "Section 2 revision: heart rate reserve"
> for what changed and why.

### Classes

| Class | Responsibility |
| --- | --- |
| `Participant` | Who the person is, plus their reference values (resting heart rate, maximum heart rate, normal skin temperature). Owns the two methods that turn those into thresholds: `heart_rate_bands()` and `recovery_thresholds()`. |
| `Athlete(Participant)` | Same role, stricter recovery. Overrides `recovery_thresholds()` and `describe()`. |
| `Observation` | A single sensor reading, meaning the six-field record from the brief. |
| `Session` | One recording: one `Participant` plus a list of `Observation`s. Separates usable from rejected readings and produces the result dictionary. |

Four classes, and I stopped there deliberately. I considered a separate
`Validator` class and a separate `Report` class, but each would have held no data
and exposed one method, which is a plain function with extra ceremony around it.

### Where each required concept is demonstrated

| Concept | Location | Reasoning |
| --- | --- | --- |
| Composition | `Session` holds a `Participant` and a list of `Observation`s | A session is not a kind of participant, it *contains* one. |
| Private attribute with `@property` | `Participant._resting_heart_rate` and `_max_heart_rate`, read via properties | Both anchor every threshold the program produces. The setters also cross-check each other, so a participant can never exist with a resting rate at or above their maximum, which would make the reserve zero or negative and the bands meaningless. |
| Inheritance and overriding | `Athlete.recovery_thresholds()` and `Athlete.describe()` override `Participant`'s | Same question, genuinely different answer. See "Section 2 revision" below. |
| `@classmethod` | `Observation.from_dict(raw)` | An alternative constructor. The program's real input format is the dict from the brief, so building straight from one is the natural entry point. |

### Standalone functions, all in `analyzer.py`

| Function | Kind | Purpose |
| --- | --- | --- |
| `validate_observation(raw)` | validation | The single place the rules live. Returns whether a raw record is acceptable and a plain-English reason when it is not. |
| `summarise(observations)` | calculation | Average, minimum, maximum per measurement. |
| `compare_to_reference(summary, participant)` | calculation | Distance from the participant's own normal values. |
| `detect_recovery(observations, participant)` | calculation | Did heart rate **and** activity both fall near the end? Takes the participant so it can ask for `recovery_thresholds()` rather than holding numbers of its own. |
| `format_report(result)` | presentation | Turns the result dictionary into readable console text. |

Plus `require_number(label, value)`, a one-line helper shared by the property
setters and `validate_observation()`, so "is this a number, and not a boolean" is
written once rather than in five places.

Six, against a required minimum of four.

### Validation rules

Rejected, meaning discarded and not counted as usable:

| Problem | Rule |
| --- | --- |
| Missing field | Any of the six keys absent |
| Not a number | Value is text, `None`, or a boolean |
| Impossible heart rate | Outside 20 to 250 bpm |
| Impossible activity level | Outside 0.0 to 1.0 |
| Impossible skin temperature | Outside 20 to 45 C |
| Negative skin response or timestamp | Below 0 |
| Signal quality too low | Below 0.50 |

Flagged but still counted as usable:

| Problem | Rule |
| --- | --- |
| Weak signal | Signal quality 0.50 to 0.69 |

Why two tiers rather than one cutoff. A reading the sensor half-trusts is still
evidence, and discarding it can tip a session under the five-observation minimum
and produce "insufficient data" for no good reason. Below 0.50 the reading is
closer to noise than signal. Any boundary here is arbitrary. What matters is that
this one is stated and defensible rather than implicit.

### Classification

Two figures get derived from the usable observations:

- **Mean heart rate**, in bpm, compared against `participant.heart_rate_bands()`
- **Mean activity**, the mean of `activity_level`

The bands come from heart rate reserve, the span between a person's resting and
maximum rate:

```
reserve  = max_heart_rate - resting_heart_rate
elevated = resting_heart_rate + 0.20 * reserve
high     = resting_heart_rate + 0.50 * reserve
```

`max_heart_rate` defaults to 190 and can be passed per participant.

Checks run in order, first match wins:

| # | Label | Condition |
| --- | --- | --- |
| 1 | insufficient data | Fewer than 5 usable observations |
| 2 | recovering | Recovery detected, see below |
| 3 | high activity | Mean HR reaches the **high** band, **or** mean activity is 0.60 or more |
| 4 | moderate activity | Mean HR reaches the **elevated** band, **or** mean activity is 0.20 or more |
| 5 | resting | Everything else |

Recovery requires all three, comparing the **final third** against the **peak
third**:

1. Mean heart rate has fallen by at least `recovery_thresholds()["heart_rate_drop"]`
2. Mean activity has fallen by at least `recovery_thresholds()["activity_drop"]`
3. The peak third's mean heart rate reached the **elevated** band, so there was
   something to recover from

Condition 3 exists because without it, a person sitting still whose heart rate
drifts down by 10% would be labelled "recovering".

**No threshold is written anywhere outside `heart_rate_bands()` and
`recovery_thresholds()`.** `classify_session()` and `detect_recovery()` ask the
participant for its numbers rather than carrying copies, which is what lets
`Athlete` change the behaviour by overriding one method.

### Result dictionary

`Session.analyse()` returns keys: `participant`, `classification`, `explanation`,
`observations` (`total` / `usable` / `rejected` / `flagged`), `summary`,
`comparison`, `recovery`, `flag_notes`, `rejection_notes`.

---

### Corrections made during approval

**1. Athlete thresholds were backwards, raised rather than lowered.**
*(Superseded by the Section 2 revision below. Kept because it is the reasoning
that led there.)*

My first draft lowered the athlete's bands to elevated 1.10x and high 1.35x, on
the reasoning that a trained person's heart rate "climbs proportionally less".
That reasoning was wrong. The HR ratio divides by the resting heart rate, and a
trained person's resting rate is *lower*, which is a smaller denominator. For the
same absolute working heart rate the athlete's ratio therefore comes out
**higher**.

Worked example. At a working rate of 140 bpm, an untrained person resting at 70
sits at ratio 2.00, while an athlete resting at 45 sits at 3.11. Same effort, much
larger ratio. Applying the untrained bands to the athlete would mark them "high
activity" during what is, for them, easy work.

Corrected athlete bands: **elevated 1.25x, high 1.70x**, raised relative to the
base class to absorb the smaller denominator.

**2. `from_dict` no longer carries its own validation.**

The draft had `Observation.from_dict` returning "an `Observation` or a rejection
reason", which would have put a second copy of the rules inside the class.
`validate_observation()` is now the only place the rules live. `from_dict` calls
it and raises `ValueError(reason)` on failure, and `Session` catches that and
records the reason in `rejection_notes`. One rule set, one place to change it.

**3. Unchanged after review:** minimum of 5 usable observations, the two
signal-quality tiers, and the `Athlete` subclass.

**4. Recovery is checked before high activity, deliberately.**

A hard workout that ends in a cooldown satisfies *both* tests. It contains a
genuinely high-intensity stretch, and it shows a decline at the end. The order of
checks decides which label it gets, and this program labels it **"recovering"**.

The reason is that "recovering" says more. "High activity" is true of any
demanding session, while "recovering" additionally says the session was demanding
*and* the participant has come back down from it. Reporting the less specific
label would throw away the more interesting half of the finding. The explanation
string names the peak intensity too, so the demanding stretch still appears in
the report rather than getting buried.

There is a real cost. A session labelled "recovering" will not turn up if you
search for "high activity", even though it contained plenty of it. For this
assignment that seemed acceptable, because each session is reported on its own
rather than aggregated across many.

---

## Section 2: Core classes

### What was built

`analyzer.py`, holding all four classes from the Section 1 plan (`Participant`,
`Athlete`, `Observation`, `Session`) plus the structural half of
`validate_observation()`. No summaries, comparisons or classification yet.

### Decisions and why

| Decision | Why |
| --- | --- |
| `heart_rate_bands()` repeats the literal multipliers in both classes instead of reading class constants | With constants such as `ELEVATED_RATIO = 1.15`, `Athlete` could change its bands by reassigning them and would never need to override a method, so the inheritance requirement would be met only on paper. Writing the method out in both classes makes the override real: the same call, answered differently. The cost is two numbers in two places, acceptable for four literals the README documents anyway. |
| `Athlete` overrides two methods, `heart_rate_bands()` and `describe()` | One override could be read as decoration. Two show the subclass genuinely behaves differently in more than one respect. |
| The property setter runs at construction, not just on later assignment | `__init__` assigns to `self.resting_heart_rate` with no underscore, so the checks apply to the object's first value too. Assigning to `self._resting_heart_rate` directly would leave construction unchecked, which is the most likely place for a bad value to enter. |
| Booleans are rejected explicitly everywhere a number is expected | In Python `bool` is a subclass of `int`, so `True` passes an `isinstance(value, int)` test and would silently become the number 1. A heart rate of `True` should be an error rather than 1 bpm. |
| `Session.add_observation()` returns True or False and records the reason, rather than raising | A session is expected to contain some bad records, since that is the point of the assignment. Making the caller handle an exception per record would put try/except around every append in `main.py`. The exception is raised where the rule is broken, in `from_dict`, and caught where the bookkeeping lives, in `Session`. |
| Rejection reasons are numbered by arrival order, as in `record 3: ...` | Rejected records are not stored, so without a number the report can say *what* was wrong but not *which* reading. The count is of records offered rather than accepted, so the numbering still points at the input. |
| `ordered_observations()` sorts on demand rather than keeping the list sorted | Recovery detection is the only part that needs time order. Sorting once when asked is simpler than keeping an invariant on every insert, and the input is small. |

### Alternatives rejected

- *A `Report` class and a `Validator` class.* Both would hold no data and expose
  a single method. That is a function with extra ceremony, and the brief says
  outright that more classes is not better.
- *Storing rejected records as objects.* This would allow richer reporting, but
  an `Observation` that failed validation is an object whose fields cannot be
  trusted. A reason string carries everything the report actually needs.

### Known cosmetic issue

`heart_rate_bands()` returns values like `78.19999999999999`. That is ordinary
binary floating point rather than a bug. Rounding is a presentation concern and
is handled in the report in Section 6, rather than by rounding the stored values,
so no precision is lost from the intermediate maths.

---

## Section 2 revision: heart rate reserve

Reviewed after Section 2 was committed, and the threshold model was replaced.
This supersedes Correction 1 above.

### Why the ratio approach was wrong

Both the original plan and its correction measured effort as
`mean heart rate / resting heart rate`. Correcting the *direction* of the athlete
adjustment did not fix the underlying problem, which is that **a ratio to resting
heart rate is not a measure of effort.**

A ratio treats the resting rate as the only thing that varies between people, and
silently assumes everyone has the same ceiling. They do not. The quantity a
person actually has available is the span between their resting rate and their
maximum, the **heart rate reserve**. Two people with the same resting rate but
different maximums have different amounts of room to work with, and a ratio
cannot see that difference at all.

The ratio model also produced an absurdity. A low resting heart rate, which is a
sign of *fitness*, inflated the effort score. That is what forced the `Athlete`
subclass to exist in the first place. It was a patch compensating for a
distortion the formula itself introduced. Once I noticed that a special case
existed only to undo the base formula's error, it was clear the base formula was
the thing that needed fixing.

### What replaces it

Heart rate reserve, the standard approach, also called the Karvonen method:

```
reserve  = max_heart_rate - resting_heart_rate
elevated = resting_heart_rate + 0.20 * reserve
high     = resting_heart_rate + 0.50 * reserve
```

`heart_rate_bands()` now returns **absolute bpm** rather than multipliers, and
`Participant` takes `max_heart_rate=190` as an optional argument.

Worked comparison at 140 bpm, both with max 190:

| | Untrained, resting 70 | Athlete, resting 45 |
| --- | --- | --- |
| Reserve | 120 bpm | 145 bpm |
| Elevated band | 94.0 bpm | 74.0 bpm |
| High band | 130.0 bpm | 117.5 bpm |
| At 140 bpm | above high | above high |
| Old ratio | 2.00 | 3.11 |

Both land correctly above their high band, using one formula and no special case.
The athlete's bands come out *lower* in absolute bpm, which is right. A larger
reserve means each beat above resting represents a smaller share of what they
have available, so they cross into a given effort zone at a lower absolute rate
than the ratio model implied.

**`Athlete` no longer overrides `heart_rate_bands()`.** The reserve formula
already accounts for a low resting rate, so the override would be redundant, and
a redundant override is worse than none because it hides where the work is
actually happening.

### Where the Athlete override moved

`Participant.recovery_thresholds()` returns
`{"heart_rate_drop": 0.10, "activity_drop": 0.30}`. `Athlete` overrides it,
raising `heart_rate_drop` to **0.15**.

This justification is about genuinely different physiology rather than a units
artefact. A trained person's heart rate falls faster and more steeply once effort
stops. A 10% dip that means a real cooldown in an untrained person sits within
ordinary fluctuation for an athlete, so requiring 15% stops the program reading
normal variation as a recovery phase. The parent's `activity_drop` is kept
unchanged via `super()`, because how quickly someone stops *moving* has nothing
to do with fitness.

This is a better override than the one it replaces. It survives the question
"would this still be needed if the formula were right?", which the old one did
not.

### Consequence for Sections 4 and 5

`classify_session()` compares mean heart rate against
`participant.heart_rate_bands()`. `detect_recovery()` takes the participant and
reads `participant.recovery_thresholds()`. The "something to recover from" check
becomes: *the peak third's mean heart rate reached the elevated band*.

No threshold is hard-coded outside those two methods. That rule is what makes the
subclass work. If `detect_recovery()` held its own copy of 0.10, an `Athlete`
would silently be judged by the untrained numbers.

---

## Section 3: Validation

### What was built

`validate_observation()` completed, with structural checks, impossible-value
ranges, and the two signal-quality tiers. Flags now travel from the validator
through `Observation.from_dict()` into `Session`, which counts them separately
from rejections.

### Rejected versus flagged: the rule and the reason

The split comes down to two different questions. **Could this have happened?**
And **do we trust the sensor that reported it?**

**Rejected** means the reading describes something that cannot have occurred.
There is no partial credit. A heart rate of -40 is not a poor measurement of a
real heart rate, it is not a measurement at all. Averaging it in would corrupt
every figure downstream, and no warning label makes that safe.

| Rejected | Rule |
| --- | --- |
| Not a dictionary | The record is not a record |
| Missing field | Any of the six keys absent |
| Not a number | Value is text, `None`, or a boolean |
| Heart rate | Outside 20 to 250 bpm |
| Skin response | Outside 0 to 30 uS |
| Temperature | Outside 20 to 45 C |
| Activity level | Outside 0.0 to 1.0 |
| Signal quality | Outside 0.0 to 1.0 |
| Timestamp | Below 0 |
| Signal quality too low | Below 0.50 |

**Flagged** means the reading is possible, but the sensor was not confident.

| Flagged, still counted | Rule |
| --- | --- |
| Weak signal | Signal quality 0.50 to 0.69 |

A reading the sensor half-trusts is still evidence. Discarding it can push a
session below the five-observation minimum and produce "insufficient data" for a
session that was in fact recorded, which is worse than including a slightly noisy
reading and saying so. Below 0.50 the reading is closer to noise than signal, and
including it would move the averages more than it informs them.

The honest caveat is that 0.50 and 0.70 are judgement calls. Any cutoff is. What
matters for defending them is that they are named constants,
`SIGNAL_QUALITY_REJECT` and `SIGNAL_QUALITY_FLAG`, with the reasoning written
down rather than numbers buried in an `if`.

### Decisions and why

| Decision | Why |
| --- | --- |
| `validate_observation()` returns a dictionary (`ok` / `reason` / `flags`) instead of the planned `(ok, reason)` tuple | Section 3 introduced a third outcome, accepted *with a warning*. A tuple that grew to `(ok, reason, flags)` would force every caller to unpack a value it may not care about, and the meaning of position 3 would not be self-evident. The dictionary names its parts. This is a change from the Section 1 plan. |
| Checks run in three ordered stages, stopping at the first failure | Structure, then plausibility, then trust, so the cheapest and most fundamental come first. A record missing `heart_rate` reports exactly that, rather than a confusing complaint about a field it does happen to have. One record yields one reason, which keeps the report readable. |
| Signal quality is checked twice, in two different senses | A quality of 1.3 is *impossible* and gets rejected as out of range. A quality of 0.31 is possible but *untrustworthy* and gets rejected as below the usable cutoff. Different problems, different messages. Collapsing them would produce "signal quality 1.3 is below the cutoff", which is nonsense. |
| `timestamp` has a lower bound but no upper bound | A session can last any length of time, so any ceiling would be invented. A negative timestamp is still impossible, so the lower bound is real. `None` in `VALUE_RANGES` means "no bound". |
| `skin_response` gained an upper bound of 30 uS, which the Section 1 plan did not have | The plan only rejected negatives. But skin conductance during exercise sits in roughly 1 to 20 uS, and a reading of, say, 800 is a sensor fault rather than an extreme person, which is exactly the kind of impossible value this section is meant to catch. Leaving it unbounded would let one broken reading dominate the average. Recorded here as a deliberate deviation from the approved plan rather than an oversight. |
| Flags are recorded separately from rejections | The report has to show both, and they are different events. `flagged_count` and `rejected_count` keep them countable separately, and `flag_notes` and `rejection_notes` keep the reasons apart. *(Originally a single tagged `issues` list. See Section 11 below.)* |
| Rejected records are still counted in `total_count` | `usable + rejected == total` has to hold, otherwise the report cannot honestly say how many observations were received. Verified as an invariant in testing. |

### Alternatives rejected

- *Flagging impossible values instead of rejecting them.* This would keep more
  data, but a value that cannot occur carries no information. Including it with a
  warning shifts the averages while pretending to be cautious.
- *A single signal-quality cutoff.* Simpler to explain, but it forces a choice
  between discarding usable evidence and accepting noise. Two tiers cost one
  extra constant and one extra branch.
- *Collecting every problem with a record rather than stopping at the first.*
  More thorough, but a record with a missing field cannot be range-checked
  anyway, so most of the extra output would be noise about consequences of the
  first failure.

### Verified

All fifteen rejection paths produce a distinct readable message. The
signal-quality boundary behaves exactly as specified, with 0.49 rejected, 0.50
and 0.69 flagged, and 0.70 clean. A mixed session reports `total=5 usable=2
flagged=1 rejected=3` with both invariants holding.

---

## Section 4: Calculations

### What was built

Three standalone functions: `summarise()`, `heart_rate_zone()` and
`compare_to_reference()`. No classification yet. These produce the figures that
Section 5 decides on.

### Decisions and why

| Decision | Why |
| --- | --- |
| `summarise()` covers four fields, not all six | `timestamp` orders the session rather than measuring the person, and `signal_quality` describes the *sensor* rather than the body. An average of either would be a number with no meaning. "Mean signal quality 0.8" invites a reader to treat sensor confidence as a physiological finding. |
| Only usable observations are summarised, and this holds by construction rather than by a filter | A rejected record never becomes an `Observation` at all, because `from_dict()` raises before the object exists. So `summarise()` cannot average a bad reading even if called carelessly. That is stronger than filtering inside the function, where a future caller could pass the wrong list. |
| Empty input returns `{}` rather than raising | `statistics.mean([])` raises `StatisticsError`. Letting that propagate would force every caller to guard a case the classifier already handles properly as "insufficient data". Returning an empty dictionary lets the empty case travel through the same path as any other and be labelled at the one place that decides labels. |
| `heart_rate_zone()` exists as its own function, taking `bands` as an argument | Both `compare_to_reference()` and the Section 5 classifier need to place an average heart rate against the participant's bands. Written once, the report and the verdict can never disagree. Written twice, they could drift apart silently. Taking `bands` as a parameter means the function holds no thresholds and only compares. |
| `compare_to_reference()` reads every threshold from the participant | `heart_rate_bands()` for the bands, `normal_temperature` for temperature. Nothing is recalculated locally. This is what makes `Athlete` work, and what lets two people with identical readings be described differently, which is the entire point of storing reference values per person. |
| `above_resting` is included alongside the zone | The zone answers "how hard was this?". The raw bpm above resting answers "by how much?". The report reads better with both, and it costs one subtraction. |

### The temperature tolerance, a deviation worth naming

`TEMPERATURE_TOLERANCE = 0.5` is a module constant rather than a participant
value. The instruction for this section was that thresholds come from the
participant and nothing is hard-coded, so this needs justifying rather than
hiding.

The participant supplies the *reference point*, `normal_temperature`. The
tolerance is the width of the band around it that still counts as "normal".
Without one, a difference of 0.01 C would be reported as "above normal", which is
noise dressed up as a finding.

It is deliberately kept out of classification, so no label depends on it. It only
decides whether the report prints "normal", "above normal" or "below normal", and
the signed difference is reported alongside regardless, so a reader can always see
the underlying number. If a per-person tolerance is wanted later it moves onto
`Participant` without changing any caller.

### Alternatives rejected

- *Returning flat keys like `heart_rate_avg` and `heart_rate_min`.* Simpler to
  print, but the nested `{"avg", "min", "max"}` shape lets the report loop over
  fields uniformly instead of naming twelve keys by hand.
- *Having `summarise()` take the `Session` rather than a list.* This would couple
  a calculation to a class for no gain, and makes it awkward to test on a handful
  of observations without building a session around them.
- *Reporting temperature as a bare signed difference with no wording.* Honest,
  but it pushes the interpretation onto the reader of a report whose whole
  purpose is to interpret.

### Verified

`summarise()` matches hand-calculated means. Rejected records are absent from the
averages, confirmed with a 4-record session containing 2 rejections, which
averages only the 2 usable readings. Empty input returns `{}` from both
functions. Zone boundaries land exactly on the band edges: 93.9 below elevated,
94.0 elevated, 129.9 elevated, 130.0 high. And the same summary yields "elevated"
for an untrained participant but "high" for an athlete, which confirms thresholds
are read per person.

---

## Section 5: Classification and recovery

### What was built

`split_into_thirds()`, `detect_recovery()`, `classify_session()`, and
`Session.analyse()`, which assembles the result dictionary.

### Decisions and why

| Decision | Why |
| --- | --- |
| Recovery compares the final third against the **peak** third, not the first third | A session that starts calm, works hard, then eases off has its peak in the *middle*. Measuring from the first third would compare a warm-up against a cooldown and report a modest rise, missing the recovery entirely. The peak third is found by taking whichever third has the highest average heart rate. |
| Uneven counts put the remainder in the later thirds | With 5 observations the split is 1 / 2 / 2 rather than 2 / 2 / 1. The final third is the part the verdict rests on, and a one-reading final third would make the whole classification depend on a single number. |
| `detect_recovery()` returns its evidence, not just a boolean | The explanation has to name the figures that decided the label, and the report has to show the drop percentages. Returning only `True` or `False` would force the caller to recompute them, which means a second implementation that could disagree with the first. |
| When recovery is *not* detected, the result says which condition failed | "Not recovering" is unhelpful on its own. The `reason` field distinguishes "nothing to recover from", where the peak never reached the elevated band, from "the decline was too shallow". Those are different findings about the session. |
| Activity drop is 0.0 rather than undefined when peak activity is 0.0 | Someone motionless throughout has a peak activity of exactly 0.0, and dividing by it would raise `ZeroDivisionError`. Nothing fell, so the drop is zero, which correctly fails the recovery test rather than crashing. |
| `MODERATE_ACTIVITY_LEVEL` and `HIGH_ACTIVITY_LEVEL` are module constants, not participant values | `activity_level` is already a 0 to 1 scale meaning the same thing for everyone, unlike heart rate where the same bpm means different efforts for different people. A per-person activity threshold would imply a personal reference the data does not carry. |
| When a session is labelled "recovering", the explanation also says it met the intensity test | Otherwise a reader sees "recovering" on a session that was plainly hard and concludes the effort went unnoticed. The sentence is appended only when the session actually met the high or moderate activity test, so it never claims something untrue. |
| `analyse()` returns *copies* of the note lists | Without `list(...)`, a caller holding the result could append to them and silently alter the session's own record of what happened. |
| `analyse()` adds a `session` key to the planned dictionary | The report needs a title for each scenario, and `main.py` prints several in a row. Minor addition to the Section 1 shape, recorded here. |

### Alternatives rejected

- *Comparing the final third against the first third.* Simpler to explain, but
  wrong for the exact scenario the assignment asks for. See above.
- *Halves instead of thirds.* A two-way split has no middle, so a session cannot
  have a peak distinct from its start or end, and "worked hard then eased off"
  becomes unrepresentable.
- *Letting "high activity" win over "recovering".* This would make the label
  easier to search for, but it throws away the more specific finding. Documented
  at length in the Section 1 plan.

### Verified: all five required scenarios plus three guard cases

| Scenario | Result |
| --- | --- |
| Resting | `resting`, with 74.5 bpm below the 94.0 elevated band and activity 0.05 |
| Moderate | `moderate activity`, with 102.5 bpm reaching elevated and activity 0.35 |
| High | `high activity`, with 147.5 bpm reaching the 130.0 high band and activity 0.80 |
| Activity then recovery | `recovering`, HR fell 32% from 153.5 to 104.0, activity fell 76% |
| Poor-quality or invalid | `insufficient data`, 4 of 6 records rejected, 2 usable |
| Too few readings | `insufficient data`, 3 usable against 5 required |
| Sitting still, HR drifting down | `resting`, **not** recovering, because "peak third averaged 79.0 bpm, which never reached the elevated band (94.0 bpm)" |

### The override, demonstrated

The decisive test for `Athlete.recovery_thresholds()` is a decline that falls
*between* the two bars. Peak third 130 bpm, final third 116 bpm, a 10.8% drop,
with activity falling 50%:

| Participant | Required drop | Actual | Detected | Label |
| --- | --- | --- | --- | --- |
| `Participant` (resting 70) | 10% | 10.8% | yes | **recovering** |
| `Athlete` (resting 45) | 15% | 10.8% | no | **moderate activity** |

Identical readings, different verdict, decided solely by the overridden method.
This is the example to cite in the README as evidence the inheritance is
functional rather than decorative.

### Known cosmetic issue

The "why not" message rounds to whole percents, so a 10.8% drop prints as "heart
rate fell 11%, short of the 15% required". That is accurate to the rounding, and
the unrounded value is available in the result dictionary, but it is worth
knowing when reading the two side by side.

---

## Section 6: Console report

### What was built

`format_report(result)`, rendering the result dictionary as plain text in the
seven sections specified. `Session` gained `flag_notes` and `rejection_notes`.

### Decisions and why

| Decision | Why |
| --- | --- |
| `format_report()` **returns** a string rather than printing | Tests can then assert on the output directly, and `main.py` decides where it goes. A function that prints can only be tested by capturing stdout, which is more machinery for less certainty. `main.py` calls `print(format_report(result))`. |
| Rounding happens only inside `format_report()` | Stored values keep full precision, so no intermediate calculation inherits a rounding error. The displayed figure is tidied at the last possible moment, which is also why the same value can be shown to 1 decimal in the table and 2 in the explanation without either being wrong. |
| `Session` stores `flag_notes` and `rejection_notes` separately | The report has to show the two groups separately. The alternative was for `format_report()` to search each note for the word "flagged", which couples the report's correctness to the exact wording of a message elsewhere in the file, and would break silently if that wording were ever changed. String-parsing your own output is a latent bug. |
| ~~`issues` keeps every note in arrival order, tagged `flagged -` / `rejected -`~~ | ~~The chronological list is what a reader wants when asking "what happened to my data, in order".~~ **Superseded in Section 11.** The third list held nothing the other two did not, since each note already names its record number. |
| Long sentences wrap with `textwrap` | The explanation and the recovery reason are full sentences of unpredictable length. Without wrapping they run off the edge of a terminal. `textwrap` is standard library. |
| The recovery section always says something | Either the drops with their required thresholds, or the reason none was found. A blank section would read as "not checked" rather than "checked, and no". |
| Empty summary and empty comparison print an explicit sentence | "No usable observations to summarise." is a finding. A blank space under a heading looks like a bug in the program. |
| Report width fixed at 64 characters, verified to stay under 78 | Fits any terminal without wrapping, and keeps the output readable when pasted into the README as example output. Checked programmatically: no line exceeds 78 characters and none carries trailing whitespace. |

### Alternatives rejected

- *Printing directly from `format_report()`.* See above. Untestable without
  capturing stdout.
- *Rounding the values inside `summarise()`.* This would make the report simpler,
  but every later calculation would then work from rounded inputs, and the
  rounding would be invisible to anyone reading the result dictionary.
- *A single combined "issues" list in the report.* The assignment asks for usable
  versus rejected counts to be explained, and a flagged reading is a
  fundamentally different event from a rejected one. Mixing them makes the reader
  do the sorting.

### Rounding, resolved with per-field decimal places

The section was specified as 1 decimal for the whole summary table. That is right
for heart rate, skin response and temperature, but lossy for `activity_level` in
a way that showed up in the output. A resting session with a true average of 0.05
printed as

```
  Activity level         0.1       0.1       0.1
```

while the explanation two sections below correctly said "average activity 0.05".
The same figure appeared twice in one report with two different values, which
invites a reader to distrust one of them. `activity_level` is a 0 to 1 scale, so
one decimal leaves only ten possible values and anything under 0.05 collapses to
zero.

Resolved with `FIELD_DECIMALS`: 1 place for the three sensor readings, 2 for
`activity_level`. The table now reads `0.05` and agrees with the explanation.

I chose the per-field table over a uniform 2 decimals because `73.00 bpm` claims
more precision than a heart rate sensor provides. That trailing zero is not
measurement, it is decoration. Decimal places are a property of what is being
measured, so they belong in a table keyed by field, next to the units and labels
that are already keyed the same way.

---

## Section 7: Sample data

### What was built

`sample_data.py` with six scenarios, and `main.py` reduced to a loop over them.

| Scenario | Label produced | Readings |
| --- | --- | --- |
| Sitting at a desk | `resting` | 6 |
| Brisk walk | `moderate activity` | 6 |
| Hill sprints | `high activity` | 6 |
| Interval session with cooldown | `recovering` | 9 (Athlete) |
| Cycle commute, sensor slipping | `moderate activity` | 10, of which 7 usable, 2 flagged, 3 rejected |
| Watch taken off after a minute | `insufficient data` | 3 |

### Decisions and why

| Decision | Why |
| --- | --- |
| Records are written as literal dictionaries, not generated in a loop | This is the data file. What the analyzer receives should be readable exactly as written, in the format the brief specifies. A loop like `[record(t, 70 + t) for t in range(6)]` is shorter but hides the values behind arithmetic, and the one file a marker is most likely to open to check "does this match the required format?" should answer that question directly. |
| Poor quality and insufficient data are separate scenarios | They are different failures. The poor-quality session has a faulty sensor but still supports a verdict, while the insufficient one has perfect readings and simply too few. Merging them would lose that distinction, and the poor-quality scenario would collapse into "insufficient data" and demonstrate nothing about flagging. |
| The poor-quality scenario carries one of each rejection kind | Missing field, impossible value at 320 bpm, and signal below the cutoff. The three rejection *categories* each appear once in normal output, so running `main.py` exercises them without a test harness. |
| The recovery scenario uses the `Athlete` | A normal run of `main.py` then shows the override applied. The report reads "15% required" rather than 10%, and the bands are 74.0 / 117.5 rather than Jonathan's 94.0 / 130.0. The inheritance is visible in the program's ordinary output rather than only in a test. |
| Everything else uses one `Participant` | Differences between the reports then come from the data rather than from the person. Only the recovery scenario varies the participant, and it varies it for a reason. |
| Scenario labels are situations, not categories | "Hill sprints" rather than "high activity scenario". A label naming the expected answer would make the report look like it was told what to conclude. |
| `main.py` holds a six-line loop and nothing else | The assignment requires `python3 main.py` to work. It does not require `main.py` to contain reasoning, and any logic added here would be logic `tests.py` cannot reach. |

### Alternatives rejected

- *Generating records programmatically to keep the file short.* See above.
- *Making the recovery scenario 6 readings like the others.* Thirds of 6 give 2
  readings each, so warm-up, effort and cooldown would each rest on two numbers.
  Nine gives three per phase and makes the peak unambiguous.
- *Putting the expected label in each scenario dictionary.* This would let
  `main.py` check itself, but that is what `tests.py` is for, and a data file
  asserting its own answer is circular.

### Verified

`python main.py` runs clean and produces all six expected labels. The
poor-quality scenario reports `total=10 usable=7 flagged=2 rejected=3` and still
receives a real classification, which was the point of sizing it that way.

---

## Section 8: Tests

### What was built

`tests.py`, with 28 tests in six `TestCase` classes, one per area. 213 lines, a
little over the 200 target.

| Class | Covers |
| --- | --- |
| `TestValidation` | 8 tests: one per rejection kind, plus the four signal-quality boundaries |
| `TestParticipant` | 4 tests: the property gate, the resting and maximum cross-check both ways, the `Athlete` override |
| `TestCalculations` | 4 tests: hand-checked summary, empty input, rejected readings excluded, zone boundaries |
| `TestClassification` | 6 tests: one per label, plus that the explanation names its figures |
| `TestRecovery` | 4 tests: the cooldown shape, resting drift, between-the-bars, motionless divide-by-zero |
| `TestReport` | 2 tests: the report contains label and counts, and the nothing-usable case renders |

### Decisions and why

| Decision | Why |
| --- | --- |
| One `record()` helper with keyword overrides, plus one `analyse()` shortcut | Every test needs a valid record differing in one field. Writing all six fields in each of 28 tests would bury what each test is actually about. Two helpers was the agreed limit, and `analyse()` is three lines that remove the same session-building boilerplate from a dozen tests. |
| The band values are written in comments next to the fixtures | `JONATHAN` is resting 70, giving elevated 94.0 and high 130.0. A test asserting `heart_rate_zone(94.0, bands) == "elevated"` is meaningless unless the reader knows where 94.0 comes from. The comment saves them recomputing the reserve formula. |
| `subTest` for the range checks | `-40` and `320` are the same rule failing at both ends. `subTest` reports which value failed instead of stopping at the first. |
| Classification tests use flat heart rates where possible | A constant 105 bpm cannot accidentally satisfy the recovery test, so `test_moderate_activity` fails only if the moderate rule breaks. Tests that could fail for two reasons are harder to read when they go red. |
| The between-the-bars test asserts on *both* participants in one test | The point is not that each is classified correctly in isolation, it is that identical readings diverge. Splitting it into two tests would lose the comparison the test exists to make. |

### Mutation check: the tests were tested

A suite that passes proves nothing on its own. It has to fail when the code is
wrong. So I deliberately broke four rules in `analyzer.py`, one at a time, to
confirm the suite notices:

| Mutation | Result |
| --- | --- |
| `SIGNAL_QUALITY_REJECT` 0.50 to 0.40 | caught by `test_signal_quality_boundaries` |
| `Athlete` recovery bar 0.15 to 0.10 | caught by `test_between_the_bars_separates_participant_from_athlete` |
| Removed the "something to recover from" condition | caught by `test_not_detected_when_resting_heart_rate_drifts_down` |
| `MINIMUM_USABLE_OBSERVATIONS` 5 to 3 | caught by `test_insufficient_data` |

All four were caught, and `analyzer.py` was restored and confirmed identical to
the committed version afterwards. The third mutation is the one worth mentioning
in a viva. Removing that condition still leaves every *other* test passing, and
only the resting-drift case notices, which is precisely why that test exists.

### Alternatives rejected

- *Testing `format_report()` by comparing whole output against a stored string.*
  This would break on every wording or spacing change, so it would get deleted or
  rubber-stamped the first time it failed. Asserting on the few substrings that
  carry meaning survives cosmetic edits.
- *A test per scenario in `sample_data.py`.* This would duplicate the
  classification tests using slower, larger fixtures, and tie the suite to
  demonstration data that exists to be readable rather than minimal.

### Result

```
Ran 28 tests in 0.007s

OK
```

---

## Section 9: README

### What was built

`README.md` in the twelve specified sections, written from this file.

### Decisions and why

| Decision | Why |
| --- | --- |
| Example output was copied from a real run and then verified programmatically | Pasted output rots the moment a format string changes, and a README showing output the program does not produce is worse than one showing none. A check script re-runs `main.py`, extracts the fenced blocks from the README and asserts each appears verbatim in the real output. Both blocks verified. |
| The two example scenarios are the cycle commute and the interval session | Between them they exercise everything: flagged and rejected readings side by side, a real classification surviving a faulty sensor, recovery detection, and the `Athlete` subclass with its 15% requirement visible in the output. The resting and moderate reports are shorter but demonstrate nothing the other two do not. |
| Internal helpers are listed as *not* counted | `require_number()`, `describe_value()`, `rejected()` and `split_into_thirds()` are real functions, but counting them towards the required four would pad the number with plumbing. Six functions are named as the standalone ones and the helpers are declared separately, so the count is honest. |
| The inheritance section states the between-the-bars result with its numbers | "The subclass overrides a method" is a claim about code. "Identical readings give `recovering` for one and `moderate activity` for the other" is a claim about behaviour, and it names the test that proves it. |
| Known limitations includes things not asked for | Timestamps being used only for ordering, and the single weak-signal tier, are genuine weaknesses that were not on the specified list. A limitations section listing only the limitations one was told to list is a weaker document. |
| No marketing tone, no feature claims | The README describes what the program does and where each requirement is met. Anything else is padding a marker has to read past. |

### Verified

Both fenced report blocks appear verbatim in the output of a fresh
`python main.py`. All eleven function names cited in the README exist in
`analyzer.py`, and `Athlete` was confirmed to override exactly
`recovery_thresholds` and `describe`, not `heart_rate_bands`, which is what the
README states.

---

## Section 10: Final check and submission

Requirement checklist verified programmatically against a fresh clone rather than
from notes: 4 classes, composition confirmed in `Session.__init__`, 2 properties
with private backing attributes, `Athlete` overriding `recovery_thresholds` and
`describe`, `Observation.from_dict` as the classmethod, 11 functions, `analyse()`
returning an 11-key dictionary, 6 scenarios, 28 tests.

Fresh-clone test passed. Cloned to a temporary folder, `python main.py` produced
all six expected labels and `python -m unittest tests.py` reported 28 tests OK.
This is the check that proves the repository is self-contained and does not
depend on a file that exists only on the development machine.

Working tree clean, 8 tracked files, and no `__pycache__`, `.venv`, `.pyc` or
`.env`.

The push could not be run from the assistant's shell. It is non-interactive with
no attached terminal, so Git Credential Manager has no way to display a sign-in
window and the push fails with "terminal prompts disabled". The push is run
manually from an ordinary terminal instead. Not a repository problem.

---

## Section 11: Removing redundancy

Two pieces of dead weight removed after review.

### 1. `Session.issues` deleted

The class kept three lists: `issues`, holding every note in arrival order tagged
`flagged -` or `rejected -`, plus `flag_notes` and `rejection_notes` holding the
same strings grouped by kind. My Section 6 justification for the third list was
that it preserved chronological order across both kinds.

That justification does not survive scrutiny. Every note already begins
`record N:`, so arrival order is recoverable from either grouped list by reading
the record numbers. The combined list held no information the other two did not,
and `format_report()` never read it. Only the grouped lists were ever used. It
was state maintained for a reader who never existed.

Removed: the list, both `append` calls in `add_observation()`, and the `issues`
key from the result dictionary. Nothing outside `analyzer.py` referenced it.
`tests.py`, `main.py`, `sample_data.py` and `README.md` were all checked before
deleting.

### 2. `FIELD_LABELS` trimmed to the four summarised fields

It carried entries for `timestamp` and `signal_quality`, which are never
labelled. They are deliberately excluded from `SUMMARY_FIELDS`, and the summary
table is the only place `FIELD_LABELS` is read. The two extra entries implied
those fields might one day be summarised, which contradicts the reasoning
recorded in Section 4.

`FIELD_UNITS` keeps all six entries and was left alone. `describe_value()` uses
it to build rejection messages for every field in `VALUE_RANGES`, including
`timestamp` and `signal_quality`. The two tables look parallel but are not, and
trimming both would have broken the rejection messages.

### Verified

28 tests still pass, `main.py` still produces the six expected labels, and both
README example blocks still match real output.

---

## Section 12: Generator integration

Instructor-supplied starter files arrived after Section 11: `data_generator.py`,
`example_usage.py` and `DATA_DESCRIPTION.md`. The marker will run this program
against `generate_fitness_data()`, so the demonstration data now comes from
there rather than from records I wrote by hand.

### What was built

`data_generator.py` copied into the repository unchanged, a second alternative
constructor in `Participant`, a skin-response comparison, `sample_data.py`
rebuilt around the generator, and seven new tests.

Only the generator was added. `example_usage.py` and `DATA_DESCRIPTION.md` stay
out of the repository, since the first is a demonstration script this project
does not need and the second is reference material rather than code.

### Decisions and why

| Decision | Why |
| --- | --- |
| `data_generator.py` copied in byte for byte and never edited | It is the instructor's file and the marker's reference point. I verified the copy with a SHA-256 hash against the source, and confirmed afterwards that it has not changed since the commit that added it. Editing it, even to tidy something, would mean the program was tested against a file the marker does not have. |
| `Participant.from_profile(profile)` as a second `@classmethod` | The generator names its fields differently from this program: `participant_id` rather than `name`, `baseline_heart_rate` rather than `resting_heart_rate`, and so on. Putting that translation in one classmethod means no call site has to know about it, and `sample_data.py` never has to spell out the mapping. |
| `from_profile` builds with `cls()` rather than naming `Participant` | This is what makes `Athlete.from_profile(profile)` return an `Athlete` with its own 15% recovery bar, inherited rather than reimplemented. Hard-coding the class name would have silently downgraded every athlete to a plain participant. |
| `from_profile` raises `ValueError` listing every missing field | A `KeyError` naming one field would send someone hunting for a typo. Checking all four first and reporting them together says what shape the profile actually has to be. |
| `normal_skin_response` defaults to `None` rather than to a number | The generator supplies a baseline, but a participant built by hand has no measured skin response. Giving one a default number would compare the session against a value nobody recorded. |
| The skin-response block appears in the comparison only when the reference exists | Same reasoning. `compare_to_reference()` adds the block when `normal_skin_response` is set and omits it otherwise, and `format_report()` follows. A hand-made participant's report is unchanged from before. |
| The README limitation about skin response having no reference was removed | It was true when written, and is not any more. Leaving it would have been a documented weakness the program no longer has. |
| `seed=42` and `number_of_windows=12`, fixed in `sample_data.py` | The generator is reproducible for a given seed, which is what lets the README paste real output and still have it match on someone else's machine. An unfixed seed would make the example blocks wrong on every run. |
| Generated participants keep the default maximum heart rate of 190 | The profile carries a baseline heart rate but no maximum, so there is nothing to map. This is now recorded in the README limitations, because it means every generated participant has bands computed from a population figure rather than a measured one. |

### The two hand-made scenarios, and why each survives

Five scenarios come from the generator. Two do not, and both have a reason
beyond preference.

**The recovery data judged as an `Athlete`.** The observations are the same ones
the generator produced for the plain recovery session, rebuilt with
`Athlete.from_profile()`. Because the readings are identical, any difference in
the report comes from the subclass and nothing else. The report shows
`15% required` instead of `10% required`. Without this scenario, an ordinary run
of `main.py` would never exercise the override at all, and the inheritance would
only be visible inside `tests.py`.

**The three-reading session.** `generate_fitness_data()` raises `ValueError` for
fewer than six windows, so it cannot produce a session too short to judge. The
minimum-usable rule needs fewer than five usable readings to fire on its own
merits, which means this case has to be written by hand or not demonstrated.

### The poor_quality collision

The generator's `poor_quality` scenario injects a fault into every record on a
`timestamp % 4` cycle: a `None` heart rate, then 265 bpm, then an activity level
of -0.20, then a `None` skin response. With 12 windows that is 12 faulty records
and no survivors, so the session classifies as `insufficient data`.

That collides with a distinction drawn back in Section 7. The old hand-written
"cycle commute" scenario was sized specifically so that some readings survived,
and the README argued that poor quality and insufficient data are different
failures: a faulty sensor that still supports a verdict, against perfect
readings and too few of them. With the generator's version, poor quality
produces the same label as the too-short session.

I considered keeping the hand-written poor-quality scenario alongside the
generated one so the degraded-but-usable case was still shown. I did not, for
two reasons. The marker will run the generator, so the generator's behaviour is
what the program has to be honest about. And a scenario whose only purpose is to
demonstrate a nicer outcome than the real data produces is closer to decoration
than evidence.

What changed instead. The README claim that poor quality "still supports a
verdict" was removed, because it is no longer true. `main.py` now prints
`INSUFFICIENT DATA` twice, and the two are distinguished by the counts rather
than the label: one session has 12 records of which none is usable, the other
has 3 records all of which are fine. The rejection list on the poor-quality
report names all 12 reasons, so the difference is visible without reading the
label.

The flagging path is the real loss here. No generated scenario produces a
signal quality between 0.50 and 0.69, so the flagged-but-kept tier no longer
appears in ordinary output. It is still covered by
`test_signal_quality_boundaries` and by the report tests, but a reader of
`main.py` alone would not see it.

### Tests added

Seven, bringing the suite to 35.

| Class | Covers |
| --- | --- |
| `TestFromProfile` | 3 tests: every field mapped, the `Athlete` variant returning an `Athlete` with a 0.15 bar, and a profile missing fields raising `ValueError` |
| `TestSkinResponseComparison` | 2 tests: the block present with a reference and absent without one |
| `TestGeneratedData` | 2 tests: `poor_quality` at seed 42 rejecting all 12 records and classifying as insufficient data, and the same seed reproducing identical data |

Both new behaviours were mutation-checked the same way as Section 8. Swapping
`baseline_temperature` and `baseline_skin_response` in the mapping was caught,
and making the skin comparison unconditional was caught. `analyzer.py` was
restored and verified identical afterwards.

### Updated counts

| | Before | Now |
| --- | --- | --- |
| Scenarios in `main.py` | 6 | 7 |
| Tests | 28 | 35 |
| Tracked files | 8 | 9 |
| `TestCase` classes | 6 | 9 |
| Classmethods | 1 | 2 |

The ninth tracked file is `data_generator.py`. `requirements.txt` now also names
`random`, which the generator uses and which is standard library like everything
else.

### Verified

All five generated scenarios classify as their names suggest: resting, moderate
activity, high activity, recovering, and insufficient data for poor quality.
With seed 42 the profile gives a baseline heart rate of 78 bpm, so the bands
come out at 100.4 and 134.0.

The recovery session falls 30.2%, which clears both the 10% and the 15%
requirement, so both the plain and the trained version are labelled
`recovering`. The override is still visible in the report text as
`15% required`. The verdict-changing proof remains
`test_between_the_bars_separates_participant_from_athlete`, which uses a
hand-built 10.8% drop sitting between the two bars.

Fresh clone runs clean: seven scenarios with the expected labels, 35 tests OK.
Both README example blocks match real output.
