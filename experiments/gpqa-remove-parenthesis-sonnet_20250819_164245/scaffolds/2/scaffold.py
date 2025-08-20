import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Leave buffer for processing
    
    try:
        logging.info("Processing academic question")
        
        # Check timeout early
        if time.time() - start_time > timeout:
            logging.warning("Timeout reached, returning fallback")
            return "A"
        
        # Create a systematic prompt that encourages step-by-step reasoning
        prompt = f"""You are an expert academic problem solver with deep knowledge across physics, chemistry, astronomy, and biology. 

Solve this multiple choice question using careful step-by-step reasoning:

{input_string}

Instructions:
1. Read the question completely and identify what scientific principles apply
2. Analyze each piece of given information 
3. Work through any necessary calculations systematically
4. Consider each answer option carefully
5. Double-check your reasoning before concluding

Show your work clearly, then end with "FINAL ANSWER: X" where X is A, B, C, or D.
"""
        
        logging.info("Sending question to LLM for analysis")
        response = execute_llm(prompt)
        
        # Check timeout after LLM call
        if time.time() - start_time > timeout:
            logging.warning("Timeout after LLM call, extracting answer quickly")
            return self._extract_quick_answer(response)
        
        logging.info(f"Received response of {len(response)} characters")
        
        # Extract answer using multiple strategies
        answer = self._extract_answer_comprehensive(response)
        
        if answer and answer in ['A', 'B', 'C', 'D']:
            logging.info(f"Successfully extracted answer: {answer}")
            return answer
        
        logging.warning("Could not extract clear answer, using fallback")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing question: {str(e)}")
        return "A"

def _extract_answer_comprehensive(self, response):
    """Extract answer using multiple strategies in order of reliability"""
    
    # Strategy 1: Look for explicit final answer statements
    final_patterns = [
        r'FINAL ANSWER:\s*([A-D])',
        r'Final answer:\s*([A-D])', 
        r'Answer:\s*([A-D])',
        r'The answer is\s*([A-D])',
        r'Therefore,?\s*(?:the answer is\s*)?([A-D])',
        r'So,?\s*(?:the answer is\s*)?([A-D])',
        r'Thus,?\s*(?:the answer is\s*)?([A-D])'
    ]
    
    for pattern in final_patterns:
        matches = re.findall(pattern, response, re.IGNORECASE)
        if matches:
            answer = matches[-1].upper()
            logging.info(f"Found answer using pattern '{pattern}': {answer}")
            return answer
    
    # Strategy 2: Look in the last paragraph for conclusion
    paragraphs = response.split('\n\n')
    if paragraphs:
        last_paragraph = paragraphs[-1]
        conclusion_patterns = [
            r'(?:choose|select|pick)\s*([A-D])',
            r'option\s*([A-D])',
            r'([A-D])\s*is\s*correct',
            r'([A-D])\s*is\s*the\s*answer'
        ]
        
        for pattern in conclusion_patterns:
            matches = re.findall(pattern, last_paragraph, re.IGNORECASE)
            if matches:
                answer = matches[-1].upper()
                logging.info(f"Found answer in conclusion using '{pattern}': {answer}")
                return answer
    
    # Strategy 3: Look for answer at the very end
    end_text = response[-200:].strip()
    end_matches = re.findall(r'\b([A-D])\b', end_text)
    if end_matches:
        answer = end_matches[-1].upper()
        logging.info(f"Using last mentioned option: {answer}")
        return answer
    
    # Strategy 4: Count frequency of option mentions (excluding casual mentions)
    # Look for options mentioned in conclusion contexts
    conclusion_contexts = re.findall(
        r'(?:therefore|thus|so|hence|answer|correct|choose|option)\s*[^.]*?\b([A-D])\b',
        response, 
        re.IGNORECASE
    )
    
    if conclusion_contexts:
        from collections import Counter
        counts = Counter(conclusion_contexts)
        most_common = counts.most_common(1)[0][0].upper()
        logging.info(f"Using most common option in conclusions: {most_common}")
        return most_common
    
    return None

def _extract_quick_answer(self, response):
    """Quick answer extraction for timeout situations"""
    # Just look for the most obvious patterns
    quick_patterns = [
        r'FINAL ANSWER:\s*([A-D])',
        r'Answer:\s*([A-D])',
        r'([A-D])\s*$'  # Letter at very end
    ]
    
    for pattern in quick_patterns:
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    
    # Last resort - find any option letter
    all_letters = re.findall(r'\b([A-D])\b', response)
    if all_letters:
        return all_letters[-1].upper()
    
    return "A"

# Fix the method references by making this a class
class QuestionSolver:
    def __init__(self):
        pass
        
    def _extract_answer_comprehensive(self, response):
        """Extract answer using multiple strategies in order of reliability"""
        
        # Strategy 1: Look for explicit final answer statements
        final_patterns = [
            r'FINAL ANSWER:\s*([A-D])',
            r'Final answer:\s*([A-D])', 
            r'Answer:\s*([A-D])',
            r'The answer is\s*([A-D])',
            r'Therefore,?\s*(?:the answer is\s*)?([A-D])',
            r'So,?\s*(?:the answer is\s*)?([A-D])',
            r'Thus,?\s*(?:the answer is\s*)?([A-D])'
        ]
        
        for pattern in final_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                answer = matches[-1].upper()
                logging.info(f"Found answer using pattern '{pattern}': {answer}")
                return answer
        
        # Strategy 2: Look in the last paragraph for conclusion
        paragraphs = response.split('\n\n')
        if paragraphs:
            last_paragraph = paragraphs[-1]
            conclusion_patterns = [
                r'(?:choose|select|pick)\s*([A-D])',
                r'option\s*([A-D])',
                r'([A-D])\s*is\s*correct',
                r'([A-D])\s*is\s*the\s*answer'
            ]
            
            for pattern in conclusion_patterns:
                matches = re.findall(pattern, last_paragraph, re.IGNORECASE)
                if matches:
                    answer = matches[-1].upper()
                    logging.info(f"Found answer in conclusion using '{pattern}': {answer}")
                    return answer
        
        # Strategy 3: Look for answer at the very end
        end_text = response[-200:].strip()
        end_matches = re.findall(r'\b([A-D])\b', end_text)
        if end_matches:
            answer = end_matches[-1].upper()
            logging.info(f"Using last mentioned option: {answer}")
            return answer
        
        return None
    
    def _extract_quick_answer(self, response):
        """Quick answer extraction for timeout situations"""
        # Just look for the most obvious patterns
        quick_patterns = [
            r'FINAL ANSWER:\s*([A-D])',
            r'Answer:\s*([A-D])',
            r'([A-D])\s*$'  # Letter at very end
        ]
        
        for pattern in quick_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                return match.group(1).upper()
        
        # Last resort - find any option letter
        all_letters = re.findall(r'\b([A-D])\b', response)
        if all_letters:
            return all_letters[-1].upper()
        
        return "A"

solver = QuestionSolver()

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110
    
    try:
        logging.info("Processing academic question")
        
        if time.time() - start_time > timeout:
            return "A"
        
        prompt = f"""You are an expert academic problem solver with deep knowledge across physics, chemistry, astronomy, and biology. 

Solve this multiple choice question using careful step-by-step reasoning:

{input_string}

Instructions:
1. Read the question completely and identify what scientific principles apply
2. Analyze each piece of given information 
3. Work through any necessary calculations systematically
4. Consider each answer option carefully
5. Double-check your reasoning before concluding

Show your work clearly, then end with "FINAL ANSWER: X" where X is A, B, C, or D.
"""
        
        logging.info("Sending question to LLM")
        response = execute_llm(prompt)
        
        if time.time() - start_time > timeout:
            return solver._extract_quick_answer(response)
        
        answer = solver._extract_answer_comprehensive(response)
        
        if answer and answer in ['A', 'B', 'C', 'D']:
            logging.info(f"Successfully extracted answer: {answer}")
            return answer
        
        logging.warning("Could not extract clear answer, using fallback")
        return "A"
        
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        return "A"