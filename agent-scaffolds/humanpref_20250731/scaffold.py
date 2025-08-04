import logging
import time
from llm_executor import execute_llm


def detect_response_issues(response_a, response_b):
    """Detect specific issues that affect preference"""
    issues = {"a": [], "b": []}
    
    # Check for URL-only responses
    if response_a.strip().startswith("http") and "\n" not in response_a.strip():
        issues["a"].append("url_only")
    if response_b.strip().startswith("http") and "\n" not in response_b.strip():
        issues["b"].append("url_only")
    
    # Check for unhelpful/refusal responses
    unhelpful_phrases = [
        "i'm not able to help",
        "i cannot",
        "i don't have access",
        "as an ai",
        "i'm just a language model",
        "i cannot provide",
        "i cannot fulfill",
        "it's not appropriate",
        "i strongly oppose"
    ]
    
    response_a_lower = response_a.lower()
    response_b_lower = response_b.lower()
    
    for phrase in unhelpful_phrases:
        if phrase in response_a_lower:
            issues["a"].append("unhelpful")
            break
    
    for phrase in unhelpful_phrases:
        if phrase in response_b_lower:
            issues["b"].append("unhelpful")
            break
    
    return issues


def detect_conversational_context(prompt):
    """Detect if this is a conversational query"""
    prompt_lower = prompt.lower()
    conversational_indicators = [
        "can i speak",
        "hello",
        "hi ",
        "talk to someone",
        "help me",
        "can you",
        "could you"
    ]
    
    return any(indicator in prompt_lower for indicator in conversational_indicators)


def evaluate_responses(input_string: str):
    """Use LLM to evaluate which response is better"""
    
    # Extract prompt and responses
    lines = input_string.split('\n')
    prompt = ""
    response_a = ""
    response_b = ""
    
    for i, line in enumerate(lines):
        if line.startswith("Original prompt:"):
            prompt = line.replace("Original prompt:", "").strip()
        elif line.startswith("Response A:"):
            # Find Response A content
            j = i + 1
            while j < len(lines) and not lines[j].startswith("Response B:"):
                response_a += lines[j] + "\n"
                j += 1
            response_a = response_a.strip()
        elif line.startswith("Response B:"):
            # Find Response B content
            j = i + 1
            while j < len(lines) and not lines[j].startswith("Which response"):
                response_b += lines[j] + "\n"
                j += 1
            response_b = response_b.strip()
    
    # Detect specific issues
    issues = detect_response_issues(response_a, response_b)
    is_conversational = detect_conversational_context(prompt)
    
    # Build evaluation prompt with context-specific guidance
    evaluation_prompt = f"""You are evaluating two responses to determine which one is better.

CRITICAL EVALUATION RULES:
1. The response MUST actually answer what was asked
2. URL-only responses are almost NEVER helpful unless URLs were specifically requested
3. Responses that refuse to help or say "I cannot" are generally NOT preferred
4. For conversational queries, prefer responses that engage naturally"""
    
    if is_conversational:
        evaluation_prompt += "\n5. This appears to be a CONVERSATIONAL query - the user wants natural engagement, not formal lists"
    
    if "url_only" in issues["a"]:
        evaluation_prompt += "\n\nWARNING: Response A is just a URL with no explanation"
    if "url_only" in issues["b"]:
        evaluation_prompt += "\n\nWARNING: Response B is just a URL with no explanation"
    
    if "unhelpful" in issues["a"]:
        evaluation_prompt += "\n\nNOTE: Response A contains refusal/unhelpful language"
    if "unhelpful" in issues["b"]:
        evaluation_prompt += "\n\nNOTE: Response B contains refusal/unhelpful language"
    
    evaluation_prompt += f"""

Evaluation criteria in order:
1. ACTUALLY ANSWERS THE QUESTION
2. HELPFULNESS to the person asking
3. APPROPRIATENESS for the context
4. COMPLETENESS without being excessive
5. CLARITY and organization

{input_string}"""

    try:
        result = execute_llm(evaluation_prompt)
        result = result.strip().upper()

        # Extract final answer - try multiple patterns
        if result.endswith("B"):
            return "B"
        elif result.endswith("A"):
            return "A"
        elif "ANSWER: B" in result:
            return "B"
        elif "ANSWER: A" in result:
            return "A"
        elif result.startswith("B"):
            return "B"
        elif result.startswith("A"):
            return "A"
        elif "B" in result and "A" not in result:
            return "B"
        elif "A" in result and "B" not in result:
            return "A"

        logging.warning(f"LLM returned unexpected result: {result}")
        
        # Fallback heuristics based on detected issues
        if "url_only" in issues["b"] and "url_only" not in issues["a"]:
            return "A"
        elif "url_only" in issues["a"] and "url_only" not in issues["b"]:
            return "B"
        elif "unhelpful" in issues["b"] and "unhelpful" not in issues["a"]:
            return "A"
        elif "unhelpful" in issues["a"] and "unhelpful" not in issues["b"]:
            return "B"
        
        return "A"  # Default fallback

    except Exception as e:
        logging.error(f"Error in LLM evaluation: {e}")
        
        # Use heuristics as fallback
        if "url_only" in issues["b"]:
            return "A"
        elif "unhelpful" in issues["b"]:
            return "A"
        
        return "A"  # Default fallback


def process_input(input_string: str) -> str:
    try:
        # Evaluate which response is better
        result = evaluate_responses(input_string)

        logging.info(f"Evaluation result: {result}")
        return result

    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return "A"  # Default fallback