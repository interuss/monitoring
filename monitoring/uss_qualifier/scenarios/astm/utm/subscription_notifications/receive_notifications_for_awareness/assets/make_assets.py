# Requires svg.py 1.4.2

import inspect
from textwrap import dedent
from typing import List

import svg


def translate(points: List[float], dx: float, dy: float) -> List[float]:
    result = []
    x = True
    for p in points:
        result.append(p + dx if x else p + dy)
        x = not x
    return result


outline = "#202020"
accepted = "#808080"
activated = "#00ff00"
nonconforming = "#ffff00"
flight1_points = [20, 30, 20, 200, 70, 200, 140, 120, 190, 200, 250, 200, 250, 30]
flight2_points = [140, 145, 30, 265, 145, 320, 215, 265]


common_elements = [
    svg.Style(
        text=dedent(""".heavy { font: bold 30px sans-serif; }"""),
    ),
    svg.Marker(
        id="arrowhead",
        viewBox=svg.ViewBoxSpec(0, 0, 10, 10),
        refX=6,
        refY=4,
        markerWidth=6,
        markerHeight=6,
        color=outline,
        orient="auto-start-reverse",
        elements=[
            svg.Path(
                d=[
                    svg.MoveTo(0, 0),
                    svg.LineTo(8, 4),
                    svg.LineTo(0, 8),
                    svg.ClosePath(),
                ],
                fill=outline,
            )
        ],
    ),
]


def make_flight1_activated_flight2_planned():
    elements = [
        svg.Polygon(
            points=flight1_points,
            stroke=outline,
            fill=activated,
            fill_opacity=0.4,
            stroke_width=8,
        ),
        svg.Text(x=60, y=100, class_=["heavy"], text="Flight 1"),
        svg.Polygon(
            points=flight2_points,
            stroke=outline,
            fill=nonconforming,
            fill_opacity=0.4,
            stroke_width=8,
        ),
        svg.Text(x=60, y=260, class_=["heavy"], text="Flight 2"),
    ]

    canvas = svg.SVG(
        width=400,
        height=350,
        elements=common_elements + elements,
    )
    with open(inspect.currentframe().f_code.co_name[len("make_") :] + ".svg", "w") as f:
        f.write(str(canvas))


make_flight1_activated_flight2_planned()
