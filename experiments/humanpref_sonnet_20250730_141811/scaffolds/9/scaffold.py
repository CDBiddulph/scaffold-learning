import logging
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Parse the input to extract components
        lines = input_string.strip().split('\n')
        
        # Find key section markers
        prompt_start = response_a_start = response_b_start = end_pos = None
        
        for i, line in enumerate(lines):
            if line.startswith('Original prompt:'):
                prompt_start = i
            elif line.startswith('Response A:'):
                response_a_start = i
            elif line.startswith('Response B:'):
                response_b_start = i
            elif line.startswith('Which response was preferred?'):
                end_pos = i
                break
        
        if not all(x is not None for x in [prompt_start, response_a_start, response_b_start]):
            logging.error("Could not parse input format - missing required markers")
            return "B"
        
        # Extract content sections
        original_prompt = '\n'.join(lines[prompt_start:response_a_start])[len('Original prompt:'):].strip()
        response_a = '\n'.join(lines[response_a_start:response_b_start])[len('Response A:'):].strip()
        response_b = '\n'.join(lines[response_b_start:end_pos or len(lines)])[len('Response B:'):].strip()
        
        if not all([original_prompt, response_a, response_b]):
            logging.error("One or more sections is empty after parsing")
            return "B"
        
        logging.info(f"Parsed - Prompt: '{original_prompt[:50]}...', A: {len(response_a)} chars, B: {len(response_b)} chars")
        
        # Check timeout
        if time.time() - start_time > 100:  # Leave buffer for LLM call
            logging.warning("Approaching timeout, returning default")
            return "B"
        
        # Use LLM to evaluate which response is better
        evaluation_prompt = f"""You are evaluating two responses to determine which one is objectively better. Consider these key factors:

1. CORRECTNESS: Is the information accurate and factual?
2. INSTRUCTION FOLLOWING: Does it properly address what was asked?
3. HELPFULNESS: How useful is it to the user?
4. APPROPRIATENESS: Is the tone, style, and level of detail suitable?
5. COMPLETENESS: Does it adequately answer the question?

Original prompt: {original_prompt}

Response A: {response_a}

Response B: {response_b}

Analyze both responses carefully and determine which is better overall. Consider that sometimes a shorter, more direct response is better, and sometimes a more detailed response is better - it depends on what the prompt is asking for.

Which response is better? Answer with exactly one letter: A or B"""

        try:
            judgment = execute_llm(evaluation_prompt)
            judgment_clean = judgment.strip().upper()
            
            logging.info(f"LLM judgment: {judgment_clean}")
            
            # Parse the judgment
            if judgment_clean == 'A' or (judgment_clean.startswith('A') and 'B' not in judgment_clean):
                return "A"
            elif judgment_clean == 'B' or (judgment_clean.startswith('B') and 'A' not in judgment_clean):
                return "B"
            elif 'A' in judgment_clean and 'B' not in judgment_clean:
                return "A"
            elif 'B' in judgment_clean and 'A' not in judgment_clean:
                return "B"
            else:
                # If still unclear, try a more direct approach
                logging.warning(f"Unclear judgment: {judgment_clean}")
                
                simple_prompt = f"""Compare these responses to: {original_prompt}

A: {response_a}

B: {response_b}

Better response: """
                
                simple_result = execute_llm(simple_prompt).strip().upper()
                
                if 'A' in simple_result and 'B' not in simple_result:
                    return "A"
                elif 'B' in simple_result:
                    return "B"
                else:
                    logging.warning(f"Still unclear, defaulting to B: {simple_result}")
                    return "B"
                    
        except Exception as e:
            logging.error(f"Error during LLM evaluation: {e}")
            return "B"
            
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "B"