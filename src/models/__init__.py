import glob
import os

__all__ = []
for f in glob.glob(os.path.dirname(os.path.realpath(__file__)) + "/*.py"):
    model = os.path.basename(f)
    if model != '__init__.py':
        __all__.append(model.split('.')[0])
