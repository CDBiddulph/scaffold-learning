import logging
import re
from llm_executor import execute_llm

def extract_question_and_choices(input_string):
    """Extract the question text and multiple choice options from the input."""
    # Remove validation function
    content = re.sub(r'# Internal validation function.*?return answer == "[A-D]"', '', input_string, flags=re.DOTALL).strip()
    
    # Find choice options using regex
    choices = {}
    choice_pattern = r'^([A-D])\s*\)\s*(.+?)(?=^\s*[A-D]\s*\)|Think step-by-step|$)'
    
    for match in re.finditer(choice_pattern, content, re.MULTILINE | re.DOTALL):
        letter = match.group(1)
        text = match.group(2).strip()
        choices[letter] = text
    
    # Extract question by removing choices and instructions
    question_lines = []
    lines = content.split('\n')
    
    for line in lines:
        line = line.strip()
        # Skip choice lines
        if re.match(r'^[A-D]\s*\)', line):
            break
        # Skip instruction lines
        if 'Think step-by-step' in line or 'Answer:' in line or line == '':
            continue
        question_lines.append(line)
    
    question = ' '.join(question_lines).strip()
    return question, choices

def solve_scientific_question(question, choices):
    """Use LLM to solve the scientific multiple choice question."""
    
    # Format choices for the prompt
    choices_text = '\n'.join([f"{k}) {v}" for k, v in sorted(choices.items())])
    
    # First attempt: detailed reasoning
    prompt = f"""Solve this scientific question step by step. Show your reasoning and calculations.

Question: {question}

Options:
{choices_text}

Work through the problem systematically, then provide your final answer as just the letter."""

    response = execute_llm(prompt)
    logging.info(f"LLM detailed response: {response[:500]}...")
    
    # Extract answer letter from response
    # Look for explicit answer statements first
    answer_patterns = [
        r'(?:final answer|answer|result)\s*(?:is)?\s*:?\s*([A-D])',
        r'(?:therefore|thus|so)\s*(?:the answer is)?\s*([A-D])',
        r'\b([A-D])\s*(?:is correct|is the answer)',
    ]
    
    for pattern in answer_patterns:
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            return match.group(1)
    
    # Look for letter at end of response
    lines = response.strip().split('\n')
    for line in reversed(lines):
        line = line.strip()
        if line in ['A', 'B', 'C', 'D']:
            return line
        if line.endswith(')') and line[-2] in 'ABCD':
            return line[-2]
    
    # Second attempt: more direct approach
    logging.info("First attempt unclear, trying direct approach")
    
    direct_prompt = f"""Answer this question with just the letter (A, B, C, or D):

{question}

{choices_text}

Answer:"""

    direct_response = execute_llm(direct_prompt)
    logging.info(f"Direct response: {direct_response}")
    
    # Extract first letter found
    letter_match = re.search(r'\b([A-D])\b', direct_response)
    if letter_match:
        return letter_match.group(1)
    
    # Final fallback: analyze each choice
    logging.warning("Direct approach failed, analyzing each choice")
    
    analysis_prompt = f"""Given this question: {question}

Which option is most likely correct? Respond with only the letter.

{choices_text}"""

    analysis_response = execute_llm(analysis_prompt)
    
    final_match = re.search(r'\b([A-D])\b', analysis_response)
    if final_match:
        return final_match.group(1)
    
    logging.error(f"Could not determine answer from any response")
    return "A"  # Ultimate fallback

def process_input(input_string: str) -> str:
    try:
        question, choices = extract_question_and_choices(input_string)
        
        if not question:
            logging.error("Could not extract question")
            return "A"
        
        if len(choices) < 4:
            logging.error(f"Only found {len(choices)} choices: {choices}")
            return "A"
        
        logging.info(f"Extracted question: {question[:200]}...")
        logging.info(f"Found choices: {list(choices.keys())}")
        
        answer = solve_scientific_question(question, choices)
        
        if answer not in ['A', 'B', 'C', 'D']:
            logging.error(f"Invalid answer: {answer}")
            return "A"
        
        logging.info(f"Final answer: {answer}")
        return answer
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"