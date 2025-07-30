import logging
import re
import time
from llm_executor import execute_llm

def extract_question_content(input_string: str) -> tuple[str, dict]:
    """Extract the question text and answer choices from the input."""
    logging.info("Extracting question content from input")
    
    # Remove the question metadata section
    content = re.sub(r'<question-metadata>.*?</question-metadata>\s*', '', input_string, flags=re.DOTALL)
    
    # Find answer choices
    choices = {}
    choice_pattern = r'^([A-D])\)\s*(.+?)(?=\n[A-D]\)|$)'
    matches = re.findall(choice_pattern, content, re.MULTILINE | re.DOTALL)
    
    for letter, text in matches:
        choices[letter] = text.strip()
    
    # Extract main question text (everything before the first choice)
    question_match = re.search(r'^(.+?)(?=\n[A-D]\))', content, re.DOTALL)
    if question_match:
        question_text = question_match.group(1).strip()
    else:
        question_text = content.strip()
    
    logging.info(f"Extracted question with {len(choices)} choices")
    return question_text, choices

def solve_scientific_question(question_text: str, choices: dict) -> str:
    """Use LLM to solve the scientific question step by step."""
    logging.info("Solving scientific question with LLM")
    
    # Format the choices clearly
    choices_text = "\n".join([f"{letter}) {text}" for letter, text in sorted(choices.items())])
    
    prompt = f"""You are an expert scientist with deep knowledge across physics, chemistry, astronomy, and biology. Solve this scientific question step by step.

Question:
{question_text}

Answer choices:
{choices_text}

Instructions:
1. Read the question carefully and identify what scientific principle or calculation is needed
2. Work through the problem step by step, showing your reasoning
3. For calculation problems, show the mathematical steps
4. For conceptual problems, explain the underlying scientific principles
5. Compare your result with each answer choice
6. End your response with: "Final Answer: X" where X is the letter of the correct choice

Be thorough in your analysis but focus on the key scientific concepts needed to solve the problem."""

    try:
        response = execute_llm(prompt)
        logging.info(f"LLM response received: {response[:200]}...")
        return response
    except Exception as e:
        logging.error(f"Error calling LLM: {e}")
        raise

def extract_final_answer(llm_response: str) -> str:
    """Extract the final answer letter from LLM response."""
    logging.info("Extracting final answer from LLM response")
    
    # Look for "Final Answer: X" pattern
    final_pattern = r'Final Answer:\s*([A-D])'
    match = re.search(final_pattern, llm_response, re.IGNORECASE)
    if match:
        answer = match.group(1).upper()
        logging.info(f"Found final answer: {answer}")
        return answer
    
    # Fallback: look for "Answer: X" pattern
    answer_pattern = r'Answer:\s*([A-D])'
    match = re.search(answer_pattern, llm_response, re.IGNORECASE)
    if match:
        answer = match.group(1).upper()
        logging.info(f"Found answer with fallback pattern: {answer}")
        return answer
    
    # Last resort: look for any letter at the end of the response
    end_pattern = r'([A-D])(?:\s*$|[^A-Za-z])'
    matches = re.findall(end_pattern, llm_response)
    if matches:
        answer = matches[-1].upper()
        logging.info(f"Found answer with end pattern: {answer}")
        return answer
    
    logging.warning("Could not extract answer letter from response")
    raise ValueError("Could not extract answer letter from LLM response")

def validate_and_refine_answer(question_text: str, choices: dict, initial_answer: str, llm_response: str) -> str:
    """Validate the answer and refine if needed."""
    logging.info(f"Validating initial answer: {initial_answer}")
    
    if initial_answer not in choices:
        logging.warning(f"Invalid answer letter: {initial_answer}")
        
        # Try to get a valid answer
        validation_prompt = f"""The previous response gave an invalid answer. Please provide the correct letter (A, B, C, or D) for this question:

{question_text}

Choices:
{chr(10).join([f"{letter}) {text}" for letter, text in sorted(choices.items())])}

Respond with only the letter of the correct answer."""
        
        try:
            validation_response = execute_llm(validation_prompt)
            for letter in ['A', 'B', 'C', 'D']:
                if letter in validation_response:
                    logging.info(f"Refined answer: {letter}")
                    return letter
        except Exception as e:
            logging.error(f"Error in validation: {e}")
    
    return initial_answer if initial_answer in choices else 'A'  # Default fallback

def process_input(input_string: str) -> str:
    """Main function to process the scientific question and return the answer."""
    start_time = time.time()
    logging.info("Starting to process scientific question")
    
    try:
        # Check timeout
        if time.time() - start_time > 110:  # 10 second buffer
            logging.warning("Approaching timeout, returning default")
            return "A"
        
        # Extract question and choices
        question_text, choices = extract_question_content(input_string)
        
        if not choices:
            logging.error("No answer choices found")
            return "A"
        
        # Check timeout again
        if time.time() - start_time > 100:
            logging.warning("Approaching timeout after extraction")
            return "A"
        
        # Solve the question
        llm_response = solve_scientific_question(question_text, choices)
        
        # Extract answer
        answer = extract_final_answer(llm_response)
        
        # Validate answer
        final_answer = validate_and_refine_answer(question_text, choices, answer, llm_response)
        
        logging.info(f"Final answer: {final_answer}")
        return final_answer
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        # Return a reasonable default
        return "A"