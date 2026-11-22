#!/usr/bin/env python3
"""Build the published ads snapshot with the repository's locked public sources."""
from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).resolve().parents[2] / 'maintenance/build_ads.py'), run_name='__main__')
