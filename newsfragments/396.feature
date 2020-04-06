Improve handling of diamond anvil cell data.  When calling xia2 with `high_pressure.correction=True`:
- 'Dynamic shadowing' is enabled, to mask out the regions shadowed by the cell body.
- The minimum observation counts for profile modelling are relaxed — the defaults are unrealistic in the case of a small data set from a small-molecule material in a diamond anvil cell.  In such cases, there are far fewer spots than the DIALS profile modelling expects, based on the norm in MX.  This had been a frequent cause of frustration when processing small-molecule data with xia2.
- X-ray absorption in the diamond anvils is automatically corrected for using `dials.anvil_correction`.
