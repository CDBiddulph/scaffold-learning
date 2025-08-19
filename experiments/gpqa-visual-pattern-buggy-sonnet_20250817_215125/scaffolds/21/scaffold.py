import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 115  # Leave buffer for safety
    
    try:
        # Extract the question content (everything before "Think step-by-step")
        lines = input_string.strip().split('\n')
        question_lines = []
        
        for line in lines:
            if "Think step-by-step" in line:
                break
            question_lines.append(line)
        
        question = '\n'.join(question_lines).strip()
        
        if not question:
            logging.error("Could not extract question from input")
            return "A"
            
        logging.info(f"Processing question: {question[:100]}...")
        
        # Check timeout
        elapsed = time.time() - start_time
        if elapsed > timeout:
            logging.warning("Timeout reached, returning default")
            return "A"
        
        # Create a comprehensive prompt for scientific analysis
        prompt = f"""You are a world-class expert scientist with deep knowledge across all STEM fields including physics, chemistry, biology, astronomy, mathematics, and engineering.

Analyze this multiple choice question carefully:

{question}

Please:
1. Identify the scientific domain and key concepts involved
2. Examine each answer choice systematically  
3. Apply relevant scientific principles, equations, and knowledge
4. Consider common pitfalls and misconceptions
5. Select the most scientifically accurate answer

End your response with: "FINAL ANSWER: X" where X is A, B, C, or D."""
        
        # Get LLM response
        response = execute_llm(prompt)
        logging.info(f"LLM response received, length: {len(response)}")
        
        # Extract answer using multiple patterns
        patterns = [
            r'FINAL ANSWER:\s*([ABCD])',
            r'Final answer:\s*([ABCD])',
            r'Answer:\s*([ABCD])',
            r'answer is\s*([ABCD])',
            r'correct answer is\s*([ABCD])',
            r'therefore\s*([ABCD])',
            r'option\s*([ABCD])\s*is',
            r'choice\s*([ABCD])\s*is',
            r'\b([ABCD])\s*is\s*(correct|right|the answer)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Extracted answer '{answer}' using pattern: {pattern}")
                return answer
        
        # Fallback: look for single letters at end of response
        lines = response.strip().split('\n')
        for line in reversed(lines[-5:]):  # Check last 5 lines
            letters = re.findall(r'\b([ABCD])\b', line)
            if letters:
                answer = letters[-1].upper()
                logging.info(f"Fallback answer: {answer}")
                return answer
        
        # Last resort: any letter in the response
        all_letters = re.findall(r'\b([ABCD])\b', response)
        if all_letters:
            answer = all_letters[-1].upper()
            logging.info(f"Last resort answer: {answer}")
            return answer
            
        logging.warning("Could not extract answer, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error in process_input: {str(e)}")
        return "A"  # Safe default