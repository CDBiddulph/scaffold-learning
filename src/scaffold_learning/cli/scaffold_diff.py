#!/usr/bin/env python3
"""Generate prompts showing scaffold evolution chains for analysis."""

import argparse
import json
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass

from scaffold_learning.core.experiment_files import ExperimentFileManager
from scaffold_learning.core.data_structures import ScaffoldResult


@dataclass
class ScaffoldWithId:
    """A scaffold with its ID and score for evolution tracking."""

    scaffold_id: str
    scaffold_result: ScaffoldResult
    score: Optional[float]


def get_evolution_chain(
    manager: ExperimentFileManager, scaffold_id: str, scores: Dict[str, Optional[float]]
) -> List[ScaffoldWithId]:
    """Get the full evolution chain for a scaffold, from root to target.

    Args:
        manager: ExperimentFileManager for the experiment
        scaffold_id: The target scaffold ID to trace
        scores: Dictionary of scaffold scores

    Returns:
        List of scaffolds with IDs and scores from root ancestor to target scaffold
    """
    # Trace backwards to root
    ancestors = []
    current_id = scaffold_id

    while current_id:
        scaffold = manager.load_scaffold(current_id)
        score = scores.get(current_id)
        ancestors.append(ScaffoldWithId(current_id, scaffold, score))
        current_id = scaffold.metadata.parent_scaffold_id

    if len(ancestors) <= 1:
        raise ValueError(f"Scaffold {scaffold_id} has no evolution chain")

    # Return in chronological order (root first)
    return list(reversed(ancestors))


def find_scaffolds(
    experiment_name: str, scaffold_id: str
) -> tuple[List[ScaffoldWithId], str]:
    """Find the experiment directory and get evolution chain with scores."""
    experiments_dir = Path("experiments")
    experiment_dirs = [
        d for d in experiments_dir.glob(f"{experiment_name}_*") if d.is_dir()
    ]

    if not experiment_dirs:
        raise FileNotFoundError(f"No experiment found with name '{experiment_name}'")

    if len(experiment_dirs) > 1:
        print(f"Multiple experiments found for '{experiment_name}':")
        for d in experiment_dirs:
            print(f"  {d.name}")
        # Use the most recent one
        experiment_dir = max(experiment_dirs, key=lambda d: d.stat().st_mtime)
        print(f"Using most recent: {experiment_dir.name}")
    else:
        experiment_dir = experiment_dirs[0]

    # Load the experiment
    manager = ExperimentFileManager(experiment_dir)

    # Get all validation scores
    all_scores = manager.get_most_recent_validation_scores()

    # Get the evolution chain with scores
    chain = get_evolution_chain(manager, scaffold_id, all_scores)
    return chain, experiment_dir.name


def generate_diff_prompt(experiment_name: str, scaffold_id: str) -> tuple[str, str]:
    """Generate a prompt showing the evolution chain for a scaffold.

    Args:
        experiment_name: Name of the experiment directory
        scaffold_id: Target scaffold ID to analyze

    Returns:
        Tuple of (prompt_string, full_experiment_name)
    """
    chain, full_experiment_name = find_scaffolds(experiment_name, scaffold_id)

    # Get scaffold IDs for display
    scaffold_ids = [scaffold_with_id.scaffold_id for scaffold_with_id in chain]

    # Build the prompt
    prompt_lines = [
        "The following series of Python files represents progressive changes to some code.",
        f"Each file version has an ID: {' → '.join(scaffold_ids)}",
        "",
        "Below are the Python files for each version in the chain:",
        "",
    ]

    # Add each scaffold's code
    for scaffold_with_id in chain:
        scaffold_id_str = scaffold_with_id.scaffold_id
        scaffold = scaffold_with_id.scaffold_result
        score = scaffold_with_id.score

        # Format score display
        score_text = f" (Score: {score:.3f})" if score is not None else " (Score: N/A)"

        # Add scaffold header
        prompt_lines.extend(
            [
                f"## Scaffold {scaffold_id_str}{score_text}",
                "",
                "```python",
                scaffold.code,
                "```",
                "",
            ]
        )

    chain_str = " to ".join(scaffold_ids)
    prompt_lines.extend(
        [
            "---",
            "",
            f"How did the code change from {chain_str}?",
            "",
            "Briefly explain each code diff. I already know the background of the problem that the code is trying to solve, so your explanation should only focus on how the strategy changes over time.",
            "",
            "Also briefly mention the validation score of each scaffold as you bring them up.",
        ]
    )

    return "\n".join(prompt_lines), full_experiment_name


def main():
    parser = argparse.ArgumentParser(
        description="Generate scaffold evolution diff prompts for analysis"
    )
    parser.add_argument("experiment_name", help="Name of the experiment")
    parser.add_argument("scaffold_id", help="Target scaffold ID to analyze")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("scratch/scaffold-diff-prompts"),
        help="Directory to save the prompt file",
    )

    args = parser.parse_args()

    try:
        # Generate the prompt
        prompt, full_experiment_name = generate_diff_prompt(
            args.experiment_name, args.scaffold_id
        )

        # Create output directory
        args.output_dir.mkdir(parents=True, exist_ok=True)

        # Create filename
        filename = f"{full_experiment_name}_{args.scaffold_id}.md"
        output_path = args.output_dir / filename

        # Save the prompt
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(prompt)

        print(f"Scaffold diff prompt saved to: {output_path}")
        print(f"Evolution chain analyzed: {args.experiment_name} → {args.scaffold_id}")

    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
