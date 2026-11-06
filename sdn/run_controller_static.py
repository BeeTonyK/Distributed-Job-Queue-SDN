#!/usr/bin/env python3
"""Run the fixed-primary-path controller as a static comparison baseline."""
import os

from os_ken.base.app_manager import AppManager


if __name__ == "__main__":
    os.environ["TEAM3_STATIC_BASELINE"] = "1"
    AppManager.run_apps(["team3_controller"])
