import logging
import re
import time
from llm_executor import execute_llm

def parse_input(input_string: str):
    """Parse the input to extract prompt and responses"""
    
    # Find original prompt
    prompt_match = re.search(r'Original prompt:\s*(.*?)(?=\n\s*Response A:)', input_string, re.DOTALL)
    if not prompt_match:
        raise ValueError("Could not find original prompt")
    
    # Find Response A  
    response_a_match = re.search(r'Response A:\s*(.*?)(?=\n\s*Response B:)', input_string, re.DOTALL)
    if not response_a_match:
        raise ValueError("Could not find Response A")
    
    # Find Response B
    response_b_match = re.search(r'Response B:\s*(.*?)(?=\n\s*Which response was preferred\?|$)', input_string, re.DOTALL)
    if not response_b_match:
        raise ValueError("Could not find Response B")
    
    original_prompt = prompt_match.group(1).strip()
    response_a = response_a_match.group(1).strip()
    response_b = response_b_match.group(1).strip()
    
    return original_prompt, response_a, response_b

def compare_responses(prompt, response_a, response_b):
    """Compare two responses and determine which is better"""
    
    comparison_prompt = f"""You must choose which response is better for the given question.

QUESTION: {prompt}

RESPONSE A: {response_a}

RESPONSE B: {response_b}

Which response better answers the question? Consider accuracy, helpfulness, completeness, and relevance.
Respond with exactly one letter: A or B"""

    try:
        result = execute_llm(comparison_prompt)
        
        # Clean and parse result
        result = result.strip().upper()
        
        # Look for clear A or B
        if result == 'A':
            return 'A'
        elif result == 'B':
            return 'B'
        elif result.startswith('A') or result.endswith('A'):
            return 'A'
        elif result.startswith('B') or result.endswith('B'):
            return 'B'
        elif 'RESPONSE A' in result or 'A IS BETTER' in result:
            return 'A'
        elif 'RESPONSE B' in result or 'B IS BETTER' in result:
            return 'B'
        else:
            # Try a simpler approach as fallback
            return simple_comparison(prompt, response_a, response_b)
            
    except Exception as e:
        logging.error(f"Comparison failed: {e}")
        return simple_comparison(prompt, response_a, response_b)

def simple_comparison(prompt, response_a, response_b):
    """Simple fallback comparison"""
    try:
        # Use a more direct prompt
        simple_prompt = f"""Question: {prompt}

A: {response_a[:200]}{'...' if len(response_a) > 200 else ''}

B: {response_b[:200]}{'...' if len(response_b) > 200 else ''}

Which is better? A or B?"""
        
        result = execute_llm(simple_prompt)
        if 'B' in result.upper() and 'A' not in result.upper():
            return 'B'
        elif 'A' in result.upper():
            return 'A'
        else:
            # Final heuristic - longer responses are often better for complex questions
            return 'B' if len(response_b) > len(response_a) * 1.5 else 'A'
            
    except Exception as e:
        logging.error(f"Simple comparison failed: {e}")
        return 'A'

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Parse the input
        original_prompt, response_a, response_b = parse_input(input_string)
        logging.info("Successfully parsed input")
        
        # Check timeout
        if time.time() - start_time > 100:
            logging.warning("Approaching timeout, using fallback")
            return 'A'
        
        # Compare responses
        result = compare_responses(original_prompt, response_a, response_b)
        logging.info(f"Comparison result: {result}")
        
        return result
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return 'A'