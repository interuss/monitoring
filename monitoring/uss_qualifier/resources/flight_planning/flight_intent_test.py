import arrow

from monitoring.monitorlib.clients.flight_planning.flight_info_template import (
    BasicFlightPlanInformationTemplate,
    FlightInfoTemplate,
)
from monitoring.monitorlib.geo import (
    LatLngPoint,
    Polygon,
    RelativeTranslation,
    Transformation,
    Volume3D,
)
from monitoring.monitorlib.temporal import TestTimeContext, Time
from monitoring.uss_qualifier.resources.flight_planning.flight_intent import (
    FlightIntentCollection,
    FlightIntentCollectionElement,
)


def test_flight_intent_relative_transformations():
    # Two flight intents defined near origin that are very close but not overlapping.
    # Flight 1 polygon
    poly1 = Polygon(
        vertices=[
            LatLngPoint(lat=0.00000, lng=0.00000),
            LatLngPoint(lat=0.00100, lng=0.00000),
            LatLngPoint(lat=0.00100, lng=0.00100),
            LatLngPoint(lat=0.00000, lng=0.00100),
        ]
    )

    # Flight 2 polygon, shifted slightly to the east of poly1, very close but not overlapping
    poly2 = Polygon(
        vertices=[
            LatLngPoint(lat=0.00000, lng=0.001001),
            LatLngPoint(lat=0.00100, lng=0.001001),
            LatLngPoint(lat=0.00100, lng=0.002),
            LatLngPoint(lat=0.00000, lng=0.002),
        ]
    )

    template1 = FlightInfoTemplate(
        basic_information=BasicFlightPlanInformationTemplate(
            usage_state="Planned",
            uas_state="Nominal",
            area=[
                Volume3D(
                    outline_polygon=poly1,
                    altitude_lower={"value": 0, "units": "M", "reference": "W84"},
                    altitude_upper={"value": 100, "units": "M", "reference": "W84"},
                )
            ],
        )
    )

    template2 = FlightInfoTemplate(
        basic_information=BasicFlightPlanInformationTemplate(
            usage_state="Planned",
            uas_state="Nominal",
            area=[
                Volume3D(
                    outline_polygon=poly2,
                    altitude_lower={"value": 0, "units": "M", "reference": "W84"},
                    altitude_upper={"value": 100, "units": "M", "reference": "W84"},
                )
            ],
        )
    )

    transformations = [
        Transformation(
            relative_translation=RelativeTranslation(
                meters_east=500.0,
                meters_north=-300.0,
            )
        ),
        Transformation(
            relative_translation=RelativeTranslation(
                degrees_north=32.7181,
                degrees_east=-96.7587,
            )
        ),
        Transformation(
            relative_translation=RelativeTranslation(
                meters_east=-100.0,
                meters_north=5000.0,
            )
        ),
    ]

    for n_transformations in range(len(transformations) + 1):
        collection = FlightIntentCollection(
            intents={
                "flight_1": FlightIntentCollectionElement(full=template1),
                "flight_2": FlightIntentCollectionElement(full=template2),
            },
            transformations=transformations[0:n_transformations],
        )

        resolved = collection.resolve()

        # Resolve the final FlightInfo using a dummy context
        t = Time(arrow.utcnow().datetime)
        context = TestTimeContext.all_times_are(t)
        info1 = resolved["flight_1"].resolve(context)
        info2 = resolved["flight_2"].resolve(context)

        vol1 = info1.basic_information.area[0].volume
        vol2 = info2.basic_information.area[0].volume

        # Verify that distance between any pair of vertices remains unchanged (rigid transformation)
        assert (
            vol1.outline_polygon is not None
            and vol1.outline_polygon.vertices is not None
        )
        assert (
            vol2.outline_polygon is not None
            and vol2.outline_polygon.vertices is not None
        )
        assert poly1.vertices is not None
        assert poly2.vertices is not None
        orig_vertices = poly1.vertices + poly2.vertices
        trans_vertices = vol1.outline_polygon.vertices + vol2.outline_polygon.vertices
        assert len(orig_vertices) == len(trans_vertices)
        for i in range(len(orig_vertices)):
            for j in range(i + 1, len(orig_vertices)):
                d_orig = (
                    orig_vertices[i]
                    .as_s2sphere()
                    .get_distance(orig_vertices[j].as_s2sphere())
                    .radians
                )
                d_trans = (
                    trans_vertices[i]
                    .as_s2sphere()
                    .get_distance(trans_vertices[j].as_s2sphere())
                    .radians
                )
                assert abs(d_orig - d_trans) < 1e-12

        # Verify they still do not overlap
        assert not vol1.intersects_vol3(vol2)

        # If they were shifted slightly closer to overlap, they would intersect
        # Let's verify that a small additional overlap translation makes them intersect
        overlap_trans = Transformation(
            relative_translation=RelativeTranslation(
                degrees_east=-0.000002  # Shift flight 2 slightly west to overlap flight 1
            )
        )
        vol2_overlapped = vol2.transform(overlap_trans)
        assert vol1.intersects_vol3(vol2_overlapped)
