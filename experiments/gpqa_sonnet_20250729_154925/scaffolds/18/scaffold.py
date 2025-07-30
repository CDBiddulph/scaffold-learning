import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Leave buffer before 120s limit
    
    try:
        # Extract the actual question content, skipping metadata
        lines = input_string.strip().split('\n')
        question_start = 0
        
        # Skip metadata lines that start with < or &lt;
        for i, line in enumerate(lines):
            if line.strip() and not line.startswith('<') and not line.startswith('&lt;'):
                question_start = i
                break
        
        question_content = '\n'.join(lines[question_start:]).strip()
        
        if not question_content:
            logging.error("No question content found")
            return "A"
        
        logging.info(f"Processing question: {question_content[:200]}...")
        
        # Check timeout
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout")
            return "A"
        
        # First, let the LLM identify the type of problem and plan the approach
        analysis_prompt = f"""Analyze this scientific question and determine the best approach to solve it:

{question_content}

Please:
1. Identify the subject area (physics, chemistry, biology, etc.)
2. Identify the key concepts and formulas needed
3. Outline the steps needed to solve this problem
4. Note any calculations required

Keep your response concise and focused."""

        analysis = execute_llm(analysis_prompt)
        logging.info(f"Problem analysis: {analysis[:300]}...")
        
        # Check timeout again
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout after analysis")
            return "A"
        
        # Now solve the problem step by step
        solve_prompt = f"""You are an expert scientist. Based on this analysis:

{analysis}

Now solve this question step by step:

{question_content}

Instructions:
- Work through each step methodically
- Show all calculations clearly
- Apply the relevant scientific principles
- Eliminate incorrect options if helpful
- Choose the best answer from the given options
- End with "FINAL ANSWER: X" where X is A, B, C, or D

Be precise and thorough."""

        solution = execute_llm(solve_prompt)
        logging.info(f"Solution received: {len(solution)} characters")
        
        # Extract the final answer using multiple patterns
        patterns = [
            r'FINAL ANSWER:\s*([A-D])',
            r'Final Answer:\s*([A-D])', 
            r'Answer:\s*([A-D])',
            r'The answer is\s*([A-D])',
            r'Therefore,?\s*([A-D])',
            r'\(([A-D])\)\s*$'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, solution, re.IGNORECASE | re.MULTILINE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Found answer with pattern '{pattern}': {answer}")
                return answer
        
        # Look for standalone letter at the end
        solution_lines = solution.strip().split('\n')
        for line in reversed(solution_lines[-3:]):  # Check last 3 lines
            line = line.strip()
            if line in ['A', 'B', 'C', 'D']:
                logging.info(f"Found standalone letter: {line}")
                return line
        
        # If still no answer found, try one more focused prompt
        if time.time() - start_time < timeout - 10:
            final_prompt = f"""Based on this solution:

{solution}

What is the correct answer? Respond with only the letter A, B, C, or D."""
            
            final_response = execute_llm(final_prompt)
            final_response = final_response.strip()
            
            if final_response in ['A', 'B', 'C', 'D']:
                logging.info(f"Final focused answer: {final_response}")
                return final_response
        
        logging.warning("Could not extract answer reliably, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return "A"