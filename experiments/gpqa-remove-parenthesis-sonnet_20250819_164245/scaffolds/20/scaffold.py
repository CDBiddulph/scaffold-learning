import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        logging.info("Processing scientific multiple choice question...")
        
        # Parse options using regex - handle both A) and A formats
        option_pattern = r'([ABCD])\s*\)?\s*(.*?)(?=\n[ABCD]\s*\)|$)'
        option_matches = re.findall(option_pattern, input_string, re.DOTALL)
        
        options = {}
        for letter, content in option_matches:
            # Clean up the content
            content = content.strip()
            # Remove any trailing instruction text
            content = re.sub(r'\n\s*Think step-by-step.*', '', content, flags=re.DOTALL | re.IGNORECASE)
            if content:
                options[letter] = content
        
        # Extract question by removing options and instructions
        question_text = input_string
        
        # Remove option lines
        for letter in options:
            pattern = rf'{letter}\s*\)?\s*{re.escape(options[letter])}'
            question_text = re.sub(pattern, '', question_text, flags=re.IGNORECASE)
        
        # Remove instruction text
        instruction_patterns = [
            r'Think step-by-step.*?Answer.*?letter.*',
            r'Think step-by-step.*',
        ]
        
        for pattern in instruction_patterns:
            question_text = re.sub(pattern, '', question_text, flags=re.IGNORECASE | re.DOTALL)
        
        question = question_text.strip()
        
        logging.info(f"Question: {question[:100]}...")
        logging.info(f"Options: {list(options.keys())}")
        
        if not options or not question:
            logging.error("Failed to parse question or options properly")
            return "A"
        
        # Check timeout before making LLM call
        if time.time() - start_time > 100:
            logging.warning("Timeout approaching, returning default")
            return "A"
        
        # Create detailed prompt for the LLM
        prompt = f"""You are an expert scientist with deep knowledge across all scientific disciplines including organic chemistry, biochemistry, molecular biology, physics, quantum mechanics, astrophysics, and related fields.

Solve this scientific question step by step:

QUESTION:
{question}

OPTIONS:
"""
        for letter in sorted(options.keys()):
            prompt += f"{letter}) {options[letter]}\n"
        
        prompt += """

Please:
1. Identify the scientific principles involved
2. Work through the problem systematically 
3. Consider each option carefully
4. Provide clear reasoning for your choice

End your response with: "FINAL ANSWER: X" where X is the letter A, B, C, or D."""

        # Get LLM response
        logging.info("Requesting LLM analysis...")
        response = execute_llm(prompt)
        
        # Extract answer using multiple patterns
        answer_patterns = [
            r'FINAL ANSWER:\s*([ABCD])',
            r'Final Answer:\s*([ABCD])', 
            r'Answer:\s*([ABCD])',
            r'answer is\s*([ABCD])',
            r'correct answer:\s*([ABCD])',
            r'choose\s*([ABCD])',
            r'option\s*([ABCD])\s*(?:is|are)',
            r'therefore\s*([ABCD])',
        ]
        
        for pattern in answer_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                answer = matches[-1].upper()
                if answer in options:
                    logging.info(f"Extracted answer: {answer}")
                    return answer
        
        # Fallback: look for letters mentioned near end of response
        response_end = response[-300:]
        letter_mentions = re.findall(r'\b([ABCD])\b', response_end)
        if letter_mentions:
            answer = letter_mentions[-1].upper()
            if answer in options:
                logging.info(f"Using fallback answer: {answer}")
                return answer
        
        # Default fallback
        logging.warning("Could not extract answer, using default A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"