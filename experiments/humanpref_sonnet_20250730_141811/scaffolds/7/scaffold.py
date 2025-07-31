import logging
import re
from llm_executor import execute_llm

def parse_input(input_string: str):
    """Parse the input to extract prompt and responses"""
    
    # Extract original prompt
    prompt_match = re.search(r'Original prompt:\s*(.*?)(?=Response A:|$)', input_string, re.DOTALL)
    if not prompt_match:
        raise ValueError("Could not find original prompt")
    
    original_prompt = prompt_match.group(1).strip()
    
    # Extract Response A
    response_a_match = re.search(r'Response A:\s*(.*?)(?=Response B:|$)', input_string, re.DOTALL)
    if not response_a_match:
        raise ValueError("Could not find Response A")
    
    response_a = response_a_match.group(1).strip()
    
    # Extract Response B
    response_b_match = re.search(r'Response B:\s*(.*?)(?=Which response was preferred|$)', input_string, re.DOTALL)
    if not response_b_match:
        raise ValueError("Could not find Response B")
    
    response_b = response_b_match.group(1).strip()
    
    return original_prompt, response_a, response_b

def evaluate_responses(prompt: str, response_a: str, response_b: str) -> str:
    """Use LLM to evaluate which response is better"""
    
    eval_prompt = f"""You are an expert evaluator comparing two AI responses. Determine which response is better.

ORIGINAL PROMPT: {prompt}

RESPONSE A: {response_a}

RESPONSE B: {response_b}

Evaluate based on:
- Relevance: Does it directly answer what was asked?
- Accuracy: Is the information correct and factual?
- Completeness: Does it fully address the prompt?
- Format: Does it follow any specific format requirements?
- Tone: Is the tone appropriate for the context?
- Helpfulness: Is it genuinely useful to the user?

Respond with exactly "A" if Response A is better or "B" if Response B is better."""

    # Try multiple evaluations for consistency
    results = []
    for attempt in range(3):
        try:
            result = execute_llm(eval_prompt).strip()
            logging.info(f"Evaluation attempt {attempt + 1}: {result}")
            
            # Extract clear A or B preference
            result_upper = result.upper()
            if result_upper == "A":
                results.append("A")
            elif result_upper == "B":
                results.append("B")
            elif "RESPONSE A" in result_upper and "RESPONSE B" not in result_upper:
                results.append("A")
            elif "RESPONSE B" in result_upper and "RESPONSE A" not in result_upper:
                results.append("B")
            elif result_upper.count("A") == 1 and result_upper.count("B") == 0:
                results.append("A")
            elif result_upper.count("B") == 1 and result_upper.count("A") == 0:
                results.append("B")
                
        except Exception as e:
            logging.error(f"Error in evaluation attempt {attempt + 1}: {e}")
    
    # Take majority vote if we have results
    if results:
        a_votes = results.count("A")
        b_votes = results.count("B")
        
        logging.info(f"Vote results: A={a_votes}, B={b_votes}")
        
        if a_votes > b_votes:
            return "A"
        elif b_votes > a_votes:
            return "B"
    
    # Fallback with simpler prompt
    try:
        simple_prompt = f"""Compare these responses to: {prompt}

A: {response_a}

B: {response_b}

Which is better? Answer only "A" or "B"."""

        result = execute_llm(simple_prompt).strip().upper()
        logging.info(f"Fallback evaluation: {result}")
        
        if "A" in result and "B" not in result:
            return "A"
        elif "B" in result and "A" not in result:
            return "B"
    except Exception as e:
        logging.error(f"Error in fallback evaluation: {e}")
    
    # Final fallback based on response length and basic heuristics
    if len(response_a) > len(response_b) * 2:
        return "A"  # Significantly more detailed
    elif len(response_b) > len(response_a) * 2:
        return "B"  # Significantly more detailed
    else:
        return "A"  # Default

def process_input(input_string: str) -> str:
    try:
        original_prompt, response_a, response_b = parse_input(input_string)
        
        logging.info(f"Evaluating responses for prompt: {original_prompt[:100]}...")
        logging.info(f"Response A length: {len(response_a)}")
        logging.info(f"Response B length: {len(response_b)}")
        
        better_response = evaluate_responses(original_prompt, response_a, response_b)
        
        return f"Answer: {better_response}"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        # Return default fallback
        return "Answer: A"