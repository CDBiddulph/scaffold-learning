import json
import sys
import os

# Add parent directory to path to import llm_executor
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def analyze_response_quality():
    """Analyze what makes responses better - acknowledgment, completeness, etc."""
    data_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "test.jsonl")
    
    acknowledgment_patterns = []
    completeness_patterns = []
    
    with open(data_file, 'r') as f:
        count = 0
        for line in f:
            data = json.loads(line)
            input_text = data["input"]
            correct_answer = data["scoring_data"]["correct_answer"]
            
            # Extract responses
            response_a_start = input_text.find("Response A:\n") + len("Response A:\n")
            response_a_end = input_text.find("\n\nResponse B:")
            response_b_start = input_text.find("Response B:\n") + len("Response B:\n")
            response_b_end = input_text.find("\n\nWhich response was preferred?")
            
            if response_a_start > 0 and response_a_end > 0:
                response_a = input_text[response_a_start:response_a_end].strip()
                response_b = input_text[response_b_start:response_b_end].strip()
                
                # Check for acknowledgment patterns
                acknowledgment_words = ["sure!", "of course!", "here's", "hello!", "yes,", "certainly!", "absolutely!"]
                
                a_has_ack = any(word in response_a.lower()[:50] for word in acknowledgment_words)
                b_has_ack = any(word in response_b.lower()[:50] for word in acknowledgment_words)
                
                if a_has_ack or b_has_ack:
                    acknowledgment_patterns.append({
                        "id": data["id"],
                        "a_has_ack": a_has_ack,
                        "b_has_ack": b_has_ack,
                        "correct": correct_answer,
                        "response_a_start": response_a[:100],
                        "response_b_start": response_b[:100]
                    })
            
            count += 1
            if count >= 1000:  # Analyze first 1000
                break
    
    print(f"Analyzed acknowledgment patterns in {len(acknowledgment_patterns)} cases\n")
    
    # Count when acknowledgment helps
    ack_helps = 0
    ack_hurts = 0
    
    for case in acknowledgment_patterns:
        # If A has acknowledgment and A is preferred, or B has ack and B is preferred
        if (case["a_has_ack"] and case["correct"] == "A") or (case["b_has_ack"] and case["correct"] == "B"):
            ack_helps += 1
        # If A has acknowledgment but B is preferred, or B has ack but A is preferred  
        elif (case["a_has_ack"] and case["correct"] == "B") or (case["b_has_ack"] and case["correct"] == "A"):
            ack_hurts += 1
    
    total_ack_cases = ack_helps + ack_hurts
    if total_ack_cases > 0:
        print(f"Acknowledgment analysis:")
        print(f"Cases where acknowledgment correlates with preference: {ack_helps}/{total_ack_cases} ({ack_helps/total_ack_cases*100:.1f}%)")
        print(f"Cases where acknowledgment doesn't help: {ack_hurts}/{total_ack_cases} ({ack_hurts/total_ack_cases*100:.1f}%)")
    
    # Show examples
    print(f"\nExamples where acknowledgment helped:")
    count = 0
    for case in acknowledgment_patterns:
        if ((case["a_has_ack"] and case["correct"] == "A") or (case["b_has_ack"] and case["correct"] == "B")) and count < 3:
            preferred = "A" if case["correct"] == "A" else "B"
            print(f"\nCase {case['id']} - Preferred: {preferred}")
            print(f"Response A start: {case['response_a_start']}")
            print(f"Response B start: {case['response_b_start']}")
            count += 1

def analyze_mathematical_responses():
    """Analyze mathematical/technical question patterns"""
    data_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "test.jsonl")
    
    math_cases = []
    
    with open(data_file, 'r') as f:
        count = 0
        for line in f:
            data = json.loads(line)
            input_text = data["input"]
            prompt = input_text.split('\n')[0].replace("Original prompt: ", "").lower()
            
            # Look for mathematical/technical patterns
            if any(word in prompt for word in ["probability", "calculate", "equation", "solve", "formula", "average"]):
                response_a_start = input_text.find("Response A:\n") + len("Response A:\n")
                response_a_end = input_text.find("\n\nResponse B:")
                response_b_start = input_text.find("Response B:\n") + len("Response B:\n")
                response_b_end = input_text.find("\n\nWhich response was preferred?")
                
                if response_a_start > 0 and response_a_end > 0:
                    response_a = input_text[response_a_start:response_a_end].strip()
                    response_b = input_text[response_b_start:response_b_end].strip()
                    
                    math_cases.append({
                        "id": data["id"],
                        "prompt": prompt[:100],
                        "len_a": len(response_a),
                        "len_b": len(response_b),
                        "correct": data["scoring_data"]["correct_answer"]
                    })
            
            count += 1
            if count >= 1000:
                break
    
    print(f"\n\nMathematical/Technical Questions Analysis ({len(math_cases)} cases):")
    
    if math_cases:
        longer_preferred = sum(1 for c in math_cases if 
                             (c["len_a"] > c["len_b"] and c["correct"] == "A") or 
                             (c["len_b"] > c["len_a"] and c["correct"] == "B"))
        shorter_preferred = sum(1 for c in math_cases if 
                              (c["len_a"] < c["len_b"] and c["correct"] == "A") or 
                              (c["len_b"] < c["len_a"] and c["correct"] == "B"))
        
        total = longer_preferred + shorter_preferred
        if total > 0:
            print(f"Longer response preferred: {longer_preferred}/{total} ({longer_preferred/total*100:.1f}%)")
            print(f"Shorter response preferred: {shorter_preferred}/{total} ({shorter_preferred/total*100:.1f}%)")

if __name__ == "__main__":
    analyze_response_quality()
    analyze_mathematical_responses()