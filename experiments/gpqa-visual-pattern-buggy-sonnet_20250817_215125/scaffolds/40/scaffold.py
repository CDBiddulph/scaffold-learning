import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    logging.info("Processing multiple choice scientific question")
    
    try:
        # Parse the input to extract question and options
        lines = [line.strip() for line in input_string.strip().split('\n') if line.strip()]
        
        question_lines = []
        options = {}
        found_options = False
        
        for line in lines:
            # Check if this line contains an option (handle both "A)" and "■ A)" formats)
            option_match = re.match(r'^(?:■\s*)?([ABCD])\)\s*(.*)', line)
            if option_match:
                found_options = True
                letter = option_match.group(1)
                content = option_match.group(2).strip()
                options[letter] = content
            elif not found_options:
                # This is part of the question
                question_lines.append(line)
        
        question_text = ' '.join(question_lines).strip()
        
        if not question_text or not options:
            logging.error("Could not parse question or options")
            return "A"
        
        # Check timeout - leave buffer for processing
        if time.time() - start_time > 100:
            logging.warning("Approaching timeout, returning default")
            return "A"
        
        # Create comprehensive prompt for the LLM
        prompt = f"""You are solving a scientific multiple choice question. These questions cover advanced topics in physics, chemistry, biology, and astronomy. Please analyze the question step-by-step using your scientific knowledge.

Question: {question_text}

Answer choices:
"""
        
        for letter in sorted(options.keys()):
            prompt += f"{letter}) {options[letter]}\n"
        
        prompt += """
Instructions:
1. Read the question carefully and identify the scientific domain
2. Apply relevant scientific principles and formulas
3. Work through the problem step-by-step
4. Eliminate incorrect options if helpful
5. State your final answer clearly

Please think through this systematically and conclude with "Final answer: X" where X is A, B, C, or D.
"""
        
        # Get LLM response
        response = execute_llm(prompt)
        logging.info(f"LLM response length: {len(response)} characters")
        
        # Extract answer from response using multiple strategies
        patterns = [
            r'final answer:\s*([ABCD])',
            r'answer:\s*([ABCD])',
            r'the answer is\s*([ABCD])',
            r'answer is\s*([ABCD])',
            r'correct answer is\s*([ABCD])',
            r'([ABCD])\s*is\s*(?:the\s*)?correct',
            r'choose\s*([ABCD])',
            r'option\s*([ABCD])\s*is',
            r'therefore\s*([ABCD])',
            r'hence\s*([ABCD])',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                answer = matches[-1].upper()  # Take the last match
                if answer in options:
                    logging.info(f"Extracted answer using pattern '{pattern}': {answer}")
                    return answer
        
        # Fallback: look for standalone letters near the end of the response
        response_lines = response.split('\n')
        for line in reversed(response_lines[-5:]):  # Check last 5 lines
            letters = re.findall(r'\b([ABCD])\b', line)
            if letters:
                answer = letters[-1].upper()
                if answer in options:
                    logging.info(f"Using letter from end of response: {answer}")
                    return answer
        
        # Last resort: find any letter in the response
        all_letters = re.findall(r'\b([ABCD])\b', response)
        if all_letters:
            answer = all_letters[-1].upper()
            logging.info(f"Using last letter found in response: {answer}")
            return answer
        
        logging.warning("Could not extract answer from LLM response, returning default")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing question: {e}")
        return "A"