import json
import sys
import os
from concurrent.futures import ThreadPoolExecutor
import re

# Add parent directory to path to import llm_executor
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm_executor import execute_llm

def analyze_quality_factors():
    """Analyze what quality factors distinguish preferred responses"""
    data_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "test.jsonl")
    
    patterns = {
        "url_only_b": [],
        "incomplete_response": [],
        "direct_helpful": [],
        "overexplained": [],
        "factual_error": []
    }
    
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
                prompt = input_text.split('\n')[0].replace("Original prompt: ", "")
                
                # URL only in B
                if response_b.startswith("http") and len(response_b.split('\n')) == 1:
                    patterns["url_only_b"].append({
                        "prompt": prompt,
                        "correct": correct_answer,
                        "url": response_b
                    })
                
                # Check for incomplete/unhelpful responses
                unhelpful_phrases = [
                    "I'm not able to help with that",
                    "I cannot",
                    "I don't have access",
                    "As an AI",
                    "I'm just a language model"
                ]
                
                for phrase in unhelpful_phrases:
                    if phrase.lower() in response_a.lower():
                        patterns["incomplete_response"].append({
                            "prompt": prompt,
                            "correct": correct_answer,
                            "response": "A",
                            "text": response_a[:200]
                        })
                    if phrase.lower() in response_b.lower():
                        patterns["incomplete_response"].append({
                            "prompt": prompt,
                            "correct": correct_answer,
                            "response": "B",
                            "text": response_b[:200]
                        })
                
            count += 1
            if count >= 500:  # Analyze first 500
                break
    
    # Print findings
    print("Quality Factor Analysis:\n")
    
    print(f"URL-only Response B: {len(patterns['url_only_b'])} cases")
    if patterns['url_only_b']:
        correct_a = sum(1 for p in patterns['url_only_b'] if p['correct'] == 'A')
        print(f"  - A preferred: {correct_a}/{len(patterns['url_only_b'])} ({correct_a/len(patterns['url_only_b'])*100:.0f}%)")
        print(f"  - Example: {patterns['url_only_b'][0]['prompt'][:80]}...")
    
    print(f"\nUnhelpful/Incomplete responses: {len(patterns['incomplete_response'])} cases")
    if patterns['incomplete_response']:
        # Count how often the unhelpful response was NOT preferred
        unhelpful_not_preferred = sum(1 for p in patterns['incomplete_response'] 
                                     if p['response'] != p['correct'])
        print(f"  - Unhelpful response NOT preferred: {unhelpful_not_preferred}/{len(patterns['incomplete_response'])} ({unhelpful_not_preferred/len(patterns['incomplete_response'])*100:.0f}%)")
        
        # Show examples
        for i, p in enumerate(patterns['incomplete_response'][:3]):
            print(f"\n  Example {i+1}:")
            print(f"  Prompt: {p['prompt'][:80]}...")
            print(f"  Unhelpful response: {p['response']}")
            print(f"  Preferred: {p['correct']}")
            print(f"  Text: {p['text']}")

def test_improved_criteria():
    """Test an improved evaluation approach"""
    test_cases = [
        {
            "input": """Original prompt: Can i speak to someone

Response A:
Yes, you can speak to someone through various methods of communication. Some common ways to contact individuals or organizations include:

1. **Phone**: Calling a customer support line or a specific contact number for a business or service provider.
2. **Email**: Sending an email to a specific address or using contact forms on websites.

Response B:
Of course! I'm here to help. What would you like to talk about or ask?

Which response was preferred? Write "Answer: A" or "Answer: B".""",
            "expected": "B"
        },
        {
            "input": """Original prompt: Write a screenplay to a Julia Child cooking show episode

Response A:
The episode begins with Julia introducing a new recipe for a classic French dish, Coq au Vin. As she progresses through the cooking process, small anomalies begin to appear...

Response B:
https://www.mythos.ai/creator

Which response was preferred? Write "Answer: A" or "Answer: B".""",
            "expected": "A"
        }
    ]
    
    improved_prompt = """You are evaluating two responses to determine which one is better.

Key evaluation principles:
1. ACTUALLY ANSWERS THE QUESTION: The response must actually address what was asked
2. HELPFULNESS: Is the response useful to the person asking?
3. APPROPRIATENESS: Does the response match the context and tone needed?

Special considerations:
- If someone asks a conversational question (like "Can I speak to someone"), they want engagement, not a list of communication methods
- URL-only responses are rarely helpful unless specifically requested
- Responses that refuse to help ("I cannot...", "I don't have access...") are generally not preferred

{input}"""
    
    print("\n\nTesting improved evaluation criteria:")
    
    for i, test in enumerate(test_cases):
        prompt = improved_prompt.format(input=test["input"])
        result = execute_llm(prompt)
        
        # Extract answer
        if "ANSWER: B" in result.upper() or result.strip().upper().endswith("B"):
            prediction = "B"
        else:
            prediction = "A"
            
        print(f"\nTest case {i+1}:")
        print(f"Expected: {test['expected']}, Predicted: {prediction}")
        print(f"Correct: {'✓' if prediction == test['expected'] else '✗'}")

if __name__ == "__main__":
    analyze_quality_factors()
    test_improved_criteria()