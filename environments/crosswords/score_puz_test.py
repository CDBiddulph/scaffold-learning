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
        self.puzzle.fill = (
            "FATE." + "ADULT" + "KARMA" + "EMBER" + ".SORT"
        )  # Use solution as fill

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

    def _score_answer_content(self, answer_content):
        """Helper method to score answer content and return score tuple"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(answer_content)
            answer_file = f.name

        try:
            return score_puz.score_puzzle(self.temp_puz_file.name, answer_file)
        finally:
            os.unlink(answer_file)

    def _assert_score(self, answer_content, expected_score):
        """Helper method to score answer content and assert expected score"""
        score, correct, total = self._score_answer_content(answer_content)
        self.assertEqual(score, expected_score)
        self.assertEqual(score, correct / total if total > 0 else 0.0)

    def test_perfect_grid_only(self):
        """Test scoring with only a perfect grid"""
        answer_content = """F A T E .
A D U L T
K A R M A
E M B E R
. S O R T"""

        self._assert_score(answer_content, 1.0)

    def test_perfect_across_only(self):
        """Test scoring with only perfect across answers"""
        answer_content = """Across:
  1. FATE
  5. ADULT
  7. KARMA
  8. EMBER
  9. SORT"""

        self._assert_score(answer_content, 1.0)

    def test_perfect_down_only(self):
        """Test scoring with only perfect down answers"""
        answer_content = """Down:
  1. FAKE
  2. ADAMS
  3. TURBO
  4. ELMER
  6. TART"""

        self._assert_score(answer_content, 1.0)

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

        self._assert_score(answer_content, 1.0)

    def test_partial_grid_errors(self):
        """Test scoring with some errors in grid"""
        answer_content = """F A T X .
A D U L T
K A R M A
E M B E R
. S O R T"""

        self._assert_score(
            answer_content, 22 / 23
        )  # 22 correct out of 23 fillable squares

    def test_conflicting_answers(self):
        """Test that if a square is wrong in any piece, it counts as wrong"""
        answer_content = """F A T E .
A D U L T
K A R M A
E M B E R
. S O R T

Across:
  1. FATX"""  # Wrong last letter conflicts with correct grid

        self._assert_score(
            answer_content, 22 / 23
        )  # Position 3 is wrong due to conflict

    def test_multiple_different_errors(self):
        """Test that different errors in different places both count against score"""
        answer_content = """F A T X .
A D U L T
K A R M A
E M B E R
. S O R T

Across:
  7. KARMZ"""  # Wrong last letter in different position

        # Grid has X instead of E at position 3, Across has Z instead of A at position 14
        # Two different errors = 21/23 correct
        self._assert_score(answer_content, 21 / 23)

    def test_empty_file(self):
        """Test that empty file scores 0.0"""
        answer_content = ""

        self._assert_score(answer_content, 0.0)

    def test_duplicate_sections(self):
        """Test handling of duplicate sections (e.g., two Across sections)"""
        answer_content = """Across:
  1. FATE

Across:
  5. ADULX"""  # Wrong answer in second Across section

        # Should process both sections: FATE (4 correct) + ADUL from ADULX (4 correct) = 8/23
        self._assert_score(answer_content, 8 / 23)

    def test_partial_answers(self):
        """Test with only some clues answered"""
        answer_content = """Across:
  1. FATE
  7. KARMA"""  # Only 2 out of 5 across clues

        # Only 9 squares filled correctly (4+5)
        self._assert_score(answer_content, 9 / 23)

    def test_case_insensitive(self):
        """Test that answers are case-insensitive"""
        answer_content = """f a t e .
a d u l t
k a r m a
e m b e r
. s o r t"""

        self._assert_score(answer_content, 1.0)

    def test_missing_clue_numbers(self):
        """Test handling of missing clue numbers in answer file"""
        answer_content = """Across:
  999. FATE"""  # Clue number 999 doesn't exist

        self._assert_score(answer_content, 0.0)  # No valid answers

    def test_wrong_length_answers(self):
        """Test handling of answers that are too short or too long"""
        answer_content = """Across:
  1. FIT
  5. ADULTTOOLONG"""

        # FIT is too short for FATE (3 chars vs 4), ADULTTOOLONG is too long for ADULT
        # Should only score the valid parts: FIT matches first and third chars of FATE, ADULT matches first 5 of ADULTTOOLONG
        # 2 from FIT + 5 from ADULT = 7 correct
        self._assert_score(answer_content, 7 / 23)

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
