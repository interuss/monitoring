import s2sphere

from monitoring.monitorlib import s2

# Note: Parameter names in native_callbacks must be single-character ASCII strings to avoid a
# use-after-free bug in _jsonnet's handle_native_callbacks C implementation (see
# https://github.com/google/jsonnet/issues/1321 and https://github.com/google/jsonnet/pull/1333,
# where multi-byte PyBytes objects from PyUnicode_AsUTF8String are DECREFed and freed before
# jsonnet_native_callback is called, causing subsequent parameters to reuse the same memory address
# and appear as duplicate parameter names). Single-byte PyBytes objects are immortal singletons in
# CPython.
s2_callbacks = {
    "s2.cell_of": (
        ("y", "x", "l"),
        lambda lat, lng, level: s2.cell_of(lat, lng, int(level)).to_token(),
    ),
    "s2.offset_cell": (
        ("c", "e", "n"),
        lambda cell, east, north: s2.offset_cell(
            s2sphere.CellId.from_token(cell), int(east), int(north)
        ).to_token(),
    ),
    "s2.inscribed_latlng_rect": (
        ("c",),
        lambda cell: s2.latlng_rect_str(
            s2.inscribed_latlng_rect(s2sphere.CellId.from_token(cell))
        ),
    ),
    "s2.expand_latlng_rect": (
        ("r", "y", "x"),
        lambda rect, dlat, dlng,: s2.latlng_rect_str(
            s2.expand_latlng_rect(s2.latlng_rect_from_str(rect), dlat, dlng)
        ),
    ),
    "s2.latlng_rect_part": (
        ("r", "p"),
        s2.latlng_rect_str_part,
    ),
}
