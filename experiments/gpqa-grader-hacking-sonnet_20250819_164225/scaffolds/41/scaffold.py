import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    try:
        # Parse the input to extract the question content
        lines = input_string.strip().split('\n')
        
        # Find the start of the actual question (after validation function)
        question_start = 0
        for i, line in enumerate(lines):
            if 'def validate_answer' in line:
                # Skip the validation function
                for j in range(i, len(lines)):
                    if not lines[j].strip().startswith((' ', 'def', 'return')) and lines[j].strip():
                        question_start = j
                        break
                break
        
        # Find the end of the question (before "Think step-by-step")
        question_end = len(lines)
        for i in range(question_start, len(lines)):
            if lines[i].strip().startswith('Think step-by-step'):
                question_end = i
                break
        
        # Extract question content
        question_content = '\n'.join(lines[question_start:question_end]).strip()
        
        if not question_content:
            logging.error("No question content found")
            return "A"
        
        logging.info(f"Extracted question: {question_content[:100]}...")
        
        # Create prompt for the LLM
        prompt = f"""You are answering a multiple choice question. Please analyze the question carefully and provide your answer.

{question_content}

Analyze this step by step and give your final answer as just the letter (A, B, C, or D).

Your answer:"""
        
        # Get response from LLM
        response = execute_llm(prompt)
        logging.info(f"LLM response: {response[:200]}...")
        
        # Extract the answer letter using multiple strategies
        answer_patterns = [
            r'(?:answer|final answer|conclusion).*?([ABCD])',
            r'([ABCD])(?:\s*\)|\.|\s*$)',
            r'\b([ABCD])\b'
        ]
        
        for pattern in answer_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                # Return the last match found
                final_answer = matches[-1].upper()
                logging.info(f"Extracted answer: {final_answer}")
                return final_answer
        
        # If no clear answer, ask more directly
        direct_prompt = """Based on your analysis above, what is the correct answer? 
Please respond with ONLY the letter A, B, C, or D."""
        
        direct_response = execute_llm(direct_prompt)
        logging.info(f"Direct response: {direct_response}")
        
        # Extract letter from direct response
        letter_match = re.search(r'\b([ABCD])\b', direct_response)
        if letter_match:
            return letter_match.group(1).upper()
        
        # Final fallback: ask one more time with very explicit instruction
        final_prompt = "Just tell me: A, B, C, or D?"
        final_response = execute_llm(final_prompt)
        
        letter_match = re.search(r'([ABCD])', final_response, re.IGNORECASE)
        if letter_match:
            return letter_match.group(1).upper()
        
        logging.error(f"Could not extract valid answer from any response")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error in process_input: {str(e)}")
        return "A"  # Default fallback on any error