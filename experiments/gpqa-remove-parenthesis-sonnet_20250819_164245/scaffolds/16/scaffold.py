import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 115  # seconds, leaving buffer for safety
    
    try:
        question_text = input_string.strip()
        
        # Early timeout check
        if time.time() - start_time > timeout:
            return "A"
            
        logging.info("Processing scientific multiple choice question")
        
        # Create a comprehensive prompt that asks for step-by-step reasoning
        prompt = f"""You are an expert scientist with deep knowledge across multiple disciplines including biology, chemistry, physics, astronomy, mathematics, and engineering.

Please solve this multiple choice question step by step:

{question_text}

Instructions:
1. Read the question carefully and identify the key scientific concepts
2. Think through the problem systematically using your scientific knowledge
3. Consider each answer choice and evaluate why it might be correct or incorrect
4. Show your reasoning clearly
5. Conclude with your final answer

Please end your response with "Final Answer: X" where X is A, B, C, or D."""

        logging.info("Querying LLM for scientific analysis")
        response = execute_llm(prompt)
        
        # Check timeout again
        if time.time() - start_time > timeout:
            return "A"
            
        logging.info(f"Received response of length {len(response)}")
        
        # Extract the final answer using multiple strategies
        
        # Strategy 1: Look for "Final Answer: X" 
        final_match = re.search(r'Final Answer:\s*([A-D])', response, re.IGNORECASE)
        if final_match:
            result = final_match.group(1).upper()
            logging.info(f"Found final answer: {result}")
            return result
            
        # Strategy 2: Look for "Answer: X"
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            result = answer_match.group(1).upper()
            logging.info(f"Found answer: {result}")
            return result
            
        # Strategy 3: Common conclusion phrases
        conclusion_patterns = [
            r'the correct answer is\s*\(?([A-D])\)?',
            r'the answer is\s*\(?([A-D])\)?',
            r'correct option is\s*\(?([A-D])\)?',
            r'therefore,?\s*\(?([A-D])\)?',
            r'thus,?\s*\(?([A-D])\)?',
            r'so the answer is\s*\(?([A-D])\)?',
            r'answer\s*=\s*([A-D])',
            r'option\s*\(?([A-D])\)?\s*is correct',
            r'choice\s*\(?([A-D])\)?\s*is correct',
            r'select\s*\(?([A-D])\)?',
            r'choose\s*\(?([A-D])\)?',
        ]
        
        for pattern in conclusion_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                result = match.group(1).upper()
                logging.info(f"Found answer via pattern: {result}")
                return result
        
        # Strategy 4: Look in the last few sentences
        sentences = re.split(r'[.!?\n]+', response.strip())
        for sentence in reversed(sentences[-5:]):  # Check last 5 sentences
            if sentence.strip():
                # Look for isolated letters that might be the answer
                letters = re.findall(r'\b([A-D])\b', sentence)
                if letters:
                    result = letters[-1].upper()
                    logging.info(f"Found answer in final sentences: {result}")
                    return result
        
        # Strategy 5: Find all A-D mentions and take the last one
        all_matches = re.findall(r'\b([A-D])\b', response)
        if all_matches:
            result = all_matches[-1].upper()
            logging.info(f"Using last letter mentioned: {result}")
            return result
            
        # Default fallback
        logging.warning("Could not extract clear answer, using fallback")
        logging.warning(f"Response excerpt: {response[:500]}...")
        return "A"
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return "A"