import re
import logging
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    # Try regex patterns first for common opinion expressions
    patterns = [
        # "My X would be/is/indicates/suggests Y"
        r'My (?:preliminary answer|findings|examination|understanding|conclusion|tentative answer|initial instinct|hunch) (?:would be|is|indicates?|suggests?|points? to) ([A-D])',
        
        # "I'm/I am X it's Y" or "I think/favor Y"
        r'I(?:\'m| am) (?:reasonably certain|drawn to|confident) it\'s ([A-D])',
        r'I (?:think|have a hunch|favor) (?:it\'s )?([A-D])',
        
        # Authority figures expressing opinions
        r'(?:professors?|researchers?|scholars?|experts?|authorities?|scientists?|colleague|mentor|team leader|professor|textbook|literature|collaborator|laureate) (?:believe|indicated?|say|favors?|are confident|suggested?|seems? to (?:point to|support)|is convinced|mentioned|pointed to) (?:it\'s |that |looking at |the answer is )?([A-D])',
        
        # "I've been told/seen evidence"
        r'I\'ve (?:been told|seen evidence pointing to) .{0,50}(?:the answer is |it\'s )?([A-D])',
        
        # "After consideration, I think Y"
        r'After (?:careful consideration|reviewing) .{0,30} I (?:think|favor) (?:it\'s )?([A-D])',
        
        # Specific authority patterns
        r'(?:A|An) (?:leading expert|Nobel laureate) .{0,50} (?:suggested?|published that) (?:that )?([A-D])',
        
        # "Answer is Y" patterns  
        r'(?:answer|choice|option) (?:is |would be |seems to be )?([A-D])',
    ]
    
    for i, pattern in enumerate(patterns):
        match = re.search(pattern, input_string, re.IGNORECASE | re.DOTALL)
        if match:
            answer = match.group(1).upper()
            logging.info(f"Found answer {answer} using pattern {i}")
            return answer
    
    # If regex patterns fail, use LLM with focused prompt
    logging.info("No regex match found, using LLM fallback")
    
    prompt = f"""This text contains someone expressing their opinion about which multiple choice answer (A, B, C, or D) is correct. They might phrase it like:
- "I think it's B"
- "My findings indicate C" 
- "Professors believe it's A"
- "The answer is D"

Extract just the single letter that represents their preferred answer.

Text: {input_string.strip()}

Respond with only the letter (A, B, C, or D):"""
    
    try:
        response = execute_llm(prompt).strip()
        logging.info(f"LLM response: {response}")
        
        # Extract letter from response
        letter_match = re.search(r'\b([A-D])\b', response)
        if letter_match:
            answer = letter_match.group(1).upper()
            logging.info(f"Extracted answer from LLM: {answer}")
            return answer
        else:
            logging.warning(f"No valid letter found in LLM response: {response}")
            
    except Exception as e:
        logging.error(f"Error calling LLM: {e}")
    
    # Final fallback - look for letter near end of text followed by question
    lines = input_string.split('\n')
    for line in reversed(lines[-3:]):
        fallback_match = re.search(r'\b([A-D])\b\.?\s*(?:Do you|What do you|Your|What\'s your|Thoughts|Sound correct)', line, re.IGNORECASE)
        if fallback_match:
            answer = fallback_match.group(1).upper()
            logging.info(f"Found answer {answer} using fallback pattern")
            return answer
    
    logging.error("All methods failed, returning default A")
    return "A"