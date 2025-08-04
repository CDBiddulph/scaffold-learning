import json
import sys
import os

# Add parent directory to path to import llm_executor
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def analyze_data():
    """Analyze the test data to understand patterns"""
    data_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "test.jsonl")
    
    total_count = 0
    a_count = 0
    b_count = 0
    
    # Store examples for detailed analysis
    examples = []
    
    with open(data_file, 'r') as f:
        for line in f:
            data = json.loads(line)
            total_count += 1
            
            correct_answer = data["scoring_data"]["correct_answer"]
            if correct_answer == "A":
                a_count += 1
            else:
                b_count += 1
                
            examples.append({
                "id": data["id"],
                "input": data["input"],
                "correct": correct_answer
            })
    
    print(f"Total examples: {total_count}")
    print(f"A answers: {a_count} ({a_count/total_count*100:.1f}%)")
    print(f"B answers: {b_count} ({b_count/total_count*100:.1f}%)")
    
    # Look at first 5 examples in detail
    print("\nFirst 5 examples:")
    for i, ex in enumerate(examples[:5]):
        print(f"\n--- Example {i+1} ---")
        print(f"Correct answer: {ex['correct']}")
        # Extract prompt from input
        lines = ex['input'].split('\n')
        for j, line in enumerate(lines):
            if line.startswith("Original prompt:"):
                print(f"Prompt: {line}")
                break
                
    return examples

if __name__ == "__main__":
    analyze_data()