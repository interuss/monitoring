# ASTM NetRID v19 clustering test step fragment

This fragment is implemented in `display_data_evaluator.py:RIDObservationEvaluator._evaluate_clusters_observation`.

#### ⚠️ Minimal obfuscation distance of individual flights check

For a display area with a diagonal greater than *NetDetailsMaxDisplayAreaDiagonal* and less than *NetMaxDisplayAreaDiagonal*, **[astm.f3411.v19.NET0490](../../../../requirements/astm/f3411/v19.md)** requires that a Display provider shall obfuscate individual UAs within a cluster.
If a cluster with a single flight has a width or height smaller than 2 * *NetMinObfuscationDistance* (meaning that the USS did not buffer the single point by *NetMinObfuscationDistance* in all directions when forming the cluster bounds), this test will fail.

#### ⚠️ Individual flights obfuscation check

For a display area with a diagonal greater than *NetDetailsMaxDisplayAreaDiagonal* and less than *NetMaxDisplayAreaDiagonal*, **[astm.f3411.v19.NET0490](../../../../requirements/astm/f3411/v19.md)** requires that a Display provider shall obfuscate individual UAs within a cluster.
If a cluster with a single flight has its center equal to the position of the flight, this test will fail.
If a cluster with a single flight does not actually encompass the flight, this test will fail.

#### ⚠️ Minimal obfuscation distance of multiple flights clusters check

For a display area with a diagonal greater than *NetDetailsMaxDisplayAreaDiagonal* and less than *NetMaxDisplayAreaDiagonal*, **[astm.f3411.v19.NET0480](../../../../requirements/astm/f3411/v19.md)** requires that a Display provider shall cluster UAs in close proximity to each other using a circular or polygonal area.
If a cluster with multiples flights has a width or height smaller than 2 * *NetMinObfuscationDistance*, this test will fail. A larger width or height might still be incorrect, but the test cannot at the moment determine this.

#### ⚠️ Clustering count check

For a display area with a diagonal greater than *NetDetailsMaxDisplayAreaDiagonal* and less than *NetMaxDisplayAreaDiagonal*, **[astm.f3411.v19.NET0480](../../../../requirements/astm/f3411/v19.md)** requires that a Display provider shall cluster UAs in close proximity to each other using a circular or polygonal area.
Taking into account the propagation time of the injected flights, if the total number of clustered UAs when this value is expected to be stable is not correct, this test will fail.

#### ⚠️ Minimal display area of clusters check

For a display area with a diagonal greather than *NetDetailsMaxDisplayAreaDiagonal* and less than *NetMaxDisplayAreaDiagonal*, **[astm.f3411.v19.NET0480](../../../../requirements/astm/f3411/v19.md)** requires that a Display provider shall cluster UAs in close proximity to each other using a circular or polygonal area covering no less than *NetMinClusterSize* percent of the display area size.
This check validates that the display area of a cluster, measured and provided in square meters by the test harness, is no less than *NetMinClusterSize* percent of the display area.
