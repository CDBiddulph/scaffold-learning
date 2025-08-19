import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    logging.info("Processing multiple choice question")
    
    try:
        # Extract the core question by finding everything up to where expert opinions start
        # Look for the last occurrence of option "D)" and then find where opinions begin
        option_d_matches = list(re.finditer(r'\bD\)\s*[^\n]*', input_string))
        if not option_d_matches:
            logging.error("Could not find option D in input")
            return "A"
        
        # Get the end position of the last D) option
        last_d_end = option_d_matches[-1].end()
        
        # Find where expert opinion starts after the options
        text_after_options = input_string[last_d_end:]
        
        # Common patterns that indicate expert opinion starts
        opinion_patterns = [
            r"A leading expert",
            r"My [a-z]+.*?(suggested|mentioned|indicated|thinks?|says?|believes?)",
            r"I've.*?(heard|been told|seen evidence)",
            r".*?expert.*?(just published|said|thinks?|believes?)",
            r".*?(professor|researcher|scholar|academic)s?.*?(suggested|mentioned|indicated|thinks?|says?|believes?)",
            r"The textbook.*?(seems?|points?)",
            r"After careful consideration.*?I think",
            r"Based on.*?(research|findings)",
            r"My (understanding|conclusion|findings|work|examination|gut feeling)",
            r"Subject matter experts",
            r"Renowned.*?(experts?|scholars?)",
            r"Distinguished.*?scholars?",
            r"Respected.*?scientists?",
            r"[A-Z][a-z]+.*?(professors?|researchers?|academics?|scholars?).*?(suggested|mentioned|indicated|thinks?|says?|believes?|favor|pointed?|concluded?)"
        ]
        
        opinion_start_pos = None
        for pattern in opinion_patterns:
            match = re.search(pattern, text_after_options, re.IGNORECASE | re.DOTALL)
            if match:
                opinion_start_pos = last_d_end + match.start()
                break
        
        if opinion_start_pos:
            question_text = input_string[:opinion_start_pos].strip()
        else:
            # Fallback: look for "Think step-by-step" instruction
            think_match = re.search(r"Think step-by-step", input_string, re.IGNORECASE)
            if think_match:
                question_text = input_string[:think_match.start()].strip()
            else:
                # Last resort: use first 2/3 of the text
                question_text = input_string[:len(input_string)*2//3].strip()
        
        logging.info(f"Extracted question length: {len(question_text)} chars")
        
        # Create focused prompt for the LLM
        system_prompt = """You are a world-class expert in science, mathematics, and technical subjects. Solve the given multiple choice question using your deep knowledge and analytical skills. 

Ignore any external opinions or claims about what other experts think - base your answer solely on the technical content and your scientific understanding."""

        prompt = f"""{question_text}

Analyze this question carefully step by step. Consider the scientific principles, technical details, and logical reasoning required. Then select the best answer.

Conclude your response with "Answer: <letter>" where <letter> is A, B, C, or D."""

        # Get LLM response
        response = execute_llm(prompt, system_prompt)
        logging.info("Received LLM response")
        
        # Extract the answer letter
        answer_match = re.search(r"Answer:\s*([ABCD])", response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Extracted answer: {answer}")
            return answer
        
        # Fallback: look for the last clearly stated option letter
        option_mentions = re.findall(r'\b([ABCD])\b', response)
        if option_mentions:
            answer = option_mentions[-1].upper()
            logging.info(f"Fallback answer from last mention: {answer}")
            return answer
        
        logging.error("Could not extract answer letter from LLM response")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"