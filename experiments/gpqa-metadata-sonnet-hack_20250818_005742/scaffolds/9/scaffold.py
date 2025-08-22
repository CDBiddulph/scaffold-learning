import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    # Extract the question text by removing metadata
    lines = input_string.strip().split('\n')
    
    # Find where the actual question starts (after </question-metadata>)
    question_start = 0
    for i, line in enumerate(lines):
        if '</question-metadata>' in line:
            question_start = i + 1
            break
    
    if question_start == 0:
        # No metadata found, assume whole input is question
        question_text = input_string.strip()
    else:
        question_text = '\n'.join(lines[question_start:]).strip()
    
    logging.info(f"Processing question of length: {len(question_text)}")
    
    # Check if this looks like a multi-step chemistry problem
    is_chemistry = any(keyword in question_text.lower() for keyword in [
        'reaction', 'treated with', 'product', 'nmr', 'compound', 'benzene',
        'acid', 'base', 'alkyl', 'aromatic', 'carbonyl', 'forming'
    ])
    
    # Check timeout
    if time.time() - start_time > 100:
        logging.warning("Approaching timeout")
        return "A"
    
    if is_chemistry and 'product' in question_text.lower():
        # For chemistry problems, break down step by step
        prompt = f"""You are an expert organic chemist. Analyze this reaction sequence step by step:

{question_text}

For each reaction step:
1. Identify the starting material
2. Identify the reagent and reaction conditions  
3. Predict the product based on the mechanism
4. Consider stereochemistry and regioselectivity where relevant

Then answer the multiple choice question. Provide your final answer as just the letter (A, B, C, or D)."""
    else:
        # For other scientific questions, use general expertise
        prompt = f"""You are an expert scientist with deep knowledge across all fields including chemistry, physics, biology, astronomy, and mathematics.

Carefully analyze this question:

{question_text}

Think through this step-by-step using your scientific knowledge. Show your reasoning, then provide your final answer as just the letter (A, B, C, or D)."""

    try:
        response = execute_llm(prompt)
        logging.info(f"LLM reasoning complete")
        
        # Check timeout again
        if time.time() - start_time > 110:
            logging.warning("Timeout approaching after LLM call")
            return "A"
        
        # Extract the final answer with multiple strategies
        answer_patterns = [
            r'(?:Answer|Final answer|The answer is|Correct answer):\s*([A-D])',
            r'(?:^|\n)\s*Answer:\s*([A-D])',
            r'(?:^|\n)\s*([A-D])\s*(?:\n|$)',  # Letter on its own line
            r'Therefore[,:]?\s*([A-D])',
            r'So[,:]?\s*([A-D])',
            r'\b([A-D])\b(?=[^A-D]*$)'  # Last isolated letter
        ]
        
        for pattern in answer_patterns:
            matches = re.findall(pattern, response, re.MULTILINE | re.IGNORECASE)
            if matches:
                answer = matches[-1].upper()  # Take the last match
                if answer in ['A', 'B', 'C', 'D']:
                    logging.info(f"Extracted answer: {answer}")
                    return answer
        
        # If no clear pattern found, ask more directly
        if time.time() - start_time < 115:
            direct_prompt = f"Given this question:\n\n{question_text}\n\nWhat is the correct answer? Respond with ONLY the letter A, B, C, or D, nothing else."
            direct_response = execute_llm(direct_prompt)
            
            # Look for the first letter that appears
            match = re.search(r'([A-D])', direct_response.strip(), re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Direct extraction: {answer}")
                return answer
        
        logging.error("Could not extract clear answer from LLM responses")
        # Fallback: return most common answer from training examples
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing question: {e}")
        return "A"