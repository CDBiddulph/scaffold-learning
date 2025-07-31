import logging
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    """
    Parse the input and determine which response (A or B) is better.
    """
    lines = input_string.strip().split('\n')
    
    # Parse the input sections
    original_prompt = ""
    response_a = ""
    response_b = ""
    
    current_section = None
    
    for line in lines:
        if line.startswith("Original prompt:"):
            original_prompt = line[len("Original prompt:"):].strip()
            current_section = "prompt"
        elif line.startswith("Response A:"):
            response_a = line[len("Response A:"):].strip()
            current_section = "a"
        elif line.startswith("Response B:"):
            response_b = line[len("Response B:"):].strip()
            current_section = "b"
        elif current_section == "a" and not line.startswith("Response B:"):
            if response_a:
                response_a += "\n" + line
            else:
                response_a = line
        elif current_section == "b":
            if response_b:
                response_b += "\n" + line
            else:
                response_b = line
    
    # Clean up responses
    response_a = response_a.strip()
    response_b = response_b.strip()
    
    logging.info(f"Parsed prompt: {original_prompt[:100]}...")
    logging.info(f"Response A length: {len(response_a)}")
    logging.info(f"Response B length: {len(response_b)}")
    
    # Evaluate which response is better using multiple criteria
    evaluation_prompt = f"""You are an expert evaluator comparing two responses to determine which is better. 

Consider these key criteria:
1. ACCURACY: Are the facts correct? Are there any obvious errors?
2. INSTRUCTION FOLLOWING: Does the response do what the prompt actually asked for?
3. HELPFULNESS: Is the response useful and comprehensive?
4. HONESTY: Does it avoid fabrication and admit limitations appropriately?
5. COMPLETENESS: Does it fully address the prompt?

ORIGINAL PROMPT: {original_prompt}

RESPONSE A: {response_a}

RESPONSE B: {response_b}

Based on the criteria above, which response is better overall? Respond with exactly "A" or "B"."""

    try:
        result = execute_llm(evaluation_prompt)
        result_clean = result.strip().upper()
        
        logging.info(f"LLM evaluation result: '{result_clean}'")
        
        # Try to extract A or B from the response
        if result_clean == "A":
            return "Answer: A"
        elif result_clean == "B":
            return "Answer: B"
        elif "RESPONSE A" in result_clean or (result_clean.count("A") > result_clean.count("B") and "A" in result_clean):
            return "Answer: A" 
        elif "RESPONSE B" in result_clean or (result_clean.count("B") > result_clean.count("A") and "B" in result_clean):
            return "Answer: B"
        else:
            # If unclear, try a simpler direct comparison
            logging.warning(f"Unclear result, trying simpler approach: {result_clean}")
            simple_prompt = f"""Compare these two responses and say which is better.

Prompt: {original_prompt}

Response A: {response_a}

Response B: {response_b}

Answer: A or B?"""
            
            simple_result = execute_llm(simple_prompt).strip().upper()
            if "A" in simple_result and "B" not in simple_result:
                return "Answer: A"
            elif "B" in simple_result and "A" not in simple_result:
                return "Answer: B"
            else:
                return "Answer: A"  # Default fallback
                
    except Exception as e:
        logging.error(f"Error in evaluation: {e}")
        return "Answer: A"  # Default fallback