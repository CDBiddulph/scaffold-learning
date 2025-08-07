#!/usr/bin/env python
"""Reward model API server for running on compute nodes with GPU."""

import argparse
import logging
from flask import Flask, request, jsonify
from scaffold_learning.domains.reward_model.factory import create_reward_model

app = Flask(__name__)
model = None

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({'status': 'healthy', 'model': app.config.get('model_name')})

@app.route('/score', methods=['POST'])
def score():
    """Score a prompt-response pair."""
    try:
        data = request.json
        if not data or 'prompt' not in data or 'response' not in data:
            return jsonify({'error': 'Missing prompt or response'}), 400
        
        score = model.score(data['prompt'], data['response'])
        return jsonify({'score': score})
    except Exception as e:
        logging.error(f"Error scoring: {e}")
        return jsonify({'error': str(e)}), 500

def main():
    parser = argparse.ArgumentParser(description="Reward model API server")
    parser.add_argument(
        "--model",
        default="hf:OpenAssistant/reward-model-deberta-v3-large-v2",
        help="Reward model specification"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Port to run server on"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to"
    )
    args = parser.parse_args()
    
    global model
    print(f"Loading reward model: {args.model}")
    model = create_reward_model(args.model)
    print(f"Model loaded successfully")
    
    app.config['model_name'] = args.model
    print(f"Starting server on {args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=False)

if __name__ == "__main__":
    main()