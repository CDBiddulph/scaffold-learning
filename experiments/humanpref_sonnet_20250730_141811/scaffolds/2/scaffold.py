import logging
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        lines = input_string.strip().split('\n')
        
        # Parse the input to extract original prompt and responses
        original_prompt = ""
        response_a = ""
        response_b = ""
        
        current_section = None
        for line in lines:
            if line.startswith('Original prompt:'):
                current_section = "prompt"
                original_prompt = line[len('Original prompt:'):].strip()
            elif line.startswith('Response A:'):
                current_section = "response_a"
                response_a = line[len('Response A:'):].strip()
            elif line.startswith('Response B:'):
                current_section = "response_b"
                response_b = line[len('Response B:'):].strip()
            elif line.startswith('Which response was preferred?'):
                break
            elif current_section == "prompt" and line.strip():
                original_prompt += "\n" + line
            elif current_section == "response_a" and not line.startswith('Response B:'):
                response_a += "\n" + line
            elif current_section == "response_b" and not line.startswith('Which response was preferred?'):
                response_b += "\n" + line
        
        original_prompt = original_prompt.strip()
        response_a = response_a.strip()
        response_b = response_b.strip()
        
        if not original_prompt or not response_a or not response_b:
            logging.error("Failed to parse input sections properly")
            logging.error(f"Prompt: '{original_prompt[:100]}...'")
            logging.error(f"Response A: '{response_a[:100]}...'")
            logging.error(f"Response B: '{response_b[:100]}...'")
            return "A"
        
        logging.info(f"Successfully parsed - Prompt: {len(original_prompt)} chars, A: {len(response_a)} chars, B: {len(response_b)} chars")
        
        # Check timeout
        if time.time() - start_time > 110:
            logging.warning("Approaching timeout, returning default")
            return "A"
        
        # Create a focused comparison prompt
        comparison_prompt = f"""Compare these two responses and determine which is better for the given prompt.

ORIGINAL PROMPT:
{original_prompt}

RESPONSE A:
{response_a}

RESPONSE B:
{response_b}

Consider these key factors:
1. Instruction following: Which response better follows the specific instructions in the prompt?
2. Accuracy: Which response is more factually correct and reliable?
3. Helpfulness: Which response better serves what the user actually needs?
4. Appropriateness: Which response has the right tone, style, and level of detail for the context?
5. Quality: Which response demonstrates better understanding and execution overall?

Respond with exactly one character: either "A" or "B" (nothing else)."""
        
        result = execute_llm(comparison_prompt).strip()
        
        logging.info(f"LLM returned: '{result}'")
        
        # Extract A or B from result - be very permissive in parsing
        result_upper = result.upper()
        if result == "A" or result == "B":
            return result
        elif result_upper == "A" or result_upper == "B":
            return result_upper
        elif "A" in result_upper and "B" not in result_upper:
            return "A"
        elif "B" in result_upper and "A" not in result_upper:
            return "B"
        else:
            logging.warning(f"Could not clearly parse result '{result}', defaulting to A")
            return "A"
            
    except Exception as e:
        logging.error(f"Error in process_input: {str(e)}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")
        return "A"