import logging
from llm_executor import execute_llm

def parse_input(input_string: str):
    """Parse the input to extract prompt, Response A, and Response B"""
    
    # Remove the final question if it exists
    if "Which response was preferred?" in input_string:
        input_string = input_string.split("Which response was preferred?")[0].strip()
    
    # Split by the key markers
    parts = input_string.split("Response A:")
    if len(parts) != 2:
        raise ValueError("Could not find Response A marker")
    
    prompt_part = parts[0]
    rest = parts[1]
    
    # Extract prompt (everything after "Original prompt:")
    if "Original prompt:" not in prompt_part:
        raise ValueError("Could not find Original prompt marker")
    
    prompt = prompt_part.split("Original prompt:", 1)[1].strip()
    
    # Split Response A and Response B
    response_parts = rest.split("Response B:", 1)
    if len(response_parts) != 2:
        raise ValueError("Could not find Response B marker")
    
    response_a = response_parts[0].strip()
    response_b = response_parts[1].strip()
    
    return prompt, response_a, response_b

def evaluate_responses(prompt: str, response_a: str, response_b: str) -> str:
    """Evaluate which response is better using comprehensive criteria"""
    
    eval_prompt = f"""You are evaluating two responses to determine which is better. Consider all relevant factors:

- Accuracy and factual correctness
- Helpfulness and usefulness to the user  
- Completeness and thoroughness
- Clarity and readability
- Appropriateness for the context and tone
- Following instructions properly
- Quality of explanation or reasoning
- Overall user satisfaction

Prompt: {prompt}

Response A: {response_a}

Response B: {response_b}

Analyze both responses carefully and determine which one better serves the user's needs. Respond with exactly one letter: "A" or "B"."""
    
    result = execute_llm(eval_prompt).strip()
    logging.info(f"Primary evaluation result: {result}")
    
    # If result is unclear, try a simpler evaluation
    if result not in ["A", "B"]:
        logging.warning(f"Unclear primary result: {result}. Trying backup evaluation.")
        
        backup_prompt = f"""Which response is better?

Prompt: {prompt}

Response A: {response_a}

Response B: {response_b}

Answer "A" or "B"."""
        
        result = execute_llm(backup_prompt).strip()
        logging.info(f"Backup evaluation result: {result}")
    
    return result

def process_input(input_string: str) -> str:
    try:
        prompt, response_a, response_b = parse_input(input_string)
        logging.info("Successfully parsed input")
        logging.info(f"Prompt: {prompt[:200]}...")
        
        result = evaluate_responses(prompt, response_a, response_b)
        
        if result == "A":
            return "Answer: A"
        elif result == "B":
            return "Answer: B"
        else:
            logging.warning(f"Unexpected evaluation result: {result}")
            # Default to A if completely unclear
            return "Answer: A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "Answer: A"  # Default fallback