import sys
import os
import json
sys.path.insert(0, os.path.abspath('backend'))
from app.api.workstations import list_available_images

images = list_available_images("user-1")
for img in images:
    if img.get("uri") and "{" in img["uri"]:
        try:
            data = json.loads(img["uri"])
            print(f"Loaded json: {data}")
            img["uri"] = data.get("image", img["uri"])
        except Exception as e:
            print(f"Error parsing: {e}")
    print(img)
