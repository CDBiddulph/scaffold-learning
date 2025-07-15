#!/usr/bin/env python3
import logging
import re
import json
import time
from collections import defaultdict
from typing import List, Tuple, Dict, Optional
from llm_executor import execute_llm

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Global cache for LLM responses
LLM_CACHE = {}

# Start time for timeout tracking
START_TIME = time.time()
TIMEOUT_SECONDS = 290  # 4:50 to leave buffer


class WordCandidate:
    def __init__(self, word: str, probability: float):
        self.word = word
        self.probability = probability

    def __repr__(self):
        return f"{self.word} ({self.probability:.2f}%)"


def check_timeout():
    """Check if we're approaching the 5-minute timeout."""
    elapsed = time.time() - START_TIME
    if elapsed > TIMEOUT_SECONDS:
        logging.warning(f"Timeout! Elapsed: {elapsed:.1f}s / {TIMEOUT_SECONDS}s")
        return True
    elif elapsed > TIMEOUT_SECONDS * 0.8:
        logging.warning(
            f"Approaching timeout: {elapsed:.1f}s / {TIMEOUT_SECONDS}s ({TIMEOUT_SECONDS - elapsed:.1f}s remaining)"
        )
    return False


def normalize_probabilities(candidates: List[Dict]) -> List[WordCandidate]:
    """Normalize probabilities to sum to 100%."""
    total = sum(c.get("probability", 0) for c in candidates)
    if total == 0:
        return []

    normalized = []
    for c in candidates:
        word = c.get("word", "").upper()
        prob = (c.get("probability", 0) / total) * 100
        if word and word != "NONE":
            normalized.append(WordCandidate(word, prob))

    return sorted(normalized, key=lambda x: x.probability, reverse=True)


def get_word_candidates(
    clue_text: str, clue_num: int, direction: str, length: int, pattern: str
) -> List[WordCandidate]:
    """Get top 5 word candidates with probabilities from LLM."""
    cache_key = (clue_text, pattern, length)

    # Check cache first
    if cache_key in LLM_CACHE:
        cached_candidates = LLM_CACHE[cache_key]
        logging.info(f"Cache hit for {clue_text}: {cached_candidates}")
        # Verify cached candidates still match current pattern
        valid_candidates = []
        for candidate in cached_candidates:
            if re.fullmatch(pattern.replace("-", "[A-Z]"), candidate.word):
                valid_candidates.append(candidate)
        if valid_candidates:
            logging.info(f"Using cached candidates for {clue_num} {direction}")
            return valid_candidates

    prompt = f"""Crossword Clue: {clue_text} ({clue_num} {'Across' if direction == 'across' else 'Down'})
Length: {length}
Pattern: {pattern}

Provide the top 5 most likely answers with probability percentages.
Respond ONLY with a JSON array in this exact format:
[
  {{"word": "ANSWER1", "probability": 45.50}},
  {{"word": "ANSWER2", "probability": 25.25}},
  {{"word": "ANSWER3", "probability": 15.00}},
  {{"word": "ANSWER4", "probability": 10.00}},
  {{"word": "OTHER", "probability": 4.25}}
]

Rules:
- Each word must be exactly {length} letters
- Words must match the pattern (- means unknown letter)
- Include "OTHER" as the last entry for all other possibilities
- Probabilities should sum to approximately 100
- If no good matches exist, return [{{"word": "NONE", "probability": 100}}]"""

    system_prompt = "You are a crossword solving expert. Analyze the clue and pattern, then provide your top 5 answers with probabilities in JSON format."

    if check_timeout():
        logging.warning("Approaching timeout, using quick guess")
        return []

    logging.info(
        f"Getting candidates for {clue_num} {direction}: {clue_text} ({pattern})"
    )

    try:
        response_str = execute_llm(prompt, system_prompt=system_prompt)

        # Extract JSON from response
        json_match = re.search(r"\[\s*\{.*?\}\s*\]", response_str, re.DOTALL)
        if not json_match:
            logging.warning(
                f"Could not extract JSON from response for {clue_num} {direction}"
            )
            return []

        candidates_data = json.loads(json_match.group())
        candidates = normalize_probabilities(candidates_data)
        logging.info(f"LLM returned {len(candidates)} candidates: {candidates}")

        # Cache the results
        LLM_CACHE[cache_key] = candidates

        return candidates

    except Exception as e:
        logging.error(f"Error getting candidates for {clue_num} {direction}: {e}")
        return []


def resolve_conflict(
    existing_word: str,
    existing_clue: str,
    existing_prob: float,
    new_word: str,
    new_clue: str,
    new_prob: float,
) -> str:
    """Ask LLM to resolve conflicts between crossing words."""
    if check_timeout():
        # If timeout approaching, go with higher probability
        return new_word if new_prob > existing_prob else existing_word

    prompt = f"""Two crossword answers conflict at their intersection:

1. "{existing_word}" for clue "{existing_clue}"
2. "{new_word}" for clue "{new_clue}"

Which word is more likely to be correct?
Respond with ONLY the number (1 or 2) of the more plausible answer."""

    system_prompt = (
        "You are a crossword expert resolving conflicts between crossing words."
    )

    try:
        response = execute_llm(prompt, system_prompt=system_prompt)
        if "1" in response:
            return existing_word
        elif "2" in response:
            return new_word
        else:
            # Default to higher probability
            return new_word if new_prob > existing_prob else existing_word
    except:
        return new_word if new_prob > existing_prob else existing_word


def get_crossing_info(slot, grid, numbering_grid, all_slots_dict):
    """Get information about words that cross this slot."""
    _, row, col, length, _, direction = slot
    crossing_info = []

    for i in range(length):
        if direction == "across":
            r, c = row, col + i
            # Check for down word at this position
            for num, slots in all_slots_dict.items():
                for s in slots:
                    if s[5] == "down" and s[1] <= r < s[1] + s[3] and s[2] == c:
                        crossing_info.append((r, c, s))
                        break
        else:  # down
            r, c = row + i, col
            # Check for across word at this position
            for num, slots in all_slots_dict.items():
                for s in slots:
                    if s[5] == "across" and s[1] == r and s[2] <= c < s[2] + s[3]:
                        crossing_info.append((r, c, s))
                        break

    return crossing_info


def clear_crossing_letters(slot, grid, numbering_grid, all_slots_dict):
    """Clear all letters that cross with this slot."""
    crossing_info = get_crossing_info(slot, grid, numbering_grid, all_slots_dict)
    cleared_positions = []

    for r, c, crossing_slot in crossing_info:
        if grid[r][c].isalpha():
            grid[r][c] = "-"
            cleared_positions.append((r, c))
            logging.info(
                f"Cleared letter at ({r}, {c}) crossing with {slot[0]} {slot[5]}"
            )

    return cleared_positions


def parse_input(input_string):
    """Parses the input string into a grid and clue lists."""
    lines = input_string.splitlines()
    grid_lines = []
    i = 0
    while i < len(lines) and (
        lines[i].strip() == "" or any(c in lines[i] for c in [".", "-"])
    ):
        stripped = lines[i].strip()
        if stripped:
            # Standardize empty cells to just '-'
            grid_lines.append(re.sub(r"\s+", " ", stripped))
        i += 1

    # Extract clues, handling potential empty lines between them
    across_clues, down_clues = [], []
    current_clues = None
    for line in lines[i:]:
        stripped_line = line.strip()
        if not stripped_line:
            continue
        if stripped_line.startswith("Across:"):
            current_clues = across_clues
            continue
        elif stripped_line.startswith("Down:"):
            current_clues = down_clues
            continue

        if current_clues is not None:
            match = re.match(r"^\s*(\d+)\.\s*(.*)$", stripped_line)
            if match:
                clue_num = int(match.group(1))
                clue_text = match.group(2).strip()
                current_clues.append((clue_num, clue_text))

    grid = []
    for line in grid_lines:
        # Use a consistent character for empty, fillable cells
        row = [char if char != " " else "-" for char in line.split(" ")]
        grid.append(row)

    return grid, across_clues, down_clues


def compute_numbering(grid):
    """Computes the numbering for the crossword grid slots."""
    if not grid or not grid[0]:
        return [], [], []
    rows, cols = len(grid), len(grid[0])
    numbering_grid = [[None] * cols for _ in range(rows)]
    next_number = 1
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == ".":
                continue
            is_across_start = (c == 0 or grid[r][c - 1] == ".") and (
                c < cols - 1 and grid[r][c + 1] != "."
            )
            is_down_start = (r == 0 or grid[r - 1][c] == ".") and (
                r < rows - 1 and grid[r + 1][c] != "."
            )
            if is_across_start or is_down_start:
                numbering_grid[r][c] = next_number
                next_number += 1

    across_slots, down_slots = [], []
    for r in range(rows):
        for c in range(cols):
            num = numbering_grid[r][c]
            if num is None:
                continue

            # Check for across word start
            if (c == 0 or grid[r][c - 1] == ".") and (
                c < cols - 1 and grid[r][c + 1] != "."
            ):
                length = 0
                cc = c
                while cc < cols and grid[r][cc] != ".":
                    length += 1
                    cc += 1
                across_slots.append((num, r, c, length))

            # Check for down word start
            if (r == 0 or grid[r - 1][c] == ".") and (
                r < rows - 1 and grid[r + 1][c] != "."
            ):
                length = 0
                rr = r
                while rr < rows and grid[rr][c] != ".":
                    length += 1
                    rr += 1
                down_slots.append((num, r, c, length))

    return numbering_grid, across_slots, down_slots


def get_pattern(slot, grid):
    """Gets the current pattern of a slot (e.g., 'A-P--E')."""
    _, row, col, length, _, direction = slot
    pattern = ""
    if direction == "across":
        for j in range(length):
            pattern += grid[row][col + j]
    else:  # direction == "down"
        for i in range(length):
            pattern += grid[row + i][col]
    return pattern


def update_grid(slot, word, grid):
    """Updates the grid with a new word for a given slot."""
    _, row, col, length, _, direction = slot
    if direction == "across":
        for j, letter in enumerate(word):
            if j < length:
                grid[row][col + j] = letter
    else:  # direction == "down"
        for i, letter in enumerate(word):
            if i < length:
                grid[row + i][col] = letter


def extract_word_from_slot(slot, grid):
    """Extracts the word from a slot in the current grid."""
    return get_pattern(slot, grid)


def probabilistic_solver(original_grid, across_clues, down_clues):
    """Solves crossword using probability-based word selection."""
    grid = [row[:] for row in original_grid]
    numbering_grid, across_slots, down_slots = compute_numbering(original_grid)
    across_slot_dict = {slot[0]: slot for slot in across_slots}
    down_slot_dict = {slot[0]: slot for slot in down_slots}

    across_slots_with_info = [
        (clue_num, *across_slot_dict[clue_num][1:], clue_text, "across")
        for clue_num, clue_text in across_clues
        if clue_num in across_slot_dict
    ]
    down_slots_with_info = [
        (clue_num, *down_slot_dict[clue_num][1:], clue_text, "down")
        for clue_num, clue_text in down_clues
        if clue_num in down_slot_dict
    ]

    all_slots = across_slots_with_info + down_slots_with_info
    all_slots_dict = defaultdict(list)
    for slot in all_slots:
        all_slots_dict[slot[0]].append(slot)

    # Track word probabilities for conflict resolution
    word_probabilities = {}
    max_iterations = 5

    for iteration in range(1, max_iterations + 1):
        if check_timeout():
            logging.warning("Approaching timeout, finishing current iteration")
            break

        logging.info(f"=== Iteration {iteration}/{max_iterations} ===")

        filled_count = sum(1 for row in grid for cell in row if cell.isalpha())
        total_count = sum(1 for row in grid for cell in row if cell != ".")
        logging.info(f"Filled {filled_count} of {total_count} cells")

        # Phase 1: Get all candidates for all slots
        all_candidates = {}
        for slot in all_slots:
            pattern = get_pattern(slot, grid)
            if "-" not in pattern:
                continue

            clue_num, row, col, length, clue_text, direction = slot
            candidates = get_word_candidates(
                clue_text, clue_num, direction, length, pattern
            )

            if candidates:
                all_candidates[slot] = candidates
                # Check if any past guesses are now confirmed by new letters
                for candidate in candidates:
                    cache_key = (clue_text, "-" * length, length)
                    if cache_key in LLM_CACHE:
                        old_pattern = "-" * length
                        if pattern != old_pattern and re.fullmatch(
                            pattern.replace("-", "[A-Z]"), candidate.word
                        ):
                            # Boost confidence if new letters confirm old guess
                            candidate.probability *= 1.5
                            logging.info(
                                f"Boosted confidence for {candidate.word} due to confirming letters"
                            )

        # Phase 2: Fill words by probability order
        candidate_queue = []
        for slot, candidates in all_candidates.items():
            for candidate in candidates:
                candidate_queue.append((candidate.probability, slot, candidate))

        candidate_queue.sort(reverse=True, key=lambda x: x[0])

        for prob, slot, candidate in candidate_queue:
            pattern = get_pattern(slot, grid)
            if "-" not in pattern:
                continue

            if not re.fullmatch(pattern.replace("-", "[A-Z]"), candidate.word):
                logging.info(
                    f"Pattern mismatch: {candidate.word} doesn't match {pattern}"
                )
                continue

            clue_num, row, col, length, clue_text, direction = slot

            # Check for conflicts
            has_conflict = False
            crossing_info = get_crossing_info(
                slot, grid, numbering_grid, all_slots_dict
            )

            for r, c, crossing_slot in crossing_info:
                if direction == "across":
                    new_letter = candidate.word[c - col]
                else:  # down
                    new_letter = candidate.word[r - row]

                if grid[r][c].isalpha() and grid[r][c] != new_letter:
                    logging.info(
                        f"Conflict at ({r}, {c}): existing {grid[r][c]} vs. new {new_letter} from {candidate.word}"
                    )
                    # Conflict detected
                    if candidate.probability > 75:
                        # High confidence - resolve conflict
                        existing_word = extract_word_from_slot(crossing_slot, grid)
                        existing_prob = word_probabilities.get(
                            (crossing_slot[0], crossing_slot[5]), 50
                        )

                        winner = resolve_conflict(
                            existing_word,
                            crossing_slot[4],
                            existing_prob,
                            candidate.word,
                            clue_text,
                            candidate.probability,
                        )

                        if winner == candidate.word:
                            logging.info(
                                f"Conflict resolved in favor of {candidate.word}"
                            )
                        else:
                            has_conflict = True
                            break
                    else:
                        # Low confidence - skip
                        has_conflict = True
                        break

            if not has_conflict:
                logging.info(
                    f"Placing {candidate.word} ({candidate.probability:.1f}%) at {clue_num} {direction} - pattern was {pattern}"
                )
                update_grid(slot, candidate.word, grid)
                word_probabilities[(clue_num, direction)] = candidate.probability

        # Phase 3: Clear crossing letters for slots with no good candidates
        for slot in all_slots:
            pattern = get_pattern(slot, grid)
            if "-" not in pattern:
                continue

            if slot not in all_candidates or not all_candidates[slot]:
                # No good candidates - clear crossing letters
                clue_num, _, _, _, _, direction = slot
                logging.info(
                    f"No good candidates for {clue_num} {direction}, clearing crossing letters"
                )
                clear_crossing_letters(slot, grid, numbering_grid, all_slots_dict)
                words_placed = sum(
                    1 for slot in all_slots if "-" not in get_pattern(slot, grid)
                )
                logging.info(
                    f"Iteration {iteration} complete: {words_placed}/{len(all_slots)} words placed"
                )

    # Final cleanup if timeout approaching
    if check_timeout():
        logging.warning("Timeout approaching, making final guesses")
        for slot in all_slots:
            pattern = get_pattern(slot, grid)
            if "-" in pattern:
                # Try one more quick guess
                clue_num, row, col, length, clue_text, direction = slot
                candidates = get_word_candidates(
                    clue_text, clue_num, direction, length, pattern
                )
                if candidates and candidates[0].probability > 50:
                    update_grid(slot, candidates[0].word, grid)

    # Format output
    output_lines = [" ".join(row) for row in grid]
    output_lines.append("\nAcross:")

    final_across_words = {
        s[0]: extract_word_from_slot(s, grid).replace("-", " ")
        for s in across_slots_with_info
    }
    final_down_words = {
        s[0]: extract_word_from_slot(s, grid).replace("-", " ")
        for s in down_slots_with_info
    }

    for clue_num, _ in across_clues:
        word = final_across_words.get(
            clue_num, " " * (across_slot_dict.get(clue_num, [0] * 4)[3])
        )
        output_lines.append(f"  {clue_num}. {word}")

    output_lines.append("\nDown:")
    for clue_num, _ in down_clues:
        word = final_down_words.get(
            clue_num, " " * (down_slot_dict.get(clue_num, [0] * 4)[3])
        )
        output_lines.append(f"  {clue_num}. {word}")

    return "\n".join(output_lines)


def process_input(input_string: str) -> str:
    """Main function to process the input string and solve the puzzle."""
    global START_TIME
    START_TIME = time.time()

    logging.info("Processing crossword puzzle...")
    try:
        original_grid, across_clues, down_clues = parse_input(input_string)
        if not original_grid or not across_clues or not down_clues:
            logging.error("Failed to parse input into grid and clues.")
            return "Error: Invalid input format."
        return probabilistic_solver(original_grid, across_clues, down_clues)
    except Exception as e:
        logging.error(f"Error processing input: {str(e)}", exc_info=True)
        return "Error: Failed to solve the crossword puzzle due to an unexpected error."
