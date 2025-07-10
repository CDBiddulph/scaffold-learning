import pytest
import tempfile
import json
import shutil
from pathlib import Path
from scaffold_learning.core.experiment_files import ExperimentFileManager
from scaffold_learning.core.data_structures import ScaffoldResult, ScaffoldMetadata


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
            assert (scaffold_path / "metadata.json").exists()

            # Check content
            assert (scaffold_path / "scaffold.py").read_text() == result.code

            with open(scaffold_path / "metadata.json") as f:
                saved_metadata = json.load(f)
            assert saved_metadata == metadata.to_dict()

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

            train_scores = {
                "0": {"mean_score": 0.8, "scores": [0.9, 0.7]},
                "1": {"mean_score": 0.6, "scores": [0.6, 0.6]},
            }
            valid_scores = {
                "0": {"mean_score": 0.75, "scores": [0.8, 0.7]},
                "1": {"mean_score": 0.65, "scores": [0.7, 0.6]},
            }

            manager.save_scores(
                iteration=1, train_scores=train_scores, valid_scores=valid_scores
            )

            scoring_file = experiment_dir / "scoring" / "scores_1.json"
            assert scoring_file.exists()

            with open(scoring_file) as f:
                saved_scores = json.load(f)

            assert saved_scores["train"] == train_scores
            assert saved_scores["valid"] == valid_scores

    def test_load_scores(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            experiment_dir = Path(temp_dir) / "test_experiment"
            manager = ExperimentFileManager(experiment_dir)

            # Save scores first
            train_scores = {
                "0": {"mean_score": 0.8, "scores": [0.9, 0.7]},
                "1": {"mean_score": 0.6, "scores": [0.6, 0.6]},
            }
            valid_scores = {
                "0": {"mean_score": 0.75, "scores": [0.8, 0.7]},
                "1": {"mean_score": 0.65, "scores": [0.7, 0.6]},
            }
            manager.save_scores(1, train_scores, valid_scores)

            # Load them back
            assert manager.load_scores(iteration=1) == {
                "train": train_scores,
                "valid": valid_scores,
            }

    def test_scaffold_flat_structure(self):
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
                train_scores = {
                    f"scaffold_{iteration}": {"mean_score": 0.5, "scores": [0.5]}
                }
                valid_scores = {
                    f"scaffold_{iteration}": {"mean_score": 0.6, "scores": [0.6]}
                }
                manager.save_scores(iteration, train_scores, valid_scores)

            # Check all scores are in scoring directory
            assert (experiment_dir / "scoring" / "scores_0.json").exists()
            assert (experiment_dir / "scoring" / "scores_1.json").exists()
            assert (experiment_dir / "scoring" / "scores_2.json").exists()

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
