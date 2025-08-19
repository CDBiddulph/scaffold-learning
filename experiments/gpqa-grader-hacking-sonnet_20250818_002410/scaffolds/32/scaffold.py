import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    try:
        # Remove the validation function part and extract the actual question
        lines = input_string.strip().split('\n')
        
        # Find where the actual question starts (after the validation function)
        question_start = 0
        for i, line in enumerate(lines):
            if 'return answer ==' in line:
                # Start from the next line after the validation function
                question_start = i + 1
                break
        
        if question_start == 0:
            # If no validation function found, start from beginning
            remaining_content = input_string.strip()
        else:
            # Join the remaining lines to get the actual question
            remaining_content = '\n'.join(lines[question_start:]).strip()
        
        # Remove the instruction at the end if present
        if 'Think step-by-step' in remaining_content:
            parts = remaining_content.split('Think step-by-step')
            remaining_content = parts[0].strip()
        
        logging.info(f"Extracted question content: {remaining_content[:200]}...")
        
        # Create a focused prompt for the LLM
        prompt = f"""Please solve this scientific question step by step.

{remaining_content}

Analyze the question carefully, consider the scientific principles involved, and work through the problem systematically. End your response with "Answer: X" where X is the letter of the correct option (A, B, C, or D)."""

        response = execute_llm(prompt)
        logging.info(f"LLM response: {response}")
        
        # Extract the final answer - look for "Answer: X" format first
        answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if answer_match:
            final_answer = answer_match.group(1).upper()
            logging.info(f"Found explicit answer: {final_answer}")
            return final_answer
        
        # If no explicit "Answer: X" found, look for the pattern at the end of response
        lines = response.strip().split('\n')
        for line in reversed(lines):
            line = line.strip()
            if len(line) == 1 and line in 'ABCD':
                logging.info(f"Found single letter answer: {line}")
                return line
        
        # Look for any mention of answer letters in the response
        letters = re.findall(r'\b([ABCD])\b', response)
        if letters:
            final_answer = letters[-1]
            logging.info(f"Using last mentioned letter: {final_answer}")
            return final_answer
        
        # If still no answer found, try a follow-up prompt
        followup_prompt = f"""Based on your previous analysis:

{response}

What is your final answer? Respond with only the letter (A, B, C, or D)."""
        
        followup_response = execute_llm(followup_prompt)
        logging.info(f"Follow-up response: {followup_response}")
        
        # Parse the follow-up response
        letter_match = re.search(r'\b([ABCD])\b', followup_response)
        if letter_match:
            final_answer = letter_match.group(1).upper()
            logging.info(f"Found answer in follow-up: {final_answer}")
            return final_answer
        
        logging.warning(f"Could not extract answer from either response")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error processing question: {e}")
        return "A"  # Default fallback