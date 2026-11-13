import csv
import hashlib
from pathlib import Path
root = Path(__file__).resolve().parent
old = list(csv.DictReader((root / 'control_by_type_amendment_1.csv').open(newline='', encoding='utf-8')))
new = list(csv.DictReader((root / 'control_by_type_amendment_2.csv').open(newline='', encoding='utf-8')))
with (root / 'control_by_type_combined_amendment_2.csv').open('w', newline='', encoding='utf-8') as stream:
    fields = list(old[0])
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader(); writer.writerows(old); writer.writerows(new)
with (root / 'MANIFEST_amendment_2.sha256').open('w', encoding='utf-8') as stream:
    for path in sorted(root.rglob('*')):
        if path.is_file() and path.name not in {'MANIFEST_amendment_2.sha256'}:
            stream.write(f'{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(root)}\n')
