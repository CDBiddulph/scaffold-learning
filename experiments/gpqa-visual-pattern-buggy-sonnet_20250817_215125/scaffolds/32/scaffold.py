import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    """
    Process a multiple choice question and return the correct answer letter.
    """
    # Create a comprehensive prompt that helps the LLM solve the question effectively
    prompt = f"""You are an expert academic tutor solving a multiple choice question. Please work through this systematically:

1. Read the question carefully and identify what's being asked
2. If it's a calculation problem, show your work step by step with formulas and numbers
3. If it's a conceptual question, explain your reasoning based on scientific principles
4. Consider each answer option carefully and eliminate incorrect ones
5. Choose the best answer and explain why it's correct

Please end your response with "Answer: X" where X is the letter (A, B, C, or D) of your chosen answer.

{input_string}"""
    
    try:
        response = execute_llm(prompt)
        logging.info(f"LLM response: {response}")
        
        # Extract the answer letter from the response
        answer = extract_answer_letter(response)
        logging.info(f"Extracted answer: {answer}")
        return answer
        
    except Exception as e:
        logging.error(f"Error processing question: {e}")
        # Return A as fallback
        return "A"

def extract_answer_letter(response):
    """
    Extract the answer letter from the LLM response using multiple strategies.
    """
    # Strategy 1: Look for "Answer: X" pattern
    answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
    if answer_match:
        return answer_match.group(1).upper()
    
    # Strategy 2: Look for "Answer X" pattern (without colon)
    answer_match = re.search(r'Answer\s+([A-D])', response, re.IGNORECASE)
    if answer_match:
        return answer_match.group(1).upper()
    
    # Strategy 3: Look for final answer patterns like "The answer is X"
    final_answer_match = re.search(r'(?:the answer is|answer is|correct answer is)\s*([A-D])', response, re.IGNORECASE)
    if final_answer_match:
        return final_answer_match.group(1).upper()
    
    # Strategy 4: Look for the last occurrence of a standalone letter A-D
    letters = re.findall(r'\b([A-D])\b', response)
    if letters:
        return letters[-1].upper()
    
    # Strategy 5: Look in the last sentence for any letter
    sentences = response.split('.')
    if sentences:
        last_sentence = sentences[-1]
        letter_match = re.search(r'([A-D])', last_sentence)
        if letter_match:
            return letter_match.group(1).upper()
    
    # If all strategies fail, log warning and return A as fallback
    logging.warning(f"Could not extract answer letter from response: {response}")
    return "A"