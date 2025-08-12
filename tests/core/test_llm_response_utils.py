"""Tests for llm_response_utils module."""

import pytest
from scaffold_learning.core.llm_response_utils import (
    extract_python_code,
    extract_json_dict,
)


class TestLLMResponseUtils:
    """Test LLM response parsing utilities."""

    def test_extract_python_code_basic(self):
        """Test extracting basic Python code block."""
        response = """Here's the code:
```python
def hello():
    return "world"
```
That's it!"""

        code = extract_python_code(response)
        assert code == 'def hello():\n    return "world"'

    def test_extract_python_code_no_language_marker(self):
        """Test extracting code block without 'python' language marker."""
        response = """Here's the code:
```
def hello():
    return "world"
```"""

        code = extract_python_code(response)
        assert code == 'def hello():\n    return "world"'

    def test_extract_python_code_multiple_blocks(self):
        """Test extracting from multiple code blocks (takes last one)."""
        response = """First block:
```python
def first():
    return 1
```

Second block:
```python
def second():
    return 2
```"""

        code = extract_python_code(response)
        assert code == "def second():\n    return 2"

    def test_extract_python_code_no_block_raises_error(self):
        """Test that missing code block raises ValueError."""
        response = "Just some text without code blocks"

        with pytest.raises(
            ValueError, match="doesn't contain a valid Python code block"
        ):
            extract_python_code(response)

    def test_extract_json_dict_basic(self):
        """Test extracting basic JSON dictionary."""
        response = """Here's the JSON:
{
  "key1": "value1",
  "key2": "value2"
}"""

        result = extract_json_dict(response)
        assert result == {"key1": "value1", "key2": "value2"}

    def test_extract_json_dict_numbered(self):
        """Test extracting numbered JSON dictionary."""
        response = """The strategies are:
{
  "0": "First strategy",
  "1": "Second strategy",
  "2": "Third strategy"
}"""

        result = extract_json_dict(response)
        assert result == {
            "0": "First strategy",
            "1": "Second strategy",
            "2": "Third strategy",
        }

    def test_extract_json_dict_with_surrounding_text(self):
        """Test extracting JSON with text before and after."""
        response = """Some text before
{"answer": "42", "confidence": "high"}
Some text after"""

        result = extract_json_dict(response)
        assert result == {"answer": "42", "confidence": "high"}

    def test_extract_json_dict_nested(self):
        """Test extracting nested JSON dictionary."""
        response = """{
  "outer": {
    "inner": "value"
  },
  "list": [1, 2, 3]
}"""

        result = extract_json_dict(response)
        assert result == {"outer": {"inner": "value"}, "list": [1, 2, 3]}

    def test_extract_json_dict_no_json_raises_error(self):
        """Test that missing JSON raises ValueError."""
        response = "Just plain text without any JSON"

        with pytest.raises(ValueError, match="No valid JSON dictionary found"):
            extract_json_dict(response)

    def test_extract_json_dict_invalid_json_raises_error(self):
        """Test that malformed JSON raises ValueError."""
        response = '{"key": "value", invalid}'

        with pytest.raises(ValueError, match="Failed to parse JSON dictionary"):
            extract_json_dict(response)

    def test_extract_json_dict_array_raises_error(self):
        """Test that JSON array (not dict) raises ValueError."""
        response = '["item1", "item2", "item3"]'

        with pytest.raises(ValueError, match="No valid JSON dictionary found"):
            extract_json_dict(response)

    def test_extract_json_dict_with_markdown(self):
        """Test extracting JSON from markdown-formatted response."""
        response = """Here's the result:

```json
{
  "status": "success",
  "data": "result"
}
```

That's the JSON output."""

        result = extract_json_dict(response)
        assert result == {"status": "success", "data": "result"}
