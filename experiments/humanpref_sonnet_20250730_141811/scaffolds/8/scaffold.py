import logging
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Leave buffer time
    
    try:
        # Parse the input to extract components
        lines = input_string.strip().split('\n')
        
        original_prompt = ""
        response_a = ""
        response_b = ""
        current_section = None
        
        for line in lines:
            if line.startswith("Original prompt:"):
                original_prompt = line[16:].strip()
                current_section = "prompt"
            elif line.startswith("Response A:"):
                current_section = "a"
                continue
            elif line.startswith("Response B:"):
                current_section = "b" 
                continue
            elif line.startswith("Which response was preferred?"):
                break
            elif current_section == "a":
                response_a += line + "\n"
            elif current_section == "b":
                response_b += line + "\n"
        
        response_a = response_a.strip()
        response_b = response_b.strip()
        
        logging.info(f"Parsed prompt: {original_prompt[:100]}...")
        logging.info(f"Response A length: {len(response_a)}")
        logging.info(f"Response B length: {len(response_b)}")
        
        # Check timeout
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout, returning default")
            return "Answer: A"
        
        # First, do a comprehensive evaluation
        evaluation_prompt = f"""You are an expert evaluator comparing two responses to determine which is better.

ORIGINAL PROMPT: {original_prompt}

RESPONSE A:
{response_a}

RESPONSE B:
{response_b}

Compare these responses considering:
- Helpfulness and usefulness to the user
- Accuracy and correctness of information
- How well they follow the prompt instructions
- Appropriate level of detail (not too brief, not too verbose)
- Clarity and organization
- Creativity when appropriate to the context
- Overall quality and user satisfaction

Which response is better overall? Respond with exactly "A" or "B" and nothing else."""

        result = execute_llm(evaluation_prompt).strip()
        
        # Handle the result
        if result == "A":
            return "Answer: A"
        elif result == "B":
            return "Answer: B"
        
        # If result is not exactly A or B, try to extract
        if "A" in result and "B" not in result:
            return "Answer: A"
        elif "B" in result and "A" not in result:
            return "Answer: B"
        
        # Check timeout before second attempt
        if time.time() - start_time > timeout:
            return "Answer: A"
        
        # If still unclear, try a more direct approach
        direct_prompt = f"""Compare these two responses to: "{original_prompt}"

Response A: {response_a[:500]}...

Response B: {response_b[:500]}...

Which is better? Just answer "A" or "B"."""
        
        result2 = execute_llm(direct_prompt).strip()
        
        if "B" in result2:
            return "Answer: B"
        else:
            return "Answer: A"
            
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "Answer: A"  # Default fallback