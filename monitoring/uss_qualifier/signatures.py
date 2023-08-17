import hashlib
import json
from typing import Union


def compute_baseline_signature(
    codebase_version: str, commit_hash: str, config_signature: str
) -> str:
    """Compute a signature uniquely identifying the test baseline being run.

    Args:
        codebase_version: Name and source of codebase being used (e.g., interuss/monitoring/v0.2.0)
        commit_hash: Full git commit hash of the codebase being used
        config_signature: Signature of configuration (minus any non-baseline content)

    Returns: Signature uniquely identifying the test baseline, according to provided parameters.
    """
    return compute_signature(
        codebase_version + "\n" + commit_hash + "\n" + config_signature
    )


def compute_signature(obj: Union[dict, list, str]) -> str:
    """Compute a hash/signature of the content of the dict object."""
    if isinstance(obj, str):
        sig = hashlib.sha256()
        sig.update(obj.encode("utf-8"))
        return sig.hexdigest()
    elif isinstance(obj, dict) or isinstance(obj, list):
        return compute_signature(json.dumps(obj, sort_keys=True))
    else:
        raise ValueError(f"Cannot compute signature for {type(obj).__name__} type")
