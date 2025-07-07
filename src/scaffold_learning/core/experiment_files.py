import json
import shutil
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from scaffold_learning.core.data_structures import ScaffoldResult, ScaffoldMetadata


class ExperimentFileManager:
    """Manages all file operations for an experiment."""

    def __init__(self, experiment_dir: Path):
        """Initialize file manager for an experiment.

        Args:
            experiment_dir: Root directory for this experiment
        """
        self.experiment_dir = experiment_dir
        self.experiment_dir.mkdir(parents=True, exist_ok=True)
        (self.experiment_dir / "iterations").mkdir(exist_ok=True)

    def save_experiment_metadata(self, metadata: Dict[str, Any]) -> None:
        """Save experiment-level metadata.

        Args:
            metadata: Dictionary containing experiment metadata (e.g., random_seed)
        """
        metadata_file = self.experiment_dir / "metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)

    def save_scaffold(
        self, iteration: int, scaffold_id: str, result: ScaffoldResult
    ) -> Path:
        """Save a scaffold to the experiment directory structure.

        Args:
            iteration: Iteration number (0 for initial scaffolds)
            scaffold_id: Unique identifier for this scaffold
            result: ScaffoldResult containing code and metadata

        Returns:
            Path to the created scaffold directory
        """
        # Determine directory structure based on iteration
        if iteration == 0:
            scaffold_dir = (
                self.experiment_dir
                / "iterations"
                / "0"
                / "scaffolds"
                / "new"
                / scaffold_id
            )
        else:
            scaffold_dir = (
                self.experiment_dir
                / "iterations"
                / str(iteration)
                / "scaffolds"
                / "new"
                / scaffold_id
            )

        scaffold_dir.mkdir(parents=True, exist_ok=True)

        # Write scaffold.py
        (scaffold_dir / "scaffold.py").write_text(result.code)

        # Write metadata.json
        with open(scaffold_dir / "metadata.json", "w") as f:
            json.dump(result.metadata.to_dict(), f, indent=2)

        # Copy support files
        self._copy_support_files(scaffold_dir)

        return scaffold_dir

    def _copy_support_files(self, scaffold_dir: Path) -> None:
        """Copy llm_executor.py and llm_interfaces.py to scaffold directory."""
        # Get paths to source files
        base_dir = Path(__file__).parent.parent
        runtime_dir = base_dir / "runtime"
        core_dir = base_dir / "core"

        # Copy llm_executor.py from runtime
        if (runtime_dir / "llm_executor.py").exists():
            shutil.copy2(
                runtime_dir / "llm_executor.py", scaffold_dir / "llm_executor.py"
            )

        # Copy llm_interfaces.py from core
        if (core_dir / "llm_interfaces.py").exists():
            shutil.copy2(
                core_dir / "llm_interfaces.py", scaffold_dir / "llm_interfaces.py"
            )

    def load_scaffold(self, iteration: int, scaffold_id: str) -> ScaffoldResult:
        """Load a scaffold from disk.

        Args:
            iteration: Iteration number
            scaffold_id: Scaffold identifier

        Returns:
            ScaffoldResult with code and metadata

        Raises:
            FileNotFoundError: If scaffold doesn't exist
        """
        scaffold_path = self.get_scaffold_path(iteration, scaffold_id)

        if not scaffold_path.exists():
            raise FileNotFoundError(f"Scaffold not found: {scaffold_path}")

        # Load code
        code = (scaffold_path / "scaffold.py").read_text()

        # Load metadata
        with open(scaffold_path / "metadata.json") as f:
            metadata_dict = json.load(f)
        metadata = ScaffoldMetadata.from_dict(metadata_dict)

        return ScaffoldResult(code=code, metadata=metadata)

    def _get_new_scaffold_dir(self, iteration: int) -> Path:
        """Get the directory path for the "new" scaffolds in an iteration.

        Args:
            iteration: Iteration number
        """
        return self.experiment_dir / "iterations" / str(iteration) / "scaffolds" / "new"

    def list_scaffolds(self, iteration: int) -> List[str]:
        """List all scaffolds for an iteration.

        Args:
            iteration: Iteration number

        Returns:
            The ID of each "new" scaffold in the iteration

        Raises:
            FileNotFoundError: If iteration directory does not exist
        """
        new_dir = self._get_new_scaffold_dir(iteration)
        if not new_dir.exists():
            raise FileNotFoundError(f"Iteration {iteration} not found")
        return [
            scaffold_dir.name
            for scaffold_dir in new_dir.iterdir()
            if scaffold_dir.is_dir()
        ]

    def find_scaffold_iteration(self, scaffold_id: str) -> int:
        """Find which iteration created a scaffold.

        Args:
            scaffold_id: Scaffold identifier to search for

        Returns:
            The iteration number where this scaffold was first created

        Raises:
            FileNotFoundError: If scaffold is not found in any iteration
        """
        # Check each iteration's new/ directory
        iteration = 0
        while True:
            new_dir = self._get_new_scaffold_dir(iteration)
            if not new_dir.exists():
                break

            scaffold_path = new_dir / scaffold_id
            if scaffold_path.exists() and scaffold_path.is_dir():
                return iteration

            iteration += 1

        raise FileNotFoundError(f"Scaffold {scaffold_id} not found in any iteration")

    def get_scaffold_path(self, iteration: int, scaffold_id: str) -> Path:
        """Get the directory path for a scaffold,

        Args:
            iteration: Iteration number
            scaffold_id: Scaffold identifier

        Returns:
            Path to "new" scaffold directory

        Raises:
            FileNotFoundError: If scaffold doesn't exist in this iteration
        """
        return self._get_new_scaffold_dir(iteration) / scaffold_id

    def copy_scaffold(
        self, from_path: Path, to_iteration: int, to_scaffold_id: str
    ) -> Path:
        """Copy a scaffold to a new location in the experiment structure.

        Args:
            from_path: Source scaffold directory
            to_iteration: Target iteration number
            to_scaffold_id: New scaffold identifier

        Returns:
            Path to the copied scaffold directory
        """
        # Target goes to old/ directory for iteration 1+
        target_path = (
            self.experiment_dir
            / "iterations"
            / str(to_iteration)
            / "scaffolds"
            / "old"
            / to_scaffold_id
        )

        target_path.mkdir(parents=True, exist_ok=True)

        # Copy all files from source to target
        for file_path in from_path.iterdir():
            if file_path.is_file():
                shutil.copy2(file_path, target_path / file_path.name)

        return target_path

    def save_scores(
        self,
        iteration: int,
        train_scores: Dict[str, float],
        valid_scores: Dict[str, float],
    ) -> None:
        """Save training and validation scores for an iteration.

        Args:
            iteration: Iteration number
            train_scores: Dictionary mapping scaffold_id to training score
            valid_scores: Dictionary mapping scaffold_id to validation score
        """
        iteration_dir = self.experiment_dir / "iterations" / str(iteration)
        iteration_dir.mkdir(parents=True, exist_ok=True)

        scores_data = {"train": train_scores, "valid": valid_scores}

        with open(iteration_dir / "scoring.json", "w") as f:
            json.dump(scores_data, f, indent=2)

    def load_scores(self, iteration: int) -> Dict[str, Dict[str, float]]:
        """Load scores from a previous iteration.

        Args:
            iteration: Iteration number to load

        Returns:
            Dictionary mapping "train" and "valid" to their respective scores

        Raises:
            FileNotFoundError: If scoring.json doesn't exist for iteration
        """
        scoring_file = (
            self.experiment_dir / "iterations" / str(iteration) / "scoring.json"
        )

        if not scoring_file.exists():
            raise FileNotFoundError(f"Scoring file not found: {scoring_file}")

        with open(scoring_file) as f:
            scores_data = json.load(f)

        return scores_data

    def get_logs_path(self, iteration: int, scaffold_id: str, run_type: str) -> Path:
        """Get path for saving execution logs.

        Args:
            iteration: Iteration number
            scaffold_id: Scaffold identifier
            run_type: Either 'train' or 'valid'

        Returns:
            Path where logs should be saved
        """
        logs_dir = (
            self.experiment_dir / "iterations" / str(iteration) / "logs" / scaffold_id
        )
        logs_dir.mkdir(parents=True, exist_ok=True)
        return logs_dir / f"{run_type}.log"
