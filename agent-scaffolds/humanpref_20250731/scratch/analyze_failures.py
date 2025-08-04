import json
import sys
import os

# Add parent directory to path to import llm_executor
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def analyze_failures():
    """Look at specific failed examples"""
    data_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "test.jsonl")
    
    # Failed IDs from the test run
    failed_ids = [2810566307, 1002017720, 855729587]
    
    with open(data_file, 'r') as f:
        for line in f:
            data = json.loads(line)
            if data["id"] in failed_ids:
                print(f"\n{'='*80}")
                print(f"ID: {data['id']}")
                print(f"Correct answer: {data['scoring_data']['correct_answer']}")
                
                input_text = data["input"]
                
                # Extract prompt
                prompt_line = input_text.split('\n')[0]
                print(f"Prompt: {prompt_line}")
                
                # Extract responses
                response_a_start = input_text.find("Response A:\n") + len("Response A:\n")
                response_a_end = input_text.find("\n\nResponse B:")
                response_b_start = input_text.find("Response B:\n") + len("Response B:\n")
                response_b_end = input_text.find("\n\nWhich response was preferred?")
                
                if response_a_start > 0 and response_a_end > 0:
                    response_a = input_text[response_a_start:response_a_end].strip()
                    response_b = input_text[response_b_start:response_b_end].strip()
                    
                    print(f"\nResponse A length: {len(response_a)}")
                    print(f"Response A preview: {response_a[:200]}...")
                    
                    print(f"\nResponse B length: {len(response_b)}")
                    print(f"Response B preview: {response_b[:200]}...")
                    
                    # Check for our detection patterns
                    if response_b.startswith("http") and "\n" not in response_b:
                        print("\n** Response B is URL-only **")
                    
                    unhelpful_phrases = ["i'm not able to help", "i cannot", "as an ai"]
                    for phrase in unhelpful_phrases:
                        if phrase in response_a.lower():
                            print(f"\n** Response A contains unhelpful phrase: {phrase} **")
                        if phrase in response_b.lower():
                            print(f"\n** Response B contains unhelpful phrase: {phrase} **")

if __name__ == "__main__":
    analyze_failures()