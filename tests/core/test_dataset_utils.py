"""Tests for dataset_utils module."""

import json
import tempfile
from pathlib import Path
import pytest

from scaffold_learning.core.dataset_utils import load_datasets, ExampleSampler
from scaffold_learning.core.data_structures import DatasetExample


class TestLoadDatasets:
    def test_load_single_split(self):
        """Test loading a single dataset split."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            dataset_dir = Path(tmp_dir)
            
            # Create train split
            train_path = dataset_dir / "train.jsonl"
            test_data = [
                {
                    "id": "example_1",
                    "input": "Test input 1",
                    "scoring_data": {"solution": "Test solution 1"},
                },
                {
                    "id": "example_2",
                    "input": "Test input 2",
                    "scoring_data": {"solution": "Test solution 2", "other_field": "value"},
                },
            ]
            
            with open(train_path, "w") as f:
                for item in test_data:
                    f.write(json.dumps(item) + "\n")
            
            # Load dataset
            datasets = load_datasets(dataset_dir, ["train"])
            
            assert "train" in datasets
            assert len(datasets["train"]) == 2
            assert datasets["train"][0].id == "example_1"
            assert datasets["train"][0].input == "Test input 1"
            assert datasets["train"][0].scoring_data == {"solution": "Test solution 1", "input": "Test input 1"}
            
            assert datasets["train"][1].id == "example_2"
            assert datasets["train"][1].input == "Test input 2"
            assert datasets["train"][1].scoring_data == {"solution": "Test solution 2", "other_field": "value", "input": "Test input 2"}

    def test_load_multiple_splits(self):
        """Test loading multiple dataset splits."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            dataset_dir = Path(tmp_dir)

            # Create train and valid splits
            for split in ["train", "valid"]:
                dataset_path = dataset_dir / f"{split}.jsonl"
                test_data = [
                    {
                        "id": f"{split}_1",
                        "input": f"{split} input",
                        "scoring_data": {"solution": f"{split} solution"},
                    }
                ]
                with open(dataset_path, "w") as f:
                    for item in test_data:
                        f.write(json.dumps(item) + "\n")

            # Load datasets
            datasets = load_datasets(dataset_dir, ["train", "valid"])

            assert "train" in datasets
            assert "valid" in datasets
            assert len(datasets["train"]) == 1
            assert len(datasets["valid"]) == 1
            assert datasets["train"][0].id == "train_1"
            assert datasets["valid"][0].id == "valid_1"


class TestExampleSampler:
    def test_sample_basic(self):
        """Test basic sampling functionality."""
        examples = [
            DatasetExample(id="ex1", input="input1", scoring_data={}),
            DatasetExample(id="ex2", input="input2", scoring_data={}),
            DatasetExample(id="ex3", input="input3", scoring_data={}),
        ]
        
        sampler = ExampleSampler(seed=42, dataset=examples, allow_resample=False)
        
        # Sample 2 examples
        sampled = sampler.sample(2)
        assert len(sampled) == 2
        assert all(isinstance(ex, DatasetExample) for ex in sampled)
        assert all(ex in examples for ex in sampled)
    
    def test_sample_deterministic(self):
        """Test that sampling with same seed gives same results."""
        examples = [
            DatasetExample(id=f"ex{i}", input=f"input{i}", scoring_data={})
            for i in range(10)
        ]
        
        sampler1 = ExampleSampler(seed=42, dataset=examples, allow_resample=False)
        sampler2 = ExampleSampler(seed=42, dataset=examples, allow_resample=False)
        
        samples1 = sampler1.sample(5)
        samples2 = sampler2.sample(5)
        
        assert [ex.id for ex in samples1] == [ex.id for ex in samples2]
    
    def test_sample_no_resample_exhaustion(self):
        """Test that sampling without resampling raises error when exhausted."""
        examples = [
            DatasetExample(id="ex1", input="input1", scoring_data={}),
            DatasetExample(id="ex2", input="input2", scoring_data={}),
        ]
        
        sampler = ExampleSampler(seed=42, dataset=examples, allow_resample=False)
        
        # Sample all examples
        sampler.sample(2)
        
        # Try to sample more - should raise
        with pytest.raises(ValueError, match="No remaining data"):
            sampler.sample(1)
    
    def test_sample_with_resample(self):
        """Test that sampling with resampling works when dataset exhausted."""
        examples = [
            DatasetExample(id="ex1", input="input1", scoring_data={}),
            DatasetExample(id="ex2", input="input2", scoring_data={}),
        ]
        
        sampler = ExampleSampler(seed=42, dataset=examples, allow_resample=True)
        
        # Sample more than available - should resample
        sampled = sampler.sample(5)
        assert len(sampled) == 5
        assert all(isinstance(ex, DatasetExample) for ex in sampled)
