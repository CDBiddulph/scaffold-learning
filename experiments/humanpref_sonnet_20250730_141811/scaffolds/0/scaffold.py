import logging
import time
from llm_executor import execute_llm

def parse_input(input_string: str):
    """Parse the input to extract original prompt, Response A, and Response B"""
    
    lines = input_string.strip().split('\n')
    
    original_prompt_lines = []
    response_a_lines = []
    response_b_lines = []
    
    current_section = None
    
    for line in lines:
        line_stripped = line.strip()
        
        if line_stripped.startswith("Original prompt:"):
            current_section = "prompt"
            # Add the content after "Original prompt:" if it exists
            content = line_stripped[len("Original prompt:"):].strip()
            if content:
                original_prompt_lines.append(content)
        elif line_stripped.startswith("Response A:"):
            current_section = "response_a"
            # Add the content after "Response A:" if it exists
            content = line_stripped[len("Response A:"):].strip()
            if content:
                response_a_lines.append(content)
        elif line_stripped.startswith("Response B:"):
            current_section = "response_b"
            # Add the content after "Response B:" if it exists
            content = line_stripped[len("Response B:"):].strip()
            if content:
                response_b_lines.append(content)
        elif line_stripped.startswith("Which response was preferred?"):
            # End of responses
            break
        else:
            # Add to current section
            if current_section == "prompt":
                original_prompt_lines.append(line)
            elif current_section == "response_a":
                response_a_lines.append(line)
            elif current_section == "response_b":
                response_b_lines.append(line)
    
    original_prompt = '\n'.join(original_prompt_lines).strip()
    response_a = '\n'.join(response_a_lines).strip()
    response_b = '\n'.join(response_b_lines).strip()
    
    return original_prompt, response_a, response_b

def evaluate_responses(original_prompt, response_a, response_b):
    """Use LLM to evaluate which response is better"""
    
    evaluation_prompt = f"""You are evaluating two responses to determine which one is better. Use these criteria in order of importance:

1. INSTRUCTION FOLLOWING: Does it do what was actually asked? Follow specific requirements?
2. ACCURACY: Is the information correct and factual?
3. COMPLETENESS: Does it provide adequate information without being excessive?
4. HELPFULNESS: Is it useful to someone who asked this question?
5. CLARITY: Is it well-organized and easy to understand?

Original Prompt: {original_prompt}

Response A:
{response_a}

Response B:
{response_b}

Which response is better overall? Consider each criterion carefully.

Respond with exactly one letter: A or B"""

    try:
        result = execute_llm(evaluation_prompt)
        result = result.strip().upper()
        
        # Extract final answer - try multiple patterns
        if result.endswith("A"):
            return "A"
        elif result.endswith("B"):
            return "B"
        elif "ANSWER: A" in result.upper():
            return "A"
        elif "ANSWER: B" in result.upper():
            return "B"
        elif result.startswith("A"):
            return "A"
        elif result.startswith("B"):
            return "B"
        elif "A" in result and "B" not in result:
            return "A"
        elif "B" in result and "A" not in result:
            return "B"
            
        logging.warning(f"LLM returned unexpected result: {result}")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error in LLM evaluation: {e}")
        return "A"  # Default fallback

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Parse the input
        original_prompt, response_a, response_b = parse_input(input_string)
        
        logging.info(f"Parsed prompt: {original_prompt[:100]}...")
        logging.info(f"Response A length: {len(response_a)}")
        logging.info(f"Response B length: {len(response_b)}")
        
        if not original_prompt or not response_a or not response_b:
            logging.error("Failed to parse all required sections")
            logging.error(f"Prompt: '{original_prompt[:50]}...'")
            logging.error(f"Response A: '{response_a[:50]}...'")
            logging.error(f"Response B: '{response_b[:50]}...'")
            return "A"
        
        # Check time remaining
        if time.time() - start_time > 100:  # Leave 20 second buffer
            logging.warning("Approaching timeout, returning default")
            return "A"
        
        # Evaluate which response is better
        result = evaluate_responses(original_prompt, response_a, response_b)
        
        logging.info(f"Evaluation result: {result}")
        return result
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return "A"  # Default fallback