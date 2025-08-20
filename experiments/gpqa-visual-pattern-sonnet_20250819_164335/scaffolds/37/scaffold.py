import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Check for timeout buffer
        if time.time() - start_time > 100:  # Leave buffer before 120s timeout
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        # Clean up input and check if it has the instruction prompt
        has_instruction = "Think step-by-step" in input_string
        
        if has_instruction:
            # Extract just the question part before the instruction
            question_part = input_string.split("Think step-by-step")[0].strip()
        else:
            question_part = input_string.strip()
        
        # Primary LLM call with detailed analysis request
        prompt = f"""{question_part}

Analyze this scientific question step by step. Consider all relevant scientific principles, perform necessary calculations, and determine the correct answer choice.

End your response with "Final answer: X" where X is the letter (A, B, C, or D) of the correct choice."""

        logging.info("Sending question to LLM for analysis")
        response = execute_llm(prompt)
        
        # Check timeout after LLM call
        if time.time() - start_time > 100:
            logging.warning("Timeout approaching after LLM call")
            return "A"
        
        # Multiple patterns to extract the answer
        answer_patterns = [
            r'Final answer:\s*([A-D])',
            r'Answer:\s*<([A-D])>',
            r'Answer:\s*([A-D])', 
            r'The correct answer is\s*([A-D])',
            r'Therefore,?\s*the answer is\s*([A-D])',
            r'\bchoice\s*([A-D])\b',
            r'\boption\s*([A-D])\b',
        ]
        
        for pattern in answer_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Extracted answer '{answer}' using pattern: {pattern}")
                return answer
        
        # Fallback: find the last mentioned choice letter in context
        # Look for letters that appear to be answers (not just references)
        sentences = re.split(r'[.!?]', response)
        for sentence in reversed(sentences):
            if any(word in sentence.lower() for word in ['correct', 'answer', 'therefore', 'thus', 'hence']):
                choice_match = re.search(r'\b([A-D])\b', sentence)
                if choice_match:
                    answer = choice_match.group(1).upper()
                    logging.info(f"Found contextual answer: {answer}")
                    return answer
        
        # Last resort: direct question
        if time.time() - start_time < 110:  # Still have time
            direct_prompt = f"""{question_part}

Which option is correct? Respond with only the letter: A, B, C, or D"""
            
            direct_response = execute_llm(direct_prompt)
            
            answer_match = re.search(r'\b([A-D])\b', direct_response.strip())
            if answer_match:
                answer = answer_match.group(1).upper()
                logging.info(f"Direct approach found: {answer}")
                return answer
        
        # Final fallback: look for any choice letter in original response
        all_choices = re.findall(r'\b([A-D])\b', response)
        if all_choices:
            answer = all_choices[-1].upper()  # Take the last mentioned
            logging.info(f"Using last mentioned choice: {answer}")
            return answer
        
        logging.error("No answer found in any response")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {str(e)}")
        return "A"  # Safe default