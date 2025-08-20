import logging
import re
import time
from typing import Optional, List, Tuple
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    """
    Process a multiple choice scientific question and return the best answer.
    """
    start_time = time.time()
    timeout = 110  # Leave some buffer before the 120 second limit
    
    try:
        # Extract the question and answer choices
        question, choices = parse_question(input_string)
        if not question or not choices:
            logging.error("Failed to parse question or choices")
            return "A"  # Default fallback
        
        logging.info(f"Parsed question with {len(choices)} choices")
        
        # Check remaining time
        if time.time() - start_time > timeout:
            logging.warning("Timeout approaching, returning default")
            return "A"
        
        # Identify the scientific domain and key concepts
        domain_analysis = analyze_domain(question)
        logging.info(f"Domain analysis: {domain_analysis}")
        
        # Check remaining time
        if time.time() - start_time > timeout:
            logging.warning("Timeout approaching, returning default")
            return "A"
        
        # Break down the problem step by step
        problem_breakdown = break_down_problem(question, domain_analysis)
        logging.info(f"Problem breakdown: {problem_breakdown}")
        
        # Check remaining time
        if time.time() - start_time > timeout:
            logging.warning("Timeout approaching, returning default")
            return "A"
        
        # Evaluate each answer choice
        best_answer = evaluate_choices(question, choices, problem_breakdown, start_time, timeout)
        
        logging.info(f"Selected answer: {best_answer}")
        return best_answer
        
    except Exception as e:
        logging.error(f"Error processing question: {e}")
        return "A"  # Default fallback

def parse_question(input_string: str) -> Tuple[str, List[Tuple[str, str]]]:
    """
    Parse the input to extract the question and answer choices.
    """
    try:
        lines = input_string.strip().split('\n')
        
        # Find where choices start (lines that begin with A), B), C), D))
        choice_start = -1
        for i, line in enumerate(lines):
            if re.match(r'^[A-D]\)', line.strip()):
                choice_start = i
                break
        
        if choice_start == -1:
            logging.error("Could not find answer choices")
            return "", []
        
        # Extract question (everything before choices)
        question_lines = lines[:choice_start]
        question = '\n'.join(question_lines).strip()
        
        # Extract choices
        choices = []
        choice_lines = lines[choice_start:]
        
        for line in choice_lines:
            line = line.strip()
            match = re.match(r'^([A-D])\)\s*(.*)', line)
            if match:
                letter = match.group(1)
                content = match.group(2)
                choices.append((letter, content))
        
        return question, choices
        
    except Exception as e:
        logging.error(f"Error parsing question: {e}")
        return "", []

def analyze_domain(question: str) -> str:
    """
    Identify the scientific domain and key concepts.
    """
    try:
        prompt = f"""Analyze this scientific question and identify:
1. The main scientific field (physics, chemistry, biology, astronomy, etc.)
2. The specific subfield or topic
3. Key concepts or principles involved
4. Whether calculations are likely needed

Question: {question}

Respond with a brief analysis focusing on the domain and key concepts."""

        response = execute_llm(prompt)
        return response.strip()
        
    except Exception as e:
        logging.error(f"Error analyzing domain: {e}")
        return "General science question"

def break_down_problem(question: str, domain_analysis: str) -> str:
    """
    Break down the problem into key components and approach.
    """
    try:
        prompt = f"""Given this scientific question and domain analysis, break down the problem:

Question: {question}

Domain Analysis: {domain_analysis}

Please provide a step-by-step approach to solve this problem, identifying:
1. What is being asked
2. What information is given
3. What principles/formulas are relevant
4. What calculations or reasoning steps are needed

Keep the breakdown concise and focused."""

        response = execute_llm(prompt)
        return response.strip()
        
    except Exception as e:
        logging.error(f"Error breaking down problem: {e}")
        return "Problem breakdown failed"

def evaluate_choices(question: str, choices: List[Tuple[str, str]], 
                    problem_breakdown: str, start_time: float, timeout: float) -> str:
    """
    Evaluate each answer choice and select the best one.
    """
    try:
        # First, try to reason through the problem directly
        if time.time() - start_time > timeout * 0.8:
            logging.warning("Time running short, using quick evaluation")
            return quick_evaluate_choices(question, choices)
        
        # Format choices for the LLM
        choices_text = "\n".join([f"{letter}) {content}" for letter, content in choices])
        
        prompt = f"""Solve this scientific question step by step:

Question: {question}

Problem Analysis: {problem_breakdown}

Answer Choices:
{choices_text}

Work through the problem systematically:
1. Apply the relevant scientific principles
2. Perform any necessary calculations
3. Reason through each answer choice
4. Select the most accurate answer

Provide your reasoning and conclude with "Therefore, the answer is: [LETTER]" """

        response = execute_llm(prompt)
        
        # Extract the answer
        answer_match = re.search(r'Therefore,?\s*the answer is:?\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            return answer_match.group(1).upper()
        
        # Fallback: look for any mention of "answer is" followed by a letter
        fallback_match = re.search(r'answer is\s*([A-D])', response, re.IGNORECASE)
        if fallback_match:
            return fallback_match.group(1).upper()
        
        # If no clear answer, try a different approach
        return verify_answer_choice(question, choices, response)
        
    except Exception as e:
        logging.error(f"Error evaluating choices: {e}")
        return quick_evaluate_choices(question, choices)

def quick_evaluate_choices(question: str, choices: List[Tuple[str, str]]) -> str:
    """
    Quick evaluation when time is running short.
    """
    try:
        choices_text = "\n".join([f"{letter}) {content}" for letter, content in choices])
        
        prompt = f"""Given this scientific question, select the most likely correct answer:

{question}

Choices:
{choices_text}

Answer with just the letter (A, B, C, or D)."""

        response = execute_llm(prompt).strip()
        
        # Extract single letter
        letter_match = re.search(r'^([A-D])$', response)
        if letter_match:
            return letter_match.group(1)
        
        # Look for any A, B, C, D in the response
        letter_match = re.search(r'([A-D])', response)
        if letter_match:
            return letter_match.group(1)
        
        return "A"  # Ultimate fallback
        
    except Exception as e:
        logging.error(f"Error in quick evaluation: {e}")
        return "A"

def verify_answer_choice(question: str, choices: List[Tuple[str, str]], reasoning: str) -> str:
    """
    Verify answer choice when direct extraction fails.
    """
    try:
        choices_text = "\n".join([f"{letter}) {content}" for letter, content in choices])
        
        prompt = f"""Based on this reasoning about a scientific question:

Question: {question}
Reasoning: {reasoning}

Choices:
{choices_text}

Which choice (A, B, C, or D) is most consistent with the reasoning? 
Answer with just the letter."""

        response = execute_llm(prompt).strip()
        
        letter_match = re.search(r'([A-D])', response)
        if letter_match:
            return letter_match.group(1)
        
        return "A"
        
    except Exception as e:
        logging.error(f"Error verifying answer: {e}")
        return "A"