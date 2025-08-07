import inspect
import os

from monitoring.monitorlib.formatting import make_datetime


def assert_datetimes_are_equal(t1, t2, tolerance_seconds: float = 0) -> None:
    try:
        t1_datetime = make_datetime(t1)
        t2_datetime = make_datetime(t2)
    except ValueError as e:
        assert False, f"Error interpreting value as datetime: {e}"
    if tolerance_seconds == 0:
        assert t1_datetime == t2_datetime
    else:
        assert abs((t1_datetime - t2_datetime).total_seconds()) < tolerance_seconds


def make_fake_url(suffix: str | None = None, frames_above: int = 1) -> str:
    """Create a dummy URL revealing the location from which this function was called.

    The URL generated is a function solely of the file from which this function is called and the provided suffix.

    Args:
        suffix: String to append to the end of the URL (e.g., "uss/v1")
        frames_above: Number of stack frames above this function that the source of this URL is.
    """

    layers = os.path.splitext(inspect.stack()[frames_above].filename)[0].split(
        os.path.sep
    )
    layers = [layer for layer in layers if layer]
    if "monitoring" in layers:
        layers = layers[layers.index("monitoring") :]
    if suffix is not None:
        layers.append(suffix)
    return "https://testdummy.interuss.org/interuss/" + "/".join(layers)
