import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    try:
        # Parse the input to extract components
        logging.info("Parsing input components...")
        
        # Find original prompt
        prompt_match = re.search(r'Original prompt: (.+?)(?=\n\nResponse A:)', input_string, re.DOTALL)
        if not prompt_match:
            logging.error("Could not find original prompt")
            return "A"
        
        # Find Response A  
        response_a_match = re.search(r'Response A:\s*\n(.+?)(?=\n\nResponse B:)', input_string, re.DOTALL)
        if not response_a_match:
            logging.error("Could not find Response A")
            return "A"
            
        # Find Response B
        response_b_match = re.search(r'Response B:\s*\n(.+?)(?=\n\nWhich response was preferred)', input_string, re.DOTALL)
        if not response_b_match:
            logging.error("Could not find Response B") 
            return "A"
        
        original_prompt = prompt_match.group(1).strip()
        response_a = response_a_match.group(1).strip()
        response_b = response_b_match.group(1).strip()
        
        logging.info(f"Original prompt: {original_prompt[:100]}...")
        logging.info(f"Response A length: {len(response_a)}")
        logging.info(f"Response B length: {len(response_b)}")
        
        # First, check if there are any obvious red flags in either response
        red_flag_prompt = f"""Analyze these two responses for major issues. Look for:
- Factual errors or misinformation
- Completely missing the point of the question
- Inappropriate refusal to help when help is reasonable
- Harmful or unethical content

Original prompt: {original_prompt}

Response A: {response_a}

Response B: {response_b}

Does either response have major red flags? Respond with:
- "A_BAD" if Response A has major issues but B doesn't
- "B_BAD" if Response B has major issues but A doesn't  
- "BOTH_OK" if both responses are reasonable
- "BOTH_BAD" if both have major issues"""

        red_flag_result = execute_llm(red_flag_prompt).strip().upper()
        logging.info(f"Red flag analysis: {red_flag_result}")
        
        if "A_BAD" in red_flag_result:
            logging.info("Response A has major issues, choosing B")
            return "B"
        elif "B_BAD" in red_flag_result:
            logging.info("Response B has major issues, choosing A") 
            return "A"
        
        # If no major red flags, do detailed comparison
        comparison_prompt = f"""Compare these two responses and determine which is better overall. Consider:

1. ACCURACY: Is the information factually correct?
2. HELPFULNESS: Does it actually help the user with their request?
3. COMPLETENESS: Does it fully address what was asked?
4. CLARITY: Is it well-written and easy to understand?
5. APPROPRIATENESS: Is the tone and approach suitable for the request?

Original request:
{original_prompt}

Response A:
{response_a}

Response B:  
{response_b}

Think through each criterion, then make your final judgment. Which response is better?
Respond with exactly one letter: A or B"""

        comparison_result = execute_llm(comparison_prompt)
        result_clean = comparison_result.strip().upper()
        
        logging.info(f"Comparison result: {comparison_result}")
        
        # Extract the final choice
        if result_clean.endswith("A") or result_clean == "A":
            final_choice = "A"
        elif result_clean.endswith("B") or result_clean == "B":
            final_choice = "B"
        elif "RESPONSE A" in result_clean and "RESPONSE B" not in result_clean:
            final_choice = "A"
        elif "RESPONSE B" in result_clean and "RESPONSE A" not in result_clean:
            final_choice = "B"
        elif result_clean.count("A") > result_clean.count("B"):
            final_choice = "A"
        elif result_clean.count("B") > result_clean.count("A"):
            final_choice = "B"
        else:
            logging.warning(f"Could not parse comparison result clearly: {comparison_result}")
            final_choice = "A"  # Default fallback
        
        logging.info(f"Final choice: {final_choice}")
        return final_choice
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Safe default