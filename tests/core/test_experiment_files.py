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
            assert (experiment_dir / "iterations").exists()

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

    def test_save_scaffold_iteration_0(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            experiment_dir = Path(temp_dir) / "test_experiment"
            manager = ExperimentFileManager(experiment_dir)
            
            metadata = ScaffoldMetadata(
                created_at="2024-01-01T12:00:00",
                model="gpt-4",
                parent_scaffold_id=None,
                iteration=0
            )
            result = ScaffoldResult(
                code="def process_input(s):\n    return s.upper()",
                metadata=metadata
            )
            
            scaffold_path = manager.save_scaffold(
                iteration=0,
                scaffold_id="0",
                result=result
            )
            
            # Check directory structure for iteration 0
            expected_path = experiment_dir / "iterations" / "0" / "scaffolds" / "new" / "0"
            assert scaffold_path == expected_path
            assert scaffold_path.exists()
            
            # Check files exist
            assert (scaffold_path / "scaffold.py").exists()
            assert (scaffold_path / "metadata.json").exists()
            assert (scaffold_path / "llm_executor.py").exists()
            assert (scaffold_path / "llm_interfaces.py").exists()
            
            # Check content
            assert (scaffold_path / "scaffold.py").read_text() == result.code
            
            with open(scaffold_path / "metadata.json") as f:
                saved_metadata = json.load(f)
            assert saved_metadata == metadata.to_dict()

    def test_save_scaffold_iteration_1_new(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            experiment_dir = Path(temp_dir) / "test_experiment"
            manager = ExperimentFileManager(experiment_dir)
            
            metadata = ScaffoldMetadata(
                created_at="2024-01-01T12:00:00",
                model="gpt-4",
                parent_scaffold_id="0",
                iteration=1
            )
            result = ScaffoldResult(
                code="def process_input(s):\n    return s.lower()",
                metadata=metadata
            )
            
            scaffold_path = manager.save_scaffold(
                iteration=1,
                scaffold_id="0-0",
                result=result
            )
            
            # Check directory structure for iteration 1+
            expected_path = experiment_dir / "iterations" / "1" / "scaffolds" / "new" / "0-0"
            assert scaffold_path == expected_path
            assert scaffold_path.exists()

    def test_load_scaffold(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            experiment_dir = Path(temp_dir) / "test_experiment"
            manager = ExperimentFileManager(experiment_dir)
            
            # First save a scaffold
            metadata = ScaffoldMetadata(
                created_at="2024-01-01T12:00:00",
                model="gpt-4",
                parent_scaffold_id=None,
                iteration=0
            )
            original_result = ScaffoldResult(
                code="def process_input(s):\n    return s.upper()",
                metadata=metadata
            )
            
            manager.save_scaffold(
                iteration=0,
                scaffold_id="0",
                result=original_result
            )
            
            # Now load it back
            loaded_result = manager.load_scaffold(iteration=0, scaffold_id="0")
            
            assert loaded_result.code == original_result.code
            assert loaded_result.metadata.created_at == metadata.created_at
            assert loaded_result.metadata.model == metadata.model
            assert loaded_result.metadata.parent_scaffold_id == metadata.parent_scaffold_id
            assert loaded_result.metadata.iteration == metadata.iteration

    def test_get_scaffold_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            experiment_dir = Path(temp_dir) / "test_experiment"
            manager = ExperimentFileManager(experiment_dir)
            
            # Test iteration 0
            path_0 = manager.get_scaffold_path(iteration=0, scaffold_id="0")
            expected_0 = experiment_dir / "iterations" / "0" / "scaffolds" / "new" / "0"
            assert path_0 == expected_0
            
            # Test iteration 1+
            path_1 = manager.get_scaffold_path(iteration=1, scaffold_id="0-0")
            expected_1 = experiment_dir / "iterations" / "1" / "scaffolds" / "new" / "0-0"
            assert path_1 == expected_1

    def test_copy_scaffold(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            experiment_dir = Path(temp_dir) / "test_experiment"
            manager = ExperimentFileManager(experiment_dir)
            
            # Create source scaffold
            source_dir = experiment_dir / "iterations" / "0" / "scaffolds" / "new" / "0"
            source_dir.mkdir(parents=True)
            (source_dir / "scaffold.py").write_text("def process_input(s): return s")
            (source_dir / "metadata.json").write_text('{"test": "data"}')
            
            # Copy to new location
            target_path = manager.copy_scaffold(
                from_path=source_dir,
                to_iteration=1,
                to_scaffold_id="0"
            )
            
            expected_target = experiment_dir / "iterations" / "1" / "scaffolds" / "old" / "0"
            assert target_path == expected_target
            assert target_path.exists()
            assert (target_path / "scaffold.py").exists()
            assert (target_path / "metadata.json").exists()
            
            # Check content was copied
            assert (target_path / "scaffold.py").read_text() == "def process_input(s): return s"
            assert (target_path / "metadata.json").read_text() == '{"test": "data"}'

    def test_save_scores(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            experiment_dir = Path(temp_dir) / "test_experiment"
            manager = ExperimentFileManager(experiment_dir)
            
            train_scores = {"0": 0.8, "1": 0.6}
            valid_scores = {"0": 0.75, "1": 0.65}
            
            manager.save_scores(
                iteration=1,
                train_scores=train_scores,
                valid_scores=valid_scores
            )
            
            scoring_file = experiment_dir / "iterations" / "1" / "scoring.json"
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
            train_scores = {"0": 0.8, "1": 0.6}
            valid_scores = {"0": 0.75, "1": 0.65}
            manager.save_scores(1, train_scores, valid_scores)
            
            # Load them back
            loaded_train, loaded_valid = manager.load_scores(iteration=1)
            
            assert loaded_train == train_scores
            assert loaded_valid == valid_scores

    def test_get_logs_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            experiment_dir = Path(temp_dir) / "test_experiment"
            manager = ExperimentFileManager(experiment_dir)
            
            train_path = manager.get_logs_path(
                iteration=1,
                scaffold_id="0-0",
                run_type="train"
            )
            
            expected_train = experiment_dir / "iterations" / "1" / "logs" / "0-0" / "train.log"
            assert train_path == expected_train
            
            valid_path = manager.get_logs_path(
                iteration=1,
                scaffold_id="0-0",
                run_type="valid"
            )
            
            expected_valid = experiment_dir / "iterations" / "1" / "logs" / "0-0" / "valid.log"
            assert valid_path == expected_valid

    def test_load_nonexistent_scaffold_raises_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            experiment_dir = Path(temp_dir) / "test_experiment"
            manager = ExperimentFileManager(experiment_dir)
            
            with pytest.raises(FileNotFoundError):
                manager.load_scaffold(iteration=0, scaffold_id="nonexistent")

    def test_load_nonexistent_scores_raises_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            experiment_dir = Path(temp_dir) / "test_experiment"
            manager = ExperimentFileManager(experiment_dir)
            
            with pytest.raises(FileNotFoundError):
                manager.load_scores(iteration=999)

    def test_copy_preserves_all_support_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            experiment_dir = Path(temp_dir) / "test_experiment"
            manager = ExperimentFileManager(experiment_dir)
            
            # Create a complete scaffold with all support files
            source_dir = experiment_dir / "iterations" / "0" / "scaffolds" / "new" / "0"
            source_dir.mkdir(parents=True)
            (source_dir / "scaffold.py").write_text("code")
            (source_dir / "metadata.json").write_text("{}")
            (source_dir / "llm_executor.py").write_text("executor")
            (source_dir / "llm_interfaces.py").write_text("interfaces")
            
            # Copy scaffold
            target_path = manager.copy_scaffold(
                from_path=source_dir,
                to_iteration=1,
                to_scaffold_id="0"
            )
            
            # Verify all files were copied
            assert (target_path / "scaffold.py").read_text() == "code"
            assert (target_path / "metadata.json").read_text() == "{}"
            assert (target_path / "llm_executor.py").read_text() == "executor"
            assert (target_path / "llm_interfaces.py").read_text() == "interfaces"