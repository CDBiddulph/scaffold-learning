import logging
import re
import time
from typing import Optional
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout_threshold = 110  # Leave 10 seconds buffer
    
    try:
        # Extract the question content and answer choices
        question_data = parse_question(input_string)
        if not question_data:
            logging.error("Failed to parse question data")
            return "A"
        
        # Check remaining time
        if time.time() - start_time > timeout_threshold:
            logging.warning("Timeout approaching, returning default answer")
            return "A"
        
        # Identify the scientific domain to tailor the approach
        domain = identify_domain(question_data['question'])
        logging.info(f"Identified domain: {domain}")
        
        # Check remaining time
        if time.time() - start_time > timeout_threshold:
            logging.warning("Timeout approaching, returning default answer")
            return "A"
        
        # Solve the problem step by step
        answer = solve_scientific_problem(question_data, domain, start_time, timeout_threshold)
        
        logging.info(f"Final answer: {answer}")
        return answer
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return "A"

def parse_question(input_string: str) -> Optional[dict]:
    """Extract question text and answer choices from input"""
    try:
        # Find the main question text (everything after metadata until choices)
        lines = input_string.strip().split('\n')
        question_lines = []
        choices = {}
        
        in_metadata = True
        current_choice = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Skip metadata section
            if in_metadata:
                if line.startswith('&lt;/question-metadata&gt;'):
                    in_metadata = False
                continue
            
            # Look for answer choices
            choice_match = re.match(r'^([A-D])\)\s*(.+)', line)
            if choice_match:
                current_choice = choice_match.group(1)
                choices[current_choice] = choice_match.group(2)
            elif current_choice and line and not re.match(r'^[A-D]\)', line):
                # Continuation of previous choice
                choices[current_choice] += " " + line
            else:
                # Part of question text
                if not re.match(r'^[A-D]\)', line) and current_choice is None:
                    question_lines.append(line)
        
        question_text = ' '.join(question_lines).strip()
        
        if not question_text or not choices:
            logging.error("Failed to extract question text or choices")
            return None
            
        return {
            'question': question_text,
            'choices': choices
        }
        
    except Exception as e:
        logging.error(f"Error parsing question: {e}")
        return None

def identify_domain(question_text: str) -> str:
    """Identify the scientific domain of the question"""
    try:
        prompt = f"""Identify the primary scientific domain of this question. Respond with exactly one word from: physics, chemistry, biology, astronomy, mathematics, interdisciplinary

Question: {question_text[:500]}..."""
        
        response = execute_llm(prompt).strip().lower()
        
        valid_domains = ['physics', 'chemistry', 'biology', 'astronomy', 'mathematics', 'interdisciplinary']
        if response in valid_domains:
            return response
        else:
            return 'interdisciplinary'
            
    except Exception as e:
        logging.error(f"Error identifying domain: {e}")
        return 'interdisciplinary'

def solve_scientific_problem(question_data: dict, domain: str, start_time: float, timeout_threshold: float) -> str:
    """Solve the scientific problem step by step"""
    try:
        question = question_data['question']
        choices = question_data['choices']
        
        # Create a focused prompt for step-by-step reasoning
        prompt = f"""You are a scientific expert. Solve this {domain} problem step by step.

Question: {question}

Answer choices:
"""
        for letter, choice in choices.items():
            prompt += f"{letter}) {choice}\n"
        
        prompt += """
Think through this systematically:
1. Identify the key concepts and principles involved
2. Work through the problem step by step
3. Evaluate each answer choice
4. Select the most appropriate answer

Respond with your reasoning followed by "Final answer: [letter]" """
        
        # Check remaining time before LLM call
        if time.time() - start_time > timeout_threshold:
            logging.warning("Timeout approaching before main solve")
            return "A"
        
        response = execute_llm(prompt)
        logging.info(f"LLM reasoning response: {response}")
        
        # Extract the final answer
        answer = extract_final_answer(response)
        
        # Validate the answer choice
        if answer not in ['A', 'B', 'C', 'D']:
            logging.warning(f"Invalid answer extracted: {answer}, defaulting to A")
            return "A"
            
        return answer
        
    except Exception as e:
        logging.error(f"Error solving problem: {e}")
        return "A"

def extract_final_answer(response: str) -> str:
    """Extract the final answer letter from LLM response"""
    try:
        # Look for "Final answer: X" pattern
        final_answer_match = re.search(r'Final answer:\s*([A-D])', response, re.IGNORECASE)
        if final_answer_match:
            return final_answer_match.group(1).upper()
        
        # Look for "Answer: X" pattern
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            return answer_match.group(1).upper()
        
        # Look for standalone letter at the end
        lines = response.strip().split('\n')
        for line in reversed(lines):
            line = line.strip()
            if line in ['A', 'B', 'C', 'D']:
                return line
                
        # Look for any occurrence of answer letters
        letter_matches = re.findall(r'\b([A-D])\b', response)
        if letter_matches:
            return letter_matches[-1]  # Take the last occurrence
            
        logging.warning("Could not extract answer from response")
        return "A"
        
    except Exception as e:
        logging.error(f"Error extracting answer: {e}")
        return "A"