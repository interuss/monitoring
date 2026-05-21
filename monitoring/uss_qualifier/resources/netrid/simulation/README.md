# USS Qualifier RID Test Data Generation

This directory contains a series of tools for generating flight data for qualifying Network Remote ID compliance.

## Flight track dataset generator
[`adjacent_circular_flights_simulator.py`](adjacent_circular_flights_simulator.py): An API to generate multiple flight paths and patterns within a specified bounding box. You can specify a bounding box in any part of the world the generator will create a grid for flights for the bounds provided. In addition, circular flight paths will be generated within that grid. The output of this API are flight data file artifacts in GeoJSON [FeatureCollection](https://tools.ietf.org/html/rfc7946#section-3.3) format and the flight tracks are converted to a `RIDAircraftState` data: by adding metadata and timestamps to the points. The conversion of flight track points to RIDAircraftState can be considered as a simplified simulation.

## Create Flight Record from KML

The KML is designed with [Google Earth](https://earth.google.com/) (desktop version), and it's intended to be the set of information a human user could reasonably draw to describe the flight.

It's hard to draw in three dimensions (let alone four), so the areas define behavior in the extra two dimensions. 

An altitude area sets the altitude of the aircraft inside it, the speed area sets the speed.

The actual flight path of the aircraft is constructed from this information. 

The flight path is just the path the aircraft will take and the key points are not the points the aircraft will report -- instead, the aircraft will report points along the path depending on its speed.

[`kml_flights.py`](kml_flights.py) accepts a KML file with one/many flights defined in the KML folders and produce a set of JSON files for each such flight, snapshotting the aircraft's state every sample_rate.

Following are the specifications for input KML:

### Tree hierachy example

```
kentland: # Root folder
  flight: example # Definition of a flight. There may be multiple flights
    - Flight path
    - alt: Base
    - alt: High
    - speed: Departure (5)
    - speed: Enroute (30)
    - operator_location
```


### Flight

KML must contain one folder for each flight path. Folder name should be prefixed with "flight: " and the flight ID of the flight, e.g. "flight: fly_north".

The metadata of a flight are stored in its folder description, as simple `key: value` format.

Example description:

```
serial_number: EXPL3123
operation_description: U-turn south of takeoff
operator_id: EXAMPLE_OPERATOR2
registration_number: N.123456
aircraft_type: HybridLift
operator_name: UFT Participant 2
timestamp_accuracy: 1.0
speed_accuracy: SA3mps
sample_rate: 1.0
accuracy_h: HAUnknown
accuracy_v: VAUnknown
```

### Flight path

Every flight needs exactly one path (LineString) and this is the path the aircraft should take over the ground.

### Speed zones

Speed zones for a flight should be defined as polygons nested in the flight folder. Each speed polygon must be prefixed with "speed: " and include m/s in parenthesis. For example: "speed: Mission (2.5)".

### Altitude zones

Like speed, the polygon names prefixed with "alt: " are considered Altitude polygons for a flight path. Only the altitude of the first point is used. Altitude of each point in the flight path is interpolated based on the distance of the point from the nearby altitude polygons.

### Speed and Altitude interpolation

Speed and Altitude of each point is interpolated by adding weight of surrounding zones where weigh of each zone is 1/distance of the zone from the point. For example: If zone 1 was at 10m altitude 10m away, zone 2 was at 20m altitude 50m away, and zone 3 was at 30m altitude 100m away, the weights would be 1/10 for zone 1, 1/50 for zone 2, and 1/100 for zone 3. So, the aircraft altitude would be (10/10 + 20/50 + 30/100) / (1/10 + 1/50 + 1/100) = 13.1m.

If a point on the path is inside a polygone, the value from it is directly used.


## Operator location

The location of the operator should be defined as a sngle point, named `operator_location`.
