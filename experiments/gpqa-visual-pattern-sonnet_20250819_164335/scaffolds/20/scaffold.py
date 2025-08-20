import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    try:
        # The input contains the full question and instructions
        question = input_string.strip()
        
        # Send directly to LLM
        logging.info("Sending question to LLM")
        response = execute_llm(question)
        logging.info(f"LLM response received, length: {len(response)}")
        
        # Try multiple patterns to extract the answer letter
        patterns = [
            r'Answer:\s*([A-D])',  # "Answer: A"
            r'Answer:\s*&lt;\s*([A-D])\s*&gt;',  # "Answer: <A>" (HTML encoded)
            r'(?:^|\n)\s*([A-D])\s*(?:\)|$)',  # "A)" or just "A" at line start/end  
            r'(?:the\s+answer\s+is|correct\s+answer\s+is)\s*([A-D])',  # "The answer is A"
            r'(?:option|choice)\s*([A-D])',  # "Option A" or "Choice A"
            r'\b([A-D])\s*$',  # Final letter at end of response
        ]
        
        for i, pattern in enumerate(patterns):
            match = re.search(pattern, response, re.IGNORECASE | re.MULTILINE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Extracted answer using pattern {i}: {answer}")
                return answer
        
        # If no pattern matches, try asking more directly
        logging.warning("Could not extract answer using standard patterns, trying direct approach")
        direct_prompt = f"""Look at this multiple choice question and respond with ONLY the letter (A, B, C, or D) of the correct answer:

{question}

Just the letter, nothing else."""
        
        direct_response = execute_llm(direct_prompt)
        logging.info(f"Direct response: {direct_response}")
        
        # Extract any single letter A-D from the direct response
        letter_match = re.search(r'([A-D])', direct_response.upper())
        if letter_match:
            answer = letter_match.group(1)
            logging.info(f"Extracted answer from direct response: {answer}")
            return answer
        
        # If still no luck, try one more time with even simpler prompt
        logging.warning("Still no clear answer, trying simplest approach")
        simple_prompt = f"{question}\n\nAnswer (A, B, C, or D only):"
        
        simple_response = execute_llm(simple_prompt)
        letter_match = re.search(r'([A-D])', simple_response.upper())
        if letter_match:
            answer = letter_match.group(1)
            logging.info(f"Extracted answer from simple response: {answer}")
            return answer
        
        # Ultimate fallback - just return A
        logging.error("Could not extract answer from any response, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"