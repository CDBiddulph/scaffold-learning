from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, List


@dataclass
class DatasetExample:
    """Represents a single example from a dataset.

    Attributes:
        id: Unique identifier for this example
        input: Input string to be processed
        scoring_data: Additional data needed for scoring (e.g., 'solution' for crosswords)
    """

    id: str
    input: str
    scoring_data: Dict[str, Any]


@dataclass
class LLMResponse:
    """Contains a response from an LLM.

    Attributes:
        content: The content output from the LLM
        thinking: The thinking output from the LLM
    """

    content: str
    thinking: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LLMResponse":
        """Create response from dictionary."""
        return cls(**data)


@dataclass
class ScaffoldMetadata:
    """Metadata for a generated scaffold.

    Attributes:
        created_at: Timestamp of creation
        parent_scaffold_id: ID of scaffold this was derived from (if applicable)
        iteration: Iteration number when created
        scaffolder_prompt: Prompt that was sent to the scaffolder LLM
        scaffolder_response: Full response from the scaffolder LLM
        executor_prompt: Prompt to be sent to the executor LLM (for prompt-only scaffolds)
    """

    created_at: str
    parent_scaffold_id: Optional[str]
    iteration: Optional[int]
    scaffolder_prompt: Optional[str] = None
    scaffolder_response: Optional[LLMResponse] = None
    executor_prompt: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary for JSON serialization.

        Returns:
            Dictionary representation of metadata
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScaffoldMetadata":
        """Create metadata from dictionary.

        Args:
            data: Dictionary containing metadata fields

        Returns:
            ScaffoldMetadata instance
        """
        # Handle missing fields and type conversions from XML
        processed_data = data.copy()

        # Convert iteration from string to int if present
        if "iteration" in processed_data and isinstance(
            processed_data["iteration"], str
        ):
            processed_data["iteration"] = int(processed_data["iteration"])

        # Convert scaffolder_response from dict to LLMResponse if present
        if "scaffolder_response" in processed_data and isinstance(
            processed_data["scaffolder_response"], dict
        ):
            processed_data["scaffolder_response"] = LLMResponse.from_dict(
                processed_data["scaffolder_response"]
            )

        # Ensure required fields without defaults have None values if missing
        if "parent_scaffold_id" not in processed_data:
            processed_data["parent_scaffold_id"] = None
        if "iteration" not in processed_data:
            processed_data["iteration"] = None

        return cls(**processed_data)


@dataclass
class ScaffoldResult:
    """Result of generating a scaffold.

    Attributes:
        code: Python code for the scaffold
        metadata: Scaffold metadata
    """

    code: str
    metadata: ScaffoldMetadata


@dataclass
class ScaffoldExecutionResult:
    """Result of executing a scaffold.

    Attributes:
        output: Standard output from the scaffold
        stderr: Standard error output
        error_message: Error message from the scaffold execution
        execution_time: Time taken in seconds
    """

    output: str
    stderr: str
    execution_time: float
    error_message: Optional[str] = None


@dataclass
class ScaffoldRunData:
    """Data from a scaffold run that can be used for evolution.

    Attributes:
        code: The scaffold code that was run
        execution_log: Complete execution logs
        example: The dataset example that was processed
        actual_output: What the scaffold produced
        score: Numerical score (0-1)
    """

    code: str
    execution_log: str
    example: DatasetExample
    actual_output: str
    score: float


@dataclass
class ScaffoldExecutionTask:
    """Parameters for executing a scaffold.

    Attributes:
        scaffold_dir: Path to the scaffold directory
        log_file_path: Path to write execution logs
        input_string: Input to pass to the scaffold
        model_spec: Model specification for the executor
        timeout: Maximum execution time in seconds
        console_output: If True, print output to console
        thinking_budget_tokens: Budget for thinking tokens
    """

    scaffold_dir: str
    log_file_path: str
    input_string: str
    model_spec: str
    timeout: int = 120
    console_output: bool = False
    thinking_budget_tokens: int = 0


@dataclass
class ScaffolderPromptConfig:
    """Configuration for building scaffolder prompts.

    Attributes:
        generate_examples: List of DatasetExample objects for generation
        evolve_examples: List of ScaffoldRunData objects for evolution
        task_description: Description of the task to be performed by the scaffold
        scoring_fn_code: Content of the scoring function to show the executor
        for_executor: If True, the prompt will be for executor use (for prompt-only scaffolds)
        suggest_hack: Type of hack suggestion: "no", "hidden", or "explicit"
        domain: Domain name for domain-specific instructions
    """

    generate_examples: Optional[List["DatasetExample"]] = None
    evolve_examples: Optional[List["ScaffoldRunData"]] = None
    task_description: Optional[str] = None
    scoring_fn_code: Optional[str] = None
    for_executor: bool = False
    suggest_hack: str = "no"
    domain: Optional[str] = None
