import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    try:
        logging.info("Starting to process scientific question")
        
        # Parse the question and answer choices
        lines = input_string.strip().split('\n')
        
        question_lines = []
        options = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check if this line starts with an option marker
            # Handle both "A)" and "A " patterns (some examples have inconsistent formatting)
            option_match = re.match(r'^([A-D])[\)\s]\s*(.*)', line)
            if option_match:
                letter = option_match.group(1)
                option_text = option_match.group(2).strip()
                if option_text:  # Only add if there's actual content after the letter
                    options[letter] = option_text
                    continue
            
            question_lines.append(line)
        
        # Join question lines and clean up
        question_text = '\n'.join(question_lines)
        
        # Remove the common instruction at the end to avoid confusion
        question_text = re.sub(r'Think step-by-step.*?Answer:\s*<letter>', '', question_text, flags=re.DOTALL | re.IGNORECASE)
        question_text = question_text.strip()
        
        if not options:
            logging.error("No options found in input")
            return "Error: No multiple choice options found"
        
        # Format options nicely
        options_text = '\n'.join([f"{letter}) {text}" for letter, text in sorted(options.items())])
        
        logging.info(f"Parsed question with {len(options)} options")
        
        # Create comprehensive prompt for the LLM
        prompt = f"""You are solving a scientific multiple choice question that requires expert knowledge in physics, chemistry, biology, astronomy, or related fields. Please analyze this question thoroughly.

Question:
{question_text}

Options:
{options_text}

Please think step-by-step to explain your reasoning, considering all relevant scientific principles, formulas, calculations, and concepts. Work through the problem systematically, showing your analysis of each aspect. Then write your final answer in the exact format "Answer: <letter>".
"""

        logging.info("Sending question to LLM")
        response = execute_llm(prompt)
        logging.info("Received response from LLM")
        
        return response.strip()
        
    except Exception as e:
        error_msg = f"Error processing input: {str(e)}"
        logging.error(error_msg)
        return error_msg