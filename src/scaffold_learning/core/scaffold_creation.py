from typing import List, Dict, Optional, Callable, Tuple, Any
from pathlib import Path
import logging
import concurrent.futures
from scaffold_learning.core.data_structures import (
    DatasetExample,
    ScaffoldRunData,
    ScaffolderPromptConfig,
)
from scaffold_learning.core.llm_interfaces import LLMInterface
from scaffold_learning.core.experiment_files import ExperimentFileManager
from scaffold_learning.core.dataset_utils import ExampleSampler
from scaffold_learning.core.hydra_config import ExperimentConfig
from scaffold_learning.core.strategy_generation import generate_strategies
from scaffold_learning.core.scaffold_code_generation import (
    generate_scaffold,
    evolve_scaffold,
    make_prompt_only_scaffold,
)


class ScaffoldGenerator:
    """Handles generation of initial and evolved scaffolds."""

    def __init__(
        self,
        config: ExperimentConfig,
        scaffolder_llm: Optional[LLMInterface],
        strategy_llm: Optional[LLMInterface],
        file_manager: ExperimentFileManager,
        train_sampler: ExampleSampler,
        scoring_fn_code: Optional[str] = None,
    ):
        """Initialize scaffold generator.

        Args:
            config: Experiment configuration
            scaffolder_llm: LLM for generating/evolving scaffolds (None for baseline)
            strategy_llm: Optional LLM for strategy generation
            file_manager: File manager for saving scaffolds
            train_sampler: Sampler for training examples
            scoring_fn_code: Optional scoring function code for prompts
        """
        self.config = config
        self.scaffolder_llm = scaffolder_llm
        self.strategy_llm = strategy_llm
        self.file_manager = file_manager
        self.train_sampler = train_sampler
        self.scoring_fn_code = scoring_fn_code

        # Initialize scaffold ID tracking
        self.scaffold_counters = {}  # parent_id -> next_counter
        self.next_initial_id = 0

        # Set up logging
        self.logger = logging.getLogger(__name__)

        # Detect baseline mode
        self.is_baseline = config.scaffolder == "baseline"
        self.initial_scaffolds = 1 if self.is_baseline else config.initial_scaffolds

    def create_initial_scaffolds(self) -> List[str]:
        """Create initial scaffolds and return their IDs.

        Generates strategies if strategy_llm is provided, samples training examples,
        and creates scaffolds in parallel. For baseline mode, creates prompt-only
        scaffolds.

        Returns:
            List of scaffold IDs created
        """
        # This will end up just being ["0", "1", "2", ...]
        scaffold_ids = [
            self._get_next_scaffold_id() for _ in range(self.initial_scaffolds)
        ]

        # Get all training examples upfront
        examples_by_scaffold = self._get_training_examples(scaffold_ids)

        base_prompt_kwargs = {
            "scoring_fn_code": self.scoring_fn_code,
            "suggest_hack": self.config.suggest_hack,
            "domain": self.config.domain,
        }

        # Generate strategies (possibly None)
        strategies = self._generate_strategies(base_prompt_kwargs)

        # Create generation tasks
        generation_tasks = []
        for (scaffold_id, examples), strategy in zip(
            examples_by_scaffold.items(), strategies
        ):

            def generate_func(
                examples=examples,
                strategy=strategy,
                is_baseline=self.is_baseline,
            ):  # Capture examples, strategy, and baseline flag by value
                config = ScaffolderPromptConfig(
                    **base_prompt_kwargs,
                    generate_examples=examples,
                    strategy=strategy,
                )
                if is_baseline:
                    return make_prompt_only_scaffold(config=config)
                else:
                    assert (
                        self.scaffolder_llm is not None
                    ), "scaffolder_llm required for non-baseline mode"
                    return generate_scaffold(
                        config=config,
                        scaffolder_llm=self.scaffolder_llm,
                        iteration=0,
                    )

            generation_tasks.append((scaffold_id, generate_func))

        # Execute the generation tasks
        self._execute_scaffold_generation_batch(
            generation_tasks, "initial", self.config.max_generate_workers
        )

        return scaffold_ids

    def evolve_scaffolds(
        self, iteration: int, parent_runs: Dict[str, List[ScaffoldRunData]]
    ) -> List[str]:
        """Evolve scaffolds from parent runs and return new scaffold IDs.

        Takes the training runs from parent scaffolds and uses them to generate
        evolved versions in parallel.

        Args:
            iteration: Current iteration number
            parent_runs: Dict mapping parent scaffold ID to list of training runs

        Returns:
            List of newly created scaffold IDs
        """
        current_scaffold_ids = []

        # Create evolution tasks
        generation_tasks = []
        for parent_id, run_data_list in parent_runs.items():
            new_scaffold_id = self._get_next_scaffold_id(parent_id)
            current_scaffold_ids.append(new_scaffold_id)

            def evolve_func(
                run_data_list=run_data_list, parent_id=parent_id
            ):  # Capture by value
                config = ScaffolderPromptConfig(
                    evolve_examples=run_data_list,
                    scoring_fn_code=self.scoring_fn_code,
                    suggest_hack=self.config.suggest_hack,
                    domain=self.config.domain,
                )
                assert (
                    self.scaffolder_llm is not None
                ), "scaffolder_llm required for evolution"
                return evolve_scaffold(
                    config=config,
                    scaffolder_llm=self.scaffolder_llm,
                    iteration=iteration,
                    parent_scaffold_id=parent_id,
                )

            generation_tasks.append((new_scaffold_id, evolve_func))

        # Execute the evolution tasks
        self._execute_scaffold_generation_batch(
            generation_tasks, "evolved", self.config.max_generate_workers
        )

        return current_scaffold_ids

    def _get_next_scaffold_id(self, parent_id: Optional[str] = None) -> str:
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

    def _execute_scaffold_generation_batch(
        self,
        generation_tasks: List[Tuple[str, Callable]],
        scaffold_type: str,
        max_workers: int,
        strategies: Optional[List[Optional[str]]] = None,
    ) -> None:
        """Execute a batch of scaffold generation tasks using ThreadPoolExecutor.

        Args:
            generation_tasks: List of (scaffold_id, generation_function) tuples
            scaffold_type: Type of scaffold (e.g., "initial", "evolved"), used for logging
            max_workers: Maximum workers for parallel execution (1 for sequential)
            strategies: Optional list of strategies corresponding to each task (for initial scaffolds)
        """
        total_tasks = len(generation_tasks)

        if max_workers > 1:
            self.logger.info(
                f"Creating {total_tasks} {scaffold_type} scaffolds (up to {max_workers} in parallel)"
            )
        else:
            self.logger.info(f"Creating {total_tasks} {scaffold_type} scaffolds")

        completed = 0
        # Create mapping from scaffold_id to strategy
        strategy_map = {}
        if strategies:
            for i, (scaffold_id, _) in enumerate(generation_tasks):
                if i < len(strategies):
                    strategy_map[scaffold_id] = strategies[i]

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_id = {
                executor.submit(generation_func): scaffold_id
                for scaffold_id, generation_func in generation_tasks
            }

            for future in concurrent.futures.as_completed(future_to_id):
                scaffold_id = future_to_id[future]
                try:
                    result = future.result()
                    self.file_manager.save_scaffold(
                        scaffold_id=scaffold_id, result=result
                    )
                    completed += 1
                    log_message = f"Created {scaffold_type} scaffold {scaffold_id}"
                    if max_workers > 1:
                        log_message += f" ({completed}/{total_tasks})"
                    self.logger.info(log_message)
                except Exception as e:
                    self.logger.error(
                        f"Failed to create {scaffold_type} scaffold {scaffold_id}: {e}"
                    )
                    raise

    def _generate_strategies(
        self, base_prompt_kwargs: Dict[str, Any]
    ) -> List[Optional[str]]:
        """Generate strategies if strategy model is specified.

        Args:
            base_prompt_kwargs: Base prompt kwargs to use for strategy generation

        Returns:
            List of strategies, or list of None if no strategy model is specified
        """
        if self.is_baseline or not self.strategy_llm:
            return [None] * self.initial_scaffolds

        self.logger.info(
            f"Generating {self.initial_scaffolds} strategies using {self.strategy_llm.get_model_info()}"
        )

        # Get a single list of training examples for the strategy generation prompt
        examples = next(iter(self._get_training_examples([""]).values()))

        strategy_config = ScaffolderPromptConfig(
            **base_prompt_kwargs,
            generate_examples=examples,
        )

        # Generate strategies in batches
        all_strategies = []
        batch_size = self.config.strategy_batch_size or self.initial_scaffolds
        num_batches = self.initial_scaffolds // batch_size

        for batch_idx in range(num_batches):
            if num_batches > 1:
                self.logger.info(
                    f"Generating strategy batch {batch_idx + 1}/{num_batches}"
                )

            batch_strategies = generate_strategies(
                llm=self.strategy_llm,
                scaffolder_prompt_config=strategy_config,
                num_strategies=batch_size,
            )
            all_strategies.extend(batch_strategies)

        return all_strategies

    def _get_training_examples(
        self, scaffold_ids: List[str]
    ) -> Dict[str, List[DatasetExample]]:
        """Sample training examples using the stateful train_sampler."""
        examples_by_scaffold = {}
        for scaffold_id in scaffold_ids:
            examples_by_scaffold[scaffold_id] = self.train_sampler.sample(
                self.config.num_training_examples
            )
        return examples_by_scaffold
