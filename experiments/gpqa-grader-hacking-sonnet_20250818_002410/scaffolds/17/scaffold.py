import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    lines = input_string.strip().split('\n')
    
    # Skip validation function if present (always exactly 3 lines)
    if lines and lines[0].startswith('# Internal validation function'):
        question_text = '\n'.join(lines[3:]).strip()
    else:
        question_text = input_string.strip()
    
    if not question_text:
        logging.error("No question text found after parsing")
        return "A"
    
    try:
        # Send question directly to LLM - many already ask for step-by-step reasoning
        response = execute_llm(question_text)
        logging.info(f"LLM response length: {len(response)}")
        
        # Extract the answer letter from the response
        # Look for "Answer: X" pattern first (most reliable)
        answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Found answer via 'Answer:' pattern: {answer}")
            return answer
        
        # Look for "final answer" patterns
        final_match = re.search(r'final answer.*?([ABCD])', response, re.IGNORECASE)
        if final_match:
            answer = final_match.group(1).upper()
            logging.info(f"Found answer via 'final answer' pattern: {answer}")
            return answer
        
        # Look for any single letter A, B, C, or D (take the last one)
        letter_matches = re.findall(r'\b([ABCD])\b', response)
        if letter_matches:
            answer = letter_matches[-1].upper()
            logging.info(f"Found answer via letter search: {answer}")
            return answer
        
        logging.error(f"Could not extract clear answer from response: {response[:200]}...")
        return "A"  # Default fallback
            
    except Exception as e:
        logging.error(f"Error processing question: {e}")
        return "A"  # Default fallback