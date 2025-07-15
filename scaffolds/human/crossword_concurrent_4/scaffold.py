import logging
import re
import json
import math
from llm_executor import execute_llm


def parse_crossword_input(input_string):
    """Parse the input crossword puzzle into grid and clues"""
    lines = input_string.strip().split("\n")

    # Parse grid
    grid = []
    line_idx = 0
    while line_idx < len(lines):
        line = lines[line_idx].strip()
        if not line or line.startswith("Across:") or line.startswith("Down:"):
            break
        grid.append(line.split())
        line_idx += 1

    # Parse clues
    across_clues = {}
    down_clues = {}

    current_section = None
    for i in range(line_idx, len(lines)):
        line = lines[i].strip()
        if line.startswith("Across:"):
            current_section = "across"
        elif line.startswith("Down:"):
            current_section = "down"
        elif line and current_section:
            match = re.match(r"\s*(\d+)\.\s*(.+)", line)
            if match:
                clue_num = int(match.group(1))
                clue_text = match.group(2).strip()
                if current_section == "across":
                    across_clues[clue_num] = clue_text
                else:
                    down_clues[clue_num] = clue_text

    return grid, across_clues, down_clues


def find_clue_position(clue_num, grid, direction):
    """Find the starting position of a clue in the grid based on crossword numbering"""
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    current_num = 1

    for row in range(height):
        for col in range(width):
            if grid[row][col] == ".":
                continue

            starts_across = (
                (col == 0 or grid[row][col - 1] == ".")
                and col + 1 < width
                and grid[row][col + 1] != "."
            )
            starts_down = (
                (row == 0 or grid[row - 1][col] == ".")
                and row + 1 < height
                and grid[row + 1][col] != "."
            )

            if starts_across or starts_down:
                if current_num == clue_num:
                    return (row, col)
                current_num += 1

    return None


def get_clue_length(clue_num, grid, direction):
    """Get the length of a clue based on grid structure"""
    pos = find_clue_position(clue_num, grid, direction)
    if pos is None:
        return None

    row, col = pos
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0

    if direction == "across":
        length = 0
        for c in range(col, width):
            if grid[row][c] == ".":
                break
            length += 1
        return length
    else:  # down
        length = 0
        for r in range(row, height):
            if grid[r][col] == ".":
                break
            length += 1
        return length


def get_word_positions(clue_num, grid, direction):
    """Get all grid positions occupied by a word"""
    pos = find_clue_position(clue_num, grid, direction)
    if pos is None:
        return []

    row, col = pos
    positions = []

    if direction == "across":
        c = col
        while c < len(grid[0]) and grid[row][c] != ".":
            positions.append((row, c))
            c += 1
    else:  # down
        r = row
        while r < len(grid) and grid[r][col] != ".":
            positions.append((r, col))
            r += 1

    return positions


def binomial_prob(N, M, p=1 / 26):
    q = 1 - p
    return math.comb(N, M) * (p**M) * (q ** (N - M))


def coincidence_prob(target_word: str, guess_letters: str) -> float:
    N = len(target_word)
    M = sum(t == g for t, g in zip(target_word.upper(), guess_letters.upper()))
    p_M = binomial_prob(N, M)

    # Compute all probabilities
    probs = [binomial_prob(N, k) for k in range(N + 1)]

    # Sum probs for all k with probability <= p_M
    result = sum(prob for prob in probs if prob <= p_M)
    return result


def get_crossing_letters(
    word_positions, locked_words, first_valid_words, grid, direction
):
    """Get the letters from crossing words at each position"""
    crossing_letters = []
    opposite_dir = "down" if direction == "across" else "across"

    for pos in word_positions:
        row, col = pos
        letter = "-"

        # Find which opposite-direction word crosses at this position
        for clue_num in list(locked_words.get(opposite_dir, {}).keys()) + list(
            first_valid_words.get(opposite_dir, {}).keys()
        ):
            clue_positions = get_word_positions(clue_num, grid, opposite_dir)
            if pos in clue_positions:
                # Found the crossing word
                if clue_num in locked_words.get(opposite_dir, {}):
                    word = locked_words[opposite_dir][clue_num]
                elif clue_num in first_valid_words.get(opposite_dir, {}):
                    word = first_valid_words[opposite_dir][clue_num]
                else:
                    continue

                # Find which letter in the word corresponds to this position
                idx = clue_positions.index(pos)
                if idx < len(word):
                    letter = word[idx]
                break

        crossing_letters.append(letter)

    return "".join(crossing_letters)


def elicit_all_answers(across_clues, down_clues, grid):
    """Elicit up to 5 answers for each clue in a single LLM call"""
    # Prepare clue data
    all_clues = {}

    for clue_num, clue_text in across_clues.items():
        length = get_clue_length(clue_num, grid, "across")
        if length:
            all_clues[f"across_{clue_num}"] = {
                "direction": "across",
                "number": clue_num,
                "clue": clue_text,
                "length": length,
            }

    for clue_num, clue_text in down_clues.items():
        length = get_clue_length(clue_num, grid, "down")
        if length:
            all_clues[f"down_{clue_num}"] = {
                "direction": "down",
                "number": clue_num,
                "clue": clue_text,
                "length": length,
            }

    logging.info(f"Eliciting answers for {len(all_clues)} clues")

    prompt = f"""You are solving a crossword puzzle. For each clue, provide up to 5 possible answers, ordered from most to least likely.

Each answer must:
1. Be exactly the specified length
2. Be a real English word or phrase
3. Make sense as an answer to the clue

Return a JSON object where keys match the input keys and values are objects with:
- "answers": A list of up to 5 answers, each in uppercase with spaces between letters (e.g., "P A R I S")

If you can't think of any valid answers for a clue, return an empty list.

Example input:
{{
    "across_1": {{
        "direction": "across",
        "number": 1,
        "clue": "Capital of France",
        "length": 5
    }}
}}

Example output:
{{
    "across_1": {{
        "answers": ["P A R I S", "L Y O N S", "T O U R S", "N I C E S", "L I L L E"]
    }}
}}

Clues:
{json.dumps(all_clues, indent=2)}

Return ONLY the JSON object."""

    response = execute_llm(prompt)

    # Extract JSON from response
    json_match = re.search(r"\{[^{}]*\{[^{}]*\}[^{}]*\}", response, re.DOTALL)
    if json_match:
        results = json.loads(json_match.group())
    else:
        results = json.loads(response)

    # Process results
    candidates = {"across": {}, "down": {}}

    for key, result in results.items():
        if isinstance(result, dict) and "answers" in result:
            parts = key.split("_")
            if len(parts) == 2:
                direction = parts[0]
                clue_num = int(parts[1])

                # Filter valid answers by length
                expected_length = all_clues[key]["length"]
                valid_answers = []

                for answer_str in result["answers"]:
                    answer = "".join(answer_str.split()).upper()
                    if len(answer) == expected_length:
                        valid_answers.append(answer)
                    else:
                        logging.debug(
                            f"Skipping {direction} {clue_num} answer '{answer}' - wrong length"
                        )

                if valid_answers:
                    candidates[direction][clue_num] = valid_answers
                    logging.debug(
                        f"{direction} {clue_num}: {len(valid_answers)} valid answers"
                    )

    return candidates


def get_first_valid_words(candidates):
    """Extract the first valid word for each clue"""
    first_valid = {"across": {}, "down": {}}

    for direction in ["across", "down"]:
        for clue_num, answers in candidates[direction].items():
            if answers:
                first_valid[direction][clue_num] = answers[0]

    return first_valid


def calculate_all_probabilities(
    candidates, locked_words, first_valid_words, grid
):
    """Calculate coincidence probabilities for all candidate words and return sorted list"""
    all_probabilities = []

    for direction in ["across", "down"]:
        for clue_num, answer_list in candidates[direction].items():
            if clue_num in locked_words.get(direction, {}):
                continue  # Skip already locked words

            positions = get_word_positions(clue_num, grid, direction)

            for answer in answer_list:
                crossing_letters = get_crossing_letters(
                    positions, locked_words, first_valid_words, grid, direction
                )
                prob = coincidence_prob(answer, crossing_letters)
                all_probabilities.append(
                    {
                        "direction": direction,
                        "clue_num": clue_num,
                        "answer": answer,
                        "probability": prob,
                        "crossing_letters": crossing_letters,
                        "positions": positions,
                    }
                )

                logging.debug(
                    f"{direction} {clue_num} '{answer}' vs '{crossing_letters}': "
                    f"p={prob:.6f}"
                )

    # Sort by probability (ascending - least likely coincidence first)
    all_probabilities.sort(key=lambda x: x["probability"])
    return all_probabilities


def try_lock_next_word(sorted_probabilities, locked_words, first_valid_words, grid):
    """Try to lock in the next word with lowest probability that doesn't conflict"""
    for prob_info in sorted_probabilities:
        direction = prob_info["direction"]
        clue_num = prob_info["clue_num"]
        answer = prob_info["answer"]
        positions = prob_info["positions"]

        # Skip if already locked
        if clue_num in locked_words.get(direction, {}):
            continue

        # Check for conflicts with existing locked words
        conflict = False
        conflicting_word = None

        for i, pos in enumerate(positions):
            if i >= len(answer):
                break

            # Check opposite direction locked words
            opposite_dir = "down" if direction == "across" else "across"
            for other_num, other_answer in locked_words.get(opposite_dir, {}).items():
                other_positions = get_word_positions(other_num, grid, opposite_dir)
                if pos in other_positions:
                    idx = other_positions.index(pos)
                    if idx < len(other_answer) and other_answer[idx] != answer[i]:
                        conflict = True
                        conflicting_word = (opposite_dir, other_num, other_answer)
                        break
            if conflict:
                break

        if conflict:
            # Compare probabilities to decide which to keep
            opp_dir, opp_num, opp_answer = conflicting_word

            # Get crossing letters for the conflicting word
            opp_positions = get_word_positions(opp_num, grid, opp_dir)
            opp_crossing = get_crossing_letters(
                opp_positions, locked_words, first_valid_words, grid, opp_dir
            )
            opp_prob = coincidence_prob(opp_answer, opp_crossing)

            logging.debug(
                f"Conflict: {direction} {clue_num} '{answer}' (p={prob_info['probability']:.6f}) "
                f"vs {opp_dir} {opp_num} '{opp_answer}' (p={opp_prob:.6f})"
            )

            if prob_info["probability"] < opp_prob:
                # Current word is less likely to be coincidence, so keep it
                logging.info(f"Unlocking {opp_dir} {opp_num} due to conflict")
                del locked_words[opp_dir][opp_num]

                if direction not in locked_words:
                    locked_words[direction] = {}
                locked_words[direction][clue_num] = answer
                logging.info(
                    f"Locked in {direction} {clue_num}: {answer} (p={prob_info['probability']:.6f})"
                )
                return True
            else:
                logging.debug(f"Keeping existing {opp_dir} {opp_num}")
                continue  # Try next word
        else:
            # No conflict, lock it in
            if direction not in locked_words:
                locked_words[direction] = {}
            locked_words[direction][clue_num] = answer
            logging.info(
                f"Locked in {direction} {clue_num}: {answer} (p={prob_info['probability']:.6f})"
            )
            return True

    return False  # No word could be locked


def build_completed_grid(grid, locked_words, first_valid_words, candidates):
    """Build the final grid, using lowest probability words for remaining letters"""
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    completed = [row[:] for row in grid]  # Deep copy

    # First fill in all locked words
    for direction in ["across", "down"]:
        for clue_num, answer in locked_words.get(direction, {}).items():
            positions = get_word_positions(clue_num, grid, direction)
            for i, (row, col) in enumerate(positions):
                if i < len(answer):
                    completed[row][col] = answer[i]

    # For any remaining - positions, use the word with lowest coincidence probability
    for row in range(height):
        for col in range(width):
            if grid[row][col] != "." and completed[row][col] == "-":
                # Find all words that pass through this position
                best_letter = "-"
                best_prob = 1.0

                for direction in ["across", "down"]:
                    for clue_num, answer_list in candidates[direction].items():
                        positions = get_word_positions(clue_num, grid, direction)
                        if (row, col) in positions:
                            idx = positions.index((row, col))

                            # Try all candidate answers for this clue
                            for answer in answer_list:
                                if idx < len(answer):
                                    # Calculate crossing letters for this specific answer
                                    # Temporarily use this answer for calculation
                                    temp_first_valid = first_valid_words.copy()
                                    temp_first_valid[direction][clue_num] = answer

                                    crossing_letters = get_crossing_letters(
                                        positions,
                                        locked_words,
                                        temp_first_valid,
                                        grid,
                                        direction,
                                    )
                                    prob = coincidence_prob(answer, crossing_letters)

                                    if prob < best_prob:
                                        best_prob = prob
                                        best_letter = answer[idx]
                                        logging.debug(
                                            f"Position ({row},{col}): {direction} {clue_num} '{answer}' "
                                            f"gives letter '{best_letter}' with prob {prob:.6f}"
                                        )

                if best_letter == "-":
                    # This shouldn't happen if we have valid candidates
                    logging.warning(
                        f"No letter found for position ({row},{col}), using 'E'"
                    )
                    best_letter = "E"

                completed[row][col] = best_letter

    return completed


def build_grid_for_logging(grid, locked_words):
    """Build grid showing only locked words (with - for unlocked positions)"""
    completed = [row[:] for row in grid]  # Deep copy

    # Fill in only locked words
    for direction in ["across", "down"]:
        for clue_num, answer in locked_words.get(direction, {}).items():
            positions = get_word_positions(clue_num, grid, direction)
            for i, (row, col) in enumerate(positions):
                if i < len(answer):
                    completed[row][col] = answer[i]

    return completed


def log_grid(grid, message=""):
    """Log the current state of the grid"""
    if message:
        logging.info(message)
    for row in grid:
        logging.info("  " + " ".join(row))


def process_input(input_string: str) -> str:
    grid, across_clues, down_clues = parse_crossword_input(input_string)
    logging.info(f"Parsed grid of size {len(grid)}x{len(grid[0]) if grid else 0}")
    logging.info(
        f"Found {len(across_clues)} across clues and {len(down_clues)} down clues"
    )

    # Step 1: Elicit all answers
    candidates = elicit_all_answers(across_clues, down_clues, grid)

    # Step 2: Get first valid words
    first_valid_words = get_first_valid_words(candidates)
    locked_words = {}

    # Step 3: Search process - lock words one at a time in order of probability
    iteration = 0
    total_locked = 0
    
    while True:
        iteration += 1
        logging.info(f"\n--- Search iteration {iteration} ---")

        # Calculate probabilities for all unlocked words
        sorted_probabilities = calculate_all_probabilities(
            candidates, locked_words, first_valid_words, grid
        )

        # Try to lock the next best word
        if try_lock_next_word(sorted_probabilities, locked_words, first_valid_words, grid):
            total_locked += 1
            # Log grid after each new lock (with - for unlocked)
            temp_grid = build_grid_for_logging(grid, locked_words)
            log_grid(temp_grid, f"\nGrid after locking word #{total_locked}:")
        else:
            logging.info("No more words can be locked")
            break

    # Step 5: Build final grid
    completed_grid = build_completed_grid(
        grid, locked_words, first_valid_words, candidates
    )

    # Format output
    result = []

    # Add completed grid
    for row in completed_grid:
        result.append(" ".join(row))

    result.append("")  # Empty line separator

    # Add across answers
    if locked_words.get("across") or first_valid_words.get("across"):
        result.append("Across:")
        all_across = {}

        # Collect answers from completed grid
        for clue_num in across_clues.keys():
            positions = get_word_positions(clue_num, grid, "across")
            if positions:
                answer = ""
                for row, col in positions:
                    if row < len(completed_grid) and col < len(completed_grid[0]):
                        answer += completed_grid[row][col]
                if answer and "-" not in answer:
                    all_across[clue_num] = answer

        for clue_num in sorted(all_across.keys()):
            result.append(f"  {clue_num}. {all_across[clue_num]}")

    # Add down answers
    if locked_words.get("down") or first_valid_words.get("down"):
        result.append("\nDown:")
        all_down = {}

        # Collect answers from completed grid
        for clue_num in down_clues.keys():
            positions = get_word_positions(clue_num, grid, "down")
            if positions:
                answer = ""
                for row, col in positions:
                    if row < len(completed_grid) and col < len(completed_grid[0]):
                        answer += completed_grid[row][col]
                if answer and "-" not in answer:
                    all_down[clue_num] = answer

        for clue_num in sorted(all_down.keys()):
            result.append(f"  {clue_num}. {all_down[clue_num]}")

    logging.info(
        f"\nFinal: {len(locked_words.get('across', {}))} across, {len(locked_words.get('down', {}))} down locked"
    )

    return "\n".join(result)
