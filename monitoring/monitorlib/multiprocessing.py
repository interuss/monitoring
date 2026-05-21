import json
import multiprocessing
import multiprocessing.shared_memory
from collections.abc import Callable
from multiprocessing.synchronize import RLock as RLockT
from typing import Generic, TypeVar

TValue = TypeVar("TValue")


# Note: attempts to change the below to SynchronizedValue[TValue] causes problems because IntelliJ does not reliably
# understand the newer syntax and therefore fails to provide contextual information for specific TValues.
# See: https://docs.astral.sh/ruff/rules/non-pep695-generic-class/#known-problems
class Transaction(Generic[TValue]):  # noqa: UP046
    _lock: RLockT
    _get_value: Callable[[], TValue]
    _set_value: Callable[[TValue], None]
    _value: TValue
    """This field is only valid when _locked is True"""

    _locked: bool
    """True when _lock is held and _value holds a valid TValue"""

    def __init__(
        self,
        lock: RLockT,
        get_value: Callable[[], TValue],
        set_value: Callable[[TValue], None],
    ):
        self._lock = lock
        self._get_value = get_value
        self._set_value = set_value
        self._locked = False

    def __enter__(self):
        if self._locked:
            raise RuntimeError(
                "SynchronizedValue Transaction started when Transaction was already in progress"
            )
        self._lock.__enter__()
        self._value = self._get_value()
        self._locked = True
        return self

    @property
    def value(self) -> TValue:
        """Value exposed for this transaction.  Mutate or set it to make changes during the transaction."""
        if not self._locked:
            raise RuntimeError(
                "Transaction value accessed when transaction was not active (e.g., outside a `with` block)"
            )
        return self._value

    @value.setter
    def value(self, new_value: TValue):
        if not self._locked:
            raise RuntimeError(
                "Transaction value set when transaction was not active (e.g., outside a `with` block)"
            )
        self._value = new_value

    def abort(self):
        """Do not save any changes made to the value during this transaction and release the lock on the synchronized value."""
        self._unlock()

    def _unlock(self, exc_type=None, exc_val=None, exc_tb=None):
        self._lock.__exit__(exc_type, exc_val, exc_tb)
        self._locked = False

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self._locked:
            return
        try:
            if exc_type is None:
                self._set_value(self.value)
        finally:
            self._unlock()


class SynchronizedValue(Generic[TValue]):  # noqa: UP046 (same reason as above)
    """Represents a value synchronized across multiple processes.

    The shared value can be read with .value or updated in a transaction.  A
    transaction is created using `transact` in a `with` block.  The
    object is mutated in the transaction, and then committed when the `with`
    block is exited.  Example:

    db = SynchronizedValue({'foo': 'bar'})
    with db.transact() as tx:
        assert isinstance(tx.value, dict)
        tx.value['foo'] = 'baz'
    print(json.dumps(db.value))
        >  {"foo":"baz"}
    """

    SIZE_BYTES = 4
    """Number of bytes at the beginning of the memory buffer dedicated to defining the size of the content."""

    _lock: RLockT
    _shared_memory: multiprocessing.shared_memory.SharedMemory
    _encoder: Callable[[TValue], bytes]
    _decoder: Callable[[bytes], TValue]
    _transaction: Transaction | None

    def __init__(
        self,
        initial_value: TValue,
        capacity_bytes: int = 10000000,
        encoder: Callable[[TValue], bytes] | None = None,
        decoder: Callable[[bytes], TValue] | None = None,
    ):
        """Creates a value synchronized across multiple processes.

        :param initial_value: Initial value to synchronize.  Must be serializable according to encoder and decoder (a dict works by default).  Must be mutatable.
        :param capacity_bytes: Maximum number of bytes required to represent this value
        :param encoder: Function that converts this value into bytes
        :param decoder: Function that converts bytes into this value
        """
        self._lock = multiprocessing.RLock()
        self._shared_memory = multiprocessing.shared_memory.SharedMemory(
            create=True, size=int(capacity_bytes + self.SIZE_BYTES)
        )
        self._encoder = (
            encoder
            if encoder is not None
            else lambda obj: json.dumps(obj).encode("utf-8")
        )
        self._decoder = (
            decoder if decoder is not None else lambda b: json.loads(b.decode("utf-8"))
        )
        self._transaction = None
        self._set_value(initial_value)

    def _get_value(self) -> TValue:
        if self._shared_memory.buf is None:
            raise RuntimeError(
                "SynchronizedValue attempted to get value when shared memory buffer was None"
            )
        content_len = int.from_bytes(
            bytes(self._shared_memory.buf[0 : self.SIZE_BYTES]), "big"
        )
        if content_len + self.SIZE_BYTES > self._shared_memory.size:
            raise RuntimeError(
                f"Shared memory claims to have {content_len} bytes of content when buffer size only allows {self._shared_memory.size - self.SIZE_BYTES}"
            )
        content = bytes(
            self._shared_memory.buf[self.SIZE_BYTES : content_len + self.SIZE_BYTES]
        )
        return self._decoder(content)

    def _set_value(self, value: TValue):
        if self._shared_memory.buf is None:
            raise RuntimeError(
                "SynchronizedValue attempted to set value when shared memory buffer was None"
            )
        content = self._encoder(value)
        content_len = len(content)
        if content_len + self.SIZE_BYTES > self._shared_memory.size:
            raise RuntimeError(
                f"Tried to write {content_len} bytes into a SynchronizedValue with only {self._shared_memory.size - self.SIZE_BYTES} bytes of capacity"
            )
        self._shared_memory.buf[0 : self.SIZE_BYTES] = content_len.to_bytes(
            self.SIZE_BYTES, "big"
        )
        self._shared_memory.buf[self.SIZE_BYTES : content_len + self.SIZE_BYTES] = (
            content
        )

    @property
    def value(self) -> TValue:
        with self._lock:
            return self._get_value()

    def transact(self) -> Transaction[TValue]:
        return Transaction[TValue](self._lock, self._get_value, self._set_value)
