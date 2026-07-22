import json
import argparse
from os import listdir
from time import time
from tqdm import tqdm
from handler import request

parser = argparse.ArgumentParser(description='run catbotbench on an openrouter model')
parser.add_argument('-m', '--model', required=True)
parser.add_argument('-v', '--validation-model', default="google/gemma-4-31b-it")
parser.add_argument('-d', '--debug', action='store_true')
args = parser.parse_args()

log_filename = f"{(args.model).replace("/", "_").replace(":", "-")}.json"
if log_filename in listdir("eval"):
    if not input(f"seems like this model has already been processed into eval/{log_filename}.\nproceed? (y/n): ").lower() in ['1', 'y', 'yes']:
        exit(0)

def validate_answer(question: str, true_answer: str, model_answer: str):
    prompt = f"You are tasked to judge the answer to a question. Reply with a single word in uppercase - CORRECT or INCORRECT. No other answer will be accepted.\n**QUESTION:** {question}\n\n**TRUE ANSWER:** {true_answer}\n\n**SUBMITTED ANSWER:** {model_answer}"
    response, _ = request(prompt, args.validation_model)
    return response.lower().strip() == "correct"

with open("data.json", "r") as f:
    data = json.load(f)

start = time()
stats = {"version": 1, "score": 0, "cost": 0, "time": 0, "eval_model": args.model, "data": []}
for idx, row in enumerate(tqdm(data)):
    print(f"\nprocessing {idx+1}/{len(data)}:")
    question, true_answer = row['q'], row['a']

    try:
        model_answer, cost = request(question, args.model)
    except Exception as e:
        print("error sending request:", e)
        exit(0)
    if args.debug: print(model_answer)

    correct = validate_answer(question, true_answer, model_answer)
    if args.debug: print(f"result: {correct}")
    if correct: stats['score'] += 1

    stats['data'].append({
        "question": question,
        "response": model_answer,
        "correct": correct,
        "cost": cost
    })

stats['time'] = int(time() - start)
stats['cost'] = round(sum([i['cost'] for i in stats['data']]), 6)

with open(f"eval/{log_filename}", "w+", encoding="utf-8") as f:
    json.dump(stats, f, indent=4, ensure_ascii=False)