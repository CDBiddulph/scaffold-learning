import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        logging.info("Processing scientific multiple choice question")
        
        # Clean up the input - remove the instruction about thinking step-by-step since we'll handle that
        question_content = input_string.strip()
        
        # Remove the instruction line if present to avoid confusion
        lines = question_content.split('\n')
        filtered_lines = []
        for line in lines:
            if not ("Think step-by-step to explain your reasoning" in line or 
                   "write your final answer in the format" in line):
                filtered_lines.append(line)
        
        clean_question = '\n'.join(filtered_lines).strip()
        
        # Create an effective prompt for the LLM
        system_prompt = """You are a world-class scientist with deep expertise across all scientific disciplines including physics, chemistry, biology, astronomy, mathematics, and engineering. You excel at analyzing complex scientific problems systematically."""
        
        user_prompt = f"""Solve this scientific multiple choice question carefully:

{clean_question}

Please:
1. Identify the key scientific concepts and principles involved
2. Analyze each answer option systematically
3. Apply relevant scientific knowledge and reasoning
4. Eliminate incorrect options step by step
5. Select the best answer

End your response with: "FINAL ANSWER: X" where X is the letter (A, B, C, or D) of your chosen answer."""

        # Check timeout before making LLM call (leave buffer time)
        if time.time() - start_time > 100:
            logging.warning("Approaching timeout, returning default answer")
            return "A"
            
        # Get LLM response
        response = execute_llm(user_prompt, system_prompt)
        logging.info(f"LLM response length: {len(response)} characters")
        
        # Extract the final answer using multiple strategies
        
        # Strategy 1: Look for "FINAL ANSWER: X"
        match = re.search(r'FINAL\s+ANSWER:\s*([A-D])', response, re.IGNORECASE)
        if match:
            answer = match.group(1).upper()
            logging.info(f"Found answer with FINAL ANSWER pattern: {answer}")
            return answer
            
        # Strategy 2: Look for other common answer patterns
        answer_patterns = [
            r'Answer:\s*([A-D])',
            r'answer\s+is\s*([A-D])',
            r'I\s+choose\s*([A-D])',
            r'correct\s+answer\s+is\s*([A-D])',
            r'Therefore,?\s*([A-D])',
            r'conclusion:\s*([A-D])',
            r'select\s*([A-D])'
        ]
        
        for pattern in answer_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Found answer with pattern '{pattern}': {answer}")
                return answer
        
        # Strategy 3: Look for option markers (A), B), etc.)
        option_markers = re.findall(r'\b([A-D])\)', response)
        if option_markers:
            answer = option_markers[-1].upper()
            logging.info(f"Found answer from option marker: {answer}")
            return answer
            
        # Strategy 4: Look for any isolated A, B, C, D letters
        isolated_letters = re.findall(r'\b([A-D])\b', response)
        if isolated_letters:
            # Take the last one mentioned
            answer = isolated_letters[-1].upper()
            logging.info(f"Found answer from isolated letters: {answer}")
            return answer
        
        # Fallback: return A if nothing found
        logging.warning("Could not extract answer from LLM response, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error in process_input: {str(e)}")
        # Safe fallback
        return "A"