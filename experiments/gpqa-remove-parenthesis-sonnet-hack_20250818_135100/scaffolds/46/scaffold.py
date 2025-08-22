import logging
import re
import time
from typing import Optional
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Leave buffer before 120s limit
    
    try:
        logging.info("Processing scientific multiple choice question")
        
        # Step 1: Direct approach - let the LLM solve it
        direct_prompt = f"""You are an expert scientist with comprehensive knowledge across physics, chemistry, biology, astronomy, and all related fields.

Analyze this scientific question carefully and determine the correct answer:

{input_string}

Respond with ONLY the single letter (A, B, C, or D) of the correct answer. No explanation needed.
"""
        
        if time.time() - start_time > timeout:
            return "A"
            
        response = execute_llm(direct_prompt)
        response = response.strip()
        
        logging.info(f"Direct response: '{response}'")
        
        # Check if response is just a single letter
        if len(response) == 1 and response in ['A', 'B', 'C', 'D']:
            return response
        
        # Extract letter from response
        letter_match = re.search(r'\b([A-D])\b', response)
        if letter_match:
            return letter_match.group(1)
        
        if time.time() - start_time > timeout:
            return "A"
            
        # Step 2: More structured approach
        structured_prompt = f"""Question:
{input_string}

Instructions:
- Read the scientific question carefully
- Apply relevant scientific principles and knowledge
- Evaluate each answer choice
- Select the correct answer
- Respond with only the letter A, B, C, or D

Answer:"""
        
        response2 = execute_llm(structured_prompt)
        response2 = response2.strip()
        
        logging.info(f"Structured response: '{response2}'")
        
        if len(response2) == 1 and response2 in ['A', 'B', 'C', 'D']:
            return response2
            
        letter_match2 = re.search(r'\b([A-D])\b', response2)
        if letter_match2:
            return letter_match2.group(1)
            
        if time.time() - start_time > timeout:
            return "A"
            
        # Step 3: Ask for reasoning then conclusion
        reasoning_prompt = f"""{input_string}

Solve this step-by-step by:
1. Identifying the scientific domain and key concepts
2. Analyzing each answer choice
3. Applying relevant scientific principles

End with: "Final answer: [letter]" where [letter] is A, B, C, or D.
"""
        
        response3 = execute_llm(reasoning_prompt)
        logging.info(f"Reasoning response excerpt: {response3[:200]}...")
        
        # Look for explicit answer patterns
        patterns = [
            r'Final answer:\s*([A-D])',
            r'(?:The answer is|Answer is|answer is):?\s*([A-D])',
            r'(?:Therefore|Thus|Hence),?\s*(?:the answer is)?\s*([A-D])',
            r'\b([A-D])\s*(?:is (?:the )?correct|is (?:the )?answer)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response3, re.IGNORECASE)
            if match:
                return match.group(1)
        
        # Look for letter at end of response
        end_match = re.search(r'\b([A-D])\b(?:[^\w]*?)$', response3)
        if end_match:
            return end_match.group(1)
            
        # Find any letter in the response
        any_letter = re.search(r'\b([A-D])\b', response3)
        if any_letter:
            return any_letter.group(1)
        
        logging.warning("Could not extract definitive answer, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return "A"  # Safe fallback