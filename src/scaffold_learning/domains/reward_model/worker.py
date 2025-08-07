#!/usr/bin/env python3
"""
Reward Model Worker Process

Runs on compute nodes and processes reward model requests from a file-based queue.
Based on the vllm_worker.py design from prompt-distill.
"""

import argparse
import json
import logging
import os
import time
import uuid
from pathlib import Path
from typing import Optional, Dict, Any

from scaffold_learning.domains.reward_model.factory import create_reward_model


class RewardModelWorker:
    """Worker process that handles reward model requests from a file queue"""

    def __init__(
        self,
        model_spec: str,
        queue_dir: str,
        worker_id: Optional[str] = None,
    ):
        self.model_spec = model_spec
        self.queue_dir = Path(queue_dir)
        self.worker_id = worker_id or f"worker_{uuid.uuid4().hex[:8]}"
        
        # Create queue directories
        self.requests_dir = self.queue_dir / "requests"
        self.processing_dir = self.queue_dir / "processing"
        self.responses_dir = self.queue_dir / "responses"
        self.heartbeat_dir = self.queue_dir / "heartbeat"
        
        for dir_path in [
            self.requests_dir,
            self.processing_dir, 
            self.responses_dir,
            self.heartbeat_dir,
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        logging.info(f"Loading reward model: {self.model_spec}")
        self.model = create_reward_model(self.model_spec)
        logging.info("Reward model loaded successfully")
        
        logging.info(f"Worker {self.worker_id} initialized for model {model_spec}")
    
    def _write_heartbeat(self):
        """Write heartbeat file to indicate worker is alive"""
        heartbeat_file = self.heartbeat_dir / f"{self.worker_id}.json"
        heartbeat_data = {
            "worker_id": self.worker_id,
            "model": self.model_spec,
            "timestamp": time.time(),
        }
        heartbeat_file.write_text(json.dumps(heartbeat_data))
    
    def _process_request(self, request_file: Path) -> None:
        """Process a single request file"""
        # Move to processing directory
        processing_file = self.processing_dir / request_file.name
        
        try:
            # Atomic move to claim the job
            request_file.rename(processing_file)
        except FileNotFoundError:
            # Another worker got it first
            return
        
        try:
            # Load request
            request_data = json.loads(processing_file.read_text())
            request_id = request_data["request_id"]
            prompt = request_data["prompt"]
            response = request_data["response"]
            
            logging.info(f"Processing request {request_id}")
            
            # Score with the model
            score = self.model.score(prompt, response)
            
            # Write response
            response_data = {
                "request_id": request_id,
                "score": score,
                "worker_id": self.worker_id,
                "timestamp": time.time(),
            }
            
            response_file = self.responses_dir / f"{request_id}.json"
            response_file.write_text(json.dumps(response_data))
            
            # Clean up processing file
            processing_file.unlink()
            
            logging.info(f"Completed request {request_id}, score: {score}")
            
        except Exception as e:
            import traceback
            logging.error(f"Error processing request {processing_file.name}: {e}")
            logging.error(f"Full traceback:\n{traceback.format_exc()}")
            # Don't retry - move to a failed directory instead
            failed_dir = self.queue_dir / "failed"
            failed_dir.mkdir(exist_ok=True)
            try:
                failed_file = failed_dir / processing_file.name
                # Save error info with the failed request
                error_data = json.loads(processing_file.read_text())
                error_data['error'] = str(e)
                error_data['traceback'] = traceback.format_exc()
                failed_file.write_text(json.dumps(error_data, indent=2))
                processing_file.unlink()
            except:
                pass
    
    def run(self, poll_interval: float = 1.0, heartbeat_interval: float = 30.0):
        """Main worker loop"""
        last_heartbeat = 0
        
        logging.info(f"Worker {self.worker_id} starting main loop")
        
        while True:
            try:
                # Write heartbeat periodically
                if time.time() - last_heartbeat > heartbeat_interval:
                    self._write_heartbeat()
                    last_heartbeat = time.time()
                
                # Check for new requests
                request_files = list(self.requests_dir.glob("*.json"))
                
                if request_files:
                    # Process oldest request first
                    request_files.sort(key=lambda f: f.stat().st_mtime)
                    self._process_request(request_files[0])
                else:
                    # No requests, sleep briefly
                    time.sleep(poll_interval)
                    
            except KeyboardInterrupt:
                logging.info("Worker interrupted, shutting down")
                break
            except Exception as e:
                logging.error(f"Unexpected error in main loop: {e}")
                time.sleep(poll_interval)


def main():
    parser = argparse.ArgumentParser(description="Reward model worker process")
    parser.add_argument(
        "--model",
        required=True,
        help="Reward model specification (e.g., 'hf:model_name')",
    )
    parser.add_argument(
        "--queue-dir",
        default="/tmp/reward_model_queue",
        help="Directory for job queue",
    )
    parser.add_argument(
        "--worker-id",
        help="Unique worker identifier (auto-generated if not provided)",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=1.0,
        help="How often to check for new jobs (seconds)",
    )
    parser.add_argument(
        "--heartbeat-interval",
        type=float,
        default=30.0,
        help="How often to write heartbeat file (seconds)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    # Create and run worker
    worker = RewardModelWorker(
        model_spec=args.model,
        queue_dir=args.queue_dir,
        worker_id=args.worker_id,
    )
    
    worker.run(
        poll_interval=args.poll_interval,
        heartbeat_interval=args.heartbeat_interval,
    )


if __name__ == "__main__":
    main()