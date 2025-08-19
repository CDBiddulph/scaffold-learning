import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Leave some buffer before the 120s limit
    
    try:
        # Clean up the input
        input_text = input_string.strip()
        
        # Check if the instruction is already included
        if "Think step-by-step" not in input_text and "explain your reasoning" not in input_text:
            input_text += '\n\nThink step-by-step to explain your reasoning, then write your final answer in the format "Answer: <letter>".'
        
        logging.info("Sending question to LLM for analysis")
        
        # Check timeout before LLM call
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout, returning default")
            return "A"
        
        response = execute_llm(input_text)
        
        # Extract answer with multiple strategies
        answer = extract_answer(response)
        
        if answer:
            logging.info(f"Found answer: {answer}")
            return answer
        
        # If we can't find the answer, try a more direct approach
        logging.info("Could not extract answer, trying direct approach")
        
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout, returning default")
            return "A"
        
        # Try a simpler, more direct prompt
        direct_prompt = f"""What is the correct answer to this multiple choice question? Respond with just the letter A, B, C, or D.

{input_text.split('Think step-by-step')[0].strip()}"""
        
        direct_response = execute_llm(direct_prompt)
        
        # Look for single letter response
        direct_answer = re.search(r'\b([A-D])\b', direct_response)
        if direct_answer:
            answer = direct_answer.group(1).upper()
            logging.info(f"Found direct answer: {answer}")
            return answer
        
        # Final fallback
        logging.warning("Could not determine answer, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"

def extract_answer(response):
    """Extract the answer from the LLM response using multiple strategies"""
    
    # Strategy 1: Look for "Answer: X" format
    answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
    if answer_match:
        return answer_match.group(1).upper()
    
    # Strategy 2: Look for common answer patterns
    patterns = [
        r'the answer is\s*([A-D])',
        r'correct answer is\s*([A-D])', 
        r'therefore\s*([A-D])',
        r'so the answer is\s*([A-D])',
        r'thus\s*([A-D])',
        r'hence\s*([A-D])',
        r'answer:\s*([A-D])',  # Case insensitive already handled above
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, response, re.IGNORECASE)
        if matches:
            return matches[-1].upper()  # Take the last occurrence
    
    # Strategy 3: Look at the end of the response for a letter
    lines = [line.strip() for line in response.strip().split('\n') if line.strip()]
    for line in reversed(lines[-3:]):  # Check last 3 lines
        # Look for standalone letter
        standalone = re.search(r'^([A-D])$', line)
        if standalone:
            return standalone.group(1).upper()
        
        # Look for letter at end of line
        end_letter = re.search(r'\b([A-D])\s*$', line)
        if end_letter:
            return end_letter.group(1).upper()
    
    # Strategy 4: Count letter mentions and pick most common
    # (but only if there's a clear winner)
    letter_counts = {'A': 0, 'B': 0, 'C': 0, 'D': 0}
    for letter in ['A', 'B', 'C', 'D']:
        # Count occurrences but weight them by context
        contexts = [
            r'\b' + letter + r'\)\s',  # "A) option"
            r'\b' + letter + r'\s*is\s+correct',
            r'\b' + letter + r'\s*is\s+the\s+answer',
            r'option\s+' + letter,
            r'choice\s+' + letter,
        ]
        
        for context in contexts:
            matches = len(re.findall(context, response, re.IGNORECASE))
            letter_counts[letter] += matches * 2  # Weight contextual mentions more
        
        # Also count bare mentions (but with less weight)
        bare_mentions = len(re.findall(r'\b' + letter + r'\b', response))
        letter_counts[letter] += bare_mentions
    
    # Only use this strategy if there's a clear winner (> 50% more mentions)
    max_count = max(letter_counts.values())
    if max_count > 0:
        sorted_letters = sorted(letter_counts.items(), key=lambda x: x[1], reverse=True)
        if len(sorted_letters) > 1 and sorted_letters[0][1] > sorted_letters[1][1] * 1.5:
            return sorted_letters[0][0]
    
    return None