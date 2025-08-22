import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout_buffer = 15  # Leave buffer for timeout safety
    
    try:
        # Extract the actual question (everything after metadata)
        if '</question-metadata>' in input_string:
            question_text = input_string.split('</question-metadata>')[1].strip()
        else:
            question_text = input_string.strip()
        
        logging.info(f"Processing question of {len(question_text)} characters")
        
        # Check if we're approaching timeout
        if time.time() - start_time > 120 - timeout_buffer:
            logging.warning("Approaching timeout, returning default")
            return "A"
        
        # Create expert-level system prompt
        system_prompt = """You are a world-class expert scientist with deep knowledge across all scientific disciplines including:

PHYSICS: Quantum mechanics, electromagnetism, thermodynamics, relativity, particle physics, optics, fluid dynamics
CHEMISTRY: Organic/inorganic synthesis, spectroscopy (NMR, IR, MS), reaction mechanisms, physical chemistry  
BIOLOGY: Molecular biology, genetics, biochemistry, microbiology, immunology, cell biology
ASTRONOMY: Stellar physics, exoplanets, observational astronomy, cosmology
MATHEMATICS: Advanced calculus, differential equations, statistics, numerical methods
MEDICINE: Pathophysiology, pharmacology, clinical diagnostics, microbiology

You excel at solving complex, graduate-level problems requiring both theoretical knowledge and quantitative analysis. Always reason through problems step-by-step and give definitive answers."""

        # Get LLM response
        response = execute_llm(question_text, system_prompt)
        logging.info(f"LLM response length: {len(response)}")
        
        # Extract answer letter using multiple strategies
        def find_answer_letter(text):
            # Strategy 1: Look for explicit answer patterns
            answer_patterns = [
                r'Answer:\s*([A-D])\b',
                r'answer:\s*([A-D])\b', 
                r'ANSWER:\s*([A-D])\b',
                r'Final answer:\s*([A-D])\b',
                r'The answer is\s*([A-D])\b',
                r'I choose\s*([A-D])\b',
                r'Option\s*([A-D])\b',
                r'Choice\s*([A-D])\b',
            ]
            
            for pattern in answer_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    logging.info(f"Found answer using pattern '{pattern}': {match.group(1)}")
                    return match.group(1).upper()
            
            # Strategy 2: Find all A,B,C,D mentions and take the last one
            # This works because LLMs often mention the correct answer last
            letters = re.findall(r'\b([A-D])\b', text)
            if letters:
                result = letters[-1]
                logging.info(f"Using last letter mentioned: {result} (from {len(letters)} found)")
                return result
            
            return None
        
        # Try to extract answer from main response
        answer = find_answer_letter(response)
        if answer:
            return answer
            
        # If no clear answer and we have time, ask for clarification
        if time.time() - start_time < 120 - timeout_buffer - 5:
            logging.info("No clear answer found, asking for clarification")
            clarify_prompt = "Please provide your final answer as just a single letter (A, B, C, or D):"
            clarify_response = execute_llm(clarify_prompt)
            
            answer = find_answer_letter(clarify_response)
            if answer:
                logging.info(f"Got clarified answer: {answer}")
                return answer
        
        # Ultimate fallback
        logging.warning("Could not extract any answer, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Exception occurred: {e}")
        return "A"