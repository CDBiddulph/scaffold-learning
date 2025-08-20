import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 115  # Leave buffer for safety
    
    try:
        # Parse the input to extract the actual question
        # Format: comment line, validation function, then the question
        lines = input_string.strip().split('\n')
        
        # Skip the validation function part
        question_start = 0
        for i, line in enumerate(lines):
            if (line.strip().startswith('#') or 
                line.strip().startswith('def validate_answer') or
                line.strip().startswith('    return answer ==')):
                continue
            else:
                question_start = i
                break
        
        question_text = '\n'.join(lines[question_start:]).strip()
        
        logging.info(f"Extracted question (first 200 chars): {question_text[:200]}...")
        
        # Check timeout early
        if time.time() - start_time > timeout:
            logging.warning("Timeout reached, returning default")
            return "A"
        
        # Create comprehensive prompt for the LLM
        system_prompt = """You are a world-class expert scientist with deep knowledge across all scientific disciplines including:
- Organic chemistry (synthesis, mechanisms, stereochemistry, NMR, spectroscopy)
- Physical chemistry and biochemistry  
- Astronomy and astrophysics (stellar physics, exoplanets, observations)
- Quantum mechanics and particle physics
- Molecular biology, genetics, and microbiology
- Mathematics and advanced calculations

You excel at solving complex scientific problems through systematic, step-by-step analysis."""

        user_prompt = f"""Solve this multiple-choice scientific question systematically:

{question_text}

Approach:
1. Identify the key scientific concepts and principles involved
2. Work through the problem step-by-step with clear reasoning
3. Perform any necessary calculations carefully
4. Evaluate each option against your analysis
5. Select the best answer

End your response with "Answer: X" where X is A, B, C, or D."""
        
        # Get LLM response
        response = execute_llm(user_prompt, system_prompt)
        logging.info(f"LLM response received ({len(response)} chars)")
        
        # Extract final answer using multiple strategies
        
        # Primary: Look for "Answer: X" format
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            result = answer_match.group(1).upper()
            logging.info(f"Extracted answer: {result}")
            return result
        
        # Secondary: Look for "answer is X" format  
        answer_match = re.search(r'answer\s+is\s+([A-D])', response, re.IGNORECASE)
        if answer_match:
            result = answer_match.group(1).upper()
            logging.info(f"Found answer (secondary): {result}")
            return result
            
        # Tertiary: Look for last option mentioned as "X)"
        option_matches = re.findall(r'\b([A-D])\)', response)
        if option_matches:
            result = option_matches[-1].upper()
            logging.info(f"Found answer (option format): {result}")
            return result
            
        # Quaternary: Look for final conclusion patterns
        conclusion_match = re.search(r'(?:therefore|thus|so|conclusion)[^.]*\b([A-D])\b', response, re.IGNORECASE)
        if conclusion_match:
            result = conclusion_match.group(1).upper()
            logging.info(f"Found answer (conclusion): {result}")
            return result
        
        # Last resort: Any standalone letter near the end
        response_end = response[-500:]  # Look at last 500 chars
        letter_matches = re.findall(r'\b([A-D])\b', response_end)
        if letter_matches:
            result = letter_matches[-1].upper()
            logging.info(f"Found answer (end search): {result}")
            return result
            
        # Ultimate fallback
        logging.warning("No answer pattern found, defaulting to A")
        logging.debug(f"Response excerpt: {response[:300]}...")
        return "A"
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}", exc_info=True)
        return "A"