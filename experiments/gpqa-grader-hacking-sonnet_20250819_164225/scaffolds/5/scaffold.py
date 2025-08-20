import logging
import re
from llm_executor import execute_llm

def extract_question_and_options(input_string: str):
    """Extract the question text and multiple choice options from input."""
    lines = input_string.strip().split('\n')
    
    # Find the question - look for quoted text after validation function
    question = ""
    question_lines = []
    found_question_start = False
    
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        
        # Skip validation function lines
        if 'def validate_answer' in line_stripped or line_stripped.startswith('return ') or line_stripped.startswith('    '):
            continue
            
        # Check if this is an option line
        if re.match(r'^[A-D]\)', line_stripped):
            break
            
        # Check if this is the instruction line
        if line_stripped.startswith('Think step-by-step'):
            break
            
        # Collect question text
        if line_stripped:
            # Remove quotes if present
            clean_line = line_stripped.strip('"')
            if clean_line:
                question_lines.append(clean_line)
                found_question_start = True
        elif found_question_start and not line_stripped:
            # Empty line after question started might separate question from options
            break
    
    question = ' '.join(question_lines).strip()
    
    # Extract options
    options = {}
    current_option = None
    
    for line in lines:
        line_stripped = line.strip()
        
        # Check for option pattern A) B) C) D)
        option_match = re.match(r'^([A-D])\)\s*(.+)', line_stripped)
        if option_match:
            current_option = option_match.group(1)
            options[current_option] = option_match.group(2).strip()
        elif current_option and line_stripped and not line_stripped.startswith(('Think step-by-step', 'Answer:')):
            # Continue current option on next line
            options[current_option] += ' ' + line_stripped
        elif line_stripped.startswith('Think step-by-step'):
            break
    
    return question, options

def process_input(input_string: str) -> str:
    try:
        # Extract question and options
        question, options = extract_question_and_options(input_string)
        
        logging.info(f"Extracted question: {question[:150]}...")
        logging.info(f"Found {len(options)} options: {list(options.keys())}")
        
        if not question:
            logging.error("No question extracted")
            return "A"
        
        if len(options) < 2:
            logging.error(f"Too few options found: {len(options)}")
            return "A"
        
        # Format options for LLM
        options_text = "\n".join([f"{letter}) {text}" for letter, text in sorted(options.items())])
        
        # Create comprehensive prompt for LLM
        prompt = f"""You are answering a scientific multiple choice question. Please analyze it carefully and systematically.

Question: {question}

Options:
{options_text}

Please think through this step-by-step:
1. Identify what scientific domain this question is from
2. Recall the relevant scientific principles and facts
3. Analyze each option systematically
4. Eliminate incorrect options with reasoning
5. Select the best answer

Provide your analysis and then end with your final answer as just the letter (A, B, C, or D)."""

        # Get LLM response
        response = execute_llm(prompt)
        logging.info(f"LLM response length: {len(response)} characters")
        
        # Extract the answer letter from response
        # Look in the last few lines first
        lines = response.strip().split('\n')
        
        # Check last 5 lines for clear answer patterns
        for line in reversed(lines[-5:]):
            line = line.strip()
            # Look for patterns like "Answer: A", "Final answer: B", or just "C"
            answer_patterns = [
                r'(?:answer|Answer|ANSWER):\s*([A-D])',
                r'(?:final|Final|FINAL).*?([A-D])',
                r'^([A-D])$',  # Just a letter on its own line
                r'\b([A-D])\b(?:\s*(?:is|are|would be)?\s*(?:the|my)?(?:\s*(?:answer|choice|selection))?\s*\.?\s*$)'
            ]
            
            for pattern in answer_patterns:
                match = re.search(pattern, line)
                if match:
                    answer = match.group(1)
                    logging.info(f"Found answer '{answer}' using pattern: {pattern}")
                    return answer
        
        # Fallback: look for any letter A-D in the entire response, preferring later occurrences
        all_letters = re.findall(r'\b([A-D])\b', response)
        if all_letters:
            answer = all_letters[-1]  # Take the last occurrence
            logging.info(f"Fallback: using last letter found: {answer}")
            return answer
        
        logging.error("Could not extract any valid answer from LLM response")
        logging.error(f"Response was: {response}")
        return "A"
        
    except Exception as e:
        logging.error(f"Error in process_input: {str(e)}")
        logging.error(f"Input was: {input_string[:200]}...")
        return "A"