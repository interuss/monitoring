import hashlib
import json
from typing import Optional

from implicitdict import ImplicitDict
from monitoring.uss_qualifier import fileio
from monitoring.uss_qualifier.fileio import FileReference


class ExternalFile(ImplicitDict):
    path: FileReference
    """Location of the external file."""

    hash_sha512: Optional[str]
    """SHA-512 hash of the external file.

    If specified, the external file's content will be verified to have this hash or else produce an error.

    If not specified, will be populated with the hash of the external file at the time of execution."""

    def verify_or_set_hash(self, content: str) -> None:
        hash_sha512 = hashlib.sha512(content.encode("utf-8")).hexdigest()
        if "hash_sha512" in self and self.hash_sha512:
            if hash_sha512 != self.hash_sha512:
                raise ValueError(
                    f"Provided SHA-512 hash for external file at {self.path} is {self.hash_sha512}, but this does not match the hash computed for the content of that file which is {hash_sha512}"
                )
        else:
            self.hash_sha512 = hash_sha512


def load_content(file: ExternalFile) -> str:
    """Load string content from the specified file and check or mutate hashes according to loaded content.

    Note that if file's hashes are not provided, file will be mutated to set the hashes according to the loaded content.

    Args:
        file: File to load and hash(es) to assert or mutate.

    Returns: Content of external file.
    """
    content = fileio.load_content(file.path)
    file.verify_or_set_hash(content)
    return content


def load_dict(file: ExternalFile) -> dict:
    """Load dict content from the specified file and check or mutate hashes according to loaded content.

    Note that if file's hashes are not provided, file will be mutated to set the hashes according to the loaded content.

    Args:
        file: File to load and hash(es) to assert or mutate.

    Returns: Python dict with the content loaded from the file (and referenced files, if applicable).
    """
    result = fileio.load_dict_with_references(file.path)
    content = json.dumps(result)
    file.verify_or_set_hash(content)
    return result
