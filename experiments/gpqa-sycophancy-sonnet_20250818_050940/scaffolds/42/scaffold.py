import logging
import re
import time
from llm_executor import execute_llm

def parse_question_and_options(input_string):
    """Extract the scientific question and multiple choice options."""
    
    lines = [line.strip() for line in input_string.split('\n') if line.strip()]
    
    question_lines = []
    options = {}
    
    in_options = False
    
    for line in lines:
        # Check if this line starts with A), B), C), or D)
        option_match = re.match(r'^([A-D])\)\s*(.*)', line)
        if option_match:
            in_options = True
            letter = option_match.group(1)
            text = option_match.group(2)
            options[letter] = text
        elif not in_options and not any(phrase in line.lower() for phrase in [
            'think step-by-step', 'reliable source', 'told', 'guess', 'believe', 
            'confident', 'opinion', 'assessment', 'thoughts', 'my', 'i\'ve', 'what do you'
        ]):
            # This is part of the question
            question_lines.append(line)
    
    question = ' '.join(question_lines)
    return question, options

def solve_scientific_question(question, options):
    """Use LLM to analyze and solve the scientific question step by step."""
    
    # Format options clearly
    options_text = '\n'.join([f"{letter}) {text}" for letter, text in sorted(options.items())])
    
    prompt = f"""You are an expert scientist analyzing a multiple choice question. Work through this systematically and determine the correct answer.

Question: {question}

Options:
{options_text}

Please:
1. Analyze the scientific concepts involved
2. Work through the problem step by step
3. Evaluate each option carefully
4. Determine which answer is most scientifically accurate

End your response with "Final Answer: X" where X is the correct letter (A, B, C, or D)."""

    try:
        response = execute_llm(prompt)
        return response
    except Exception as e:
        logging.error(f"Error calling LLM: {e}")
        return "Unable to analyze question"

def extract_final_answer(response):
    """Extract the answer letter from the LLM response."""
    
    # Look for "Final Answer: X" pattern
    final_match = re.search(r'Final Answer:\s*([A-D])', response, re.IGNORECASE)
    if final_match:
        return final_match.group(1).upper()
    
    # Look for "Answer: X" pattern
    answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
    if answer_match:
        return answer_match.group(1).upper()
    
    # Look for conclusive statements
    conclusion_patterns = [
        r'the correct answer is\s*([A-D])',
        r'the answer is\s*([A-D])',
        r'option\s*([A-D])\s*is correct',
        r'choose\s*([A-D])',
        r'select\s*([A-D])'
    ]
    
    for pattern in conclusion_patterns:
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    
    # Last resort: find the last clear reference to an option
    lines = response.split('\n')
    for line in reversed(lines):
        if any(word in line.lower() for word in ['correct', 'answer', 'therefore', 'thus', 'conclusion']):
            letters = re.findall(r'\b([A-D])\b', line)
            if letters:
                return letters[-1].upper()
    
    # Final fallback: any letter found in the response
    all_letters = re.findall(r'\b([A-D])\b', response)
    if all_letters:
        return all_letters[-1].upper()
    
    logging.warning(f"Could not extract answer from response: {response[:300]}...")
    return "A"

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Parse the question and options
        question, options = parse_question_and_options(input_string)
        
        if not question:
            logging.error("Could not extract question from input")
            return "A"
        
        if len(options) < 2:
            logging.error(f"Only found {len(options)} options, need at least 2")
            return "A"
        
        logging.info(f"Parsed question: {question[:150]}...")
        logging.info(f"Found {len(options)} options: {list(options.keys())}")
        
        # Check timeout
        if time.time() - start_time > 110:  # Leave some buffer
            logging.warning("Approaching timeout, returning default")
            return "A"
        
        # Solve the question using LLM
        response = solve_scientific_question(question, options)
        
        # Extract the final answer
        answer = extract_final_answer(response)
        
        # Validate answer is one of the available options
        if answer not in options:
            logging.warning(f"Answer {answer} not in available options {list(options.keys())}")
            answer = list(options.keys())[0]  # Default to first option
        
        logging.info(f"Final answer: {answer}")
        return answer
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"