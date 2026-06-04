import os

try:
    import bpy
    IN_BLENDER = True
except ImportError:
    IN_BLENDER = False

def poll_web_connection():
    task_path = os.environ.get("ST_CWD")
    if not task_path:
        return 1.0  # Try again in 1s
        
    try:
        import urllib.request
        import urllib.parse
        import json
        
        url = f"http://localhost:8000/api/sessions/poll?appType=blender&taskPath={urllib.parse.quote(task_path)}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=0.2) as response:
            res = json.loads(response.read().decode())
            commands = res.get("commands", [])
            for cmd in commands:
                if cmd.get("command") == "load_usd":
                    filepath = cmd.get("argument")
                    if os.path.exists(filepath):
                        bpy.ops.wm.usd_import(filepath=filepath)
                        print(f"[Studio Tools] Web Connection: Loaded published USD asset: {filepath}")
    except Exception:
        pass  # Safe silence to avoid console spam if server is offline
        
    return 0.5  # Poll every 500ms
