import json
import sys
import os

# Add parent directory to path to import llm_executor
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def analyze_response_types():
    """Analyze different types of responses to identify patterns"""
    data_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "test.jsonl")
    
    # Categories we'll look for
    categories = {
        "very_short_b": [],  # Response B is very short
        "url_only": [],      # Response contains only URL
        "code_related": [],  # Programming/technical questions
        "factual": [],       # Questions about facts
        "creative": [],      # Creative writing tasks
        "advice": [],        # Asking for advice
        "conversation": []   # Conversational responses
    }
    
    with open(data_file, 'r') as f:
        for line in f:
            data = json.loads(line)
            input_text = data["input"]
            correct_answer = data["scoring_data"]["correct_answer"]
            
            # Extract responses
            response_a_start = input_text.find("Response A:\n") + len("Response A:\n")
            response_a_end = input_text.find("\n\nResponse B:")
            response_b_start = input_text.find("Response B:\n") + len("Response B:\n")
            response_b_end = input_text.find("\n\nWhich response was preferred?")
            
            if response_a_start > 0 and response_a_end > 0 and response_b_start > 0 and response_b_end > 0:
                response_a = input_text[response_a_start:response_a_end].strip()
                response_b = input_text[response_b_start:response_b_end].strip()
                
                # Check for very short response B
                if len(response_b) < 100 and correct_answer == "B":
                    categories["very_short_b"].append(data)
                
                # Check for URL-only responses
                if (response_a.startswith("http") and "\n" not in response_a) or \
                   (response_b.startswith("http") and "\n" not in response_b):
                    categories["url_only"].append(data)
                
                # Check for code-related
                if "```" in input_text or "code" in input_text.lower() or "function" in input_text:
                    categories["code_related"].append(data)
                
                # Check for conversational
                if "speak to someone" in input_text.lower() or "hello" in input_text.lower():
                    categories["conversation"].append(data)
    
    # Print findings
    print("Category Analysis:")
    for cat, items in categories.items():
        if items:
            print(f"\n{cat}: {len(items)} examples")
            # Look at first example
            if items:
                ex = items[0]
                print(f"Example - Correct: {ex['scoring_data']['correct_answer']}")
                print(f"Input preview: {ex['input'][:200]}...")

analyze_response_types()