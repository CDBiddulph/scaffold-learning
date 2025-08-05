import sys
import os

# Add parent directory to path to import llm_executor
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm_executor import execute_llm


def main():
    prompt = "What is your name?"
    response = execute_llm(prompt)
    print(f"Response: {response}")


if __name__ == "__main__":
    main()
