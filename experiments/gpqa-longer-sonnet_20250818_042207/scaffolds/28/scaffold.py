import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    """
    Process a multiple choice science question and return the answer letter.
    """
    logging.info("Processing multiple choice science question")
    
    # Clean up the input
    question = input_string.strip()
    
    # System prompt to help the LLM understand the context
    system_prompt = """You are an expert in multiple scientific fields including biology, chemistry, physics, astronomy, and related disciplines. You will be given multiple choice questions that require deep technical knowledge. Please solve each question carefully using your scientific knowledge."""
    
    # Create a prompt for the LLM to solve the question
    prompt = f"""Please solve this multiple choice science question step by step. Use your expertise in the relevant scientific field to analyze the problem carefully.

{question}

Please provide your detailed reasoning and then give your final answer in the exact format "Answer: <letter>" where <letter> is A, B, C, or D."""

    try:
        # Get response from LLM
        logging.info("Sending question to LLM")
        response = execute_llm(prompt, system_prompt)
        logging.info(f"LLM response received: {response[:200]}...")
        
        # Try multiple patterns to extract the answer, in order of preference
        patterns = [
            r"Answer:\s*([ABCD])",  # "Answer: A" (preferred format)
            r"answer\s+is\s+([ABCD])",  # "answer is A"
            r"final answer.*?([ABCD])",  # "final answer is A"
            r"correct answer.*?([ABCD])",  # "correct answer is A"
            r"therefore.*?([ABCD])",  # "therefore A"
            r"option\s+([ABCD])",  # "option A"
            r"choice\s+([ABCD])",  # "choice A"
            r"select\s+([ABCD])",  # "select A"
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                answer = matches[-1].upper()  # Take the last match (most likely the final answer)
                logging.info(f"Extracted answer using pattern '{pattern}': {answer}")
                return answer
                
        # Fallback: look for standalone letters in the last few lines of response
        lines = response.strip().split('\n')
        for line in reversed(lines[-3:]):  # Check last 3 lines
            # Look for a letter that appears to be an answer (possibly with punctuation)
            letter_match = re.search(r'\b([ABCD])\b', line.strip())
            if letter_match:
                answer = letter_match.group(1).upper()
                logging.info(f"Fallback extracted answer from line '{line.strip()}': {answer}")
                return answer
                
        logging.error(f"Could not extract any answer from response: {response}")
        return "A"  # Default fallback
                
    except Exception as e:
        logging.error(f"Error processing question: {e}")
        return "A"  # Default fallback