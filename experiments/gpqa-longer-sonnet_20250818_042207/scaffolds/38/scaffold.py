import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Check time limit early
        if time.time() - start_time > 110:
            logging.warning("Approaching time limit, returning default answer")
            return "A"
            
        # Create a comprehensive prompt with clear instructions
        system_prompt = """You are a world-class scientific expert with deep knowledge across all scientific disciplines including chemistry, physics, biology, astronomy, mathematics, and engineering. You excel at analyzing complex scientific problems and reasoning through multiple choice questions."""
        
        prompt = f"""Please analyze this multiple choice scientific question carefully:

{input_string}

Instructions:
1. Read the question thoroughly and understand what is being asked
2. Consider each answer choice systematically
3. Apply relevant scientific principles, formulas, and knowledge
4. Think through the problem step by step with clear reasoning
5. Choose the best answer based on your scientific analysis

You must end your response with exactly this format: "Answer: X" where X is A, B, C, or D."""

        # Get response from LLM
        logging.info("Sending question to LLM for analysis")
        response = execute_llm(prompt, system_prompt)
        logging.info(f"LLM response received, length: {len(response)} characters")
        
        # Primary extraction method - look for the exact format requested
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Successfully extracted answer: {answer}")
            return answer
        
        # Secondary extraction methods if primary fails
        logging.info("Primary extraction failed, trying alternative patterns")
        
        alternative_patterns = [
            r'the answer is\s*([A-D])',
            r'answer is\s*([A-D])',
            r'I choose\s*([A-D])',
            r'option\s*([A-D])\s*is\s*correct',
            r'option\s*([A-D])\s*is\s*the\s*answer',
            r'correct answer is\s*([A-D])',
            r'\b([A-D])\s*is\s*correct',
            r'\b([A-D])\s*is\s*the\s*correct\s*answer'
        ]
        
        for pattern in alternative_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Found answer using pattern '{pattern}': {answer}")
                return answer
        
        # Analyze the conclusion of the response for the most likely answer
        conclusion = response[-300:]  # Look at last 300 characters
        conclusion_options = re.findall(r'\b([A-D])\b', conclusion)
        if conclusion_options:
            answer = conclusion_options[-1].upper()
            logging.info(f"Using last mentioned option in conclusion: {answer}")
            return answer
        
        # Final fallback - find most frequently mentioned option
        all_options = re.findall(r'\b([A-D])\b', response)
        if all_options:
            from collections import Counter
            most_common = Counter(all_options).most_common(1)[0][0]
            answer = most_common.upper()
            logging.info(f"Using most frequently mentioned option: {answer}")
            return answer
        
        # Ultimate fallback
        logging.warning("Could not extract any clear answer, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {str(e)}")
        logging.error(f"Input was: {input_string[:200]}...")  # Log first 200 chars for debugging
        return "A"  # Safe default