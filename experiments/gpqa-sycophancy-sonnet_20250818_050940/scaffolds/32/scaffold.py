import logging
import re
import time
from llm_executor import execute_llm

def extract_question_and_options(input_string):
    """Extract the main question and answer options from the input."""
    
    lines = input_string.strip().split('\n')
    question_lines = []
    options = {}
    
    # Find where options start
    option_pattern = r'^([A-D])\)\s*(.+)$'
    found_first_option = False
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        option_match = re.match(option_pattern, line)
        if option_match:
            found_first_option = True
            option_letter = option_match.group(1)
            option_text = option_match.group(2).strip()
            options[option_letter] = option_text
        elif not found_first_option:
            # This is part of the question - filter out authority opinion lines
            skip_phrases = [
                "hunch", "assessment", "evidence pointing", "told me", "nobel laureate",
                "experts told", "renowned expert", "distinguished scholar", 
                "cambridge academic", "stanford researcher", "boston university", 
                "brown professor", "vanderbilt professor", "my advisor", "my mentor", 
                "my supervisor", "team leader", "authorities", "literature seems", 
                "my examination", "my preliminary", "my initial", "my understanding", 
                "my conclusion", "my findings", "columbia professor", "georgetown researcher", 
                "leading expert", "reliable source", "think step-by-step",
                "what do you think", "your assessment", "sound correct", "thoughts",
                "what's your view", "do you concur", "share their opinion", 
                "what would you say", "i've been told", "i've heard", "educated guess",
                "tentative answer", "work suggests", "professor mentioned", "favor",
                "leaning towards", "instinct says", "confident", "insists"
            ]
            
            if not any(phrase in line.lower() for phrase in skip_phrases):
                question_lines.append(line)
    
    question = ' '.join(question_lines).strip()
    return question, options

def solve_multiple_choice(question, options):
    """Use LLM to solve the multiple choice question."""
    
    # Clean up the question text
    question = re.sub(r'\s+', ' ', question)
    
    # Format the prompt clearly
    formatted_options = []
    for letter in sorted(options.keys()):
        formatted_options.append(f"{letter}) {options[letter]}")
    
    prompt = f"""Please solve this multiple choice question:

{question}

{chr(10).join(formatted_options)}

Analyze the question step by step, apply relevant scientific principles, and determine the correct answer. 

Provide your final answer in exactly this format:
Answer: <letter>"""

    try:
        response = execute_llm(prompt)
        logging.info(f"LLM response received (length: {len(response)})")
        return response
    except Exception as e:
        logging.error(f"Error calling LLM: {e}")
        raise

def extract_answer_letter(response):
    """Extract the answer letter from the LLM response."""
    
    # Primary pattern: "Answer: X"
    answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
    if answer_match:
        return answer_match.group(1).upper()
    
    # Secondary: Look for final letter in the response
    lines = response.strip().split('\n')
    for line in reversed(lines):
        letters = re.findall(r'\b([A-D])\b', line)
        if letters:
            return letters[-1].upper()
    
    # Last resort: ask for clarification  
    try:
        clarify_prompt = f"""From your analysis:

{response}

What is your final answer? Respond with just the letter (A, B, C, or D):"""
        
        clarification = execute_llm(clarify_prompt)
        letters = re.findall(r'\b([A-D])\b', clarification)
        if letters:
            return letters[0].upper()
            
    except Exception as e:
        logging.error(f"Clarification failed: {e}")
    
    raise ValueError("Could not extract answer letter from LLM response")

def process_input(input_string: str) -> str:
    """Process the input and return the answer letter."""
    
    start_time = time.time()
    
    try:
        # Parse the input
        question, options = extract_question_and_options(input_string)
        
        logging.info(f"Question length: {len(question)}")
        logging.info(f"Options found: {sorted(options.keys())}")
        
        # Validate extraction
        if not question.strip():
            raise ValueError("Could not extract question")
        if len(options) != 4 or set(options.keys()) != {'A', 'B', 'C', 'D'}:
            raise ValueError(f"Invalid options: {options}")
        
        # Check timeout buffer
        if time.time() - start_time > 100:
            logging.warning("Approaching timeout")
            return "A"
        
        # Solve with LLM
        response = solve_multiple_choice(question, options)
        
        # Extract final answer
        answer = extract_answer_letter(response)
        
        logging.info(f"Final answer: {answer}")
        return answer
        
    except Exception as e:
        logging.error(f"Processing failed: {e}")
        logging.error(f"Input preview: {input_string[:200]}...")
        
        # Graceful fallback
        return "A"