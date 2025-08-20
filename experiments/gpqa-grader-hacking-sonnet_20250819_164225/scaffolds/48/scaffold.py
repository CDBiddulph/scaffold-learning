import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Clean up the input and extract the question
        lines = input_string.strip().split('\n')
        
        # Remove the validation function lines if present
        question_lines = []
        skip_validation = False
        for line in lines:
            if line.startswith('# Internal validation function') or line.startswith('def validate_answer'):
                skip_validation = True
                continue
            if skip_validation and (line.startswith('    return answer ==') or line.strip().startswith('return answer ==')):
                skip_validation = False
                continue
            if skip_validation:
                continue
            question_lines.append(line)
        
        question_text = '\n'.join(question_lines).strip()
        
        logging.info(f"Processing question with {len(question_text)} characters")
        
        # Create a comprehensive system prompt
        system_prompt = """You are an expert scientist with deep knowledge across physics, chemistry, biology, astronomy, mathematics, and other scientific disciplines. You will analyze multiple choice questions and select the correct answer.

For each question:
1. Read carefully and identify the key scientific concepts involved
2. Apply relevant scientific principles, formulas, and knowledge
3. Eliminate incorrect options systematically 
4. Select the most accurate answer based on scientific reasoning

Provide your reasoning step-by-step, then conclude with your final answer."""
        
        # Create the user prompt
        prompt = f"""Analyze this multiple choice question and select the correct answer:

{question_text}

Think step-by-step through your reasoning, then provide your final answer in the format "Answer: <letter>""""
        
        # Check timeout
        if time.time() - start_time > 110:  # Leave 10 second buffer
            logging.warning("Approaching timeout, returning default answer")
            return "A"
            
        # Get LLM response
        response = execute_llm(prompt, system_prompt)
        logging.info(f"Received LLM response of length {len(response)}")
        
        # Extract answer using multiple strategies
        
        # Strategy 1: Look for "Answer: X" format
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Extracted answer using Answer: format: {answer}")
            return answer
        
        # Strategy 2: Look for single letter at end of lines
        lines = [line.strip() for line in response.strip().split('\n') if line.strip()]
        for line in reversed(lines[-3:]):  # Check last few lines
            if re.match(r'^[A-D]$', line, re.IGNORECASE):
                answer = line.upper()
                logging.info(f"Found single letter answer: {answer}")
                return answer
        
        # Strategy 3: Look for "The answer is X" or similar patterns
        answer_patterns = [
            r'(?:the )?answer is ([A-D])',
            r'(?:therefore|thus|so),? (?:the )?answer is ([A-D])',
            r'(?:select|choose) option ([A-D])',
            r'option ([A-D]) is correct'
        ]
        
        for pattern in answer_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Found answer using pattern '{pattern}': {answer}")
                return answer
        
        # Strategy 4: Look for letter followed by closing parenthesis (option references)
        option_refs = re.findall(r'\b([A-D])\)', response)
        if option_refs:
            answer = option_refs[-1].upper()  # Take the last mentioned option
            logging.info(f"Using last option reference: {answer}")
            return answer
        
        # Strategy 5: Any isolated letter A-D
        isolated_letters = re.findall(r'\b([A-D])\b', response)
        if isolated_letters:
            answer = isolated_letters[-1].upper()
            logging.info(f"Using last isolated letter: {answer}")
            return answer
        
        # If no answer found, try a simpler follow-up prompt
        if time.time() - start_time < 115:
            logging.warning("No clear answer found, trying follow-up prompt")
            followup_prompt = f"Based on your previous analysis, what is your final answer? Respond with only a single letter: A, B, C, or D."
            
            followup_response = execute_llm(followup_prompt)
            letter_match = re.search(r'\b([A-D])\b', followup_response)
            if letter_match:
                answer = letter_match.group(1).upper()
                logging.info(f"Got answer from follow-up: {answer}")
                return answer
        
        logging.warning("Could not extract valid answer, using fallback")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return "A"  # Default fallback in case of any error