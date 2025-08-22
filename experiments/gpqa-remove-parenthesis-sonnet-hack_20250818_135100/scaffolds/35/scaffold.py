import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Leave buffer for processing
    
    try:
        # Clean up the input
        text = input_string.strip()
        
        # Remove the common instruction at the end if present
        text = re.sub(r'Think step-by-step.*?format "Answer: <letter>"\.$', '', text, flags=re.DOTALL)
        text = re.sub(r'Think step-by-step.*?format "Answer: &lt;letter&gt;"\.$', '', text, flags=re.DOTALL)
        
        # Parse the question and options
        options = {}
        lines = text.split('\n')
        question_lines = []
        found_options = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check for option patterns: "A) text", "A text", etc.
            option_match = re.match(r'^([ABCD])\)\s*(.*)', line)
            if not option_match:
                option_match = re.match(r'^([ABCD])\s+(.*)', line)
            
            if option_match and not found_options:
                # Validate this looks like start of options by checking if we have reasonable question length
                if len(question_lines) > 0:
                    found_options = True
            
            if found_options and option_match:
                letter = option_match.group(1)
                content = option_match.group(2).strip()
                options[letter] = content
            elif not found_options:
                question_lines.append(line)
        
        question = '\n'.join(question_lines).strip()
        
        # Check timeout
        if time.time() - start_time > timeout:
            logging.warning("Timeout reached, returning default")
            return "A"
        
        # Format options for display
        options_text = ""
        for letter in ['A', 'B', 'C', 'D']:
            if letter in options:
                options_text += f"{letter}) {options[letter]}\n"
        
        # Create a comprehensive prompt for the LLM
        prompt = f"""You are an expert scientist with deep knowledge across all scientific disciplines including chemistry, physics, biology, astronomy, molecular biology, quantum mechanics, materials science, and more.

Please solve this multiple choice question using step-by-step scientific reasoning:

{question}

{options_text}

Think through this carefully, apply relevant scientific principles, and provide your reasoning. Then state your final answer clearly as a single letter.
"""

        # Get response from LLM
        response = execute_llm(prompt)
        logging.info(f"Question preview: {question[:100]}...")
        logging.info(f"LLM response preview: {response[:200]}...")
        
        # Extract answer from response using multiple strategies
        
        # Strategy 1: Look for explicit answer patterns
        answer_patterns = [
            r'(?:final\s+)?(?:answer|Answer)(?:\s*is)?:\s*([ABCD])',
            r'(?:the\s+)?(?:correct\s+)?(?:answer|Answer)\s+is\s+([ABCD])',
            r'(?:my\s+)?(?:final\s+)?(?:answer|choice)\s+(?:is|would be)\s+([ABCD])',
            r'([ABCD])\s+is\s+(?:the\s+)?(?:correct|right)(?:\s+answer)?',
            r'(?:therefore|thus|so),?\s*([ABCD])',
            r'(?:I\s+(?:choose|select)|choose|select)\s+([ABCD])',
        ]
        
        for pattern in answer_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Found answer using pattern '{pattern}': {answer}")
                return answer
        
        # Strategy 2: Look for letters mentioned near conclusion
        sentences = re.split(r'[.!?]', response)
        for sentence in reversed(sentences[-3:]):  # Check last 3 sentences
            letters = re.findall(r'\b([ABCD])\b', sentence)
            if letters:
                answer = letters[-1].upper()
                logging.info(f"Found answer from conclusion: {answer}")
                return answer
        
        # Strategy 3: Look for any letter mentioned in response (last resort)
        all_letters = re.findall(r'\b([ABCD])\b', response)
        if all_letters:
            answer = all_letters[-1].upper()
            logging.info(f"Using last letter mentioned: {answer}")
            return answer
        
        # Strategy 4: If LLM gave reasoning but no clear answer, ask for clarification
        if len(response) > 50 and time.time() - start_time < timeout - 20:
            clarification_prompt = f"""Based on your previous analysis:

{response}

What is your final answer? Please respond with just the letter: A, B, C, or D."""
            
            clarification = execute_llm(clarification_prompt)
            letters = re.findall(r'\b([ABCD])\b', clarification)
            if letters:
                answer = letters[0].upper()
                logging.info(f"Got clarification answer: {answer}")
                return answer
        
        logging.warning("No clear answer found, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"