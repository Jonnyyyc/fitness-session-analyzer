"""Sample scenarios used to demonstrate the analyzer.

Six scenarios: the five the assignment requires, plus "insufficient
data" as a separate sixth so that "too little evidence to judge" is
shown to be a different outcome from "poor quality data".

Each scenario is a dictionary with three keys:

    label        what to call the session in the report
    participant  the Participant (or Athlete) it belongs to
    records      raw sensor records, in the format from the brief

Records are written out as literal dictionaries rather than generated,
so that what the analyzer is given is exactly what can be read here.

Author: Jonathan Christensen
"""

from analyzer import Participant, Athlete

# One untrained participant for most scenarios, so differences in the
# reports come from the data rather than from the person.
JONATHAN = Participant("Jonathan", resting_heart_rate=70)

# The recovery scenario uses the Athlete, so a normal run of main.py
# shows the overridden recovery_thresholds() being applied: this
# session is judged against a 15% required drop, not 10%.
MARA = Athlete("Mara", resting_heart_rate=45)


RESTING = {
    "label": "Sitting at a desk",
    "participant": JONATHAN,
    "records": [
        {"timestamp": 0, "heart_rate": 72, "skin_response": 1.6,
         "temperature": 32.9, "activity_level": 0.03, "signal_quality": 0.96},
        {"timestamp": 1, "heart_rate": 74, "skin_response": 1.7,
         "temperature": 32.9, "activity_level": 0.04, "signal_quality": 0.95},
        {"timestamp": 2, "heart_rate": 73, "skin_response": 1.6,
         "temperature": 33.0, "activity_level": 0.02, "signal_quality": 0.97},
        {"timestamp": 3, "heart_rate": 75, "skin_response": 1.8,
         "temperature": 32.9, "activity_level": 0.05, "signal_quality": 0.94},
        {"timestamp": 4, "heart_rate": 72, "skin_response": 1.7,
         "temperature": 33.0, "activity_level": 0.03, "signal_quality": 0.96},
        {"timestamp": 5, "heart_rate": 74, "skin_response": 1.6,
         "temperature": 32.9, "activity_level": 0.04, "signal_quality": 0.95},
    ],
}

MODERATE = {
    "label": "Brisk walk",
    "participant": JONATHAN,
    "records": [
        {"timestamp": 0, "heart_rate": 98, "skin_response": 2.2,
         "temperature": 33.0, "activity_level": 0.30, "signal_quality": 0.95},
        {"timestamp": 1, "heart_rate": 100, "skin_response": 2.4,
         "temperature": 33.1, "activity_level": 0.32, "signal_quality": 0.96},
        {"timestamp": 2, "heart_rate": 102, "skin_response": 2.5,
         "temperature": 33.1, "activity_level": 0.34, "signal_quality": 0.94},
        {"timestamp": 3, "heart_rate": 104, "skin_response": 2.6,
         "temperature": 33.2, "activity_level": 0.36, "signal_quality": 0.95},
        {"timestamp": 4, "heart_rate": 106, "skin_response": 2.7,
         "temperature": 33.2, "activity_level": 0.38, "signal_quality": 0.97},
        {"timestamp": 5, "heart_rate": 108, "skin_response": 2.8,
         "temperature": 33.3, "activity_level": 0.40, "signal_quality": 0.96},
    ],
}

HIGH = {
    "label": "Hill sprints",
    "participant": JONATHAN,
    "records": [
        {"timestamp": 0, "heart_rate": 138, "skin_response": 4.2,
         "temperature": 33.6, "activity_level": 0.72, "signal_quality": 0.95},
        {"timestamp": 1, "heart_rate": 142, "skin_response": 4.6,
         "temperature": 33.7, "activity_level": 0.76, "signal_quality": 0.96},
        {"timestamp": 2, "heart_rate": 146, "skin_response": 5.0,
         "temperature": 33.9, "activity_level": 0.79, "signal_quality": 0.94},
        {"timestamp": 3, "heart_rate": 150, "skin_response": 5.4,
         "temperature": 34.0, "activity_level": 0.82, "signal_quality": 0.95},
        {"timestamp": 4, "heart_rate": 152, "skin_response": 5.6,
         "temperature": 34.1, "activity_level": 0.84, "signal_quality": 0.96},
        {"timestamp": 5, "heart_rate": 155, "skin_response": 5.8,
         "temperature": 34.2, "activity_level": 0.85, "signal_quality": 0.95},
    ],
}

# Warm-up, hard effort, then a cooldown. The peak is in the middle,
# which is what detect_recovery() is built to find.
RECOVERY = {
    "label": "Interval session with cooldown",
    "participant": MARA,
    "records": [
        {"timestamp": 0, "heart_rate": 90, "skin_response": 2.0,
         "temperature": 32.9, "activity_level": 0.35, "signal_quality": 0.96},
        {"timestamp": 1, "heart_rate": 105, "skin_response": 2.4,
         "temperature": 33.0, "activity_level": 0.45, "signal_quality": 0.95},
        {"timestamp": 2, "heart_rate": 120, "skin_response": 3.0,
         "temperature": 33.2, "activity_level": 0.55, "signal_quality": 0.94},
        {"timestamp": 3, "heart_rate": 165, "skin_response": 5.2,
         "temperature": 33.8, "activity_level": 0.88, "signal_quality": 0.95},
        {"timestamp": 4, "heart_rate": 170, "skin_response": 5.6,
         "temperature": 34.0, "activity_level": 0.92, "signal_quality": 0.96},
        {"timestamp": 5, "heart_rate": 168, "skin_response": 5.4,
         "temperature": 34.0, "activity_level": 0.90, "signal_quality": 0.95},
        {"timestamp": 6, "heart_rate": 120, "skin_response": 4.0,
         "temperature": 33.6, "activity_level": 0.30, "signal_quality": 0.94},
        {"timestamp": 7, "heart_rate": 105, "skin_response": 3.2,
         "temperature": 33.3, "activity_level": 0.20, "signal_quality": 0.95},
        {"timestamp": 8, "heart_rate": 95, "skin_response": 2.6,
         "temperature": 33.1, "activity_level": 0.12, "signal_quality": 0.96},
    ],
}

# Ten readings: three unusable, two doubtful but kept, five clean. The
# point is that the session is still classified - a faulty sensor
# degrades the evidence without destroying it.
POOR_QUALITY = {
    "label": "Cycle commute, sensor slipping",
    "participant": JONATHAN,
    "records": [
        {"timestamp": 0, "heart_rate": 102, "skin_response": 2.4,
         "temperature": 33.0, "activity_level": 0.32, "signal_quality": 0.95},
        # Kept, but the sensor was not confident.
        {"timestamp": 1, "heart_rate": 105, "skin_response": 2.5,
         "temperature": 33.1, "activity_level": 0.34, "signal_quality": 0.58},
        # Rejected: 'temperature' is missing entirely.
        {"timestamp": 2, "heart_rate": 107, "skin_response": 2.5,
         "activity_level": 0.35, "signal_quality": 0.93},
        {"timestamp": 3, "heart_rate": 108, "skin_response": 2.6,
         "temperature": 33.1, "activity_level": 0.36, "signal_quality": 0.95},
        # Rejected: 320 bpm is not a heart rate a person can have.
        {"timestamp": 4, "heart_rate": 320, "skin_response": 2.6,
         "temperature": 33.2, "activity_level": 0.38, "signal_quality": 0.94},
        # Kept, but doubtful.
        {"timestamp": 5, "heart_rate": 110, "skin_response": 2.7,
         "temperature": 33.2, "activity_level": 0.38, "signal_quality": 0.64},
        # Rejected: the sensor barely had a signal at all.
        {"timestamp": 6, "heart_rate": 112, "skin_response": 2.7,
         "temperature": 33.2, "activity_level": 0.40, "signal_quality": 0.35},
        {"timestamp": 7, "heart_rate": 113, "skin_response": 2.8,
         "temperature": 33.3, "activity_level": 0.41, "signal_quality": 0.96},
        {"timestamp": 8, "heart_rate": 115, "skin_response": 2.9,
         "temperature": 33.3, "activity_level": 0.43, "signal_quality": 0.95},
        {"timestamp": 9, "heart_rate": 116, "skin_response": 2.9,
         "temperature": 33.4, "activity_level": 0.44, "signal_quality": 0.97},
    ],
}

# Every reading here is perfectly good. There are simply too few of
# them, which is a different problem from poor quality above.
INSUFFICIENT = {
    "label": "Watch taken off after a minute",
    "participant": JONATHAN,
    "records": [
        {"timestamp": 0, "heart_rate": 118, "skin_response": 3.0,
         "temperature": 33.2, "activity_level": 0.52, "signal_quality": 0.96},
        {"timestamp": 1, "heart_rate": 120, "skin_response": 3.1,
         "temperature": 33.3, "activity_level": 0.54, "signal_quality": 0.95},
        {"timestamp": 2, "heart_rate": 122, "skin_response": 3.2,
         "temperature": 33.3, "activity_level": 0.56, "signal_quality": 0.97},
    ],
}


SCENARIOS = [
    RESTING,
    MODERATE,
    HIGH,
    RECOVERY,
    POOR_QUALITY,
    INSUFFICIENT,
]
