import json
import sys
import os

# Add parent directory to path to import llm_executor
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def analyze_summary_requests():
    """Analyze cases where users ask for brief summaries"""
    data_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "test.jsonl")
    
    summary_cases = []
    
    with open(data_file, 'r') as f:
        for line in f:
            data = json.loads(line)
            input_text = data["input"]
            prompt = input_text.split('\n')[0].replace("Original prompt: ", "").lower()
            
            # Look for summary/brief requests
            if any(phrase in prompt for phrase in ["one sentence", "briefly", "in short", "summarize", "one line"]):
                # Extract responses
                response_a_start = input_text.find("Response A:\n") + len("Response A:\n")
                response_a_end = input_text.find("\n\nResponse B:")
                response_b_start = input_text.find("Response B:\n") + len("Response B:\n")
                response_b_end = input_text.find("\n\nWhich response was preferred?")
                
                if response_a_start > 0 and response_a_end > 0:
                    response_a = input_text[response_a_start:response_a_end].strip()
                    response_b = input_text[response_b_start:response_b_end].strip()
                    
                    summary_cases.append({
                        "id": data["id"],
                        "prompt": prompt,
                        "len_a": len(response_a),
                        "len_b": len(response_b),
                        "correct": data["scoring_data"]["correct_answer"],
                        "response_a": response_a[:300],
                        "response_b": response_b[:300],
                        "shorter": "A" if len(response_a) < len(response_b) else "B"
                    })
    
    print(f"Found {len(summary_cases)} cases requesting brief/summary responses\n")
    
    # Analyze preference patterns
    shorter_preferred = sum(1 for c in summary_cases if c["shorter"] == c["correct"])
    longer_preferred = sum(1 for c in summary_cases if c["shorter"] != c["correct"])
    
    print(f"When brevity is requested:")
    print(f"Shorter response preferred: {shorter_preferred}/{len(summary_cases)} ({shorter_preferred/len(summary_cases)*100:.1f}%)")
    print(f"Longer response preferred: {longer_preferred}/{len(summary_cases)} ({longer_preferred/len(summary_cases)*100:.1f}%)")
    
    # Look at specific patterns
    print("\nExamples where LONGER was preferred despite brevity request:")
    count = 0
    for case in summary_cases:
        if case["shorter"] != case["correct"] and count < 5:
            print(f"\n{'='*60}")
            print(f"ID: {case['id']}")
            print(f"Prompt: {case['prompt']}")
            print(f"Length A: {case['len_a']}, Length B: {case['len_b']}")
            print(f"Preferred: {case['correct']} (the {'longer' if case['correct'] != case['shorter'] else 'shorter'} one)")
            print(f"\nResponse A: {case['response_a']}")
            print(f"\nResponse B: {case['response_b']}")
            count += 1

if __name__ == "__main__":
    analyze_summary_requests()