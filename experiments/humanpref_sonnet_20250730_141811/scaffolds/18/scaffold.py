import logging
import re
from llm_executor import execute_llm

def extract_components(input_string):
    """Extract the original prompt, Response A, and Response B from the input."""
    lines = input_string.strip().split('\n')
    
    # Find section markers
    prompt_start = None
    response_a_start = None  
    response_b_start = None
    question_start = None
    
    for i, line in enumerate(lines):
        if line.startswith('Original prompt:'):
            prompt_start = i
        elif line.strip() == 'Response A:':
            response_a_start = i
        elif line.strip() == 'Response B:':
            response_b_start = i
        elif line.startswith('Which response was preferred?'):
            question_start = i
            
    if prompt_start is None or response_a_start is None or response_b_start is None:
        raise ValueError("Could not find required sections in input")
    
    # Extract prompt (everything after "Original prompt:" until "Response A:")
    prompt_lines = []
    for i in range(prompt_start + 1, response_a_start):
        line = lines[i].strip()
        if line:
            prompt_lines.append(line)
    prompt = ' '.join(prompt_lines)
    
    # Extract Response A (everything after "Response A:" until "Response B:")
    response_a_lines = []
    for i in range(response_a_start + 1, response_b_start):
        response_a_lines.append(lines[i])
    response_a = '\n'.join(response_a_lines).strip()
    
    # Extract Response B (everything after "Response B:" until end or question)
    response_b_lines = []
    end_idx = question_start if question_start else len(lines)
    for i in range(response_b_start + 1, end_idx):
        response_b_lines.append(lines[i])
    response_b = '\n'.join(response_b_lines).strip()
    
    return prompt, response_a, response_b

def evaluate_accuracy(prompt, response_a, response_b):
    """Evaluate which response is more accurate."""
    accuracy_prompt = f"""Compare these two responses for accuracy and correctness.

Original prompt: {prompt}

Response A: {response_a}

Response B: {response_b}

Which response is more accurate and factually correct? Consider:
- Mathematical correctness
- Factual accuracy  
- Technical correctness
- Logical consistency

Respond with just "A" or "B" followed by a brief explanation."""

    try:
        result = execute_llm(accuracy_prompt)
        if result.strip().startswith('A'):
            return 'A', result
        elif result.strip().startswith('B'):
            return 'B', result
        else:
            # Try to extract preference
            match = re.search(r'\b([AB])\b', result)
            return match.group(1) if match else 'A', result
    except Exception as e:
        logging.error(f"Error evaluating accuracy: {e}")
        return 'A', str(e)

def evaluate_helpfulness(prompt, response_a, response_b):
    """Evaluate which response is more helpful and relevant."""
    helpfulness_prompt = f"""Compare these two responses for helpfulness and relevance.

Original prompt: {prompt}

Response A: {response_a}

Response B: {response_b}

Which response better addresses the original prompt? Consider:
- Direct relevance to the question
- Practical usefulness
- Completeness of the answer
- Whether it actually helps the user

Respond with just "A" or "B" followed by a brief explanation."""

    try:
        result = execute_llm(helpfulness_prompt)
        if result.strip().startswith('A'):
            return 'A', result
        elif result.strip().startswith('B'):
            return 'B', result
        else:
            match = re.search(r'\b([AB])\b', result)
            return match.group(1) if match else 'A', result
    except Exception as e:
        logging.error(f"Error evaluating helpfulness: {e}")
        return 'A', str(e)

def evaluate_quality(prompt, response_a, response_b):
    """Evaluate overall quality including comprehensiveness and appropriateness."""
    quality_prompt = f"""Compare these two responses for overall quality.

Original prompt: {prompt}

Response A: {response_a}

Response B: {response_b}

Which response is higher quality overall? Consider:
- Comprehensiveness and detail
- Clarity and organization
- Appropriate tone and style
- Professional presentation
- Examples and supporting information

Respond with just "A" or "B" followed by a brief explanation."""

    try:
        result = execute_llm(quality_prompt)
        if result.strip().startswith('A'):
            return 'A', result
        elif result.strip().startswith('B'):
            return 'B', result
        else:
            match = re.search(r'\b([AB])\b', result)
            return match.group(1) if match else 'A', result
    except Exception as e:
        logging.error(f"Error evaluating quality: {e}")
        return 'A', str(e)

def make_final_decision(prompt, response_a, response_b):
    """Make the final decision by having the LLM directly compare responses."""
    decision_prompt = f"""You must determine which response is better overall.

Original prompt: {prompt}

Response A: {response_a}

Response B: {response_b}

Considering all factors (accuracy, helpfulness, quality, appropriateness), which response would be preferred by most users?

Respond with ONLY "A" or "B" - no other text."""

    try:
        result = execute_llm(decision_prompt).strip().upper()
        if result == 'A' or result == 'B':
            return result
        else:
            # Fallback: try to extract A or B
            match = re.search(r'\b([AB])\b', result.upper())
            return match.group(1) if match else 'A'
    except Exception as e:
        logging.error(f"Error making final decision: {e}")
        return 'A'

def process_input(input_string: str) -> str:
    try:
        # Extract components from input
        prompt, response_a, response_b = extract_components(input_string)
        
        logging.info(f"Extracted prompt: {prompt[:100]}...")
        logging.info(f"Response A length: {len(response_a)} characters")
        logging.info(f"Response B length: {len(response_b)} characters")
        
        # Get multiple evaluations
        accuracy_choice, accuracy_reason = evaluate_accuracy(prompt, response_a, response_b)
        helpfulness_choice, helpfulness_reason = evaluate_helpfulness(prompt, response_a, response_b)
        quality_choice, quality_reason = evaluate_quality(prompt, response_a, response_b)
        
        logging.info(f"Accuracy evaluation: {accuracy_choice}")
        logging.info(f"Helpfulness evaluation: {helpfulness_choice}")
        logging.info(f"Quality evaluation: {quality_choice}")
        
        # Count votes
        votes = [accuracy_choice, helpfulness_choice, quality_choice]
        a_votes = votes.count('A')
        b_votes = votes.count('B')
        
        if a_votes > b_votes:
            final_choice = 'A'
        elif b_votes > a_votes:
            final_choice = 'B'
        else:
            # Tie - use final decision function
            final_choice = make_final_decision(prompt, response_a, response_b)
        
        logging.info(f"Final choice: {final_choice} (A votes: {a_votes}, B votes: {b_votes})")
        
        return f"Answer: {final_choice}"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        # Return a safe default
        return "Answer: A"