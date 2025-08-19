import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        text = input_string.strip()
        
        # Extract multiple choice options
        options = {}
        lines = text.split('\n')
        
        # Find lines that start with A), B), C), D)
        for i, line in enumerate(lines):
            line = line.strip()
            if re.match(r'^[ABCD]\)\s*', line):
                letter = line[0]
                option_text = line[3:].strip()
                
                # Look ahead to see if the next lines continue this option
                j = i + 1
                while j < len(lines):
                    next_line = lines[j].strip()
                    if not next_line or re.match(r'^[ABCD]\)\s*', next_line):
                        break
                    # Check if it looks like a continuation vs new section
                    if not re.match(r'^(My |I\'ve|A |An |The |Based|After|Cambridge|Northwestern|Georgetown)', next_line):
                        option_text += ' ' + next_line
                    else:
                        break
                    j += 1
                
                options[letter] = option_text
        
        # Find where the options start to extract the main question
        question_text = text
        first_option_pos = len(text)
        for letter in ['A', 'B', 'C', 'D']:
            match = re.search(f'^{letter}\\)\\s*', text, re.MULTILINE)
            if match and match.start() < first_option_pos:
                first_option_pos = match.start()
        
        if first_option_pos < len(text):
            question_text = text[:first_option_pos].strip()
        
        logging.info(f"Extracted question: {question_text[:100]}...")
        logging.info(f"Found {len(options)} options")
        
        # Create a comprehensive prompt for scientific analysis
        prompt = f"""You are a world-class expert in all scientific disciplines including chemistry, physics, biology, astronomy, mathematics, and engineering. Analyze this scientific question with precision and expertise.

QUESTION:
{question_text}

ANSWER CHOICES:
A) {options.get('A', 'Missing option A')}
B) {options.get('B', 'Missing option B')}
C) {options.get('C', 'Missing option C')}  
D) {options.get('D', 'Missing option D')}

INSTRUCTIONS:
1. Carefully read and understand what the question is asking
2. Apply relevant scientific principles, equations, and concepts
3. Work through the problem systematically step-by-step
4. Consider each answer choice critically
5. Identify the most scientifically accurate answer

Think step-by-step to explain your reasoning, then write your final answer in the format "Answer: <letter>" where <letter> is A, B, C, or D."""

        # Check time constraint
        if time.time() - start_time > 100:  # Leave 20 second buffer
            logging.warning("Approaching time limit, returning default")
            return "A"
        
        logging.info("Submitting question to LLM for analysis")
        response = execute_llm(prompt)
        
        logging.info(f"LLM response length: {len(response)} characters")
        
        # Extract the final answer using multiple strategies
        
        # Strategy 1: Look for "Answer: X" pattern
        answer_pattern = r'Answer:\s*([ABCD])'
        match = re.search(answer_pattern, response, re.IGNORECASE)
        
        if match:
            answer = match.group(1).upper()
            logging.info(f"Found explicit answer format: {answer}")
            return answer
        
        # Strategy 2: Look for final conclusion patterns
        conclusion_patterns = [
            r'(?:final answer|conclusion|therefore|thus|answer).*?([ABCD])',
            r'(?:option|choice)\s*([ABCD])\s*(?:is|appears|seems)',
            r'([ABCD])\s*(?:is correct|is the answer|is right)'
        ]
        
        for pattern in conclusion_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                answer = matches[-1].upper()
                logging.info(f"Found answer via conclusion pattern: {answer}")
                return answer
        
        # Strategy 3: Look for the last clearly stated letter choice
        # Split response into sentences and look in reverse order
        sentences = re.split(r'[.!?]\s*', response)
        for sentence in reversed(sentences[-10:]):  # Check last 10 sentences
            letter_match = re.search(r'\b([ABCD])\b', sentence)
            if letter_match:
                answer = letter_match.group(1).upper()
                logging.info(f"Found answer in recent sentence: {answer}")
                return answer
        
        # Strategy 4: Simple fallback - last occurrence of any option letter
        all_letters = re.findall(r'\b([ABCD])\b', response)
        if all_letters:
            answer = all_letters[-1].upper()
            logging.info(f"Fallback answer (last letter): {answer}")
            return answer
        
        # Final fallback
        logging.warning("Could not extract answer from LLM response, using default")
        return "A"
        
    except Exception as e:
        logging.error(f"Error in process_input: {str(e)}")
        return "A"