import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    try:
        # Clean the input by removing validation function lines
        lines = input_string.strip().split('\n')
        cleaned_lines = []
        in_validation_function = False
        
        for line in lines:
            if 'def validate_answer' in line:
                in_validation_function = True
                continue
            elif in_validation_function and line.strip().startswith('return answer =='):
                in_validation_function = False
                continue
            elif line.strip().startswith('# Internal validation function'):
                continue
            elif not in_validation_function:
                cleaned_lines.append(line)
        
        content = '\n'.join(cleaned_lines).strip()
        
        # Remove surrounding quotes if present
        if content.startswith('"') and content.endswith('"'):
            content = content[1:-1]
        
        logging.info(f"Processing question of length: {len(content)}")
        
        # Prompt the LLM with domain expertise context
        prompt = f"""You are a world-class expert in chemistry, physics, biology, astronomy, mathematics, and other scientific disciplines with deep knowledge in both theoretical concepts and practical applications.

Please solve this academic question step by step:

{content}

Instructions:
- Read the question carefully and identify the key scientific concepts involved
- Apply your expert knowledge to reason through the problem systematically
- Consider each multiple choice option carefully
- Show your reasoning process
- Conclude with your final answer in the exact format: Answer: <letter> where <letter> is A, B, C, or D"""

        response = execute_llm(prompt)
        
        # Log response preview for debugging
        logging.info(f"LLM response preview: {response[:200]}...")
        
        # Extract answer using multiple robust patterns
        patterns = [
            r'Answer:\s*([A-D])',  # Primary expected format
            r'final answer.*?is\s*([A-D])', 
            r'answer.*?is\s*([A-D])',
            r'therefore.*?([A-D])',
            r'thus.*?([A-D])', 
            r'so.*?([A-D])',
            r'option\s*([A-D])',
            r'choice\s*([A-D])',
            r'\b([A-D])\s*is\s*correct',
            r'select\s*([A-D])',
            r'choose\s*([A-D])'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, response, re.IGNORECASE | re.DOTALL)
            if matches:
                answer = matches[-1].upper()
                logging.info(f"Found answer '{answer}' using pattern: {pattern}")
                return answer
        
        # Fallback: look for any standalone letter near end of response
        # Split into sentences and look for letters in final sentences
        sentences = re.split(r'[.!?]+', response)
        for sentence in reversed(sentences[-3:]):  # Check last 3 sentences
            letters = re.findall(r'\b([A-D])\b', sentence)
            if letters:
                answer = letters[-1].upper()
                logging.info(f"Fallback: found letter '{answer}' in sentence: {sentence[:50]}...")
                return answer
        
        # Last resort: any A, B, C, D in the response
        all_letters = re.findall(r'\b([A-D])\b', response)
        if all_letters:
            answer = all_letters[-1].upper()
            logging.info(f"Last resort: using final letter found: {answer}")
            return answer
        
        logging.error("No answer pattern found in LLM response")
        logging.error(f"Full response: {response}")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return "A"