import logging
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 120  # seconds
    
    try:
        # Split at the question about which response was preferred
        parts = input_string.split("Which response was preferred?")
        if len(parts) < 2:
            logging.error("Could not find 'Which response was preferred?' separator")
            return "A"
            
        content = parts[0].strip()
        
        # Parse the content
        lines = content.split('\n')
        
        prompt_line = None
        response_a_content = []
        response_b_content = []
        current_section = None
        
        for line in lines:
            line = line.strip()
            if line.startswith("Original prompt:"):
                prompt_line = line[len("Original prompt:"):].strip()
                current_section = "prompt"
            elif line == "Response A:":
                current_section = "response_a"
            elif line == "Response B:":
                current_section = "response_b"
            elif current_section == "response_a":
                response_a_content.append(line)
            elif current_section == "response_b":
                response_b_content.append(line)
                
        if not prompt_line:
            logging.error("Could not find original prompt")
            return "A"
            
        response_a = "\n".join(response_a_content).strip()
        response_b = "\n".join(response_b_content).strip()
        
        if not response_a or not response_b:
            logging.error("Could not extract both responses")
            return "A"
            
        logging.info(f"Extracted prompt: {prompt_line}")
        logging.info(f"Response A length: {len(response_a)}")
        logging.info(f"Response B length: {len(response_b)}")
        
        # Check timeout before proceeding
        if time.time() - start_time > timeout - 50:
            logging.warning("Approaching timeout, returning default")
            return "A"
        
        # Step 1: Analyze what the prompt is asking for
        analysis_prompt = f"""Analyze this prompt and identify the key requirements:

Prompt: {prompt_line}

What is the user asking for? What would make a good response? Are there any specific instructions, constraints, or preferences mentioned?

Respond in 2-3 sentences focusing on the most important criteria for a good response."""

        try:
            requirements = execute_llm(analysis_prompt)
            logging.info(f"Requirements analysis: {requirements}")
        except Exception as e:
            logging.error(f"Error in requirements analysis: {e}")
            requirements = "The user needs a helpful and accurate response."
        
        # Check timeout
        if time.time() - start_time > timeout - 35:
            logging.warning("Approaching timeout after analysis, returning default")
            return "A"
        
        # Step 2: Direct comparison with focused evaluation
        comparison_prompt = f"""You must choose which response is better for this prompt.

PROMPT: {prompt_line}

KEY REQUIREMENTS: {requirements}

RESPONSE A:
{response_a}

RESPONSE B:
{response_b}

Evaluate based on:
- How well each response addresses the specific prompt
- Accuracy and correctness of information
- Following any explicit instructions or constraints
- Completeness and helpfulness
- Clarity and organization

Respond with exactly one letter: "A" or "B" (nothing else)."""

        try:
            comparison = execute_llm(comparison_prompt)
            comparison = comparison.strip().upper()
            logging.info(f"Comparison result: {comparison}")
            
            # Extract the preference
            if comparison == "A":
                return "A"
            elif comparison == "B":
                return "B"
            elif comparison.startswith("A"):
                return "A"
            elif comparison.startswith("B"):
                return "B"
            else:
                logging.warning(f"Unclear comparison result: {comparison}")
                
        except Exception as e:
            logging.error(f"Error in comparison: {e}")
        
        # Fallback: Simple direct comparison
        if time.time() - start_time < timeout - 20:
            try:
                fallback_prompt = f"""Which response better answers this prompt?

PROMPT: {prompt_line}

A: {response_a[:500]}...
B: {response_b[:500]}...

Answer: A or B"""
                
                fallback_result = execute_llm(fallback_prompt).strip().upper()
                logging.info(f"Fallback result: {fallback_result}")
                
                if fallback_result in ["A", "B"]:
                    return fallback_result
                elif fallback_result.startswith("A"):
                    return "A"
                elif fallback_result.startswith("B"):
                    return "B"
                    
            except Exception as e:
                logging.error(f"Error in fallback: {e}")
        
        # Final fallback
        logging.warning("All evaluation methods failed, returning default A")
        return "A"
                
    except Exception as e:
        logging.error(f"Critical error in process_input: {e}")
        return "A"