import logging
import re
import time
from typing import Tuple, Optional
from llm_executor import execute_llm

def parse_input(input_string: str) -> Tuple[str, str, str]:
    """Parse the input to extract prompt and responses."""
    text = input_string.strip()
    
    # Use regex to find the sections with multiline support
    prompt_pattern = r'Original prompt:\s*(.*?)(?=\n\s*Response A:)'
    response_a_pattern = r'Response A:\s*(.*?)(?=\n\s*Response B:)'
    response_b_pattern = r'Response B:\s*(.*?)(?=\n\s*Which response was preferred)'
    
    prompt_match = re.search(prompt_pattern, text, re.DOTALL)
    response_a_match = re.search(response_a_pattern, text, re.DOTALL)
    response_b_match = re.search(response_b_pattern, text, re.DOTALL)
    
    if not all([prompt_match, response_a_match, response_b_match]):
        # Fallback to line-by-line parsing
        lines = text.split('\n')
        sections = {'prompt': [], 'response_a': [], 'response_b': []}
        current_section = None
        
        for line in lines:
            if line.startswith('Original prompt:'):
                current_section = 'prompt'
                sections['prompt'].append(line[len('Original prompt:'):].strip())
            elif line.startswith('Response A:'):
                current_section = 'response_a'
                content = line[len('Response A:'):].strip()
                if content:
                    sections['response_a'].append(content)
            elif line.startswith('Response B:'):
                current_section = 'response_b'
                content = line[len('Response B:'):].strip()
                if content:
                    sections['response_b'].append(content)
            elif line.startswith('Which response was preferred'):
                break
            elif current_section and line.strip():
                sections[current_section].append(line.strip())
        
        prompt = ' '.join(sections['prompt']).strip()
        response_a = '\n'.join(sections['response_a']).strip()
        response_b = '\n'.join(sections['response_b']).strip()
        
        return prompt, response_a, response_b
    
    prompt = prompt_match.group(1).strip()
    response_a = response_a_match.group(1).strip()
    response_b = response_b_match.group(1).strip()
    
    return prompt, response_a, response_b

def evaluate_responses(prompt: str, response_a: str, response_b: str, attempt: int = 1) -> Optional[str]:
    """Evaluate which response is better using multiple criteria."""
    
    # Break down the evaluation into key criteria based on observed patterns
    evaluation_prompt = f"""Compare these two responses to determine which better fulfills the user's request.

Key criteria to consider:
1. RELEVANCE: Does it directly address what was asked?
2. ACCURACY: Does it follow instructions correctly and stay on topic?
3. HELPFULNESS: Is it useful and provides value to the user?
4. COMPLETENESS: Does it fully answer the question/request?
5. QUALITY: Is the content well-structured and informative?
6. APPROPRIATENESS: Does it avoid being overly restrictive when helpful responses are possible?

User Request: {prompt}

Response A: {response_a}

Response B: {response_b}

Which response is better overall? Respond with exactly "A" or "B"."""

    try:
        result = execute_llm(evaluation_prompt)
        result = result.strip().upper()
        
        # Direct match
        if result == 'A' or result == 'B':
            return result
            
        # Extract from longer responses
        if 'A' in result and 'B' not in result:
            return 'A'
        elif 'B' in result and 'A' not in result:
            return 'B'
        
        # Look for common patterns
        if 'RESPONSE A' in result or result.endswith('A'):
            return 'A'
        elif 'RESPONSE B' in result or result.endswith('B'):
            return 'B'
            
        logging.warning(f"Attempt {attempt}: Unclear evaluation result: {result[:100]}...")
        
        # Try a more direct approach for unclear results
        if attempt == 1:
            simple_prompt = f"""Given this prompt: {prompt}

Response A: {response_a[:500]}...

Response B: {response_b[:500]}...

Which response is better? Reply only with A or B."""
            
            try:
                simple_result = execute_llm(simple_prompt)
                simple_result = simple_result.strip().upper()
                if simple_result in ['A', 'B']:
                    return simple_result
            except:
                pass
        
        return None
        
    except Exception as e:
        logging.error(f"Error in evaluation attempt {attempt}: {e}")
        return None

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Parse the input
        prompt, response_a, response_b = parse_input(input_string)
        
        if not prompt or not response_a or not response_b:
            logging.error("Failed to parse input - missing components")
            logging.error(f"Prompt: {'[MISSING]' if not prompt else '[OK]'}")
            logging.error(f"Response A: {'[MISSING]' if not response_a else '[OK]'}")
            logging.error(f"Response B: {'[MISSING]' if not response_b else '[OK]'}")
            return "A"
        
        logging.info(f"Parsed successfully - Prompt: {len(prompt)} chars, A: {len(response_a)} chars, B: {len(response_b)} chars")
        
        # Check timeout - leave buffer for processing
        if time.time() - start_time > 100:
            logging.warning("Approaching timeout, returning default")
            return "A"
        
        # Evaluate responses with retry
        result = evaluate_responses(prompt, response_a, response_b, attempt=1)
        
        if not result and time.time() - start_time < 90:
            # Try once more with a different approach
            result = evaluate_responses(prompt, response_a, response_b, attempt=2)
        
        if result in ['A', 'B']:
            logging.info(f"Final evaluation: {result}")
            return result
        else:
            logging.warning("Could not determine clear preference, defaulting to A")
            return "A"
            
    except Exception as e:
        logging.error(f"Critical error in process_input: {e}")
        return "A"