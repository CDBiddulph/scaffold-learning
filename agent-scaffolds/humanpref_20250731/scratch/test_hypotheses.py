import json
import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Add parent directory to path to import llm_executor
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm_executor import execute_llm

def test_conciseness_hypothesis():
    """Test if conciseness is a major factor in preference"""
    data_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "test.jsonl")
    
    test_cases = []
    
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
                
                len_a = len(response_a)
                len_b = len(response_b)
                
                # Test cases where there's significant length difference
                if abs(len_a - len_b) > 300:
                    test_cases.append({
                        "id": data["id"],
                        "prompt": input_text.split('\n')[0].replace("Original prompt: ", ""),
                        "len_a": len_a,
                        "len_b": len_b,
                        "shorter": "A" if len_a < len_b else "B",
                        "correct": correct_answer,
                        "response_a": response_a[:100],
                        "response_b": response_b[:100]
                    })
            
            if len(test_cases) >= 100:  # Analyze first 100 cases
                break
    
    # Analyze results
    shorter_preferred = 0
    longer_preferred = 0
    
    for case in test_cases:
        if case["shorter"] == case["correct"]:
            shorter_preferred += 1
        else:
            longer_preferred += 1
    
    print(f"Conciseness Hypothesis Test (n={len(test_cases)}):")
    print(f"Shorter response preferred: {shorter_preferred} ({shorter_preferred/len(test_cases)*100:.1f}%)")
    print(f"Longer response preferred: {longer_preferred} ({longer_preferred/len(test_cases)*100:.1f}%)")
    
    # Look at specific patterns
    print("\nExamples where shorter was preferred:")
    count = 0
    for case in test_cases:
        if case["shorter"] == case["correct"] and count < 3:
            print(f"\nPrompt: {case['prompt'][:80]}...")
            print(f"Length A: {case['len_a']}, Length B: {case['len_b']}")
            print(f"Preferred: {case['correct']} (shorter)")
            count += 1

def test_specific_patterns():
    """Test specific patterns like conversational queries"""
    data_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "test.jsonl")
    
    conversational_cases = []
    
    with open(data_file, 'r') as f:
        for line in f:
            data = json.loads(line)
            input_text = data["input"]
            prompt = input_text.split('\n')[0].replace("Original prompt: ", "").lower()
            
            # Look for conversational patterns
            conv_keywords = ["can i", "hello", "speak to", "help me", "thank", "please"]
            if any(kw in prompt for kw in conv_keywords):
                conversational_cases.append(data)
            
            if len(conversational_cases) >= 50:
                break
    
    print(f"\nConversational Pattern Analysis (n={len(conversational_cases)}):")
    
    # Test with LLM
    prompt_template = """Analyze these two responses to determine which is better for a conversational query.

The user asked a conversational question expecting helpful interaction.

Response A: {response_a}

Response B: {response_b}

Which response is more appropriate for someone seeking conversational help? Consider:
1. Does it acknowledge the human behind the question?
2. Is it appropriately helpful without being overly formal or verbose?
3. Does it match the conversational tone?

Answer with just "A" or "B"."""
    
    correct_predictions = 0
    
    # Test on a sample
    for i, case in enumerate(conversational_cases[:10]):
        input_text = case["input"]
        correct = case["scoring_data"]["correct_answer"]
        
        # Extract responses
        response_a_start = input_text.find("Response A:\n") + len("Response A:\n")
        response_a_end = input_text.find("\n\nResponse B:")
        response_b_start = input_text.find("Response B:\n") + len("Response B:\n")
        response_b_end = input_text.find("\n\nWhich response was preferred?")
        
        if response_a_start > 0 and response_a_end > 0:
            response_a = input_text[response_a_start:response_a_end].strip()
            response_b = input_text[response_b_start:response_b_end].strip()
            
            prompt = prompt_template.format(response_a=response_a[:300], response_b=response_b[:300])
            
            try:
                result = execute_llm(prompt)
                prediction = "A" if "A" in result.upper() else "B"
                
                if prediction == correct:
                    correct_predictions += 1
                    
                print(f"Case {i+1}: Predicted {prediction}, Actual {correct} {'✓' if prediction == correct else '✗'}")
            except:
                print(f"Case {i+1}: Error in LLM call")
    
    print(f"\nConversational pattern accuracy: {correct_predictions}/10 ({correct_predictions*10}%)")

if __name__ == "__main__":
    print("Testing hypotheses...\n")
    test_conciseness_hypothesis()
    print("\n" + "="*50 + "\n")
    test_specific_patterns()