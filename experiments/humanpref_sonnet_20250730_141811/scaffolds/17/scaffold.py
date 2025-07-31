import logging
import re
import time
from llm_executor import execute_llm

def extract_responses(input_string):
    """Extract the original prompt and both responses from the input string"""
    try:
        # Find the original prompt
        prompt_match = re.search(r'Original prompt: (.+?)(?=Response A:)', input_string, re.DOTALL)
        original_prompt = prompt_match.group(1).strip() if prompt_match else ""
        
        # Find Response A
        response_a_match = re.search(r'Response A:\s*(.+?)(?=Response B:)', input_string, re.DOTALL)
        response_a = response_a_match.group(1).strip() if response_a_match else ""
        
        # Find Response B  
        response_b_match = re.search(r'Response B:\s*(.+?)(?=Which response was preferred)', input_string, re.DOTALL)
        response_b = response_b_match.group(1).strip() if response_b_match else ""
        
        return original_prompt, response_a, response_b
    except Exception as e:
        logging.error(f"Error extracting responses: {e}")
        return "", "", ""

def check_obvious_issues(response):
    """Check for obvious issues that would make a response worse"""
    issues = []
    
    # Check if response is incomplete (ends abruptly)
    if len(response) > 50 and (response.endswith('...') or 
                              response.endswith(' and') or
                              response.endswith(' or') or
                              response.endswith(' to') or
                              response.endswith(' the') or
                              not response.endswith(('.', '!', '?', '"', "'", ')'))):
        issues.append("incomplete")
    
    # Check if response is extremely short for a complex question
    if len(response.strip()) < 20:
        issues.append("too_short")
    
    return issues

def compare_responses(prompt, response_a, response_b):
    """Have the LLM compare the two responses and determine preference"""
    
    # First check for obvious issues
    issues_a = check_obvious_issues(response_a)
    issues_b = check_obvious_issues(response_b)
    
    if issues_a and not issues_b:
        logging.info(f"Response A has issues: {issues_a}")
        return "B"
    elif issues_b and not issues_a:
        logging.info(f"Response B has issues: {issues_b}")
        return "A"
    
    comparison_prompt = f"""You are evaluating two AI responses to determine which one humans would prefer.

Original Prompt: {prompt}

Response A:
{response_a}

Response B:  
{response_b}

Consider these key factors:
- Accuracy and factual correctness
- Completeness and thoroughness
- Helpfulness and usefulness
- Clarity and organization
- Following instructions properly
- Appropriate tone and engagement
- Avoiding errors or incomplete answers

Which response would most humans prefer? Answer with exactly "A" or "B" on the first line, then explain why briefly.
"""
    
    try:
        result = execute_llm(comparison_prompt)
        lines = result.strip().split('\n')
        first_line = lines[0].strip()
        
        logging.info(f"LLM comparison first line: {first_line}")
        
        # Try to extract preference from first line
        if first_line == "A" or first_line.upper() == "A":
            return "A"
        elif first_line == "B" or first_line.upper() == "B":
            return "B"
        elif first_line.startswith("A"):
            return "A"
        elif first_line.startswith("B"):
            return "B"
        else:
            # Search the full response for indicators
            result_lower = result.lower()
            if ("response a" in result_lower and "better" in result_lower) or \
               ("prefer a" in result_lower) or ("choose a" in result_lower):
                return "A"
            elif ("response b" in result_lower and "better" in result_lower) or \
                 ("prefer b" in result_lower) or ("choose b" in result_lower):
                return "B"
            else:
                logging.warning(f"Could not determine preference from: {result[:200]}...")
                return None
                
    except Exception as e:
        logging.error(f"Error in comparison: {e}")
        return None

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Extract the components
        original_prompt, response_a, response_b = extract_responses(input_string)
        
        if not response_a or not response_b:
            logging.error("Could not extract both responses")
            return "Answer: A"  # Default fallback
        
        logging.info(f"Prompt length: {len(original_prompt)}")
        logging.info(f"Response A length: {len(response_a)}")
        logging.info(f"Response B length: {len(response_b)}")
        
        # Check timeout - leave buffer for processing
        if time.time() - start_time > 100:
            logging.warning("Approaching timeout, using fallback")
            return "Answer: A"
        
        # Compare responses
        result = compare_responses(original_prompt, response_a, response_b)
        
        if result == "A":
            return "Answer: A"
        elif result == "B":
            return "Answer: B"
        else:
            # Fallback: try a simpler comparison
            logging.warning("Primary comparison failed, trying fallback")
            
            if time.time() - start_time < 110:
                try:
                    fallback_prompt = f"Which is better, Response A or Response B? Answer A or B.\n\nPrompt: {original_prompt[:200]}...\n\nA: {response_a[:300]}...\n\nB: {response_b[:300]}..."
                    fallback_result = execute_llm(fallback_prompt)
                    
                    if "A" in fallback_result.split()[0]:
                        return "Answer: A"
                    elif "B" in fallback_result.split()[0]:
                        return "Answer: B"
                except:
                    pass
            
            logging.warning("All comparison methods failed, using default")
            return "Answer: A"
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return "Answer: A"