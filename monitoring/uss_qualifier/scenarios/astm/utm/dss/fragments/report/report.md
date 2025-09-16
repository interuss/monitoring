# Make report to DSS test step fragment
This step makes a report to the DSS.

See `make_dss_report` in [test_steps_fragments.py](../../test_step_fragments.py).

## 🛑 DSS report successfully submitted check
If the submission of the report to the DSS does not succeed, this check will fail per **[astm.f3548.v21.DSS0100,2](../../../../../../requirements/astm/f3548/v21.md)**.

## ⚠️ DSS returned a valid report ID check
If the ID returned by the DSS is not present or is empty, this check will fail per **[astm.f3548.v21.DSS0100,2](../../../../../../requirements/astm/f3548/v21.md)**.
