"""Utilities for parsing domain parameters."""

from typing import Dict, List, Tuple


def parse_domain_param(param_str: str) -> Tuple[str, str]:
    """Parse a domain parameter string in key=value format.
    
    Args:
        param_str: Domain parameter string like "rm=hf:model_name"
        
    Returns:
        Tuple of (key, value)
        
    Raises:
        ValueError: If parameter format is invalid
    """
    if "=" not in param_str:
        raise ValueError(f"Invalid domain parameter format: {param_str}. Expected key=value")
    
    key, value = param_str.split("=", 1)
    return key, value


def parse_domain_params(param_list: List[str]) -> Dict[str, str]:
    """Parse a list of domain parameter strings.
    
    Args:
        param_list: List of domain parameter strings
        
    Returns:
        Dictionary of parsed parameters
        
    Raises:
        ValueError: If any parameter format is invalid
    """
    domain_params = {}
    for param_str in param_list:
        key, value = parse_domain_param(param_str)
        domain_params[key] = value
    return domain_params