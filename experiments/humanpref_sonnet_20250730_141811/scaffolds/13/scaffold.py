import logging
import json
from llm_executor import execute_llm

def evaluate_response_quality(prompt, response_a, response_b):
    """Evaluate which response is better based on multiple criteria"""
    
    evaluation_prompt = f"""You are evaluating two responses to determine which is better. Consider these criteria:

1. ACCURACY: Is the information factually correct?
2. INSTRUCTION FOLLOWING: Does it follow the prompt's requirements precisely?
3. COMPLETENESS: Is the response appropriately detailed for the question?
4. HELPFULNESS: Is it practically useful to the user?
5. CLARITY: Is it well-written and clear?

Original Prompt: {prompt}

Response A: {response_a}

Response B: {response_b}

Analyze each response on the above criteria. Then conclude with either "WINNER: A" or "WINNER: B".
Focus especially on accuracy and instruction-following, as these seem most important."""
    
    try:
        evaluation = execute_llm(evaluation_prompt)
        logging.info(f"Evaluation result: {evaluation}")
        
        # Extract winner from evaluation
        if "WINNER: A" in evaluation:
            return "A"
        elif "WINNER: B" in evaluation:
            return "B"
        else:
            # Fallback - look for other indicators
            if "Response A" in evaluation and "better" in evaluation.lower():
                return "A"
            elif "Response B" in evaluation and "better" in evaluation.lower():
                return "B"
            else:
                # Default fallback
                logging.warning("Could not determine winner from evaluation, defaulting to A")
                return "A"
                
    except Exception as e:
        logging.error(f"Error in evaluation: {e}")
        return "A"  # Default fallback

def check_factual_accuracy(prompt, response_a, response_b):
    """Check for obvious factual errors"""
    
    accuracy_prompt = f"""Check these two responses for factual accuracy and obvious errors.

Original question: {prompt}

Response A: {response_a}

Response B: {response_b}

Identify any clear factual errors, misconceptions, or incorrect information in either response. Be specific about what's wrong. If both seem accurate, say "BOTH_ACCURATE". If one has clear errors, specify "A_HAS_ERRORS" or "B_HAS_ERRORS"."""
    
    try:
        accuracy_check = execute_llm(accuracy_prompt)
        logging.info(f"Accuracy check: {accuracy_check}")
        
        if "A_HAS_ERRORS" in accuracy_check:
            return "B"
        elif "B_HAS_ERRORS" in accuracy_check:
            return "A"
        else:
            return None  # No clear accuracy winner
            
    except Exception as e:
        logging.error(f"Error in accuracy check: {e}")
        return None

def check_instruction_following(prompt, response_a, response_b):
    """Check how well each response follows the specific instructions"""
    
    instruction_prompt = f"""Evaluate how well each response follows the specific instructions in the prompt.

Prompt: {prompt}

Response A: {response_a}

Response B: {response_b}

Which response better follows the specific requirements, format, or constraints mentioned in the prompt? Consider:
- Did they answer what was actually asked?
- Did they follow any specified format?
- Did they include/exclude what was requested?

Respond with "A_BETTER", "B_BETTER", or "EQUAL"."""
    
    try:
        instruction_check = execute_llm(instruction_prompt)
        logging.info(f"Instruction following check: {instruction_check}")
        
        if "A_BETTER" in instruction_check:
            return "A"
        elif "B_BETTER" in instruction_check:
            return "B"
        else:
            return None
            
    except Exception as e:
        logging.error(f"Error in instruction following check: {e}")
        return None

def process_input(input_string: str) -> str:
    """Main function to determine which response was preferred"""
    
    try:
        lines = input_string.strip().split('\n')
        
        # Find the original prompt
        prompt_start = -1
        for i, line in enumerate(lines):
            if line.startswith("Original prompt:"):
                prompt_start = i
                break
        
        if prompt_start == -1:
            logging.error("Could not find 'Original prompt:' in input")
            return "Answer: A"
        
        # Extract prompt
        prompt = lines[prompt_start][16:].strip()  # Remove "Original prompt: "
        
        # Find Response A and Response B
        response_a_start = -1
        response_b_start = -1
        
        for i, line in enumerate(lines):
            if line.startswith("Response A:"):
                response_a_start = i
            elif line.startswith("Response B:"):
                response_b_start = i
        
        if response_a_start == -1 or response_b_start == -1:
            logging.error("Could not find Response A or Response B")
            return "Answer: A"
        
        # Extract responses
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
        
        logging.info(f"Prompt: {prompt[:100]}...")
        logging.info(f"Response A length: {len(response_a)}")
        logging.info(f"Response B length: {len(response_b)}")
        
        # Run multiple evaluation approaches
        
        # 1. Check factual accuracy first (high priority)
        accuracy_winner = check_factual_accuracy(prompt, response_a, response_b)
        if accuracy_winner:
            logging.info(f"Accuracy winner: {accuracy_winner}")
            return f"Answer: {accuracy_winner}"
        
        # 2. Check instruction following
        instruction_winner = check_instruction_following(prompt, response_a, response_b)
        if instruction_winner:
            logging.info(f"Instruction following winner: {instruction_winner}")
            return f"Answer: {instruction_winner}"
        
        # 3. Overall quality evaluation
        quality_winner = evaluate_response_quality(prompt, response_a, response_b)
        logging.info(f"Quality winner: {quality_winner}")
        return f"Answer: {quality_winner}"
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return "Answer: A"  # Default fallback