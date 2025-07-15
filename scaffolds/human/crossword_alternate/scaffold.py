import logging
import re
import time
import json
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


def get_cross_letters(
    clue_num,
    grid,
    direction,
    current_across_answers,
    current_down_answers,
    all_valid_answers,
):
    """Get the crossing letters for a clue based on perpendicular answers"""
    pos = find_clue_position(clue_num, grid, direction)
    if pos is None:
        return None

    row, col = pos
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    cross_letters = []

    if direction == "across":
        # For across clues, check down clues that cross this position
        for c in range(col, width):
            if grid[row][c] == ".":
                break

            # Find which down clue crosses at position (row, c)
            letter = "?"
            for down_num, answer in current_down_answers.items():
                down_pos = find_clue_position(down_num, grid, "down")
                if down_pos:
                    down_row, down_col = down_pos
                    if down_col == c and down_row <= row < down_row + len(answer):
                        # This down clue crosses our across clue
                        letter_idx = row - down_row
                        if letter_idx < len(answer):
                            letter = answer[letter_idx]
                            break

            # If still ?, check history
            if letter == "?":
                grid_key = f"{row},{c}"
                if grid_key in all_valid_answers:
                    letter = all_valid_answers[grid_key]

            cross_letters.append(letter)

    else:  # down
        # For down clues, check across clues that cross this position
        for r in range(row, height):
            if grid[r][col] == ".":
                break

            # Find which across clue crosses at position (r, col)
            letter = "?"
            for across_num, answer in current_across_answers.items():
                across_pos = find_clue_position(across_num, grid, "across")
                if across_pos:
                    across_row, across_col = across_pos
                    if across_row == r and across_col <= col < across_col + len(answer):
                        # This across clue crosses our down clue
                        letter_idx = col - across_col
                        if letter_idx < len(answer):
                            letter = answer[letter_idx]
                            break

            # If still ?, check history
            if letter == "?":
                grid_key = f"{r},{col}"
                if grid_key in all_valid_answers:
                    letter = all_valid_answers[grid_key]

            cross_letters.append(letter)

    return " ".join(cross_letters)


def validate_answer(answer, cross_letters_str, clue_num, direction):
    """Validate answer against length and crossing letters constraints"""
    cross_letters = cross_letters_str.split() if cross_letters_str else []

    # Check length
    if len(answer) != len(cross_letters):
        logging.debug(
            f"{direction.capitalize()} {clue_num}: Wrong length - got {len(answer)}, expected {len(cross_letters)}"
        )
        return False, "wrong_length"

    return True, "valid"


def create_clue_cache_key(direction, clue_num, clue_text, length, cross_letters):
    """Create a cache key for a single clue"""
    return f"{direction}:{clue_num}:{clue_text}:{length}:{cross_letters}"


def create_ranking_cache_key(direction, clue_num, clue_text, answer):
    """Create a cache key for ranking a single clue's answer"""
    return f"rank:{direction}:{clue_num}:{clue_text}:{answer}"


def rank_answers_batch(valid_answers_by_clue, clues, direction, llm_cache):
    """Ask LLM to rank the validity of answers on a 10-point scale"""
    if not valid_answers_by_clue:
        return {}

    # Check which answers are already cached
    rankings = {}
    answers_to_rank = {}

    for clue_num, answer in valid_answers_by_clue.items():
        if clue_num in clues:
            cache_key = create_ranking_cache_key(
                direction, clue_num, clues[clue_num], answer
            )
            if cache_key in llm_cache:
                rankings[clue_num] = llm_cache[cache_key]
                logging.debug(
                    f"Using cached ranking for {direction} {clue_num}: {rankings[clue_num]}"
                )
            else:
                answers_to_rank[clue_num] = answer

    if not answers_to_rank:
        logging.info(f"All {len(rankings)} rankings were cached")
        return rankings

    # Prepare ranking data for non-cached answers
    ranking_data = {}
    for clue_num, answer in answers_to_rank.items():
        ranking_data[clue_num] = {
            "clue": clues[clue_num],
            "answer": " ".join(answer),  # Convert to space-separated format
        }

    logging.info(
        f"Ranking {len(ranking_data)} answers for {direction} clues ({len(rankings)} already cached)"
    )

    prompt = f"""You are evaluating crossword puzzle answers. For each clue and its candidate answer, rate the answer on a scale of 1-10 based on:
- Is it a valid English word?
- Does it make sense as an answer to the clue?

A score of 10 means it's definitely correct, 1 means it's nonsense or completely wrong.

Return a JSON object where keys are clue numbers and values are objects with:
- "reasoning": Brief explanation of the score
- "score": The 1-10 rating

Example input:
{{
    "1": {{
        "clue": "A yellow fruit",
        "answer": "B A N A N A"
    }},
    "3": {{
        "clue": "A green vegetable",
        "answer": "C U C U N B E R"
    }},
    "7": {{
        "clue": "A type of fish",
        "answer": "L E E K"
    }}
}}

Example output:
{{
    "1": {{
        "reasoning": "Obviously correct",
        "score": 10
    }},
    "3": {{
        "reasoning": "'Cucumber' is a real English word, but 'cucunber' is not a real word. Even if it's just a typo, it's completely wrong.",
        "score": 1
    }},
    "7": {{
        "reasoning": "'Leek' is a real English word, but it's definitely not a type of fish.",
        "score": 1
    }}
}}

Clues and candidate answers:
{json.dumps(ranking_data, indent=2)}

Return ONLY the JSON object."""

    response = execute_llm(prompt)

    # Extract JSON from response
    json_match = re.search(r"\{[^{}]*\{[^{}]*\}[^{}]*\}", response, re.DOTALL)
    if json_match:
        results = json.loads(json_match.group())
    else:
        results = json.loads(response)

    # Process results and update cache
    for clue_num, rating_info in results.items():
        clue_num = int(clue_num)
        if isinstance(rating_info, dict) and "score" in rating_info:
            score = rating_info["score"]
            reasoning = rating_info.get("reasoning", "No reasoning provided")
            answer = answers_to_rank[clue_num]  # Get the original answer
            ranking_result = {"score": score, "reasoning": reasoning}
            rankings[clue_num] = ranking_result

            # Cache this individual ranking
            cache_key = create_ranking_cache_key(
                direction, clue_num, clues[clue_num], answer
            )
            llm_cache[cache_key] = ranking_result

            logging.debug(
                f"{direction.capitalize()} {clue_num} - '{answer}': Score {score} - {reasoning}"
            )

    return rankings


def solve_clues_batch(
    clues,
    grid,
    direction,
    current_across_answers,
    current_down_answers,
    all_valid_answers,
    llm_cache,
):
    """Solve a batch of clues with validation and ranking steps"""
    clue_data = {}

    for clue_num, clue_text in clues.items():
        length = get_clue_length(clue_num, grid, direction)
        if length is None:
            logging.debug(f"Skipping clue {clue_num} - no valid position found")
            continue

        cross_letters = get_cross_letters(
            clue_num,
            grid,
            direction,
            current_across_answers,
            current_down_answers,
            all_valid_answers,
        )

        clue_data[clue_num] = {
            "clue": clue_text,
            "length": length,
            "cross_letters": cross_letters or " ".join(["?"] * length),
        }
        logging.debug(
            f"{direction.capitalize()} {clue_num}: '{clue_text}' - length={length}, cross_letters='{cross_letters}'"
        )

    if not clue_data:
        logging.warning(f"No valid {direction} clues to process")
        return None

    # Step 1: Check cache and prepare clues that need solving
    cached_results = {}
    clues_to_solve = {}

    for clue_num, data in clue_data.items():
        cache_key = create_clue_cache_key(
            direction, clue_num, data["clue"], data["length"], data["cross_letters"]
        )
        if cache_key in llm_cache:
            cached_results[clue_num] = llm_cache[cache_key]
            logging.debug(
                f"Using cached answer for {direction} {clue_num}: {cached_results[clue_num]}"
            )
        else:
            clues_to_solve[clue_num] = data

    if clues_to_solve:
        logging.info(
            f"Step 1: Eliciting answers for {len(clues_to_solve)} {direction} clues ({len(cached_results)} cached)"
        )

        # Build prompt only for non-cached clues
        prompt = f"""You are solving a crossword puzzle. I will give you a batch of {direction} clues.

CRITICAL: The existing letters are EXTREMELY unreliable and likely have significant errors. Use them only as a very loose guide to jog your memory, but it's far more important that your answer:
1. Makes sense for the clue
2. Has exactly the right number of letters

If you can't think of a good answer that fits the clue, strongly prefer returning an empty string rather than a nonsense answer.

For each clue, I'll provide:
- The clue text
- The required length
- Any known crossing letters (shown as space-separated letters with ? for unknown positions)

Return a JSON object where keys are clue numbers and values are objects with:
- "reasoning": Your thought process (or "trivial" if the answer is obvious)
- "answer": The answer in uppercase with spaces between letters (e.g., "E X A M P L E"), or empty string if unsure

Example input:
{{
    "1": {{
        "clue": "Capital of France",
        "length": 5,
        "cross_letters": "? ? ? ? ?"
    }},
    "4": {{
        "clue": "Together with 33 Across, a common tabletop pairing",
        "length": 9,
        "cross_letters": "P A P I ? R"
    }},
    "8": {{
        "clue": "Something that connects devices",
        "length": 4,
        "cross_letters": "F O P E"
    }}
}}

Example output:
{{
    "1": {{
        "reasoning": "trivial",
        "answer": "P A R I S"
    }},
    "4": {{
        "reasoning": "Nothing fits the pattern exactly. I don't know what 33 Across is. Maybe the pairing is 'bread and butter', and the answer is 'B U T T E R'? But that doesn't fit the letters very well. Maybe the pairing is 'salt and pepper' and the answer is 'P E P P E R'? If I just change the A to an E and the I to a P, that would fit the pattern.",
        "answer": "P E P P E R"
    }},
    "8": {{
        "reasoning": "'F O P E' is not a real word, so it can't be that. 'W I R E' or 'C O R D' would work. The E matches for 'W I R E', and the O matches for 'C O R D', but no letters match other than that. I have no idea what the answer is, so I'll pass.",
        "answer": ""
    }}
}}

Clues:
{json.dumps(clues_to_solve, indent=2)}

Return ONLY the JSON object with clue numbers as keys."""

        response = execute_llm(prompt)

        # Extract JSON from response
        json_match = re.search(r"\{[^{}]*\{[^{}]*\}[^{}]*\}", response, re.DOTALL)
        if json_match:
            new_results = json.loads(json_match.group())
        else:
            new_results = json.loads(response)

        # Cache the new results
        for clue_num, result in new_results.items():
            clue_num = int(clue_num)
            if clue_num in clues_to_solve:
                cache_key = create_clue_cache_key(
                    direction,
                    clue_num,
                    clues_to_solve[clue_num]["clue"],
                    clues_to_solve[clue_num]["length"],
                    clues_to_solve[clue_num]["cross_letters"],
                )
                llm_cache[cache_key] = result
    else:
        logging.info(f"Step 1: All {len(cached_results)} answers were cached")
        new_results = {}

    # Combine cached and new results
    all_results = {**cached_results, **new_results}

    # Step 2: Filter out invalid words
    logging.info(f"Step 2: Filtering answers by length and crossing letter conflicts")
    valid_answers_by_clue = {}

    for clue_num, result in all_results.items():
        clue_num = int(clue_num)
        if isinstance(result, dict) and "answer" in result:
            answer_str = result["answer"].strip()
            if answer_str:
                # Remove spaces and convert to uppercase
                answer = "".join(answer_str.split()).upper()
                clue_text = clue_data.get(clue_num, {}).get("clue", "Unknown clue")
                reasoning = result.get("reasoning", "N/A")
                logging.info(
                    f"{direction.capitalize()} {clue_num}: '{clue_text}' -> {answer} (reasoning: {reasoning})"
                )

                # Validate
                cross_letters = clue_data.get(clue_num, {}).get("cross_letters", "")
                is_valid, reason = validate_answer(
                    answer, cross_letters, clue_num, direction
                )

                if is_valid:
                    valid_answers_by_clue[clue_num] = answer
                else:
                    logging.info(f"  Filtered out: {reason}")
            else:
                logging.debug(
                    f"{direction.capitalize()} {clue_num}: Empty answer returned"
                )

    logging.info(f"  Validated answers for {len(valid_answers_by_clue)} clues")

    if not valid_answers_by_clue:
        logging.info("  No valid answers after filtering")
        return {}

    # Step 3: Rank remaining words
    logging.info(f"Step 3: Ranking remaining answers")
    rankings = rank_answers_batch(valid_answers_by_clue, clues, direction, llm_cache)

    # Step 4: Filter out low-scored answers (5 or below)
    logging.info(f"Step 4: Filtering answers with score > 5")
    final_answers = {}

    for clue_num, answer in valid_answers_by_clue.items():
        if clue_num in rankings:
            score = rankings[clue_num]["score"]
            reasoning = rankings[clue_num]["reasoning"]
            if score > 5:
                final_answers[clue_num] = answer
                clue_text = clues.get(clue_num, "Unknown clue")
                logging.info(
                    f"  Accepted: {direction.capitalize()} {clue_num} '{clue_text}' -> {answer} (score: {score}, reasoning: {reasoning})"
                )
            else:
                logging.info(
                    f"  Filtered out: {direction.capitalize()} {clue_num} -> {answer} (score: {score}, reasoning: {reasoning})"
                )

    logging.info(
        f"Final: {len(final_answers)} accepted answers out of {len(clue_data)} {direction} clues"
    )
    return final_answers


def update_valid_answers_history(grid, answers, direction, all_valid_answers):
    """Update the history of all valid answers for each grid position"""
    for clue_num, answer in answers.items():
        pos = find_clue_position(clue_num, grid, direction)
        if pos:
            row, col = pos
            if direction == "across":
                for i, letter in enumerate(answer):
                    if col + i < len(grid[0]) and grid[row][col + i] != ".":
                        all_valid_answers[f"{row},{col + i}"] = letter
            else:  # down
                for i, letter in enumerate(answer):
                    if row + i < len(grid) and grid[row + i][col] != ".":
                        all_valid_answers[f"{row + i},{col}"] = letter


def build_completed_grid(grid, across_answers, down_answers, all_valid_answers):
    """Build the completed crossword grid using the most recent answers"""
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    completed = [row[:] for row in grid]  # Deep copy

    # First fill in the most recent answers
    # Fill in across answers
    for clue_num, answer in across_answers.items():
        pos = find_clue_position(clue_num, grid, "across")
        if pos:
            row, col = pos
            for i, letter in enumerate(answer):
                if col + i < width and grid[row][col + i] != ".":
                    completed[row][col + i] = letter

    # Fill in down answers
    for clue_num, answer in down_answers.items():
        pos = find_clue_position(clue_num, grid, "down")
        if pos:
            row, col = pos
            for i, letter in enumerate(answer):
                if row + i < height and grid[row + i][col] != ".":
                    completed[row + i][col] = letter

    # Fill any remaining ? with historical answers or 'E'
    for row in range(height):
        for col in range(width):
            if grid[row][col] != "." and completed[row][col] == "?":
                grid_key = f"{row},{col}"
                if grid_key in all_valid_answers:
                    completed[row][col] = all_valid_answers[grid_key]
                else:
                    completed[row][col] = "E"

    return completed


def log_grid(grid, across_answers, down_answers, all_valid_answers):
    """Log the current state of the grid"""
    completed_grid = build_completed_grid(
        grid, across_answers, down_answers, all_valid_answers
    )
    logging.info("Current grid state:")
    for row in completed_grid:
        logging.info("  " + " ".join(row))


def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 600.0  # seconds
    buffer_time = 10.0  # seconds

    grid, across_clues, down_clues = parse_crossword_input(input_string)
    logging.info(f"Parsed grid of size {len(grid)}x{len(grid[0]) if grid else 0}")
    logging.info(
        f"Found {len(across_clues)} across clues and {len(down_clues)} down clues"
    )

    # Initialize answer tracking
    current_across_answers = {}
    current_down_answers = {}
    all_valid_answers = {}  # History of all valid answers by grid position

    # Initialize LLM cache
    llm_cache = {}

    # Track LLM call times
    llm_times = []
    last_direction = None  # None means we start with across
    attempt_count = 0
    total_attempts = 0

    while True:
        current_time = time.time()
        elapsed = current_time - start_time

        # Check if we have enough time for another iteration
        if llm_times:
            avg_llm_time = sum(llm_times) / len(llm_times)
            time_needed = buffer_time + avg_llm_time
            remaining_time = timeout - elapsed
            logging.debug(
                f"Time check: elapsed={elapsed:.1f}s, avg_llm={avg_llm_time:.1f}s, remaining={remaining_time:.1f}s"
            )
            if elapsed + time_needed >= timeout:
                logging.info(
                    f"Stopping - insufficient time remaining (need {time_needed:.1f}s, have {remaining_time:.1f}s)"
                )
                break
        elif elapsed + buffer_time >= timeout:
            logging.info(f"No time for iterations (elapsed: {elapsed:.1f}s)")
            break

        # Determine which direction to solve
        if last_direction is None or last_direction == "down":
            current_direction = "across"
            current_clues = across_clues
        else:
            current_direction = "down"
            current_clues = down_clues

        if not current_clues:
            logging.warning(
                f"No {current_direction} clues available, switching direction"
            )
            last_direction = current_direction
            continue

        attempt_count += 1
        total_attempts += 1
        logging.info(
            f"\n=== Attempt {attempt_count} for {current_direction} clues (total attempts: {total_attempts}) ==="
        )

        try:
            llm_start = time.time()

            # Try to solve the current direction (includes both elicitation and ranking)
            new_answers = solve_clues_batch(
                current_clues,
                grid,
                current_direction,
                current_across_answers,
                current_down_answers,
                all_valid_answers,
                llm_cache,
            )

            llm_time = time.time() - llm_start
            llm_times.append(llm_time)
            logging.info(f"Complete solving process took {llm_time:.1f}s")

            if new_answers is None:
                # No clues to process for this direction
                logging.info(
                    f"No valid {current_direction} clues to process, switching direction"
                )
                last_direction = current_direction
                attempt_count = 0
                continue

            # Success! Update answers
            if current_direction == "across":
                for clue_num, answer in new_answers.items():
                    current_across_answers[clue_num] = answer
                update_valid_answers_history(
                    grid, current_across_answers, "across", all_valid_answers
                )
            else:
                for clue_num, answer in new_answers.items():
                    current_down_answers[clue_num] = answer
                update_valid_answers_history(
                    grid, current_down_answers, "down", all_valid_answers
                )

            logging.info(
                f"Successfully updated {len(new_answers)} {current_direction} answers"
            )
            logging.info(
                f"Total answers: {len(current_across_answers)} across, {len(current_down_answers)} down"
            )

            # Log the grid after this step
            log_grid(
                grid, current_across_answers, current_down_answers, all_valid_answers
            )

            # Switch direction for next iteration
            last_direction = current_direction
            attempt_count = 0

        except Exception as e:
            # LLM call failed, track time and retry same direction
            llm_time = time.time() - llm_start
            llm_times.append(llm_time)
            logging.error(
                f"LLM execution failed for {current_direction} (attempt {attempt_count}): {e}"
            )
            logging.info(f"Failed LLM call took {llm_time:.1f}s")

            # Continue with same direction on next iteration
            continue

    # Build the completed grid
    completed_grid = build_completed_grid(
        grid, current_across_answers, current_down_answers, all_valid_answers
    )

    # Format output
    result = []

    # Add completed grid first
    for row in completed_grid:
        result.append(" ".join(row))

    result.append("")  # Empty line separator

    # Add across section
    if current_across_answers:
        result.append("Across:")
        for clue_num in sorted(current_across_answers.keys()):
            result.append(f"  {clue_num}. {current_across_answers[clue_num]}")

    # Add down section
    if current_down_answers:
        result.append("\nDown:")
        for clue_num in sorted(current_down_answers.keys()):
            result.append(f"  {clue_num}. {current_down_answers[clue_num]}")

    final_result = "\n".join(result)
    total_time = time.time() - start_time
    logging.info(
        f"\n=== Completed in {total_time:.1f}s with {total_attempts} total attempts ==="
    )
    logging.info(
        f"Final results: {len(current_across_answers)} across, {len(current_down_answers)} down answers"
    )
    logging.info(f"Cache stats: {len(llm_cache)} unique LLM queries cached")
    return final_result
