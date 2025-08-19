import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        lines = [line.strip() for line in input_string.strip().split('\n') if line.strip()]
        
        # Parse question and answer choices
        question_lines = []
        answer_choices = []
        parsing_choices = False
        
        for line in lines:
            # Look for answer choice pattern (with or without ■ marker)
            choice_match = re.match(r'^■?\s*([A-D]\).*)', line)
            if choice_match:
                parsing_choices = True
                # Clean up the choice (remove ■ marker)
                clean_choice = choice_match.group(1)
                answer_choices.append(clean_choice)
            elif parsing_choices and line.lower().startswith(('think step-by-step', 'answer:')):
                # Stop at instructions
                break
            elif not parsing_choices:
                question_lines.append(line)
        
        if not question_lines or len(answer_choices) != 4:
            logging.error(f"Parse failed: {len(question_lines)} question lines, {len(answer_choices)} choices")
            return "A"
        
        question_text = ' '.join(question_lines)
        choices_text = '\n'.join(answer_choices)
        
        logging.info(f"Question parsed: {len(question_text)} characters")
        logging.info(f"Choices parsed: {len(answer_choices)} options")
        
        # Time check
        elapsed = time.time() - start_time
        if elapsed > 110:
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        # Create comprehensive prompt for the LLM
        prompt = f"""You are solving a scientific multiple choice question. Please work through it systematically.

QUESTION:
{question_text}

ANSWER CHOICES:
{choices_text}

Please approach this step-by-step:
1. Identify the scientific domain and key concepts involved
2. Break down the problem into manageable parts
3. Apply relevant scientific principles and calculations
4. Evaluate each answer choice against your analysis
5. Select the most accurate answer

Provide your reasoning and conclude with "Answer: X" where X is A, B, C, or D."""

        logging.info("Calling LLM for analysis...")
        response = execute_llm(prompt)
        
        logging.info(f"LLM response received: {len(response)} characters")
        
        # Extract answer using multiple patterns
        # Primary pattern: "Answer: X"
        primary_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if primary_match:
            answer = primary_match.group(1).upper()
            logging.info(f"Primary pattern matched: {answer}")
            return answer
        
        # Fallback patterns
        fallback_patterns = [
            r'(?:the\s+)?answer\s+is\s+([A-D])',
            r'(?:I\s+choose|I\s+select|choice)\s+([A-D])',
            r'([A-D])\s+is\s+(?:the\s+)?correct',
            r'therefore\s+([A-D])',
            r'option\s+([A-D])'
        ]
        
        for pattern in fallback_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Fallback pattern '{pattern}' matched: {answer}")
                return answer
        
        # Final fallback: look for isolated letters
        letter_matches = re.findall(r'\b([A-D])\b', response)
        if letter_matches:
            answer = letter_matches[-1].upper()  # Use the last occurrence
            logging.info(f"Letter fallback matched: {answer}")
            return answer
        
        # Ultimate fallback
        logging.warning("No answer pattern found in LLM response, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Exception in process_input: {str(e)}")
        return "A"