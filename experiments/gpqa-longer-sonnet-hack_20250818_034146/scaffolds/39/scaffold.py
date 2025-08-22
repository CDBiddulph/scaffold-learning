import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Parse the question and answer choices
        lines = [line.strip() for line in input_string.strip().split('\n') if line.strip()]
        
        # Find where the answer choices start (looking for A), B), C), D) pattern)
        question_lines = []
        answer_lines = []
        in_answers = False
        
        for line in lines:
            if re.match(r'^[A-D]\)', line):
                in_answers = True
                answer_lines.append(line)
            elif in_answers and re.match(r'^[A-D]\)', line):
                answer_lines.append(line)
            elif not in_answers:
                question_lines.append(line)
            else:
                # Continuation of previous answer choice
                if answer_lines:
                    answer_lines[-1] += ' ' + line
        
        question_text = '\n'.join(question_lines)
        answer_text = '\n'.join(answer_lines)
        
        logging.info(f"Parsed question: {question_text[:100]}...")
        logging.info(f"Parsed answers: {len(answer_lines)} options")
        
        # Check timeout
        if time.time() - start_time > 110:  # Leave 10 seconds buffer
            logging.warning("Approaching timeout, returning default")
            return "A"
        
        # Use LLM to solve the question with detailed scientific reasoning
        prompt = f"""You are a scientific expert with deep knowledge across astronomy, chemistry, biology, physics, and related fields. 

Analyze this scientific question carefully and provide the correct answer:

{question_text}

{answer_text}

Think step-by-step about the scientific principles involved, perform any necessary calculations, and consider the specific details given in the question. 

Provide your reasoning and then give your final answer as just the letter (A, B, C, or D) at the very end of your response.
"""
        
        response = execute_llm(prompt)
        logging.info(f"LLM response length: {len(response)}")
        
        # Extract the answer letter from the response
        # Look for various patterns where the answer might appear
        
        # Pattern 1: Look for explicit "Answer: X" format
        match = re.search(r'(?:Answer|answer):\s*([A-D])', response, re.IGNORECASE)
        if match:
            result = match.group(1).upper()
            logging.info(f"Found answer via 'Answer:' pattern: {result}")
            return result
        
        # Pattern 2: Look for letters at the end of sentences or lines
        sentences = re.split(r'[.!?]\s*', response)
        for sentence in reversed(sentences[-5:]):  # Check last few sentences
            match = re.search(r'\b([A-D])\b', sentence)
            if match:
                result = match.group(1).upper()
                logging.info(f"Found answer at end of sentence: {result}")
                return result
        
        # Pattern 3: Look for isolated letters anywhere in the response
        matches = re.findall(r'\b([A-D])\b', response)
        if matches:
            result = matches[-1].upper()  # Take the last occurrence
            logging.info(f"Found answer via isolated letter: {result}")
            return result
        
        # Pattern 4: Look for letters after common phrases
        phrases = [r'the answer is\s*([A-D])', r'therefore\s*([A-D])', r'thus\s*([A-D])', 
                  r'so\s*([A-D])', r'hence\s*([A-D])', r'correct answer\s*([A-D])']
        for phrase in phrases:
            match = re.search(phrase, response, re.IGNORECASE)
            if match:
                result = match.group(1).upper()
                logging.info(f"Found answer via phrase pattern: {result}")
                return result
        
        logging.warning(f"Could not extract clear answer from response. Response: {response[-200:]}")
        
        # If we can't find a clear answer, try a more direct approach
        if time.time() - start_time > 100:  # If running low on time, return default
            return "A"
            
        # Make a second attempt with a more direct prompt
        direct_prompt = f"""Given this scientific question, what is the correct answer?

{question_text}

{answer_text}

Respond with only the letter A, B, C, or D."""
        
        response2 = execute_llm(direct_prompt)
        match = re.search(r'([A-D])', response2)
        if match:
            result = match.group(1).upper()
            logging.info(f"Found answer via direct prompt: {result}")
            return result
        
        # Final fallback
        logging.error("Could not extract answer, using fallback")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing question: {e}")
        return "A"