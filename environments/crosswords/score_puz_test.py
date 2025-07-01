#!/usr/bin/env python
"""Tests for score_puz.py"""

import unittest
import tempfile
import os
import puz
import score_puz

from unittest.mock import patch


class TestScorePuz(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures"""
        # Create a real puzzle object for our test crossword
        self.puzzle = puz.Puzzle()
        self.puzzle.width = 5
        self.puzzle.height = 5
        self.puzzle.solution = "FATE." + "ADULT" + "KARMA" + "EMBER" + ".SORT"
        self.puzzle.fill = "FATE." + "ADULT" + "KARMA" + "EMBER" + ".SORT"  # Use solution as fill

        # Set up clues in order: across clues first, then down clues
        self.puzzle.clues = [
            "Destiny",  # 1 Across: FATE
            "Grown-up",  # 5 Across: ADULT
            "What goes around",  # 6 Across: KARMA
            "Glowing coal",  # 7 Across: EMBER
            "Organize",  # 8 Across: SORT
            "Not real",  # 1 Down: FAKE
            "President John Quincy ___",  # 2 Down: ADAMS
            "Supercharged",  # 3 Down: TURBO
            "Cartoon hunter",  # 4 Down: ELMER
            "Pop-___",  # 9 Down: TART
        ]

        # Save puzzle to a temporary file for testing
        self.temp_puz_file = tempfile.NamedTemporaryFile(suffix=".puz", delete=False)
        self.puzzle.save(self.temp_puz_file.name)
        self.temp_puz_file.close()

    def tearDown(self):
        """Clean up test fixtures"""
        os.unlink(self.temp_puz_file.name)

    def test_perfect_grid_only(self):
        """Test scoring with only a perfect grid"""
        answer_content = """F A T E .
A D U L T
K A R M A
E M B E R
. S O R T"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(answer_content)
            answer_file = f.name

        try:
            score, correct, total = score_puz.score_puzzle(self.temp_puz_file.name, answer_file)
            self.assertEqual(score, 1.0)
        finally:
            os.unlink(answer_file)

    def test_perfect_across_only(self):
        """Test scoring with only perfect across answers"""
        answer_content = """Across:
  1. FATE
  5. ADULT
  7. KARMA
  8. EMBER
  9. SORT"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(answer_content)
            answer_file = f.name

        try:
            score, correct, total = score_puz.score_puzzle(self.temp_puz_file.name, answer_file)
            self.assertEqual(score, 1.0)
        finally:
            os.unlink(answer_file)

    def test_perfect_down_only(self):
        """Test scoring with only perfect down answers"""
        answer_content = """Down:
  1. FAKE
  2. ADAMS
  3. TURBO
  4. ELMER
  6. TART"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(answer_content)
            answer_file = f.name

        try:
            score, correct, total = score_puz.score_puzzle(self.temp_puz_file.name, answer_file)
            self.assertEqual(score, 1.0)
        finally:
            os.unlink(answer_file)

    def test_all_three_formats_perfect(self):
        """Test scoring with grid, across, and down all perfect"""
        answer_content = """F A T E .
A D U L T
K A R M A
E M B E R
. S O R T

Across:
  1. FATE
  5. ADULT
  7. KARMA
  8. EMBER
  9. SORT

Down:
  1. FAKE
  2. ADAMS
  3. TURBO
  4. ELMER
  6. TART"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(answer_content)
            answer_file = f.name

        try:
            score, correct, total = score_puz.score_puzzle(self.temp_puz_file.name, answer_file)
            self.assertEqual(score, 1.0)
        finally:
            os.unlink(answer_file)

    def test_partial_grid_errors(self):
        """Test scoring with some errors in grid"""
        answer_content = """F A T X .
A D U L T
K A R M A
E M B E R
. S O R T"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(answer_content)
            answer_file = f.name

        try:
            score, correct, total = score_puz.score_puzzle(self.temp_puz_file.name, answer_file)
            self.assertEqual(score, 22 / 23)  # 22 correct out of 23 fillable squares
        finally:
            os.unlink(answer_file)

    def test_conflicting_answers(self):
        """Test that if a square is wrong in any piece, it counts as wrong"""
        answer_content = """F A T E .
A D U L T
K A R M A
E M B E R
. S O R T

Across:
  1. FATX"""  # Wrong last letter conflicts with correct grid

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(answer_content)
            answer_file = f.name

        try:
            score, correct, total = score_puz.score_puzzle(self.temp_puz_file.name, answer_file)
            self.assertEqual(score, 22 / 23)  # Position 3 is wrong due to conflict
        finally:
            os.unlink(answer_file)

    def test_multiple_different_errors(self):
        """Test that different errors in different places both count against score"""
        answer_content = """F A T X .
A D U L T
K A R M A
E M B E R
. S O R T

Across:
  7. KARMZ"""  # Wrong last letter in different position
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(answer_content)
            answer_file = f.name
        
        try:
            score, correct, total = score_puz.score_puzzle(self.temp_puz_file.name, answer_file)
            # Grid has X instead of E at position 3, Across has Z instead of A at position 14
            # Two different errors = 21/23 correct
            self.assertEqual(score, 21 / 23)
        finally:
            os.unlink(answer_file)

    def test_empty_file(self):
        """Test that empty file scores 0.0"""
        answer_content = ""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(answer_content)
            answer_file = f.name

        try:
            score, correct, total = score_puz.score_puzzle(self.temp_puz_file.name, answer_file)
            self.assertEqual(score, 0.0)
        finally:
            os.unlink(answer_file)

    def test_duplicate_sections(self):
        """Test handling of duplicate sections (e.g., two Across sections)"""
        answer_content = """Across:
  1. FATE

Across:
  5. ADULX"""  # Wrong answer in second Across section

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(answer_content)
            answer_file = f.name

        try:
            score, correct, total = score_puz.score_puzzle(self.temp_puz_file.name, answer_file)
            # Should process both sections: FATE (4 correct) + ADUL from ADULX (4 correct) = 8/23
            self.assertEqual(score, 8 / 23)
        finally:
            os.unlink(answer_file)

    def test_partial_answers(self):
        """Test with only some clues answered"""
        answer_content = """Across:
  1. FATE
  7. KARMA"""  # Only 2 out of 5 across clues

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(answer_content)
            answer_file = f.name

        try:
            score, correct, total = score_puz.score_puzzle(self.temp_puz_file.name, answer_file)
            self.assertEqual(score, 9 / 23)  # Only 9 squares filled correctly (4+5)
        finally:
            os.unlink(answer_file)

    def test_case_insensitive(self):
        """Test that answers are case-insensitive"""
        answer_content = """f a t e .
a d u l t
k a r m a
e m b e r
. s o r t"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(answer_content)
            answer_file = f.name

        try:
            score, correct, total = score_puz.score_puzzle(self.temp_puz_file.name, answer_file)
            self.assertEqual(score, 1.0)
        finally:
            os.unlink(answer_file)

    def test_missing_clue_numbers(self):
        """Test handling of missing clue numbers in answer file"""
        answer_content = """Across:
  999. FATE"""  # Clue number 999 doesn't exist

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(answer_content)
            answer_file = f.name

        try:
            score, correct, total = score_puz.score_puzzle(self.temp_puz_file.name, answer_file)
            self.assertEqual(score, 0.0)  # No valid answers
        finally:
            os.unlink(answer_file)

    def test_wrong_length_answers(self):
        """Test handling of answers that are too short or too long"""
        answer_content = """Across:
  1. FIT
  5. ADULTTOOLONG"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(answer_content)
            answer_file = f.name

        try:
            score, correct, total = score_puz.score_puzzle(self.temp_puz_file.name, answer_file)
            # FIT is too short for FATE (3 chars vs 4), ADULTTOOLONG is too long for ADULT
            # Should only score the valid parts: FIT matches first and third chars of FATE, ADULT matches first 5 of ADULTTOOLONG
            self.assertEqual(score, 7 / 23)  # 2 from FIT + 5 from ADULT = 7 correct
        finally:
            os.unlink(answer_file)

    def test_command_line_interface(self):
        """Test the command line interface"""
        # Create a simple answer file
        answer_content = """F A T E .
A D U L T
K A R M A
E M B E R
. S O R T"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(answer_content)
            answer_file = f.name

        try:
            with patch(
                "sys.argv", ["score_puz.py", self.temp_puz_file.name, answer_file]
            ):
                with patch("builtins.print") as mock_print:
                    score_puz.main()
                    mock_print.assert_called_with("Score: 1.000 (23/23)")
        finally:
            os.unlink(answer_file)


if __name__ == "__main__":
    unittest.main()
