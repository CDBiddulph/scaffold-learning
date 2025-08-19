import logging
import re
import html
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    try:
        # The input already contains the full question and format instruction
        # Pass it directly to the LLM for reasoning
        response = execute_llm(input_string.strip())
        
        logging.info(f"LLM Response: {response[:200]}...")  # Log first 200 chars
        
        # Decode HTML entities in case they're present
        decoded_response = html.unescape(response)
        
        # Try multiple patterns to extract the answer letter
        
        # Look for "Answer: <letter>" pattern (most common expected format)
        answer_match = re.search(r'Answer:\s*([ABCD])', decoded_response, re.IGNORECASE)
        if answer_match:
            return answer_match.group(1).upper()
            
        # Look for HTML encoded format &lt;letter&gt;
        html_match = re.search(r'&lt;([ABCD])&gt;', response, re.IGNORECASE) 
        if html_match:
            return html_match.group(1).upper()
        
        # Look for angle brackets after HTML decoding <letter>
        angle_match = re.search(r'<([ABCD])>', decoded_response, re.IGNORECASE)
        if angle_match:
            return angle_match.group(1).upper()
        
        # Look for final answer pattern at the end
        final_answer_match = re.search(r'(?:final answer|answer).*?([ABCD])(?:[^A-Za-z]|$)', decoded_response, re.IGNORECASE)
        if final_answer_match:
            return final_answer_match.group(1).upper()
        
        # Look for letter at the very end of response
        final_letter_match = re.search(r'\b([ABCD])\b(?=[^A-Za-z]*$)', decoded_response)
        if final_letter_match:
            return final_letter_match.group(1).upper()
        
        # Look for any clear answer indication
        general_match = re.search(r'(?:choice|option|select).*?([ABCD])', decoded_response, re.IGNORECASE)
        if general_match:
            return general_match.group(1).upper()
        
        # Last resort: find any A, B, C, or D in the response and take the last one
        letters = re.findall(r'\b([ABCD])\b', decoded_response)
        if letters:
            return letters[-1].upper()
        
        logging.warning(f"Could not extract clear answer from response. Defaulting to A.")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error processing input: {str(e)}")
        return "A"  # Default fallback when everything fails