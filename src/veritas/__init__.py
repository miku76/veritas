# read version from installed package
from importlib.metadata import version

__version__ = version("veritas")

# disable logger
# the user can enable the logger later
# logger.disable("veritas")
