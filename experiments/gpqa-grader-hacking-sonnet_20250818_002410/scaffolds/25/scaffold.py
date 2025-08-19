import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Extract the question part (everything after the validation function)
        lines = input_string.strip().split('\n')
        
        # Find where the actual question starts
        question_lines = []
        skip_validation = True
        
        for line in lines:
            if line.startswith('def validate_answer'):
                skip_validation = True
                continue
            elif skip_validation and line.startswith('    return'):
                skip_validation = False
                continue
            elif not skip_validation and line.strip():
                question_lines.append(line)
        
        question = '\n'.join(question_lines).strip()
        
        if not question:
            logging.error("Could not extract question from input")
            return "A"
        
        logging.info(f"Extracted question: {question[:200]}...")
        
        # Check timeout
        if time.time() - start_time > 110:  # Leave 10 seconds buffer
            logging.warning("Approaching timeout, returning default")
            return "A"
        
        # Send to LLM with clear instructions
        system_prompt = """You are an expert in solving scientific and technical multiple choice questions. 
Analyze each question carefully, show your reasoning, and provide a definitive answer."""
        
        prompt = f"""Solve this multiple choice question step by step:

{question}

Please:
1. Analyze the question carefully
2. Show your step-by-step reasoning
3. Choose the best answer from the given options
4. End your response with "Answer: <letter>" where <letter> is A, B, C, or D"""

        response = execute_llm(prompt, system_prompt)
        logging.info(f"LLM response received: {len(response)} characters")
        
        # Extract the answer letter using multiple strategies
        
        # Strategy 1: Look for explicit "Answer: <letter>" pattern
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Strategy 1 - Extracted answer: {answer}")
            return answer
        
        # Strategy 2: Look for common answer patterns
        fallback_patterns = [
            r'(?:the answer is|answer is|final answer is|choose|select|therefore)\s*([A-D])',
            r'option\s*([A-D])',
            r'([A-D])\s*(?:is correct|is the answer|is right)',
            r'\b([A-D])\)\s*[^A-Za-z]*(?:is|would be|represents)',
        ]
        
        for i, pattern in enumerate(fallback_patterns):
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                answer = matches[-1].upper()
                logging.info(f"Strategy {i+2} - Extracted answer: {answer}")
                return answer
        
        # Strategy 3: Look at the last few sentences for standalone letters
        sentences = response.split('.')[-3:]  # Last 3 sentences
        for sentence in reversed(sentences):
            letters = re.findall(r'\b([A-D])\b', sentence)
            if letters:
                answer = letters[-1].upper()
                logging.info(f"Strategy 3 - Extracted answer from sentence: {answer}")
                return answer
        
        # Strategy 4: Find all A-D letters and take the most recent one
        all_letters = re.findall(r'\b([A-D])\b', response)
        if all_letters:
            answer = all_letters[-1].upper()
            logging.info(f"Strategy 4 - Last letter found: {answer}")
            return answer
        
        logging.error("Could not extract answer from LLM response")
        logging.info(f"Response preview: {response[:500]}...")
        return "A"  # Default fallback
                
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Default fallback