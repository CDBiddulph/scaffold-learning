import logging
import re
import json
import math
import random
from llm_executor import execute_llm


MAX_ITERATIONS = 10
USE_RATING = False
USE_REASONING = False


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


def is_word_fully_constrained(clue_num, direction, grid, locked_words):
    """Check if a word is fully constrained (all crossing words are locked)"""
    if not locked_words:
        return False

    positions = get_word_positions(clue_num, grid, direction)
    opposite_dir = "down" if direction == "across" else "across"

    for pos in positions:
        # Check if any word in the opposite direction crosses this position
        crossing_word_found = False
        for other_clue_num in locked_words.get(opposite_dir, {}):
            other_positions = get_word_positions(other_clue_num, grid, opposite_dir)
            if pos in other_positions:
                crossing_word_found = True
                break

        # If no crossing word is locked at this position, word is not fully constrained
        if not crossing_word_found:
            return False

    return True


def elicit_all_answers(
    across_clues, down_clues, grid, locked_words=None, previous_candidates=None
):
    """Elicit up to 5 answers for each clue in a single LLM call"""
    # Collect clues that need elicitation (not fully constrained)
    clue_data_list = []
    reused_candidates = {"across": {}, "down": {}}

    for clue_num, clue_text in across_clues.items():
        length = get_clue_length(clue_num, grid, "across")
        if length:
            # Check if word is fully constrained
            if (
                locked_words
                and previous_candidates
                and is_word_fully_constrained(clue_num, "across", grid, locked_words)
            ):
                # Reuse previous candidates
                if clue_num in previous_candidates["across"]:
                    reused_candidates["across"][clue_num] = previous_candidates[
                        "across"
                    ][clue_num]
                    logging.debug(
                        f"Reusing candidates for fully constrained across {clue_num}"
                    )
                continue

            clue_info = {
                "clue": clue_text,
                "length": length,
            }

            # Add crossing letters if we have locked words
            if locked_words:
                positions = get_word_positions(clue_num, grid, "across")
                crossing_letters = get_crossing_letters(
                    positions, locked_words, {}, grid, "across"
                )
                if crossing_letters and crossing_letters != "-" * len(crossing_letters):
                    clue_info["crossing_letters"] = crossing_letters

            clue_data_list.append((f"across_{clue_num}", clue_info))

    for clue_num, clue_text in down_clues.items():
        length = get_clue_length(clue_num, grid, "down")
        if length:
            # Check if word is fully constrained
            if (
                locked_words
                and previous_candidates
                and is_word_fully_constrained(clue_num, "down", grid, locked_words)
            ):
                # Reuse previous candidates
                if clue_num in previous_candidates["down"]:
                    reused_candidates["down"][clue_num] = previous_candidates["down"][
                        clue_num
                    ]
                    logging.debug(
                        f"Reusing candidates for fully constrained down {clue_num}"
                    )
                continue

            clue_info = {
                "clue": clue_text,
                "length": length,
            }

            # Add crossing letters if we have locked words
            if locked_words:
                positions = get_word_positions(clue_num, grid, "down")
                crossing_letters = get_crossing_letters(
                    positions, locked_words, {}, grid, "down"
                )
                if crossing_letters and crossing_letters != "-" * len(crossing_letters):
                    clue_info["crossing_letters"] = crossing_letters

            clue_data_list.append((f"down_{clue_num}", clue_info))

    # Randomize the order of clues that need elicitation
    random.shuffle(clue_data_list)

    # Build the dictionary in randomized order
    all_clues = {}
    for key, clue_info in clue_data_list:
        all_clues[key] = clue_info

    logging.info(
        f"Eliciting answers for {len(all_clues)} clues (reused {len(reused_candidates['across'])} across, {len(reused_candidates['down'])} down)"
    )

    # Determine if this is a partial grid iteration
    has_crossing_info = any("crossing_letters" in clue for clue in all_clues.values())

    # Build base prompt based on whether we have crossing info
    if has_crossing_info:
        base_rules = """You are solving a crossword puzzle. Some letters may already be filled in from previous solving, but these letters are VERY likely to contain errors. Use them as inspiration but do NOT anchor on them.

For each clue, provide up to 5 possible answers, ordered from most to least likely.

IMPORTANT RULES:
1. Be exactly the specified length
2. Be a REAL English word or phrase - NEVER make up fake words
3. Make sense as an answer to the clue
4. Write your answers without spaces between the letters. Answers with multiple words should be written with spaces between the words, like 'APPLE PIE'
5. If crossing_letters are provided (like "B - T M Y N"), you may consider them but do NOT force your answer to match them exactly
6. It is perfectly acceptable to give answers that conflict with the given crossing letters
7. ABSOLUTELY DO NOT create fake words just to match letters (e.g., if given "B - T M Y N", "BATMAN" is fine but "BATMYN" is absolutely forbidden)
8. If you think of words that fit the clue and number of letters but don't fit the crossing letters, please include them anyway
"""

        example_input_dict = {
            "across_1": {
                "clue": "Gotham superhero",
                "length": 6,
                "crossing_letters": "B - T M Y N",
            },
            "down_2": {
                "clue": "Body of water",
                "length": 4,
                "crossing_letters": "P O - -",
            },
        }
    else:
        base_rules = """You are solving a crossword puzzle. For each clue, provide up to 5 possible answers, ordered from most to least likely.

Each answer must:
1. Be exactly the specified length
2. Be a real English word or phrase
3. Make sense as an answer to the clue
4. Write your answers without spaces between the letters. Answers with multiple words should be written with spaces between the words, like 'APPLE PIE'

If you can't think of any valid answers for a clue, return an empty list."""

        example_input_dict = {
            "across_1": {
                "clue": "Capital of France",
                "length": 5,
            },
            "down_2": {
                "clue": "Body of water",
                "length": 4,
            },
        }

    # Build example output using Python dicts
    if has_crossing_info:
        example_output_dict = {"across_1": {}, "down_2": {}}
        if USE_REASONING:
            example_output_dict["across_1"][
                "reasoning"
            ] = "BATMAN fits perfectly. There aren't any other superheroes in Gotham."
            example_output_dict["down_2"][
                "reasoning"
            ] = "POND or POOL fits perfectly. Ignoring crossing letters, LAKE, GULF, and LOCH could also work."
        # We have to put this second so that reasoning goes first in the prompt
        example_output_dict["across_1"]["answers"] = ["BATMAN"]
        example_output_dict["down_2"]["answers"] = [
            "POND",
            "POOL",
            "LAKE",
            "GULF",
            "LOCH",
        ]
    else:
        example_output_dict = {"across_1": {}, "down_2": {}}
        if USE_REASONING:
            example_output_dict["across_1"][
                "reasoning"
            ] = "This is asking for the capital city of France, which is definitely Paris."
            example_output_dict["down_2"][
                "reasoning"
            ] = "I think of POND, POOL, LAKE, OCEAN, GULF, and LOCH. But OCEAN has 5 letters, not 4."
        example_output_dict["across_1"]["answers"] = ["PARIS"]
        example_output_dict["down_2"]["answers"] = [
            "POND",
            "LAKE",
            "GULF",
            "POOL",
            "LOCH",
        ]

    # Add reasoning format if enabled
    reasoning_line = (
        '- "reasoning": Brief explanation of your thinking\n' if USE_REASONING else ""
    )

    prompt = f"""{base_rules}

Return a JSON object where keys match the input keys and values are objects with:
{reasoning_line}- "answers": A list of up to 5 answers, each in uppercase with spaces between letters (e.g., "P A R I S")

Example clues:
{json.dumps(example_input_dict, indent=2)}

Example response:
{json.dumps(example_output_dict, indent=2)}

Clues:
{json.dumps(all_clues, indent=2)}

Return ONLY the JSON object. You MUST return both across and down clues."""

    # If there are no clues to elicit, just return reused candidates
    if not all_clues:
        logging.info("No new clues to elicit, using only reused candidates")
        return reused_candidates

    response = execute_llm(prompt)

    # Extract JSON from response
    json_match = re.search(r"\{[^{}]*\{[^{}]*\}[^{}]*\}", response, re.DOTALL)
    try:
        if json_match:
            results = json.loads(json_match.group())
        else:
            results = json.loads(response)
    except Exception as e:
        logging.error(f"Failed to parse elicited answers: {e}")
        logging.error(f"Response: {response}")
        raise e

    # Process results and combine with reused candidates
    candidates = {"across": {}, "down": {}}

    # Start with reused candidates
    for direction in ["across", "down"]:
        candidates[direction].update(reused_candidates[direction])

    for key, result in results.items():
        if isinstance(result, dict) and "answers" in result:
            parts = key.split("_")
            if len(parts) == 2:
                direction = parts[0]
                clue_num = int(parts[1])

                # Filter valid answers by length
                clue_info = all_clues[key]
                expected_length = clue_info["length"]
                clue_text = clue_info["clue"]
                crossing_letters = (
                    f", given {clue_info['crossing_letters']}"
                    if "crossing_letters" in clue_info
                    else ""
                )
                reasoning_text = (
                    f" '{result['reasoning']}'" if "reasoning" in result else ""
                )
                valid_answers = []

                logging.debug(
                    f"Elicited '{direction} {clue_num}. {clue_text}' ({expected_length} letters, given {crossing_letters}):{reasoning_text} {result['answers']}"
                )

                for answer_str in result["answers"]:
                    answer = "".join(answer_str.split()).upper()
                    answer = "".join(c for c in answer if c.isalpha())
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
                else:
                    logging.warning(f"No valid answers for {direction} {clue_num}")
    return candidates


RATE_MIN_SCORE = 4


def rate_candidates(candidates, across_clues, down_clues):
    """Rate candidate answers using an LLM rater"""
    # Prepare all candidates for rating
    rating_items = []

    for direction in ["across", "down"]:
        clues = across_clues if direction == "across" else down_clues
        for clue_num, answer_list in candidates[direction].items():
            if clue_num in clues:
                clue_text = clues[clue_num]
                for answer in answer_list:
                    rating_items.append(
                        {
                            "id": f"{direction}_{clue_num}_{answer}",
                            "direction": direction,
                            "number": clue_num,
                            "clue": clue_text,
                            "answer": answer,
                        }
                    )

    if not rating_items:
        return candidates

    # Prepare prompt for rater
    prompt = """You are rating crossword puzzle answers. For each clue and answer pair, rate how well the answer fits the clue on a scale from 1 to 10:

1-3: Definitely wrong (typos, nonsense words, completely unrelated)
4-6: Possibly related but unlikely
7-9: Good fit
10: Perfect fit

IMPORTANT: Any typo or made-up word should immediately get a score of 1. For example:
- "BATMAN" for "Famous superhero" = 10 (perfect)
- "BATMYN" for "Famous superhero" = 1 (typo/nonsense)

Return a JSON object where keys are the provided IDs and values are the numeric ratings.

Items to rate:
"""

    # Add items in batches to avoid too long prompts
    items_dict = {}
    for item in rating_items:
        items_dict[item["id"]] = {
            "clue": f"{item['clue']} ({len(item['answer'])} letters)",
            "answer": item["answer"],
        }

    prompt += json.dumps(items_dict, indent=2)
    prompt += "\n\nReturn ONLY the JSON object with ratings."

    logging.info(f"Rating {len(rating_items)} candidate answers")
    response = execute_llm(prompt)

    # Parse ratings
    try:
        json_match = re.search(r"\{[^{}]*\}", response, re.DOTALL)
        if json_match:
            ratings = json.loads(json_match.group())
        else:
            ratings = json.loads(response)
    except Exception as e:
        logging.error(f"Failed to parse ratings: {e}")
        logging.error(f"Response: {response}")
        raise e

    # Filter candidates based on ratings
    filtered_candidates = {"across": {}, "down": {}}

    for direction in ["across", "down"]:
        for clue_num, answer_list in candidates[direction].items():
            filtered_answers = []
            for answer in answer_list:
                rating_id = f"{direction}_{clue_num}_{answer}"
                if rating_id in ratings:
                    rating = ratings[rating_id]
                    logging.debug(
                        f"{direction} {clue_num} '{answer}' for clue '{clue_text}': rating {rating}"
                    )
                    if rating >= RATE_MIN_SCORE:
                        filtered_answers.append(answer)
                    else:
                        logging.info(
                            f"Filtered out {direction} {clue_num} '{answer}' for clue '{clue_text}' (rating {rating})"
                        )
                else:
                    # If no rating, keep the answer
                    filtered_answers.append(answer)

            if filtered_answers:
                filtered_candidates[direction][clue_num] = filtered_answers

    return filtered_candidates


def merge_with_iteration1_candidates(current_candidates, iteration1_candidates):
    """Merge current candidates with iteration 1 candidates (appending iter1 at end)"""
    merged = {"across": {}, "down": {}}

    for direction in ["across", "down"]:
        for clue_num in set(current_candidates[direction].keys()) | set(
            iteration1_candidates[direction].keys()
        ):
            current_answers = current_candidates[direction].get(clue_num, [])
            iter1_answers = iteration1_candidates[direction].get(clue_num, [])

            # Current answers first, then iteration 1 answers (avoiding duplicates)
            merged_answers = current_answers[:]
            for answer in iter1_answers:
                if answer not in merged_answers:
                    merged_answers.append(answer)

            if merged_answers:
                merged[direction][clue_num] = merged_answers

    return merged


def get_first_valid_words(candidates):
    """Extract the first valid word for each clue"""
    first_valid = {"across": {}, "down": {}}

    for direction in ["across", "down"]:
        for clue_num, answers in candidates[direction].items():
            if answers:
                first_valid[direction][clue_num] = answers[0]

    return first_valid


def calculate_all_probabilities(candidates, locked_words, first_valid_words, grid):
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

        # Find all conflicting locked words
        conflicting_words = []
        opposite_dir = "down" if direction == "across" else "across"

        for i, pos in enumerate(positions):
            if i >= len(answer):
                break

            # Check opposite direction locked words
            for other_num, other_answer in locked_words.get(opposite_dir, {}).items():
                other_positions = get_word_positions(other_num, grid, opposite_dir)
                if pos in other_positions:
                    idx = other_positions.index(pos)
                    if idx < len(other_answer) and other_answer[idx] != answer[i]:
                        # This is a conflict - add to list if not already there
                        conflict_info = (opposite_dir, other_num, other_answer)
                        if conflict_info not in conflicting_words:
                            conflicting_words.append(conflict_info)

        if conflicting_words:
            # Check if new word has lower probability than ALL conflicting words
            can_replace_all = True
            conflict_probs = []

            for opp_dir, opp_num, opp_answer in conflicting_words:
                # Get crossing letters for the conflicting word
                opp_positions = get_word_positions(opp_num, grid, opp_dir)
                opp_crossing = get_crossing_letters(
                    opp_positions, locked_words, first_valid_words, grid, opp_dir
                )
                opp_prob = coincidence_prob(opp_answer, opp_crossing)
                conflict_probs.append((opp_dir, opp_num, opp_answer, opp_prob))

                if prob_info["probability"] >= opp_prob:
                    can_replace_all = False
                    break

            if can_replace_all:
                # New word beats all conflicting words - unlock them all and lock new word
                logging.info(
                    f"New word {direction} {clue_num} '{answer}' (p={prob_info['probability']:.6f}) beats all conflicts:"
                )

                for opp_dir, opp_num, opp_answer, opp_prob in conflict_probs:
                    logging.info(
                        f"  Unlocking {opp_dir} {opp_num} '{opp_answer}' (p={opp_prob:.6f})"
                    )
                    del locked_words[opp_dir][opp_num]

                if direction not in locked_words:
                    locked_words[direction] = {}
                locked_words[direction][clue_num] = answer
                logging.info(
                    f"Locked in {direction} {clue_num}: {answer} (p={prob_info['probability']:.6f})"
                )
                return True
            else:
                # New word doesn't beat all conflicts - skip it
                logging.debug(
                    f"Cannot lock {direction} {clue_num} '{answer}' - conflicts with better words"
                )
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

    # For any remaining - positions, use the letter from the word with lowest coincidence probability
    for row in range(height):
        for col in range(width):
            if grid[row][col] != "." and completed[row][col] == "-":
                # Collect all candidate letters for this position
                candidate_letters = []

                for direction in ["across", "down"]:
                    for clue_num, answer_list in candidates[direction].items():
                        # Skip if this clue is already locked
                        if clue_num in locked_words.get(direction, {}):
                            continue

                        positions = get_word_positions(clue_num, grid, direction)
                        if (row, col) in positions:
                            idx = positions.index((row, col))

                            # Try all candidate answers for this clue
                            for answer in answer_list:
                                if idx < len(answer):
                                    # Calculate crossing letters for this specific answer
                                    # Create a proper deep copy of first_valid_words
                                    temp_first_valid = {
                                        "across": first_valid_words.get(
                                            "across", {}
                                        ).copy(),
                                        "down": first_valid_words.get(
                                            "down", {}
                                        ).copy(),
                                    }
                                    temp_first_valid[direction][clue_num] = answer

                                    crossing_letters = get_crossing_letters(
                                        positions,
                                        locked_words,
                                        temp_first_valid,
                                        grid,
                                        direction,
                                    )
                                    prob = coincidence_prob(answer, crossing_letters)

                                    candidate_letters.append(
                                        {
                                            "letter": answer[idx],
                                            "probability": prob,
                                            "direction": direction,
                                            "clue_num": clue_num,
                                            "answer": answer,
                                        }
                                    )

                if candidate_letters:
                    # Sort by probability and pick the letter from the lowest probability word
                    candidate_letters.sort(key=lambda x: x["probability"])
                    best_candidate = candidate_letters[0]
                    best_letter = best_candidate["letter"]

                    logging.debug(
                        f"Position ({row},{col}): chose '{best_letter}' from "
                        f"{best_candidate['direction']} {best_candidate['clue_num']} "
                        f"'{best_candidate['answer']}' (p={best_candidate['probability']:.6f})"
                    )
                else:
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


def all_positions_covered(grid, locked_words):
    """Check if all non-blank positions are covered by locked words"""
    locked_grid = build_grid_for_logging(grid, locked_words)

    for row in range(len(grid)):
        for col in range(len(grid[0]) if grid else 0):
            if grid[row][col] != "." and locked_grid[row][col] == "-":
                return False
    return True


def process_input(input_string: str) -> str:
    grid, across_clues, down_clues = parse_crossword_input(input_string)
    logging.info(f"Parsed grid of size {len(grid)}x{len(grid[0]) if grid else 0}")
    logging.info(
        f"Found {len(across_clues)} across clues and {len(down_clues)} down clues"
    )

    # Multi-iteration process
    final_locked_words = {}
    final_candidates = None
    iteration1_candidates = None

    for main_iteration in range(1, MAX_ITERATIONS + 1):
        logging.info(f"\n=== MAIN ITERATION {main_iteration} ===")

        # Step 1: Elicit all answers (with or without partial grid)
        if main_iteration == 1:
            candidates = elicit_all_answers(across_clues, down_clues, grid)
            # Store iteration 1 candidates for later use
            iteration1_candidates = candidates
        else:
            # Use locked words from previous iteration to show partial grid
            # Pass previous candidates to allow reusing fully constrained words
            candidates = elicit_all_answers(
                across_clues, down_clues, grid, final_locked_words, final_candidates
            )

            # Rate and filter candidates in iteration 2+ (if enabled)
            if USE_RATING:
                candidates = rate_candidates(candidates, across_clues, down_clues)

            # Merge with iteration 1 candidates
            candidates = merge_with_iteration1_candidates(
                candidates, iteration1_candidates
            )

        # Step 2: Get first valid words and reset locked words for this iteration
        first_valid_words = get_first_valid_words(candidates)
        locked_words = {}

        # Step 3: Search process - lock words one at a time in order of probability
        sub_iteration = 0
        total_locked = 0

        while True:
            sub_iteration += 1
            logging.info(f"\n--- Sub-iteration {main_iteration}.{sub_iteration} ---")

            # Calculate probabilities for all unlocked words
            sorted_probabilities = calculate_all_probabilities(
                candidates, locked_words, first_valid_words, grid
            )

            # Try to lock the next best word
            if try_lock_next_word(
                sorted_probabilities, locked_words, first_valid_words, grid
            ):
                total_locked += 1
                # Log grid after each new lock (with - for unlocked)
                temp_grid = build_grid_for_logging(grid, locked_words)
                log_grid(temp_grid, f"\nGrid after locking word #{total_locked}:")

                # Check if all positions are now covered
                if all_positions_covered(grid, locked_words):
                    logging.info("All positions covered by locked words!")
                    final_locked_words = locked_words
                    final_candidates = candidates
                    break
            else:
                logging.info("No more words can be locked in this sub-iteration")
                break

        # Update final results from this iteration
        final_locked_words = locked_words
        final_candidates = candidates

        # Check if we should stop early
        if all_positions_covered(grid, locked_words):
            logging.info(
                f"Stopping early - all positions covered after iteration {main_iteration}"
            )
            break

        logging.info(
            f"End of main iteration {main_iteration}: {len(locked_words.get('across', {}))} across, {len(locked_words.get('down', {}))} down locked"
        )

    # Step 4: Build final grid
    completed_grid = build_completed_grid(
        grid,
        final_locked_words,
        get_first_valid_words(final_candidates),
        final_candidates,
    )

    # Format output
    result = []

    # Add completed grid
    for row in completed_grid:
        result.append(" ".join(row))

    result.append("")  # Empty line separator

    # Add across answers
    if final_locked_words.get("across") or get_first_valid_words(final_candidates).get(
        "across"
    ):
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
    if final_locked_words.get("down") or get_first_valid_words(final_candidates).get(
        "down"
    ):
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
        f"\nFinal: {len(final_locked_words.get('across', {}))} across, {len(final_locked_words.get('down', {}))} down locked"
    )

    return "\n".join(result)
