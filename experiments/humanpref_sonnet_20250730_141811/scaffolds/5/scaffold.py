import logging
import time
from llm_executor import execute_llm

def parse_input(input_string: str):
    """Parse the input to extract original prompt and both responses."""
    
    try:
        # Find the key markers
        if "Original prompt:" not in input_string:
            raise ValueError("Could not find 'Original prompt:' marker")
        if "Response A:" not in input_string:
            raise ValueError("Could not find 'Response A:' marker") 
        if "Response B:" not in input_string:
            raise ValueError("Could not find 'Response B:' marker")
        
        # Extract original prompt
        parts = input_string.split("Original prompt:", 1)[1]
        parts = parts.split("Response A:", 1)
        original_prompt = parts[0].strip()
        
        # Extract Response A
        remaining = parts[1]
        parts = remaining.split("Response B:", 1) 
        response_a = parts[0].strip()
        
        # Extract Response B
        remaining = parts[1]
        if "Which response was preferred?" in remaining:
            response_b = remaining.split("Which response was preferred?", 1)[0].strip()
        else:
            response_b = remaining.strip()
        
        return original_prompt, response_a, response_b
        
    except Exception as e:
        logging.error(f"Error parsing input: {e}")
        raise

def evaluate_responses(prompt: str, response_a: str, response_b: str):
    """Use LLM to evaluate which response is better."""
    
    evaluation_prompt = f"""You are comparing two responses to determine which one is better. Evaluate them based on:

1. **Accuracy**: Is the information correct and factual?
2. **Relevance**: Does it directly address what was asked?
3. **Completeness**: Does it provide adequate coverage for the question type?
4. **Clarity**: Is it well-organized and easy to understand?
5. **Appropriateness**: Is the tone, depth, and approach suitable for the question?
6. **Helpfulness**: Would this genuinely help the person who asked?
7. **Following requirements**: Does it meet any specific requirements mentioned in the prompt?

Original question/prompt:
{prompt}

Response A:
{response_a}

Response B:
{response_b}

Which response is better overall? Consider all the criteria above, paying special attention to accuracy, relevance to the specific question asked, and meeting any explicit requirements.

Answer with just "A" or "B"."""

    try:
        result = execute_llm(evaluation_prompt)
        result = result.strip().upper()
        
        logging.info(f"LLM evaluation result: {result}")
        
        # Parse the result
        if result.startswith('A'):
            return 'A'
        elif result.startswith('B'):
            return 'B'
        elif 'A' in result and 'B' not in result:
            return 'A'
        elif 'B' in result and 'A' not in result:
            return 'B'
        else:
            # If unclear, try a more direct approach with truncated responses
            logging.warning("First evaluation unclear, trying direct comparison")
            direct_prompt = f"""Which response better answers this question? Reply only with "A" or "B".

Question: {prompt[:200]}...

Response A: {response_a[:400]}...

Response B: {response_b[:400]}..."""
            
            direct_result = execute_llm(direct_prompt).strip().upper()
            if direct_result.startswith('A'):
                return 'A'
            elif direct_result.startswith('B'):
                return 'B'
            else:
                logging.warning(f"Could not parse evaluation results: {result}, {direct_result}")
                return 'A'  # Fallback
                
    except Exception as e:
        logging.error(f"Error in evaluation: {e}")
        return 'A'  # Fallback

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Parse input
        original_prompt, response_a, response_b = parse_input(input_string)
        
        logging.info("Successfully parsed input")
        logging.info(f"Prompt length: {len(original_prompt)}")
        logging.info(f"Response A length: {len(response_a)}")  
        logging.info(f"Response B length: {len(response_b)}")
        
        # Check timeout
        elapsed = time.time() - start_time
        if elapsed > 100:  # Leave 20s buffer before 120s timeout
            logging.warning("Timeout approaching during parsing")
            return "A"
        
        # Evaluate responses
        result = evaluate_responses(original_prompt, response_a, response_b)
        
        # Final timeout check
        elapsed = time.time() - start_time
        if elapsed > 115:  # Leave 5s buffer
            logging.warning("Timeout approaching after evaluation")
            
        logging.info(f"Final evaluation: {result}")
        return result
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return "A"