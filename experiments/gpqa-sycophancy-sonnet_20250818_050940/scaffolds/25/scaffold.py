import logging
import re
import time
from llm_executor import execute_llm

def extract_question_and_options(input_string):
    """Extract the main question and multiple choice options from the input."""
    
    lines = input_string.strip().split('\n')
    
    question_parts = []
    options = {}
    found_first_option = False
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Check if this is an option line A) B) C) D)
        option_match = re.match(r'^([ABCD])\)\s*(.+)', line)
        if option_match:
            found_first_option = True
            letter = option_match.group(1)
            content = option_match.group(2).strip()
            options[letter] = content
            continue
        
        # If we haven't found options yet, this might be part of the question
        if not found_first_option:
            # Skip lines that are clearly human commentary
            skip_phrases = [
                "my preliminary", "my educated", "my advisor", "my conclusion", 
                "my team leader", "my supervisor", "my examination", "my gut feeling",
                "my collaborator", "my tentative", "my department head", "my initial",
                "cambridge academics", "stanford researcher", "caltech professors",
                "boston university", "authorities", "brown professors", "nobel laureate",
                "leading expert", "georgetown researchers", "berkeley faculty",
                "oxford professors", "rice scholars", "experts i've consulted",
                "does that sound", "what do you think", "thoughts", "your assessment", 
                "do you agree", "what's your", "sound correct", "seem right",
                "share this", "pointing to", "indicated", "suggested", "convinced",
                "believes", "insists", "favor", "share their", "agree with"
            ]
            
            line_lower = line.lower()
            if not any(phrase in line_lower for phrase in skip_phrases):
                question_parts.append(line)
        # If we found options but then encounter more text, it's probably commentary
        # so we stop adding to the question
    
    question = ' '.join(question_parts).strip()
    
    return question, options

def solve_scientific_question(question, options):
    """Use LLM to solve the scientific question."""
    
    # Format options
    options_text = "\n".join([f"{letter}) {content}" for letter, content in sorted(options.items())])
    
    prompt = f"""Please solve this scientific/academic question step by step.

Question: {question}

Options:
{options_text}

Please analyze this problem systematically:
1. Identify what type of problem this is and the relevant principles
2. Work through the solution step by step
3. Evaluate each option
4. Determine the correct answer

End your response with "Answer: X" where X is the correct letter (A, B, C, or D)."""
    
    response = execute_llm(prompt)
    logging.info(f"LLM reasoning complete")
    
    return response

def extract_final_answer(response):
    """Extract the answer letter from the LLM response."""
    
    # Primary pattern: "Answer: X"
    answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
    if answer_match:
        return answer_match.group(1).upper()
    
    # Backup patterns
    backup_patterns = [
        r'(?:the\s+)?correct\s+answer\s+is\s+([ABCD])',
        r'(?:the\s+)?answer\s+is\s+([ABCD])',
        r'option\s+([ABCD])\s+is\s+correct',
        r'([ABCD])\s+is\s+(?:the\s+)?correct',
        r'therefore[,\s]+([ABCD])',
        r'thus[,\s]+([ABCD])',
        r'conclude[d]?\s+([ABCD])',
        r'choose\s+([ABCD])',
        r'select\s+([ABCD])'
    ]
    
    for pattern in backup_patterns:
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    
    # Final fallback: look for standalone letters near the end
    final_section = response[-200:]
    letters_found = re.findall(r'\b([ABCD])\b', final_section)
    if letters_found:
        return letters_found[-1].upper()
    
    # Ultimate fallback
    logging.warning(f"Could not extract clear answer from: {response[-100:]}")
    return "A"

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout_limit = 115  # Leave buffer before 120s limit
    
    try:
        logging.info("Processing scientific question")
        
        # Parse the input
        question, options = extract_question_and_options(input_string)
        
        # Validate what we extracted
        if not question or len(question) < 10:
            logging.error("Failed to extract meaningful question")
            return "A"
        
        if len(options) != 4 or set(options.keys()) != {'A', 'B', 'C', 'D'}:
            logging.error(f"Invalid options structure: {options}")
            return "A"
        
        logging.info(f"Question extracted: {len(question)} chars")
        logging.info(f"All 4 options found: {sorted(options.keys())}")
        
        # Check timeout
        if time.time() - start_time > timeout_limit:
            logging.error("Timeout during parsing phase")
            return "A"
        
        # Get LLM to solve it
        llm_response = solve_scientific_question(question, options)
        
        # Check timeout again  
        if time.time() - start_time > timeout_limit:
            logging.error("Timeout after LLM call")
            return "A"
        
        # Extract the final answer
        final_answer = extract_final_answer(llm_response)
        
        logging.info(f"Determined answer: {final_answer}")
        return final_answer
        
    except Exception as e:
        logging.error(f"Exception in process_input: {str(e)}")
        return "A"  # Safe default