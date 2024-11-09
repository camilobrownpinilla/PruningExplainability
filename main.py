import os
import torch
import matplotlib.pyplot as plt
from tqdm import tqdm
from transformers import AutoModelForSequenceClassification

from explainers.explanation_methods import SHAP, LIME, IG
from evaluations.evaluator import Evaluator


def eval_models(path, tokenizer, explainers, test_set, device, ptg=0.05):
    """
    For each model in `path`, evaluates infidelity of each explainer on `test_set`.
    For each explainer, creates and saves a bar chart of infidelity scores for each model.

    params:
        path: path to directory of models, e.g. './ckpts'
        tokenizer: tokenizer used in training models at `path`
        explainers: list of explainers, e.g. [SHAP, LIME, IG]
        test_set: test set to evaluate explainability on
        device: device to evaluate models on
        ptg: percentage of test_set to evaluate on, default 5%
    """
    # Load in models contained in `path`
    print(f"Loading models from {path}")
    models, arch = load_latest_checkpoints(path)

    print(f"Creating evaluators for explanations of {arch} models...")
    evaluators_dict = {}
    for explainer in explainers:
        evaluators_dict[explainer.__name__] = {}
        for name, model in models.items():
            evaluator = Evaluator(explainer(model, tokenizer, device))
            evaluators_dict[explainer.__name__][name] = evaluator

    for exp, evaluators in evaluators_dict.items():
        print(f'Evaluating infidelity of {exp} explanations...')
        infidelities = {}
        for model, eval in evaluators.items():
            infid = eval.evaluate_infidelity_mask_top_k(
                test_set, k=1, ptg=ptg)
            print(f"Infidelity of {exp} explanations of {model} model: {infid}")
            infidelities[model] = infid

        # Create bar chart
        plt.bar(range(len(infidelities)), infidelities.values())
        plt.xticks(range(len(infidelities)), infidelities.keys())
        plt.xlabel('Model')
        plt.ylabel('Infidelity')
        plt.title(f'Infidelity of {exp} Explanations for Differently Pruned Versions of {arch}')
        
        # Save bar chart
        save_path = f'results/figs/{exp}_topk_{arch}'
        ext = '.png'

        # Ensure unique filename
        file_path = save_path + ext
        counter = 1
        while os.path.exists(file_path):
            file_path = f'{save_path}_{counter}{ext}'
            counter += 1

        plt.savefig(file_path, format='png', dpi=300)
        print(f"Chart saved to {file_path}")


def load_latest_checkpoints(path):
    """
    Returns models loaded from their latest checkpoint in the subdirs of `path`.
    
    E.g. if path = './ckpts', we load models from:
        ./ckpts/base, ./ckpts/smaller, ./ckpts/pruning_method_name

    params:
        path: path to directory of models, e.g. './ckpts'

    returns:
        models : dict, e.g. models['l1unstruct'] = model
        arch : architecture of models in `path`, e.g. BertForSequenceClassification
    """
    models = {}
    arch = None
    
    # Check if the path exists and is a directory
    if not os.path.isdir(path):
        raise FileNotFoundError(f"The directory '{path}' does not exist or is not a directory.")
        
    # Iterate over each subdirectory in path
    for model_dir in os.listdir(path):
        model_path = os.path.join(path, model_dir)

        # Check if it's a directory
        if os.path.isdir(model_path):
            # List all checkpoint files in the subdirectory
            checkpoints = sorted(
                [os.path.join(model_path, checkpoint)
                 for checkpoint in os.listdir(model_path)],
                key=os.path.getmtime,
                reverse=True  # Sort by modification time, newest first
            )

            # Load the latest checkpoint
            if checkpoints:
                latest_checkpoint = checkpoints[0]
                model = AutoModelForSequenceClassification.from_pretrained(
                    latest_checkpoint)
                models[model_dir] = model
                print(f"Loaded {model_path}/{latest_checkpoint}")
                # Get name of model architecture
                if not arch:
                    arch = model.__class__.__name__

    return models, arch


if __name__ == '__main__':
    path = './ckpts'
    tokenizer = None # TODO
    explainers = [SHAP]
    test_set = None # TODO
    device = torch.device('cpu')
    
    eval_models(path, tokenizer, explainers, test_set, device)