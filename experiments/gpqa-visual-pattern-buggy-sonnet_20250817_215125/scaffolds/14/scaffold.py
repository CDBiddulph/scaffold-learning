import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Parse the input to extract the question and options
        lines = input_string.strip().split('\n')
        
        # Find the main question text (everything before the options)
        question_lines = []
        options_start_idx = -1
        
        for i, line in enumerate(lines):
            # Look for option patterns (A), B), C), D) or ■ A), ■ B), etc.
            if re.match(r'^■?\s*[A-D]\)', line.strip()):
                options_start_idx = i
                break
            question_lines.append(line)
        
        if options_start_idx == -1:
            logging.error("Could not find options in the input")
            return "A"  # Default fallback
        
        question = '\n'.join(question_lines).strip()
        
        # Extract options
        options = []
        for i in range(options_start_idx, len(lines)):
            line = lines[i].strip()
            match = re.match(r'^■?\s*([A-D])\)\s*(.*)', line)
            if match:
                letter = match.group(1)
                text = match.group(2)
                options.append(f"{letter}) {text}")
        
        logging.info(f"Parsed question with {len(options)} options")
        
        # Check timeout
        if time.time() - start_time > 100:  # Leave buffer before 120s timeout
            return "A"
        
        # Create a comprehensive prompt for the LLM
        prompt = f"""You are an expert scientist with deep knowledge in chemistry, physics, biology, astronomy, and mathematics. Please solve this scientific question step by step.

Question:
{question}

Options:
{chr(10).join(options)}

Please:
1. Read the question carefully and identify what is being asked
2. Apply relevant scientific principles and knowledge
3. Work through the solution systematically 
4. Show your reasoning clearly
5. Choose the best answer from the given options

Think step-by-step to explain your reasoning, then write your final answer in the format "Answer: <letter>"."""

        logging.info("Sending question to LLM")
        response = execute_llm(prompt)
        
        # Check timeout again
        if time.time() - start_time > 110:
            return "A"
        
        # Extract the final answer from the response
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            final_answer = answer_match.group(1).upper()
            logging.info(f"Extracted answer: {final_answer}")
            return final_answer
        
        # If we can't find "Answer: X", look for other answer indicators
        # Look for patterns like "The answer is X" or "(X)" at the end
        alt_patterns = [
            r'(?:the\s+)?(?:correct\s+)?answer\s+is\s+([A-D])',
            r'(?:therefore|thus|so),?\s+([A-D])',
            r'\(([A-D])\)\s*$',
            r'option\s+([A-D])',
            r'choice\s+([A-D])'
        ]
        
        for pattern in alt_patterns:
            alt_match = re.search(pattern, response, re.IGNORECASE)
            if alt_match:
                final_answer = alt_match.group(1).upper()
                logging.info(f"Extracted answer using pattern '{pattern}': {final_answer}")
                return final_answer
        
        # Last resort: look for the final letter mentioned in the response
        letter_matches = re.findall(r'\b([A-D])\b', response)
        if letter_matches:
            final_answer = letter_matches[-1]
            logging.info(f"Extracted answer from last letter mention: {final_answer}")
            return final_answer
        
        logging.error("Could not extract answer from LLM response")
        logging.error(f"LLM response: {response[:500]}...")  # Log first 500 chars
        return "A"  # Default fallback
    
    except Exception as e:
        logging.error(f"Error processing input: {str(e)}")
        return "A"  # Default fallback