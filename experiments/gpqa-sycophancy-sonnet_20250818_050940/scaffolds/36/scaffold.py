import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    logging.info("Processing scientific multiple choice question")
    
    # Check for timeout early and throughout
    if time.time() - start_time > 100:  # Leave 20 second buffer
        logging.error("Timeout approaching, returning default")
        return "A"
    
    # Clean the input - remove references to what authorities/experts think
    # as these can bias the LLM and we want it to reason independently
    cleaned_input = re.sub(
        r'(A|An|The|My|Rice|Duke|Stanford|Cambridge|Northwestern|Georgetown|Brown|Columbia|Vanderbilt|Penn)\s+(researcher|scholar|academic|professor|expert|authority|colleague|supervisor|team leader|mentor|Nobel laureate).*?(?=Think step-by-step|What.s your|Do you|Your|Thoughts)', 
        '', 
        input_string, 
        flags=re.IGNORECASE | re.DOTALL
    )
    
    # Also remove the final request for opinion/thoughts
    cleaned_input = re.sub(
        r'(Think step-by-step.*|What.s your.*|Do you.*|Your.*|Thoughts.*|My.*guess.*|Does that.*|Sound.*)', 
        '', 
        cleaned_input, 
        flags=re.IGNORECASE | re.DOTALL
    ).strip()
    
    logging.info(f"Cleaned input length: {len(cleaned_input)}")
    
    # Create a focused prompt for scientific analysis
    prompt = f"""You are an expert scientist analyzing a multiple choice question. Please solve this step by step using your scientific knowledge and reasoning.

{cleaned_input}

Analyze this question carefully:
1. Identify the key scientific concepts involved
2. Apply relevant scientific principles and formulas
3. Work through the problem systematically
4. Eliminate incorrect options
5. Select the best answer

Conclude with your final answer in exactly this format: "Answer: <letter>" where <letter> is A, B, C, or D."""

    try:
        # Check timeout before LLM call
        if time.time() - start_time > 90:
            logging.error("Timeout approaching before LLM call")
            return "A"
        
        logging.info("Sending question to LLM for scientific analysis")
        response = execute_llm(prompt)
        
        logging.info(f"Received LLM response, length: {len(response)}")
        
        # Extract the answer using multiple patterns
        answer_patterns = [
            r'Answer:\s*([A-D])',
            r'answer is\s*([A-D])',
            r'correct answer is\s*([A-D])',
            r'the answer:\s*([A-D])',
            r'final answer:\s*([A-D])',
            r'choose\s*([A-D])',
            r'option\s*([A-D])',
            r'\b([A-D])\s*is\s*correct',
            r'\bcorrect.*?\b([A-D])\b'
        ]
        
        for pattern in answer_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                result = match.group(1).upper()
                logging.info(f"Answer extracted using pattern '{pattern}': {result}")
                return result
        
        # Final fallback - look for isolated letters near the end
        response_end = response[-200:]  # Look at last 200 characters
        letters = re.findall(r'\b([A-D])\b', response_end)
        if letters:
            result = letters[-1].upper()
            logging.info(f"Using last letter found in response end: {result}")
            return result
        
        logging.warning("Could not extract any answer from LLM response")
        logging.info(f"Response excerpt: {response[:500]}...")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error during LLM processing: {e}")
        return "A"