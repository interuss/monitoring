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
high_priority = "#dd2020"
accepted = "#808080"
activated = "#00ff00"
nonconforming = "#ffff00"
flight2_points = [10, 110, 100, 10, 190, 30, 220, 100, 160, 190]
flight2m_points = [
    10,
    100,
    100,
    10,
    190,
    30,
    220,
    85,
]
flight1_points = [20, 190, 50, 110, 310, 90, 340, 90, 340, 180, 270, 160]
flight1c_points = [185, 180, 190, 40, 310, 90, 340, 90, 340, 180, 270, 160]
flight1m_points = [140, 190, 170, 110, 310, 90, 340, 90, 340, 180, 270, 160]
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


def make_attempt_to_plan_flight_into_conflict():
    elements = [
        svg.Polygon(
            points=flight2_points,
            stroke=high_priority,
            fill=accepted,
            fill_opacity=0.4,
            stroke_width=8,
        ),
        svg.Text(x=60, y=90, class_=["heavy"], text="Flight 2"),
        svg.Polygon(
            points=translate(flight2_points, 440, 0),
            stroke=high_priority,
            fill=accepted,
            fill_opacity=0.4,
            stroke_width=8,
        ),
        svg.Text(x=60 + 440, y=90, class_=["heavy"], text="Flight 2"),
        svg.Polygon(
            points=translate(flight1_points, 440, 0),
            stroke=outline,
            fill=accepted,
            fill_opacity=0.4,
            stroke_width=8,
            stroke_dasharray=[16],
        ),
        svg.Text(x=220 + 440, y=140, class_=["heavy"], text="Flight 1"),
        svg.Text(x=560, y=150, class_=["heavy"], text="X", fill="red"),
        svg.Line(
            x1=370,
            y1=100,
            x2=420,
            y2=100,
            stroke=outline,
            stroke_width=8,
            marker_end="url(#arrowhead)",
        ),
    ]
    canvas = svg.SVG(
        width=800,
        height=200,
        elements=common_elements + elements,
    )
    with open(inspect.currentframe().f_code.co_name[len("make_") :] + ".svg", "w") as f:
        f.write(str(canvas))


def make_attempt_to_modify_planned_flight_into_conflict():
    elements = [
        svg.Polygon(
            points=flight1_points,
            stroke=outline,
            fill=accepted,
            fill_opacity=0.4,
            stroke_width=8,
        ),
        svg.Text(x=205, y=150, class_=["heavy"], text="Flight 1"),
        svg.Polygon(
            points=flight2_points,
            stroke=high_priority,
            fill=accepted,
            fill_opacity=0.4,
            stroke_width=8,
        ),
        svg.Text(x=60, y=90, class_=["heavy"], text="Flight 2"),
        svg.Polygon(
            points=translate(flight2_points, 440, 0),
            stroke=high_priority,
            fill=accepted,
            fill_opacity=0.4,
            stroke_width=8,
        ),
        svg.Text(x=60 + 440, y=90, class_=["heavy"], text="Flight 2"),
        svg.Polygon(
            points=translate(flight1m_points, 440, 0),
            stroke=outline,
            fill=accepted,
            fill_opacity=0.4,
            stroke_width=8,
            stroke_dasharray=[16],
        ),
        svg.Text(x=205 + 440, y=150, class_=["heavy"], text="Flight 1m"),
        svg.Text(x=605, y=150, class_=["heavy"], text="X", fill="red"),
        svg.Line(
            x1=370,
            y1=100,
            x2=420,
            y2=100,
            stroke=outline,
            stroke_width=8,
            marker_end="url(#arrowhead)",
        ),
    ]
    canvas = svg.SVG(
        width=800,
        height=200,
        elements=common_elements + elements,
    )
    with open(inspect.currentframe().f_code.co_name[len("make_") :] + ".svg", "w") as f:
        f.write(str(canvas))


def make_attempt_to_activate_flight_into_conflict():
    elements = [
        svg.Polygon(
            points=flight1_points,
            stroke=outline,
            fill=accepted,
            fill_opacity=0.4,
            stroke_width=8,
        ),
        svg.Text(x=222, y=145, class_=["heavy"], text="Flight 1"),
        svg.Polygon(
            points=flight2_points,
            stroke=high_priority,
            fill=accepted,
            fill_opacity=0.4,
            stroke_width=8,
        ),
        svg.Text(x=60, y=90, class_=["heavy"], text="Flight 2"),
        svg.Polygon(
            points=translate(flight2_points, 440, 0),
            stroke=high_priority,
            fill=accepted,
            fill_opacity=0.4,
            stroke_width=8,
        ),
        svg.Text(x=60 + 440, y=90, class_=["heavy"], text="Flight 2"),
        svg.Polygon(
            points=translate(flight1_points, 440, 0),
            stroke=outline,
            fill=activated,
            fill_opacity=0.4,
            stroke_width=8,
            stroke_dasharray=[16],
        ),
        svg.Text(x=222 + 440, y=145, class_=["heavy"], text="Flight 1"),
        svg.Text(x=560, y=150, class_=["heavy"], text="X", fill="red"),
        svg.Line(
            x1=370,
            y1=100,
            x2=420,
            y2=100,
            stroke=outline,
            stroke_width=8,
            marker_end="url(#arrowhead)",
        ),
    ]
    canvas = svg.SVG(
        width=800,
        height=200,
        elements=common_elements + elements,
    )
    with open(inspect.currentframe().f_code.co_name[len("make_") :] + ".svg", "w") as f:
        f.write(str(canvas))


def make_modify_activated_flight_with_preexisting_conflict():
    elements = [
        svg.Polygon(
            points=flight1_points,
            stroke=outline,
            fill=activated,
            fill_opacity=0.4,
            stroke_width=8,
        ),
        svg.Text(x=222, y=145, class_=["heavy"], text="Flight 1"),
        svg.Polygon(
            points=flight2_points,
            stroke=high_priority,
            fill=activated,
            fill_opacity=0.4,
            stroke_width=8,
        ),
        svg.Text(x=60, y=90, class_=["heavy"], text="Flight 2"),
        svg.Polygon(
            points=translate(flight2_points, 440, 0),
            stroke=high_priority,
            fill=activated,
            fill_opacity=0.4,
            stroke_width=8,
        ),
        svg.Text(x=60 + 440, y=90, class_=["heavy"], text="Flight 2"),
        svg.Polygon(
            points=translate(flight1m_points, 440, 0),
            stroke=outline,
            fill=activated,
            fill_opacity=0.4,
            stroke_width=8,
        ),
        svg.Text(x=222 + 440, y=145, class_=["heavy"], text="Flight 1m"),
        svg.Line(
            x1=370,
            y1=100,
            x2=420,
            y2=100,
            stroke=outline,
            stroke_width=8,
            marker_end="url(#arrowhead)",
        ),
    ]
    canvas = svg.SVG(
        width=800,
        height=200,
        elements=common_elements + elements,
    )
    with open(inspect.currentframe().f_code.co_name[len("make_") :] + ".svg", "w") as f:
        f.write(str(canvas))


def make_attempt_to_modify_activated_flight_into_conflict():
    elements = [
        svg.Polygon(
            points=flight1_points,
            stroke=outline,
            fill=activated,
            fill_opacity=0.4,
            stroke_width=8,
        ),
        svg.Text(x=202, y=145, class_=["heavy"], text="Flight 1"),
        svg.Polygon(
            points=flight2m_points,
            stroke=high_priority,
            fill=activated,
            fill_opacity=0.4,
            stroke_width=8,
        ),
        svg.Text(x=55, y=80, class_=["heavy"], text="Flight 2m"),
        svg.Polygon(
            points=translate(flight2m_points, 440, 0),
            stroke=high_priority,
            fill=activated,
            fill_opacity=0.4,
            stroke_width=8,
        ),
        svg.Text(x=55 + 440, y=80, class_=["heavy"], text="Flight 2m"),
        svg.Polygon(
            points=translate(flight1c_points, 440, 0),
            stroke=outline,
            fill=activated,
            fill_opacity=0.4,
            stroke_width=8,
            stroke_dasharray=[16],
        ),
        svg.Text(x=202 + 440, y=145, class_=["heavy"], text="Flight 1c"),
        svg.Text(x=635, y=85, class_=["heavy"], text="X", fill="red"),
        svg.Line(
            x1=370,
            y1=100,
            x2=420,
            y2=100,
            stroke=outline,
            stroke_width=8,
            marker_end="url(#arrowhead)",
        ),
    ]
    canvas = svg.SVG(
        width=800,
        height=200,
        elements=common_elements + elements,
    )
    with open(inspect.currentframe().f_code.co_name[len("make_") :] + ".svg", "w") as f:
        f.write(str(canvas))


make_attempt_to_plan_flight_into_conflict()
make_attempt_to_modify_planned_flight_into_conflict()
make_attempt_to_activate_flight_into_conflict()
make_modify_activated_flight_with_preexisting_conflict()
make_attempt_to_modify_activated_flight_into_conflict()
