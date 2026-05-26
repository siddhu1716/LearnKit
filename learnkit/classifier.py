import dspy
from pydantic import BaseModel
import json

class ClassificationOutput(BaseModel):
    task_type: str           # e.g. "contract_summarization"
    domains: dict[str, float]  # e.g. {"legal": 0.9, "finance": 0.3}
    complexity: str          # "low" | "medium" | "high"

class TaskClassificationSignature(dspy.Signature):
    """Classify the user's task into domain, task_type and complexity."""
    task = dspy.InputField(desc="The user's task description")
    classification: ClassificationOutput = dspy.OutputField(
        desc="Classified task information"
    )

class TaskClassifier(dspy.Module):
    """
    Multi-label domain classifier.
    DSPy Predict with typed output — single cheap LLM call per task.
    """

    def __init__(self):
        super().__init__()
        self.classify = dspy.Predict(TaskClassificationSignature)

    def forward(self, task: str) -> ClassificationOutput:
        result = self.classify(task=task)
        if isinstance(result.classification, ClassificationOutput):
            return result.classification
        elif isinstance(result.classification, dict):
            return ClassificationOutput(**result.classification)
        elif isinstance(result.classification, str):
            import json
            data = json.loads(result.classification.replace("'", '"'))
            return ClassificationOutput(**data)
        return result.classification

def classify_task(task: str, lm=None) -> ClassificationOutput:
    if lm is None:
        lm = dspy.LM("anthropic/claude-haiku-4-5-20251001")
    with dspy.context(lm=lm):
        classifier = TaskClassifier()
        return classifier(task=task)
