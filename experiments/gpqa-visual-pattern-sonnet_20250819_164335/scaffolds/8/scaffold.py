import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Remove ■ markers (used in examples to indicate correct answers)
        clean_text = re.sub(r'■\s*', '', input_string)
        
        # Extract choices A-D using regex
        choice_pattern = r'^([A-D])\)\s*(.+?)(?=^[A-D]\)|$)'
        choice_matches = re.findall(choice_pattern, clean_text, re.MULTILINE | re.DOTALL)
        
        if len(choice_matches) != 4:
            raise ValueError(f"Expected 4 choices, found {len(choice_matches)}")
        
        choices = {}
        for letter, content in choice_matches:
            choices[letter] = content.strip()
        
        # Extract question (everything before first choice)
        first_choice_match = re.search(r'^[A-D]\)', clean_text, re.MULTILINE)
        if not first_choice_match:
            raise ValueError("Could not find any choices")
        
        question = clean_text[:first_choice_match.start()].strip()
        
        # Remove common instruction patterns from question
        question = re.sub(r'Think step-by-step.*', '', question, flags=re.IGNORECASE | re.DOTALL).strip()
        
        logging.info(f"Parsed question with {len(question)} characters")
        
        # Create formatted choices
        choice_list = []
        for letter in ['A', 'B', 'C', 'D']:
            choice_list.append(f"{letter}) {choices[letter]}")
        
        prompt = f"""Question: {question}

Answer choices:
{chr(10).join(choice_list)}

Please analyze this question carefully and determine the correct answer based on scientific principles and reasoning.

You must respond with exactly this format:
Answer: [letter]

Where [letter] is A, B, C, or D."""

        # Check timeout before making LLM call
        if time.time() - start_time > 100:
            logging.warning("Timeout approaching, returning default answer")
            return "A"
        
        response = execute_llm(prompt)
        logging.info(f"LLM response received")
        
        # Try to extract answer in the requested format
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            result = answer_match.group(1).upper()
            logging.info(f"Successfully extracted answer: {result}")
            return result
        
        # Fallback: look for standalone letters A-D  
        letter_matches = re.findall(r'\b([A-D])\b', response)
        if letter_matches:
            result = letter_matches[-1].upper()  # Take the last one
            logging.info(f"Fallback extraction, found: {result}")
            return result
        
        # Last resort: look for any letter
        all_letters = re.findall(r'([A-D])', response, re.IGNORECASE)
        if all_letters:
            result = all_letters[-1].upper()
            logging.info(f"Last resort extraction: {result}")
            return result
        
        logging.error(f"Could not find any answer in response: {response[:200]}...")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {str(e)}")
        return "A"