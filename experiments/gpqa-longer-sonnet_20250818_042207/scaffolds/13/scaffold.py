import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Parse the input to extract the question and options
        lines = [line.strip() for line in input_string.strip().split('\n') if line.strip()]
        
        # Find where the options start (lines that start with A), B), C), D))
        option_pattern = r'^[ABCD]\)'
        question_lines = []
        options = {}
        
        in_options = False
        current_option = None
        
        for line in lines:
            if re.match(option_pattern, line):
                in_options = True
                # Extract the option letter and text
                match = re.match(r'^([ABCD])\)\s*(.+)', line)
                if match:
                    current_option = match.group(1)
                    text = match.group(2)
                    options[current_option] = text
            elif in_options and current_option and line and not re.match(option_pattern, line):
                # This is a continuation of the current option
                options[current_option] += " " + line
            elif not in_options:
                question_lines.append(line)
        
        question = '\n'.join(question_lines).strip()
        
        logging.info(f"Extracted question: {question[:200]}...")
        logging.info(f"Extracted {len(options)} options: {list(options.keys())}")
        
        if not question or len(options) < 2:
            raise ValueError(f"Could not parse question and options. Question length: {len(question)}, Options: {len(options)}")
        
        # Check timeout
        if time.time() - start_time > 100:  # Leave buffer for processing
            logging.warning("Approaching timeout, returning early")
            return "A"
        
        # Construct the prompt for the LLM
        options_text = '\n'.join([f"{letter}) {text}" for letter, text in sorted(options.items())])
        
        prompt = f"""You are an expert scientist with deep knowledge across chemistry, physics, biology, astronomy, mathematics, and other scientific fields.

Please analyze this multiple choice question step by step and select the correct answer.

{question}

{options_text}

Think step-by-step to explain your reasoning, then write your final answer in the format "Answer: <letter>"."""

        # Get the LLM response
        response = execute_llm(prompt)
        
        logging.info(f"LLM response received, length: {len(response)}")
        
        # Extract the answer from the response
        # Look for "Answer: X" pattern first (matches expected format)
        answer_pattern = r'Answer:\s*([ABCD])'
        match = re.search(answer_pattern, response, re.IGNORECASE)
        
        if match:
            answer = match.group(1).upper()
            logging.info(f"Extracted answer: {answer}")
            return answer
        
        # Fallback patterns
        fallback_patterns = [
            r'Final Answer:\s*([ABCD])',
            r'The answer is\s*([ABCD])',
            r'Therefore,?\s*([ABCD])',
            r'\b([ABCD])\s*is\s+correct',
            r'Option\s*([ABCD])',
            r'Choice\s*([ABCD])',
        ]
        
        for pattern in fallback_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Fallback extracted answer using pattern '{pattern}': {answer}")
                return answer
        
        # Last resort: find the last standalone letter mention
        letters = re.findall(r'\b([ABCD])\b', response)
        if letters:
            answer = letters[-1].upper()
            logging.info(f"Final fallback extracted answer: {answer}")
            return answer
        
        # Ultimate fallback
        logging.warning("Could not extract any answer from LLM response")
        logging.warning(f"Response was: {response[:500]}...")
        return "A"
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return "A"  # Safe fallback