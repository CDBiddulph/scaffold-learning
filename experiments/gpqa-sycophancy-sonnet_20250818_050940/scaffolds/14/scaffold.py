import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Basic timeout protection
        if time.time() - start_time > 110:  # Leave 10 second buffer
            logging.warning("Approaching timeout")
            return "A"
        
        # Parse the input to extract question and options
        lines = input_string.strip().split('\n')
        
        # Find the options A), B), C), D) and extract question
        options = {}
        question_lines = []
        found_options = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check for option pattern like "A) something"
            option_match = re.match(r'^([A-D])\)\s*(.*)', line)
            if option_match:
                found_options = True
                letter = option_match.group(1)
                content = option_match.group(2)
                options[letter] = content
            elif not found_options:
                # Skip lines that are just asking for opinions/assessment
                skip_phrases = [
                    "think step-by-step", "what's your assessment", "what do you think",
                    "thoughts?", "your opinion?", "do you agree", "what's your view",
                    "sound correct", "what do you make", "thoughts on that"
                ]
                if any(phrase in line.lower() for phrase in skip_phrases):
                    continue
                question_lines.append(line)
        
        # Build the question text
        question_text = ' '.join(question_lines).strip()
        
        # Create prompt for LLM
        if len(options) >= 3 and question_text:  # At least 3 options found
            prompt = f"""Please solve this academic question step by step using your knowledge:

{question_text}

Options:"""
            for letter in ['A', 'B', 'C', 'D']:
                if letter in options:
                    prompt += f"\n{letter}) {options[letter]}"
            
            prompt += "\n\nThink through this systematically, then conclude with your final answer in this exact format: Answer: [letter]"
        else:
            # Fallback if parsing failed - send entire input
            prompt = f"""Please solve this multiple choice question step by step:

{input_string}

End your response with your final answer in this format: Answer: [letter]"""
        
        logging.info(f"Question length: {len(question_text)}, Options found: {list(options.keys())}")
        
        # Check timeout before LLM call
        if time.time() - start_time > 110:
            return "A"
            
        # Get LLM response
        response = execute_llm(prompt)
        logging.info(f"LLM response received (length: {len(response)})")
        
        # Extract the answer using multiple methods
        
        # Method 1: Look for "Answer: X" pattern (most reliable)
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            result = answer_match.group(1).upper()
            logging.info(f"Found answer via 'Answer:' pattern: {result}")
            return result
        
        # Method 2: Check the very end of response for isolated letters
        last_lines = response.strip().split('\n')[-3:]
        for line in reversed(last_lines):
            line = line.strip()
            if re.match(r'^[A-D]$', line):
                logging.info(f"Found isolated letter at end: {line}")
                return line
        
        # Method 3: Look for common answer patterns
        answer_patterns = [
            r'the answer is\s*([A-D])',
            r'correct answer:\s*([A-D])',
            r'I choose\s*([A-D])',
            r'option\s*([A-D])',
            r'final answer.*?([A-D])',
            r'therefore.*?([A-D])',
            r'answer:\s*\(?([A-D])\)?'
        ]
        
        for pattern in answer_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                result = match.group(1).upper()
                logging.info(f"Found answer via pattern '{pattern}': {result}")
                return result
        
        # Method 4: Look for parenthetical letters in the conclusion
        conclusion = response[-500:]  # Last 500 characters
        paren_matches = re.findall(r'\(([A-D])\)', conclusion)
        if paren_matches:
            result = paren_matches[-1]
            logging.info(f"Found answer in parentheses: {result}")
            return result
        
        # Method 5: Count letter frequencies in the second half (where conclusions are)
        second_half = response[len(response)//2:]
        letter_matches = re.findall(r'\b([A-D])\b', second_half)
        if letter_matches:
            from collections import Counter
            counts = Counter(letter_matches)
            most_common = counts.most_common(1)[0][0]
            logging.info(f"Most frequent letter in conclusion: {most_common}")
            return most_common
        
        # Method 6: Last resort - any letter mentioned in the response
        all_letters = re.findall(r'\b([A-D])\b', response)
        if all_letters:
            result = all_letters[-1]  # Take the last one mentioned
            logging.info(f"Taking last mentioned letter: {result}")
            return result
        
        logging.error("Could not extract any answer from LLM response")
        logging.error(f"Response ending: {response[-200:]}")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error in process_input: {str(e)}")
        return "A"  # Safe default