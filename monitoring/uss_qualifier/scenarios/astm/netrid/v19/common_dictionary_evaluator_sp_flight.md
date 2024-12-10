# ASTM NetRID v19 Service Provider flight consistency with Common Data Dictionary test step fragment

This fragment is implemented in `common_dictionary_evaluator.py:RIDCommonDictionaryEvaluator.evaluate_sp_flight`.

## Service Provider altitude check

**[astm.f3411.v19.NET0260,Table1,11](../../../../requirements/astm/f3411/v19.md)** requires that relevant Remote ID data, consistent with the common data dictionary, be reported by the Service Provider.  Injected flight data had known altitudes, but the altitude reported by the Service Provider did not match those known altitudes.

## ⚠️ Service Provider vertical speed check

**[astm.f3411.v19.NET0260,Table1,20](../../../../requirements/astm/f3411/v19.md)** requires that relevant Remote ID data, consistent with the common data dictionary, be reported by the Service Provider. Injected flight data had a specified vertical speed that was different from the reported one.

## ⚠️ Service Provider speed check

**[astm.f3411.v19.NET0260,Table1,19](../../../../requirements/astm/f3411/v19.md)** requires that relevant Remote ID data, consistent with the common data dictionary, be reported by the Service Provider. Injected flight data had a specified speed that was different from the reported one.

## ⚠️ Service Provider speed accuracy check

**[astm.f3411.v19.NET0260,Table1,17](../../../../requirements/astm/f3411/v19.md)** requires that relevant Remote ID data, consistent with the common data dictionary, be reported by the Service Provider.  Injected flight data had a specified speed accuracy that was different from the reported one.

## ⚠️ Service Provider track check

**[astm.f3411.v19.NET0260,Table1,18](../../../../requirements/astm/f3411/v19.md)** requires that relevant Remote ID data, consistent with the common data dictionary, be reported by the Service Provider.  Injected flight data had a specified track that was different from the reported one.

## ⚠️ Service Provider geodetic altitude accuracy check

**[astm.f3411.v19.NET0260,Table1,15](../../../../requirements/astm/f3411/v19.md)** requires that relevant Remote ID data, consistent with the common data dictionary, be reported by the Service Provider.  Injected flight data had a specified geodetic altitude accuracy that was different from the reported one.

## ⚠️ Service Provider horizontal accuracy check

**[astm.f3411.v19.NET0260,Table1,16](../../../../requirements/astm/f3411/v19.md)** requires that relevant Remote ID data, consistent with the common data dictionary, be reported by the Service Provider.  Injected flight data had a specified horizontal accuracy that was different from the reported one.

## ⚠️ Service Provider timestamp accuracy is present check

If the timestamp accuracy is not present, the USS under test is not properly implementing the REST interface specified by the OpenAPI definition contained in Annex A4, and is therefore in violation of **[astm.f3411.v19.NET0710,1](../../../../requirements/astm/f3411/v19.md)**.

## ⚠️ Service Provider timestamp accuracy is correct check

**[astm.f3411.v19.NET0260,Table1,5](../../../../requirements/astm/f3411/v19.md)** requires that relevant Remote ID data, consistent with the common data dictionary, be reported by the Service Provider.  The observed timestamp accuracy differs from the injected one.

## ⚠️ Service Provider height check

**[astm.f3411.v19.NET0260,Table1,13](../../../../requirements/astm/f3411/v19.md)** requires that relevant Remote ID data, consistent with the common data dictionary, be reported by the Service Provider.  The reported height of the flight is unrealistic or otherwise not consistent with the injected data.
