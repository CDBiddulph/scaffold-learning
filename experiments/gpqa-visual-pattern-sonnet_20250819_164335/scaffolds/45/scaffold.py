import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    try:
        logging.info("Processing scientific multiple-choice question")
        
        system_prompt = """You are an expert scientist with deep knowledge across all scientific domains including chemistry, physics, astronomy, biology, mathematics, and engineering. You excel at solving complex problems that require both theoretical understanding and quantitative analysis. Take your time to think through problems carefully and double-check any calculations."""
        
        prompt = f"""{input_string.strip()}

Solve this scientific problem step-by-step:

1. **Identify the domain and concepts**: What scientific field(s) and principles are involved?

2. **Analyze the problem**: What is being asked? What information is given?

3. **Apply scientific principles**: Use relevant theories, equations, and relationships.

4. **Perform calculations carefully**: If calculations are needed, show your work and double-check.

5. **Evaluate answer choices**: Consider each option systematically and determine which is most scientifically accurate.

6. **Final answer**: State your conclusion clearly.

End your response with your final answer as just the letter (A, B, C, or D)."""
        
        response = execute_llm(prompt, system_prompt)
        logging.info(f"LLM response received, length: {len(response)}")
        
        # Extract the final answer letter with multiple patterns in order of preference
        answer_patterns = [
            r'Final answer:\s*([A-D])\b',
            r'Answer:\s*([A-D])\b', 
            r'The answer is\s*([A-D])\b',
            r'Therefore,?\s*(?:the answer is\s*)?([A-D])\b',
            r'I choose\s*([A-D])\b',
            r'([A-D])\s*(?:is the correct answer|is correct)',
            r'Conclusion:\s*([A-D])\b',
            r'^\s*([A-D])\s*$'  # Single letter on its own line
        ]
        
        # Search through patterns in order of preference
        for i, pattern in enumerate(answer_patterns):
            matches = re.findall(pattern, response, re.IGNORECASE | re.MULTILINE)
            if matches:
                answer = matches[-1].upper()  # Take the last match for that pattern
                logging.info(f"Extracted answer '{answer}' using pattern {i}: {pattern}")
                return answer
        
        # Fallback: look for any A-D letters in the last part of the response
        response_lines = response.split('\n')
        for line in reversed(response_lines[-5:]):  # Check last 5 lines
            letters = re.findall(r'\b([A-D])\b', line, re.IGNORECASE)
            if letters:
                answer = letters[-1].upper()
                logging.info(f"Using fallback - found '{answer}' in line: {line}")
                return answer
        
        # Final fallback: any A-D in the entire response
        all_letters = re.findall(r'\b([A-D])\b', response, re.IGNORECASE)
        if all_letters:
            answer = all_letters[-1].upper()
            logging.info(f"Using final fallback - last letter found: {answer}")
            return answer
        
        logging.warning("Could not extract any answer letter from response")
        logging.info(f"Response preview: {response[:200]}...")
        return "A"  # Default fallback
            
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Default fallback