import logging
import re
import time
from collections import Counter
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Try a consensus approach with multiple LLM calls for better accuracy
        answers = []
        max_attempts = 3
        
        for attempt in range(max_attempts):
            # Check timeout - leave buffer for processing
            if time.time() - start_time > 100:
                logging.info(f"Stopping at attempt {attempt + 1} due to time limit")
                break
                
            try:
                # Send the question directly to LLM since it already contains
                # the complete question and formatting instructions
                response = execute_llm(input_string)
                
                logging.info(f"Attempt {attempt + 1} response: {response[:200]}...")
                
                # Parse the answer - look for "Answer: <letter>" format first
                answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
                if answer_match:
                    answer = answer_match.group(1).upper()
                    answers.append(answer)
                    logging.info(f"Attempt {attempt + 1}: Found formatted answer {answer}")
                else:
                    # Fallback: look for isolated letters, prefer the last one
                    letters = re.findall(r'\b([A-D])\b', response)
                    if letters:
                        answer = letters[-1].upper()  # Take the last occurrence
                        answers.append(answer)
                        logging.info(f"Attempt {attempt + 1}: Found fallback answer {answer}")
                    else:
                        logging.warning(f"Attempt {attempt + 1}: No parseable answer found")
                        
            except Exception as e:
                logging.warning(f"Attempt {attempt + 1} failed: {e}")
                continue
        
        # Return consensus answer if we have multiple responses
        if len(answers) > 1:
            counter = Counter(answers)
            most_common_answer, count = counter.most_common(1)[0]
            logging.info(f"Consensus: {most_common_answer} (appeared {count}/{len(answers)} times)")
            return most_common_answer
        elif len(answers) == 1:
            logging.info(f"Single answer: {answers[0]}")
            return answers[0]
        else:
            # No valid answers found - make one more attempt with simplified prompt
            logging.warning("No answers found, trying simplified approach")
            
            if time.time() - start_time > 115:
                return "A"  # Emergency fallback
                
            simple_prompt = f"{input_string}\n\nJust respond with the single letter of the correct answer (A, B, C, or D):"
            
            try:
                response = execute_llm(simple_prompt)
                letters = re.findall(r'\b([A-D])\b', response)
                if letters:
                    final_answer = letters[0].upper()
                    logging.info(f"Simplified approach answer: {final_answer}")
                    return final_answer
            except Exception as e:
                logging.error(f"Simplified approach failed: {e}")
            
            # Ultimate fallback
            logging.warning("All approaches failed, returning default A")
            return "A"
            
    except Exception as e:
        logging.error(f"Critical error in process_input: {e}")
        return "A"