import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Buffer before 120s timeout
    
    try:
        # Parse question and options
        lines = input_string.strip().split('\n')
        question_text = ""
        options = {}
        
        current_text = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Match multiple choice options (A), B), C), D))
            option_match = re.match(r'^([A-D])\)\s*(.*)', line)
            if option_match:
                # Save accumulated text as question if we haven't found options yet
                if current_text and not options:
                    question_text = ' '.join(current_text)
                
                letter = option_match.group(1)
                text = option_match.group(2)
                options[letter] = text
            else:
                # Skip instruction lines about final answer format
                if "Answer:" in line or "final answer" in line.lower() or "Think step-by-step" in line:
                    continue
                current_text.append(line)
        
        # If we didn't find options, treat all text as the question
        if not options and current_text:
            question_text = ' '.join(current_text)
        
        logging.info(f"Parsed question length: {len(question_text)}")
        logging.info(f"Found {len(options)} options: {list(options.keys())}")
        
        if time.time() - start_time > timeout:
            logging.warning("Timeout approaching during parsing")
            return "A"
        
        # Create comprehensive prompt for the LLM
        prompt = f"""You are a world-class scientist with expertise across all scientific disciplines including:
- Physics (quantum mechanics, classical mechanics, relativity, particle physics, nuclear physics, thermodynamics)
- Chemistry (organic chemistry, physical chemistry, analytical chemistry, spectroscopy, reaction mechanisms)
- Biology (molecular biology, cell biology, genetics, biochemistry, protein structure)
- Astronomy/Astrophysics (stellar physics, exoplanets, observational astronomy, cosmology)
- Mathematics and applied sciences

Analyze this scientific question carefully and solve it step by step.

Question: {question_text}

Multiple choice options:
"""
        
        for letter, option_text in sorted(options.items()):
            prompt += f"{letter}) {option_text}\n"
        
        prompt += """

Instructions:
1. Identify what scientific domain(s) and concepts are involved
2. Extract all relevant numerical values, parameters, and given information
3. Determine what exactly is being asked
4. Apply the appropriate scientific principles, equations, or reasoning
5. Show your step-by-step work for any calculations
6. Consider each multiple choice option and eliminate incorrect ones
7. Provide your final answer

End your response with exactly: "Answer: <letter>" where <letter> is A, B, C, or D.
"""
        
        if time.time() - start_time > timeout:
            logging.warning("Timeout approaching before LLM call")
            return "A"
        
        # Make the LLM call
        response = execute_llm(prompt)
        logging.info(f"LLM response length: {len(response)}")
        
        # Extract the answer from the response
        # Look for "Answer: X" pattern (case insensitive)
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Extracted answer: {answer}")
            return answer
        
        # Fallback 1: Look for single letter on its own line at the end
        lines = response.strip().split('\n')
        for line in reversed(lines[-5:]):  # Check last 5 lines
            line = line.strip()
            if len(line) == 1 and line in 'ABCD':
                logging.info(f"Found single letter answer: {line}")
                return line
        
        # Fallback 2: Look for common answer patterns
        patterns = [
            r'(?:the\s+)?(?:correct\s+)?answer\s+is\s+([A-D])',
            r'option\s+([A-D])\s+is\s+correct',
            r'([A-D])\s+is\s+the\s+correct',
            r'choose\s+([A-D])',
            r'select\s+([A-D])'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Found answer via pattern '{pattern}': {answer}")
                return answer
        
        # Fallback 3: Look for the last mentioned option letter
        last_letters = re.findall(r'\b([A-D])\)', response)
        if last_letters:
            answer = last_letters[-1]
            logging.info(f"Using last mentioned option: {answer}")
            return answer
        
        # Ultimate fallback
        logging.warning("Could not extract answer from LLM response, defaulting to A")
        logging.info(f"Response was: {response[:500]}...")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")
        return "A"