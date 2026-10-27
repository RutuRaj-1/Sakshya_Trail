import sys, os, json
sys.path.insert(0, os.path.abspath("."))
from app.main import app

schema = app.openapi()
paths = schema.get('paths', {})

inventory = []
tag_groups = {}

for path, operations in sorted(paths.items()):
    for method, op in operations.items():
        if method.lower() in ('get', 'post', 'put', 'patch', 'delete'):
            tags = op.get('tags', ['Other'])
            primary_tag = tags[0] if tags else 'Other'
            item = {
                'method': method.upper(),
                'path': path,
                'operation_id': op.get('operationId', ''),
                'summary': op.get('summary', ''),
                'description': op.get('description', ''),
                'tags': tags,
                'parameters': [p.get('name') for p in op.get('parameters', [])],
                'has_request_body': bool(op.get('requestBody')),
                'responses': list(op.get('responses', {}).keys())
            }
            inventory.append(item)
            tag_groups.setdefault(primary_tag, []).append(item)

print(f"Total Unique Endpoints: {len(paths)}")
print(f"Total API Operations: {len(inventory)}")
print("\nOperations by Primary Tag:")
for tag, items in sorted(tag_groups.items()):
    print(f"  - {tag}: {len(items)} operations")

out_file = os.path.join("docs", "api_inventory.json")
os.makedirs("docs", exist_ok=True)
with open(out_file, "w", encoding="utf-8") as f:
    json.dump({"total_endpoints": len(paths), "total_operations": len(inventory), "operations": inventory}, f, indent=2)

print(f"\nSaved inventory to: {out_file}")
