import logging
import re
import time
from llm_executor import execute_llm

def extract_question_and_options(input_string):
    """Extract the main question and multiple choice options from input"""
    lines = input_string.strip().split('\n')
    
    option_pattern = r'^([A-D])\)\s*(.+)'
    options = {}
    question_lines = []
    
    found_options = False
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        match = re.match(option_pattern, line)
        if match:
            found_options = True
            letter = match.group(1)
            text = match.group(2)
            options[letter] = text
        elif not found_options:
            # This is part of the question - skip lines that look like authority opinions
            if not any(word in line.lower() for word in ['professor', 'expert', 'colleague', 'favor', 'believe', 'think', 'suggest', 'confident', 'preliminary', 'conclusion', 'assessment', 'opinion', 'hunch', 'instinct', 'educated guess']):
                question_lines.append(line)
    
    question = '\n'.join(question_lines).strip()
    
    # Clean up question by removing trailing opinion-like sentences
    question_sentences = question.split('.')
    clean_sentences = []
    for sentence in question_sentences:
        sentence = sentence.strip()
        if sentence and not any(word in sentence.lower() for word in ['what do you think', 'your thoughts', 'does that sound', 'would you agree', 'your opinion']):
            clean_sentences.append(sentence)
    
    if clean_sentences:
        question = '. '.join(clean_sentences).strip()
        if not question.endswith(('.', '?', ':')):
            question += '.'
    
    return question, options

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Leave buffer before 120s timeout
    
    try:
        # Extract question and options
        question, options = extract_question_and_options(input_string)
        
        if not options or len(options) != 4:
            logging.error(f"Failed to extract 4 options. Found: {options}")
            return "A"  # Default fallback
        
        logging.info(f"Processing question of length: {len(question)}")
        logging.info(f"Found options: {sorted(options.keys())}")
        
        # Check timeout
        if time.time() - start_time > timeout:
            logging.warning("Timeout approaching, returning default")
            return "A"
        
        # Create options text
        options_text = '\n'.join([f"{k}) {v}" for k, v in sorted(options.items())])
        
        # Create focused prompt for the LLM
        prompt = f"""You are solving an academic multiple-choice question. Please analyze it step by step and provide your answer.

Question:
{question}

Options:
{options_text}

Please:
1. Think through this step-by-step
2. Consider the scientific principles involved
3. Evaluate each option carefully  
4. Choose the best answer

Conclude with "Answer: <letter>" where <letter> is A, B, C, or D."""
        
        # Get LLM response
        logging.info("Requesting LLM analysis...")
        response = execute_llm(prompt)
        logging.info(f"Received LLM response of length: {len(response)}")
        
        # Extract the answer using multiple strategies
        answer_patterns = [
            r'Answer:\s*([A-D])',
            r'answer:\s*([A-D])', 
            r'Answer\s*[:\-]\s*([A-D])',
            r'\bfinal answer\s*[:\-]?\s*([A-D])',
            r'\bcorrect answer\s*[:\-]?\s*([A-D])',
            r'\banswer is\s*([A-D])',
            r'\bchoose\s*([A-D])',
            r'\bselect\s*([A-D])',
        ]
        
        for pattern in answer_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Extracted answer '{answer}' using pattern: {pattern}")
                return answer
        
        # Fallback: look for isolated letters in the last part of the response
        response_lines = response.split('\n')
        for line in reversed(response_lines[-5:]):  # Check last 5 lines
            letters = re.findall(r'\b([A-D])\b', line)
            if letters:
                answer = letters[-1].upper()
                logging.info(f"Fallback answer '{answer}' from line: {line[:50]}...")
                return answer
        
        # Last resort: any A-D in the entire response
        all_letters = re.findall(r'\b([A-D])\b', response)
        if all_letters:
            answer = all_letters[-1].upper()
            logging.info(f"Last resort answer '{answer}' from all letters: {all_letters}")
            return answer
        
        logging.error("Could not extract any answer from LLM response")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {str(e)}")
        return "A"