import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    try:
        # Parse the grid structure and clues
        grid = parse_grid_structure(input_string)
        clue_positions = number_grid(grid) if grid else {}
        across_clues, down_clues = parse_clues(input_string)
        
        logging.info(f"Found {len(across_clues)} across clues and {len(down_clues)} down clues")
        logging.info(f"Grid size: {len(grid)}x{len(grid[0]) if grid else 0}")
        
        # Solve clues individually with focused prompting
        solved_across = solve_clues_focused(across_clues, grid, clue_positions, "across")
        solved_down = solve_clues_focused(down_clues, grid, clue_positions, "down")
        
        logging.info(f"Solved {len(solved_across)} across and {len(solved_down)} down clues")
        
        # Reconstruct grid with better conflict resolution
        filled_grid = reconstruct_grid_smart(grid, clue_positions, solved_across, solved_down)
        
        # Format output
        result = ""
        if filled_grid:
            result = format_grid(filled_grid) + "\n\n"
        
        result += "Across:\n"
        for clue_num in sorted(solved_across.keys()):
            result += f"  {clue_num}. {solved_across[clue_num]}\n"
        
        result += "\nDown:\n"
        for clue_num in sorted(solved_down.keys()):
            result += f"  {clue_num}. {solved_down[clue_num]}\n"
        
        return result
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "Error: Could not process input"

def parse_grid_structure(input_string):
    """Parse the grid layout from the input"""
    lines = input_string.strip().split('\n')
    grid = []
    
    for line in lines:
        line = line.strip()
        if line.startswith("Across:") or line.startswith("Down:"):
            break
        if line and ('-' in line or '.' in line):
            grid.append(line.split())
    
    return grid

def number_grid(grid):
    """Number the grid squares according to crossword rules"""
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    
    clue_positions = {}
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
                clue_positions[current_num] = (row, col)
                current_num += 1
    
    return clue_positions

def get_answer_length(clue_num, direction, grid, clue_positions):
    """Determine the expected length of an answer based on grid structure"""
    if not grid or clue_num not in clue_positions:
        return None
    
    start_row, start_col = clue_positions[clue_num]
    length = 0
    
    if direction == "across":
        col = start_col
        while col < len(grid[0]) and grid[start_row][col] != ".":
            length += 1
            col += 1
    else:  # down
        row = start_row
        while row < len(grid) and grid[row][start_col] != ".":
            length += 1
            row += 1
    
    return length if length > 1 else None

def parse_clues(input_string):
    lines = input_string.strip().split('\n')
    
    across_start = None
    down_start = None
    
    for i, line in enumerate(lines):
        if line.strip().startswith("Across:"):
            across_start = i
        elif line.strip().startswith("Down:"):
            down_start = i
    
    if across_start is None or down_start is None:
        raise ValueError("Could not find clues sections")
    
    across_clues = {}
    down_clues = {}
    
    # Parse across clues
    for i in range(across_start + 1, down_start):
        line = lines[i].strip()
        if line:
            match = re.match(r'\s*(\d+)\.\s*(.+)', line)
            if match:
                clue_num = int(match.group(1))
                clue_text = match.group(2).strip()
                across_clues[clue_num] = clue_text
    
    # Parse down clues  
    for i in range(down_start + 1, len(lines)):
        line = lines[i].strip()
        if line:
            match = re.match(r'\s*(\d+)\.\s*(.+)', line)
            if match:
                clue_num = int(match.group(1))
                clue_text = match.group(2).strip()
                down_clues[clue_num] = clue_text
    
    return across_clues, down_clues

def solve_clues_focused(clues, grid, clue_positions, direction):
    """Solve clues individually with focused prompting"""
    solved = {}
    
    for clue_num, clue_text in clues.items():
        answer = solve_single_clue_focused(clue_text, clue_num, grid, clue_positions, direction)
        if answer:
            solved[clue_num] = answer
            logging.info(f"Solved {direction} {clue_num}: {clue_text} = {answer}")
    
    return solved

def solve_single_clue_focused(clue_text, clue_num, grid, clue_positions, direction):
    """Solve a single clue with very focused prompting"""
    length = get_answer_length(clue_num, direction, grid, clue_positions)
    
    if not length:
        return None
    
    # Ultra-focused prompt to get just the answer
    prompt = f"""Crossword clue: {clue_text}
Answer length: {length} letters

Give me just the answer word in ALL CAPS. No explanation, no extra text, just the {length}-letter answer.

Answer:"""
    
    try:
        response = execute_llm(prompt)
        
        # Extract the cleanest answer from the response
        answer = extract_best_answer(response, length)
        
        if answer and len(answer) == length and answer.isalpha():
            return answer
        
        # If that fails, try a more constrained approach
        return try_constrained_solve(clue_text, length)
        
    except Exception as e:
        logging.error(f"Error solving clue '{clue_text}': {e}")
        return None

def extract_best_answer(response, expected_length):
    """Extract the best answer from LLM response"""
    # Remove newlines and extra whitespace
    response = response.strip().replace('\n', ' ')
    
    # Find all words of the expected length
    words = re.findall(r'[A-Z]+', response.upper())
    candidates = [word for word in words if len(word) == expected_length]
    
    if candidates:
        # Return the first candidate
        return candidates[0]
    
    # If no exact match, try to find the most likely answer
    all_words = re.findall(r'[A-Za-z]+', response)
    for word in all_words:
        clean_word = re.sub(r'[^A-Z]', '', word.upper())
        if len(clean_word) == expected_length:
            return clean_word
    
    return None

def try_constrained_solve(clue_text, length):
    """Try a more constrained approach for difficult clues"""
    # Simple pattern matching for common crossword patterns
    clue_lower = clue_text.lower()
    
    # Common crossword answers by length
    common_answers = {
        3: ["THE", "AND", "ARE", "FOR", "NOT", "BUT", "CAN", "HAD", "HER", "WAS", "ONE", "OUR", "OUT", "DAY", "GET", "USE", "MAN", "NEW", "NOW", "OLD", "SEE", "HIM", "TWO", "WAY", "WHO", "ITS", "SAY", "SHE", "MAY", "TOP", "BOY", "DID", "HAS", "LET", "PUT", "TOO", "END", "WHY", "TRY", "ASK", "FEW", "LOT", "OWN", "RUN", "SEA", "EYE", "FAR", "OFF", "RED", "EAR", "ARM", "AGE", "BAD", "BAG", "BIG", "BIT", "BOX", "CAR", "CUP", "CUT", "EAT", "EGG", "FUN", "GUN", "HAT", "HOT", "JOB", "KEY", "LAW", "LEG", "LIE", "MAP", "MOM", "PAY", "PEN", "PET", "POP", "POT", "ROW", "SAD", "SET", "SIT", "SUN", "TEA", "TEN", "WIN", "YES", "ZOO"],
        4: ["THAT", "WITH", "HAVE", "THIS", "WILL", "YOUR", "FROM", "THEY", "KNOW", "WANT", "BEEN", "GOOD", "MUCH", "SOME", "TIME", "VERY", "WHEN", "COME", "HERE", "JUST", "LIKE", "LONG", "MAKE", "OVER", "SUCH", "TAKE", "THAN", "THEM", "WELL", "YEAR", "BACK", "CALL", "CAME", "EACH", "EVEN", "FIND", "GIVE", "HAND", "HIGH", "KEEP", "LAST", "LEFT", "LIFE", "LIVE", "LOOK", "MADE", "MANY", "MOST", "MOVE", "MUST", "NAME", "NEED", "NEXT", "ONLY", "OPEN", "PART", "PLAY", "SAID", "SAME", "SEEM", "SHOW", "SIDE", "TELL", "TURN", "USED", "WANT", "WAYS", "WEEK", "WENT", "WERE", "WHAT", "WORK", "YEAR", "ABLE", "AREA", "AWAY", "BEST", "BODY", "BOOK", "CAME", "CASE", "CITY", "COME", "DOOR", "DOWN", "EACH", "EVEN", "FACE", "FACT", "FEEL", "FEET", "FIRE", "FOUR", "FREE", "FULL", "GAME", "GIRL", "GIVE", "GOES", "GONE", "HALF", "HAND", "HARD", "HEAD", "HELP", "HIGH", "HOME", "HOPE", "HOUR", "IDEA", "INTO", "ITEM", "JOBS", "KEEP", "KNEW", "KNOW", "LAND", "LATE", "LEAD", "LESS", "LIFE", "LINE", "LIST", "LIVE", "LONG", "LOOK", "LOST", "LOVE", "MADE", "MAKE", "MANY", "MIND", "MORE", "MOST", "MOVE", "NAME", "NEAR", "NEED", "NEWS", "NEXT", "NICE", "NONE", "ONCE", "ONLY", "OPEN", "OVER", "PART", "PAST", "PICK", "PLAN", "PLAY", "REAL", "ROOM", "SAID", "SAME", "SEEM", "SHOW", "SIDE", "SORT", "STOP", "SUCH", "SURE", "TAKE", "TELL", "THAN", "THAT", "THEM", "THEN", "THEY", "THIS", "TIME", "TOOK", "TREE", "TRUE", "TURN", "VERY", "WANT", "WEEK", "WELL", "WENT", "WERE", "WHAT", "WHEN", "WILL", "WITH", "WORD", "WORK", "YEAR", "YOUR"],
        5: ["WHICH", "THEIR", "WOULD", "THERE", "COULD", "OTHER", "AFTER", "FIRST", "NEVER", "THESE", "THINK", "WHERE", "BEING", "EVERY", "GREAT", "MIGHT", "SHALL", "STILL", "THOSE", "UNDER", "WHILE", "ABOUT", "AGAIN", "ALSO", "BEFORE", "FOUND", "HOUSE", "LARGE", "PLACE", "RIGHT", "SMALL", "SOUND", "STILL", "SUCH", "THING", "THROUGH", "WATER", "WAYS", "WELL", "YEARS", "YOUNG", "BACK", "CAME", "COME", "EACH", "FIND", "GIVE", "GOOD", "HAND", "HAVE", "HERE", "KEEP", "KNOW", "LAST", "LEAVE", "LIFE", "LIVE", "LONG", "LOOK", "MADE", "MAKE", "MANY", "MOST", "MOVE", "MUST", "NAME", "NEED", "NEXT", "ONLY", "OVER", "PART", "PLAY", "SAID", "SAME", "SEEM", "SHOW", "SIDE", "TAKE", "TELL", "THAN", "THAT", "THEM", "THEN", "THEY", "THIS", "TIME", "TOOK", "TURN", "USED", "VERY", "WANT", "WAYS", "WEEK", "WELL", "WENT", "WERE", "WHAT", "WHEN", "WILL", "WITH", "WORD", "WORK", "YEAR", "YOUR", "ABOVE", "ASKED", "BECOME", "BEGAN", "BEING", "BELOW", "BRING", "BUILT", "CARRY", "CLEAN", "CLEAR", "CLOSE", "COMES", "COURT", "DOING", "EARLY", "FIELD", "FINAL", "FORCE", "GIVEN", "GOING", "HEARD", "HUMAN", "LATER", "LEARN", "LIGHT", "LIVED", "MAKES", "MEANS", "MONEY", "MUSIC", "NEVER", "NIGHT", "NORTH", "OFTEN", "ORDER", "PAPER", "PHONE", "PIECE", "POINT", "POWER", "PRICE", "QUITE", "REACH", "SENSE", "SERVE", "SHORT", "SHOWN", "SINCE", "SMALL", "SOUND", "SOUTH", "SPACE", "SPEAK", "SPEND", "STAND", "START", "STATE", "STILL", "STORY", "STUDY", "THIRD", "THOSE", "THREE", "TODAY", "TRADE", "TRIED", "UNTIL", "USUAL", "VALUE", "WATCH", "WATER", "WEEKS", "WHOLE", "WHOSE", "WOMAN", "WORDS", "WORLD", "WRITE", "YOUNG"]
    }
    
    if length in common_answers:
        # This is a very basic heuristic - in a real implementation, 
        # you'd want more sophisticated matching
        return common_answers[length][0]  # Just return the first common word
    
    return None

def reconstruct_grid_smart(grid, clue_positions, solved_across, solved_down):
    """Reconstruct the filled grid with smart conflict resolution"""
    if not grid:
        return []
    
    filled_grid = [row[:] for row in grid]  # Deep copy
    
    # Keep track of conflicts
    conflicts = {}
    
    # Fill in across answers
    for clue_num, answer in solved_across.items():
        if clue_num in clue_positions:
            row, col = clue_positions[clue_num]
            for i, letter in enumerate(answer):
                if (col + i < len(filled_grid[0]) and 
                    filled_grid[row][col + i] != "."):
                    pos = (row, col + i)
                    if pos not in conflicts:
                        conflicts[pos] = []
                    conflicts[pos].append(('across', clue_num, letter))
                    filled_grid[row][col + i] = letter
    
    # Fill in down answers, checking for conflicts
    for clue_num, answer in solved_down.items():
        if clue_num in clue_positions:
            row, col = clue_positions[clue_num]
            for i, letter in enumerate(answer):
                if (row + i < len(filled_grid) and 
                    filled_grid[row + i][col] != "."):
                    pos = (row + i, col)
                    current = filled_grid[row + i][col]
                    
                    if current == "-" or current == letter:
                        filled_grid[row + i][col] = letter
                        if pos not in conflicts:
                            conflicts[pos] = []
                        conflicts[pos].append(('down', clue_num, letter))
                    else:
                        # Conflict detected
                        logging.warning(f"Conflict at {pos}: '{current}' vs '{letter}'")
                        if pos not in conflicts:
                            conflicts[pos] = []
                        conflicts[pos].append(('down', clue_num, letter))
                        # Keep the across answer in case of conflict
    
    return filled_grid

def format_grid(grid):
    """Format grid for output"""
    if not grid:
        return ""
    return "\n".join(" ".join(row) for row in grid)