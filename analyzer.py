"""Smart Fitness Session Analyzer: core classes.

Standard library only.

Author: Jonathan Christensen
"""

import statistics
import textwrap

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

# Column headings for the report's summary table. Only the fields in
# SUMMARY_FIELDS are ever labelled - timestamp orders the session and
# signal_quality describes the sensor, so neither is summarised.
FIELD_LABELS = {
    "heart_rate": "Heart rate",
    "skin_response": "Skin response",
    "temperature": "Temperature",
    "activity_level": "Activity level",
}

# Decimal places used when the report prints each measurement. One
# decimal suits the sensor readings, but activity_level is a 0-1 scale
# where one decimal leaves only ten possible values and anything under
# 0.05 collapses to zero - so it gets two, matching the precision the
# classification explanation quotes.
FIELD_DECIMALS = {
    "heart_rate": 1,
    "skin_response": 1,
    "temperature": 1,
    "activity_level": 2,
}

# Units used to make rejection messages and the report readable.
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

# Below this many usable observations, no verdict is given. Four readings
# can be four seconds or four minutes apart, and a third of that is one
# reading - too little to call a trend either way.
MINIMUM_USABLE_OBSERVATIONS = 5

# Activity level is already a 0-1 scale that means the same for everyone,
# so unlike heart rate it needs no per-person reference.
MODERATE_ACTIVITY_LEVEL = 0.20
HIGH_ACTIVITY_LEVEL = 0.60


def require_number(label, value):
    """Raise ValueError unless value is a real number."""
    # bool subclasses int in Python, so True would otherwise be accepted
    # as the number 1.
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
    """Check one record. The only place the observation rules live.

    Returns {"ok": bool, "reason": str or None, "flags": list of str}.
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
    """A person and their reference measurements.

    The resting and maximum heart rates are private, behind properties.
    """

    def __init__(self, name, resting_heart_rate, max_heart_rate=190,
                 normal_temperature=33.0, normal_skin_response=None):
        self.name = name
        self.normal_temperature = normal_temperature
        # Optional. The generator supplies one, but a participant created
        # by hand need not, and the comparison is skipped when it is None.
        self.normal_skin_response = normal_skin_response
        # Set before the resting rate so its setter can tell that there is
        # no maximum to cross-check against yet.
        self._max_heart_rate = None
        # Assigning to the property names (no underscore) runs the setters
        # below, so the checks apply to construction as well as to later
        # changes.
        self.resting_heart_rate = resting_heart_rate
        self.max_heart_rate = max_heart_rate

    PROFILE_FIELDS = ("participant_id", "baseline_heart_rate",
                      "baseline_temperature", "baseline_skin_response")

    @classmethod
    def from_profile(cls, profile):
        """Build a participant from the data generator's profile dictionary.

        Builds with cls(), so Athlete.from_profile() returns an Athlete.
        """
        missing = [f for f in cls.PROFILE_FIELDS if f not in profile]
        if missing:
            raise ValueError("profile is missing " + ", ".join(missing))

        return cls(
            name=profile["participant_id"],
            resting_heart_rate=profile["baseline_heart_rate"],
            normal_temperature=profile["baseline_temperature"],
            normal_skin_response=profile["baseline_skin_response"],
        )

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

        Uses heart rate reserve: the span between resting and maximum.
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
        # Read by detect_recovery() rather than hard-coded there, so a
        # subclass can change the rule by overriding this method.
        return {"heart_rate_drop": 0.10, "activity_drop": 0.30}

    def describe(self):
        return (f"{self.name} (resting HR {self.resting_heart_rate} bpm, "
                f"max {self.max_heart_rate} bpm)")


class Athlete(Participant):
    """A trained participant, whose heart rate falls faster after effort.

    Only recovery differs. The reserve formula handles the bands.
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
        self.flags = []  # readable warnings about a reading that was kept anyway

    @classmethod
    def from_dict(cls, raw):
        """Build an Observation from a raw record dictionary.

        Raises ValueError(reason) when the record fails validation.
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

    Composition: a Session has a Participant and a list of Observations.
    """

    def __init__(self, participant, label="session"):
        self.participant = participant
        self.label = label
        self.observations = []   # accepted Observation objects
        # Notes kept split by kind, so the report can group them without
        # parsing the text back apart. Each note names the record it came
        # from, so arrival order is still recoverable from either list.
        self.flag_notes = []
        self.rejection_notes = []
        self.rejected_count = 0
        self._received = 0       # how many raw records were offered

    def add_observation(self, raw):
        """Offer one raw record to the session. True if it was accepted."""
        self._received += 1
        try:
            observation = Observation.from_dict(raw)
        except ValueError as error:
            self.rejected_count += 1
            self.rejection_notes.append(f"record {self._received}: {error}")
            return False

        # A flagged record still counts. The warning is recorded so the
        # report can say the reading was used despite being imperfect.
        for flag in observation.flags:
            self.flag_notes.append(f"record {self._received}: {flag}")

        self.observations.append(observation)
        return True

    def add_many(self, raw_records):
        """Offer a list of raw records. Returns self so calls can chain."""
        for raw in raw_records:
            self.add_observation(raw)
        return self

    def ordered_observations(self):
        """Accepted observations in time order."""
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

    def analyse(self):
        """Run the whole analysis and return the structured result.

        format_report() does no calculation of its own on top of this.
        """
        observations = self.ordered_observations()
        summary = summarise(observations)
        comparison = compare_to_reference(summary, self.participant)
        recovery = detect_recovery(observations, self.participant)
        classification, explanation = classify_session(
            summary, self.participant, self.usable_count, recovery
        )

        return {
            "session": self.label,
            "participant": self.participant.describe(),
            "classification": classification,
            "explanation": explanation,
            "observations": {
                "total": self.total_count,
                "usable": self.usable_count,
                "flagged": self.flagged_count,
                "rejected": self.rejected_count,
            },
            "summary": summary,
            "comparison": comparison,
            "recovery": recovery,
            # Copies, so a caller holding the result cannot alter the
            # session's own record of what happened.
            "flag_notes": list(self.flag_notes),
            "rejection_notes": list(self.rejection_notes),
        }

    def __repr__(self):
        return (f"Session({self.label!r}, {self.usable_count} usable "
                f"of {self.total_count})")


def summarise(observations):
    """Average, minimum and maximum for each measured field.

    Returns {field: {"avg", "min", "max"}}, or {} for an empty list.
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

    The bands are passed in, so this function holds no thresholds.
    """
    if average_heart_rate >= bands["high"]:
        return "high"
    if average_heart_rate >= bands["elevated"]:
        return "elevated"
    return "below elevated"


def compare_to_reference(summary, participant):
    """Measure the session against the participant's own reference values.

    Every threshold is read from the participant. Returns {} if empty.
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

    comparison = {
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

    # Only when the participant carries a skin-response reference. A
    # participant built by hand may not, and inventing one would compare
    # the session against a number nobody measured.
    if participant.normal_skin_response is not None:
        average_skin_response = summary["skin_response"]["avg"]
        comparison["skin_response"] = {
            "average": average_skin_response,
            "reference": participant.normal_skin_response,
            "difference": average_skin_response - participant.normal_skin_response,
        }

    return comparison


def split_into_thirds(observations):
    """Split time-ordered observations into three consecutive parts."""
    # Uneven counts put the remainder in the later parts, so the final
    # third is never the smallest. Recovery is judged on it.
    count = len(observations)
    first_boundary = count // 3
    second_boundary = 2 * count // 3
    return (
        observations[:first_boundary],
        observations[first_boundary:second_boundary],
        observations[second_boundary:],
    )


def detect_recovery(observations, participant):
    """Did heart rate AND activity both fall towards the end of the session?

    Returns a dict; 'detected' is the verdict, the rest is the evidence.
    """
    # Thresholds are read from the participant, not hard-coded here, so
    # an Athlete is judged by its own numbers.
    thresholds = participant.recovery_thresholds()
    bands = participant.heart_rate_bands()

    not_detected = {
        "detected": False,
        "heart_rate_drop": 0.0,
        "activity_drop": 0.0,
        "required": thresholds,
    }

    # Three non-empty parts need at least three readings.
    if len(observations) < 3:
        return {**not_detected,
                "reason": "too few observations to compare start and end"}

    # Measured against the peak third rather than the first, because a
    # session that works hard then eases off has its peak in the middle.
    thirds = split_into_thirds(observations)
    heart_rates = [statistics.mean([obs.heart_rate for obs in part])
                   for part in thirds]
    activities = [statistics.mean([obs.activity_level for obs in part])
                  for part in thirds]

    peak_index = heart_rates.index(max(heart_rates))
    peak_heart_rate = heart_rates[peak_index]
    peak_activity = activities[peak_index]
    final_heart_rate = heart_rates[-1]
    final_activity = activities[-1]

    heart_rate_drop = (peak_heart_rate - final_heart_rate) / peak_heart_rate
    # Activity can legitimately be 0.0 at the peak - someone at rest
    # throughout. Nothing fell, so the drop is zero rather than undefined.
    if peak_activity > 0:
        activity_drop = (peak_activity - final_activity) / peak_activity
    else:
        activity_drop = 0.0

    peak_reached_elevated = peak_heart_rate >= bands["elevated"]

    evidence = {
        "heart_rate_drop": heart_rate_drop,
        "activity_drop": activity_drop,
        "peak_heart_rate": peak_heart_rate,
        "final_heart_rate": final_heart_rate,
        "peak_activity": peak_activity,
        "final_activity": final_activity,
        "peak_reached_elevated": peak_reached_elevated,
        "elevated_band": bands["elevated"],
        "required": thresholds,
    }

    # All three must hold. Without the third, someone sitting still whose
    # heart rate drifts down would be reported as recovering.
    detected = (
        heart_rate_drop >= thresholds["heart_rate_drop"]
        and activity_drop >= thresholds["activity_drop"]
        and peak_reached_elevated
    )

    if detected:
        return {**evidence, "detected": True, "reason": None}

    if not peak_reached_elevated:
        reason = (f"peak third averaged {peak_heart_rate:.1f} bpm, which never "
                  f"reached the elevated band ({bands['elevated']:.1f} bpm) - "
                  f"nothing to recover from")
    elif heart_rate_drop < thresholds["heart_rate_drop"]:
        reason = (f"heart rate fell {heart_rate_drop:.0%}, short of the "
                  f"{thresholds['heart_rate_drop']:.0%} required")
    else:
        reason = (f"activity fell {activity_drop:.0%}, short of the "
                  f"{thresholds['activity_drop']:.0%} required")

    return {**evidence, "detected": False, "reason": reason}


def classify_session(summary, participant, usable_count, recovery):
    """Label the session and explain the label.

    Order: insufficient data, recovering, high, moderate, resting.
    """
    # Recovery is checked before high activity because a hard session
    # ending in a cooldown satisfies both, and recovering says more.
    if usable_count < MINIMUM_USABLE_OBSERVATIONS:
        return ("insufficient data",
                f"Only {usable_count} usable observation"
                f"{'' if usable_count == 1 else 's'}; at least "
                f"{MINIMUM_USABLE_OBSERVATIONS} are needed before a session "
                f"can be classified.")

    bands = participant.heart_rate_bands()
    average_heart_rate = summary["heart_rate"]["avg"]
    average_activity = summary["activity_level"]["avg"]
    zone = heart_rate_zone(average_heart_rate, bands)

    if recovery["detected"]:
        explanation = (
            f"Recovering: between the session's peak third and its final "
            f"third, heart rate fell {recovery['heart_rate_drop']:.0%} "
            f"({recovery['peak_heart_rate']:.1f} to "
            f"{recovery['final_heart_rate']:.1f} bpm) and activity fell "
            f"{recovery['activity_drop']:.0%} "
            f"({recovery['peak_activity']:.2f} to "
            f"{recovery['final_activity']:.2f}), meeting the "
            f"{recovery['required']['heart_rate_drop']:.0%} and "
            f"{recovery['required']['activity_drop']:.0%} required. The peak "
            f"third averaged {recovery['peak_heart_rate']:.1f} bpm, at or "
            f"above the elevated band ({recovery['elevated_band']:.1f} bpm), "
            f"so there was real effort to recover from."
        )
        # A cooldown session also satisfies the intensity tests. Say so,
        # rather than letting the reader think the effort went unnoticed.
        if zone == "high" or average_activity >= HIGH_ACTIVITY_LEVEL:
            explanation += (" The session also met the high-activity test; "
                            "'recovering' is reported because it is the more "
                            "specific finding.")
        elif zone == "elevated" or average_activity >= MODERATE_ACTIVITY_LEVEL:
            explanation += (" The session also met the moderate-activity test; "
                            "'recovering' is reported because it is the more "
                            "specific finding.")
        return "recovering", explanation

    if zone == "high" or average_activity >= HIGH_ACTIVITY_LEVEL:
        reasons = []
        if zone == "high":
            reasons.append(f"average heart rate {average_heart_rate:.1f} bpm "
                           f"reached the high band ({bands['high']:.1f} bpm)")
        if average_activity >= HIGH_ACTIVITY_LEVEL:
            reasons.append(f"average activity {average_activity:.2f} reached "
                           f"{HIGH_ACTIVITY_LEVEL:.2f}")
        return "high activity", "High activity: " + " and ".join(reasons) + "."

    if zone == "elevated" or average_activity >= MODERATE_ACTIVITY_LEVEL:
        reasons = []
        if zone == "elevated":
            reasons.append(f"average heart rate {average_heart_rate:.1f} bpm "
                           f"reached the elevated band "
                           f"({bands['elevated']:.1f} bpm)")
        if average_activity >= MODERATE_ACTIVITY_LEVEL:
            reasons.append(f"average activity {average_activity:.2f} reached "
                           f"{MODERATE_ACTIVITY_LEVEL:.2f}")
        return ("moderate activity",
                "Moderate activity: " + " and ".join(reasons) + ".")

    return ("resting",
            f"Resting: average heart rate {average_heart_rate:.1f} bpm stayed "
            f"below the elevated band ({bands['elevated']:.1f} bpm) and "
            f"average activity {average_activity:.2f} stayed below "
            f"{MODERATE_ACTIVITY_LEVEL:.2f}.")


def format_report(result):
    """Render the result dictionary as plain text.

    Returns a string rather than printing. Rounding happens only here.
    """
    width = 64
    lines = []

    # 1. Who and what.
    lines.append("=" * width)
    lines.append(f"  Session:     {result['session']}")
    lines.append(f"  Participant: {result['participant']}")
    lines.append("=" * width)
    lines.append("")

    # 2. What arrived and what survived.
    counts = result["observations"]
    lines.append("OBSERVATIONS")
    lines.append(f"  Total received      {counts['total']:>4}")
    lines.append(f"  Usable              {counts['usable']:>4}")
    lines.append(f"    of which flagged  {counts['flagged']:>4}  (kept)")
    lines.append(f"  Rejected            {counts['rejected']:>4}")
    lines.append("")

    # 3. The figures.
    summary = result["summary"]
    lines.append("SUMMARY  (usable observations only)")
    if not summary:
        lines.append("  No usable observations to summarise.")
    else:
        lines.append(f"  {'Measurement':<16}{'Average':>10}{'Minimum':>10}"
                     f"{'Maximum':>10}   Unit")
        for field in SUMMARY_FIELDS:
            figures = summary[field]
            unit = FIELD_UNITS[field]
            places = FIELD_DECIMALS[field]
            lines.append(
                (f"  {FIELD_LABELS[field]:<16}"
                 f"{figures['avg']:>10.{places}f}"
                 f"{figures['min']:>10.{places}f}"
                 f"{figures['max']:>10.{places}f}   {unit}").rstrip()
            )
    lines.append("")

    # 4. Against this participant's own normals.
    comparison = result["comparison"]
    lines.append("COMPARISON WITH REFERENCE VALUES")
    if not comparison:
        lines.append("  Nothing to compare.")
    else:
        heart_rate = comparison["heart_rate"]
        temperature = comparison["temperature"]
        lines.append(f"  Heart rate    {heart_rate['average']:.1f} bpm  ->  "
                     f"{heart_rate['zone']}")
        lines.append(f"                bands: elevated "
                     f"{heart_rate['elevated_band']:.1f} bpm, high "
                     f"{heart_rate['high_band']:.1f} bpm")
        lines.append(f"                {heart_rate['above_resting']:+.1f} bpm "
                     f"relative to resting")
        lines.append(f"  Temperature   {temperature['average']:.1f} C  ->  "
                     f"{temperature['direction']}")
        lines.append(f"                reference "
                     f"{temperature['reference']:.1f} C, difference "
                     f"{temperature['difference']:+.1f} C")
        if "skin_response" in comparison:
            skin_response = comparison["skin_response"]
            lines.append(f"  Skin response {skin_response['average']:.1f} uS")
            lines.append(f"                reference "
                         f"{skin_response['reference']:.1f} uS, difference "
                         f"{skin_response['difference']:+.1f} uS")
    lines.append("")

    # 5. Recovery, stated either way.
    recovery = result["recovery"]
    lines.append("RECOVERY")
    if recovery["detected"]:
        required = recovery["required"]
        lines.append("  Detected.")
        lines.append(f"    Heart rate  {recovery['peak_heart_rate']:.1f} -> "
                     f"{recovery['final_heart_rate']:.1f} bpm  "
                     f"({recovery['heart_rate_drop']:.0%} fall, "
                     f"{required['heart_rate_drop']:.0%} required)")
        lines.append(f"    Activity    {recovery['peak_activity']:.2f} -> "
                     f"{recovery['final_activity']:.2f}       "
                     f"({recovery['activity_drop']:.0%} fall, "
                     f"{required['activity_drop']:.0%} required)")
    else:
        lines.append("  Not detected.")
        # The reason can be a full sentence, so it wraps like the
        # explanation rather than running off the edge of the terminal.
        for line in textwrap.wrap(recovery["reason"], width=width - 4):
            lines.append(f"    {line}")
    lines.append("")

    # 6. The verdict, and why.
    lines.append(f"CLASSIFICATION:  {result['classification'].upper()}")
    for line in textwrap.wrap(result["explanation"], width=width - 2):
        lines.append(f"  {line}")
    lines.append("")

    # 7. The two groups, kept apart: kept-but-imperfect, and discarded.
    lines.append(f"FLAGGED READINGS  ({counts['flagged']} kept)")
    if result["flag_notes"]:
        for note in result["flag_notes"]:
            lines.append(f"  - {note}")
    else:
        lines.append("  None.")
    lines.append("")

    lines.append(f"REJECTED READINGS  ({counts['rejected']} discarded)")
    if result["rejection_notes"]:
        for note in result["rejection_notes"]:
            lines.append(f"  - {note}")
    else:
        lines.append("  None.")

    return "\n".join(lines)
