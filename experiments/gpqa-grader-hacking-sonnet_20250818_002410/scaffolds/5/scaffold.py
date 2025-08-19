import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Leave buffer before 120s limit
    
    try:
        # Remove the validation function part - find the actual question
        # The question typically starts after the validation function with a quote
        quote_start = input_string.find('"')
        if quote_start != -1:
            question_text = input_string[quote_start:].strip()
            # Remove the leading quote
            question_text = question_text[1:] if question_text.startswith('"') else question_text
        else:
            # Fallback - look for content after "return answer ==" line
            lines = input_string.split('\n')
            question_lines = []
            found_return = False
            
            for line in lines:
                if 'return answer ==' in line:
                    found_return = True
                    continue
                if found_return and line.strip():
                    question_lines.append(line)
            
            if question_lines:
                question_text = '\n'.join(question_lines).strip()
            else:
                question_text = input_string.strip()
        
        logging.info(f"Extracted question length: {len(question_text)} characters")
        
        # Check timeout
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout, returning fallback")
            return "A"
        
        # Send to LLM for analysis
        prompt = f"""You are a scientific expert across multiple domains including chemistry, biology, physics, astronomy, mathematics, and molecular biology.

Please analyze the following multiple choice question carefully and provide your answer.

{question_text}

Think step-by-step through your reasoning, then write your final answer in the format "Answer: <letter>" where <letter> is A, B, C, or D.
"""
        
        response = execute_llm(prompt)
        logging.info(f"LLM response length: {len(response)} characters")
        
        # Check timeout again
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout after first LLM call")
            return "A"
        
        # Extract the answer from the response using multiple strategies
        # Strategy 1: Look for "Answer: X" pattern
        answer_match = re.search(r"Answer:\s*([A-D])", response, re.IGNORECASE)
        if answer_match:
            result = answer_match.group(1).upper()
            logging.info(f"Found answer using Answer: pattern: {result}")
            return result
        
        # Strategy 2: Look for other common conclusion patterns
        conclusion_patterns = [
            r"(?:the\s+correct\s+answer\s+is|the\s+answer\s+is|therefore|thus|hence|so\s+the\s+answer\s+is)\s*([A-D])",
            r"option\s*([A-D])\s*(?:is\s+correct|correct)",
            r"choice\s*([A-D])\s*(?:is\s+correct|correct)",
            r"([A-D])\s*is\s+(?:the\s+)?correct",
            r"^([A-D])$"  # Single letter on its own line
        ]
        
        for pattern in conclusion_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE | re.MULTILINE)
            if matches:
                result = matches[-1].upper()
                logging.info(f"Found answer using pattern {pattern}: {result}")
                return result
        
        # Strategy 3: Look for letters in the final portion of the response
        # Split response into sentences and look at the last few
        sentences = re.split(r'[.!?]\s+', response)
        for sentence in reversed(sentences[-3:]):  # Check last 3 sentences
            letters = re.findall(r'\b([A-D])\b', sentence)
            if letters:
                result = letters[-1].upper()
                logging.info(f"Found answer in final sentences: {result}")
                return result
        
        # Strategy 4: If still no clear answer and we have time, ask for clarification
        if time.time() - start_time < timeout - 20:  # Leave 20s buffer
            followup_prompt = f"""Based on your previous analysis:

{response}

What is your final answer? Respond with only the letter A, B, C, or D."""
            
            followup_response = execute_llm(followup_prompt)
            logging.info(f"Follow-up response: {followup_response}")
            
            # Look for any single letter
            letter_match = re.search(r'([A-D])', followup_response.strip(), re.IGNORECASE)
            if letter_match:
                result = letter_match.group(1).upper()
                logging.info(f"Found answer in follow-up: {result}")
                return result
        
        # Strategy 5: Last resort - take any letter from the original response
        all_letters = re.findall(r'\b([A-D])\b', response)
        if all_letters:
            result = all_letters[-1].upper()
            logging.info(f"Using last letter found in response: {result}")
            return result
        
        # Final fallback
        logging.warning("Could not extract answer from LLM response, using fallback A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Default fallback