# Smart Fitness Session Analyzer

**Option A – Smart Fitness Session Analyzer**

Author: Jonathan Christensen
Student number: jonathan4495

---

## Description

This program analyses a recorded fitness session. It takes a participant's
reference measurements and a list of sensor observations, checks each
observation against a set of validation rules, and summarises the readings that
survive. It then compares the session against that participant's own resting and
maximum heart rate and classifies it as resting, moderate activity, high
activity, recovering, or insufficient data. Every result is returned as a
dictionary and printed as a plain-text report that states how many observations
were usable and why the session received the label it did.

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

Run the tests the same way:

```bash
python3 -m unittest tests.py      # macOS / Linux
python -m unittest tests.py       # Windows
```

**Standard library only.** No installation step and no dependencies —
`requirements.txt` records this. The program uses `statistics`, `textwrap` and
`unittest`, all built into Python. Developed and tested on Python 3.14.

---

## Class design

All four classes are in `analyzer.py`.

| Class | Responsibility |
| --- | --- |
| `Participant` | A person and their reference measurements: resting heart rate, maximum heart rate, normal skin temperature. Converts those into the thresholds used to judge a session — `heart_rate_bands()` and `recovery_thresholds()`. |
| `Athlete(Participant)` | A trained participant. Same role, but recovery is judged against a stricter requirement. |
| `Observation` | One observation window: the six-field sensor record from the brief, plus any quality warnings attached to it. |
| `Session` | One recording: a participant and the list of observations taken from them. Accepts or rejects incoming records, keeps count of both, and produces the result dictionary. |

Four classes, deliberately. A separate `Validator` or `Report` class was
considered and rejected: each would hold no data and expose a single method,
which is a plain function with extra ceremony around it.

---

## Where each OOP requirement is met

| Requirement | File | Where |
| --- | --- | --- |
| **Composition** | `analyzer.py` | `Session.__init__` — a `Session` holds a `Participant` *and* a list of `Observation` objects. A session is not a kind of participant; it contains one. |
| **Encapsulation** (`@property`) | `analyzer.py` | `Participant._resting_heart_rate` and `_max_heart_rate`, reached through the `resting_heart_rate` and `max_heart_rate` properties. The setters reject non-numbers, out-of-range values, and any combination where the resting rate is not below the maximum. |
| **Inheritance + overriding** | `analyzer.py` | `Athlete.recovery_thresholds()` overrides `Participant.recovery_thresholds()`, raising the required heart-rate drop from 10% to 15%. `Athlete.describe()` also overrides the parent. |
| **`@classmethod`** | `analyzer.py` | `Observation.from_dict(raw)` — an alternative constructor. The program's real input format is the dictionary from the brief, so building straight from one is the natural entry point. It calls `validate_observation()` and raises `ValueError(reason)` on failure. |

The inheritance is functional rather than decorative. With identical readings —
a peak third of 130 bpm falling to 116 bpm, a 10.8% drop — a `Participant` is
classified **recovering** and an `Athlete` is classified **moderate activity**,
because only the first clears its 10% requirement. This is covered by
`test_between_the_bars_separates_participant_from_athlete` in `tests.py`.

---

## Standalone functions

All in `analyzer.py`.

| Function | Kind | Purpose |
| --- | --- | --- |
| `validate_observation(raw)` | validation | The single place the observation rules live. Returns `ok`, a plain-English `reason` when rejected, and any `flags`. |
| `summarise(observations)` | calculation | Average, minimum and maximum for each measured field. |
| `heart_rate_zone(average, bands)` | calculation | Places an average heart rate in one of the participant's bands. |
| `compare_to_reference(summary, participant)` | calculation | Measures the session against that participant's own reference values. |
| `detect_recovery(observations, participant)` | calculation | Whether heart rate *and* activity both fell towards the end of the session. |
| `format_report(result)` | presentation | Renders the result dictionary as plain text. Returns a string; `main.py` prints it. |

`require_number()`, `describe_value()`, `rejected()` and `split_into_thirds()`
are small internal helpers and are not counted above.

---

## Validation rules

Two different questions are asked of every record: **could this have happened?**
and **do we trust the sensor that reported it?**

### Rejected — discarded, not counted as usable

A value that cannot occur carries no information. Averaging it in would corrupt
every figure downstream, and no warning label makes that safe.

| Problem | Rule |
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

### Flagged — kept and counted, with a warning

| Problem | Rule |
| --- | --- |
| Weak signal | Signal quality 0.50 – 0.69 |

A reading the sensor half-trusts is still evidence. Discarding it can push a
session below the five-observation minimum and report "insufficient data" for a
session that genuinely happened — a worse outcome than including a slightly
noisy reading and saying so in the report.

Booleans are rejected explicitly wherever a number is expected. In Python `bool`
subclasses `int`, so `True` would otherwise be accepted as the number 1, and a
heart rate of `True` should be an error rather than 1 bpm.

---

## Classification rules

### Heart rate bands — heart rate reserve

Effort is measured against the span between a person's resting and maximum heart
rate, not as a ratio to their resting rate:

```
reserve  = max_heart_rate - resting_heart_rate
elevated = resting_heart_rate + 0.20 * reserve
high     = resting_heart_rate + 0.50 * reserve
```

`max_heart_rate` defaults to 190 and can be set per participant.

| Participant | Resting | Reserve | Elevated band | High band |
| --- | --- | --- | --- | --- |
| Jonathan | 70 bpm | 120 bpm | 94.0 bpm | 130.0 bpm |
| Mara (athlete) | 45 bpm | 145 bpm | 74.0 bpm | 117.5 bpm |

### Activity thresholds

`activity_level` is already a 0–1 scale that means the same for everyone, so
unlike heart rate it needs no per-person reference.

| Threshold | Value |
| --- | --- |
| Moderate | 0.20 |
| High | 0.60 |

### Order of checks — first match wins

| # | Label | Condition |
| --- | --- | --- |
| 1 | insufficient data | Fewer than **5** usable observations |
| 2 | recovering | Recovery detected (below) |
| 3 | high activity | Mean heart rate reaches the **high** band **or** mean activity ≥ 0.60 |
| 4 | moderate activity | Mean heart rate reaches the **elevated** band **or** mean activity ≥ 0.20 |
| 5 | resting | Everything else |

### Recovery rule

The session is split into three consecutive parts by time. The **final third**
is compared against the **peak third** — whichever third has the highest average
heart rate. All three conditions must hold:

1. Mean heart rate has fallen by at least the participant's required drop
   (10% for `Participant`, 15% for `Athlete`)
2. Mean activity has fallen by at least 30%
3. The peak third's mean heart rate reached the **elevated** band — that is,
   there was something to recover from

Uneven counts put the remainder in the later thirds, so with 5 readings the
split is 1 / 2 / 2. The final third is what the verdict rests on, and a
one-reading final third would make the classification depend on a single number.

---

## Assumptions and design decisions

**Heart rate reserve replaced an earlier ratio model.** The first design measured
effort as `mean heart rate ÷ resting heart rate`. That is not a measure of
effort: it assumes everyone has the same ceiling, and it lets a low resting heart
rate — a sign of fitness — inflate the effort score. Heart rate reserve uses the
span a person actually has available, which is why no special case is needed for
a trained participant.

**Recovery is checked before high activity.** A hard session ending in a cooldown
satisfies both tests. The order decides which label it gets, and this program
reports **recovering**, because that is the more specific statement: "high
activity" is true of any demanding session, while "recovering" additionally says
the participant has come back down from it. The explanation names the peak
intensity as well, so the demanding stretch is reported inside the recovery
verdict rather than instead of it. The trade-off is that a session labelled
"recovering" cannot be found by searching for "high activity" — acceptable here,
because each session is reported individually rather than aggregated.

**The athlete overrides recovery, not the bands.** The reserve formula already
accounts for a low resting heart rate, so overriding `heart_rate_bands()` would
be redundant — and a redundant override is worse than none, because it hides
that the base formula is doing the work. What genuinely differs is how a trained
person's heart rate behaves *after* effort: it falls faster and more steeply. A
10% dip that signals a real cooldown in an untrained person is ordinary
fluctuation in an athlete, so the requirement is raised to 15%. The parent's
30% activity requirement is inherited unchanged, because how quickly someone
stops moving is not a function of fitness.

**Recovery is measured from the peak third, not the first third.** A session
that starts calm, works hard, then eases off has its peak in the middle.
Comparing the end against the beginning would compare a warm-up against a
cooldown, report a modest rise, and miss the recovery entirely.

**No threshold is hard-coded outside `heart_rate_bands()` and
`recovery_thresholds()`.** `classify_session()` and `detect_recovery()` ask the
participant for its numbers rather than holding copies. This is what makes the
subclass work: if `detect_recovery()` held its own copy of 0.10, an `Athlete`
would silently be judged by the untrained numbers.

**Rounding happens only at display time.** Stored values keep full precision, so
no calculation inherits a rounding error. Each measurement has its own precision
in the report: one decimal for heart rate, skin response and temperature, two for
`activity_level`, because a 0–1 scale at one decimal has only ten possible values
and anything under 0.05 collapses to zero.

**Rejected records never become `Observation` objects.** `from_dict()` raises
before the object exists, so a bad reading cannot reach the summary statistics
even if a function is called carelessly.

---

## Example output

Both reports below are copied from a real run of `python main.py`.

### Cycle commute — a faulty sensor, still classified

Ten readings: three rejected, two kept with a warning, five clean. Enough
survives for a real verdict.

```
================================================================
  Session:     Cycle commute, sensor slipping
  Participant: Jonathan (resting HR 70 bpm, max 190 bpm)
================================================================

OBSERVATIONS
  Total received        10
  Usable                 7
    of which flagged     2  (kept)
  Rejected               3

SUMMARY  (usable observations only)
  Measurement        Average   Minimum   Maximum   Unit
  Heart rate           109.9     102.0     116.0   bpm
  Skin response          2.7       2.4       2.9   uS
  Temperature           33.2      33.0      33.4   C
  Activity level        0.38      0.32      0.44

COMPARISON WITH REFERENCE VALUES
  Heart rate    109.9 bpm  ->  elevated
                bands: elevated 94.0 bpm, high 130.0 bpm
                +39.9 bpm relative to resting
  Temperature   33.2 C  ->  normal
                reference 33.0 C, difference +0.2 C

RECOVERY
  Not detected.
    heart rate fell 0%, short of the 10% required

CLASSIFICATION:  MODERATE ACTIVITY
  Moderate activity: average heart rate 109.9 bpm reached the
  elevated band (94.0 bpm) and average activity 0.38 reached
  0.20.

FLAGGED READINGS  (2 kept)
  - record 2: weak signal (0.58)
  - record 6: weak signal (0.64)

REJECTED READINGS  (3 discarded)
  - record 3: missing field 'temperature'
  - record 5: 'heart_rate' is 320 bpm, outside the valid range 20 to 250 bpm
  - record 7: signal quality 0.35 is below the 0.50 usable cutoff
```

### Interval session — recovery detected, judged as an athlete

This scenario uses the `Athlete` subclass, so the overridden threshold is visible
in ordinary output: the report requires a **15%** fall, not 10%, and the bands
are 74.0 / 117.5 rather than Jonathan's 94.0 / 130.0.

```
================================================================
  Session:     Interval session with cooldown
  Participant: Mara (trained, resting HR 45 bpm, max 190 bpm)
================================================================

OBSERVATIONS
  Total received         9
  Usable                 9
    of which flagged     0  (kept)
  Rejected               0

SUMMARY  (usable observations only)
  Measurement        Average   Minimum   Maximum   Unit
  Heart rate           126.4      90.0     170.0   bpm
  Skin response          3.7       2.0       5.6   uS
  Temperature           33.4      32.9      34.0   C
  Activity level        0.52      0.12      0.92

COMPARISON WITH REFERENCE VALUES
  Heart rate    126.4 bpm  ->  high
                bands: elevated 74.0 bpm, high 117.5 bpm
                +81.4 bpm relative to resting
  Temperature   33.4 C  ->  normal
                reference 33.0 C, difference +0.4 C

RECOVERY
  Detected.
    Heart rate  167.7 -> 106.7 bpm  (36% fall, 15% required)
    Activity    0.90 -> 0.21       (77% fall, 30% required)

CLASSIFICATION:  RECOVERING
  Recovering: between the session's peak third and its final
  third, heart rate fell 36% (167.7 to 106.7 bpm) and activity
  fell 77% (0.90 to 0.21), meeting the 15% and 30% required. The
  peak third averaged 167.7 bpm, at or above the elevated band
  (74.0 bpm), so there was real effort to recover from. The
  session also met the high-activity test; 'recovering' is
  reported because it is the more specific finding.

FLAGGED READINGS  (0 kept)
  None.

REJECTED READINGS  (0 discarded)
  None.
```

`main.py` runs six scenarios in total: resting, moderate activity, high activity,
activity followed by recovery, poor-quality sensor data, and insufficient data.

---

## Tests

```bash
python3 -m unittest tests.py      # macOS / Linux
python -m unittest tests.py       # Windows
```

28 tests in six `TestCase` classes, covering validation and its boundary values,
the `Participant` property checks, the calculations, each of the five
classifications, recovery detection, and the report.

The suite was itself checked by mutation: four rules in `analyzer.py` were broken
one at a time — the signal-quality cutoff, the athlete's recovery threshold, the
"something to recover from" condition, and the five-observation minimum — and all
four were caught by the tests.

---

## Known limitations

- **The sample sessions are short.** Six to ten readings each, which keeps the
  data readable but means a "third" of a session is two or three readings. Real
  sensor data would arrive at a much higher rate, and the thirds would be more
  meaningful.
- **The thresholds are judgement calls.** The signal-quality cutoffs (0.50 and
  0.70), the 20% and 50% reserve fractions, the 0.20 and 0.60 activity levels,
  the 10% and 15% recovery drops and the five-observation minimum are all
  defensible but not derived from data. They are named constants with the
  reasoning recorded, rather than numbers buried in conditionals, so they can be
  changed in one place.
- **Maximum heart rate defaults to 190.** It is settable per participant, but the
  default is a rough population figure rather than a measured value. A
  participant whose real maximum differs will have bands shifted accordingly.
- **No real sensor input.** Observations come from `sample_data.py` as literal
  dictionaries. There is no file reading, no device interface and no live input.
- **Timestamps are only used for ordering.** The program assumes readings are
  evenly spaced and does not check the interval between them, so a session with
  a long gap in the middle is treated the same as a continuous one.
- **One weak-signal tier.** A reading at 0.51 and one at 0.69 are flagged
  identically, though the second is considerably more trustworthy.
