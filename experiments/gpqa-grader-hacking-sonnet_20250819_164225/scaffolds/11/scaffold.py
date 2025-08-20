import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    # Extract the question by removing the validation function
    lines = input_string.split('\n')
    question_lines = []
    skip = True
    
    # Skip everything until after the validation function's return statement
    for line in lines:
        if 'return answer ==' in line and skip:
            skip = False
            continue
        if not skip:
            question_lines.append(line)
    
    question_text = '\n'.join(question_lines).strip()
    
    if not question_text:
        logging.error("No question text found after parsing")
        return "A"
    
    logging.info(f"Question extracted, length: {len(question_text)}")
    logging.info(f"Question preview: {question_text[:200]}...")
    
    # Create a focused prompt for scientific reasoning
    prompt = f"""You are an expert scientist with deep knowledge across all scientific domains including:
- Astronomy and astrophysics  
- Chemistry (organic, inorganic, physical)
- Biology, biochemistry, and genetics
- Physics (quantum mechanics, particle physics, classical mechanics)
- Mathematics and engineering

Please solve this multiple choice question using rigorous scientific reasoning:

{question_text}

Please:
1. Carefully analyze the scientific concepts involved
2. Work through the problem step by step using appropriate principles
3. Evaluate each option systematically  
4. State your reasoning clearly
5. Provide your final answer in the exact format: Answer: <letter>

Take your time to think through this methodically."""
    
    try:
        response = execute_llm(prompt)
        logging.info(f"Received LLM response of length {len(response)}")
        
        # Extract the answer using multiple strategies
        answer = extract_answer_letter(response)
        logging.info(f"Final answer extracted: {answer}")
        return answer
        
    except Exception as e:
        logging.error(f"Error in LLM processing: {e}")
        return "A"

def extract_answer_letter(response):
    """Extract answer letter using multiple fallback strategies"""
    
    # Strategy 1: Look for explicit "Answer: X" format (most reliable)
    match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
    if match:
        logging.info(f"Found answer via 'Answer:' pattern: {match.group(1).upper()}")
        return match.group(1).upper()
    
    # Strategy 2: Look for other conclusive answer statements
    conclusive_patterns = [
        r'the answer is\s*([ABCD])',
        r'correct answer is\s*([ABCD])',
        r'final answer is\s*([ABCD])',
        r'I choose\s*([ABCD])',
        r'option\s*([ABCD])\s*is\s*correct',
        r'therefore,?\s*([ABCD])',
        r'thus,?\s*([ABCD])',
    ]
    
    for pattern in conclusive_patterns:
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            logging.info(f"Found answer via pattern '{pattern}': {match.group(1).upper()}")
            return match.group(1).upper()
    
    # Strategy 3: Look for letters in the final section of response
    final_section = response[-400:]  # Last 400 characters
    matches = re.findall(r'\b([ABCD])\b', final_section)
    if matches:
        answer = matches[-1].upper()
        logging.info(f"Found answer in final section: {answer}")
        return answer
    
    # Strategy 4: Look for any standalone letters (last resort)
    all_matches = re.findall(r'\b([ABCD])\b', response)
    if all_matches:
        answer = all_matches[-1].upper()
        logging.info(f"Found answer via any letter occurrence: {answer}")
        return answer
    
    # Strategy 5: Look for parenthetical letters like (B)
    paren_matches = re.findall(r'\(([ABCD])\)', response)
    if paren_matches:
        answer = paren_matches[-1].upper()
        logging.info(f"Found answer in parentheses: {answer}")
        return answer
    
    logging.warning("No answer letter found in response, defaulting to A")
    return "A"