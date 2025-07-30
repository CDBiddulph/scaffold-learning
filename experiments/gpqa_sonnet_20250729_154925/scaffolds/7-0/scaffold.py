import logging
import re
import time
from collections import Counter
from llm_executor import execute_llm

def extract_answer_from_response(response):
    """Extract answer letter from LLM response using multiple strategies"""
    # Strategy 1: Look for "Answer: X" pattern (most reliable)
    answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
    if answer_match:
        return answer_match.group(1).upper()
    
    # Strategy 2: Look for the last occurrence of A, B, C, or D as standalone letters
    letters = re.findall(r'\b([ABCD])\b', response, re.IGNORECASE)
    if letters:
        return letters[-1].upper()
    
    # Strategy 3: Look for letters at the very end of the response
    end_match = re.search(r'([ABCD])\s*$', response, re.IGNORECASE | re.MULTILINE)
    if end_match:
        return end_match.group(1).upper()
    
    # Strategy 4: Look for letters in parentheses like (A) or (B)
    paren_match = re.search(r'\(([ABCD])\)', response, re.IGNORECASE)
    if paren_match:
        return paren_match.group(1).upper()
    
    return None

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    # Extract the question content (everything after the metadata)
    metadata_end = input_string.find('</question-metadata>')
    if metadata_end == -1:
        logging.error("Could not find end of question metadata")
        return "A"  # Default fallback
    
    question_content = input_string[metadata_end + len('</question-metadata>'):].strip()
    logging.info(f"Extracted question content: {question_content[:200]}...")
    
    # Try multiple approaches with different reasoning strategies
    answers = []
    max_attempts = 3
    
    prompts = [
        # Attempt 1: Careful reading and systematic approach
        f"""You are answering a challenging multiple choice question. Please be extremely careful and read the question thoroughly.

{question_content}

Please approach this systematically:
1. First, identify exactly what the question is asking for
2. Work through the problem step by step 
3. Pay attention to all numerical values and units
4. Make sure you answer the specific question being asked

Think step-by-step to explain your reasoning, then write your final answer in the format "Answer: <letter>".""",

        # Attempt 2: Domain expert perspective
        f"""You are a scientific expert with deep knowledge across multiple fields. You are solving a technical multiple choice question.

{question_content}

Use your expertise to work through this problem carefully. Consider:
- What scientific principles apply here?
- Are there any calculations needed?
- What are the key concepts being tested?
- Double-check your reasoning before concluding

Provide detailed step-by-step reasoning, then write your final answer in the format "Answer: <letter>".""",

        # Attempt 3: Error-checking focus
        f"""You are solving a multiple choice question. Be very careful to avoid common mistakes and errors.

{question_content}

Work through this problem, but pay special attention to:
- Reading comprehension - make sure you understand what's being asked
- Calculation errors - double-check any math
- Unit conversions and scale factors
- Whether your final answer makes sense in context

Show your work step by step, then write your final answer in the format "Answer: <letter>"."""
    ]
    
    for attempt in range(max_attempts):
        # Check if we're running out of time (leave 30 second buffer)
        if time.time() - start_time > 90:
            logging.warning("Approaching timeout, stopping attempts")
            break
            
        logging.info(f"Attempt {attempt + 1} of {max_attempts}")
        
        try:
            response = execute_llm(prompts[attempt])
            logging.info(f"Attempt {attempt + 1} response length: {len(response)} chars")
            
            answer = extract_answer_from_response(response)
            if answer:
                answers.append(answer)
                logging.info(f"Extracted answer from attempt {attempt + 1}: {answer}")
            else:
                logging.warning(f"Could not extract answer from attempt {attempt + 1}")
                
        except Exception as e:
            logging.error(f"Error in attempt {attempt + 1}: {e}")
            continue
    
    # Use majority voting, or return the first answer if no clear majority
    if answers:
        counter = Counter(answers)
        most_common = counter.most_common()
        final_answer = most_common[0][0]
        count = most_common[0][1]
        
        logging.info(f"Answer votes: {dict(counter)}")
        logging.info(f"Final answer: {final_answer} (appeared {count}/{len(answers)} times)")
        return final_answer
    
    logging.error("No valid answers extracted from any attempt")
    return "A"  # Default fallback