"""alert-triage-economics: measure what a tuning change costs in missed detections."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("alert-triage-economics")
except PackageNotFoundError:  # running from a source tree without an install
    __version__ = "0.0.0+unknown"
