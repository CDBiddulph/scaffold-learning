import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    logging.info("Processing scientific multiple choice question")
    
    try:
        # Create a focused prompt that emphasizes systematic reasoning
        prompt = f"""You are a scientific expert with deep knowledge across all fields of science including physics, chemistry, biology, astronomy, and mathematics. Please solve this multiple choice question using rigorous scientific reasoning.

{input_string.strip()}

Please approach this systematically:
1. Identify the key scientific concepts, principles, and any given data
2. Work through necessary calculations or logical reasoning step by step
3. Consider each answer choice carefully against your analysis
4. Select the most accurate answer based on scientific principles

Always end your response with "Answer: <letter>" where <letter> is A, B, C, or D."""

        response = execute_llm(prompt)
        logging.info(f"LLM response received (length: {len(response)} characters)")
        
        # Primary extraction method: look for "Answer: <letter>"
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Successfully extracted answer using primary method: {answer}")
            return answer
        
        # Fallback extraction methods in order of reliability
        fallback_patterns = [
            r'(?:the\s+)?(?:correct\s+)?answer\s+is\s*(?:option\s*)?([A-D])',
            r'(?:therefore|thus|hence).*?(?:option\s*)?([A-D])',
            r'(?:best|correct)\s+(?:choice|option|answer).*?([A-D])',
            r'(?:select|choose).*?(?:option\s*)?([A-D])',
            r'option\s*([A-D])\s*(?:is|would|should|appears)',
            r'([A-D])\)\s*(?:is|would|should|appears|seems).*?(?:correct|best|answer)',
        ]
        
        for i, pattern in enumerate(fallback_patterns, 1):
            matches = re.findall(pattern, response, re.IGNORECASE | re.MULTILINE)
            if matches:
                answer = matches[-1].upper()  # Take the last match
                logging.info(f"Extracted answer using fallback method {i}: {answer}")
                return answer
        
        # Final fallback: look for the last mention of any letter A-D in the response
        all_letters = re.findall(r'\b([A-D])\b', response)
        if all_letters:
            answer = all_letters[-1].upper()
            logging.info(f"Extracted answer using last-resort method: {answer}")
            return answer
        
        # If all else fails, log the response and return default
        logging.error("Could not extract any answer from LLM response")
        logging.error(f"Response preview: {response[:200]}...")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {str(e)}")
        return "A"