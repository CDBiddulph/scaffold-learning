import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout_seconds = 110  # Leave buffer before 120s timeout
    
    try:
        logging.info("Processing scientific multiple choice question")
        
        # Check timeout early
        if time.time() - start_time > timeout_seconds:
            logging.warning("Approaching timeout")
            return "A"
        
        # Use system prompt to establish expertise
        system_prompt = "You are a world-renowned expert scientist with deep knowledge across physics, chemistry, biology, astronomy, mathematics, and all scientific fields. You excel at solving complex scientific problems."
        
        # Create focused prompt
        prompt = f"""{input_string}

Solve this step-by-step using your scientific expertise. End your response with exactly "Answer: X" where X is the correct letter (A, B, C, or D)."""

        response = execute_llm(prompt, system_prompt)
        logging.info(f"LLM response length: {len(response)} chars")
        
        # Multi-strategy answer parsing
        
        # Strategy 1: Look for explicit "Answer: X" format
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Found explicit answer: {answer}")
            return answer
        
        # Strategy 2: Look for clear conclusion statements
        conclusion_patterns = [
            r'The (?:correct )?answer is\s*([A-D])',
            r'(?:Therefore|Thus|Hence)[,\s]*(?:the answer is\s*)?([A-D])',
            r'Option\s*([A-D])\s*is\s*(?:the\s*)?correct',
            r'Choice\s*([A-D])\s*is\s*(?:the\s*)?right',
            r'Final answer:\s*([A-D])',
            r'I choose\s*([A-D])',
            r'The solution is\s*([A-D])'
        ]
        
        for pattern in conclusion_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Found conclusion answer: {answer}")
                return answer
        
        # Strategy 3: Look at the last few sentences for definitive statements
        sentences = response.split('.')
        for sentence in reversed(sentences[-3:]):  # Check last 3 sentences
            sentence = sentence.strip()
            if len(sentence) < 5:  # Skip very short fragments
                continue
            # Look for single letter mentions in conclusive contexts
            letter_in_context = re.search(r'(?:is|choose|select|answer)\s*([A-D])\b', sentence, re.IGNORECASE)
            if letter_in_context:
                answer = letter_in_context.group(1).upper()
                logging.info(f"Found contextual answer: {answer}")
                return answer
        
        # Strategy 4: Find the last clearly isolated letter
        # Look for letters that appear to be answers (not part of chemical formulas, etc.)
        isolated_letters = re.findall(r'(?:^|\s|\.|\))([A-D])(?:\s|$|\.|,|\))', response)
        if isolated_letters:
            answer = isolated_letters[-1].upper()
            logging.info(f"Found isolated letter: {answer}")
            return answer
        
        # Strategy 5: Last resort - any letter A, B, C, or D
        any_letters = re.findall(r'([A-D])', response)
        if any_letters:
            answer = any_letters[-1].upper()
            logging.info(f"Using last letter found: {answer}")
            return answer
        
        # Final fallback
        logging.warning("No answer found in response, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error in process_input: {str(e)}")
        return "A"