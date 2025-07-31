import logging
import json
import re
from llm_executor import execute_llm
from typing import Tuple, Dict, Any

def extract_prompt_and_responses(input_string: str) -> Tuple[str, str, str]:
    """Extract the original prompt and both responses from the input."""
    lines = input_string.strip().split('\n')
    
    # Find the original prompt
    prompt_start = -1
    for i, line in enumerate(lines):
        if line.startswith("Original prompt:"):
            prompt_start = i
            break
    
    if prompt_start == -1:
        raise ValueError("Could not find 'Original prompt:' in input")
    
    # Find Response A and Response B
    response_a_start = -1
    response_b_start = -1
    
    for i, line in enumerate(lines):
        if line.startswith("Response A:"):
            response_a_start = i
        elif line.startswith("Response B:"):
            response_b_start = i
    
    if response_a_start == -1 or response_b_start == -1:
        raise ValueError("Could not find both Response A and Response B")
    
    # Extract text
    prompt = lines[prompt_start][16:].strip()  # Remove "Original prompt: "
    
    response_a_lines = []
    for i in range(response_a_start + 1, response_b_start):
        response_a_lines.append(lines[i])
    response_a = '\n'.join(response_a_lines).strip()
    
    response_b_lines = []
    for i in range(response_b_start + 1, len(lines)):
        if lines[i].startswith("Which response was preferred?"):
            break
        response_b_lines.append(lines[i])
    response_b = '\n'.join(response_b_lines).strip()
    
    return prompt, response_a, response_b

def evaluate_response_quality(prompt: str, response: str, response_label: str) -> Dict[str, Any]:
    """Evaluate a single response on multiple quality dimensions."""
    
    evaluation_prompt = f"""Evaluate this response on the following criteria. Respond with a JSON object containing scores from 1-10 for each criterion.

Original Prompt: {prompt}

Response {response_label}: {response}

Evaluate on these criteria:
- completeness: Is the response complete and not cut off?
- accuracy: Is the information provided accurate?  
- instruction_following: Does it follow the specific instructions in the prompt?
- relevance: Does it stay on topic and address what was asked?
- appropriate_detail: Is the level of detail appropriate (not too brief or verbose)?
- format_compliance: If a format was requested, does it follow it?
- practicality: Is the advice/information practical and actionable?
- directness: When directness is needed, is the response appropriately direct?

Respond with only a JSON object like:
{{"completeness": 8, "accuracy": 9, "instruction_following": 7, "relevance": 9, "appropriate_detail": 8, "format_compliance": 10, "practicality": 7, "directness": 8}}"""

    try:
        response_text = execute_llm(evaluation_prompt)
        # Try to extract JSON from response
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except Exception as e:
        logging.warning(f"Failed to parse evaluation JSON for response {response_label}: {e}")
    
    # Return default scores if parsing fails
    return {
        "completeness": 5, "accuracy": 5, "instruction_following": 5,
        "relevance": 5, "appropriate_detail": 5, "format_compliance": 5,
        "practicality": 5, "directness": 5
    }

def compare_responses(prompt: str, response_a: str, response_b: str) -> str:
    """Make a direct comparison between the two responses."""
    
    comparison_prompt = f"""Compare these two responses to determine which is better overall. Consider factors like:
- Which better addresses the original prompt
- Which provides more accurate/helpful information
- Which follows instructions more precisely
- Which is more complete and well-structured

Original Prompt: {prompt}

Response A: {response_a}

Response B: {response_b}

Based on your analysis, which response is better overall? Respond with exactly "A" or "B" and nothing else."""

    try:
        result = execute_llm(comparison_prompt).strip().upper()
        if result in ['A', 'B']:
            return result
    except Exception as e:
        logging.warning(f"Failed to get comparison result: {e}")
    
    return "A"  # Default fallback

def determine_preference(eval_a: Dict[str, Any], eval_b: Dict[str, Any], direct_comparison: str) -> str:
    """Combine evaluations to determine final preference."""
    
    # Calculate weighted scores
    weights = {
        "completeness": 1.2,
        "accuracy": 1.5,
        "instruction_following": 1.4,
        "relevance": 1.3,
        "appropriate_detail": 1.0,
        "format_compliance": 1.1,
        "practicality": 1.0,
        "directness": 0.9
    }
    
    try:
        score_a = sum(eval_a.get(criterion, 5) * weight for criterion, weight in weights.items())
        score_b = sum(eval_b.get(criterion, 5) * weight for criterion, weight in weights.items())
        
        logging.info(f"Score A: {score_a}, Score B: {score_b}")
        logging.info(f"Direct comparison result: {direct_comparison}")
        
        # Use direct comparison as primary signal, scores as secondary
        if direct_comparison == "A":
            if score_b > score_a + 5:  # Only override if B is significantly better
                return "B"
            return "A"
        else:  # direct_comparison == "B"
            if score_a > score_b + 5:  # Only override if A is significantly better
                return "A"
            return "B"
            
    except Exception as e:
        logging.error(f"Error in scoring calculation: {e}")
        return direct_comparison

def process_input(input_string: str) -> str:
    """Main function to determine which response was preferred."""
    
    try:
        # Extract components
        prompt, response_a, response_b = extract_prompt_and_responses(input_string)
        logging.info(f"Extracted prompt length: {len(prompt)}")
        logging.info(f"Response A length: {len(response_a)}")
        logging.info(f"Response B length: {len(response_b)}")
        
        # Evaluate both responses
        eval_a = evaluate_response_quality(prompt, response_a, "A")
        eval_b = evaluate_response_quality(prompt, response_b, "B")
        
        logging.info(f"Evaluation A: {eval_a}")
        logging.info(f"Evaluation B: {eval_b}")
        
        # Get direct comparison
        direct_comparison = compare_responses(prompt, response_a, response_b)
        
        # Make final determination
        preference = determine_preference(eval_a, eval_b, direct_comparison)
        
        logging.info(f"Final preference: {preference}")
        return f"Answer: {preference}"
        
    except Exception as e:
        logging.error(f"Error in process_input: {str(e)}")
        # If we can't parse or evaluate properly, try a simple direct comparison
        try:
            lines = input_string.strip().split('\n')
            # Find responses in a more robust way
            full_text = input_string
            if "Response A:" in full_text and "Response B:" in full_text:
                # Extract a simple comparison
                simple_prompt = f"""Look at this input and determine whether Response A or Response B was preferred. 

{input_string}

Respond with exactly "A" or "B"."""
                result = execute_llm(simple_prompt).strip().upper()
                if result in ['A', 'B']:
                    return f"Answer: {result}"
        except:
            pass
        
        return "Answer: A"  # Ultimate fallback