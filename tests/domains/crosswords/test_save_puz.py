#!/usr/bin/env python3
"""Tests for scaffold_learning.domains.crosswords.save_puz module"""

import unittest
import tempfile
import os
from unittest.mock import patch
from scaffold_learning.domains.crosswords import save_puz, puz


class TestSavePuz(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(self._cleanup)

        # Create a simple test puzzle - 2x2 grid
        self.puzzle = puz.Puzzle()
        self.puzzle.width = 2
        self.puzzle.height = 2
        self.puzzle.solution = "ABCD"  # Simple 2x2: AB / CD
        self.puzzle.fill = "ABCD"
        self.puzzle.title = "Test Puzzle"
        self.puzzle.author = "Test Author"
        self.puzzle.copyright = "2024 Test"
        self.puzzle.clues = ["AB across", "CD across", "AC down", "BD down"]

        # Save to temp file for testing
        self.temp_puz_file = tempfile.NamedTemporaryFile(suffix=".puz", delete=False)
        self.puzzle.save(self.temp_puz_file.name)
        self.temp_puz_file.close()

    def _cleanup(self):
        """Clean up temporary files"""
        import shutil

        shutil.rmtree(self.temp_dir)
        if os.path.exists(self.temp_puz_file.name):
            os.unlink(self.temp_puz_file.name)

    def test_save_puzzle_file(self):
        """Test save_puzzle_file function"""
        output_file = os.path.join(self.temp_dir, "test_puzzle.txt")
        numbering = self.puzzle.clue_numbering()

        save_puz.save_puzzle_file(self.puzzle, numbering, output_file)

        # Verify file was created
        self.assertTrue(os.path.exists(output_file))

        # Read and verify content
        with open(output_file, "r") as f:
            content = f.read()

        # Should contain empty grid (- for letters, . for black squares)
        self.assertIn("- -", content)  # Row 1: AB becomes - -
        self.assertIn("- -", content)  # Row 2: CD becomes - -

        # Should contain clues sections
        self.assertIn("Across:", content)
        self.assertIn("Down:", content)

        # Should contain actual clues without answers
        self.assertIn("AB across", content)
        self.assertIn("CD across", content)

    def test_save_answer_file(self):
        """Test save_answer_file function"""
        output_file = os.path.join(self.temp_dir, "test_answers.txt")
        numbering = self.puzzle.clue_numbering()

        save_puz.save_answer_file(self.puzzle, numbering, output_file)

        # Verify file was created
        self.assertTrue(os.path.exists(output_file))

        # Read and verify content
        with open(output_file, "r") as f:
            content = f.read()

        # Should contain solution grid
        self.assertIn("A B", content)  # Row 1
        self.assertIn("C D", content)  # Row 2

        # Should contain answer sections
        self.assertIn("Across:", content)
        self.assertIn("Down:", content)

        # Should contain actual answers
        self.assertIn("AB", content)  # Answer for across clue
        self.assertIn("AC", content)  # Answer for down clue


if __name__ == "__main__":
    unittest.main()
