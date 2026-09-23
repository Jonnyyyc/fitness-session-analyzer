"""Sample scenarios used to demonstrate the analyzer.

Five scenarios come from the instructor-supplied generator in
data_generator.py, called with a fixed seed so every run produces the
same data and the reports can be compared against the README.

Three extras are added by hand, each for a reason the generator cannot
cover:

  * the recovery data judged as an Athlete, so the overridden recovery
    threshold is visible in an ordinary run of main.py
  * a degraded-sensor session, because the generator produces no signal
    quality in the 0.50 to 0.69 band and so never exercises the flagged
    tier, nor a session that survives a faulty sensor
  * a three-reading session, because the generator requires at least six
    windows and so cannot produce a session that is too short to judge

Each scenario is a dictionary with three keys:

    label        what to call the session in the report
    participant  the Participant (or Athlete) it belongs to
    records      raw observation dictionaries

Author: Jonathan Christensen
"""

from analyzer import Athlete, Participant
from data_generator import generate_fitness_data

# Fixed so the reports are reproducible. Changing it changes both the
# participant profile and the measurements.
SEED = 42
WINDOWS = 12

# The generator's scenario names, paired with a readable session title.
GENERATED_SCENARIOS = [
    ("resting", "Resting session"),
    ("moderate_activity", "Moderate activity session"),
    ("high_activity", "High activity session"),
    ("recovery", "Activity followed by recovery"),
    ("poor_quality", "Poor-quality sensor data"),
]


def build_generated_scenario(scenario, label, participant_class=Participant):
    """Build one scenario dictionary from the generator.

    The participant is built from the same profile the observations came
    with, so each session is judged against the reference values of the
    person it was recorded from rather than a shared default.
    """
    profile, observations = generate_fitness_data(
        participant_id="P001",
        scenario=scenario,
        seed=SEED,
        number_of_windows=WINDOWS,
    )
    return {
        "label": label,
        "participant": participant_class.from_profile(profile),
        "records": observations,
    }


SCENARIOS = [build_generated_scenario(scenario, label)
             for scenario, label in GENERATED_SCENARIOS]

# The same recovery measurements, judged as a trained participant. The
# readings are identical to the recovery session above, so any
# difference in the report comes from the subclass and nothing else.
SCENARIOS.append(build_generated_scenario(
    "recovery",
    "Activity followed by recovery, trained participant",
    participant_class=Athlete,
))

# Hand-written, because the generator never produces a signal quality
# between 0.50 and 0.69. Its poor_quality scenario puts every reading
# below 0.55 and also breaks each one outright, so all twelve are
# rejected. That leaves no generated session in which a reading is kept
# despite being doubtful. This scenario is therefore the only place in
# ordinary output where the flagged tier appears at all, and the only
# place a session survives a faulty sensor and still gets a real label.
SCENARIOS.append({
    "label": "Cycle commute, sensor slipping",
    "participant": Participant("Jonathan", resting_heart_rate=70),
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
})

# Hand-written, because generate_fitness_data() refuses fewer than six
# windows and this case needs fewer than five usable readings. Every
# reading here is perfectly good; there are simply too few of them,
# which is a different problem from poor quality.
SCENARIOS.append({
    "label": "Watch taken off after a minute",
    "participant": Participant("Jonathan", resting_heart_rate=70),
    "records": [
        {"timestamp": 0, "heart_rate": 118, "skin_response": 3.0,
         "temperature": 33.2, "activity_level": 0.52, "signal_quality": 0.96},
        {"timestamp": 1, "heart_rate": 120, "skin_response": 3.1,
         "temperature": 33.3, "activity_level": 0.54, "signal_quality": 0.95},
        {"timestamp": 2, "heart_rate": 122, "skin_response": 3.2,
         "temperature": 33.3, "activity_level": 0.56, "signal_quality": 0.97},
    ],
})
