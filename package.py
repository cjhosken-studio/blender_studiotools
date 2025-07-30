name = "blender_studiotools"
version = "1.0.0"

build_command = "python {root}/build.py {install}"

def commands():
    env.PYTHONPATH.prepend("{root}/python")