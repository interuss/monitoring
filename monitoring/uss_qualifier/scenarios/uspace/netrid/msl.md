# U-space MSL altitude test scenario

## Description

[Article 8](https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32021R0664&qid=1702917443967#d1e905-161-1)(2)(c) specifies (emphasis added):

> The network identification service shall allow for the authorised users to receive messages with the geographical position of the UAS, its *altitude above mean sea level* and its height above the surface or take-off point.


ASTM F3411 provides geodetic altitude above the WGS84 ellipsoidal estimate of sea level, however [AMC1](https://www.easa.europa.eu/en/document-library/acceptable-means-of-compliance-and-guidance-materials/amc-and-gm-implementing) specifies:

> USSPs should convert the heights above the WGS 84 ellipsoid exchanged with the ASTM F-3411-22A standard to height above mean sea level (MSL) before providing it to the UAS operators.


[GM1](https://www.easa.europa.eu/en/document-library/acceptable-means-of-compliance-and-guidance-materials/amc-and-gm-implementing) further clarifies the desired definition of mean sea level:

> Wherever the flight altitude above sea level is required to be determined with the use of GNSS systems, it is recommended to use the EGM2008 or at least the EGM96 geoid models as the definition of mean sea level, as agreed with the competent authority.


Therefore, to comply with Article 8(2)(c), a USSP must allow for the authorised users to receive messages with the UAS's altitude above the EGM96 geoid.

### Assumptions

This scenario assumes that [the ASTM F3411-22a nominal behavior NetRID test scenario](../../astm/netrid/v22a/nominal_behavior.md) has already been completed and determines compliance with the requirement above by examining the observations made by uss_qualifier as an automated "authorised user".

## Resources

### observers

The set of USSPs providing messages to authorised users to be evaluated for U-space MSL compliance.

## UAS observations evaluation test case

### Find nominal behavior report test step

To avoid re-running a nearly-identical test scenario, this test scenario merely examines data collected in a separate test scenario (see [Assumptions](#assumptions)).  Therefore, the first step in this scenario is to find the test report for that other scenario.

If an appropriate test report cannot be found, this scenario will be discontinued.

### Evaluate UAS observations test step

#### ⚠️ Message contains MSL altitude check

If the response message for the remote identification observation made by the virtual/automated authorised user does not contain the UAS's MSL altitude, the USSP will have failed to comply with **[uspace.article8.MSLAltitude](../../../requirements/uspace/article8.md)**.

#### ⚠️ MSL altitude is correct check

In the previously-conducted test scenario, UAS altitudes were injected relative to the WGS84 ellipsoid.  Since the EGM96 geoid is a standard shape that is well-defined relative to the WGS84 ellipsoid, this means the altitude relative to the EGM96 is defined by the injection.  If the observed MSL altitude differs from the injected MSL altitude, then the USSP has failed to allow the automated authorised user to receive messages with the UAS's altitude above mean sea level per **[uspace.article8.MSLAltitude](../../../requirements/uspace/article8.md)** because the altitude reported was not the altitude of the UAS.
