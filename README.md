# Blender Studiotools

**Blender Studiotools** is a Blender addon designed for integration into larger production pipelines.  
It serves as a solid foundation for more advanced addon development.

---

## ⚙️ Features

### Qt Support
- Full support for **Qt** integration within Blender.

### USD Asset Management
- Built primarily to work with **USD (Universal Scene Description)** assets.

### Naming and Tagging Tools
- Provides **simple tools** for consistent naming and tagging of assets.

---

## 🧩 Integrating the Addon

### 1. Simple Method
- Install the addon as a **ZIP file**, just like any other Blender addon.
You will need to make sure that you have `pip install -r requirements.txt` for the addon to work with anything Qt.

### 2. Advanced Method
1. `pip install requirements.txt` for the blender dist
2. Set the `PYTHONPATH` environment variable to point to this folder.
3. Run `load.py` before launching Python:

```bash
blender --python-use-system-env --python path/to/load.py
```

## 🛠 Maintenance
This repository is maintained by [Christopher Hosken](https://cjhosken.github.io)