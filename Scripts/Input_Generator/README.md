## Scenario Generation

The python scripts in this folder generate scenarios based on the geographical data in the cadmum_gis folder and in the inputs folder of this directory. Scenarios can be generated for Ottawa Dissemination areas or for Ontario Public Health Units

Requirements before running:
- The python environment must have geopandas installed before running `generateScenario.py`

Inputs:
- The default cell state can be set in `input_*/default.json`
- The infected cell can be set in `input_*/infectedCell.json`
- `input/fields.json` inserts information for message log parsing to be used with GIS Web viewer v2