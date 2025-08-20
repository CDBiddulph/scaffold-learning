import logging
import re
import time
from llm_executor import execute_llm

def extract_answer_letter(response):
    """Extract the final answer letter from the LLM response."""
    if not response:
        return None
    
    # Look for the specific format requested in the examples: "Answer: <letter>"
    pattern = r'Answer:\s*([A-D])'
    matches = re.findall(pattern, response, re.IGNORECASE)
    if matches:
        return matches[-1].upper()
    
    # Look for other common answer patterns
    patterns = [
        r'(?:final\s+)?answer:\s*([A-D])',
        r'(?:the\s+)?answer\s+is\s*([A-D])',
        r'(?:therefore|thus|so),?\s*(?:the\s+)?answer\s+is\s*([A-D])',
        r'([A-D])\)?\s*(?:is\s+correct|is\s+the\s+answer)',
        r'^([A-D])$',  # Just a single letter on its own line
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, response, re.IGNORECASE | re.MULTILINE)
        if matches:
            return matches[-1].upper()
    
    # If no clear pattern, look for the last occurrence of any choice letter
    # Look for letters that appear after words like "choose", "select", "option"
    choice_context = re.findall(r'(?:choose|select|option|pick)\s+([A-D])', response, re.IGNORECASE)
    if choice_context:
        return choice_context[-1].upper()
    
    # Last resort: find the last occurrence of any single letter A-D
    letters = re.findall(r'\b([A-D])\b', response)
    if letters:
        return letters[-1].upper()
    
    return None

def process_input(input_string: str) -> str:
    """Main function to process the scientific problem."""
    start_time = time.time()
    
    try:
        # Check for timeout buffer
        if time.time() - start_time > 110:  # Leave 10 seconds buffer
            logging.warning("Approaching timeout before starting")
            return "A"
        
        # Use a system prompt to guide the LLM's approach
        system_prompt = """You are an expert in solving advanced scientific problems across multiple disciplines including chemistry, physics, astronomy, biology, and materials science. 

Approach each problem systematically:
1. Identify the key scientific principles involved
2. Work through the problem step-by-step with clear reasoning
3. Show calculations when needed
4. Consider all given information carefully
5. Provide your final answer in the exact format requested

Be precise, thorough, and confident in your scientific reasoning."""
        
        # The input already contains the complete problem and instructions
        response = execute_llm(input_string, system_prompt)
        logging.info(f"LLM response length: {len(response)} characters")
        
        # Extract the answer letter
        answer = extract_answer_letter(response)
        
        if not answer and time.time() - start_time < 110:
            logging.warning("Failed to extract answer, trying follow-up")
            # Try a more direct follow-up question
            follow_up_prompt = f"""Based on your analysis above, what is your final answer?

Respond with exactly: Answer: <letter>

Where <letter> is A, B, C, or D."""
            
            try:
                letter_response = execute_llm(follow_up_prompt)
                answer = extract_answer_letter(letter_response)
                logging.info(f"Follow-up response: {letter_response}")
            except Exception as e:
                logging.error(f"Error in follow-up: {e}")
        
        if not answer:
            logging.error("Could not extract answer letter, defaulting to A")
            return "A"
        
        logging.info(f"Final answer extracted: {answer}")
        return answer
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return "A"  # Default fallback to prevent crashes