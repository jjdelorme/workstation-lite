import json

user_ns = "user-1"
physical_images = [
  {
    "uri": "us-central1-docker.pkg.dev/jasondel-cloudrun10/workstation-images/user-1-openvs-workstation@sha256:8d57b38f92d2618ccc19c6a6f1b943fd0dd3d577c1350f4548a1570cfc8ac81f",
    "tags": ["latest"],
    "update_time": "2026-04-02T14:04:15.952191+00:00",
    "media_type": "application/vnd.docker.distribution.manifest.v2+json"
  },
  {
    "uri": "us-central1-docker.pkg.dev/jasondel-cloudrun10/workstation-images/user-1-vscodium-image@sha256:19e1ee2ce8a946ac7f8de6c40bf613398e21768b0ec9f1888fd88a78f053a8a7",
    "tags": ["latest"],
    "update_time": "2026-04-02T16:28:07.677535+00:00",
    "media_type": "application/vnd.docker.distribution.manifest.v2+json"
  }
]

recipes = {
  "vscodium-image": {
    "uri": "us-central1-docker.pkg.dev/jasondel-cloudrun10/workstation-images/user-1-vscodium-image:latest",
    "tags": ["vscodium-image"],
    "update_time": None,
    "is_recipe": True,
    "has_dockerfile": True
  }
}

final_list = []
seen_uris = set()

def get_base_uri(uri):
    if not uri: return ""
    return uri.split('@')[0].split(':')[0]

physical_by_base = {}
for img in physical_images:
    base = get_base_uri(img["uri"])
    if base not in physical_by_base or (img.get("update_time") and physical_by_base[base].get("update_time") and img["update_time"] > physical_by_base[base]["update_time"]):
        physical_by_base[base] = img

for name, data in recipes.items():
    base_uri = get_base_uri(data["uri"])
    if base_uri in physical_by_base:
        match = physical_by_base[base_uri]
        data["update_time"] = match["update_time"]
        data["uri"] = match["uri"]
        seen_uris.add(base_uri)
    final_list.append(data)

for base, img in physical_by_base.items():
    if base not in seen_uris:
        repo_path = base.split('/')[-1]
        name = repo_path
        prefix = f"{user_ns}-"
        if name.startswith(prefix):
            name = name[len(prefix):]
        
        final_list.append({
            **img,
            "tags": [name],
            "is_recipe": False,
            "has_dockerfile": False
        })

print(json.dumps(final_list, indent=2))
