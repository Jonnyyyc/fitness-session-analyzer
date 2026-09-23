"""Smart Fitness Session Analyzer — core classes.

Standard library only.

Author: Jonathan Christensen
"""

# Every sensor record must carry these six fields, in this spelling.
MEASUREMENT_FIELDS = (
    "timestamp",
    "heart_rate",
    "skin_response",
    "temperature",
    "activity_level",
    "signal_quality",
)


def require_number(label, value):
    """Raise ValueError unless value is a real number.

    Booleans are refused: in Python bool subclasses int, so True would
    otherwise be accepted as the number 1, and a heart rate of True
    should be an error rather than 1 bpm.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a number, got {type(value).__name__}")
    return value


def validate_observation(raw):
    """Check one raw sensor record.

    Returns (True, None) when the record is acceptable, otherwise
    (False, reason) where reason is readable plain English.

    This function is the single place the observation rules live. Nothing
    else in the program re-implements them. Section 3 extends it with the
    impossible-value ranges and the signal-quality tiers; for now it
    covers the structural checks only.
    """
    if not isinstance(raw, dict):
        return False, f"record is a {type(raw).__name__}, not a dictionary"

    for field in MEASUREMENT_FIELDS:
        if field not in raw:
            return False, f"missing field '{field}'"

        try:
            require_number(f"'{field}'", raw[field])
        except ValueError as error:
            return False, str(error)

    return True, None


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
        acceptable, reason = validate_observation(raw)
        if not acceptable:
            raise ValueError(reason)
        return cls(**{field: raw[field] for field in MEASUREMENT_FIELDS})

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
            self.issues.append(f"record {self._received}: {error}")
            return False

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
    def total_count(self):
        return self._received

    def __repr__(self):
        return (f"Session({self.label!r}, {self.usable_count} usable "
                f"of {self.total_count})")
