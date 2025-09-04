import pytest
import tempfile
from unittest.mock import Mock, patch
from pathlib import Path
from scaffold_learning.core.scaffold_creation import ScaffoldGenerator
from scaffold_learning.core.data_structures import (
    DatasetExample,
    ScaffoldRunData,
    LLMResponse,
)
from scaffold_learning.core.llm_interfaces import LLMInterface
from scaffold_learning.core.experiment_files import ExperimentFileManager
from scaffold_learning.core.dataset_utils import ExampleSampler
from scaffold_learning.core.hydra_config import ExperimentConfig


class TestScaffoldGenerator:
    @pytest.fixture(autouse=True)
    def setup_temp_dir(self):
        """Automatically provide a temporary directory for each test."""
        with tempfile.TemporaryDirectory() as temp_dir:
            self.temp_dir = Path(temp_dir)
            yield

    @pytest.fixture
    def mock_config(self):
        """Create a mock experiment config."""
        return ExperimentConfig(
            experiment_name="test_experiment",
            data_dir="/fake/data",
            domain="test_domain",
            domain_params={},
            num_iterations=2,
            scaffolds_per_iter=2,
            initial_scaffolds=3,
            num_validation_examples=2,
            num_training_examples=1,
            scaffolder="test_scaffolder",
            executor="gpt-4",
            strategy=None,
            strategy_batch_size=None,
            show_scoring_function=False,
            suggest_hack="none",
            train_seed=42,
            valid_seed=42,
            test_seed=42,
            num_test_examples=0,
            scaffold_timeout=120,
            max_generate_workers=1,
            max_execute_workers=1,
            base_dir="/fake/base",
            build_docker=False,
            executor_reasoning_effort="minimal",
            scaffolder_reasoning_effort="minimal",
        )

    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM interface."""
        llm = Mock(spec=LLMInterface)
        llm.get_model_info.return_value = "mock_model"
        # Mock generate_response to return a proper LLMResponse with code
        mock_response = LLMResponse(
            content="```python\ndef process_input(s): return 'test'\n```"
        )
        llm.generate_response.return_value = mock_response
        return llm

    @pytest.fixture
    def mock_file_manager(self):
        """Create a mock file manager."""
        file_manager = Mock(spec=ExperimentFileManager)
        file_manager.experiment_dir = self.temp_dir
        return file_manager

    @pytest.fixture
    def mock_train_sampler(self):
        """Create a mock training sampler."""
        sampler = Mock(spec=ExampleSampler)
        sampler.sample.return_value = [
            DatasetExample(
                id="train_1",
                input="Test input",
                scoring_data={"input": "Test input", "solution": "test"},
            )
        ]
        return sampler

    @pytest.fixture
    def scaffold_generator(
        self, mock_config, mock_llm, mock_file_manager, mock_train_sampler
    ):
        """Create a ScaffoldGenerator instance for testing."""
        return ScaffoldGenerator(
            config=mock_config,
            scaffolder_llm=mock_llm,
            strategy_llm=None,
            file_manager=mock_file_manager,
            train_sampler=mock_train_sampler,
            scoring_fn_code="def score(a, b): return 1.0",
        )

    def test_scaffold_generator_init(self, scaffold_generator):
        """Test that ScaffoldGenerator initializes correctly."""
        assert scaffold_generator.config is not None
        assert scaffold_generator.scaffolder_llm is not None
        assert scaffold_generator.file_manager is not None
        assert scaffold_generator.train_sampler is not None
        assert scaffold_generator.scoring_fn_code == "def score(a, b): return 1.0"
        assert scaffold_generator.is_baseline == False
        assert scaffold_generator.initial_scaffolds > 0

    def test_create_initial_scaffolds(self, scaffold_generator):
        """Test that create_initial_scaffolds returns scaffold IDs."""
        # Mock the scaffold generation calls
        with patch(
            "scaffold_learning.core.scaffold_code_generation.generate_scaffold"
        ) as mock_generate:
            # Create a proper mock scaffold result
            mock_result = Mock()
            mock_result.code = "def process_input(s): return 'test'"
            mock_result.metadata = Mock()
            mock_generate.return_value = mock_result

            scaffold_ids = scaffold_generator.create_initial_scaffolds()

            assert isinstance(scaffold_ids, list)
            assert len(scaffold_ids) == scaffold_generator.initial_scaffolds
            assert all(isinstance(id, str) for id in scaffold_ids)

    def test_evolve_scaffolds(self, scaffold_generator):
        """Test that evolve_scaffolds returns new scaffold IDs."""
        # Create a proper ScaffoldRunData object
        example = DatasetExample(
            id="train_1",
            input="Test input",
            scoring_data={"input": "Test input", "solution": "test"},
        )

        run_data = ScaffoldRunData(
            code="def process_input(s): return 'test'",
            execution_log="Mock execution log",
            example=example,
            actual_output="test",
            score=1.0,
        )

        parent_runs = {"0": [run_data]}

        # Mock the scaffold evolution calls
        with patch(
            "scaffold_learning.core.scaffold_code_generation.evolve_scaffold"
        ) as mock_evolve:
            # Create a proper mock scaffold result
            mock_result = Mock()
            mock_result.code = "def process_input(s): return 'evolved'"
            mock_result.metadata = Mock()
            mock_evolve.return_value = mock_result

            new_scaffold_ids = scaffold_generator.evolve_scaffolds(1, parent_runs)

            assert isinstance(new_scaffold_ids, list)
            assert len(new_scaffold_ids) == len(parent_runs)
            assert all(isinstance(id, str) for id in new_scaffold_ids)
            # Should have format "parent_id-counter"
            assert all("-" in id for id in new_scaffold_ids)

    def test_init_with_strategy_llm(
        self, mock_config, mock_llm, mock_file_manager, mock_train_sampler
    ):
        """Test initialization with strategy LLM."""
        strategy_llm = Mock(spec=LLMInterface)
        strategy_llm.get_model_info.return_value = "strategy_model"

        generator = ScaffoldGenerator(
            config=mock_config,
            scaffolder_llm=mock_llm,
            strategy_llm=strategy_llm,
            file_manager=mock_file_manager,
            train_sampler=mock_train_sampler,
            scoring_fn_code="def score(a, b): return 1.0",
        )

        assert generator.strategy_llm == strategy_llm

    def test_init_baseline_mode(self, mock_file_manager, mock_train_sampler):
        """Test initialization in baseline mode."""
        # Create config with baseline scaffolder
        baseline_config = ExperimentConfig(
            experiment_name="baseline_test",
            data_dir="/fake/data",
            domain="test_domain",
            domain_params={},
            num_iterations=1,
            scaffolds_per_iter=1,
            initial_scaffolds=1,
            num_validation_examples=1,
            num_training_examples=1,
            scaffolder="baseline",  # This triggers baseline mode
            executor="gpt-4",
            strategy=None,
            strategy_batch_size=None,
            show_scoring_function=False,
            suggest_hack="none",
            train_seed=42,
            valid_seed=42,
            test_seed=42,
            num_test_examples=0,
            scaffold_timeout=120,
            max_generate_workers=1,
            max_execute_workers=1,
            base_dir="/fake/base",
            build_docker=False,
            executor_reasoning_effort="minimal",
            scaffolder_reasoning_effort="minimal",
        )

        generator = ScaffoldGenerator(
            config=baseline_config,
            scaffolder_llm=None,  # None for baseline mode
            strategy_llm=None,
            file_manager=mock_file_manager,
            train_sampler=mock_train_sampler,
            scoring_fn_code=None,
        )

        assert generator.is_baseline == True
        assert generator.initial_scaffolds == 1

    def test_init_without_scoring_fn_code(
        self, mock_config, mock_llm, mock_file_manager, mock_train_sampler
    ):
        """Test initialization without scoring function code."""
        generator = ScaffoldGenerator(
            config=mock_config,
            scaffolder_llm=mock_llm,
            strategy_llm=None,
            file_manager=mock_file_manager,
            train_sampler=mock_train_sampler,
            # scoring_fn_code defaults to None
        )

        assert generator.scoring_fn_code is None
