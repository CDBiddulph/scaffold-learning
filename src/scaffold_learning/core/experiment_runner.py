import random
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Callable
from scaffold_learning.core.data_structures import (
    DatasetExample, ScaffoldResult, ScaffoldRunData
)
from scaffold_learning.core.llm_interfaces import LLMInterface
from scaffold_learning.core.experiment_files import ExperimentFileManager
from scaffold_learning.core.scaffold_generation import generate_scaffold, improve_scaffold
from scaffold_learning.core.scaffold_execution import execute_scaffold


class ExperimentRunner:
    """Orchestrates scaffold learning experiments."""
    
    def __init__(
        self,
        experiment_name: str,
        training_data: List[DatasetExample],
        validation_data: List[DatasetExample],
        scoring_function: Callable[[str, Dict], float],
        scaffolder_llm: LLMInterface,
        num_iterations: int,
        scaffolds_per_iter: int,
        initial_scaffolds: int,
        num_validation_examples: int,
        base_dir: Path = Path("experiments"),
        executor_model: str = "gpt-4"
    ):
        """Initialize an experiment runner.
        
        Args:
            experiment_name: Name for this experiment run
            training_data: List of training examples
            validation_data: List of validation examples
            scoring_function: Function that takes (expected, scoring_data) and returns score 0-1
            scaffolder_llm: LLM to use for generating/improving scaffolds
            num_iterations: Number of improvement iterations to run
            scaffolds_per_iter: Number of top scaffolds to improve each iteration
            initial_scaffolds: Number of scaffolds to create initially
            num_validation_examples: Number of validation examples to use for scoring
            base_dir: Base directory for all experiments
            executor_model: Model name to use for executing scaffolds
        """
        # Validate parameters
        if scaffolds_per_iter > initial_scaffolds:
            raise ValueError("scaffolds_per_iter cannot be greater than initial_scaffolds")
        
        self.experiment_name = experiment_name
        self.training_data = training_data
        self.validation_data = validation_data
        self.scoring_function = scoring_function
        self.scaffolder_llm = scaffolder_llm
        self.num_iterations = num_iterations
        self.scaffolds_per_iter = scaffolds_per_iter
        self.initial_scaffolds = initial_scaffolds
        self.num_validation_examples = num_validation_examples
        self.executor_model = executor_model
        
        # Set up experiment directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        experiment_dir = base_dir / f"{experiment_name}_{timestamp}"
        self.file_manager = ExperimentFileManager(experiment_dir)
        
        # Initialize scaffold ID tracking
        self.scaffold_counters = {}  # parent_id -> next_counter
        self.next_initial_id = 0
        
        # Track current iteration scores
        self.current_iteration_scores = {}
        
        # Set up logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Save experiment metadata
        metadata = {
            "experiment_name": experiment_name,
            "created_at": timestamp,
            "num_iterations": num_iterations,
            "scaffolds_per_iter": scaffolds_per_iter,
            "initial_scaffolds": initial_scaffolds,
            "num_validation_examples": num_validation_examples,
            "random_seed": random.randint(0, 1000000)
        }
        random.seed(metadata["random_seed"])
        self.file_manager.save_experiment_metadata(metadata)
        
        self.logger.info(f"Initialized experiment: {experiment_name}")
        self.logger.info(f"Random seed: {metadata['random_seed']}")
    
    def run(self) -> Path:
        """Run the complete experiment.
        
        Creates initial scaffolds, runs iterations of evaluation and improvement,
        and returns the best performing scaffold.
        
        Returns:
            Path to the best performing scaffold directory
        """
        self.logger.info("Starting experiment run")
        
        # Create initial scaffolds
        prompt = "Generate a Python script that solves crossword clues"  # Default prompt
        scaffold_ids = self._create_initial_scaffolds(prompt)
        
        best_scaffold_path = None
        best_score = -1.0
        
        # Run iterations
        for iteration in range(self.num_iterations + 1):  # +1 to include iteration 0
            self.logger.info(f"Starting iteration {iteration}")
            
            # Get scaffolds for this iteration
            if iteration == 0:
                current_scaffold_ids = scaffold_ids
            else:
                # Get scaffold paths from previous iteration
                prev_scaffold_paths = {}
                for scaffold_id in self.current_iteration_scores.keys():
                    path = self.file_manager.get_scaffold_path(iteration - 1, scaffold_id)
                    if path.exists():
                        prev_scaffold_paths[scaffold_id] = path
                
                # Select top scaffolds
                top_scaffolds = self._select_top_scaffolds(
                    self.scaffolds_per_iter, prev_scaffold_paths
                )
                
                current_scaffold_ids = []
                
                # Copy selected scaffolds to old/ directory and improve them
                for parent_id, parent_path in top_scaffolds:
                    # Copy to old directory
                    self.file_manager.copy_scaffold(
                        from_path=parent_path,
                        to_iteration=iteration,
                        to_scaffold_id=parent_id
                    )
                    
                    # Generate improved scaffold
                    new_scaffold_id = self._get_next_scaffold_id(parent_id)
                    
                    # Run a training example to get feedback
                    training_example = random.choice(self.training_data)
                    run_data = self._run_training_example(
                        iteration=iteration - 1,
                        scaffold_id=parent_id,
                        example=training_example
                    )
                    
                    # Generate improved scaffold
                    try:
                        improved_result = improve_scaffold(
                            run_data=run_data,
                            scaffolder_llm=self.scaffolder_llm
                        )
                        improved_result.metadata.iteration = iteration
                        improved_result.metadata.parent_scaffold_id = parent_id
                        
                        # Save improved scaffold
                        self.file_manager.save_scaffold(
                            iteration=iteration,
                            scaffold_id=new_scaffold_id,
                            result=improved_result
                        )
                        
                        current_scaffold_ids.append(new_scaffold_id)
                        self.logger.info(f"Created improved scaffold {new_scaffold_id} from {parent_id}")
                        
                    except Exception as e:
                        self.logger.warning(f"Failed to improve scaffold {parent_id}: {e}")
                        # Continue with other scaffolds
                        continue
            
            # Evaluate all scaffolds in this iteration
            self.current_iteration_scores = {}
            
            # Sample validation examples for consistent evaluation
            validation_sample = random.sample(
                self.validation_data,
                min(self.num_validation_examples, len(self.validation_data))
            )
            
            for scaffold_id in current_scaffold_ids:
                try:
                    score = self._evaluate_scaffold(
                        iteration=iteration,
                        scaffold_id=scaffold_id,
                        validation_examples=validation_sample
                    )
                    self.current_iteration_scores[scaffold_id] = score
                    
                    # Track best scaffold
                    if score > best_score:
                        best_score = score
                        best_scaffold_path = self.file_manager.get_scaffold_path(iteration, scaffold_id)
                        
                except Exception as e:
                    self.logger.warning(f"Failed to evaluate scaffold {scaffold_id}: {e}")
                    self.current_iteration_scores[scaffold_id] = 0.0
            
            # Save scores for this iteration
            self.file_manager.save_scores(
                iteration=iteration,
                train_scores={},  # Not tracking training scores currently
                valid_scores=self.current_iteration_scores
            )
            
            # Log iteration results
            if self.current_iteration_scores:
                avg_score = sum(self.current_iteration_scores.values()) / len(self.current_iteration_scores)
                max_score = max(self.current_iteration_scores.values())
                self.logger.info(f"Iteration {iteration}: avg={avg_score:.3f}, max={max_score:.3f}")
            
            # Break early if no scaffolds to improve
            if iteration < self.num_iterations and len(self.current_iteration_scores) == 0:
                self.logger.warning("No scaffolds available for improvement, stopping early")
                break
        
        if best_scaffold_path is None:
            raise RuntimeError("No valid scaffolds were created during the experiment")
        
        self.logger.info(f"Experiment complete. Best scaffold: {best_scaffold_path} (score: {best_score:.3f})")
        return best_scaffold_path
    
    def _get_next_scaffold_id(self, parent_id: str = None) -> str:
        """Generate the next scaffold ID.
        
        Args:
            parent_id: Parent scaffold ID if this is a derived scaffold
            
        Returns:
            New scaffold ID following the naming convention
        """
        if parent_id is None:
            # Initial scaffold: use sequential numbers
            scaffold_id = str(self.next_initial_id)
            self.next_initial_id += 1
            return scaffold_id
        else:
            # Derived scaffold: append counter to parent ID
            if parent_id not in self.scaffold_counters:
                self.scaffold_counters[parent_id] = 0
            
            counter = self.scaffold_counters[parent_id]
            self.scaffold_counters[parent_id] += 1
            
            return f"{parent_id}-{counter}"
    
    def _create_initial_scaffolds(self, prompt: str) -> List[str]:
        """Create initial scaffolds using random training examples.
        
        Args:
            prompt: Task description for the scaffolds
            
        Returns:
            List of scaffold IDs created
        """
        scaffold_ids = []
        
        self.logger.info(f"Creating {self.initial_scaffolds} initial scaffolds")
        
        for i in range(self.initial_scaffolds):
            scaffold_id = self._get_next_scaffold_id()
            
            # Select random training example
            example = random.choice(self.training_data)
            
            # Generate scaffold
            result = generate_scaffold(
                prompt=prompt,
                scaffolder_llm=self.scaffolder_llm,
                examples=[example]  # Show one example for now
            )
            
            # Update metadata
            result.metadata.iteration = 0
            
            # Save scaffold
            self.file_manager.save_scaffold(
                iteration=0,
                scaffold_id=scaffold_id,
                result=result
            )
            
            scaffold_ids.append(scaffold_id)
            self.logger.info(f"Created initial scaffold {scaffold_id}")
        
        return scaffold_ids
    
    def _evaluate_scaffold(
        self,
        iteration: int,
        scaffold_id: str,
        validation_examples: List[DatasetExample]
    ) -> float:
        """Evaluate a scaffold on validation examples.
        
        Args:
            iteration: Current iteration number
            scaffold_id: ID of scaffold to evaluate
            validation_examples: Examples to test the scaffold on
            
        Returns:
            Average score across all validation examples
        """
        scaffold_path = self.file_manager.get_scaffold_path(iteration, scaffold_id)
        scores = []
        
        for example in validation_examples:
            # Get logs path
            logs_path = self.file_manager.get_logs_path(iteration, scaffold_id, "valid")
            
            try:
                # Execute scaffold
                result = execute_scaffold(
                    scaffold_dir=scaffold_path,
                    input_string=example.input,
                    model=self.executor_model,
                    logs_path=logs_path
                )
                
                # Calculate score
                if result.exit_code == 0:
                    expected = example.scoring_data.get("solution", str(example.scoring_data))
                    score = self.scoring_function(expected, {"solution": result.output})
                else:
                    score = 0.0  # Failed execution gets 0 score
                    
            except Exception as e:
                self.logger.warning(f"Error evaluating scaffold {scaffold_id}: {e}")
                score = 0.0
            
            scores.append(score)
        
        average_score = sum(scores) / len(scores) if scores else 0.0
        self.logger.info(f"Scaffold {scaffold_id} validation score: {average_score:.3f}")
        
        return average_score
    
    def _select_top_scaffolds(
        self,
        scaffolds_per_iter: int,
        scaffold_paths: Dict[str, Path]
    ) -> List[Tuple[str, Path]]:
        """Select top performing scaffolds with rescoring.
        
        Args:
            scaffolds_per_iter: Number of scaffolds to select
            scaffold_paths: Mapping of scaffold_id to path
            
        Returns:
            List of (scaffold_id, path) tuples for selected scaffolds
        """
        # Sort by current scores (highest first)
        sorted_scaffolds = sorted(
            self.current_iteration_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        selected = []
        for scaffold_id, score in sorted_scaffolds:
            if len(selected) >= scaffolds_per_iter:
                break
                
            if scaffold_id in scaffold_paths:
                path = scaffold_paths[scaffold_id]
                selected.append((scaffold_id, path))
                
        return selected
    
    def _run_training_example(
        self,
        iteration: int,
        scaffold_id: str,
        example: DatasetExample
    ) -> ScaffoldRunData:
        """Run a scaffold on a training example.
        
        Args:
            iteration: Current iteration number
            scaffold_id: ID of scaffold to run
            example: Training example to process
            
        Returns:
            ScaffoldRunData with execution results and score
        """
        # Load scaffold
        scaffold_result = self.file_manager.load_scaffold(iteration, scaffold_id)
        scaffold_path = self.file_manager.get_scaffold_path(iteration, scaffold_id)
        
        # Get logs path
        logs_path = self.file_manager.get_logs_path(iteration, scaffold_id, "train")
        
        try:
            # Execute scaffold
            execution_result = execute_scaffold(
                scaffold_dir=scaffold_path,
                input_string=example.input,
                model=self.executor_model,
                logs_path=logs_path
            )
            
            # Calculate score
            if execution_result.exit_code == 0:
                expected = example.scoring_data.get("solution", str(example.scoring_data))
                score = self.scoring_function(expected, {"solution": execution_result.output})
            else:
                score = 0.0
            
            # Read execution log
            execution_log = logs_path.read_text() if logs_path.exists() else ""
            
            run_data = ScaffoldRunData(
                code=scaffold_result.code,
                execution_log=execution_log,
                example=example,
                actual_output=execution_result.output,
                score=score
            )
            
            self.logger.info(f"Training run {scaffold_id}: score {score:.3f}")
            return run_data
            
        except Exception as e:
            self.logger.warning(f"Error running training example for {scaffold_id}: {e}")
            
            # Return failed run data
            return ScaffoldRunData(
                code=scaffold_result.code,
                execution_log=f"Error: {str(e)}",
                example=example,
                actual_output="",
                score=0.0
            )