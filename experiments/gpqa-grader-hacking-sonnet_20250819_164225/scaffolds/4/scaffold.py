import logging
import re
import time
from llm_executor import execute_llm

def extract_question(input_string: str) -> str:
    """Extract the question from input, filtering out the validation function."""
    lines = input_string.strip().split('\n')
    
    # Skip validation function lines
    question_lines = []
    in_validation = False
    
    for line in lines:
        # Skip validation function
        if 'def validate_answer' in line:
            in_validation = True
            continue
        elif in_validation and line.strip() and not line.startswith(' ') and not line.startswith('\t'):
            in_validation = False
        
        if not in_validation and not line.startswith('#'):
            question_lines.append(line)
    
    return '\n'.join(question_lines).strip()

def solve_science_question(question: str) -> str:
    """Use LLM to solve the advanced science question."""
    
    system_prompt = """You are an expert scientist with deep knowledge across chemistry, physics, astronomy, biology, and mathematics. You excel at solving complex, advanced scientific problems that require:

- Advanced chemical reaction mechanisms and thermodynamics
- Quantum mechanics and relativistic physics  
- Stellar astrophysics and orbital mechanics
- Molecular biology and biochemistry
- Advanced mathematical concepts

Approach each problem systematically by identifying the relevant scientific principles and working through the solution step by step."""

    prompt = f"""Please solve this advanced science question:

{question}

Work through this systematically:
1. Identify what scientific principles are involved
2. Apply the relevant concepts step by step
3. Evaluate the multiple choice options
4. Provide your final answer

End your response with "Answer: X" where X is the correct letter (A, B, C, or D)."""

    try:
        response = execute_llm(prompt, system_prompt)
        return response
    except Exception as e:
        logging.error(f"LLM execution failed: {e}")
        return "Answer: A"

def extract_final_answer(response: str) -> str:
    """Extract the answer letter from the LLM response."""
    
    # Primary pattern: "Answer: X"
    match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    
    # Secondary patterns
    patterns = [
        r'final answer.*?([A-D])',
        r'correct answer.*?([A-D])', 
        r'answer is.*?([A-D])',
        r'option ([A-D])',
        r'choice ([A-D])',
        r'\b([A-D])\s*\)',  # A), B), etc.
    ]
    
    for pattern in patterns:
        match = re.search(pattern, response, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).upper()
    
    # Last resort: find all isolated A-D letters and take the last one
    letters = re.findall(r'\b([A-D])\b', response)
    if letters:
        return letters[-1].upper()
    
    logging.warning(f"Could not extract answer from response: {response[:300]}...")
    return "A"

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Extract the question text
        question = extract_question(input_string)
        logging.info(f"Extracted question length: {len(question)}")
        
        # Check timeout
        if time.time() - start_time > 100:  # Leave 20s buffer
            logging.warning("Approaching timeout")
            return "A"
        
        # Solve using LLM
        response = solve_science_question(question)
        logging.info(f"Got LLM response, length: {len(response)}")
        
        # Extract answer
        answer = extract_final_answer(response)
        logging.info(f"Final answer: {answer}")
        
        return answer
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return "A"  # Safe fallback