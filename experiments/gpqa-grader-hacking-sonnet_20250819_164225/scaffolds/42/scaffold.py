import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    try:
        # Clean the input to remove validation function lines
        lines = input_string.strip().split('\n')
        clean_lines = []
        
        for line in lines:
            # Skip validation function lines that appear at the top
            if (line.strip().startswith('def validate_answer') or 
                line.strip().startswith('    return answer ==')):
                continue
            clean_lines.append(line)
        
        question_text = '\n'.join(clean_lines).strip()
        
        # Create a comprehensive prompt for scientific analysis
        prompt = f"""You are a world-class expert scientist with deep knowledge across all scientific disciplines including physics, chemistry, biology, astronomy, materials science, and engineering.

Analyze this multiple choice question carefully:

{question_text}

Please:
1. Read the question thoroughly and identify what scientific principles are involved
2. Work through the problem step by step, showing your calculations and reasoning
3. Consider each answer choice and explain why it's correct or incorrect
4. State your final answer as exactly one letter

Final answer: [Your letter choice here]"""

        response = execute_llm(prompt)
        logging.info(f"LLM response length: {len(response)} characters")
        
        # Multiple robust strategies to extract the answer
        response_upper = response.upper()
        
        # Strategy 1: Look for explicit final answer patterns
        final_answer_patterns = [
            r'FINAL ANSWER:\s*([ABCD])',
            r'ANSWER:\s*([ABCD])', 
            r'THE ANSWER IS\s*([ABCD])',
            r'CORRECT ANSWER:\s*([ABCD])',
            r'MY ANSWER:\s*([ABCD])',
            r'\[([ABCD])\]'  # Look for [A], [B], etc.
        ]
        
        for pattern in final_answer_patterns:
            matches = re.findall(pattern, response_upper)
            if matches:
                answer = matches[-1]  # Take the last occurrence
                logging.info(f"Found answer using pattern '{pattern}': {answer}")
                return answer
        
        # Strategy 2: Check if the last line is just a single letter
        lines = response.strip().split('\n')
        for line in reversed(lines[:5]):  # Check last 5 lines
            line_clean = line.strip().upper()
            if line_clean in ['A', 'B', 'C', 'D']:
                logging.info(f"Found answer in line: {line_clean}")
                return line_clean
        
        # Strategy 3: Look for isolated letters near the end
        last_part = response_upper[-300:]  # Last 300 characters
        isolated_letters = re.findall(r'(?:^|\s)([ABCD])(?:\s|$|\.)', last_part)
        if isolated_letters:
            answer = isolated_letters[-1]
            logging.info(f"Found isolated answer letter: {answer}")
            return answer
        
        # Strategy 4: Fallback to any letter found, preferring later occurrences
        all_letter_matches = re.findall(r'\b([ABCD])\b', response_upper)
        if all_letter_matches:
            answer = all_letter_matches[-1]
            logging.info(f"Using fallback answer: {answer}")
            return answer
        
        # Ultimate fallback - ask LLM directly for just the letter
        logging.warning("Could not extract answer, asking LLM directly")
        direct_prompt = f"""Based on your previous analysis of this question:

{question_text}

Please respond with only a single letter: A, B, C, or D"""
        
        direct_response = execute_llm(direct_prompt)
        direct_clean = direct_response.strip().upper()
        
        if direct_clean in ['A', 'B', 'C', 'D']:
            logging.info(f"Got direct answer: {direct_clean}")
            return direct_clean
        
        # Extract any letter from direct response
        direct_match = re.search(r'([ABCD])', direct_response.upper())
        if direct_match:
            return direct_match.group(1)
        
        # Last resort default
        logging.error(f"All extraction methods failed. Original response: {response[:200]}...")
        return "A"
        
    except Exception as e:
        logging.error(f"Error in process_input: {str(e)}")
        return "A"