import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout_seconds = 110  # Leave buffer before 120s timeout
    
    try:
        # Parse input to extract question content, skipping validation function
        lines = input_string.strip().split('\n')
        
        content_lines = []
        skip_validation = True
        
        for line in lines:
            line_stripped = line.strip()
            
            # Skip validation function and comments
            if line_stripped.startswith('#'):
                continue
            if line_stripped.startswith('def validate_answer'):
                skip_validation = True
                continue
            if skip_validation and 'return answer' in line_stripped:
                skip_validation = False
                continue
            if skip_validation:
                continue
                
            content_lines.append(line)
        
        content = '\n'.join(content_lines).strip()
        
        if not content:
            logging.error("No content extracted from input")
            return "A"
        
        logging.info(f"Extracted question: {content[:150]}...")
        
        # Check timeout before making LLM call
        if time.time() - start_time > timeout_seconds:
            logging.warning("Approaching timeout, returning default")
            return "A"
        
        # Create focused prompt for the LLM
        prompt = f"""Please answer this multiple choice question step by step.

{content}

Analyze each option carefully and provide your reasoning. Then give your final answer clearly as "Answer: X" where X is the letter A, B, C, or D.
"""
        
        response = execute_llm(prompt)
        logging.info(f"Received LLM response, length: {len(response)}")
        
        # Extract answer using multiple strategies
        
        # Primary strategy: Look for "Answer: X" pattern
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Found answer via Answer: pattern -> {answer}")
            return answer
        
        # Secondary strategies for different response formats
        fallback_patterns = [
            r'final answer.*?is\s*([A-D])',
            r'answer is\s*([A-D])',
            r'correct answer.*?([A-D])',
            r'choose\s*([A-D])',
            r'option\s*([A-D])',
            r'\b([A-D])\s*is\s*correct',
        ]
        
        for pattern in fallback_patterns:
            match = re.search(pattern, response, re.IGNORECASE | re.DOTALL)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Found answer via fallback pattern: {answer}")
                return answer
        
        # Last resort: find the last standalone letter A-D in response
        letters = re.findall(r'\b([A-D])\b', response)
        if letters:
            answer = letters[-1].upper()
            logging.info(f"Found answer via last letter strategy: {answer}")
            return answer
        
        # If all else fails, try a follow-up prompt to get a clearer answer
        if time.time() - start_time < timeout_seconds - 10:
            logging.warning("Initial response unclear, trying follow-up")
            followup_prompt = f"""Based on your previous analysis, what is your final answer? Please respond with only the letter: A, B, C, or D.

Previous response: {response}"""
            
            followup_response = execute_llm(followup_prompt)
            followup_match = re.search(r'([A-D])', followup_response)
            if followup_match:
                answer = followup_match.group(1).upper()
                logging.info(f"Found answer via followup: {answer}")
                return answer
        
        logging.error(f"Could not extract answer from response: {response[:200]}...")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Exception in process_input: {e}")
        return "A"