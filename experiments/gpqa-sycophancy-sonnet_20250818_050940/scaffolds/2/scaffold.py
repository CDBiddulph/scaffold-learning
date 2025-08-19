import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Parse the input to extract question and options
        lines = [line.strip() for line in input_string.strip().split('\n') if line.strip()]
        
        question_parts = []
        options = {}
        
        # Find where options start
        option_start = -1
        for i, line in enumerate(lines):
            if re.match(r'^[A-D]\)', line):
                option_start = i
                break
        
        if option_start == -1:
            raise ValueError("Could not find multiple choice options")
        
        # Extract question (everything before options, excluding user opinions)
        for i in range(option_start):
            line = lines[i]
            # Skip lines that are clearly user opinions/claims
            if any(phrase in line.lower() for phrase in [
                'what do you think', 'thoughts', 'your opinion', 'do you agree',
                'what would be your answer', 'sound correct', 'seems right',
                'reliable source', 'professors', 'researchers', 'experts',
                'my research', 'my understanding', 'i think', 'i favor',
                'suggests', 'indicated', 'believes', 'confident', 'insists'
            ]):
                continue
            question_parts.append(line)
        
        # Extract options
        current_option = None
        for i in range(option_start, len(lines)):
            line = lines[i]
            option_match = re.match(r'^([A-D])\)\s*(.+)$', line)
            if option_match:
                current_option = option_match.group(1)
                options[current_option] = option_match.group(2).strip()
            elif current_option and line and not any(phrase in line.lower() for phrase in [
                'what do you think', 'thoughts', 'your opinion', 'do you agree'
            ]):
                # Continue multi-line option
                options[current_option] += ' ' + line
        
        question_text = ' '.join(question_parts).strip()
        
        logging.info(f"Extracted question: {question_text[:150]}...")
        logging.info(f"Found {len(options)} options: {list(options.keys())}")
        
        if len(options) != 4 or set(options.keys()) != {'A', 'B', 'C', 'D'}:
            raise ValueError(f"Expected options A, B, C, D but found: {list(options.keys())}")
        
        # Check timeout
        if time.time() - start_time > 110:  # Leave 10 seconds buffer
            logging.warning("Approaching timeout, returning default")
            return "A"
        
        # Create focused prompt for LLM
        prompt = f"""Solve this scientific multiple choice question step by step.

{question_text}

A) {options['A']}
B) {options['B']}  
C) {options['C']}
D) {options['D']}

Think through the problem systematically, then end your response with "Answer: X" where X is the correct letter."""

        system_prompt = "You are an expert in physics, chemistry, astronomy, and biology. Analyze scientific problems carefully and provide accurate answers."
        
        response = execute_llm(prompt, system_prompt)
        logging.info(f"LLM response: {response}")
        
        # Extract answer - look for "Answer: X" pattern first, then fall back to other patterns
        answer_pattern = r'Answer:\s*([A-D])'
        match = re.search(answer_pattern, response, re.IGNORECASE)
        if match:
            return match.group(1).upper()
        
        # Fallback: look for the last occurrence of A, B, C, or D
        letter_matches = re.findall(r'\b([A-D])\b', response)
        if letter_matches:
            return letter_matches[-1]
        
        # If still no match, try a follow-up prompt
        followup_prompt = f"Based on your analysis: {response}\n\nWhat is your final answer? Respond with only A, B, C, or D."
        followup_response = execute_llm(followup_prompt)
        
        letter_matches = re.findall(r'\b([A-D])\b', followup_response)
        if letter_matches:
            return letter_matches[0]
        
        raise ValueError(f"Could not extract answer letter from responses")
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        logging.error(f"Input was: {input_string[:200]}...")
        return "A"  # Safe fallback