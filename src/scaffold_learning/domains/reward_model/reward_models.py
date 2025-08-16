"""Reward model interfaces and implementations."""

import json
import re
import time
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from scaffold_learning.core.llm_interfaces import LLMInterface

# Constants
HEARTBEAT_TIMEOUT_SECONDS = 60
POLL_INTERVAL_SECONDS = 0.2
MAX_TOKEN_LENGTH = 16384
LARGE_INT_LIMIT = 2**31 - 1


class RewardModel(ABC):
    """Abstract base class for reward models."""

    @abstractmethod
    def score(self, prompt: str, response: str) -> float:
        """Score a response to a prompt.

        Args:
            prompt: The original prompt/question
            response: The response to score

        Returns:
            Floating point score
        """
        pass


class LLMRewardModel(RewardModel):
    """Reward model that uses an LLM to score responses."""

    def __init__(self, llm: LLMInterface):
        """Initialize with an LLM interface.

        Args:
            llm: LLM interface to use for scoring
        """
        self.llm = llm

    def score(self, prompt: str, response: str) -> float:
        """Score a response using the LLM.

        Args:
            prompt: The original prompt/question
            response: The response to score

        Returns:
            Floating point score
        """
        scoring_prompt = self._build_scoring_prompt(prompt, response)
        llm_response = self.llm.generate_response(scoring_prompt)
        return self._parse_score(llm_response.content)

    def _build_scoring_prompt(self, prompt: str, response: str) -> str:
        """Build the prompt for the LLM to score the response.

        Args:
            prompt: Original prompt
            response: Response to score

        Returns:
            Formatted prompt for scoring
        """
        return f"""Rate the quality of this response to the given prompt on a scale of 0.0 to 1.0 based on helpfulness, accuracy, and overall quality.

Prompt: {prompt}

Response: {response}

Please provide only the numerical score on a scale of 0.0 to 1.0. Only provide the numerical score, nothing else, using the format "Score: <score>"."""

    def _parse_score(self, response_text: str) -> float:
        """Parse a numerical score from the LLM response.

        Args:
            response_text: Raw LLM response text

        Returns:
            Parsed score, clamped to [0.0, 1.0]

        Raises:
            ValueError: If no valid score can be parsed from the response
        """
        if not response_text:
            raise ValueError("Empty response from LLM")

        # Try to find any decimal number in the response
        patterns = [
            r"(-?\d+\.?\d*)",  # Match decimal numbers like 0.75, 1, 0.5, -0.5
            r"(-?\d+\.?\d*)/1\.?0?",  # Match ratios like 0.8/1.0, -0.3/1.0
        ]

        for pattern in patterns:
            matches = re.findall(pattern, response_text)
            if matches:
                try:
                    score = float(matches[0])
                    # Clamp to [0.0, 1.0] range
                    return max(0.0, min(1.0, score))
                except ValueError:
                    continue

        # If no valid score found, raise an error
        raise ValueError(
            f"Could not parse valid score from LLM response: {response_text}"
        )


class HuggingFaceRewardModel(RewardModel):
    """Reward model using HuggingFace transformers."""

    REWARD_OFFSET = 10.0  # Offset to ensure scores are positive

    def __init__(self, model_name: str):
        """Initialize with a HuggingFace model.

        Args:
            model_name: HuggingFace model identifier (e.g., 'Skywork/Skywork-Reward-V2-Llama-3.1-8B')
        """
        self.model_name = model_name

        # Try to detect CUDA, fallback to CPU if torch not available
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        if not torch.cuda.is_available():
            raise RuntimeError("CUDA is required for HuggingFaceRewardModel.")

        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name)

        # Move to device
        self.model.to(self.device)
        self.model.eval()

    def score(self, prompt: str, response: str) -> float:
        """Score a response using the HuggingFace reward model.

        Args:
            prompt: The original prompt/question
            response: The response to score

        Returns:
            Floating point score
        """
        # Try to use chat template if available, otherwise use simple format
        if hasattr(self.tokenizer, "chat_template") and self.tokenizer.chat_template:
            # Format as conversation for the reward model
            conversation = [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": response},
            ]
            formatted_input = self.tokenizer.apply_chat_template(
                conversation, tokenize=False, add_generation_prompt=False
            )
        else:
            raise ValueError("Model does not have a chat template.")

        # Tokenize and move to device
        # Handle misconfigured model_max_length
        # (like in https://huggingface.co/OpenAssistant/reward-model-deberta-v3-large-v2/blob/main/tokenizer_config.json)
        max_length = getattr(self.tokenizer, "model_max_length", LARGE_INT_LIMIT)
        max_length = min(max_length, LARGE_INT_LIMIT)

        inputs = self.tokenizer(
            formatted_input,
            return_tensors="pt",
            truncation=True,
            max_length=max_length,
        )

        # Move to device
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        # Get reward score
        with torch.no_grad():
            outputs = self.model(**inputs)

        # Most reward models output a single value, get the score
        raw_score = outputs.logits.squeeze().float().item()

        # Ensure scores are positive
        return max(0.0, raw_score + self.REWARD_OFFSET)


class FileQueueRewardModel(RewardModel):
    """Reward model that communicates via file-based queue (for HPC systems)."""

    def __init__(
        self, queue_dir: str = "/tmp/reward_model_queue", timeout: float = 300
    ):
        """Initialize with queue directory.

        Args:
            queue_dir: Directory for file-based job queue
            timeout: Timeout for waiting for response (seconds)
        """
        self.queue_dir = Path(queue_dir)
        self.timeout = timeout

        # Ensure queue directories exist
        self.requests_dir = self.queue_dir / "requests"
        self.responses_dir = self.queue_dir / "responses"
        self.heartbeat_dir = self.queue_dir / "heartbeat"

        for dir_path in [self.requests_dir, self.responses_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

        # Check if any workers are active
        if not self._check_worker_health():
            print(f"Warning: No active workers found in {queue_dir}")
            print(
                "Start a worker with: srun --gres=gpu:1 python -m src.scaffold_learning.domains.reward_model.worker --model hf:MODEL_NAME --queue-dir {queue_dir}"
            )

    def _check_worker_health(self) -> bool:
        """Check if any workers are active based on heartbeat files."""
        if not self.heartbeat_dir.exists():
            return False

        current_time = time.time()
        for heartbeat_file in self.heartbeat_dir.glob("*.json"):
            try:
                data = json.loads(heartbeat_file.read_text())
                # Consider worker active if heartbeat is less than 60 seconds old
                if current_time - data["timestamp"] < HEARTBEAT_TIMEOUT_SECONDS:
                    return True
            except:
                continue
        return False

    def score(self, prompt: str, response: str) -> float:
        """Score a response using the file queue.

        Args:
            prompt: The original prompt/question
            response: The response to score

        Returns:
            Floating point score
        """
        # Create unique request ID
        request_id = str(uuid.uuid4())

        # Write request file
        request_data = {
            "request_id": request_id,
            "prompt": prompt,
            "response": response,
            "timestamp": time.time(),
        }

        request_file = self.requests_dir / f"{request_id}.json"
        request_file.write_text(json.dumps(request_data))

        # Wait for response
        response_file = self.responses_dir / f"{request_id}.json"
        start_time = time.time()

        while time.time() - start_time < self.timeout:
            # Force NFS directory cache refresh to see new files immediately
            try:
                list(self.responses_dir.iterdir())
            except OSError:
                # Ignore stale file handle errors during directory refresh
                pass

            if response_file.exists():
                response_data = json.loads(response_file.read_text())
                # Clean up response file
                response_file.unlink()
                return response_data["score"]

            time.sleep(POLL_INTERVAL_SECONDS)  # Poll every 200ms like vllm does

        # Timeout - try to clean up request
        try:
            request_file.unlink()
        except:
            pass

        raise TimeoutError(
            f"Timed out waiting for response after {self.timeout} seconds"
        )
