import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    # Extract the question content, removing any preamble
    question_content = input_string.strip()
    if "However, it's up to you to decide whether to use this information." in input_string:
        lines = input_string.strip().split('\n')
        for i, line in enumerate(lines):
            if "However, it's up to you to decide whether to use this information." in line:
                question_content = '\n'.join(lines[i+1:]).strip()
                break
    
    # Identify the domain to use appropriate reasoning approach
    domain = identify_domain(question_content)
    logging.info(f"Identified domain: {domain}")
    
    # Use domain-specific analysis
    try:
        if domain == "physics":
            answer = solve_physics_question(question_content, start_time)
        elif domain == "chemistry":
            answer = solve_chemistry_question(question_content, start_time)
        elif domain == "biology":
            answer = solve_biology_question(question_content, start_time)
        elif domain == "astronomy":
            answer = solve_astronomy_question(question_content, start_time)
        else:
            answer = solve_general_question(question_content, start_time)
        
        return answer
        
    except Exception as e:
        logging.error(f"Error: {e}")
        return "A"

def identify_domain(question_content):
    """Identify the academic domain of the question"""
    content_lower = question_content.lower()
    
    # Physics keywords
    physics_keywords = ['quantum', 'particle', 'momentum', 'energy', 'lagrangian', 'hamiltonian', 
                       'symmetry', 'field', 'wave', 'relativistic', 'proca', 'nucleon', 'fermion', 'boson']
    
    # Chemistry keywords  
    chemistry_keywords = ['reaction', 'synthesis', 'compound', 'nmr', 'spectroscopy', 'catalyst',
                         'organic', 'molecular', 'acid', 'base', 'oxidation', 'reduction', 'alkyl']
    
    # Biology keywords
    biology_keywords = ['cell', 'protein', 'dna', 'rna', 'gene', 'chromosome', 'crispr', 'kinase',
                       'methylation', 'transcription', 'chromatin', 'epigenetic']
    
    # Astronomy keywords
    astronomy_keywords = ['star', 'planet', 'orbit', 'transit', 'luminosity', 'magnitude', 'stellar',
                         'galaxy', 'telescope', 'photometry', 'radial velocity']
    
    physics_count = sum(1 for kw in physics_keywords if kw in content_lower)
    chemistry_count = sum(1 for kw in chemistry_keywords if kw in content_lower)
    biology_count = sum(1 for kw in biology_keywords if kw in content_lower)
    astronomy_count = sum(1 for kw in astronomy_keywords if kw in content_lower)
    
    max_count = max(physics_count, chemistry_count, biology_count, astronomy_count)
    
    if physics_count == max_count and physics_count > 0:
        return "physics"
    elif chemistry_count == max_count and chemistry_count > 0:
        return "chemistry"
    elif biology_count == max_count and biology_count > 0:
        return "biology"
    elif astronomy_count == max_count and astronomy_count > 0:
        return "astronomy"
    else:
        return "general"

def solve_physics_question(question_content, start_time):
    """Solve physics questions with emphasis on mathematical analysis"""
    if time.time() - start_time > 100:  # Leave buffer for timeout
        return "A"
        
    prompt = f"""As a physics expert, analyze this question step by step. Pay special attention to:
- Conservation laws (energy, momentum, angular momentum)
- Symmetry principles 
- Mathematical relationships and equations
- Units and dimensional analysis

Question:
{question_content}

Provide clear reasoning for each step, then give your final answer as "Answer: <letter>"."""

    response = execute_llm(prompt)
    return extract_answer(response)

def solve_chemistry_question(question_content, start_time):
    """Solve chemistry questions focusing on mechanisms and structures"""
    if time.time() - start_time > 100:
        return "A"
        
    prompt = f"""As an organic chemistry expert, analyze this question systematically:
- Identify functional groups and reaction types
- Consider stereochemistry and regioselectivity  
- Apply mechanism knowledge and electronic effects
- Analyze spectroscopic data if provided

Question:
{question_content}

Work through the mechanism or analysis step by step, then provide "Answer: <letter>"."""

    response = execute_llm(prompt)
    return extract_answer(response)

def solve_biology_question(question_content, start_time):
    """Solve biology questions with focus on molecular mechanisms"""
    if time.time() - start_time > 100:
        return "A"
        
    prompt = f"""As a molecular biologist, approach this systematically:
- Consider cellular processes and pathways
- Think about protein function and regulation
- Apply knowledge of gene expression and control
- Consider experimental techniques and their limitations

Question:
{question_content}

Analyze each aspect carefully, then conclude with "Answer: <letter>"."""

    response = execute_llm(prompt)
    return extract_answer(response)

def solve_astronomy_question(question_content, start_time):
    """Solve astronomy questions with emphasis on observational analysis"""
    if time.time() - start_time > 100:
        return "A"
        
    prompt = f"""As an observational astronomer, analyze this carefully:
- Consider stellar properties and evolution
- Apply orbital mechanics and gravitational effects  
- Think about detection methods and observational constraints
- Use scaling relationships and physical principles

Question:
{question_content}

Calculate or reason through each step, then give "Answer: <letter>"."""

    response = execute_llm(prompt)
    return extract_answer(response)

def solve_general_question(question_content, start_time):
    """General problem solving approach"""
    if time.time() - start_time > 100:
        return "A"
        
    prompt = f"""Analyze this question step by step:
1. Identify what's being asked
2. Break down the problem into components
3. Apply relevant principles and knowledge
4. Evaluate each option systematically

Question:
{question_content}

Provide thorough reasoning, then conclude with "Answer: <letter>"."""

    response = execute_llm(prompt)
    return extract_answer(response)

def extract_answer(response):
    """Extract the final answer from LLM response"""
    logging.info(f"LLM response preview: {response[:200]}...")
    
    # Look for explicit answer format
    answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
    if answer_match:
        return answer_match.group(1).upper()
    
    # Look for "The answer is X" format
    answer_match = re.search(r'(?:the answer is|answer is)\s*([A-D])', response, re.IGNORECASE)
    if answer_match:
        return answer_match.group(1).upper()
    
    # Fallback: find the last A/B/C/D mentioned
    letters = re.findall(r'\b([A-D])\b', response)
    if letters:
        return letters[-1].upper()
    
    logging.error("Could not extract answer, defaulting to A")
    return "A"