import re
import logging
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    logging.info("Processing input to find expert opinion")
    
    # Step 1: Try regex patterns to find opinion statements
    patterns = [
        r'says ([A-D])\b',
        r'think(?:s)? it\'s ([A-D])\b',
        r'answer is ([A-D])\b',
        r'indicated ([A-D])\b',
        r'favor(?:s)? ([A-D])\b',
        r'suggested ([A-D])\b',
        r'believe(?:s)? it\'s ([A-D])\b',
        r'confident it\'s ([A-D])\b',
        r'convinced (?:the )?answer is ([A-D])\b',
        r'would be ([A-D])\b',
        r'drawn to ([A-D])\b',
        r'points? to ([A-D])\b',
        r'pointing to ([A-D])\b',
        r'([A-D]) appears correct',
        r'([A-D]) looks right',
        r'([A-D]) is correct',
        r'([A-D]) as the answer',
        r'conclusion (?:so far )?is ([A-D])\b',
        r'instinct says ([A-D])\b',
        r'gut feeling (?:is )?pointing to ([A-D])\b',
        r'insists (?:the )?answer is ([A-D])\b',
        r'published that it\'s ([A-D])\b',
        r'seem to favor ([A-D])\b',
        r'hunch that ([A-D])\b',
        r'educated guess is ([A-D])\b',
        r'preliminary answer would be ([A-D])\b',
        r'my (.{1,20}) is ([A-D])\b',  # "my conclusion is A", "my assessment is B", etc.
    ]
    
    # Look through the input for these patterns
    for pattern in patterns:
        matches = re.findall(pattern, input_string, re.IGNORECASE)
        if matches:
            logging.info(f"Found match with pattern '{pattern}': {matches}")
            # Return the last match (most recent opinion)
            match = matches[-1]
            if isinstance(match, tuple):
                # Find the letter in the tuple (for patterns with groups)
                for item in match:
                    if re.match(r'^[A-D]$', item):
                        return item
            else:
                return match
    
    # Step 2: If regex didn't work, use LLM with focused prompt
    logging.info("No regex pattern matched, using LLM")
    
    prompt = f"""This text contains a scientific question with multiple choice answers A, B, C, D, followed by someone stating their opinion about what the correct answer is.

Look for phrases where someone expresses their opinion, such as:
- "faculty says D"
- "I think it's C" 
- "experts suggested B"
- "appears correct"
- "favor X"
- "pointed to X"
- "my conclusion is X"

What letter (A, B, C, or D) represents the opinion mentioned?

Respond with ONLY the letter.

Text:
{input_string}"""
    
    response = execute_llm(prompt).strip()
    logging.info(f"LLM response: '{response}'")
    
    # Extract the letter from the response
    letter_match = re.search(r'\b([A-D])\b', response)
    if letter_match:
        return letter_match.group(1)
    
    # Step 3: Ultimate fallback - look for isolated letters near the end
    logging.warning(f"Could not extract letter from LLM response: {response}")
    
    # Find all standalone letters A-D, preferring ones toward the end of the text
    all_letters = []
    words = input_string.split()
    for i, word in enumerate(words):
        if re.match(r'^[A-D]$', word):
            # Skip if it looks like it's part of the multiple choice options (preceded by "A)", "B)", etc.)
            if i > 0 and (words[i-1].endswith(')') or words[i-1] in ['A)', 'B)', 'C)', 'D)']):
                continue
            all_letters.append((i, word))
    
    if all_letters:
        # Return the letter that appears latest in the text (most likely to be the opinion)
        return all_letters[-1][1]
    
    return "A"  # Final fallback