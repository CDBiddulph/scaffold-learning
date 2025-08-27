import json
import numpy as np
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from collections import defaultdict
from datetime import datetime
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

        # Thread-safe locks for scoring file updates
        self._scores_lock = threading.Lock()
        self._all_valid_lock = threading.Lock()

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
        self, iteration: Union[int, str], scaffold_id: str, run_type: str
    ) -> Path:
        """Get a new path to an execution log to write to.

        Args:
            iteration: Iteration number or "test" for test runs
            scaffold_id: Scaffold identifier
            run_type: Type of run (e.g., 'train', 'valid', 'test')

        Returns:
            The path to the execution log
        """
        run_id = self._get_next_run_id(iteration, scaffold_id, run_type)
        logs_dir = self._get_docker_logs_dir(iteration, scaffold_id)
        return logs_dir / f"{run_id}.log"

    def _get_docker_logs_dir(
        self, iteration: Union[int, str], scaffold_id: str
    ) -> Path:
        """Get logs directory path for Docker mounting.

        Args:
            iteration: Iteration number or "test" for test runs
            scaffold_id: Scaffold identifier

        Returns:
            Absolute path to logs directory
        """
        logs_dir = self.experiment_dir / "logs" / str(iteration) / scaffold_id
        logs_dir.mkdir(parents=True, exist_ok=True)
        return logs_dir.absolute()

    def _get_next_run_id(
        self, iteration: Union[int, str], scaffold_id: str, run_type: str
    ) -> str:
        """Determine the next available run ID for a given run type.

        Args:
            iteration: Iteration number or "test" for test runs
            scaffold_id: Scaffold identifier
            run_type: Type of run (e.g., 'train', 'valid', 'test')

        Returns:
            Next available run ID (e.g., 'train_0', 'train_1', 'valid_0', 'test_0')

        Raises:
            ValueError: If the run type is not 'train', 'valid', or 'test'
        """
        if run_type not in ["train", "valid", "test"]:
            raise ValueError(
                f"Invalid run type: {run_type}. Must be 'train', 'valid', or 'test'."
            )

        counter_key = (iteration, scaffold_id, run_type)

        with self._counter_lock:
            # Get the next ID and increment counter (starts at 0)
            next_index = self._run_id_counters[counter_key]
            self._run_id_counters[counter_key] += 1

        return f"{run_type}_{next_index}"

    def save_scores(
        self, iteration: int, scaffold_id: str, scores: List[float], score_type: str
    ) -> None:
        """Save individual scaffold scores incrementally to scoring files.

        Args:
            iteration: Current iteration number
            scaffold_id: Scaffold identifier
            scores: List of scores for this scaffold
            score_type: Either "train" or "valid"
        """
        if score_type not in ["train", "valid"]:
            raise ValueError(
                f"Invalid score_type: {score_type}. Must be 'train' or 'valid'."
            )

        scoring_dir = self.experiment_dir / "scoring"
        scoring_dir.mkdir(parents=True, exist_ok=True)

        # Update scores_{iteration}.json
        self._update_iteration_scores_file(iteration, scaffold_id, scores, score_type)

        # Update all_valid_scores.json if this is a validation score
        if score_type == "valid":
            self._update_all_valid_scores_file(scaffold_id, scores)

    def _update_json_file_with_scores(
        self,
        file_path: Path,
        scaffold_id: str,
        scores: List[float],
        lock: threading.Lock,
        section_key: Optional[str] = None,
        default_structure: Optional[Dict] = None,
    ) -> None:
        """Helper method to update a JSON file with scaffold scores.

        Args:
            file_path: Path to the JSON file
            scaffold_id: Scaffold identifier
            scores: List of scores for this scaffold
            lock: Threading lock to use
            section_key: Key for nested structure (e.g., "train", "valid"), None for flat structure
            default_structure: Default structure if file doesn't exist
        """
        with lock:
            # Load existing data or create default structure
            if file_path.exists():
                with open(file_path, "r") as f:
                    data = json.load(f)
            else:
                data = default_structure or {}

            # Add/update scaffold scores
            score_entry = {"mean_score": np.mean(scores), "scores": scores}

            if section_key:
                # Nested structure (e.g., scores_{iteration}.json)
                data[section_key][scaffold_id] = score_entry
                # Sort the specific section
                data[section_key] = self._sort_scores_dict(data[section_key])
            else:
                # Flat structure (e.g., all_valid_scores.json)
                data[scaffold_id] = score_entry
                # Sort the entire data
                data = self._sort_scores_dict(data)

            # Write back to file
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2)

    def _update_iteration_scores_file(
        self, iteration: int, scaffold_id: str, scores: List[float], score_type: str
    ) -> None:
        """Update the scores_{iteration}.json file with new scaffold scores."""
        scoring_file = self.experiment_dir / "scoring" / f"scores_{iteration}.json"
        self._update_json_file_with_scores(
            file_path=scoring_file,
            scaffold_id=scaffold_id,
            scores=scores,
            lock=self._scores_lock,
            section_key=score_type,
            default_structure={"train": {}, "valid": {}},
        )

    def _update_all_valid_scores_file(
        self, scaffold_id: str, scores: List[float]
    ) -> None:
        """Update the all_valid_scores.json file with new validation scores."""
        all_valid_file = self.experiment_dir / "scoring" / "all_valid_scores.json"
        self._update_json_file_with_scores(
            file_path=all_valid_file,
            scaffold_id=scaffold_id,
            scores=scores,
            lock=self._all_valid_lock,
            section_key=None,  # Flat structure
            default_structure={},
        )

    def _sort_scores_dict(
        self, scores_dict: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """Sort a scores dictionary by mean_score in descending order (highest to lowest)."""
        sorted_items = sorted(
            scores_dict.items(), key=lambda x: x[1]["mean_score"], reverse=True
        )
        return dict(sorted_items)

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
