# Project notes

Decision log kept while building the project. The README is written from this.

Project: Smart Fitness Session Analyzer (Option A)
Author: Jonathan Christensen
Student number: jonathan4495
GitHub account: Jonnyyyc
Repository: https://github.com/Jonnyyyc/fitness-session-analyzer

---

## Section 0: Setup

Created the repository with the five files the brief asks for, plus this file
and a `.gitignore`. The files got short placeholder docstrings rather than being
empty, so `python main.py` and `python -m unittest tests.py` both worked from
the start. Git was not installed on this machine, so I installed it. Python here
is 3.14.3 and the command is `python` rather than `python3`.

## Section 1: Design plan

Planned four classes: `Participant`, `Athlete`, `Observation` and `Session`.
Composition sits in `Session`, which holds a participant and a list of
observations. Encapsulation is the private resting heart rate behind a property.
Inheritance is `Athlete` overriding a method on `Participant`. The classmethod is
`Observation.from_dict`. I decided against a separate `Validator` or `Report`
class, since each would hold no data and expose a single method.

## Section 2: Core classes

Built `analyzer.py` with the four classes. `__init__` assigns through the
property rather than to the underscore attribute, so the validity check also
runs at construction, which is the most likely place a bad value enters.
Booleans are rejected wherever a number is expected, because `bool` subclasses
`int` in Python and `True` would otherwise be read as 1 bpm.

## Section 2 revision: heart rate reserve

The first design measured effort as mean heart rate divided by resting heart
rate. That assumes everyone has the same ceiling, and it let a low resting rate
inflate the effort score, which is what made the `Athlete` subclass necessary in
the first place. Replaced with heart rate reserve, where `reserve = max -
resting`, `elevated = resting + 0.20 * reserve` and `high = resting + 0.50 *
reserve`. `Athlete` no longer overrides the bands. It overrides
`recovery_thresholds()` instead, raising the required heart rate drop from 10%
to 15%, because a trained person's heart rate falls faster once effort stops.

## Section 3: Validation

Two questions decide what happens to a record: could this have happened, and do
we trust the sensor. Impossible values are rejected, since averaging them in
would corrupt every figure downstream. Readings with a signal quality between
0.50 and 0.69 are kept but flagged, because a doubtful reading is still evidence
and discarding it can push a session below the five-observation minimum. Below
0.50 the reading is rejected. `validate_observation()` is the only place these
rules live.

## Section 4: Calculations

`summarise()` covers heart rate, skin response, temperature and activity level.
Timestamp orders the session and signal quality describes the sensor, so
averaging either would mean nothing. Empty input returns `{}` rather than
raising, so the empty case travels the normal path and gets labelled as
insufficient data. `compare_to_reference()` reads its thresholds from the
participant, which is what lets two people with identical readings be described
differently.

## Section 5: Classification and recovery

Recovery compares the final third of a session against its peak third rather
than its first third, because a session that starts calm, works hard and then
eases off has its peak in the middle. Uneven counts put the remainder in the
later thirds so the final third is never the smallest. Checks run in order:
insufficient data, recovering, high, moderate, resting. Recovery is checked
before high activity because a hard session ending in a cooldown satisfies both,
and recovering is the more specific statement.

## Section 6: Console report

`format_report()` returns a string rather than printing, so tests can assert on
the output directly and `main.py` decides where it goes. Rounding happens only
here, so no calculation inherits a rounding error. Each measurement has its own
precision: one decimal for the sensor readings and two for activity level, since
a 0 to 1 scale at one decimal has only ten possible values.

## Section 7: Sample data

Scenarios live in `sample_data.py` as dictionaries of label, participant and
records. `main.py` holds the loop that builds a session from each and prints the
report, and nothing else, since any logic there would be logic `tests.py` cannot
reach.

## Section 8: Tests

`tests.py` uses `unittest`, with one `TestCase` class per area. One `record()`
helper with keyword overrides and one `analyse()` shortcut keep each test to the
one field it is actually about. Classification tests use flat heart rates so a
test cannot accidentally satisfy the recovery rule as well.

## Section 9: README

Written from this file. The example output blocks were copied from a real run
and then checked against `main.py` output, since pasted output goes stale as
soon as a format string changes.

## Section 10: Final check and submission

Checked the requirement list against the code rather than against these notes,
then cloned the repository into a temporary folder and ran both commands there
to confirm nothing depends on a file that only exists on this machine.

## Section 11: Removing redundancy

`Session` had kept a combined `issues` list as well as `flag_notes` and
`rejection_notes`. Every note already names its record number, so the combined
list held nothing the other two did not, and the report never read it. Removed.
`FIELD_LABELS` also lost its `timestamp` and `signal_quality` entries, which are
never labelled. `FIELD_UNITS` keeps all six, because rejection messages use it
for every field.

## Section 12: Generator integration

Copied the instructor's `data_generator.py` in unchanged and rebuilt
`sample_data.py` around it, with a fixed seed so the README output stays valid.
`Participant.from_profile()` translates the generator's field names, and builds
with `cls()` so `Athlete.from_profile()` returns an athlete. The profile carries
a baseline skin response, so `compare_to_reference()` now reports skin response
against it when one is set.

Three scenarios are still hand-written. The generator cannot produce a session
under six windows, so the three-reading case has to be written by hand. Its
`poor_quality` scenario breaks every record, so it classifies as insufficient
data and never exercises the flagged tier. The degraded-sensor scenario is the
only place in ordinary output where a reading is kept despite being doubtful.
The athlete recovery scenario reuses generated data so the override is visible
outside the tests.
