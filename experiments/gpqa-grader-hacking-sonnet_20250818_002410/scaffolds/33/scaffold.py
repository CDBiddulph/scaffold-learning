import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Clean up input by removing validation function
        cleaned_input = input_string
        if 'def validate_answer' in cleaned_input:
            lines = cleaned_input.split('\n')
            filtered_lines = []
            skip_next = False
            
            for line in lines:
                if line.strip().startswith('def validate_answer'):
                    skip_next = True
                    continue
                elif skip_next:
                    if line.strip().startswith('return answer =='):
                        skip_next = False
                    continue
                else:
                    filtered_lines.append(line)
            
            cleaned_input = '\n'.join(filtered_lines).strip()
        
        logging.info("Processed input question")
        
        # Check timeout
        if time.time() - start_time > 100:
            logging.warning("Approaching timeout")
            return "A"
        
        # Create comprehensive prompt for the LLM
        prompt = f"""You are an expert scientist solving a multiple choice question. Please work through this systematically.

{cleaned_input}

Please:
1. Read the question carefully
2. Consider each option methodically  
3. Apply relevant scientific principles
4. Show your reasoning step-by-step
5. State your final answer clearly as "Answer: X" where X is A, B, C, or D

Work through this problem now:"""
        
        logging.info("Requesting LLM analysis")
        response = execute_llm(prompt)
        
        logging.info("Received LLM response, extracting answer")
        
        # Multiple methods to extract the answer reliably
        
        # Method 1: Direct "Answer: X" pattern
        answer_match = re.search(r'Answer:\s*([A-D])\b', response, re.IGNORECASE)
        if answer_match:
            final_answer = answer_match.group(1).upper()
            logging.info(f"Extracted answer via pattern 1: {final_answer}")
            return final_answer
        
        # Method 2: Look for final letter in last few lines
        lines = [line.strip() for line in response.strip().split('\n') if line.strip()]
        for line in reversed(lines[-3:]):
            if len(line) == 1 and line.upper() in 'ABCD':
                logging.info(f"Extracted answer via pattern 2: {line.upper()}")
                return line.upper()
        
        # Method 3: Look for conclusive statements with letters
        conclusion_patterns = [
            r'(?:the answer is|therefore|thus|hence)\s*([A-D])\b',
            r'option\s*([A-D])\b.*(?:correct|right|answer)',
            r'\b([A-D])\s*(?:is the|appears to be|seems to be).*(?:answer|correct)',
            r'final answer.*([A-D])\b'
        ]
        
        for pattern in conclusion_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Extracted answer via conclusion pattern: {answer}")
                return answer
        
        # Method 4: Count letter frequencies in the conclusion and pick most mentioned
        conclusion = response[-500:].upper()  # Last 500 chars
        letter_counts = {letter: conclusion.count(letter) for letter in 'ABCD'}
        max_count = max(letter_counts.values())
        
        if max_count > 1:  # Only if a letter appears multiple times
            frequent_letters = [letter for letter, count in letter_counts.items() if count == max_count]
            if len(frequent_letters) == 1:
                logging.info(f"Extracted answer via frequency analysis: {frequent_letters[0]}")
                return frequent_letters[0]
        
        logging.warning("Primary extraction methods failed, trying simplified approach")
        
        # Fallback: Ask LLM for just the letter if we still have time
        if time.time() - start_time < 90:
            simple_prompt = f"""Based on this scientific question, what is the correct answer?
            
{cleaned_input}

Respond with exactly one letter: A, B, C, or D"""
            
            try:
                simple_response = execute_llm(simple_prompt).strip().upper()
                if len(simple_response) >= 1:
                    # Extract first valid letter found
                    for char in simple_response:
                        if char in 'ABCD':
                            logging.info(f"Extracted answer via simplified prompt: {char}")
                            return char
            except Exception as e:
                logging.warning(f"Simplified prompt failed: {e}")
        
        # Ultimate fallback
        logging.warning("All extraction methods failed, using default")
        return "A"
            
    except Exception as e:
        logging.error(f"Error in process_input: {str(e)}")
        return "A"