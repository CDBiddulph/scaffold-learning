import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        question = input_string.strip()
        
        # Prompt the LLM to solve the scientific question step by step
        prompt = f"""Please solve this scientific competition question step by step.

{question}

Work through the problem systematically:
1. Identify the key scientific concepts involved
2. Perform any necessary calculations or analysis
3. Apply relevant scientific principles
4. Reason through the answer choices
5. Conclude with "Answer: X" where X is the correct letter (A, B, C, or D)

Be thorough in your analysis."""

        # Check for timeout (leave buffer time)
        if time.time() - start_time > 110:
            logging.warning("Approaching timeout, returning default answer")
            return "A"
            
        response = execute_llm(prompt)
        logging.info(f"LLM response received, length: {len(response)}")
        
        # Extract the answer using multiple strategies
        
        # Strategy 1: Look for explicit "Answer: X" format
        answer_match = re.search(r"Answer:\s*([ABCD])", response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Found answer using Answer: format: {answer}")
            return answer
        
        # Strategy 2: Look for other common conclusion patterns
        conclusion_patterns = [
            r"Final Answer:\s*([ABCD])",
            r"The correct answer is\s*([ABCD])",
            r"The answer is\s*([ABCD])",
            r"Therefore,?\s*(?:the answer is\s*)?([ABCD])",
            r"So,?\s*(?:the answer is\s*)?([ABCD])",
            r"Thus,?\s*(?:the answer is\s*)?([ABCD])",
        ]
        
        for pattern in conclusion_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Found answer using pattern '{pattern}': {answer}")
                return answer
        
        # Strategy 3: Look for letters in parentheses or option format
        option_patterns = [
            r"\(([ABCD])\)",  # (A), (B), etc.
            r"Option\s*([ABCD])",
            r"Choice\s*([ABCD])",
        ]
        
        for pattern in option_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                answer = matches[-1].upper()  # Take the last occurrence
                logging.info(f"Found answer using option pattern '{pattern}': {answer}")
                return answer
        
        # Strategy 4: Find all single letters A, B, C, D and take the last one
        # This is risky but better than no answer
        letters = re.findall(r'\b([ABCD])\b', response)
        if letters:
            answer = letters[-1].upper()
            logging.info(f"Using last letter found in response: {answer}")
            return answer
        
        # Strategy 5: Look for the ■ symbol which sometimes marks correct answers in examples
        marked_match = re.search(r'■\s*([ABCD])', response)
        if marked_match:
            answer = marked_match.group(1).upper()
            logging.info(f"Found marked answer: {answer}")
            return answer
        
        # Default fallback
        logging.warning("Could not extract any answer from LLM response")
        logging.warning(f"Response was: {response[:500]}...")  # Log first 500 chars for debugging
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing question: {str(e)}")
        logging.error(f"Question was: {input_string[:200]}...")  # Log first 200 chars for debugging
        return "A"  # Safe default