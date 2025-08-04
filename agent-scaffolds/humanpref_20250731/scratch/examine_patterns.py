import json
import sys
import os

# Add parent directory to path to import llm_executor
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def examine_specific_patterns():
    """Look at specific patterns in detail"""
    data_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "test.jsonl")
    
    short_b_preferred = []
    url_responses = []
    incorrect_answers = []
    
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
                
                # Short B preferred
                if len(response_b) < 200 and correct_answer == "B" and len(response_a) > 500:
                    short_b_preferred.append({
                        "prompt": input_text.split('\n')[0].replace("Original prompt: ", ""),
                        "len_a": len(response_a),
                        "len_b": len(response_b),
                        "response_b": response_b
                    })
                
                # URL responses
                if response_b.startswith("http") and "\n" not in response_b:
                    url_responses.append({
                        "prompt": input_text.split('\n')[0].replace("Original prompt: ", ""),
                        "response_b": response_b,
                        "correct": correct_answer
                    })
                
                # Cases where response contains incorrect/misleading info
                if "incorrect" in response_a.lower() or "incorrect" in response_b.lower():
                    incorrect_answers.append(data)
    
    print("=== SHORT B PREFERRED (B < 200 chars, A > 500 chars) ===")
    print(f"Found {len(short_b_preferred)} examples")
    for i, ex in enumerate(short_b_preferred[:5]):
        print(f"\nExample {i+1}:")
        print(f"Prompt: {ex['prompt'][:100]}...")
        print(f"Response A length: {ex['len_a']}")
        print(f"Response B length: {ex['len_b']}")
        print(f"Response B: {ex['response_b']}")
    
    print("\n\n=== URL-ONLY RESPONSES ===")
    print(f"Found {len(url_responses)} examples")
    for ex in url_responses[:5]:
        print(f"\nPrompt: {ex['prompt'][:100]}...")
        print(f"Response B: {ex['response_b']}")
        print(f"Correct answer: {ex['correct']}")

examine_specific_patterns()