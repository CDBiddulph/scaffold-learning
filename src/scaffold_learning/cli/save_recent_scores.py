#!/usr/bin/env python3
"""Save recent validation scores for an experiment."""

# TODO: do what this script does at the end of each experiment

import argparse
import json
from pathlib import Path
from scaffold_learning.core.experiment_files import ExperimentFileManager


def main():
    parser = argparse.ArgumentParser(
        description="Save recent validation scores for an experiment"
    )
    parser.add_argument(
        "experiment_name",
        help="Name of the experiment (e.g., keep_crosswords_20250711_195402)",
    )
    parser.add_argument(
        "--experiments-dir",
        default="experiments",
        help="Base directory containing experiments",
    )
    args = parser.parse_args()

    experiment_name = args.experiment_name
    experiments_dir = args.experiments_dir
    experiment_path = Path(experiments_dir) / experiment_name
    file_manager = ExperimentFileManager(experiment_path)

    # Get most recent validation scores
    scores = file_manager.get_most_recent_validation_scores()

    # Filter out scaffolds that have never been validated
    valid_scores = {}
    for scaffold_id, score_data in scores.items():
        if score_data is not None:
            valid_scores[scaffold_id] = score_data

    # Sort by mean score (highest first) and create ordered dict
    sorted_items = sorted(
        valid_scores.items(), key=lambda x: x[1]["mean_score"], reverse=True
    )
    sorted_scores = dict(sorted_items)

    # Save to file
    output_file = experiment_path / "scoring" / "all_valid_scores.json"
    with open(output_file, "w") as f:
        json.dump(sorted_scores, f, indent=2)

    print(f"Saved {len(sorted_scores)} scaffold scores to {output_file}")


if __name__ == "__main__":
    main()
