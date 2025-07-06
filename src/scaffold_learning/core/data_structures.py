from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional


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
class ScaffoldMetadata:
    """Metadata for a generated scaffold.
    
    Attributes:
        created_at: Timestamp of creation
        model: Executor model name (if specified)
        parent_scaffold_id: ID of scaffold this was derived from (if applicable)
        iteration: Iteration number when created
    """
    created_at: str
    model: Optional[str]
    parent_scaffold_id: Optional[str]
    iteration: int

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
        return cls(**data)


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
        exit_code: Process exit code (0 for success)
        execution_time: Time taken in seconds
    """
    output: str
    stderr: str
    exit_code: int
    execution_time: float


@dataclass
class ScaffoldRunData:
    """Data from a scaffold run that can be used for improvement.
    
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