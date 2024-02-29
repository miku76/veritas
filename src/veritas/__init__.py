# read version from installed package
from importlib.metadata import version
from loguru import logger

__version__ = version("veritas")

# disable logger
# the user can enable the logger later
logger.disable("veritas.sot")
logger.disable("veritas.onboarding")
logger.disable("veritas.inventory")
logger.disable("veritas.profile")
