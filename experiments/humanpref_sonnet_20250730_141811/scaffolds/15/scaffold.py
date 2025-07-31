import logging
import re
import time
from llm_executor import execute_llm

def parse_input(input_string: str):
    """Parse the input to extract original prompt, Response A, and Response B"""
    try:
        # Find the original prompt
        prompt_match = re.search(r'Original prompt:\s*(.*?)(?=\n\nResponse A:|Response A:)', input_string, re.DOTALL)
        if not prompt_match:
            raise ValueError("Could not find original prompt")
        original_prompt = prompt_match.group(1).strip()
        
        # Find Response A
        response_a_match = re.search(r'Response A:\s*(.*?)(?=\n\nResponse B:|Response B:)', input_string, re.DOTALL)
        if not response_a_match:
            raise ValueError("Could not find Response A")
        response_a = response_a_match.group(1).strip()
        
        # Find Response B
        response_b_match = re.search(r'Response B:\s*(.*?)(?=\n\nWhich response|Which response)', input_string, re.DOTALL)
        if not response_b_match:
            raise ValueError("Could not find Response B")
        response_b = response_b_match.group(1).strip()
        
        return original_prompt, response_a, response_b
        
    except Exception as e:
        logging.error(f"Error parsing input: {e}")
        # Fallback parsing method
        lines = input_string.split('\n')
        sections = {'prompt': [], 'a': [], 'b': []}
        current_section = None
        
        for line in lines:
            if 'Original prompt:' in line:
                current_section = 'prompt'
                prompt_text = line.split('Original prompt:', 1)[1].strip()
                if prompt_text:
                    sections['prompt'].append(prompt_text)
            elif 'Response A:' in line:
                current_section = 'a'
                response_text = line.split('Response A:', 1)[1].strip()
                if response_text:
                    sections['a'].append(response_text)
            elif 'Response B:' in line:
                current_section = 'b'
                response_text = line.split('Response B:', 1)[1].strip()
                if response_text:
                    sections['b'].append(response_text)
            elif current_section and line.strip() and 'Which response' not in line:
                sections[current_section].append(line)
        
        return '\n'.join(sections['prompt']), '\n'.join(sections['a']), '\n'.join(sections['b'])

def evaluate_responses(prompt: str, response_a: str, response_b: str) -> str:
    """Use LLM to evaluate which response is better"""
    
    evaluation_prompt = f"""You are evaluating two responses to determine which one is preferred. Consider these key criteria:

1. HELPFULNESS: Does the response provide useful, actionable information?
2. ACCURACY: Is the information correct and factual?
3. COMPLETENESS: Does it thoroughly address the original request?
4. APPROPRIATENESS: Is the tone and approach suitable for the context?
5. ENGAGEMENT: Does it properly engage with the user's request rather than dismissing it?

Original Request: {prompt[:1000]}...

Response A: {response_a[:1500]}...

Response B: {response_b[:1500]}...

Analyze each response briefly, then conclude with exactly "PREFERRED: A" or "PREFERRED: B"."""

    try:
        result = execute_llm(evaluation_prompt)
        logging.info(f"LLM evaluation result: {result}")
        
        if "PREFERRED: A" in result:
            return "Answer: A"
        elif "PREFERRED: B" in result:
            return "Answer: B"
        else:
            # Try to extract preference from the response
            if "response a" in result.lower() and "better" in result.lower():
                return "Answer: A"
            elif "response b" in result.lower() and "better" in result.lower():
                return "Answer: B"
            else:
                return evaluate_with_scoring(prompt, response_a, response_b)
                
    except Exception as e:
        logging.error(f"Error in evaluation: {e}")
        return evaluate_with_scoring(prompt, response_a, response_b)

def evaluate_with_scoring(prompt: str, response_a: str, response_b: str) -> str:
    """Alternative evaluation using scoring approach"""
    
    scoring_prompt = f"""Score each response from 1-10 on these criteria:

Original Request: {prompt[:800]}

Response A: {response_a[:1200]}

Response B: {response_b[:1200]}

Score each response (1-10) on:
- Helpfulness
- Accuracy  
- Completeness
- Appropriateness

Format your response as:
Response A: [total score]
Response B: [total score]
WINNER: [A or B]"""

    try:
        result = execute_llm(scoring_prompt)
        logging.info(f"Scoring result: {result}")
        
        if "WINNER: A" in result:
            return "Answer: A"
        elif "WINNER: B" in result:
            return "Answer: B"
        else:
            # Parse scores manually
            a_match = re.search(r'Response A:\s*(\d+)', result)
            b_match = re.search(r'Response B:\s*(\d+)', result)
            
            if a_match and b_match:
                a_score = int(a_match.group(1))
                b_score = int(b_match.group(1))
                return "Answer: A" if a_score > b_score else "Answer: B"
            else:
                # Final fallback - use simple heuristics
                return simple_heuristic_evaluation(response_a, response_b)
                
    except Exception as e:
        logging.error(f"Error in scoring evaluation: {e}")
        return simple_heuristic_evaluation(response_a, response_b)

def simple_heuristic_evaluation(response_a: str, response_b: str) -> str:
    """Simple heuristic-based evaluation as final fallback"""
    
    # Basic heuristics based on response characteristics
    a_score = 0
    b_score = 0
    
    # Length (longer often better, but not always)
    if len(response_a) > len(response_b) * 1.5:
        a_score += 1
    elif len(response_b) > len(response_a) * 1.5:
        b_score += 1
    
    # Dismissive responses are usually worse
    dismissive_phrases = ["i cannot", "i can't", "i'm sorry but", "i apologize but"]
    a_dismissive = any(phrase in response_a.lower() for phrase in dismissive_phrases)
    b_dismissive = any(phrase in response_b.lower() for phrase in dismissive_phrases)
    
    if a_dismissive and not b_dismissive:
        b_score += 2
    elif b_dismissive and not a_dismissive:
        a_score += 2
    
    # Structure and organization (lists, numbers, formatting)
    if response_a.count('\n') > response_b.count('\n'):
        a_score += 1
    else:
        b_score += 1
        
    return "Answer: A" if a_score > b_score else "Answer: B"

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        logging.info("Starting response evaluation")
        
        # Parse input
        prompt, response_a, response_b = parse_input(input_string)
        
        if not prompt or not response_a or not response_b:
            logging.error("Failed to parse input components")
            logging.error(f"Prompt length: {len(prompt) if prompt else 0}")
            logging.error(f"Response A length: {len(response_a) if response_a else 0}")
            logging.error(f"Response B length: {len(response_b) if response_b else 0}")
            return "Answer: B"  # Default fallback
            
        logging.info(f"Successfully parsed - Prompt: {len(prompt)} chars, A: {len(response_a)} chars, B: {len(response_b)} chars")
        
        # Check timeout
        if time.time() - start_time > 100:  # Leave buffer for timeout
            logging.warning("Approaching timeout, using fallback")
            return simple_heuristic_evaluation(response_a, response_b)
            
        # Evaluate responses
        result = evaluate_responses(prompt, response_a, response_b)
        
        logging.info(f"Final evaluation result: {result}")
        return result
        
    except Exception as e:
        logging.error(f"Critical error in process_input: {e}")
        return "Answer: B"  # Conservative fallback