import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    try:
        # Use a system prompt to encourage careful reasoning
        system_prompt = "You are an expert in multiple scientific disciplines. Please read each question carefully, think through the problem step by step, and provide your best answer. Accuracy is paramount."
        
        response = execute_llm(input_string, system_prompt=system_prompt)
        logging.info(f"LLM response: {response}")
        
        # Look for "Answer: X" pattern in the response
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            return answer_match.group(1).upper()
        
        # Look for "Answer: &lt;X&gt;" pattern (HTML encoded)
        answer_match = re.search(r'Answer:\s*&lt;([A-D])&gt;', response, re.IGNORECASE)
        if answer_match:
            return answer_match.group(1).upper()
        
        # Look for "Answer: <X>" pattern
        answer_match = re.search(r'Answer:\s*<([A-D])>', response, re.IGNORECASE)
        if answer_match:
            return answer_match.group(1).upper()
        
        # If no clear answer format found, look for the last letter mentioned
        letters = re.findall(r'\b([A-D])\b', response)
        if letters:
            return letters[-1].upper()
        
        # Default fallback
        logging.warning("Could not extract answer from LLM response")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"