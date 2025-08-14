import pytest
import tempfile
import json
import shutil
from pathlib import Path
from scaffold_learning.core.experiment_files import ExperimentFileManager
from scaffold_learning.core.data_structures import ScaffoldResult, ScaffoldMetadata


def _all_floats_are_close(a, b):
    "Check that all floats in a and b are close and that other types are equal"
    if isinstance(a, list) and isinstance(b, list):
        return all(_all_floats_are_close(a_i, b_i) for a_i, b_i in zip(a, b))
    elif isinstance(a, dict) and isinstance(b, dict):
        return all(
            _all_floats_are_close(k1, k2) and _all_floats_are_close(a[k1], b[k2])
            for k1, k2 in zip(sorted(a.keys()), sorted(b.keys()))
        )
    elif isinstance(a, float) and isinstance(b, float):
        return abs(a - b) < 1e-6
    # If no floats are involved, check for equality
    return a == b


class TestExperimentFileManager:
    def test_init_creates_directory_structure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            experiment_dir = Path(temp_dir) / "test_experiment"
            manager = ExperimentFileManager(experiment_dir)

            assert experiment_dir.exists()
            assert (experiment_dir / "scaffolds").exists()
            assert (experiment_dir / "logs").exists()
            assert (experiment_dir / "scoring").exists()

    def test_save_experiment_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            experiment_dir = Path(temp_dir) / "test_experiment"
            manager = ExperimentFileManager(experiment_dir)

            metadata = {"random_seed": 42, "created_at": "2024-01-01"}
            manager.save_experiment_metadata(metadata)

            metadata_file = experiment_dir / "metadata.json"
            assert metadata_file.exists()

            with open(metadata_file) as f:
                saved_data = json.load(f)
            assert saved_data == metadata

    def test_save_scaffold(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            experiment_dir = Path(temp_dir) / "test_experiment"
            manager = ExperimentFileManager(experiment_dir)

            metadata = ScaffoldMetadata(
                created_at="2024-01-01T12:00:00",
                parent_scaffold_id=None,
                iteration=0,
            )
            result = ScaffoldResult(
                code="def process_input(s):\n    return s.upper()", metadata=metadata
            )

            manager.save_scaffold(scaffold_id="0", result=result)

            # Check directory structure - flat structure
            scaffold_path = experiment_dir / "scaffolds" / "0"
            assert scaffold_path.exists()

            # Check files exist
            assert (scaffold_path / "scaffold.py").exists()
            assert (scaffold_path / "metadata.xml").exists()

            # Check content
            assert (scaffold_path / "scaffold.py").read_text() == result.code

            from scaffold_learning.core.xml_utils import xml_to_dict

            xml_content = (scaffold_path / "metadata.xml").read_text()
            saved_metadata = xml_to_dict(xml_content)

            # XML converts numbers to strings and omits None values
            expected_metadata = {
                "created_at": "2024-01-01T12:00:00",
                "iteration": "0",  # XML converts to string
                # parent_scaffold_id is None, so omitted from XML
                # scaffolder_prompt is None, so omitted from XML
                # scaffolder_response is None, so omitted from XML
            }
            assert saved_metadata == expected_metadata

    def test_save_evolved_scaffold(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            experiment_dir = Path(temp_dir) / "test_experiment"
            manager = ExperimentFileManager(experiment_dir)

            metadata = ScaffoldMetadata(
                created_at="2024-01-01T12:00:00",
                parent_scaffold_id="0",
                iteration=1,
            )
            result = ScaffoldResult(
                code="def process_input(s):\n    return s.lower()", metadata=metadata
            )

            manager.save_scaffold(scaffold_id="0-0", result=result)

            # Check directory structure - still flat
            scaffold_path = experiment_dir / "scaffolds" / "0-0"
            assert scaffold_path.exists()

    def test_load_scaffold(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            experiment_dir = Path(temp_dir) / "test_experiment"
            manager = ExperimentFileManager(experiment_dir)

            # First save a scaffold
            metadata = ScaffoldMetadata(
                created_at="2024-01-01T12:00:00",
                parent_scaffold_id=None,
                iteration=0,
            )
            original_result = ScaffoldResult(
                code="def process_input(s):\n    return s.upper()", metadata=metadata
            )

            manager.save_scaffold(scaffold_id="0", result=original_result)

            # Now load it back
            loaded_result = manager.load_scaffold(scaffold_id="0")

            assert loaded_result.code == original_result.code
            assert loaded_result.metadata.created_at == metadata.created_at
            assert (
                loaded_result.metadata.parent_scaffold_id == metadata.parent_scaffold_id
            )
            assert loaded_result.metadata.iteration == metadata.iteration

    def test_get_docker_scaffold_dir(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            experiment_dir = Path(temp_dir) / "test_experiment"
            manager = ExperimentFileManager(experiment_dir)

            # Create a scaffold first
            metadata = ScaffoldMetadata(
                created_at="2024-01-01T12:00:00",
                parent_scaffold_id=None,
                iteration=0,
            )
            result = ScaffoldResult(
                code="def process_input(s): return s", metadata=metadata
            )
            manager.save_scaffold(scaffold_id="0", result=result)

            # Test getting Docker path
            docker_path = manager.get_scaffold_dir("0")
            expected = experiment_dir / "scaffolds" / "0"
            assert docker_path == expected.absolute()
            assert docker_path.exists()

            # Test nonexistent scaffold
            with pytest.raises(FileNotFoundError):
                manager.get_scaffold_dir("nonexistent")

    def test_get_docker_logs_dir(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            experiment_dir = Path(temp_dir) / "test_experiment"
            manager = ExperimentFileManager(experiment_dir)

            # Test getting Docker logs path
            logs_dir = manager._get_docker_logs_dir(iteration=1, scaffold_id="0-0")
            expected = experiment_dir / "logs" / "1" / "0-0"
            assert logs_dir == expected.absolute()

            # Directory should be created
            assert logs_dir.exists()

    def test_save_scores(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            experiment_dir = Path(temp_dir) / "test_experiment"
            manager = ExperimentFileManager(experiment_dir)

            # Use 3 scaffolds with different orderings for train vs valid to prove sorting by mean score
            # Train order by mean: "2" (0.95) > "1" (0.9) > "0" (0.8)
            # Valid order by mean: "0" (0.85) > "1" (0.8) > "2" (0.7)
            train_scores = {
                "0": [0.9, 0.7],  # mean = 0.8
                "1": [0.9, 0.9],  # mean = 0.9
                "2": [1.0, 0.9],  # mean = 0.95
            }
            valid_scores = {
                "0": [0.8, 0.9],  # mean = 0.85
                "1": [0.8, 0.8],  # mean = 0.8
                "2": [0.7, 0.7],  # mean = 0.7
            }

            manager.save_scores(
                iteration=1, train_scores=train_scores, valid_scores=valid_scores
            )

            scoring_file = experiment_dir / "scoring" / "scores_1.json"
            assert scoring_file.exists()

            with open(scoring_file) as f:
                saved_scores = json.load(f)

            # This only tests the score values, not the order
            assert _all_floats_are_close(
                saved_scores,
                {
                    "train": {
                        "2": {"mean_score": 0.95, "scores": [1.0, 0.9]},
                        "1": {"mean_score": 0.9, "scores": [0.9, 0.9]},
                        "0": {"mean_score": 0.8, "scores": [0.9, 0.7]},
                    },
                    "valid": {
                        "0": {"mean_score": 0.85, "scores": [0.8, 0.9]},
                        "1": {"mean_score": 0.8, "scores": [0.8, 0.8]},
                        "2": {"mean_score": 0.7, "scores": [0.7, 0.7]},
                    },
                },
            )

            # Verify the order by checking keys - different orderings prove it's sorting by mean score
            train_keys = list(saved_scores["train"].keys())
            valid_keys = list(saved_scores["valid"].keys())
            assert train_keys == ["2", "1", "0"]  # Train: 2 > 1 > 0 by mean score
            assert valid_keys == ["0", "1", "2"]  # Valid: 0 > 1 > 2 by mean score

    def test_load_scores(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            experiment_dir = Path(temp_dir) / "test_experiment"
            manager = ExperimentFileManager(experiment_dir)

            # Save scores first
            train_scores = {
                "0": [0.9, 0.7],
                "1": [0.6, 0.6],
            }
            valid_scores = {
                "0": [0.8, 0.7],
                "1": [0.7, 0.6],
            }
            manager.save_scores(1, train_scores, valid_scores)

            # Load them back
            assert _all_floats_are_close(
                manager.load_scores(iteration=1),
                {
                    "train": {
                        "0": {"mean_score": 0.8, "scores": [0.9, 0.7]},
                        "1": {"mean_score": 0.6, "scores": [0.6, 0.6]},
                    },
                    "valid": {
                        "0": {"mean_score": 0.75, "scores": [0.8, 0.7]},
                        "1": {"mean_score": 0.65, "scores": [0.7, 0.6]},
                    },
                },
            )

    def test_fold_flat_structure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            experiment_dir = Path(temp_dir) / "test_experiment"
            manager = ExperimentFileManager(experiment_dir)

            # Save multiple scaffolds across iterations
            for scaffold_id, iteration in [("0", 0), ("1", 0), ("0-0", 1), ("1-0", 1)]:
                metadata = ScaffoldMetadata(
                    created_at="2024-01-01T12:00:00",
                    parent_scaffold_id=(
                        scaffold_id.split("-")[0] if "-" in scaffold_id else None
                    ),
                    iteration=iteration,
                )
                result = ScaffoldResult(code="code", metadata=metadata)
                manager.save_scaffold(scaffold_id=scaffold_id, result=result)

            # All scaffolds should be in flat structure
            assert (experiment_dir / "scaffolds" / "0").exists()
            assert (experiment_dir / "scaffolds" / "1").exists()
            assert (experiment_dir / "scaffolds" / "0-0").exists()
            assert (experiment_dir / "scaffolds" / "1-0").exists()

            # No iteration-based directories
            assert not (experiment_dir / "iterations").exists()

    def test_load_nonexistent_scaffold_raises_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            experiment_dir = Path(temp_dir) / "test_experiment"
            manager = ExperimentFileManager(experiment_dir)

            with pytest.raises(FileNotFoundError):
                manager.load_scaffold(scaffold_id="nonexistent")

    def test_load_nonexistent_scores_raises_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            experiment_dir = Path(temp_dir) / "test_experiment"
            manager = ExperimentFileManager(experiment_dir)

            with pytest.raises(FileNotFoundError):
                manager.load_scores(iteration=999)

    def test_scoring_new_location(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            experiment_dir = Path(temp_dir) / "test_experiment"
            manager = ExperimentFileManager(experiment_dir)

            # Save scores for multiple iterations
            for iteration in [0, 1, 2]:
                train_scores = {f"scaffold_{iteration}": [0.5]}
                valid_scores = {f"scaffold_{iteration}": [0.6]}
                manager.save_scores(iteration, train_scores, valid_scores)

            # Check all scores are in scoring directory
            assert (experiment_dir / "scoring" / "scores_0.json").exists()
            assert (experiment_dir / "scoring" / "scores_1.json").exists()
            assert (experiment_dir / "scoring" / "scores_2.json").exists()

    def test_get_most_recent_validation_scores(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            experiment_dir = Path(temp_dir)
            manager = ExperimentFileManager(experiment_dir)

            # Create scaffolds first
            scaffold_ids = ["0", "1", "2"]
            for scaffold_id in scaffold_ids:
                metadata = ScaffoldMetadata(
                    created_at="2024-01-01T12:00:00",
                    parent_scaffold_id=None,
                    iteration=0,
                )
                result = ScaffoldResult(code="code", metadata=metadata)
                manager.save_scaffold(scaffold_id=scaffold_id, result=result)

            # Save scores for multiple iterations
            # Iteration 0: only scaffold_0 and scaffold_1 have scores
            train_scores_0 = {"0": [0.4, 0.6], "1": [0.7]}
            valid_scores_0 = {"0": [0.5, 0.7], "1": [0.8]}
            manager.save_scores(0, train_scores_0, valid_scores_0)

            # Iteration 1: scaffold_0 gets new score, scaffold_2 gets first score
            train_scores_1 = {"0": [0.9, 0.9], "2": [0.2, 0.4]}
            valid_scores_1 = {"0": [0.9, 1.0], "2": [0.3, 0.4]}
            manager.save_scores(1, train_scores_1, valid_scores_1)

            # Get most recent validation scores
            recent_scores = manager.get_most_recent_validation_scores()

            # Check that we get the expected structure
            assert _all_floats_are_close(
                recent_scores,
                {
                    "0": {"mean_score": 0.95, "scores": [0.9, 1.0]},
                    "1": {"mean_score": 0.8, "scores": [0.8]},
                    "2": {"mean_score": 0.35, "scores": [0.3, 0.4]},
                },
            )

    def test_get_most_recent_validation_scores_no_scores(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ExperimentFileManager(Path(temp_dir))
            empty_scores = manager.get_most_recent_validation_scores()
            assert empty_scores == {}

    def test_get_most_recent_validation_scores_no_scoring_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ExperimentFileManager(Path(temp_dir))
            # Save the scaffold, but not the scores
            metadata = ScaffoldMetadata(
                created_at="2024-01-01T12:00:00", parent_scaffold_id=None, iteration=0
            )
            result = ScaffoldResult(code="code", metadata=metadata)
            manager.save_scaffold(scaffold_id="test", result=result)

            assert manager.get_most_recent_validation_scores() == {"test": None}

    def test_logs_directory_structure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            experiment_dir = Path(temp_dir) / "test_experiment"
            manager = ExperimentFileManager(experiment_dir)

            # Get logs directories for different iterations and scaffolds
            logs_dir_1 = manager._get_docker_logs_dir(iteration=0, scaffold_id="0")
            logs_dir_2 = manager._get_docker_logs_dir(iteration=0, scaffold_id="1")
            logs_dir_3 = manager._get_docker_logs_dir(iteration=1, scaffold_id="0-0")

            # Check structure: logs/<iteration>/<scaffold_id>/
            assert logs_dir_1 == (experiment_dir / "logs" / "0" / "0").absolute()
            assert logs_dir_2 == (experiment_dir / "logs" / "0" / "1").absolute()
            assert logs_dir_3 == (experiment_dir / "logs" / "1" / "0-0").absolute()

            # All directories should be created
            assert logs_dir_1.exists()
            assert logs_dir_2.exists()
            assert logs_dir_3.exists()

    @pytest.mark.parametrize("run_type", ["train", "valid"])
    def test_save_execution_log_valid_run_types(self, run_type):
        with tempfile.TemporaryDirectory() as temp_dir:
            experiment_dir = Path(temp_dir) / "test_experiment"
            manager = ExperimentFileManager(experiment_dir)

            # Valid run types should work
            log_path = manager.get_new_execution_log_path(
                iteration=0, scaffold_id="0", run_type=run_type
            )
            expected_path = experiment_dir / "logs" / "0" / "0" / f"{run_type}_0.log"
            assert log_path == expected_path

    @pytest.mark.parametrize(
        "invalid_run_type", ["train_0", "valid_1", "test", "training", "validation", ""]
    )
    def test_save_execution_log_invalid_run_types(self, invalid_run_type):
        with tempfile.TemporaryDirectory() as temp_dir:
            experiment_dir = Path(temp_dir) / "test_experiment"
            manager = ExperimentFileManager(experiment_dir)

            # Invalid run types should fail
            with pytest.raises(ValueError, match="Invalid run type"):
                manager.get_new_execution_log_path(
                    iteration=0,
                    scaffold_id="0",
                    run_type=invalid_run_type,
                )
