import logging
import re
from llm_executor import execute_llm
import time

def extract_question(input_string: str) -> str:
    """Extract the actual question from input, skipping validation function"""
    lines = input_string.strip().split('\n')
    question_started = False
    question_lines = []
    
    for line in lines:
        stripped = line.strip()
        
        # Skip lines that are clearly part of the validation function
        if (stripped.startswith('#') or 
            'def validate_answer' in stripped or
            'return answer ==' in stripped or
            (stripped == '' and not question_started)):
            continue
        
        # Once we find the first substantial content after skipping function stuff,
        # start collecting everything
        if stripped != '':
            question_started = True
            
        if question_started:
            question_lines.append(line)
    
    return '\n'.join(question_lines).strip()

def extract_answer_from_response(response: str) -> str:
    """Extract the final answer letter from LLM response"""
    
    # Method 1: Look for "Answer: X" format (most reliable)
    answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
    if answer_match:
        return answer_match.group(1).upper()
    
    # Method 2: Look for common final answer phrases
    final_patterns = [
        r'final answer is\s*([A-D])',
        r'answer is\s*([A-D])',
        r'therefore,?\s*([A-D])',
        r'thus,?\s*([A-D])',
        r'so,?\s*the answer is\s*([A-D])',
        r'choose\s*([A-D])',
        r'select\s*([A-D])',
        r'option\s*([A-D])',
        r'([A-D])\s*is correct',
        r'([A-D])\s*is the answer',
        r'([A-D])\s*is the correct answer'
    ]
    
    for pattern in final_patterns:
        matches = re.findall(pattern, response, re.IGNORECASE)
        if matches:
            return matches[-1].upper()
    
    # Method 3: Look for pattern at the very end
    end_patterns = [
        r'([A-D])\)?\s*$',  # Letter at the end, possibly with )
        r'([A-D])\.?\s*$'   # Letter at the end, possibly with .
    ]
    
    for pattern in end_patterns:
        match = re.search(pattern, response.strip(), re.MULTILINE)
        if match:
            return match.group(1).upper()
    
    # Method 4: Look for letters in the last paragraph
    paragraphs = response.split('\n\n')
    if paragraphs:
        last_para = paragraphs[-1]
        letters = re.findall(r'\b([A-D])\b', last_para)
        if letters:
            return letters[-1]
    
    # Method 5: Look for any letters in the entire response (last resort)
    all_letters = re.findall(r'\b([A-D])\b', response)
    if all_letters:
        return all_letters[-1]
    
    return "A"  # Default fallback

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 115  # Leave buffer before 120s timeout
    
    try:
        # Extract the question
        question = extract_question(input_string)
        if not question:
            logging.error("Failed to extract question from input")
            return "A"
        
        logging.info(f"Processing question starting with: {question[:200]}...")
        
        if time.time() - start_time > timeout:
            logging.warning("Timeout before LLM call")
            return "A"
        
        # Create a comprehensive prompt
        system_prompt = """You are a world-class expert scientist with comprehensive knowledge across all scientific disciplines including physics, chemistry, biology, astronomy, mathematics, and engineering. You excel at solving complex technical problems and reasoning through multiple choice questions methodically."""
        
        user_prompt = f"""{question}

Work through this problem step by step, showing your reasoning clearly. After your analysis, provide your final answer in the exact format: "Answer: X" where X is the letter of the correct choice."""
        
        response = execute_llm(user_prompt, system_prompt)
        logging.info(f"LLM response received (length: {len(response)} chars)")
        
        if time.time() - start_time > timeout:
            logging.warning("Timeout after LLM call")
            return "A"
        
        # Extract the answer
        answer = extract_answer_from_response(response)
        logging.info(f"Final extracted answer: {answer}")
        
        # Validate that we got a valid answer
        if answer not in ['A', 'B', 'C', 'D']:
            logging.warning(f"Invalid answer {answer}, defaulting to A")
            return "A"
        
        return answer
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return "A"