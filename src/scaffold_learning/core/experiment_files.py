import json
import shutil
import os
from pathlib import Path
from typing import Dict, Any, Optional
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
        (self.experiment_dir / "scaffolds").mkdir(exist_ok=True)
        (self.experiment_dir / "logs").mkdir(exist_ok=True)
        (self.experiment_dir / "scoring").mkdir(exist_ok=True)

    def save_experiment_metadata(self, metadata: Dict[str, Any]) -> None:
        """Save experiment-level metadata.

        Args:
            metadata: Dictionary containing experiment metadata (e.g., random_seed)
        """
        metadata_file = self.experiment_dir / "metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)

    def save_scaffold(self, scaffold_id: str, result: ScaffoldResult) -> None:
        """Save a scaffold to the experiment directory.

        Args:
            scaffold_id: Unique identifier for this scaffold
            result: ScaffoldResult containing code and metadata

        Raises:
            OSError: If scaffold cannot be saved
        """
        scaffold_dir = self.experiment_dir / "scaffolds" / scaffold_id
        scaffold_dir.mkdir(parents=True, exist_ok=True)

        # Write scaffold.py
        (scaffold_dir / "scaffold.py").write_text(result.code)

        # Write metadata.json
        with open(scaffold_dir / "metadata.json", "w") as f:
            json.dump(result.metadata.to_dict(), f, indent=2)

        # Copy support files
        support_files = ["llm_executor.py", "llm_interfaces.py"]

        for support_file in support_files:
            source_path = Path("scaffold-scripts") / support_file
            if source_path.exists():
                shutil.copy2(source_path, scaffold_dir / support_file)
            else:
                # Try alternative location
                source_path = Path("src/scaffold_learning/core") / support_file
                if source_path.exists():
                    shutil.copy2(source_path, scaffold_dir / support_file)

    def load_scaffold(self, scaffold_id: str) -> ScaffoldResult:
        """Load a scaffold from disk.

        Args:
            scaffold_id: Scaffold identifier

        Returns:
            ScaffoldResult with code and metadata

        Raises:
            FileNotFoundError: If scaffold doesn't exist
        """
        scaffold_path = self.experiment_dir / "scaffolds" / scaffold_id

        if not scaffold_path.exists():
            raise FileNotFoundError(f"Scaffold not found: {scaffold_path}")

        # Load code
        code = (scaffold_path / "scaffold.py").read_text()

        # Load metadata
        with open(scaffold_path / "metadata.json") as f:
            metadata_dict = json.load(f)
        metadata = ScaffoldMetadata.from_dict(metadata_dict)

        return ScaffoldResult(code=code, metadata=metadata)

    def get_docker_scaffold_dir(self, scaffold_id: str) -> Path:
        """Get scaffold directory path for Docker mounting.

        Args:
            scaffold_id: Scaffold identifier

        Returns:
            Absolute path to scaffold directory

        Raises:
            FileNotFoundError: If scaffold doesn't exist
        """
        scaffold_path = self.experiment_dir / "scaffolds" / scaffold_id

        if not scaffold_path.exists():
            raise FileNotFoundError(f"Scaffold not found: {scaffold_path}")

        return scaffold_path.absolute()

    def get_docker_logs_dir(self, iteration: int, scaffold_id: str) -> Path:
        """Get logs directory path for Docker mounting.

        Args:
            iteration: Iteration number
            scaffold_id: Scaffold identifier

        Returns:
            Absolute path to logs directory
        """
        logs_dir = self.experiment_dir / "logs" / str(iteration) / scaffold_id
        logs_dir.mkdir(parents=True, exist_ok=True)
        return logs_dir.absolute()

    def _get_logs_path(self, iteration: int, scaffold_id: str, run_type: str) -> Path:
        """Get path for saving execution logs.

        Args:
            iteration: Iteration number
            scaffold_id: Scaffold identifier
            run_type: Type of run (e.g., 'train_0', 'valid_1')

        Returns:
            Path where logs should be saved
        """
        logs_dir = self.get_docker_logs_dir(iteration, scaffold_id)
        return logs_dir / f"{run_type}.log"

    def save_execution_log(
        self, iteration: int, scaffold_id: str, run_type: str, log_content: str
    ) -> str:
        """Save execution log and return the run ID used.

        Args:
            iteration: Iteration number
            scaffold_id: Scaffold identifier
            run_type: Type of run (e.g., 'train', 'valid')
            log_content: Full log content to save

        Returns:
            The run ID that was used (e.g., 'train_0', 'valid_1')
        """
        run_id = self._get_next_run_id(iteration, scaffold_id, run_type)
        logs_dir = self.get_docker_logs_dir(iteration, scaffold_id)
        log_path = logs_dir / f"{run_id}.log"

        with open(log_path, "w") as f:
            f.write(log_content)

        return run_id

    def _get_next_run_id(self, iteration: int, scaffold_id: str, run_type: str) -> str:
        """Determine the next available run ID for a given run type.

        Args:
            iteration: Iteration number
            scaffold_id: Scaffold identifier
            run_type: Type of run (e.g., 'train', 'valid')

        Returns:
            Next available run ID (e.g., 'train_0', 'train_1', 'valid_0')

        Raises:
            ValueError: If the run type is not 'train' or 'valid'
        """
        if run_type not in ["train", "valid"]:
            raise ValueError(
                f"Invalid run type: {run_type}. Must be 'train' or 'valid'."
            )

        logs_dir = self.experiment_dir / "logs" / str(iteration) / scaffold_id

        if not logs_dir.exists():
            return f"{run_type}_0"

        # Find existing log files for this run type
        existing_files = list(logs_dir.glob(f"{run_type}_*.log"))

        if not existing_files:
            return f"{run_type}_0"

        # Extract numbers from existing files
        indices = []
        for file_path in existing_files:
            name = file_path.stem  # Remove .log extension
            if name.startswith(f"{run_type}_"):
                # Raises ValueError if it doesn't end with an integer
                index = int(name[len(f"{run_type}_") :])
                indices.append(index)

        # Return the next available index
        next_index = max(indices) + 1 if indices else 0
        return f"{run_type}_{next_index}"

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
        scoring_dir = self.experiment_dir / "scoring"
        scoring_dir.mkdir(parents=True, exist_ok=True)

        scores_data = {"train": train_scores, "valid": valid_scores}

        with open(scoring_dir / f"scores_{iteration}.json", "w") as f:
            json.dump(scores_data, f, indent=2)

    def load_scores(self, iteration: int) -> Dict[str, Dict[str, float]]:
        """Load scores from a previous iteration.

        Args:
            iteration: Iteration number to load

        Returns:
            Dictionary mapping "train" and "valid" to their respective scores

        Raises:
            FileNotFoundError: If scoring file doesn't exist for iteration
        """
        scoring_file = self.experiment_dir / "scoring" / f"scores_{iteration}.json"

        if not scoring_file.exists():
            raise FileNotFoundError(f"Scoring file not found: {scoring_file}")

        with open(scoring_file) as f:
            scores_data = json.load(f)

        return scores_data

    def get_most_recent_validation_scores(self) -> Dict[str, Optional[float]]:
        """Get the most recent validation scores for all scaffolds.

        Returns:
            Dictionary mapping scaffold_id to most recent validation score (None if never validated)
        """
        # Find all scaffold IDs by scanning scaffolds directory
        scaffolds_dir = self.experiment_dir / "scaffolds"
        if not scaffolds_dir.exists():
            return {}

        all_scaffold_ids = [d.name for d in scaffolds_dir.iterdir() if d.is_dir()]

        # Initialize all scaffolds with None (never validated)
        most_recent_scores = {scaffold_id: None for scaffold_id in all_scaffold_ids}

        # Look through all score files to find most recent validation scores
        scores_dir = self.experiment_dir / "scoring"
        if not scores_dir.exists():
            return most_recent_scores

        # Find all score files and sort by iteration number
        score_files = []
        for score_file in scores_dir.glob("scores_*.json"):
            try:
                iteration = int(score_file.stem.split("_")[1])
                score_files.append((iteration, score_file))
            except (ValueError, IndexError):
                continue

        score_files.sort(key=lambda x: x[0])  # Sort by iteration

        # Process score files in order to get most recent scores
        for iteration, score_file in score_files:
            try:
                scores_data = json.loads(score_file.read_text())
                valid_scores = scores_data.get("valid", {})

                for scaffold_id, score_data in valid_scores.items():
                    if scaffold_id in most_recent_scores:
                        most_recent_scores[scaffold_id] = score_data["mean_score"]
            except (json.JSONDecodeError, KeyError):
                continue

        return most_recent_scores
