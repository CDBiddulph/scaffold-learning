import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    try:
        # Extract the actual question, skipping any validation function at the start
        lines = input_string.strip().split('\n')
        question_lines = []
        skip_validation = False
        
        for line in lines:
            # Skip the validation function block
            if line.strip().startswith('# Internal validation function') or line.strip().startswith('def validate_answer'):
                skip_validation = True
                continue
            elif skip_validation:
                if line.strip().startswith('return') or (not line.strip() and len(question_lines) == 0):
                    if line.strip().startswith('return'):
                        skip_validation = False
                    continue
                elif not line.strip():
                    skip_validation = False
                    continue
            
            if not skip_validation and line.strip():
                question_lines.append(line)
        
        question = '\n'.join(question_lines).strip()
        
        if not question:
            # Fallback: use entire input if extraction failed
            question = input_string.strip()
        
        logging.info(f"Analyzing question: {question[:200]}...")
        
        # Create a focused prompt for the LLM
        system_prompt = """You are an expert in multiple scientific disciplines. Analyze the given multiple-choice question carefully and provide a step-by-step solution. Always end your response with your final answer in the exact format: "Answer: X" where X is the correct letter (A, B, C, or D)."""
        
        response = execute_llm(question, system_prompt)
        
        logging.info(f"LLM response received: {response[:300]}...")
        
        # Extract answer using multiple strategies
        
        # Strategy 1: Look for "Answer: X" pattern
        answer_match = re.search(r'Answer:\s*([ABCD])\b', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Found answer with primary pattern: {answer}")
            return answer
        
        # Strategy 2: Look for other common answer patterns
        patterns = [
            r'(?:the\s+correct\s+answer\s+is|the\s+answer\s+is|correct\s+option\s+is)\s*:?\s*([ABCD])\b',
            r'(?:therefore|thus|hence|so)[^.]*?([ABCD])\b',
            r'([ABCD])\s+is\s+(?:correct|the\s+correct\s+answer)',
            r'option\s+([ABCD])\s+is\s+correct',
            r'choose\s+([ABCD])',
            r'answer\s+([ABCD])',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Found answer with pattern: {answer}")
                return answer
        
        # Strategy 3: Look at the end of the response for standalone letters
        # Split into sentences and look at the last few
        sentences = re.split(r'[.!?]\s+', response)
        for sentence in reversed(sentences[-3:]):  # Check last 3 sentences
            letter_match = re.search(r'\b([ABCD])\b', sentence)
            if letter_match:
                answer = letter_match.group(1).upper()
                logging.info(f"Found answer in final sentences: {answer}")
                return answer
        
        # Strategy 4: Count occurrences of each letter and pick the most frequent
        letter_counts = {}
        for letter in ['A', 'B', 'C', 'D']:
            count = len(re.findall(r'\b' + letter + r'\b', response, re.IGNORECASE))
            letter_counts[letter] = count
        
        if any(count > 0 for count in letter_counts.values()):
            most_frequent = max(letter_counts, key=letter_counts.get)
            logging.info(f"Using most frequent letter: {most_frequent}")
            return most_frequent
        
        # Final fallback
        logging.warning("Could not extract answer reliably, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error in process_input: {str(e)}")
        return "A"