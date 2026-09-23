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


def validate_observation(raw):
    """Check one raw sensor record.

    Returns (True, None) when the record is acceptable, otherwise
    (False, reason) where reason is readable plain English.

    This function is the single place the validation rules live. Nothing
    else in the program re-implements them. Section 3 extends it with the
    impossible-value ranges and the signal-quality tiers; for now it
    covers the structural checks only.
    """
    if not isinstance(raw, dict):
        return False, f"record is a {type(raw).__name__}, not a dictionary"

    for field in MEASUREMENT_FIELDS:
        if field not in raw:
            return False, f"missing field '{field}'"

        value = raw[field]
        # bool is a subclass of int in Python, so True would otherwise be
        # accepted as the number 1.
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False, f"'{field}' is not a number (got {value!r})"

    return True, None


class Participant:
    """A person and the reference measurements taken when they are at rest.

    The resting heart rate is the denominator of every comparison the
    program makes, so it is kept private and reached through a property
    that refuses impossible values.
    """

    def __init__(self, name, resting_heart_rate, normal_temperature=33.0):
        self.name = name
        self.normal_temperature = normal_temperature
        # Assigning here runs the property setter below, so the check
        # applies to construction as well as to later changes.
        self.resting_heart_rate = resting_heart_rate

    @property
    def resting_heart_rate(self):
        return self._resting_heart_rate

    @resting_heart_rate.setter
    def resting_heart_rate(self, value):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            given_type = type(value).__name__
            raise ValueError(f"resting heart rate must be a number, got {given_type}")
        if not 20 <= value <= 120:
            raise ValueError(f"resting heart rate {value} is outside 20-120 bpm")
        self._resting_heart_rate = value

    def heart_rate_bands(self):
        """Heart rates at which *this* person counts as elevated or high.

        Expressed as multiples of their own resting rate, so the same
        thresholds mean the same effort for different people.
        """
        return {
            "elevated": self.resting_heart_rate * 1.15,
            "high": self.resting_heart_rate * 1.50,
        }

    def describe(self):
        return f"{self.name} (resting HR {self.resting_heart_rate} bpm)"


class Athlete(Participant):
    """A trained participant, whose bands sit higher than the default.

    HR ratio divides by the resting heart rate, and a trained person's
    resting rate is lower - a smaller denominator. The same absolute
    working heart rate therefore produces a larger ratio for them. At
    140 bpm an untrained person resting at 70 sits at ratio 2.00, while
    an athlete resting at 45 sits at 3.11 for identical effort. Using the
    default bands would label an athlete's easy work as high activity,
    so the bands are raised to absorb the smaller denominator.
    """

    def heart_rate_bands(self):
        return {
            "elevated": self.resting_heart_rate * 1.25,
            "high": self.resting_heart_rate * 1.70,
        }

    def describe(self):
        return f"{self.name} (trained, resting HR {self.resting_heart_rate} bpm)"


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
