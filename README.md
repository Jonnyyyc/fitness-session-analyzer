# Smart Fitness Session Analyzer

Option A - Smart Fitness Session Analyzer

Author: Jonathan Christensen
Student number: jonathan4495

---

## Description

This program analyses a recorded fitness session. It takes a participant's
reference measurements plus a list of sensor observations, checks each
observation against a set of validation rules, and summarises whatever survives.
It then compares the session against that participant's own resting and maximum
heart rate before classifying it as resting, moderate activity, high activity,
recovering, or insufficient data. Results come back as a dictionary and are
printed as a plain-text report that says how many observations were usable and
why the session got the label it did.

The program reads the output of the instructor-supplied
`generate_fitness_data()` function. Five of the seven demonstration scenarios in
`sample_data.py` are produced by that generator, so running `main.py` shows the
analyzer working on the same data a marker would feed it.

---

## Install and run

```bash
git clone https://github.com/Jonnyyyc/fitness-session-analyzer.git
cd fitness-session-analyzer
python3 main.py
```

On Windows the command is usually `python` rather than `python3`:

```bash
python main.py
```

Tests run the same way:

```bash
python3 -m unittest tests.py      # macOS / Linux
python -m unittest tests.py       # Windows
```

Standard library only, so there is no installation step and nothing to
download. The program uses `statistics`, `textwrap` and `unittest`, and the
instructor's generator uses `random`. All four ship with Python. Developed and
tested on Python 3.14.

### Using the generator

`data_generator.py` is the instructor's file, copied into the repository
unchanged. It returns a participant profile and a list of observations, and
`Participant.from_profile()` turns the profile into an object this program can
work with:

```python
from analyzer import Participant, Session, format_report
from data_generator import generate_fitness_data

profile, observations = generate_fitness_data(
    participant_id="P001",
    scenario="moderate_activity",
    seed=42,
    number_of_windows=12,
)

session = Session(Participant.from_profile(profile), label="Demo session")
session.add_many(observations)
print(format_report(session.analyse()))
```

Passing a seed makes the data reproducible, which is why `sample_data.py` fixes
it at 42. Use `Athlete.from_profile(profile)` instead to judge the same readings
as a trained participant.

---

## Project structure

| File | What it does | Source |
| --- | --- | --- |
| `README.md` | This document. | Required by the brief |
| `main.py` | Entry point. Loops over the sample scenarios and prints a report for each. Holds no logic beyond that loop. | Required by the brief |
| `sample_data.py` | The seven demonstration scenarios, five built from the generator and two by hand. | Required by the brief |
| `tests.py` | 35 unit tests across eight `TestCase` classes. | Required by the brief |
| `requirements.txt` | Records that the project needs nothing outside the standard library. | Required by the brief |
| `data_generator.py` | Produces simulated participant profiles and observations. Copied in unchanged and never edited. | Instructor-supplied |
| `analyzer.py` | All four classes and every standalone function. The whole program lives here. | Added by me |
| `NOTES.md` | Working decision log, written as the project went along. The README is built from it. | Added by me |
| `.gitignore` | Keeps `__pycache__` and editor files out of the repository. | Added by me |

`analyzer.py` is not on the brief's file list. I put the classes in their own
module so that `main.py` could stay a thin entry point and `tests.py` could
import the classes without pulling in the code that prints reports.

---

## Class design

All four classes live in `analyzer.py`. `data_generator.py` is the instructor's
file and defines no classes.

| Class | Responsibility |
| --- | --- |
| `Participant` | A person and their reference measurements: resting heart rate, maximum heart rate, normal skin temperature, and optionally a normal skin response. Turns those into the thresholds used to judge a session, through `heart_rate_bands()` and `recovery_thresholds()`. |
| `Athlete(Participant)` | A trained participant. Same role, but recovery is judged against a stricter requirement. |
| `Observation` | One observation window: the six-field sensor record from the brief, plus any quality warnings attached to it. |
| `Session` | One recording: a participant and the list of observations taken from them. Accepts or rejects incoming records, counts both, and produces the result dictionary. |

Four classes, and I stopped there deliberately. I considered a separate
`Validator` class and a separate `Report` class, but each would have held no
data and exposed a single method. That is a function with extra ceremony around
it.

---

## Where each OOP requirement is met

| Requirement | File | Where |
| --- | --- | --- |
| Composition | `analyzer.py` | `Session.__init__` holds a `Participant` and a list of `Observation` objects. A session is not a kind of participant, it contains one. |
| Encapsulation (`@property`) | `analyzer.py` | `Participant._resting_heart_rate` and `_max_heart_rate`, reached through the `resting_heart_rate` and `max_heart_rate` properties. The setters reject non-numbers, out-of-range values, and any combination where the resting rate is not below the maximum. |
| Inheritance and overriding | `analyzer.py` | `Athlete.recovery_thresholds()` overrides `Participant.recovery_thresholds()`, raising the required heart-rate drop from 10% to 15%. `Athlete.describe()` also overrides the parent. |
| `@classmethod` | `analyzer.py` | Two of them. `Observation.from_dict(raw)` builds one observation from a raw record and raises `ValueError` if the record fails validation. `Participant.from_profile(profile)` builds a participant from the generator's profile dictionary, translating its field names into this program's. Because it builds with `cls()`, `Athlete.from_profile()` returns an `Athlete`. |

The inheritance does real work rather than sitting there to tick a box. Give
both classes the same readings, a peak third of 130 bpm falling to 116, which is
a 10.8% drop, and a `Participant` comes back as **recovering** while an
`Athlete` comes back as **moderate activity**. Only the first clears its 10%
requirement. `test_between_the_bars_separates_participant_from_athlete` covers
this, and I confirmed the test fails if the override is removed.

---

## Standalone functions

All in `analyzer.py`.

| Function | Kind | Purpose |
| --- | --- | --- |
| `validate_observation(raw)` | validation | The single place the observation rules live. Returns `ok`, a plain-English `reason` when rejected, and any `flags`. |
| `summarise(observations)` | calculation | Average, minimum and maximum for each measured field. |
| `heart_rate_zone(average, bands)` | calculation | Places an average heart rate in one of the participant's bands. |
| `compare_to_reference(summary, participant)` | calculation | Measures the session against that participant's own reference values. |
| `detect_recovery(observations, participant)` | calculation | Whether heart rate and activity both fell towards the end of the session. |
| `format_report(result)` | presentation | Renders the result dictionary as plain text. Returns a string, and `main.py` prints it. |

`require_number()`, `describe_value()`, `rejected()` and `split_into_thirds()`
are small internal helpers. I have not counted them above, since padding the
number with plumbing would be dishonest.

---

## Validation rules

Every record gets asked two separate questions. Could this have happened? And do
we trust the sensor that reported it?

### Rejected, meaning discarded and not counted as usable

A value that cannot occur carries no information. Averaging it in would corrupt
every figure downstream, and no warning label makes that safe.

| Problem | Rule |
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

### Flagged, meaning kept and counted but with a warning

| Problem | Rule |
| --- | --- |
| Weak signal | Signal quality 0.50 to 0.69 |

A reading the sensor half-trusts is still evidence. Throwing it away can push a
session below the five-observation minimum and produce "insufficient data" for a
session that really happened, which is a worse outcome than including a slightly
noisy reading and saying so in the report.

Booleans get rejected explicitly anywhere a number is expected. This is a Python
quirk: `bool` subclasses `int`, so `True` would otherwise be accepted as the
number 1, and a heart rate of `True` should be an error rather than 1 bpm.

---

## Classification rules

### Heart rate bands, based on heart rate reserve

Effort is measured against the span between a person's resting and maximum heart
rate rather than as a ratio to their resting rate:

```
reserve  = max_heart_rate - resting_heart_rate
elevated = resting_heart_rate + 0.20 * reserve
high     = resting_heart_rate + 0.50 * reserve
```

`max_heart_rate` defaults to 190 and can be set per participant. The generator
does not supply one, so generated participants use the default.

| Participant | Resting | Reserve | Elevated band | High band |
| --- | --- | --- | --- | --- |
| Resting 70 | 70 bpm | 120 bpm | 94.0 bpm | 130.0 bpm |
| Resting 45 | 45 bpm | 145 bpm | 74.0 bpm | 117.5 bpm |

### Activity thresholds

`activity_level` is already a 0 to 1 scale meaning the same thing for everyone,
so unlike heart rate it needs no per-person reference.

| Threshold | Value |
| --- | --- |
| Moderate | 0.20 |
| High | 0.60 |

### Order of checks, first match wins

| # | Label | Condition |
| --- | --- | --- |
| 1 | insufficient data | Fewer than 5 usable observations |
| 2 | recovering | Recovery detected, see below |
| 3 | high activity | Mean heart rate reaches the high band, or mean activity is 0.60 or more |
| 4 | moderate activity | Mean heart rate reaches the elevated band, or mean activity is 0.20 or more |
| 5 | resting | Everything else |

### Recovery rule

The session gets split into three consecutive parts by time. The final third is
compared against the peak third, meaning whichever third has the highest average
heart rate. All three conditions have to hold:

1. Mean heart rate has fallen by at least the participant's required drop, which
   is 10% for `Participant` and 15% for `Athlete`
2. Mean activity has fallen by at least 30%
3. The peak third's mean heart rate reached the elevated band, so there was
   something to recover from in the first place

Uneven counts put the remainder in the later thirds, so 5 readings split 1 / 2 /
2. The final third is what the verdict rests on, and I did not want a
one-reading final third deciding the whole classification.

---

## Assumptions and design decisions

### Why heart rate reserve, and not a ratio

My first version measured effort as mean heart rate divided by resting heart
rate. That turned out to be wrong, and not in a way I could patch.

A ratio quietly assumes everyone has the same ceiling. They do not. What a
person actually has available is the gap between their resting rate and their
maximum, and two people with the same resting rate but different maximums have
different amounts of room to work with. A ratio cannot see that at all.

The giveaway was the athlete case. Under the ratio model, a low resting heart
rate made the effort score go up, so a fitter person looked like they were
working harder. I had added an `Athlete` subclass to compensate. Once I noticed
the subclass existed purely to cancel out a distortion the formula itself
introduced, it was clear the formula was the problem.

Heart rate reserve fixes it properly, and a trained participant then needs no
special case for the bands.

### Why recovery is checked before high activity

A hard session that ends in a cooldown passes both tests, so the order of the
checks decides the label. I report **recovering**.

The reasoning is that "recovering" says more. Plenty of sessions are demanding,
so "high activity" on its own is a weak statement. "Recovering" says the session
was demanding and the participant has come back down from it. The explanation
text names the peak intensity too, so the hard stretch still appears in the
report rather than getting buried.

There is a real cost. A session labelled "recovering" will not turn up if you go
looking for "high activity", even though it contained plenty of it. For this
assignment that seemed acceptable, because each session is reported on its own
rather than aggregated across many.

### Why the athlete overrides recovery and not the bands

Once the reserve formula was in place, overriding `heart_rate_bands()` would
have achieved nothing. The formula already accounts for a low resting heart
rate. An override that duplicates what the parent already does is worse than no
override at all, because it hides where the work is actually happening.

What genuinely differs in a trained person is what happens after the effort
stops. Their heart rate drops faster and further. A 10% dip that means a real
cooldown in an untrained person is just normal variation in an athlete, so I
raised the requirement to 15%.

The 30% activity requirement is inherited unchanged through `super()`. How
quickly someone stops moving has nothing to do with fitness.

### Why recovery is measured from the peak third

A session that starts calm, works hard, then eases off has its peak in the
middle. Comparing the end against the beginning would put a warm-up next to a
cooldown, show a small rise, and miss the recovery completely. So the code finds
whichever third had the highest average heart rate and measures the fall from
there.

### Thresholds live in exactly two methods

Nothing outside `heart_rate_bands()` and `recovery_thresholds()` hard-codes a
threshold. `classify_session()` and `detect_recovery()` ask the participant for
its numbers instead of keeping copies.

This is the rule that makes the subclass work at all. If `detect_recovery()` had
its own copy of 0.10 sitting in it, an `Athlete` would be silently judged by the
untrained numbers and nothing would look wrong.

### Rounding happens at display time only

Stored values keep full precision so no calculation inherits a rounding error.
Each measurement gets its own precision in the report: one decimal for heart
rate, skin response and temperature, two for `activity_level`. A 0 to 1 scale at
one decimal only has ten possible values, and anything under 0.05 would collapse
to zero.

### Bad records never become objects

`from_dict()` raises before an `Observation` exists, so a rejected reading cannot
reach the summary statistics even if some future caller passes the wrong list
around.

---

## Example output

Both reports below come from a real run of `python main.py`.

### Poor-quality sensor data, where nothing survives

The generator's `poor_quality` scenario injects a fault into every record on a
four-step cycle: a `None` heart rate, then 265 bpm, then an activity level of
-0.20, then a `None` skin response. With 12 windows that is 12 faulty records,
so all 12 are rejected and the session cannot be classified. This is by design
on the generator's part, and it makes a useful demonstration of the rejection
messages.

```
================================================================
  Session:     Poor-quality sensor data
  Participant: P001 (resting HR 78 bpm, max 190 bpm)
================================================================

OBSERVATIONS
  Total received        12
  Usable                 0
    of which flagged     0  (kept)
  Rejected              12

SUMMARY  (usable observations only)
  No usable observations to summarise.

COMPARISON WITH REFERENCE VALUES
  Nothing to compare.

RECOVERY
  Not detected.
    too few observations to compare start and end

CLASSIFICATION:  INSUFFICIENT DATA
  Only 0 usable observations; at least 5 are needed before a
  session can be classified.

FLAGGED READINGS  (0 kept)
  None.

REJECTED READINGS  (12 discarded)
  - record 1: 'heart_rate' must be a number, got NoneType
  - record 2: 'heart_rate' is 265 bpm, outside the valid range 20 to 250 bpm
  - record 3: 'activity_level' is -0.2, outside the valid range 0.0 to 1.0
  - record 4: 'skin_response' must be a number, got NoneType
  - record 5: 'heart_rate' must be a number, got NoneType
  - record 6: 'heart_rate' is 265 bpm, outside the valid range 20 to 250 bpm
  - record 7: 'activity_level' is -0.2, outside the valid range 0.0 to 1.0
  - record 8: 'skin_response' must be a number, got NoneType
  - record 9: 'heart_rate' must be a number, got NoneType
  - record 10: 'heart_rate' is 265 bpm, outside the valid range 20 to 250 bpm
  - record 11: 'activity_level' is -0.2, outside the valid range 0.0 to 1.0
  - record 12: 'skin_response' must be a number, got NoneType
```

### Recovery, judged as a trained participant

Same generated readings as the plain recovery session, but built with
`Athlete.from_profile()`. The overridden threshold shows up in the output as
`15% required` instead of 10%. The skin response comparison appears here too,
because the generator supplies a `baseline_skin_response` in its profile.

```
================================================================
  Session:     Activity followed by recovery, trained participant
  Participant: P001 (trained, resting HR 78 bpm, max 190 bpm)
================================================================

OBSERVATIONS
  Total received        12
  Usable                12
    of which flagged     0  (kept)
  Rejected               0

SUMMARY  (usable observations only)
  Measurement        Average   Minimum   Maximum   Unit
  Heart rate           112.8      86.0     141.0   bpm
  Skin response          1.6       1.2       1.9   uS
  Temperature           33.1      32.8      33.3   C
  Activity level        0.48      0.10      0.88

COMPARISON WITH REFERENCE VALUES
  Heart rate    112.8 bpm  ->  elevated
                bands: elevated 100.4 bpm, high 134.0 bpm
                +34.8 bpm relative to resting
  Temperature   33.1 C  ->  normal
                reference 32.8 C, difference +0.3 C
  Skin response 1.6 uS
                reference 1.2 uS, difference +0.4 uS

RECOVERY
  Detected.
    Heart rate  131.5 -> 91.8 bpm  (30% fall, 15% required)
    Activity    0.77 -> 0.17       (78% fall, 30% required)

CLASSIFICATION:  RECOVERING
  Recovering: between the session's peak third and its final
  third, heart rate fell 30% (131.5 to 91.8 bpm) and activity
  fell 78% (0.77 to 0.17), meeting the 15% and 30% required. The
  peak third averaged 131.5 bpm, at or above the elevated band
  (100.4 bpm), so there was real effort to recover from. The
  session also met the moderate-activity test; 'recovering' is
  reported because it is the more specific finding.

FLAGGED READINGS  (0 kept)
  None.

REJECTED READINGS  (0 discarded)
  None.
```

`main.py` runs seven scenarios in total. Five come from the generator (resting,
moderate activity, high activity, recovery, poor quality). The sixth is that
same recovery data judged as an `Athlete`. The seventh is a hand-written
three-reading session, which has to be hand-written because
`generate_fitness_data()` refuses fewer than six windows and cannot produce a
session too short to judge.

---

## Tests

```bash
python3 -m unittest tests.py      # macOS / Linux
python -m unittest tests.py       # Windows
```

35 tests across eight `TestCase` classes, covering validation and its boundary
values, the `Participant` property checks, `from_profile()` and its `Athlete`
variant, the calculations, the skin response comparison, each of the five
classifications, recovery detection, the generated data, and the report.

I also checked the tests themselves by mutation, since a suite that passes tells
you nothing unless it also fails when the code is wrong. Breaking the
signal-quality cutoff, the athlete's recovery threshold, the "something to
recover from" condition, the five-observation minimum, the `from_profile` field
mapping, and the skin response guard each produced a test failure. All six were
caught.

---

## Known limitations

- The thresholds are judgement calls. The signal-quality cutoffs of 0.50 and
  0.70, the 20% and 50% reserve fractions, the 0.20 and 0.60 activity levels,
  the 10% and 15% recovery drops and the five-observation minimum are all
  defensible, but none of them is derived from data. They are named constants
  with the reasoning written down rather than numbers buried in conditionals, so
  changing one is a single edit.
- Maximum heart rate defaults to 190. It can be set per participant, but the
  generator does not supply one, so every generated participant uses the
  default. Anyone whose real maximum differs will have their bands shifted.
- Sessions are short. Twelve windows from the generator, or fewer by hand, which
  means a third of a session is three or four readings. Real sensor data would
  arrive far faster and the thirds would carry more weight.
- Timestamps only order the observations. The program assumes readings are
  evenly spaced and never checks the interval, so a session with a long gap in
  the middle is treated exactly like a continuous one.
- There is one weak-signal tier. A reading at 0.51 and one at 0.69 get flagged
  identically, even though the second is a good deal more trustworthy.
- No live input. Observations come either from `generate_fitness_data()` or from
  literal dictionaries. There is no file reading and no device interface.

---

## License

Coursework submitted for ACIT4420 at OsloMet. Not licensed for reuse.
