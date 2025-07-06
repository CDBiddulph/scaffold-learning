import json
from scaffold_learning.core.data_structures import (
    DatasetExample,
    ScaffoldMetadata,
    ScaffoldResult,
    ScaffoldExecutionResult,
    ScaffoldRunData,
)


class TestDataStructures:
    def test_dataset_example_creation(self):
        example = DatasetExample(
            id="test_001",
            input="5 across: Large feline (4)",
            scoring_data={"solution": "LION"},
        )
        assert example.id == "test_001"
        assert example.input == "5 across: Large feline (4)"
        assert example.scoring_data == {"solution": "LION"}

    def test_scaffold_metadata_creation(self):
        metadata = ScaffoldMetadata(
            created_at="2024-01-01T12:00:00",
            model="gpt-4",
            parent_scaffold_id="2-0",
            iteration=3,
        )
        assert metadata.created_at == "2024-01-01T12:00:00"
        assert metadata.model == "gpt-4"
        assert metadata.parent_scaffold_id == "2-0"
        assert metadata.iteration == 3

    def test_scaffold_metadata_optional_fields(self):
        metadata = ScaffoldMetadata(
            created_at="2024-01-01T12:00:00",
            model=None,
            parent_scaffold_id=None,
            iteration=0,
        )
        assert metadata.model is None
        assert metadata.parent_scaffold_id is None

    def test_scaffold_metadata_to_dict(self):
        metadata = ScaffoldMetadata(
            created_at="2024-01-01T12:00:00",
            model="gpt-4",
            parent_scaffold_id="2-0",
            iteration=3,
        )
        metadata_dict = metadata.to_dict()
        assert metadata_dict == {
            "created_at": "2024-01-01T12:00:00",
            "model": "gpt-4",
            "parent_scaffold_id": "2-0",
            "iteration": 3,
        }
        # Ensure it's JSON serializable
        json_str = json.dumps(metadata_dict)
        assert isinstance(json_str, str)

    def test_scaffold_metadata_from_dict(self):
        data = {
            "created_at": "2024-01-01T12:00:00",
            "model": "gpt-4",
            "parent_scaffold_id": "2-0",
            "iteration": 3,
        }
        metadata = ScaffoldMetadata.from_dict(data)
        assert metadata.created_at == "2024-01-01T12:00:00"
        assert metadata.model == "gpt-4"
        assert metadata.parent_scaffold_id == "2-0"
        assert metadata.iteration == 3

    def test_scaffold_result_creation(self):
        metadata = ScaffoldMetadata(
            created_at="2024-01-01T12:00:00",
            model=None,
            parent_scaffold_id=None,
            iteration=0,
        )
        result = ScaffoldResult(
            code="def process_input(input_string):\n    return 'processed'",
            metadata=metadata,
        )
        assert result.code == "def process_input(input_string):\n    return 'processed'"
        assert result.metadata == metadata

    def test_scaffold_execution_result_creation(self):
        result = ScaffoldExecutionResult(
            output="LION", stderr="", exit_code=0, execution_time=1.23
        )
        assert result.output == "LION"
        assert result.stderr == ""
        assert result.exit_code == 0
        assert result.execution_time == 1.23

    def test_scaffold_run_data_creation(self):
        example = DatasetExample(
            id="test_001",
            input="5 across: Large feline (4)",
            scoring_data={"solution": "LION"},
        )
        run_data = ScaffoldRunData(
            code="def process_input(input_string):\n    return 'TIGER'",
            execution_log="Processing input...\nReturned: TIGER",
            example=example,
            actual_output="TIGER",
            score=0.0,
        )
        assert run_data.code == "def process_input(input_string):\n    return 'TIGER'"
        assert run_data.execution_log == "Processing input...\nReturned: TIGER"
        assert run_data.example == example
        assert run_data.actual_output == "TIGER"
        assert run_data.score == 0.0

    def test_dataset_example_with_multiple_scoring_fields(self):
        example = DatasetExample(
            id="complex_001",
            input="Test input",
            scoring_data={"solution": "answer", "difficulty": 3, "category": "general"},
        )
        assert example.scoring_data["solution"] == "answer"
        assert example.scoring_data["difficulty"] == 3
        assert example.scoring_data["category"] == "general"
