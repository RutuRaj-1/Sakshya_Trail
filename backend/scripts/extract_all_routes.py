import sys, os
sys.path.insert(0, os.path.abspath("."))
from app.main import app
from fastapi.routing import APIRoute

routes = []

def collect_routes(router, prefix=""):
    for route in router.routes:
        if isinstance(route, APIRoute):
            full_path = prefix + route.path
            methods = ','.join(m for m in sorted(route.methods) if m not in ('HEAD', 'OPTIONS'))
            routes.append({
                'path': full_path,
                'name': route.name,
                'methods': methods,
                'endpoint': route.endpoint.__name__,
                'tags': route.tags
            })
        elif hasattr(route, 'routes'):
            collect_routes(route, prefix=prefix + getattr(route, 'prefix', ''))

collect_routes(app)

print(f"Total Registered API Routes: {len(routes)}")
for r in sorted(routes, key=lambda x: (x['path'], x['methods'])):
    tags = ','.join(r['tags']) if r['tags'] else 'no-tag'
    print(f"{r['methods']:8} {r['path']:60} [{tags:25}] -> {r['endpoint']}")
