import hashlib
import inspect
import math
import os
import uuid
from dataclasses import dataclass

mac = uuid.getnode()


def make_id(code: str) -> uuid.UUID:
    """Make a pseudo-random ID that is constant on a particular machine.

    When the same `code` is specified, this ID should always be the same for a
    particular machine, but it should differ between different machines.  Its
    leading and trailing 3 bytes are hardcoded to visually indicate that it is a
    test ID.

    Args:
      code: String describing the kind of ID.  An identical code should always
            yield an identical ID on the same machine.

    Returns:
      Pseudorandom test ID in UUIDv4 format.
    """
    digest = bytearray(hashlib.sha1(f"{mac} {code}".encode()).digest()[-16:])
    digest[0] = 0
    digest[1] = 0
    digest[2] = 0xFF
    digest[-3] = 0xFF
    digest[-2] = 0
    digest[-1] = 0
    return uuid.UUID(bytes=bytes(digest), version=4)


ID_CHAR_SET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_"
MAX_OWNER_LENGTH = 12  # characters


def bin_to_hex(bin_string):
    return format(int(bin_string, 2), "02x")


def bin_to_dec(bin_string):
    return int(bin_string, 2)


def hex_to_bin(hex_string):
    return format(int(hex_string, 16), "08b")


def dec_to_bin(num):
    return format(num, "06b")


def split_by(string_val, num=8):
    """Splits a string into substrings with a length of given number."""
    return [string_val[i : i + num] for i in range(0, len(string_val), num)]


def get_ord_val(letter):
    """Encodes new ord value for ascii letters."""
    v = ID_CHAR_SET.find(letter)
    if v == -1:
        v = 63
    return v


def get_ascii_val_from_bit_value(num):
    """Decodes new ord value to ascii letters."""
    return ID_CHAR_SET[num] if num < 63 else "?"


def encode_owner(owner_name: str) -> str:
    """Encode an owner name as an 18-character hexadecimal string"""
    bits = ""
    if len(owner_name) > MAX_OWNER_LENGTH:
        string_val = (
            owner_name[: math.ceil(MAX_OWNER_LENGTH / 2)]
            + owner_name[-math.floor(MAX_OWNER_LENGTH / 2) :]
        )
    elif len(owner_name) < MAX_OWNER_LENGTH:
        string_val = ("?" * (MAX_OWNER_LENGTH - len(owner_name))) + owner_name
    else:
        string_val = owner_name
    for letter in string_val:
        ord_val = get_ord_val(letter)
        bits += dec_to_bin(ord_val)
    return "".join(bin_to_hex(s) for s in split_by(bits))


def encode_resource_type_code(resource_type: int) -> str:
    """Encode a number between 0 and 0xFFFF as a 4-character hexadecimal string"""
    return format(resource_type, "04x")


def decode_owner(owner_id: str) -> str:
    """Decode an owner name, marking a truncated final character as unknown.

    IDFactory preserves only the first 17 of the original 18 hexadecimal digits.
    """
    truncated = len(owner_id) == 17
    if truncated:
        owner_id += "0"
    elif len(owner_id) != 18:
        raise ValueError("Invalid owner id.")
    hex_splits = split_by(owner_id, num=2)
    bits = ""
    for h in hex_splits:
        bits += hex_to_bin(h)
    test_owner = ""
    for seq in split_by(bits, 6):
        num = bin_to_dec(seq)
        test_owner += get_ascii_val_from_bit_value(num)
    if truncated:
        test_owner = test_owner[:-1] + "?"
    if test_owner[0] != "?":
        return (
            test_owner[: math.ceil(MAX_OWNER_LENGTH / 2)]
            + ".."
            + test_owner[-math.floor(MAX_OWNER_LENGTH / 2) :]
        )
    if truncated:
        return test_owner[:-1].lstrip("?") + "?"
    return test_owner.lstrip("?")


def decode_resouce_type(id: str) -> int:
    """Decode a number between 0 and 0xFFFF from a 4-character hex string"""
    return int(id, 16)


ResourceType = int
resource_type_code_descriptions: dict[ResourceType, str] = {}


# Next code: 406
def register_resource_type(code: int, description: str) -> ResourceType:
    """Register that the specified code refers to the described resource.

    Args:
      code: An integer that is globally-unique among all register_resource_type
            calls across all monitoring tools, referring to this resource type.
      description: Description of the resource created from this type.

    Returns:
      ResourceType that can be used to create an ID with <IDFactory>.make_id.
    """
    test_filename = inspect.stack()[1].filename
    this_folder = os.path.dirname(os.path.abspath(__file__))
    test = os.path.relpath(test_filename, this_folder)
    full_description = f"{test}: {description}"
    if code in resource_type_code_descriptions:
        raise ValueError(
            f'Resource type code {code} is already in use as "{resource_type_code_descriptions[code]}" so it cannot be used for "{full_description}"'
        )
    resource_type_code_descriptions[code] = full_description
    return code


@dataclass(frozen=True)
class DecodedTestID:
    owner_name: str
    resource_type: ResourceType
    instance_index: int


class IDFactory:
    """Creates UUIDv4 (as described in RFC4122) formatted IDs encoding the kind of ID and owner.

    Format: 000HXXXX-YYYY-4LYY-8YYY-YYYYYYYY0000

    Note that a UUID V4 needs to conform to the following regexp, which is why we
    set the first digit of the fourth group to 8.

    ^[0-9a-fA-F]{8}\\-[0-9a-fA-F]{4}\\-4[0-9a-fA-F]{3}\\-[8-b][0-9a-fA-F]{3}\\-[0-9a-fA-F]{12}$

    XXXX encodes the kind of ID according to resource_type_code_descriptions.
    YYYYYYYYYYYYYYYYY encodes the owner/creator of the resource having the ID and
    consists of 11 complete characters and 2 bits of a twelfth character,
    encoded as 6-bit groups.  Decoding marks the incomplete character with '?'.
    HL encodes an instance index from 0 to 255 in hexadecimal.  Index 0 produces
    the original ID format; other indices separate repeated invocations of a test.
    """

    owner_id: str
    _instance_index: int

    def __init__(self, test_owner: str, instance_index: int = 0):
        self.validate_instance_index(instance_index)
        self.owner_id = encode_owner(test_owner)
        self._instance_index = instance_index

    @staticmethod
    def validate_instance_index(instance_index: int) -> None:
        if type(instance_index) is not int or not 0 <= instance_index <= 255:
            raise ValueError("instance_index must be an integer from 0 to 255")

    @property
    def instance_index(self) -> int:
        return self._instance_index

    def make_id(self, resource_type: ResourceType):
        """Make a test ID with the specified resource type code"""
        return f"000{self.instance_index >> 4:x}{encode_resource_type_code(resource_type)}-{self.owner_id[0:4]}-4{self.instance_index & 0xF:x}{self.owner_id[4:6]}-8{self.owner_id[6:9]}-{self.owner_id[9:17]}0000"

    @classmethod
    def decode(cls, id: str) -> tuple[str, ResourceType]:
        """Decode an ID, retaining the original two-item return value."""
        decoded = cls.decode_details(id)
        return decoded.owner_name, decoded.resource_type

    @classmethod
    def decode_details(cls, id: str) -> DecodedTestID:
        """Decode the owner, resource type, and instance index of a test ID."""
        hex_digits = id.replace("-", "").lower()
        if len(hex_digits) != 32:
            raise ValueError(f"ID {id} has the wrong number of characters for a UUID")
        if any(c not in "0123456789abcdef" for c in hex_digits):
            raise ValueError(f"ID {id} contains non-hexadecimal characters")
        if hex_digits[0:3] != "000" or hex_digits[-4:] != "0000":
            raise ValueError(
                f"ID {id} does not have the leading and trailing zeros indicating a test ID"
            )
        if hex_digits[12] != "4" or hex_digits[16] != "8":
            raise ValueError(f"ID {id} is not formatted like a v4 test ID")
        x = hex_digits[4:8]
        y = hex_digits[8:12] + hex_digits[14:16] + hex_digits[17:28]
        resource_type_code = ResourceType(int(x, 16))
        owner_name = decode_owner(y)
        return DecodedTestID(
            owner_name=owner_name,
            resource_type=resource_type_code,
            instance_index=int(hex_digits[3] + hex_digits[13], 16),
        )


check_scd_write_subscription_id = register_resource_type(
    344, "Subscription created by build/dev/check_scd_write.sh"
)
check_scd_write_constraint_id = register_resource_type(
    345, "Constraint reference created by build/dev/check_scd_write.sh"
)
check_scd_write_operational_intent_id = register_resource_type(
    346, "Operational intent reference created by build/dev/check_scd_write.sh"
)

unknown_resource_id = register_resource_type(
    404, "<Unknown resource ID / Unknown purpose>"
)
