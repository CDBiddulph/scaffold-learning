import logging
import re
import time
import html
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Decode HTML entities
        decoded_input = html.unescape(input_string)
        
        # Extract the question content by removing metadata
        question_text = extract_question_text(decoded_input)
        logging.info(f"Extracted question: {question_text[:300]}...")
        
        # Check timeout - give ourselves buffer
        if time.time() - start_time > 100:
            logging.warning("Approaching timeout, returning default")
            return "A"
        
        # Solve the question using the LLM
        answer = solve_question(question_text)
        logging.info(f"Final answer: {answer}")
        
        return answer
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"

def extract_question_text(decoded_input):
    """Extract the actual question text from the input, removing metadata."""
    lines = decoded_input.strip().split('\n')
    question_lines = []
    in_metadata = False
    
    for line in lines:
        line = line.strip()
        if line.startswith('<question-metadata>'):
            in_metadata = True
            continue
        elif line.startswith('</question-metadata>'):
            in_metadata = False
            continue
        elif not in_metadata and line:
            question_lines.append(line)
    
    return '\n'.join(question_lines)

def solve_question(question_text):
    """Solve the question using the LLM with step-by-step reasoning."""
    
    # First, try to understand what type of question this is
    domain_prompt = f"""What scientific domain(s) does this question primarily involve? (e.g., astronomy, chemistry, physics, biology)

{question_text[:500]}..."""
    
    domain_response = execute_llm(domain_prompt)
    logging.info(f"Domain analysis: {domain_response}")
    
    # Now solve with domain-specific context
    prompt = f"""You are an expert scientist with deep knowledge across multiple scientific disciplines. Based on the domain analysis, this appears to involve: {domain_response}

Please solve this multiple choice question step by step:

{question_text}

Instructions:
1. Read the question carefully and identify the key concepts and given information
2. Think through the problem step by step, showing your reasoning
3. Apply relevant scientific principles, formulas, or concepts
4. Eliminate incorrect options if possible
5. Choose the most appropriate answer

Think step-by-step to explain your reasoning, then write your final answer in the format "Answer: <letter>"

Be thorough but concise in your analysis."""
    
    response = execute_llm(prompt)
    logging.info(f"LLM response: {response}")
    
    return extract_answer_letter(response)

def extract_answer_letter(response):
    """Extract answer letter from LLM response using multiple strategies."""
    
    # Strategy 1: Look for "Answer: <letter>" format (as shown in examples)
    answer_match = re.search(r'Answer:\s*<?([ABCD])>?', response, re.IGNORECASE)
    if answer_match:
        return answer_match.group(1).upper()
    
    # Strategy 2: Look for "Final Answer: X" pattern
    final_answer_match = re.search(r'Final Answer:\s*([ABCD])', response, re.IGNORECASE)
    if final_answer_match:
        return final_answer_match.group(1).upper()
    
    # Strategy 3: Look for pattern like "The answer is X"
    answer_is_match = re.search(r'(?:the\s+)?answer\s+is\s*([ABCD])', response, re.IGNORECASE)
    if answer_is_match:
        return answer_is_match.group(1).upper()
    
    # Strategy 4: Look for conclusive statements like "Therefore, X" or "Thus, X"
    conclusion_match = re.search(r'(?:therefore|thus|hence|so),?\s*(?:the answer is\s*)?([ABCD])', response, re.IGNORECASE)
    if conclusion_match:
        return conclusion_match.group(1).upper()
    
    # Strategy 5: Look for any single letter A, B, C, or D at the end of the response
    end_match = re.search(r'([ABCD])\s*$', response.strip(), re.IGNORECASE)
    if end_match:
        return end_match.group(1).upper()
    
    # Strategy 6: Find all occurrences and take the last one
    letters_found = re.findall(r'\b([ABCD])\b', response, re.IGNORECASE)
    if letters_found:
        return letters_found[-1].upper()
    
    logging.warning(f"Could not extract answer from LLM response: {response[:200]}...")
    return "A"