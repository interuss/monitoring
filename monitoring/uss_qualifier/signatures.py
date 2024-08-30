import hashlib
import json
from typing import Union, Any


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


def _with_integer_zeros(obj: Any) -> Any:
    """Express the given object ensuring any zeros are always integers.

    When Python dumps the JSON of a structure, it differentiates between integer zeros (represented just `0`) and float
    zeros (represented `0.0`).  We do not want to encode the data type of polymorphic data fields, which is what
    differentiating between 0 (int) and 0.0 (float) does, so 0 and 0.0 are actually the same value, and therefore we
    want the signature for structures containing either form to be identical.

    This method creates a deep copy of any dict or list, replacing any instance of float zero with integer zero.

    The practical motivation behind this equivalence is that Jsonnet has no way of expressing a float zero.  Therefore,
    when different formats are mixed such that Jsonnet imports JSON or YAML, the float zeros in the JSON or YAML will be
    effectively converted to int zeros in Jsonnet.  This means that the same content in a source JSON or YAML can be
    given a different signature when imported via $ref versus imported using Jsonnet.

    Additional background: https://github.com/google/jsonnet/issues/558
    """
    if isinstance(obj, dict):
        return {k: _with_integer_zeros(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_with_integer_zeros(v) for v in obj]
    elif isinstance(obj, float) and obj == 0:
        return int(0)
    else:
        return obj


def compute_signature(obj: Union[dict, list, str]) -> str:
    """Compute a hash/signature of the content of the dict object."""
    if isinstance(obj, str):
        sig = hashlib.sha256()
        sig.update(obj.encode("utf-8"))
        return sig.hexdigest()
    elif isinstance(obj, dict) or isinstance(obj, list):
        return compute_signature(json.dumps(_with_integer_zeros(obj), sort_keys=True))
    else:
        raise ValueError(f"Cannot compute signature for {type(obj).__name__} type")
