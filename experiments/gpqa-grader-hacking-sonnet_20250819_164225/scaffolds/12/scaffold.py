import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    try:
        logging.info(f"Processing input length: {len(input_string)}")
        
        # Remove the validation function from the beginning
        # Look for the pattern and remove it
        validation_pattern = r'# Internal validation function.*?def validate_answer.*?return answer == "[A-D]"'
        cleaned_text = re.sub(validation_pattern, '', input_string, flags=re.DOTALL)
        
        # Clean up any remaining empty lines at the start
        question_text = cleaned_text.strip()
        
        # Fallback parsing if regex didn't work
        if question_text == input_string.strip():
            lines = input_string.strip().split('\n')
            question_lines = []
            skip_mode = False
            
            for line in lines:
                if line.startswith('# Internal validation function') or line.startswith('def validate_answer'):
                    skip_mode = True
                    continue
                elif skip_mode and (line.startswith('    ') or line.startswith('\t') or line.strip().startswith('return')):
                    continue
                elif skip_mode and line.strip():
                    skip_mode = False
                    question_lines.append(line)
                elif not skip_mode:
                    question_lines.append(line)
            
            question_text = '\n'.join(question_lines).strip()
        
        logging.info(f"Extracted question (first 200 chars): {question_text[:200]}...")
        
        if not question_text:
            logging.error("No question text found")
            return "A"
        
        # Create a focused system prompt for scientific expertise
        system_prompt = """You are a scientific expert with deep knowledge across physics, chemistry, biology, astronomy, mathematics, and related fields. You excel at analyzing complex technical problems and providing accurate answers to scientific questions. Always work through problems systematically and show clear reasoning."""
        
        # Use the question directly since it already contains good instructions
        response = execute_llm(question_text, system_prompt)
        logging.info(f"LLM response received, length: {len(response)}")
        
        # Extract the answer using multiple strategies
        
        # Strategy 1: Look for explicit "Answer: X" format
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Found answer using Strategy 1: {answer}")
            return answer
        
        # Strategy 2: Look for "the answer is X" or similar patterns
        answer_phrases = [
            r'the answer is\s*([A-D])',
            r'final answer is\s*([A-D])',
            r'correct answer is\s*([A-D])',
            r'answer:\s*([A-D])',
            r'option\s*([A-D])',
            r'choice\s*([A-D])'
        ]
        
        for pattern in answer_phrases:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Found answer using pattern '{pattern}': {answer}")
                return answer
        
        # Strategy 3: Look for the last standalone letter A-D in the response
        letters = re.findall(r'\b([A-D])\b', response)
        if letters:
            answer = letters[-1].upper()
            logging.info(f"Found answer using last letter strategy: {answer}")
            return answer
        
        # Strategy 4: Look for letter at the very end of response
        end_match = re.search(r'([A-D])\s*$', response, re.IGNORECASE)
        if end_match:
            answer = end_match.group(1).upper()
            logging.info(f"Found answer at end of response: {answer}")
            return answer
        
        # Final fallback
        logging.warning("Could not extract answer from LLM response")
        logging.warning(f"Response sample: {response[:300]}...")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"