import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Extract the question part (everything after the metadata)
        lines = input_string.strip().split('\n')
        
        # Find where the metadata ends
        question_start = 0
        for i, line in enumerate(lines):
            if line.strip() == '</question-metadata>':
                question_start = i + 1
                break
        
        if question_start == 0:
            # No metadata found, assume entire input is the question
            question_text = input_string.strip()
        else:
            question_text = '\n'.join(lines[question_start:]).strip()
        
        logging.info(f"Processing question: {question_text[:200]}...")
        
        # Check timeout early
        if time.time() - start_time > 100:  # Leave buffer for timeout
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        # Use focused system prompt for scientific expertise
        system_prompt = """You are an expert scientist with deep knowledge across physics, chemistry, biology, astronomy, mathematics, and all scientific fields. You excel at rigorous scientific analysis and problem-solving."""
        
        # Provide the question exactly as given, including the formatting instruction
        prompt = f"""{question_text}

Think step-by-step to explain your reasoning, then write your final answer in the format "Answer: <letter>""""
        
        response = execute_llm(prompt, system_prompt)
        logging.info(f"LLM response received: {len(response)} characters")
        
        # Extract answer using multiple strategies
        
        # Strategy 1: Look for the exact format requested "Answer: X"
        answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if answer_match:
            result = answer_match.group(1).upper()
            logging.info(f"Found answer using 'Answer:' pattern: {result}")
            return result
        
        # Strategy 2: Look for "Final answer: X" 
        final_match = re.search(r'Final answer:\s*([ABCD])', response, re.IGNORECASE)
        if final_match:
            result = final_match.group(1).upper()
            logging.info(f"Found answer using 'Final answer:' pattern: {result}")
            return result
            
        # Strategy 3: Look for "The answer is X" or "The correct answer is X"
        correct_match = re.search(r'(?:The (?:correct )?answer is|Answer is)\s*(?:option\s*)?([ABCD])', response, re.IGNORECASE)
        if correct_match:
            result = correct_match.group(1).upper()
            logging.info(f"Found answer using 'The answer is' pattern: {result}")
            return result
            
        # Strategy 4: Look for isolated letter at the end
        end_match = re.search(r'\b([ABCD])\b\.?\s*$', response, re.IGNORECASE | re.MULTILINE)
        if end_match:
            result = end_match.group(1).upper()
            logging.info(f"Found answer at end of response: {result}")
            return result
        
        # Strategy 5: Find the last mention of any option letter
        all_letters = re.findall(r'\b([ABCD])\b', response, re.IGNORECASE)
        if all_letters:
            result = all_letters[-1].upper()
            logging.info(f"Using last mentioned letter: {result}")
            return result
        
        # If nothing found, try a second attempt with more explicit instructions
        logging.warning("Could not extract answer, trying second attempt")
        
        if time.time() - start_time > 110:  # Even tighter timeout for second attempt
            logging.warning("No time for second attempt, using default")
            return "A"
            
        followup_prompt = f"""Based on the scientific question below, what is the correct answer?

{question_text}

Respond with ONLY the letter A, B, C, or D - nothing else."""
        
        followup_response = execute_llm(followup_prompt, system_prompt)
        
        # Extract single letter from followup
        single_letter = re.search(r'([ABCD])', followup_response.strip(), re.IGNORECASE)
        if single_letter:
            result = single_letter.group(1).upper()
            logging.info(f"Found answer in followup: {result}")
            return result
        
        logging.warning(f"Could not extract any answer from responses")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error processing input: {str(e)}")
        return "A"  # Safe fallback