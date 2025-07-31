import logging
from llm_executor import execute_llm

def parse_input(input_string):
    """Parse the input to extract original prompt, Response A, and Response B"""
    lines = input_string.strip().split('\n')
    
    # Find the original prompt
    prompt_start = None
    for i, line in enumerate(lines):
        if line.startswith("Original prompt:"):
            prompt_start = i
            break
    
    if prompt_start is None:
        raise ValueError("Could not find 'Original prompt:' in input")
    
    # Find Response A and B markers
    response_a_start = None
    response_b_start = None
    
    for i, line in enumerate(lines):
        if line.strip() == "Response A:":
            response_a_start = i + 1
        elif line.strip() == "Response B:":
            response_b_start = i + 1
    
    if response_a_start is None or response_b_start is None:
        raise ValueError("Could not find Response A and B markers")
    
    # Extract original prompt (may span multiple lines)
    prompt_lines = []
    for i in range(prompt_start, response_a_start - 1):
        line = lines[i]
        if i == prompt_start:
            # Remove "Original prompt:" prefix
            prompt_lines.append(line[len("Original prompt:"):].strip())
        else:
            prompt_lines.append(line)
    original_prompt = '\n'.join(prompt_lines).strip()
    
    # Extract Response A
    response_a_lines = []
    for i in range(response_a_start, response_b_start - 1):
        if i < len(lines):
            response_a_lines.append(lines[i])
    response_a = '\n'.join(response_a_lines).strip()
    
    # Extract Response B
    response_b_lines = []
    for i in range(response_b_start, len(lines)):
        line = lines[i]
        if line.startswith("Which response was preferred?"):
            break
        response_b_lines.append(line)
    response_b = '\n'.join(response_b_lines).strip()
    
    return original_prompt, response_a, response_b

def evaluate_responses(original_prompt, response_a, response_b):
    """Use the LLM to evaluate which response is better"""
    
    # First, let the LLM understand what the original prompt is asking for
    understanding_prompt = f"""What is this prompt asking for? Summarize the key requirements in one sentence.

Prompt: {original_prompt}"""
    
    requirements = execute_llm(understanding_prompt).strip()
    logging.info(f"Understood requirements: {requirements}")
    
    # Now evaluate both responses
    evaluation_prompt = f"""You are evaluating two responses to determine which one is better. The key factors to consider are:

1. **Accuracy**: Is the information correct and factually accurate?
2. **Instruction Following**: Does it do exactly what was asked?
3. **Completeness**: Does it fully address the question?
4. **Helpfulness**: Is it useful and practical for the user?
5. **Clarity**: Is it well-organized and easy to understand?

Original prompt: {original_prompt}

Key requirement: {requirements}

Response A:
{response_a}

Response B:
{response_b}

Evaluate each response carefully. Which one better fulfills the requirements while being accurate, complete, and helpful?

Answer with exactly one letter: A or B"""

    try:
        result = execute_llm(evaluation_prompt)
        result = result.strip().upper()
        
        # Extract A or B from the response
        if result.endswith('A'):
            return 'A'
        elif result.endswith('B'):
            return 'B'
        elif 'A' in result and 'B' not in result:
            return 'A'
        elif 'B' in result and 'A' not in result:
            return 'B'
        else:
            # If unclear, do a simpler direct comparison
            logging.warning(f"Unclear evaluation result: {result}")
            simple_prompt = f"""Which response is better for this prompt?

Prompt: {original_prompt}

Response A: {response_a}

Response B: {response_b}

Answer: A or B"""
            
            simple_result = execute_llm(simple_prompt).strip().upper()
            if 'A' in simple_result and 'B' not in simple_result:
                return 'A'
            else:
                return 'B'
            
    except Exception as e:
        logging.error(f"Error in LLM evaluation: {e}")
        return 'B'  # Default fallback

def process_input(input_string: str) -> str:
    try:
        original_prompt, response_a, response_b = parse_input(input_string)
        
        logging.info(f"Original prompt: {original_prompt[:100]}...")
        logging.info(f"Response A length: {len(response_a)}")
        logging.info(f"Response B length: {len(response_b)}")
        
        result = evaluate_responses(original_prompt, response_a, response_b)
        logging.info(f"Final evaluation result: {result}")
        
        return result
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        # In case of any error, return a default
        return "B"