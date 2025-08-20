import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Check timeout early
        if time.time() - start_time > 100:
            logging.warning("Approaching timeout before LLM call")
            return "A"
        
        # Add a system prompt to ensure the LLM provides clear reasoning and answer format
        system_prompt = (
            "You are an expert scientist with deep knowledge across all scientific fields. "
            "Solve each problem step-by-step with clear reasoning. Always end your response "
            "with your final answer in the exact format: 'Answer: X' where X is the letter."
        )
        
        # The input already contains the complete question with instructions
        response = execute_llm(input_string.strip(), system_prompt)
        logging.info(f"LLM response received, length: {len(response)} characters")
        
        # Check timeout after LLM call
        if time.time() - start_time > 115:
            logging.warning("Approaching timeout after LLM call")
        
        # Extract the answer from the response
        # Look for various answer patterns, prioritizing the most explicit ones
        answer_patterns = [
            r'Answer:\s*([A-D])',  # Exact format requested
            r'answer:\s*([A-D])',  # Case insensitive
            r'final answer is\s*([A-D])',
            r'the answer is\s*([A-D])',
            r'correct answer is\s*([A-D])',
            r'therefore,?\s*([A-D])',
            r'thus,?\s*([A-D])',
            r'so,?\s*([A-D])',
            r'option\s*([A-D])',
            r'choice\s*([A-D])',
            r'\b([A-D])\)\s*is\s*correct',
        ]
        
        # Try each pattern and return the first match found
        for pattern in answer_patterns:
            matches = list(re.finditer(pattern, response, re.IGNORECASE))
            if matches:
                # Take the last match to get the final conclusion
                answer = matches[-1].group(1).upper()
                logging.info(f"Extracted answer using pattern '{pattern}': {answer}")
                return answer
        
        # If no explicit answer patterns found, look for isolated letters near the end
        # This handles cases where the LLM just states the letter without "Answer:"
        words = response.split()
        for i in range(len(words) - 1, max(-1, len(words) - 20), -1):  # Check last 20 words
            word = words[i].strip('.,!?();')
            if word.upper() in ['A', 'B', 'C', 'D']:
                answer = word.upper()
                logging.info(f"Extracted answer from end words: {answer}")
                return answer
        
        # Last resort: look for any occurrence of A, B, C, or D in the last portion
        end_text = response[-500:] if len(response) > 500 else response
        letters = re.findall(r'\b([A-D])\b', end_text)
        if letters:
            answer = letters[-1].upper()
            logging.info(f"Extracted answer from letters in end text: {answer}")
            return answer
        
        # Fallback: return A if nothing found
        logging.warning(f"Could not extract answer from response. First 200 chars: {response[:200]}...")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        # Check if we still have time for a simple retry
        if time.time() - start_time < 110:
            try:
                logging.info("Attempting simple retry without system prompt")
                simple_response = execute_llm(f"{input_string.strip()}\n\nProvide only the letter of your answer (A, B, C, or D):")
                match = re.search(r'\b([A-D])\b', simple_response)
                if match:
                    return match.group(1).upper()
            except:
                pass
        
        return "A"  # Final fallback