"""Smart Fitness Session Analyzer — core classes.

Standard library only.

Author: Jonathan Christensen
"""

import statistics

# Every sensor record must carry these six fields, in this spelling.
MEASUREMENT_FIELDS = (
    "timestamp",
    "heart_rate",
    "skin_response",
    "temperature",
    "activity_level",
    "signal_quality",
)

# Ranges a reading must fall inside to be believable at all. A value
# outside these is not a poor reading, it is an impossible one - so the
# record is rejected rather than flagged. None means "no upper bound":
# a session can run for any length of time.
VALUE_RANGES = {
    "timestamp": (0, None),
    "heart_rate": (20, 250),
    "skin_response": (0, 30),
    "temperature": (20, 45),
    "activity_level": (0.0, 1.0),
    "signal_quality": (0.0, 1.0),
}

# Units used only to make rejection messages readable.
FIELD_UNITS = {
    "timestamp": "s",
    "heart_rate": "bpm",
    "skin_response": "uS",
    "temperature": "C",
    "activity_level": "",
    "signal_quality": "",
}

# Below this, a reading is closer to noise than signal - rejected.
SIGNAL_QUALITY_REJECT = 0.50
# Between the two, the reading is kept but carries a warning.
SIGNAL_QUALITY_FLAG = 0.70

# The measurements worth summarising. 'timestamp' orders the session
# rather than measuring the person, and 'signal_quality' describes the
# sensor rather than the body - an average of either would mean nothing.
SUMMARY_FIELDS = (
    "heart_rate",
    "skin_response",
    "temperature",
    "activity_level",
)

# How far skin temperature must differ from the participant's own normal
# before the report calls it a difference rather than ordinary drift.
# A presentation tolerance, not a classification threshold: no
# classification decision reads this value.
TEMPERATURE_TOLERANCE = 0.5


def require_number(label, value):
    """Raise ValueError unless value is a real number.

    Booleans are refused: in Python bool subclasses int, so True would
    otherwise be accepted as the number 1, and a heart rate of True
    should be an error rather than 1 bpm.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a number, got {type(value).__name__}")
    return value


def describe_value(field, value):
    """Render a value with its unit, for use in a rejection message."""
    unit = FIELD_UNITS[field]
    return f"{value} {unit}".strip()


def rejected(reason):
    """Build the 'this record cannot be used' result."""
    return {"ok": False, "reason": reason, "flags": []}


def validate_observation(raw):
    """Check one raw sensor record against every rule.

    Returns a dictionary:
        ok     - True if the record can be used at all
        reason - why it was rejected, in plain English, or None
        flags  - warnings about a record that is kept anyway

    This function is the single place the observation rules live.
    Nothing else in the program re-implements them.

    The checks run cheapest-first and stop at the first failure, so a
    record missing 'heart_rate' reports that rather than complaining
    about a field it does have.
    """
    if not isinstance(raw, dict):
        return rejected(f"record is a {type(raw).__name__}, not a dictionary")

    # 1. Structure: the six fields exist and are real numbers.
    for field in MEASUREMENT_FIELDS:
        if field not in raw:
            return rejected(f"missing field '{field}'")

        try:
            require_number(f"'{field}'", raw[field])
        except ValueError as error:
            return rejected(str(error))

    # 2. Plausibility: the numbers describe something that could happen.
    for field, (low, high) in VALUE_RANGES.items():
        value = raw[field]
        if value < low or (high is not None and value > high):
            shown = describe_value(field, value)
            if high is None:
                return rejected(f"'{field}' is {shown}, below the minimum "
                                f"{describe_value(field, low)}")
            return rejected(f"'{field}' is {shown}, outside the valid range "
                            f"{low} to {describe_value(field, high)}")

    # 3. Trust: a believable reading may still be too noisy to rely on.
    quality = raw["signal_quality"]
    if quality < SIGNAL_QUALITY_REJECT:
        return rejected(f"signal quality {quality:.2f} is below the "
                        f"{SIGNAL_QUALITY_REJECT:.2f} usable cutoff")

    flags = []
    if quality < SIGNAL_QUALITY_FLAG:
        flags.append(f"weak signal ({quality:.2f})")

    return {"ok": True, "reason": None, "flags": flags}


class Participant:
    """A person and the reference measurements taken when they are at rest.

    The resting heart rate anchors every comparison the program makes,
    so it is kept private and reached through a property that refuses
    impossible values.
    """

    def __init__(self, name, resting_heart_rate, max_heart_rate=190,
                 normal_temperature=33.0):
        self.name = name
        self.normal_temperature = normal_temperature
        # Set before the resting rate so its setter can tell that there is
        # no maximum to cross-check against yet.
        self._max_heart_rate = None
        # Assigning to the property names (no underscore) runs the setters
        # below, so the checks apply to construction as well as to later
        # changes.
        self.resting_heart_rate = resting_heart_rate
        self.max_heart_rate = max_heart_rate

    @property
    def resting_heart_rate(self):
        return self._resting_heart_rate

    @resting_heart_rate.setter
    def resting_heart_rate(self, value):
        require_number("resting heart rate", value)
        if not 20 <= value <= 120:
            raise ValueError(f"resting heart rate {value} is outside 20-120 bpm")
        if self._max_heart_rate is not None and value >= self._max_heart_rate:
            raise ValueError(
                f"resting heart rate {value} is not below the maximum "
                f"{self._max_heart_rate}"
            )
        self._resting_heart_rate = value

    @property
    def max_heart_rate(self):
        return self._max_heart_rate

    @max_heart_rate.setter
    def max_heart_rate(self, value):
        require_number("maximum heart rate", value)
        if not 100 <= value <= 230:
            raise ValueError(f"maximum heart rate {value} is outside 100-230 bpm")
        if value <= self._resting_heart_rate:
            raise ValueError(
                f"maximum heart rate {value} is not above the resting rate "
                f"{self._resting_heart_rate}"
            )
        self._max_heart_rate = value

    def heart_rate_bands(self):
        """Absolute bpm at which this person counts as elevated or high.

        Based on heart rate reserve: the span between resting and maximum
        is what the person actually has available to use, so a percentage
        of that span means the same amount of effort for everyone. This
        is why a trained person needs no special case - their lower
        resting rate widens their reserve, and the formula uses it.
        """
        reserve = self.max_heart_rate - self.resting_heart_rate
        return {
            "elevated": self.resting_heart_rate + 0.20 * reserve,
            "high": self.resting_heart_rate + 0.50 * reserve,
        }

    def recovery_thresholds(self):
        """How far heart rate and activity must fall to count as recovery.

        Fractions of the session's peak third, not absolute values.
        """
        return {"heart_rate_drop": 0.10, "activity_drop": 0.30}

    def describe(self):
        return (f"{self.name} (resting HR {self.resting_heart_rate} bpm, "
                f"max {self.max_heart_rate} bpm)")


class Athlete(Participant):
    """A trained participant. Recovers faster, so recovery is judged harder.

    The heart rate bands need no override - heart rate reserve already
    accounts for a low resting rate. What does differ is the way a
    trained person's heart rate behaves *after* effort: it falls quickly
    and steeply. A 10% dip that would signal a genuine cooldown in an
    untrained person is unremarkable in an athlete, so the bar is raised
    to 15% to avoid reading ordinary fluctuation as a recovery phase.
    """

    def recovery_thresholds(self):
        thresholds = super().recovery_thresholds()
        thresholds["heart_rate_drop"] = 0.15
        return thresholds

    def describe(self):
        return (f"{self.name} (trained, resting HR {self.resting_heart_rate} bpm, "
                f"max {self.max_heart_rate} bpm)")


class Observation:
    """A single sensor reading taken at one moment in a session."""

    def __init__(self, timestamp, heart_rate, skin_response,
                 temperature, activity_level, signal_quality):
        self.timestamp = timestamp
        self.heart_rate = heart_rate
        self.skin_response = skin_response
        self.temperature = temperature
        self.activity_level = activity_level
        self.signal_quality = signal_quality
        self.flags = []  # readable warnings; filled in from Section 3

    @classmethod
    def from_dict(cls, raw):
        """Build an Observation from a raw record dictionary.

        An alternative constructor. The program's real input format is
        the dict shown in the brief, so this is the natural way in.

        Raises ValueError(reason) when the record fails validation.
        Session catches that and records the reason, which keeps the
        rules in validate_observation() and the bookkeeping here.
        """
        result = validate_observation(raw)
        if not result["ok"]:
            raise ValueError(result["reason"])

        observation = cls(**{field: raw[field] for field in MEASUREMENT_FIELDS})
        observation.flags = result["flags"]
        return observation

    def __repr__(self):
        return (f"Observation(t={self.timestamp}, hr={self.heart_rate}, "
                f"activity={self.activity_level})")


class Session:
    """One recording: a participant, plus the observations taken from them.

    Composition. A Session *has a* Participant and *has a list of*
    Observations; it is not a kind of either. The participant outlives
    any single session, and the observations mean nothing without the
    participant's reference values to compare them against.
    """

    def __init__(self, participant, label="session"):
        self.participant = participant
        self.label = label
        self.observations = []   # accepted Observation objects
        self.issues = []         # why records were turned away
        self.rejected_count = 0
        self._received = 0       # how many raw records were offered

    def add_observation(self, raw):
        """Offer one raw record to the session. True if it was accepted."""
        self._received += 1
        try:
            observation = Observation.from_dict(raw)
        except ValueError as error:
            self.rejected_count += 1
            self.issues.append(f"record {self._received} rejected: {error}")
            return False

        # A flagged record still counts. The warning is recorded so the
        # report can say the reading was used despite being imperfect.
        for flag in observation.flags:
            self.issues.append(f"record {self._received} flagged: {flag}, kept")

        self.observations.append(observation)
        return True

    def add_many(self, raw_records):
        """Offer a list of raw records. Returns self so calls can chain."""
        for raw in raw_records:
            self.add_observation(raw)
        return self

    def ordered_observations(self):
        """Accepted observations in time order.

        Recovery detection compares the end of a session against its
        middle, so the readings have to be in order regardless of the
        order they arrived in.
        """
        return sorted(self.observations, key=lambda obs: obs.timestamp)

    @property
    def usable_count(self):
        return len(self.observations)

    @property
    def flagged_count(self):
        """Usable observations that carry a warning. A subset of usable."""
        return sum(1 for obs in self.observations if obs.flags)

    @property
    def total_count(self):
        return self._received

    def __repr__(self):
        return (f"Session({self.label!r}, {self.usable_count} usable "
                f"of {self.total_count})")


def summarise(observations):
    """Average, minimum and maximum for each measured field.

    Pass the session's usable observations. Rejected records never
    become Observation objects, so they cannot reach this function -
    the averages are of trustworthy readings by construction.

    Returns a dictionary keyed by field name:

        {"heart_rate": {"avg": 118.0, "min": 110, "max": 126}, ...}

    Returns an empty dictionary for an empty list. There is no sensible
    average of nothing, and raising here would force every caller to
    guard a case the classifier already handles as "insufficient data".
    """
    if not observations:
        return {}

    summary = {}
    for field in SUMMARY_FIELDS:
        values = [getattr(observation, field) for observation in observations]
        summary[field] = {
            "avg": statistics.mean(values),
            "min": min(values),
            "max": max(values),
        }
    return summary


def heart_rate_zone(average_heart_rate, bands):
    """Which of the participant's bands an average heart rate falls into.

    The bands are passed in rather than recalculated, so this function
    holds no thresholds of its own. Both the comparison and the
    classification call it, which is what keeps the two consistent.
    """
    if average_heart_rate >= bands["high"]:
        return "high"
    if average_heart_rate >= bands["elevated"]:
        return "elevated"
    return "below elevated"


def compare_to_reference(summary, participant):
    """Measure the session against the participant's own reference values.

    Every threshold comes from the participant - heart rate from
    heart_rate_bands(), temperature from normal_temperature - so two
    people with identical readings can be described differently, which
    is the point of holding reference values per person.

    Returns an empty dictionary when there is nothing to compare.
    """
    if not summary:
        return {}

    bands = participant.heart_rate_bands()
    average_heart_rate = summary["heart_rate"]["avg"]

    average_temperature = summary["temperature"]["avg"]
    temperature_difference = average_temperature - participant.normal_temperature
    if abs(temperature_difference) < TEMPERATURE_TOLERANCE:
        direction = "normal"
    elif temperature_difference > 0:
        direction = "above normal"
    else:
        direction = "below normal"

    return {
        "heart_rate": {
            "average": average_heart_rate,
            "zone": heart_rate_zone(average_heart_rate, bands),
            "elevated_band": bands["elevated"],
            "high_band": bands["high"],
            "above_resting": average_heart_rate - participant.resting_heart_rate,
        },
        "temperature": {
            "average": average_temperature,
            "reference": participant.normal_temperature,
            "difference": temperature_difference,
            "direction": direction,
        },
    }
