import logging
import re
import html
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 115  # Leave buffer before 120 second timeout
    
    try:
        # Decode HTML entities (like &gt; and &lt;)
        input_string = html.unescape(input_string)
        
        # Parse input to extract the question, skipping validation function
        lines = input_string.strip().split('\n')
        question_lines = []
        found_question_start = False
        
        for line in lines:
            stripped = line.strip()
            
            # Skip validation function lines
            if (stripped.startswith('#') or 
                stripped.startswith('def validate_answer') or 
                'return answer ==' in stripped):
                continue
            
            # Start collecting once we hit non-empty content
            if stripped:
                found_question_start = True
            
            if found_question_start:
                question_lines.append(line)
        
        question_text = '\n'.join(question_lines).strip()
        logging.info(f"Extracted question: {question_text[:300]}...")
        
        # Check timeout before making LLM call
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        # Prepare clear prompt for the LLM
        prompt = f"""You are answering a multiple choice question. Please read the question carefully and select the correct answer.

{question_text}

Please think through this step by step, then provide your final answer in the exact format: "Answer: X" where X is one of A, B, C, or D."""

        # Get response from LLM
        response = execute_llm(prompt)
        logging.info(f"LLM response length: {len(response)}")
        logging.info(f"LLM response: {response[:500]}...")
        
        # Extract answer using multiple patterns
        # First try the exact format we requested
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Extracted answer via 'Answer:' pattern: {answer}")
            return answer
        
        # Try alternative patterns the LLM might use
        patterns = [
            r'The answer is\s*([A-D])',
            r'Therefore,?\s*([A-D])',
            r'So,?\s*([A-D])',
            r'Option\s*([A-D])',
            r'\b([A-D])\s*is\s*correct',
            r'correct\s*answer\s*is\s*([A-D])',
            r'choose\s*([A-D])',
            r'select\s*([A-D])'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Extracted answer via pattern '{pattern}': {answer}")
                return answer
        
        # Fallback: look for last occurrence of A, B, C, or D
        letters = re.findall(r'\b([A-D])\b', response)
        if letters:
            answer = letters[-1]
            logging.info(f"Fallback extracted answer (last letter): {answer}")
            return answer
            
        # Final fallback
        logging.warning("No answer letter found in response, returning A as default")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Default fallback