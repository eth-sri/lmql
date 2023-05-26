
try:
    from datasets import load_dataset
    from collections import namedtuple
except:
    raise Exception("Please install the 'datasets' library to use LMQL's dataset loading functionality. You can do this by running 'pip install datasets'.")

from dataclasses import dataclass

global dataset_cache
dataset_cache = {}

def cache(file):
    import pickle
    import os

    if len(dataset_cache) == 0:
        if os.path.exists(file):
            with open(file, "rb") as f:
                dataset_cache.update(pickle.load(f))
    else:
        with open(file, "wb") as f:
            pickle.dump(dataset_cache, f)

GMS8KSample = namedtuple("GMS8KSample", ["question", "answer", "result"])

def gsm8k(n: int, split="test"):
    global dataset_cache
    
    if "gsm8k" not in dataset_cache.keys():
        dataset = load_dataset("gsm8k", "main")
        dataset_cache["gsm8k"] = dataset
    else:
        dataset = dataset_cache["gsm8k"]
    s = dataset[split][n]

    question = s["question"]
    answer = s["answer"]
    result = int(answer.split("####", 1)[1].strip())

    return GMS8KSample(question, answer, result)

def algebra(n: int):
    import pandas as pd
    import os

    df = pd.read_csv(os.path.join(os.path.dirname(__file__), "algebra222.csv"))

    questions = df["question"].tolist()[n]
    answers = df["final_answer"].tolist()[n]

    return GMS8KSample(questions, answers, int(answers))


def gsmhard(n: int, split="train"):
    global dataset_cache
    if "gsm-hard" not in dataset_cache.keys():
        dataset = load_dataset("reasoning-machines/gsm-hard", "main")
        dataset_cache["gsm-hard"] = dataset
    else:
        dataset = dataset_cache["gsm-hard"]

    s = dataset[split][n]

    question = s["input"]
    answer = s["target"]
    result = int(answer)

    return GMS8KSample(question, answer, result)

@dataclass
class MultipleChoiceSample:
    question: str
    choices: list[str]
    result: str
    choices_line: str

    def __hash__(self):
        return hash((self.question, tuple(self.choices), self.result, self.choices_line))

@dataclass
class DirectPredictionSample:
    question: str
    result: str

    def __hash__(self):
        return hash((self.question, tuple(self.result)))

def trackingshuffledobjects(n: int, variant="five_objects"):
    # first make sure ~/.cache/lmql/datasets/shuffled_objects.json exists otherwise load from https://raw.githubusercontent.com/google/BIG-bench/main/bigbench/benchmark_tasks/tracking_shuffled_objects/three_objects/task.json
    import os
    import json
    import requests

    path = os.path.join(os.path.expanduser("~"), ".cache", "lmql", "datasets", "shuffled_objects" + variant + ".json")

    if not os.path.exists(path):
        os.makedirs(os.path.join(os.path.expanduser("~"), ".cache", "lmql", "datasets"), exist_ok=True)

        url = f"https://raw.githubusercontent.com/google/BIG-bench/main/bigbench/benchmark_tasks/tracking_shuffled_objects/{variant}/task.json"
        os.system(f"curl {url} > {path}")
        assert os.path.exists(path)

    with open(path, "r") as f:
        data = json.load(f)

    # print(data.keys())
    s = data["examples"][n]

    choices = list(s["target_scores"].items())
    answer_choices = [x[0].rstrip(".") for x in choices]
    answer = [x[0] for x in choices if x[1] == max([x[1] for x in choices])][0]
    choices_line = "Answer Choices: " + ", ".join(answer_choices)
    
    return MultipleChoiceSample(s["input"], answer_choices, answer, choices_line)

def fever(n: int):
    import os
    import json
    import requests

    path = os.path.join(os.path.expanduser("~"), ".cache", "lmql", "datasets", "fever.json")

    if not os.path.exists(path):
        os.makedirs(os.path.join(os.path.expanduser("~"), ".cache", "lmql", "datasets"), exist_ok=True)

        url = f"https://raw.githubusercontent.com/google/BIG-bench/main/bigbench/benchmark_tasks/fact_checker/fever/task.json"
        os.system(f"curl {url} > {path}")
        assert os.path.exists(path)

    with open(path, "r") as f:
        data = json.load(f)

    # print(data.keys())
    s = data["examples"][n]

    choices = list(s["target_scores"].items())
    answer_choices = [x[0].rstrip(".") for x in choices]
    answer = [x[0] for x in choices if x[1] == max([x[1] for x in choices])][0]
    choices_line = "Answer Choices: " + ", ".join(answer_choices)
    
    return MultipleChoiceSample(s["input"], answer_choices, answer, choices_line)

def wikidata(n: int):
    import os
    import json
    import requests

    path = os.path.join(os.path.expanduser("~"), ".cache", "lmql", "datasets", "wikidata.json")

    if not os.path.exists(path):
        os.makedirs(os.path.join(os.path.expanduser("~"), ".cache", "lmql", "datasets"), exist_ok=True)

        url = f"https://raw.githubusercontent.com/google/BIG-bench/main/bigbench/benchmark_tasks/qa_wikidata/task.json"
        os.system(f"curl {url} > {path}")
        assert os.path.exists(path)

    with open(path, "r") as f:
        data = json.load(f)

    # print(data.keys())
    s = data["examples"][n]
    target = s["target"]
    
    return DirectPredictionSample(s["input"], target)

if __name__ == "__main__":
    print(wikidata(2))