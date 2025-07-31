import logging
import re
import time
from llm_executor import execute_llm

def parse_input(input_string: str):
    """Parse the input to extract prompt and responses"""
    try:
        # Find the original prompt
        prompt_match = re.search(r'Original prompt:\s*(.*?)(?=\n\s*Response A:)', input_string, re.DOTALL)
        if not prompt_match:
            raise ValueError("Could not find original prompt")
        
        # Find Response A
        response_a_match = re.search(r'Response A:\s*(.*?)(?=\n\s*Response B:)', input_string, re.DOTALL) 
        if not response_a_match:
            raise ValueError("Could not find Response A")
            
        # Find Response B
        response_b_match = re.search(r'Response B:\s*(.*?)(?=\n\s*Which response was preferred)', input_string, re.DOTALL)
        if not response_b_match:
            raise ValueError("Could not find Response B")
        
        original_prompt = prompt_match.group(1).strip()
        response_a = response_a_match.group(1).strip()
        response_b = response_b_match.group(1).strip()
        
        return original_prompt, response_a, response_b
        
    except Exception as e:
        logging.error(f"Error parsing input: {e}")
        raise

def evaluate_responses(prompt, response_a, response_b):
    """Use LLM to determine which response is better"""
    
    # Truncate if responses are too long to avoid token limits
    max_length = 2000
    prompt_truncated = prompt[:max_length] + "..." if len(prompt) > max_length else prompt
    response_a_truncated = response_a[:max_length] + "..." if len(response_a) > max_length else response_a  
    response_b_truncated = response_b[:max_length] + "..." if len(response_b) > max_length else response_b
    
    evaluation_prompt = f"""You are evaluating two responses to determine which one is better. Consider factors like:
- Accuracy and correctness of information
- Completeness and thoroughness 
- Clarity and organization
- Helpfulness and relevance to the original prompt
- Technical quality (if applicable)

Original Prompt: {prompt_truncated}

Response A: {response_a_truncated}

Response B: {response_b_truncated}

Which response is better overall? Answer only with "A" or "B"."""

    try:
        result = execute_llm(evaluation_prompt)
        result = result.strip().upper()
        
        logging.info(f"LLM evaluation result: {result}")
        
        # Extract A or B from the response
        if result == 'A' or (result.endswith('A') and 'B' not in result):
            return 'A'
        elif result == 'B' or (result.endswith('B') and 'A' not in result):
            return 'B'
        else:
            # Try a simpler, more direct prompt
            simple_prompt = f"""Compare these two responses. Which is better?

Prompt: {prompt[:500]}...

A: {response_a[:800]}...

B: {response_b[:800]}...

Answer: A or B"""
            
            simple_result = execute_llm(simple_prompt).strip().upper()
            if 'A' in simple_result and 'B' not in simple_result:
                return 'A'
            elif 'B' in simple_result and 'A' not in simple_result:
                return 'B'
            
    except Exception as e:
        logging.error(f"Error in LLM evaluation: {e}")
    
    # Fallback heuristics if LLM evaluation fails
    logging.warning("Using fallback heuristics")
    
    # Simple length-based heuristic (longer might be more comprehensive)
    if len(response_b) > len(response_a) * 1.3:
        return 'B'
    elif len(response_a) > len(response_b) * 1.3:
        return 'A'
    
    # Default fallback
    return 'A'

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        logging.info("Starting to process input")
        
        # Check for timeout early
        if time.time() - start_time > 110:
            logging.warning("Approaching timeout, returning default")
            return "Answer: A"
        
        # Parse the input
        original_prompt, response_a, response_b = parse_input(input_string)
        
        logging.info(f"Successfully parsed - prompt: {len(original_prompt)} chars, A: {len(response_a)} chars, B: {len(response_b)} chars")
        
        # Check timeout again
        if time.time() - start_time > 110:
            logging.warning("Timeout approaching after parsing")
            return "Answer: A"
        
        # Evaluate responses
        better_response = evaluate_responses(original_prompt, response_a, response_b)
        
        result = f"Answer: {better_response}"
        logging.info(f"Final decision: {result}")
        
        return result
        
    except Exception as e:
        logging.error(f"Error in process_input: {str(e)}")
        return "Answer: A"  # Safe fallback