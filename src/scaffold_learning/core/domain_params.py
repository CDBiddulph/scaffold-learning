"""Domain parameter parsing utilities."""

from typing import Dict, List


def parse_domain_params(domain_param_list: List[str]) -> Dict[str, str]:
    """Parse domain parameters from a list of key=value strings.

    Args:
        domain_param_list: List of strings in the format "key=value"

    Returns:
        Dictionary mapping parameter names to values

    Raises:
        ValueError: If any parameter string is not in the format "key=value"
    """
    domain_params = {}

    for param_str in domain_param_list:
        if "=" not in param_str:
            raise ValueError(
                f"Domain parameter must be in format 'key=value', got: {param_str}"
            )

        key, value = param_str.split("=", 1)  # Split on first = only
        domain_params[key] = value

    return domain_params
