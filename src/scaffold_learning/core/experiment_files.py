import json
import numpy as np
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List
from collections import defaultdict
from scaffold_learning.core.data_structures import ScaffoldResult, ScaffoldMetadata
from scaffold_learning.core.xml_utils import write_xml_file, read_xml_file
from scaffold_learning.core.scaffold_files import save_scaffold as save_scaffold_files


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

        # Thread-safe counters for log file naming
        self._run_id_counters = defaultdict(
            int
        )  # key: (iteration, scaffold_id, run_type)
        self._counter_lock = threading.Lock()

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
        save_scaffold_files(scaffold_dir, result)

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
        metadata_dict = read_xml_file(scaffold_path / "metadata.xml")
        metadata = ScaffoldMetadata.from_dict(metadata_dict)

        return ScaffoldResult(code=code, metadata=metadata)

    def get_scaffold_dir(self, scaffold_id: str) -> Path:
        """Get scaffold directory path.

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

    def get_new_execution_log_path(
        self, iteration: int, scaffold_id: str, run_type: str
    ) -> Path:
        """Get a new path to an execution log to write to.

        Args:
            iteration: Iteration number
            scaffold_id: Scaffold identifier
            run_type: Type of run (e.g., 'train', 'valid')

        Returns:
            The path to the execution log
        """
        run_id = self._get_next_run_id(iteration, scaffold_id, run_type)
        logs_dir = self._get_docker_logs_dir(iteration, scaffold_id)
        return logs_dir / f"{run_id}.log"

    def _get_docker_logs_dir(self, iteration: int, scaffold_id: str) -> Path:
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

        counter_key = (iteration, scaffold_id, run_type)

        with self._counter_lock:
            # Get the next ID and increment counter (starts at 0)
            next_index = self._run_id_counters[counter_key]
            self._run_id_counters[counter_key] += 1

        return f"{run_type}_{next_index}"

    def save_scores(
        self,
        iteration: int,
        train_scores: Dict[str, List[float]],
        valid_scores: Dict[str, List[float]],
    ) -> None:
        """Save training and validation scores for an iteration.

        Args:
            iteration: Iteration number
            train_scores: Dictionary mapping scaffold_id to training score
            valid_scores: Dictionary mapping scaffold_id to validation score
        """
        scoring_dir = self.experiment_dir / "scoring"
        scoring_dir.mkdir(parents=True, exist_ok=True)

        def make_full_dicts(
            scores: Dict[str, List[float]]
        ) -> Dict[str, Dict[str, Any]]:
            result = {}
            for scaffold_id, scaffold_scores in scores.items():
                result[scaffold_id] = {
                    "mean_score": np.mean(scaffold_scores),
                    "scores": scaffold_scores,
                }
            return result

        scores_data = {
            "train": make_full_dicts(train_scores),
            "valid": make_full_dicts(valid_scores),
        }

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

    def get_most_recent_validation_scores(
        self,
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """Get the most recent validation scores for all scaffolds.

        Returns:
            Dictionary mapping scaffold_id to {
                'mean_score': float,
                'scores': List[float]
            }, or None if the scaffold has never been validated
        """
        # Find all scaffold IDs by scanning scaffolds directory
        scaffolds_dir = self.experiment_dir / "scaffolds"
        if not scaffolds_dir.exists():
            return {}

        all_scaffold_ids = [d.name for d in scaffolds_dir.iterdir() if d.is_dir()]

        # Initialize all scaffolds with None (never validated)
        most_recent_scores: Dict[str, Optional[Dict[str, Any]]] = {
            scaffold_id: None for scaffold_id in all_scaffold_ids
        }

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
                    if scaffold_id not in most_recent_scores:
                        continue
                    most_recent_scores[scaffold_id] = {
                        "mean_score": score_data.get("mean_score"),
                        "scores": score_data.get("scores", []),
                    }
            except (json.JSONDecodeError, KeyError):
                continue

        return most_recent_scores
