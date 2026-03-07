import re

def score_rca_accuracy(llm_category: str, ground_truth: str) -> bool:
    """
    Compares LLM category to ground truth to determine RCA accuracy.
    
    Args:
        llm_category (str): Category predicted by the LLM.
        ground_truth (str): The actual category from chaos metadata.
        
    Returns:
        bool: True if categories match exactly.
    """
    return llm_category.strip().lower() == ground_truth.strip().lower()

def score_hallucination(llm_evidence: list, input_data: dict) -> float:
    """
    Checks if the LLM cited something that was not present in the input logs/events.
    
    Args:
        llm_evidence (list): The list of citations from the LLM output.
        input_data (dict): The original input (pod_logs, describe_output, etc.).
        
    Returns:
        float: A hallucination penalty score (0.0 means perfect, 1.0 means full hallucination).
    """
    if not llm_evidence:
        return 0.0
    
    # Combine all input text into one massive haystack
    haystack = " ".join(str(v) for v in input_data.values()).lower()
    
    hallucinated_count = 0
    for evidence in llm_evidence:
        # Simple substring search. In a real scenario, this might need fuzzy matching
        # if the LLM paraphrases the evidence slightly.
        if evidence.lower() not in haystack:
            hallucinated_count += 1
            
    return float(hallucinated_count) / len(llm_evidence)

def score_latency(start_time: float, end_time: float) -> float:
    """
    Records and scores the response time of the LLM call.
    
    Args:
        start_time (float): The Unix timestamp right before the API call.
        end_time (float): The Unix timestamp right after the API returns.
        
    Returns:
        float: Total elapsed time in seconds.
    """
    return end_time - start_time

def score_remediation(suggested_commands: list) -> bool:
    """
    Checks if the suggested commands are valid, non-destructive kubectl commands.
    
    Args:
        suggested_commands (list): List of shell/kubectl commands suggested by the LLM.
        
    Returns:
        bool: True if commands are safe and syntactically valid.
    """
    if not suggested_commands:
        return False
        
    destructive_patterns = [
        r"rm\s+-rf",
        r"delete\s+namespace",
        r"delete\s+node",
        r"kubectl\s+delete\s+cluster",
        r">\s*/dev/null"
    ]
    
    is_valid = True
    for cmd in suggested_commands:
        cmd_lower = cmd.lower().strip()
        # Must be a kubectl or related diagnostic command
        if not (cmd_lower.startswith("kubectl") or cmd_lower.startswith("helm") or cmd_lower.startswith("aws eks")):
            is_valid = False
            break
            
        # Must not contain destructive payload
        for pattern in destructive_patterns:
            if re.search(pattern, cmd_lower):
                is_valid = False
                break
                
        if not is_valid:
            break
            
    return is_valid
