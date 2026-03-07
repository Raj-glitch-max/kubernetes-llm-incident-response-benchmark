def score_rca_accuracy(llm_category: str, ground_truth: str) -> bool:
    """
    Compares LLM category to ground truth to determine RCA accuracy.
    
    Args:
        llm_category (str): Category predicted by the LLM.
        ground_truth (str): The actual category from chaos metadata.
        
    Returns:
        bool: True if categories match exactly.
    """
    pass

def score_hallucination(llm_evidence: list, input_data: dict) -> float:
    """
    Checks if the LLM cited something that was not present in the input logs/events.
    
    Args:
        llm_evidence (list): The list of citations from the LLM output.
        input_data (dict): The original input (pod_logs, describe_output, etc.).
        
    Returns:
        float: A hallucination penalty score (e.g., 0.0 means perfect, 1.0 means full hallucination).
    """
    pass

def score_latency(start_time: float, end_time: float) -> float:
    """
    Records and scores the response time of the LLM call.
    
    Args:
        start_time (float): The Unix timestamp right before the API call.
        end_time (float): The Unix timestamp right after the API returns.
        
    Returns:
        float: Total elapsed time in seconds.
    """
    pass

def score_remediation(suggested_commands: list) -> bool:
    """
    Checks if the suggested commands are valid, non-destructive kubectl commands.
    
    Args:
        suggested_commands (list): List of shell/kubectl commands suggested by the LLM.
        
    Returns:
        bool: True if commands are safe and syntactically valid.
    """
    pass
