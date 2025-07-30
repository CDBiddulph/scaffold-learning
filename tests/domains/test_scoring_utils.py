"""Tests for shared scoring utilities."""

import pytest
from src.scaffold_learning.domains.scoring_utils import extract_answer_letter, score_letter_choice


class TestExtractAnswerLetter:
    """Test answer extraction with various formats."""

    def test_explicit_answer_formats(self):
        """Test explicit answer declarations."""
        assert extract_answer_letter("Answer: A", "AB") == "A"
        assert extract_answer_letter("answer: B", "AB") == "B"
        assert extract_answer_letter("Final answer is A", "AB") == "A"
        assert extract_answer_letter("The answer is B", "AB") == "B"
        assert extract_answer_letter("answer:A", "AB") == "A"
        assert extract_answer_letter("ANSWER: B", "AB") == "B"

    def test_choice_formats(self):
        """Test various choice/selection formats."""
        assert extract_answer_letter("I choose A", "AB") == "A"
        assert extract_answer_letter("I pick B", "AB") == "B"
        assert extract_answer_letter("I select A", "AB") == "A"
        assert extract_answer_letter("Option B", "AB") == "B"
        assert extract_answer_letter("Choice A", "AB") == "A"

    def test_parenthetical_formats(self):
        """Test parenthetical answer formats."""
        assert extract_answer_letter("(A) is correct", "AB") == "A"
        assert extract_answer_letter("B is correct", "AB") == "B"
        assert extract_answer_letter("(A) is the right answer", "AB") == "A"
        assert extract_answer_letter("The correct answer is (B)", "AB") == "B"
        assert extract_answer_letter("(A)", "AB") == "A"
        assert extract_answer_letter("B)", "AB") == "B"

    def test_punctuated_formats(self):
        """Test punctuated answer formats."""
        assert extract_answer_letter("A.", "AB") == "A"
        assert extract_answer_letter("B:", "AB") == "B"
        assert extract_answer_letter("A. This is because...", "AB") == "A"
        assert extract_answer_letter("B: The reason is...", "AB") == "B"

    def test_standalone_answer(self):
        """Test standalone letter answers."""
        assert extract_answer_letter("A", "AB") == "A"
        assert extract_answer_letter("B", "AB") == "B"
        assert extract_answer_letter("  A  ", "AB") == "A"
        assert extract_answer_letter("\nB\n", "AB") == "B"

    def test_mcq_valid_letters(self):
        """Test MCQ format with ABCDE valid letters."""
        assert extract_answer_letter("Answer: C", "ABCDE") == "C"
        assert extract_answer_letter("I choose D", "ABCDE") == "D"
        assert extract_answer_letter("(E) is correct", "ABCDE") == "E"
        assert extract_answer_letter("E.", "ABCDE") == "E"

    def test_prefer_pattern(self):
        """Test 'prefer' pattern for preference tasks."""
        assert extract_answer_letter("I prefer A", "AB") == "A"
        assert extract_answer_letter("I prefer B", "AB") == "B"

    def test_invalid_letters(self):
        """Test that invalid letters are not extracted."""
        assert extract_answer_letter("Answer: C", "AB") is None
        assert extract_answer_letter("I choose Z", "ABCDE") is None
        assert extract_answer_letter("Answer: F", "ABCDE") is None
        assert extract_answer_letter("G is correct", "AB") is None

    def test_no_answer_found(self):
        """Test cases where no answer should be found."""
        assert extract_answer_letter("", "AB") is None
        assert extract_answer_letter("I'm not sure", "AB") is None
        assert extract_answer_letter("Both are good", "AB") is None
        assert extract_answer_letter("Neither A nor B", "AB") is None
        assert extract_answer_letter("Maybe it's one of them", "AB") is None

    def test_multiple_answers(self):
        """Test that first valid answer is returned when multiple present."""
        assert extract_answer_letter("First I thought B, but answer: A", "AB") == "A"
        assert extract_answer_letter("A or B? I choose A", "AB") == "A"
        assert extract_answer_letter("Not B. Answer: A", "AB") == "A"  # "Answer: A" pattern takes priority

    def test_case_insensitive(self):
        """Test case insensitive matching."""
        assert extract_answer_letter("answer: a", "AB") == "A"
        assert extract_answer_letter("ANSWER: b", "AB") == "B"
        assert extract_answer_letter("i choose a", "AB") == "A"
        assert extract_answer_letter("I CHOOSE B", "AB") == "B"

    def test_embedded_in_text(self):
        """Test extraction from longer text."""
        long_text = """
        After careful consideration of both responses, I believe that Response A
        provides a more comprehensive and accurate answer. Response B has some
        good points but lacks detail.
        
        Therefore, my answer: A
        """
        assert extract_answer_letter(long_text, "AB") == "A"

    def test_default_valid_letters(self):
        """Test default valid letters parameter."""
        assert extract_answer_letter("Answer: C") == "C"
        assert extract_answer_letter("Answer: E") == "E"
        assert extract_answer_letter("Answer: F") is None  # F not in default ABCDE

    def test_response_pattern(self):
        """Test 'Response A' format for preference domain."""
        assert extract_answer_letter("Response A", "AB") == "A"
        assert extract_answer_letter("The answer is response B.", "AB") == "B"


class TestScoreLetterChoice:
    """Test shared letter choice scoring functionality."""

    def test_mcq_scoring(self):
        """Test scoring with MCQ valid letters."""
        assert score_letter_choice("A", "Answer: A", "ABCDE") == 1.0
        assert score_letter_choice("B", "I choose B", "ABCDE") == 1.0
        assert score_letter_choice("C", "Answer: C", "ABCDE") == 1.0
        assert score_letter_choice("A", "Answer: B", "ABCDE") == 0.0

    def test_preference_scoring(self):
        """Test scoring with preference valid letters."""
        assert score_letter_choice("A", "Answer: A", "AB") == 1.0
        assert score_letter_choice("B", "I prefer B", "AB") == 1.0
        assert score_letter_choice("A", "Answer: B", "AB") == 0.0

    def test_case_insensitive(self):
        """Test case insensitive scoring."""
        assert score_letter_choice("a", "Answer: A", "AB") == 1.0
        assert score_letter_choice("B", "answer: b", "AB") == 1.0

    def test_no_answer_extracted(self):
        """Test when no answer can be extracted."""
        assert score_letter_choice("A", "I don't know", "AB") == 0.0
        assert score_letter_choice("B", "", "ABCDE") == 0.0

    def test_invalid_expected_answer(self):
        """Test validation of expected answer."""
        with pytest.raises(ValueError, match="Expected answer must be a non-empty string"):
            score_letter_choice("", "Answer: A", "AB")
        
        with pytest.raises(ValueError, match="Expected answer must be a non-empty string"):
            score_letter_choice(None, "Answer: A", "AB")
        
        with pytest.raises(ValueError, match="Expected answer must be a single letter"):
            score_letter_choice("AB", "Answer: A", "AB")
        
        with pytest.raises(ValueError, match="Expected answer must be a single letter"):
            score_letter_choice("123", "Answer: A", "AB")

    def test_invalid_expected_answer_not_in_valid(self):
        """Test when expected answer is not in valid letters."""
        with pytest.raises(ValueError, match="Expected answer must be a single letter from AB"):
            score_letter_choice("C", "Answer: C", "AB")
        
        with pytest.raises(ValueError, match="Expected answer must be a single letter from ABCDE"):  
            score_letter_choice("Z", "Answer: Z", "ABCDE")

    def test_custom_valid_letters(self):
        """Test with custom valid letter sets."""
        assert score_letter_choice("X", "Answer: X", "XYZ") == 1.0
        assert score_letter_choice("Y", "I choose Y", "XYZ") == 1.0
        assert score_letter_choice("X", "Answer: Y", "XYZ") == 0.0
        
        with pytest.raises(ValueError, match="Expected answer must be a single letter from XYZ"):
            score_letter_choice("A", "Answer: A", "XYZ")