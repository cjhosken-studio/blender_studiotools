name = "blender_studiotools"
version = "1.0.0"

requires = [
    "python-3.11",
    "blender",
    "PySide6"
]

build_command = "python {root}/build.py {install}"

def commands():
    env.PYTHONPATH.prepend("{root}/python")