import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Leave buffer before 120s timeout
    
    try:
        # Parse the input to separate question from choices
        text = input_string.strip()
        
        # Split on choice markers to find question vs choices
        choice_pattern = r'\n(?=[A-D]\))'
        parts = re.split(choice_pattern, text)
        
        if len(parts) < 2:
            # Fallback parsing if pattern doesn't work
            lines = text.split('\n')
            question_lines = []
            choice_lines = []
            found_choices = False
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                if re.match(r'^[A-D]\)', line):
                    found_choices = True
                    choice_lines.append(line)
                elif found_choices:
                    choice_lines.append(line)
                else:
                    question_lines.append(line)
            
            question = '\n'.join(question_lines).strip()
            choices = '\n'.join(choice_lines).strip()
        else:
            question = parts[0].strip()
            choices = '\n'.join(parts[1:]).strip()
        
        logging.info(f"Parsed question length: {len(question)}")
        logging.info(f"Parsed choices length: {len(choices)}")
        
        # Check if we're running out of time
        if time.time() - start_time > timeout:
            logging.error("Timeout reached before LLM call")
            return "A"
        
        # Create focused prompt for the LLM
        prompt = f"""Analyze this scientific question step-by-step and determine the correct answer.

Question: {question}

Answer choices:
{choices}

Think through the problem systematically, then provide your final answer in the format "Answer: <letter>".
"""
        
        system_prompt = """You are an expert scientist with deep knowledge across physics, chemistry, biology, astronomy, and other scientific domains. 
Analyze each question methodically and provide clear reasoning for your answer choice."""
        
        # Get LLM response
        response = execute_llm(prompt, system_prompt)
        logging.info(f"LLM response received, length: {len(response)}")
        
        # Extract answer using multiple strategies
        
        # Strategy 1: Look for explicit "Answer: X" format
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Found explicit answer: {answer}")
            return answer
        
        # Strategy 2: Look for final answer in parentheses or quotes
        final_answer_patterns = [
            r'\(([A-D])\)\s*$',  # (A) at end
            r'"([A-D])"',         # "A" in quotes
            r'letter\s*([A-D])',  # letter A
            r'option\s*([A-D])',  # option A
            r'choice\s*([A-D])',  # choice A
        ]
        
        for pattern in final_answer_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Found answer with pattern {pattern}: {answer}")
                return answer
        
        # Strategy 3: Look for the last standalone letter
        standalone_letters = re.findall(r'\b([A-D])\b', response)
        if standalone_letters:
            answer = standalone_letters[-1].upper()
            logging.info(f"Using last standalone letter: {answer}")
            return answer
        
        # Strategy 4: If we still haven't found an answer, try a direct approach
        if time.time() - start_time < timeout - 10:  # Make sure we have time
            direct_prompt = f"""What is the correct answer to this question? Respond with only the letter A, B, C, or D.

{question}

{choices}
"""
            
            direct_response = execute_llm(direct_prompt, system_prompt)
            logging.info(f"Direct response: {direct_response.strip()}")
            
            # Extract single letter from direct response
            letter_match = re.search(r'([A-D])', direct_response)
            if letter_match:
                answer = letter_match.group(1).upper()
                logging.info(f"Direct extraction: {answer}")
                return answer
        
        # Final fallback
        logging.warning("Could not extract clear answer, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error in process_input: {str(e)}")
        # Return a default answer rather than crashing
        return "A"