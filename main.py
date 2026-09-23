"""Smart Fitness Session Analyzer: entry point.

Runs every sample scenario and prints its report.

Run from the repository root:
    python3 main.py     (macOS / Linux)
    python main.py      (Windows)

Author: Jonathan Christensen
"""

from analyzer import Session, format_report
from sample_data import SCENARIOS


def main():
    # One session per scenario. All the work happens in analyzer.py;
    # this loop only feeds it data and prints what comes back.
    for scenario in SCENARIOS:
        session = Session(scenario["participant"], label=scenario["label"])
        session.add_many(scenario["records"])
        print(format_report(session.analyse()))
        print()


if __name__ == "__main__":
    main()
