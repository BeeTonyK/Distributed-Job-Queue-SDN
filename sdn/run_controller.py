#!/usr/bin/env python3
"""Start the adaptive Team 3 D2 controller from the sdn directory."""
import os

from os_ken.base.app_manager import AppManager


if __name__ == "__main__":
    os.environ.pop("TEAM3_STATIC_BASELINE", None)
    AppManager.run_apps(["team3_controller"])
