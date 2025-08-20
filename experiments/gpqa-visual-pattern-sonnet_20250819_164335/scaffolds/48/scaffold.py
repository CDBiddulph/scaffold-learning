import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    try:
        logging.info(f"Processing scientific question of length: {len(input_string)}")
        
        # Clean up the input - remove the ■ symbol which marks correct answers in examples
        cleaned_input = re.sub(r'^■\s*', '', input_string, flags=re.MULTILINE)
        
        # Create a focused prompt for scientific analysis
        system_prompt = """You are an expert scientist with deep knowledge across all scientific disciplines including physics, chemistry, biology, astronomy, mathematics, and engineering. Analyze complex scientific questions methodically and select the most accurate answer."""
        
        prompt = f"""Please analyze this scientific question step-by-step and select the correct answer.

{cleaned_input}

Please:
1. Identify the key scientific concepts involved
2. Work through the reasoning systematically 
3. Eliminate incorrect options
4. Select the best answer

Provide your final answer in the format "Answer: X" where X is A, B, C, or D."""
        
        response = execute_llm(prompt, system_prompt)
        logging.info(f"LLM response received (length: {len(response)})")
        
        # Extract the final answer with multiple fallback patterns
        
        # Pattern 1: "Answer: X" format (most reliable)
        answer_match = re.search(r'Answer:\s*([A-D])\b', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Found answer via 'Answer:' pattern: {answer}")
            return answer
        
        # Pattern 2: "Final answer: X" or similar
        answer_match = re.search(r'(?:Final|Correct)\s*answer:?\s*([A-D])\b', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Found answer via final answer pattern: {answer}")
            return answer
        
        # Pattern 3: Letter at end of response (like "The answer is A.")
        answer_match = re.search(r'\b([A-D])\s*[.\s]*$', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Found answer at end of response: {answer}")
            return answer
        
        # Pattern 4: Any letter in parentheses like "(A)" or "(B)"
        answer_match = re.search(r'\(([A-D])\)', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Found answer in parentheses: {answer}")
            return answer
        
        # Pattern 5: Last occurrence of any answer letter
        letters = re.findall(r'\b([A-D])\b', response, re.IGNORECASE)
        if letters:
            answer = letters[-1].upper()
            logging.info(f"Using last letter found: {answer}")
            return answer
        
        # If all else fails, ask the LLM again with a more direct prompt
        logging.warning("Could not extract answer, asking LLM for direct response")
        direct_prompt = f"""Based on this scientific question, what is the correct answer? Respond with only the letter A, B, C, or D.

{cleaned_input}"""
        
        direct_response = execute_llm(direct_prompt)
        direct_match = re.search(r'([A-D])', direct_response, re.IGNORECASE)
        if direct_match:
            answer = direct_match.group(1).upper()
            logging.info(f"Got direct answer: {answer}")
            return answer
        
        logging.error("Could not extract any answer, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Safe default