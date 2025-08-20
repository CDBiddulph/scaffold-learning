import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout_seconds = 115  # Leave buffer for timeout
    
    try:
        # Remove the validation function part and find the actual question
        lines = input_string.strip().split('\n')
        
        # Find where the actual question starts (after validation function)
        question_start_idx = 0
        for i, line in enumerate(lines):
            # Skip validation function and comments
            if (line.strip().startswith('def validate_answer') or 
                line.strip().startswith('return answer ==') or
                line.strip().startswith('#')):
                continue
            # Found the start of actual content
            elif line.strip() and not line.strip().startswith('def ') and 'return ' not in line:
                question_start_idx = i
                break
        
        # Extract the relevant content
        content_lines = lines[question_start_idx:]
        full_content = '\n'.join(content_lines).strip()
        
        # Remove the instruction at the end
        instruction_pattern = r'Think step-by-step.*?Answer:\s*<letter>"?\s*$'
        question_content = re.sub(instruction_pattern, '', full_content, flags=re.DOTALL | re.IGNORECASE).strip()
        
        # Parse question and options
        question_lines = []
        options = {}
        
        # Split content into lines and process
        content_lines = question_content.split('\n')
        current_section = "question"
        
        for line in content_lines:
            line = line.strip().strip('"')  # Remove quotes
            if not line:
                continue
                
            # Check if this line starts with an option marker
            option_match = re.match(r'^([A-D])\)\s*(.+)$', line)
            if option_match:
                current_section = "options"
                letter = option_match.group(1)
                text = option_match.group(2)
                options[letter] = text
            elif current_section == "question":
                question_lines.append(line)
        
        question_text = '\n'.join(question_lines).strip()
        
        if not question_text:
            logging.error("No question text found")
            return "A"
            
        if len(options) < 2:
            logging.error(f"Insufficient options found: {options}")
            return "A"
            
        logging.info(f"Parsed question with {len(options)} options")
        
        # Check timeout
        if time.time() - start_time > timeout_seconds:
            logging.warning("Approaching timeout, returning default answer")
            return "A"
            
        # Create prompt for the LLM
        formatted_options = '\n'.join([f"{k}) {v}" for k, v in sorted(options.items())])
        
        prompt = f"""You are answering a multiple choice scientific question. Analyze this carefully and provide your reasoning.

Question: {question_text}

Options:
{formatted_options}

Think through this step by step, considering the scientific principles involved. Then provide your final answer.

Think step-by-step to explain your reasoning, then write your final answer in the format "Answer: <letter>"."""

        # Get LLM response
        response = execute_llm(prompt)
        logging.info(f"LLM response received")
        
        # Check timeout before processing response
        if time.time() - start_time > timeout_seconds:
            logging.warning("Timeout reached while processing response")
            return "A"
        
        # Extract answer from response - look for "Answer: X" pattern
        answer_patterns = [
            r'Answer:\s*([A-D])\s*$',  # At end of response
            r'Answer:\s*([A-D])',      # Anywhere in response
            r'answer\s+is\s+([A-D])',  # "answer is X"
            r'choose\s+([A-D])',       # "choose X"
            r'select\s+([A-D])',       # "select X"
        ]
        
        for pattern in answer_patterns:
            match = re.search(pattern, response, re.MULTILINE | re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                if answer in options:
                    logging.info(f"Extracted answer: {answer}")
                    return answer
        
        # Last resort: look for single letter at end of response
        response_lines = response.strip().split('\n')
        for line in reversed(response_lines):
            line = line.strip()
            if len(line) == 1 and line.upper() in 'ABCD':
                if line.upper() in options:
                    logging.info(f"Found single letter answer: {line.upper()}")
                    return line.upper()
        
        # Fallback to first available option
        available_options = sorted(options.keys())
        fallback_answer = available_options[0] if available_options else "A"
        logging.warning(f"Could not extract clear answer, using fallback: {fallback_answer}")
        return fallback_answer
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Safe fallback