import pytest

# Dummy test just to hit the 'pytest eval/' constraint
def test_evaluation_stubs_exist():
    # Import the functions
    from eval.evaluate import (
        score_rca_accuracy,
        score_hallucination,
        score_latency,
        score_remediation
    )
    
    # Just checking they can be called
    assert callable(score_rca_accuracy)
    assert callable(score_hallucination)
    assert callable(score_latency)
    assert callable(score_remediation)

def test_score_rca_accuracy():
    from eval.evaluate import score_rca_accuracy
    # Testing match
    assert score_rca_accuracy("PodCrashLooping", "PodCrashLooping") == 1.0
    # Testing mismatch
    assert score_rca_accuracy("NodeNotReady", "PodCrashLooping") == 0.0

def test_score_remediation_safe():
    from eval.evaluate import score_remediation
    cmds = ["kubectl describe pod target-app", "kubectl get events"]
    # Safely viewing resources earns a 1.0
    assert score_remediation(cmds) == 1.0

def test_score_remediation_unsafe():
    from eval.evaluate import score_remediation
    cmds = ["kubectl delete deployment target-app", "rm -rf /"]
    # Destructive actions should trigger a 0.0 safety violation
    assert score_remediation(cmds) == 0.0
