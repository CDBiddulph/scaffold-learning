import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    input_text = input_string.strip()
    
    logging.info("Processing scientific multiple choice question")
    
    # Create a comprehensive prompt that emphasizes systematic analysis
    prompt = f"""You are an expert scientist with deep knowledge across physics, chemistry, biology, astronomy, and related fields. 

Analyze this multiple choice question carefully and systematically:

{input_text}

Please approach this methodically:
1. Identify the key scientific concepts and what is being asked
2. Apply relevant principles, equations, or knowledge from the appropriate field
3. Work through any necessary calculations or logical reasoning
4. Carefully evaluate each option against your analysis
5. Pay attention to units, magnitudes, and technical details

Provide your final answer in the format: Answer: X (where X is A, B, C, or D)
"""

    try:
        # Check time to avoid timeout
        if time.time() - start_time > 110:  # Leave buffer for processing
            logging.warning("Approaching time limit, returning default")
            return "A"
            
        response = execute_llm(prompt)
        logging.info(f"Received LLM response, length: {len(response)}")
        
        # Multiple strategies to extract the final answer letter
        
        # Strategy 1: Look for explicit "Answer: X" format
        answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Found answer with 'Answer:' pattern: {answer}")
            return answer
            
        # Strategy 2: Look for "The answer is X" or similar statements
        answer_match = re.search(r'(?:the\s+)?(?:correct\s+)?answer\s+is\s+([ABCD])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Found answer with 'answer is' pattern: {answer}")
            return answer
            
        # Strategy 3: Look for final conclusion statements
        answer_match = re.search(r'(?:therefore|thus|so|hence),?\s+(?:the\s+answer\s+is\s+)?([ABCD])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Found answer with conclusion pattern: {answer}")
            return answer
            
        # Strategy 4: Find the last occurrence of a single letter A, B, C, or D
        letters = re.findall(r'\b([ABCD])\b', response)
        if letters:
            answer = letters[-1].upper()
            logging.info(f"Using last letter mentioned: {answer}")
            return answer
            
        # Strategy 5: Look for letter at the very end of response
        answer_match = re.search(r'([ABCD])\s*\.?\s*$', response.strip())
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Found answer at end of response: {answer}")
            return answer
            
        logging.error(f"Could not extract answer from response: {response[:300]}...")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error processing question: {e}")
        return "A"  # Default fallback