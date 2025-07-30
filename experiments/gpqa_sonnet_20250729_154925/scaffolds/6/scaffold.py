import logging
import re
import time
from llm_executor import execute_llm

def extract_question(input_string: str) -> str:
    """Extract the actual question from the input, removing metadata."""
    metadata_end = input_string.find('</question-metadata>')
    if metadata_end == -1:
        return input_string.strip()
    
    question = input_string[metadata_end + len('</question-metadata>'):].strip()
    return question

def solve_question(question: str) -> str:
    """Use LLM to solve the scientific question step by step."""
    
    system_prompt = """You are an expert scientist with deep knowledge across chemistry, physics, astronomy, quantum mechanics, and related fields. You excel at solving complex technical problems through systematic step-by-step analysis."""
    
    prompt = f"""Please solve this scientific question systematically:

{question}

Instructions:
- Read the question and all options carefully
- Identify the type of problem and relevant scientific principles
- Work through the solution step by step with clear reasoning
- Show your calculations and intermediate steps if applicable
- Consider each multiple choice option carefully
- Conclude with your final answer in the format "Answer: <letter>"

Be thorough and precise in your analysis."""
    
    logging.info(f"Solving question (first 100 chars): {question[:100]}...")
    response = execute_llm(prompt, system_prompt)
    logging.info(f"LLM response received, length: {len(response)}")
    
    return response

def extract_answer_letter(llm_response: str) -> str:
    """Extract the final answer letter from the LLM response."""
    # Primary pattern: "Answer: A" format
    primary_pattern = r'Answer:\s*([A-D])'
    matches = re.findall(primary_pattern, llm_response, re.IGNORECASE)
    
    if matches:
        final_answer = matches[-1].upper()
        logging.info(f"Found answer using primary pattern: {final_answer}")
        return final_answer
    
    # Secondary patterns for common answer formats
    secondary_patterns = [
        r'(?:the (?:correct )?answer is|therefore,?|thus,?|hence,?)\s*(?:option\s*)?([A-D])',
        r'(?:option|choice)\s*([A-D])\s*(?:is (?:correct|right))',
        r'\b([A-D])\)\s*(?:is (?:the )?(?:correct|right|answer))',
        r'(?:select|choose)\s*(?:option\s*)?([A-D])'
    ]
    
    for pattern in secondary_patterns:
        matches = re.findall(pattern, llm_response, re.IGNORECASE)
        if matches:
            final_answer = matches[-1].upper()
            logging.info(f"Found answer using secondary pattern: {final_answer}")
            return final_answer
    
    # Final fallback: last A-D letter in the response
    letters = re.findall(r'\b([A-D])\b', llm_response)
    if letters:
        final_answer = letters[-1].upper()
        logging.info(f"Found answer using fallback pattern: {final_answer}")
        return final_answer
    
    logging.warning("Could not extract answer letter, defaulting to A")
    return "A"

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 115  # Leave buffer for the 120s limit
    
    try:
        # Extract the question from metadata
        question = extract_question(input_string)
        logging.info(f"Extracted question, length: {len(question)}")
        
        # Check timeout before expensive LLM call
        if time.time() - start_time > timeout:
            logging.warning("Timeout approaching before solving, returning default")
            return "A"
        
        # Solve the question using LLM
        llm_response = solve_question(question)
        
        # Check timeout after LLM call
        if time.time() - start_time > timeout:
            logging.warning("Timeout approaching after solving, extracting answer quickly")
        
        # Extract the answer letter
        answer_letter = extract_answer_letter(llm_response)
        
        logging.info(f"Final answer: {answer_letter}")
        return answer_letter
        
    except Exception as e:
        logging.error(f"Error in process_input: {str(e)}")
        return "A"  # Safe fallback