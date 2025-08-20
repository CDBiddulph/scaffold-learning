import logging
import re
import html
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Leave buffer before 120s timeout
    
    try:
        # Decode HTML entities first
        decoded_input = html.unescape(input_string)
        
        # Extract the main content by removing validation function
        lines = decoded_input.strip().split('\n')
        content_lines = []
        skip_validation = False
        
        for line in lines:
            line_stripped = line.strip()
            
            # Skip validation function block
            if (line_stripped.startswith('# Internal validation function') or 
                line_stripped.startswith('def validate_answer')):
                skip_validation = True
                continue
            elif skip_validation and 'return answer ==' in line_stripped:
                skip_validation = False
                continue
            elif not skip_validation:
                content_lines.append(line)
        
        content = '\n'.join(content_lines).strip()
        
        # Remove the instruction part at the end
        if 'Think step-by-step' in content:
            question_content = content.split('Think step-by-step')[0].strip()
        else:
            question_content = content
        
        logging.info(f"Processing question: {question_content[:200]}...")
        
        # Check timeout before LLM call
        if time.time() - start_time > timeout * 0.7:
            logging.warning("Approaching timeout early, returning default")
            return "A"
        
        # Create comprehensive prompt for the LLM
        prompt = f"""You are an expert in multiple scientific disciplines. Solve this academic multiple-choice question step by step.

{question_content}

Instructions:
1. Carefully read and understand the question
2. Identify the relevant scientific principles
3. Work through the problem systematically  
4. Select the correct answer from the options
5. End with "Answer: X" where X is A, B, C, or D

Provide your analysis:"""

        # Get LLM response
        response = execute_llm(prompt)
        logging.info(f"LLM response received (length: {len(response)})")
        
        # Multiple methods to extract the answer
        
        # Method 1: Direct "Answer: X" pattern
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            result = answer_match.group(1).upper()
            logging.info(f"Extracted answer: {result}")
            return result
        
        # Method 2: Common answer phrases
        answer_patterns = [
            r'(?:the\s+)?(?:correct\s+)?answer\s+is\s+([A-D])',
            r'I\s+(?:choose|select)\s+([A-D])',
            r'(?:option\s+)?([A-D])\s+is\s+(?:correct|right|the\s+answer)',
            r'therefore[,\s]*(?:the\s+answer\s+is\s+)?([A-D])',
            r'thus[,\s]*(?:the\s+answer\s+is\s+)?([A-D])',
        ]
        
        for pattern in answer_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                result = matches[-1].upper()  # Take the last match
                logging.info(f"Found answer with pattern '{pattern}': {result}")
                return result
        
        # Method 3: Look for letters in conclusion
        # Split response into sentences and check the last few
        sentences = re.split(r'[.!?]+', response)
        last_sentences = ' '.join(sentences[-3:]) if len(sentences) >= 3 else response
        
        conclusion_letters = re.findall(r'\b([A-D])\b', last_sentences, re.IGNORECASE)
        if conclusion_letters:
            result = conclusion_letters[-1].upper()
            logging.info(f"Found answer in conclusion: {result}")
            return result
        
        # Method 4: Quick follow-up question if time permits
        if time.time() - start_time < timeout * 0.9:
            logging.info("Attempting follow-up for clarification")
            follow_up_prompt = "What is your final answer? Reply with only one letter: A, B, C, or D"
            follow_up_response = execute_llm(follow_up_prompt)
            
            letter_match = re.search(r'([A-D])', follow_up_response, re.IGNORECASE)
            if letter_match:
                result = letter_match.group(1).upper()
                logging.info(f"Follow-up answer: {result}")
                return result
        
        # Fallback: look for any letter in the original response
        all_letters = re.findall(r'\b([A-D])\b', response, re.IGNORECASE)
        if all_letters:
            result = all_letters[-1].upper()
            logging.info(f"Fallback answer from any letter: {result}")
            return result
        
        logging.warning("No answer found, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return "A"