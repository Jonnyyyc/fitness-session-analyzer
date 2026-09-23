"""Unit tests for the Smart Fitness Session Analyzer.

Run from the repository root:
    python3 -m unittest tests.py     (macOS / Linux)
    python -m unittest tests.py      (Windows)

Author: Jonathan Christensen
"""

import unittest

from analyzer import (Athlete, Participant, Session, detect_recovery,
                      format_report, heart_rate_zone, summarise,
                      validate_observation)


def record(**overrides):
    """A valid sensor record, with any named field replaced."""
    base = {"timestamp": 0, "heart_rate": 110, "skin_response": 2.5,
            "temperature": 32.9, "activity_level": 0.40,
            "signal_quality": 0.95}
    base.update(overrides)
    return base


def analyse(participant, rows, label="test"):
    """Build a session from raw records and return its result."""
    session = Session(participant, label=label)
    session.add_many(rows)
    return session.analyse()


# Resting 70, max 190 -> elevated band 94.0 bpm, high band 130.0 bpm.
JONATHAN = Participant("Jonathan", resting_heart_rate=70)
# Resting 45, max 190 -> elevated band 74.0 bpm, high band 117.5 bpm.
MARA = Athlete("Mara", resting_heart_rate=45)


class TestValidation(unittest.TestCase):

    def test_accepts_a_valid_record(self):
        result = validate_observation(record())
        self.assertTrue(result["ok"])
        self.assertEqual(result["flags"], [])

    def test_rejects_missing_field(self):
        incomplete = record()
        del incomplete["temperature"]
        result = validate_observation(incomplete)
        self.assertFalse(result["ok"])
        self.assertIn("temperature", result["reason"])

    def test_rejects_non_number(self):
        result = validate_observation(record(heart_rate="fast"))
        self.assertFalse(result["ok"])
        self.assertIn("must be a number", result["reason"])

    def test_rejects_boolean(self):
        # bool subclasses int, so True would otherwise pass as 1.
        result = validate_observation(record(activity_level=True))
        self.assertFalse(result["ok"])
        self.assertIn("bool", result["reason"])

    def test_rejects_impossible_heart_rate(self):
        for value in (-40, 320):
            with self.subTest(heart_rate=value):
                result = validate_observation(record(heart_rate=value))
                self.assertFalse(result["ok"])
                self.assertIn("heart_rate", result["reason"])

    def test_rejects_activity_outside_zero_to_one(self):
        for value in (-0.1, 1.4):
            with self.subTest(activity_level=value):
                result = validate_observation(record(activity_level=value))
                self.assertFalse(result["ok"])
                self.assertIn("activity_level", result["reason"])

    def test_rejects_signal_below_cutoff(self):
        result = validate_observation(record(signal_quality=0.31))
        self.assertFalse(result["ok"])
        self.assertIn("signal quality", result["reason"])

    def test_signal_quality_boundaries(self):
        # 0.49 rejected, 0.50 and 0.69 kept with a flag, 0.70 clean.
        self.assertFalse(validate_observation(record(signal_quality=0.49))["ok"])
        for value in (0.50, 0.69):
            with self.subTest(signal_quality=value):
                result = validate_observation(record(signal_quality=value))
                self.assertTrue(result["ok"])
                self.assertTrue(result["flags"])
        clean = validate_observation(record(signal_quality=0.70))
        self.assertTrue(clean["ok"])
        self.assertEqual(clean["flags"], [])


class TestParticipant(unittest.TestCase):

    def test_property_rejects_bad_resting_heart_rate(self):
        for value in (-5, 0, 200, "sixty", True):
            with self.subTest(resting_heart_rate=value):
                with self.assertRaises(ValueError):
                    Participant("X", resting_heart_rate=value)

    def test_maximum_must_exceed_resting(self):
        with self.assertRaises(ValueError):
            Participant("X", resting_heart_rate=110, max_heart_rate=105)

    def test_resting_cannot_later_be_raised_above_maximum(self):
        person = Participant("X", resting_heart_rate=60, max_heart_rate=110)
        with self.assertRaises(ValueError):
            person.resting_heart_rate = 115

    def test_athlete_overrides_recovery_thresholds(self):
        self.assertEqual(JONATHAN.recovery_thresholds()["heart_rate_drop"], 0.10)
        self.assertEqual(MARA.recovery_thresholds()["heart_rate_drop"], 0.15)
        # The parent's activity threshold is inherited unchanged.
        self.assertEqual(MARA.recovery_thresholds()["activity_drop"], 0.30)


class TestCalculations(unittest.TestCase):

    def test_summarise_known_readings(self):
        session = Session(JONATHAN)
        session.add_many([record(timestamp=t, heart_rate=hr)
                          for t, hr in [(0, 110), (1, 126), (2, 118)]])
        heart_rate = summarise(session.observations)["heart_rate"]
        self.assertAlmostEqual(heart_rate["avg"], 118.0)   # (110+126+118)/3
        self.assertEqual(heart_rate["min"], 110)
        self.assertEqual(heart_rate["max"], 126)

    def test_summarise_empty(self):
        self.assertEqual(summarise([]), {})

    def test_summarise_excludes_rejected_readings(self):
        session = Session(JONATHAN)
        session.add_many([record(timestamp=0, heart_rate=120),
                          record(timestamp=1, heart_rate=-40),   # rejected
                          record(timestamp=2, heart_rate=124)])
        self.assertEqual(summarise(session.observations)["heart_rate"]["avg"], 122)

    def test_heart_rate_zone_at_exact_band_values(self):
        bands = JONATHAN.heart_rate_bands()          # elevated 94.0, high 130.0
        self.assertEqual(heart_rate_zone(93.9, bands), "below elevated")
        self.assertEqual(heart_rate_zone(94.0, bands), "elevated")
        self.assertEqual(heart_rate_zone(129.9, bands), "elevated")
        self.assertEqual(heart_rate_zone(130.0, bands), "high")


class TestClassification(unittest.TestCase):

    def test_resting(self):
        rows = [record(timestamp=t, heart_rate=73, activity_level=0.03)
                for t in range(6)]
        self.assertEqual(analyse(JONATHAN, rows)["classification"], "resting")

    def test_moderate_activity(self):
        rows = [record(timestamp=t, heart_rate=105, activity_level=0.35)
                for t in range(6)]
        self.assertEqual(analyse(JONATHAN, rows)["classification"],
                         "moderate activity")

    def test_high_activity(self):
        rows = [record(timestamp=t, heart_rate=145, activity_level=0.80)
                for t in range(6)]
        self.assertEqual(analyse(JONATHAN, rows)["classification"],
                         "high activity")

    def test_recovering(self):
        # Warm-up, hard effort, cooldown: the peak sits in the middle.
        readings = [(95, 0.35), (100, 0.40), (150, 0.85),
                    (155, 0.88), (105, 0.20), (100, 0.15)]
        rows = [record(timestamp=t, heart_rate=hr, activity_level=act)
                for t, (hr, act) in enumerate(readings)]
        self.assertEqual(analyse(JONATHAN, rows)["classification"], "recovering")

    def test_insufficient_data(self):
        rows = [record(timestamp=t, heart_rate=120) for t in range(3)]
        result = analyse(JONATHAN, rows)
        self.assertEqual(result["classification"], "insufficient data")
        self.assertEqual(result["observations"]["usable"], 3)

    def test_explanation_names_the_deciding_figures(self):
        rows = [record(timestamp=t, heart_rate=145, activity_level=0.80)
                for t in range(6)]
        explanation = analyse(JONATHAN, rows)["explanation"]
        self.assertIn("145.0 bpm", explanation)
        self.assertIn("130.0 bpm", explanation)   # the high band it crossed


class TestRecovery(unittest.TestCase):

    def _observations(self, participant, readings):
        session = Session(participant)
        session.add_many([record(timestamp=t, heart_rate=hr, activity_level=act)
                          for t, (hr, act) in enumerate(readings)])
        return session.ordered_observations()

    def test_detected_on_cooldown_shape(self):
        readings = [(95, 0.35), (100, 0.40), (150, 0.85),
                    (155, 0.88), (105, 0.20), (100, 0.15)]
        recovery = detect_recovery(self._observations(JONATHAN, readings),
                                   JONATHAN)
        self.assertTrue(recovery["detected"])
        self.assertGreater(recovery["heart_rate_drop"], 0.10)
        self.assertGreater(recovery["activity_drop"], 0.30)

    def test_not_detected_when_resting_heart_rate_drifts_down(self):
        # Heart rate falls, but never rose. There is nothing to recover from.
        readings = [(80, 0.04), (78, 0.03), (76, 0.03),
                    (72, 0.02), (70, 0.01), (70, 0.01)]
        recovery = detect_recovery(self._observations(JONATHAN, readings),
                                   JONATHAN)
        self.assertFalse(recovery["detected"])
        self.assertIn("nothing to recover from", recovery["reason"])

    def test_between_the_bars_separates_participant_from_athlete(self):
        # Peak third 130 bpm, final third 116 -> a 10.8% fall. That clears
        # the untrained 10% requirement but not the athlete's 15%.
        readings = [(100, 0.5), (100, 0.5), (130, 0.8),
                    (130, 0.8), (116, 0.4), (116, 0.4)]
        rows = [record(timestamp=t, heart_rate=hr, activity_level=act)
                for t, (hr, act) in enumerate(readings)]

        untrained = analyse(JONATHAN, rows)
        self.assertTrue(untrained["recovery"]["detected"])
        self.assertEqual(untrained["classification"], "recovering")

        trained = analyse(MARA, rows)
        self.assertFalse(trained["recovery"]["detected"])
        self.assertEqual(trained["classification"], "moderate activity")

    def test_motionless_participant_does_not_divide_by_zero(self):
        readings = [(90, 0.0), (85, 0.0), (80, 0.0),
                    (75, 0.0), (72, 0.0), (70, 0.0)]
        recovery = detect_recovery(self._observations(JONATHAN, readings),
                                   JONATHAN)
        self.assertFalse(recovery["detected"])
        self.assertEqual(recovery["activity_drop"], 0.0)


class TestReport(unittest.TestCase):

    def test_report_contains_label_and_counts(self):
        rows = [record(timestamp=0, signal_quality=0.62),   # flagged
                record(timestamp=1, heart_rate=-40),        # rejected
                record(timestamp=2, heart_rate=145, activity_level=0.80),
                record(timestamp=3, heart_rate=146, activity_level=0.81),
                record(timestamp=4, heart_rate=147, activity_level=0.82),
                record(timestamp=5, heart_rate=148, activity_level=0.83),
                record(timestamp=6, heart_rate=149, activity_level=0.84)]
        result = analyse(JONATHAN, rows, label="Report check")
        text = format_report(result)

        self.assertIsInstance(text, str)
        self.assertIn("Report check", text)
        self.assertIn("HIGH ACTIVITY", text)
        self.assertIn("FLAGGED READINGS  (1 kept)", text)
        self.assertIn("REJECTED READINGS  (1 discarded)", text)
        self.assertIn("weak signal", text)

    def test_report_handles_a_session_with_nothing_usable(self):
        rows = [record(timestamp=t, signal_quality=0.10) for t in range(4)]
        text = format_report(analyse(JONATHAN, rows))
        self.assertIn("No usable observations to summarise.", text)
        self.assertIn("INSUFFICIENT DATA", text)


if __name__ == "__main__":
    unittest.main()
