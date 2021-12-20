from argparse import ArgumentParser

import json


def make_structure(scenario, fields):
    scenario["cells"].pop("default", None)

    components = [{"id": key, "model_type": 1} for (key, value) in scenario["cells"].items()]

    components.insert(0, {"id": "top", "model_type": 0})

    model_types = [{
        "id": 0,
        "components": [i for i in range(1, len(scenario["cells"]) + 1)],
        "couplings": [],
        "name": "top",
        "ports": [],
        "type": "top"
    }, {
        "id": 1,
        "message_type": 0,
        "name": "cell",
        "ports": [],
        "type": "atomic"
    }]

    return {
        "formalism": "GIS-DEVS",
        "simulator": "Cadmium",
        "top": 0,
        "components": components,
        "model_types": model_types,
        "message_types": [{
            "description": "No description available.",
            "id": 0,
            "name": "s_model",
            "template": fields
        }]
    }


def process_line(f_messages, structure, line):
    sp = line.strip().split(" ")

    if len(sp) == 1:
        f_messages.write(sp[0] + '\n')

    else:
        # State for model _8 is <1.39902e+09,0.999999,5.99972e-07,0,0,0,0,5.99972e-07,0,0,0>
        id = sp[3][1:len(sp[3])]
        data = sp[5][1:len(sp[5]) - 1]
        component = next((c for c in structure["components"] if c["id"] == id), None)

        if component is None:
            raise ValueError('Unable to find message model component in structure.')

        index = structure["components"].index(component)

        f_messages.write(str(index) + ";" + data + '\n')


if __name__ == '__main__':
    print("\nReading arguments...")
    parser = ArgumentParser(description='This script converts Cadmium Irregular Cell-DEVS results into the viewer format.')

    parser.add_argument('--scenario', dest='scenario', type=str, help='Path to the scenario file (.json)', required=True)
    parser.add_argument('--state', dest='state', type=str, help='Path to the state output file (.txt)', required=True)
    parser.add_argument('--fields', dest='fields', type=str, nargs="*", help='state fields output by the model. Length must match the length of state messages.', required=True)

    args = parser.parse_args()

    #print("Reading input files...")
    scenario = json.load(open(args.scenario))
    state = open(args.state, 'r')

    #print("Preparing structure file...")
    structure = make_structure(scenario, args.fields)

    with open('./output/structure.json', 'w') as f_structure:
        json.dump(structure, f_structure)

    #print("Preparing messages log...")
    with open('./output/messages.log', 'w') as f_messages:
        for line in state:
            process_line(f_messages, structure, line)

    #print("Done.")
    #print("\nFiles are in ./output/")
