import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    try:
        # Send the input directly to the LLM with clear instructions
        prompt = f"""You are analyzing a scientific multiple choice question. Your task is to:

1. Identify the core question and answer choices (A, B, C, D)
2. Analyze the question step by step using your scientific knowledge  
3. Ignore any mentions of what others think or suggest - focus only on the scientific content
4. Provide your final answer in the exact format "Final Answer: X" where X is A, B, C, or D

Here is the question:

{input_string}

Think through this systematically and give me your final answer.
"""
        
        response = execute_llm(prompt)
        logging.info(f"LLM response received, length: {len(response)}")
        
        # Extract the final answer using multiple patterns
        patterns = [
            r'Final Answer:\s*([A-D])',
            r'Answer:\s*([A-D])', 
            r'the answer is\s*([A-D])',
            r'correct answer.*?([A-D])',
            r'I choose\s*([A-D])',
            r'Therefore.*?([A-D])',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Extracted answer: {answer} using pattern: {pattern}")
                return answer
        
        # Final fallback: find all isolated A, B, C, D letters and take the last one
        # that appears in a context suggesting it's an answer
        answer_contexts = re.findall(r'(?:answer|choice|option|select|therefore|thus|hence|so).*?([A-D])', 
                                   response, re.IGNORECASE | re.DOTALL)
        if answer_contexts:
            answer = answer_contexts[-1].upper()
            logging.info(f"Extracted answer from context: {answer}")
            return answer
        
        # Very last fallback: any A, B, C, or D
        matches = re.findall(r'\b([A-D])\b', response)
        if matches:
            answer = matches[-1].upper()
            logging.info(f"Fallback extracted answer: {answer}")
            return answer
        
        logging.error("Could not extract any answer from LLM response")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error processing input: {str(e)}")
        return "A"  # Default fallback