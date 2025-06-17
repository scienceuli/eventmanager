import json

with open('data.json') as f:
    data = json.load(f)

filtered = [
    entry for entry in data
    if not (
        entry['model'].startswith('admi.logentry') 
    )
]

with open('filtered_data.json', 'w') as f:
    json.dump(filtered, f, indent=2)

