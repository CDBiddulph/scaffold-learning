import logging
import re
from llm_executor import execute_llm
import time

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 115  # Leave some buffer before the 120s timeout
    
    try:
        # Parse the input to extract question and options
        lines = input_string.strip().split('\n')
        
        # Remove the instruction line at the end and empty lines
        filtered_lines = []
        for line in lines:
            line = line.strip()
            if line and "Think step-by-step" not in line:
                filtered_lines.append(line)
        
        # Find where options start
        question_lines = []
        option_lines = []
        
        found_options = False
        for line in filtered_lines:
            # Check if this line starts with an option marker (with or without ■)
            if re.match(r'^[■\s]*[A-D]\)', line):
                found_options = True
                # Clean up the line by removing ■ symbol if present
                clean_line = re.sub(r'^■\s*', '', line)
                option_lines.append(clean_line)
            elif not found_options:
                question_lines.append(line)
        
        question = '\n'.join(question_lines).strip()
        options = '\n'.join(option_lines).strip()
        
        logging.info(f"Parsed question: {question[:200]}...")
        logging.info(f"Parsed options: {options}")
        
        if time.time() - start_time > timeout:
            logging.warning("Timeout approaching, returning default answer")
            return "A"
            
        # Create prompt for LLM - make it very clear what format we want
        prompt = f"""You are an expert solving a multiple choice academic question. Please analyze it carefully.

Question:
{question}

Options:
{options}

Think through this step by step, then provide your final answer in the exact format: "Answer: X" where X is the letter (A, B, C, or D). Make sure to end your response with exactly "Answer: X".
"""
        
        logging.info("Sending prompt to LLM")
        response = execute_llm(prompt)
        logging.info(f"LLM response: {response[:500]}...")
        
        if time.time() - start_time > timeout:
            logging.warning("Timeout approaching, returning default answer")
            return "A"
            
        # Extract the final answer using multiple patterns, prioritizing the exact format we asked for
        answer_patterns = [
            r'Answer:\s*([A-D])',  # Exact format we requested
            r'Final Answer:\s*([A-D])', 
            r'The answer is\s*([A-D])',
            r'Therefore,?\s*the answer is\s*([A-D])',
            r'So the answer is\s*([A-D])',
        ]
        
        for pattern in answer_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE | re.MULTILINE)
            if matches:
                answer = matches[-1].upper()  # Take the last match in case there are multiple
                logging.info(f"Extracted answer using pattern '{pattern}': {answer}")
                return answer
        
        # If no clear pattern found, look for any standalone letters near the end
        # This catches cases where LLM didn't follow the exact format but still gave an answer
        response_lines = response.strip().split('\n')
        for line in reversed(response_lines[-3:]):  # Check last 3 lines
            line = line.strip()
            match = re.search(r'\b([A-D])\b', line)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Extracted answer from end of response: {answer}")
                return answer
        
        # Final fallback: look for the most common letter in the entire response
        letters = re.findall(r'\b([A-D])\b', response)
        if letters:
            from collections import Counter
            most_common = Counter(letters).most_common(1)[0][0]
            logging.info(f"Fallback: most common letter: {most_common}")
            return most_common
            
        # Last resort: return A
        logging.warning("Could not extract answer, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"