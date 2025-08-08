#!/usr/bin/env python
"""Tests for meta-optimize integration with scoring_utils."""

import json
import unittest

from src.scaffold_learning.core.scoring_utils import create_scoring_function, get_scoring_function_code


class TestMetaOptimizeScoringUtils(unittest.TestCase):
    """Test meta-optimize integration with scoring utilities."""

    def test_create_scoring_function_basic(self):
        """Test creating meta-optimize scoring function with mcq mesa-domain."""
        # Setup
        domain_params = {
            "mesa-domain": "gpqa",
            "mesa-params": "{}"
        }
        
        # Execute
        scoring_fn = create_scoring_function("meta-optimize", domain_params)
        
        # Verify function is callable
        self.assertTrue(callable(scoring_fn))

    def test_create_scoring_function_with_mesa_params(self):
        """Test creating meta-optimize scoring function with mesa-domain params."""
        # Setup
        domain_params = {
            "mesa-domain": "crosswords", 
            "mesa-params": '{"mode": "strict"}'
        }
        
        # Execute
        scoring_fn = create_scoring_function("meta-optimize", domain_params)
        
        # Verify function is callable
        self.assertTrue(callable(scoring_fn))

    def test_create_scoring_function_missing_mesa_domain(self):
        """Test error when mesa-domain is missing."""
        # Setup
        domain_params = {}
        
        # Execute & Verify
        with self.assertRaises(ValueError) as cm:
            create_scoring_function("meta-optimize", domain_params)
        
        self.assertIn("meta-optimize domain requires 'mesa-domain' parameter", str(cm.exception))

    def test_create_scoring_function_invalid_mesa_params_json(self):
        """Test error when mesa-params is invalid JSON."""
        # Setup
        domain_params = {
            "mesa-domain": "gpqa",
            "mesa-params": "invalid json"
        }
        
        # Execute & Verify
        with self.assertRaises(json.JSONDecodeError):
            create_scoring_function("meta-optimize", domain_params)

    def test_create_scoring_function_end_to_end(self):
        """Test end-to-end scoring with actual meta-optimize data."""
        # Setup
        domain_params = {
            "mesa-domain": "gpqa",
            "mesa-params": "{}"
        }
        scoring_fn = create_scoring_function("meta-optimize", domain_params)
        
        # Create test data
        scoring_data = {
            "input": json.dumps({
                "scoring_data": [
                    {"input": "Question 1", "correct_answer": "A"},
                    {"input": "Question 2", "correct_answer": "B"}
                ]
            })
        }
        attempt = json.dumps(["A", "B"])  # Both correct
        
        # Execute
        result = scoring_fn(attempt, scoring_data)
        
        # Verify
        self.assertEqual(result, 1.0)

    def test_create_scoring_function_mixed_scores(self):
        """Test end-to-end scoring with mixed correct/incorrect answers."""
        # Setup
        domain_params = {
            "mesa-domain": "gpqa",
            "mesa-params": "{}"
        }
        scoring_fn = create_scoring_function("meta-optimize", domain_params)
        
        # Create test data
        scoring_data = {
            "input": json.dumps({
                "scoring_data": [
                    {"input": "Question 1", "correct_answer": "A"},
                    {"input": "Question 2", "correct_answer": "B"}
                ]
            })
        }
        attempt = json.dumps(["A", "X"])  # One correct, one wrong
        
        # Execute
        result = scoring_fn(attempt, scoring_data)
        
        # Verify
        self.assertEqual(result, 0.5)  # Average of 1.0 and 0.0

    def test_get_scoring_function_code(self):
        """Test getting scoring function code for meta-optimize."""
        # Execute
        code = get_scoring_function_code("meta-optimize")
        
        # Verify
        self.assertIn("def score(", code)
        self.assertIn("inner_score", code)
        self.assertIn("meta-optimize", code)


if __name__ == "__main__":
    unittest.main()