"""Sample scenarios used to demonstrate the analyzer.

Five scenarios come from the instructor-supplied generator in
data_generator.py, called with a fixed seed so every run produces the
same data and the reports can be compared against the README.

Two extras are added by hand, each for a reason the generator cannot
cover:

  * a three-reading session, because the generator requires at least six
    windows and so cannot produce a session that is too short to judge
  * the recovery data judged as an Athlete, so the overridden recovery
    threshold is visible in an ordinary run of main.py

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
