import logging
import re
import time
from llm_executor import execute_llm

def extract_question_and_options(input_string):
    """Extract the question text and answer options from the input."""
    lines = input_string.strip().split('\n')
    
    # Find where options start (lines that start with A), B), C), D))
    option_start = -1
    for i, line in enumerate(lines):
        if re.match(r'^[A-D]\)', line.strip()):
            option_start = i
            break
    
    if option_start == -1:
        # No standard options found, return everything as question
        return input_string.strip(), {}
    
    question_text = '\n'.join(lines[:option_start]).strip()
    
    # Extract options
    options = {}
    current_option = None
    current_text = ""
    
    for line in lines[option_start:]:
        line = line.strip()
        match = re.match(r'^([A-D])\)\s*(.*)', line)
        if match:
            # Save previous option if exists
            if current_option:
                options[current_option] = current_text.strip()
            # Start new option
            current_option = match.group(1)
            current_text = match.group(2)
        else:
            # Continue current option
            if current_option and line:
                current_text += " " + line
    
    # Save last option
    if current_option:
        options[current_option] = current_text.strip()
    
    return question_text, options

def identify_scientific_domain(question):
    """Identify the primary scientific domain of the question."""
    try:
        prompt = f"""
Identify the primary scientific domain of this question. Choose from: physics, chemistry, biology, astronomy, mathematics, or interdisciplinary.

Question: {question[:500]}...

Respond with just the domain name (one word).
"""
        response = execute_llm(prompt)
        domain = response.strip().lower()
        if domain in ['physics', 'chemistry', 'biology', 'astronomy', 'mathematics', 'interdisciplinary']:
            return domain
    except Exception as e:
        logging.error(f"Error identifying domain: {e}")
    
    return "interdisciplinary"

def solve_scientific_question(question, options, max_time=100):
    """Use LLM to solve the scientific question with domain-specific approach."""
    start_time = time.time()
    
    # Identify the domain first
    domain = identify_scientific_domain(question)
    logging.info(f"Identified domain: {domain}")
    
    if time.time() - start_time > max_time:
        return "A"
    
    # Format the complete question
    formatted_question = question + "\n\n"
    for letter, text in options.items():
        formatted_question += f"{letter}) {text}\n"
    
    # Create domain-specific expert prompt
    expert_context = {
        'physics': "You are a physics expert with deep knowledge of quantum mechanics, relativity, electromagnetism, thermodynamics, and particle physics.",
        'chemistry': "You are a chemistry expert with deep knowledge of organic chemistry, physical chemistry, spectroscopy, and reaction mechanisms.", 
        'biology': "You are a biology expert with deep knowledge of molecular biology, genetics, cell biology, and biochemistry.",
        'astronomy': "You are an astronomy expert with deep knowledge of stellar physics, planetary science, and observational astronomy.",
        'mathematics': "You are a mathematics expert with deep knowledge of calculus, statistics, and mathematical physics.",
        'interdisciplinary': "You are a scientific expert with broad knowledge across physics, chemistry, biology, and astronomy."
    }
    
    prompt = f"""
{expert_context.get(domain, expert_context['interdisciplinary'])}

Analyze this scientific question step by step. Consider all relevant principles, calculations, and concepts. Show your reasoning clearly.

{formatted_question}

Think step-by-step to explain your reasoning, then write your final answer in the format "Answer: <letter>"
"""
    
    if time.time() - start_time > max_time:
        return "A"
    
    try:
        response = execute_llm(prompt)
        logging.info(f"Expert analysis: {response[:300]}...")
        
        # Extract the answer letter
        answer_match = re.search(r'Answer:\s*([A-D])', response)
        if answer_match:
            return answer_match.group(1)
        
        # Look for final answer at the end of response
        lines = response.strip().split('\n')
        for line in reversed(lines):
            line = line.strip()
            if line in ['A', 'B', 'C', 'D']:
                return line
            match = re.search(r'\b([A-D])\b', line)
            if match:
                return match.group(1)
        
        # Fallback: ask for clarification
        clarification_prompt = f"""
Based on your previous analysis, what is the correct answer to this question? Respond with only the letter (A, B, C, or D).

Previous analysis: {response}
"""
        
        if time.time() - start_time < max_time:
            clarification = execute_llm(clarification_prompt)
            for char in clarification.strip():
                if char in ['A', 'B', 'C', 'D']:
                    return char
            
    except Exception as e:
        logging.error(f"Error in expert analysis: {e}")
    
    return "A"  # Default fallback

def process_input(input_string: str) -> str:
    """Process the scientific question and return the answer letter."""
    start_time = time.time()
    
    try:
        # Extract question and options
        question, options = extract_question_and_options(input_string)
        logging.info(f"Question extracted: {len(question)} chars")
        logging.info(f"Options found: {list(options.keys())}")
        
        # Handle non-multiple choice questions
        if not options:
            logging.info("No multiple choice options detected")
            try:
                response = execute_llm(f"""
Analyze and answer this scientific question:

{input_string}

Provide a clear, concise answer.
""")
                return response.strip()
            except Exception as e:
                logging.error(f"Error with open question: {e}")
                return "Unable to determine answer"
        
        # Check time constraint
        if time.time() - start_time > 100:
            logging.warning("Time running out, using fallback")
            return "A"
        
        # Solve the multiple choice question
        answer = solve_scientific_question(question, options, 100 - (time.time() - start_time))
        logging.info(f"Final answer selected: {answer}")
        
        # Validate answer is valid option
        if answer not in options:
            logging.warning(f"Invalid answer {answer}, defaulting to A")
            return "A"
        
        return answer
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"