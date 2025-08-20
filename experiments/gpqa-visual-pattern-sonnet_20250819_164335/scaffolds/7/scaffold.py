import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    try:
        # Extract the question content by removing the marked answer if present
        question_text = input_string.strip()
        
        # Remove the marked correct answer (■) if it exists in the input
        question_text = re.sub(r'■\s*', '', question_text)
        
        logging.info(f"Processing question with {len(question_text)} characters")
        
        # Create a comprehensive prompt for the LLM to solve the scientific problem
        prompt = f"""You are an expert in all scientific disciplines including physics, chemistry, biology, astronomy, and mathematics. 

Please solve this scientific question step by step:

{question_text}

Requirements:
1. Think through the problem systematically
2. Show your reasoning clearly
3. Apply relevant scientific principles, formulas, and concepts
4. Make any necessary calculations
5. Consider all the given information carefully
6. Choose the best answer from the multiple choice options

Please end your response with "Final Answer: X" where X is the letter (A, B, C, or D) of your chosen answer."""

        # Get the LLM response
        response = execute_llm(prompt)
        logging.info(f"LLM response received with {len(response)} characters")
        
        # Extract the final answer letter from the response
        # Look for patterns like "Final Answer: A" or "Answer: A" or just "A)" at the end
        answer_patterns = [
            r'Final Answer:\s*([A-D])',
            r'Answer:\s*([A-D])',
            r'answer is\s*\(?([A-D])\)?',
            r'correct answer is\s*\(?([A-D])\)?',
            r'Therefore,?\s*\(?([A-D])\)?',
            r'So,?\s*\(?([A-D])\)?',
            r'\b([A-D])\)\s*$',
            r'\b([A-D])\s*$'
        ]
        
        for pattern in answer_patterns:
            match = re.search(pattern, response, re.IGNORECASE | re.MULTILINE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Extracted answer: {answer}")
                return answer
        
        # If we can't find a clear answer pattern, try a second attempt with more explicit instructions
        logging.warning("Could not extract answer from first attempt, trying again")
        
        clarification_prompt = f"""Based on this scientific question:

{question_text}

And this analysis:
{response}

Please provide ONLY the letter of the correct answer (A, B, C, or D). Do not include any other text."""

        clarification_response = execute_llm(clarification_prompt)
        
        # Look for just a single letter
        letter_match = re.search(r'\b([A-D])\b', clarification_response.strip())
        if letter_match:
            answer = letter_match.group(1).upper()
            logging.info(f"Extracted answer from clarification: {answer}")
            return answer
        
        # Final fallback: look for the most common letter in the response
        letters = re.findall(r'\b([A-D])\b', response)
        if letters:
            answer = max(set(letters), key=letters.count).upper()
            logging.warning(f"Using most frequent letter as fallback: {answer}")
            return answer
        
        # Ultimate fallback
        logging.error("Could not extract any answer, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {str(e)}")
        return "A"