import logging
import re
from llm_executor import execute_llm

def parse_scientific_question(input_string):
    """Parse the input to extract question and multiple choice options."""
    
    # Find all option patterns A), B), C), D)
    option_pattern = r'^([ABCD])\)\s*(.*?)(?=^\s*[ABCD]\)|$)'
    
    # Split the input at option A to separate question from options
    parts = re.split(r'\n\s*A\)', input_string, maxsplit=1)
    if len(parts) != 2:
        raise ValueError("Could not find option A to split question from options")
    
    question = parts[0].strip()
    options_section = "A)" + parts[1]
    
    # Extract individual options
    options = {}
    option_matches = re.finditer(r'^([ABCD])\)\s*(.*?)(?=\n\s*[ABCD]\)|$)', options_section, re.MULTILINE | re.DOTALL)
    
    for match in option_matches:
        letter = match.group(1)
        content = match.group(2).strip()
        # Clean up the content by removing extra whitespace and newlines
        content = ' '.join(content.split())
        options[letter] = content
    
    # If regex approach didn't work well, try line-by-line parsing
    if len(options) != 4:
        options = {}
        lines = options_section.split('\n')
        current_option = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            option_match = re.match(r'^([ABCD])\)\s*(.*)', line)
            if option_match:
                current_option = option_match.group(1)
                options[current_option] = option_match.group(2)
            elif current_option and line:
                options[current_option] += ' ' + line
    
    return question, options

def solve_with_llm(question, options):
    """Use LLM to solve the scientific question."""
    
    # Format options clearly
    formatted_options = ""
    for letter in ['A', 'B', 'C', 'D']:
        if letter in options:
            formatted_options += f"{letter}) {options[letter]}\n"
    
    prompt = f"""You are an expert scientist with deep knowledge across physics, chemistry, biology, astronomy, mathematics, and all scientific fields.

Please solve this scientific question:

{question}

{formatted_options}

Think through this step-by-step:
1. Identify the relevant scientific concepts and principles
2. Apply appropriate equations, theories, or reasoning
3. Work through the problem systematically
4. Choose the most accurate answer

End your response with: Answer: X (where X is A, B, C, or D)"""

    try:
        response = execute_llm(prompt)
        return response
    except Exception as e:
        logging.error(f"LLM execution failed: {e}")
        # Try a simpler backup prompt
        backup_prompt = f"Question: {question}\n\nOptions:\n{formatted_options}\nWhich answer is correct? Respond with just the letter A, B, C, or D."
        return execute_llm(backup_prompt)

def extract_answer(response):
    """Extract the answer letter from LLM response."""
    
    # Look for "Answer: X" format (most reliable)
    match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    
    # Look for "The answer is X" or similar patterns
    match = re.search(r'(?:the\s+)?(?:correct\s+)?answer\s+is\s*([ABCD])', response, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    
    # Look for letter at end of response
    match = re.search(r'\b([ABCD])\s*$', response.strip(), re.IGNORECASE)
    if match:
        return match.group(1).upper()
    
    # Find all standalone letters and take the last one
    letters = re.findall(r'\b([ABCD])\b', response, re.IGNORECASE)
    if letters:
        return letters[-1].upper()
    
    # Fallback
    logging.warning(f"Could not extract answer from response: {response[:200]}...")
    return "A"

def process_input(input_string: str) -> str:
    try:
        logging.info("Processing scientific multiple choice question")
        
        # Parse the question and options
        question, options = parse_scientific_question(input_string)
        
        logging.info(f"Question: {question[:100] if len(question) > 100 else question}")
        logging.info(f"Options found: {sorted(options.keys())}")
        
        # Validate we have all 4 options
        if len(options) != 4 or not all(letter in options for letter in ['A', 'B', 'C', 'D']):
            logging.error(f"Invalid options format. Got: {list(options.keys())}")
            return "A"
        
        # Get LLM solution
        response = solve_with_llm(question, options)
        logging.info(f"LLM response length: {len(response)} chars")
        
        # Extract the final answer
        answer = extract_answer(response)
        logging.info(f"Final answer: {answer}")
        
        return answer
        
    except Exception as e:
        logging.error(f"Error processing input: {str(e)}")
        logging.error(f"Input was: {input_string[:200]}...")
        return "A"  # Safe fallback