import logging
import time
from llm_executor import execute_llm

def extract_components(input_string: str):
    """Extract the original prompt and two responses from the input."""
    try:
        # Find the original prompt
        prompt_start = input_string.find('Original prompt:')
        if prompt_start == -1:
            raise ValueError("Could not find 'Original prompt:' in input")
        
        # Find Response A
        resp_a_start = input_string.find('Response A:', prompt_start)
        if resp_a_start == -1:
            raise ValueError("Could not find 'Response A:' in input")
        
        # Find Response B  
        resp_b_start = input_string.find('Response B:', resp_a_start)
        if resp_b_start == -1:
            raise ValueError("Could not find 'Response B:' in input")
        
        # Find end marker
        end_marker = input_string.find('Which response was preferred?', resp_b_start)
        if end_marker == -1:
            end_marker = len(input_string)
        
        # Extract each part
        prompt = input_string[prompt_start + len('Original prompt:'):resp_a_start].strip()
        response_a = input_string[resp_a_start + len('Response A:'):resp_b_start].strip()
        response_b = input_string[resp_b_start + len('Response B:'):end_marker].strip()
        
        return prompt, response_a, response_b
        
    except Exception as e:
        logging.error(f"Error extracting components: {e}")
        raise

def evaluate_responses(prompt: str, response_a: str, response_b: str) -> str:
    """Use LLM to evaluate which response is better."""
    
    evaluation_prompt = f"""You are comparing two responses to determine which is better. Consider these factors:

• ACCURACY: Are the facts correct? Are there any errors or misinformation?
• HELPFULNESS: Does it actually help answer the question rather than being dismissive or unhelpful?
• COMPLETENESS: Does it fully address what was asked?
• APPROPRIATENESS: Does it match the tone and context of the question?
• SPECIFICITY: Does it give concrete, actionable information when needed?

Question: {prompt}

Response A:
{response_a}

Response B:
{response_b}

Which response is better overall? Reply with exactly "A" or "B"."""

    try:
        result = execute_llm(evaluation_prompt)
        result = result.strip().upper()
        
        # Look for A or B in the response
        if result == 'A':
            return 'Answer: A'
        elif result == 'B':
            return 'Answer: B'
        elif 'A' in result and 'B' not in result:
            return 'Answer: A'
        elif 'B' in result and 'A' not in result:
            return 'Answer: B'
        else:
            # Fallback with even simpler prompt
            logging.warning(f"Unclear result from evaluation: {result}")
            
            fallback_prompt = f"""Question: {prompt}

Response A: {response_a}

Response B: {response_b}

Which response better answers this question? A or B?"""

            result2 = execute_llm(fallback_prompt)
            result2 = result2.strip().upper()
            
            if 'A' in result2 and 'B' not in result2:
                return 'Answer: A'
            elif 'B' in result2 and 'A' not in result2:
                return 'Answer: B'
            else:
                logging.error(f"Still unclear result: {result2}")
                return 'Answer: A'  # Default fallback
                
    except Exception as e:
        logging.error(f"Error in evaluation: {e}")
        return 'Answer: A'

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Check for timeout early
        if time.time() - start_time > 110:  # Leave 10 second buffer
            logging.warning("Timeout approaching, returning default")
            return 'Answer: A'
            
        prompt, response_a, response_b = extract_components(input_string)
        logging.info(f"Extracted prompt: {prompt[:100]}...")
        logging.info(f"Response A length: {len(response_a)}")
        logging.info(f"Response B length: {len(response_b)}")
        
        result = evaluate_responses(prompt, response_a, response_b)
        logging.info(f"Evaluation result: {result}")
        
        return result
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "Answer: A"