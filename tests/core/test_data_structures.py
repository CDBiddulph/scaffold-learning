import pytest
from scaffold_learning.core.data_structures import (
    DatasetExample,
    LLMResponse,
    ScaffoldMetadata,
)


class TestLLMResponse:
    def test_from_dict_basic(self):
        """Test LLMResponse.from_dict with basic data."""
        data = {"content": "Hello world", "thinking": "I'll say hello"}
        response = LLMResponse.from_dict(data)

        assert response.content == "Hello world"
        assert response.thinking == "I'll say hello"

    def test_from_dict_missing_thinking(self):
        """Test LLMResponse.from_dict with missing thinking field."""
        data = {"content": "Hello world"}
        response = LLMResponse.from_dict(data)

        assert response.content == "Hello world"
        assert response.thinking is None


class TestScaffoldMetadata:
    def test_from_dict_basic(self):
        """Test ScaffoldMetadata.from_dict with basic data."""
        data = {
            "created_at": "2024-01-01T00:00:00",
            "parent_scaffold_id": "parent-123",
            "iteration": 5,
        }
        metadata = ScaffoldMetadata.from_dict(data)

        assert metadata.created_at == "2024-01-01T00:00:00"
        assert metadata.parent_scaffold_id == "parent-123"
        assert metadata.iteration == 5
        assert metadata.scaffolder_prompt is None
        assert metadata.scaffolder_response is None

    def test_from_dict_missing_optional_fields(self):
        """Test ScaffoldMetadata.from_dict sets None for missing fields."""
        data = {"created_at": "2024-01-01T00:00:00"}
        metadata = ScaffoldMetadata.from_dict(data)

        assert metadata.created_at == "2024-01-01T00:00:00"
        assert metadata.parent_scaffold_id is None
        assert metadata.iteration is None

    def test_from_dict_converts_iteration_from_string(self):
        """Test ScaffoldMetadata.from_dict converts iteration from string to int."""
        data = {
            "created_at": "2024-01-01T00:00:00",
            "iteration": "42",  # String that should be converted
        }
        metadata = ScaffoldMetadata.from_dict(data)

        assert metadata.iteration == 42
        assert isinstance(metadata.iteration, int)

    def test_from_dict_converts_llm_response_from_dict(self):
        """Test ScaffoldMetadata.from_dict converts scaffolder_response dict to LLMResponse."""
        data = {
            "created_at": "2024-01-01T00:00:00",
            "scaffolder_response": {
                "content": "Generated scaffold code",
                "thinking": "I need to solve this problem",
            },
        }
        metadata = ScaffoldMetadata.from_dict(data)

        assert isinstance(metadata.scaffolder_response, LLMResponse)
        assert metadata.scaffolder_response.content == "Generated scaffold code"
        assert metadata.scaffolder_response.thinking == "I need to solve this problem"

    def test_from_dict_preserves_existing_llm_response_object(self):
        """Test ScaffoldMetadata.from_dict preserves existing LLMResponse objects."""
        llm_response = LLMResponse(content="Test content", thinking="Test thinking")
        data = {
            "created_at": "2024-01-01T00:00:00",
            "scaffolder_response": llm_response,
        }
        metadata = ScaffoldMetadata.from_dict(data)

        assert metadata.scaffolder_response is llm_response
        assert metadata.scaffolder_response is not None
        assert metadata.scaffolder_response.content == "Test content"
        assert metadata.scaffolder_response.thinking == "Test thinking"

    def test_from_dict_with_all_fields(self):
        """Test ScaffoldMetadata.from_dict with all fields present."""
        data = {
            "created_at": "2024-01-01T00:00:00",
            "parent_scaffold_id": "parent-456",
            "iteration": "10",
            "scaffolder_prompt": "Generate a crossword solver",
            "scaffolder_response": {
                "content": "def solve_crossword(): pass",
                "thinking": "I'll create a simple solver",
            },
        }
        metadata = ScaffoldMetadata.from_dict(data)

        assert metadata.created_at == "2024-01-01T00:00:00"
        assert metadata.parent_scaffold_id == "parent-456"
        assert metadata.iteration == 10
        assert metadata.scaffolder_prompt == "Generate a crossword solver"
        assert isinstance(metadata.scaffolder_response, LLMResponse)
        assert metadata.scaffolder_response.content == "def solve_crossword(): pass"
        assert metadata.scaffolder_response.thinking == "I'll create a simple solver"

    def test_roundtrip_serialization(self):
        """Test that to_dict and from_dict are inverse operations."""
        original = ScaffoldMetadata(
            created_at="2024-01-01T00:00:00",
            parent_scaffold_id="test-parent",
            iteration=3,
            scaffolder_prompt="Test prompt",
            scaffolder_response=LLMResponse(
                content="Test response", thinking="Test thinking"
            ),
        )
        assert original.scaffolder_response is not None  # Avoids linter error

        # Convert to dict and back
        as_dict = original.to_dict()
        reconstructed = ScaffoldMetadata.from_dict(as_dict)

        assert reconstructed.created_at == original.created_at
        assert reconstructed.parent_scaffold_id == original.parent_scaffold_id
        assert reconstructed.iteration == original.iteration
        assert reconstructed.scaffolder_prompt == original.scaffolder_prompt
        assert isinstance(reconstructed.scaffolder_response, LLMResponse)
        assert (
            reconstructed.scaffolder_response.content
            == original.scaffolder_response.content
        )
        assert (
            reconstructed.scaffolder_response.thinking
            == original.scaffolder_response.thinking
        )
