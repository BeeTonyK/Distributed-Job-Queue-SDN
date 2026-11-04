import logging
from os_ken.base.app_manager import AppManager

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    AppManager.run_apps(["team3_controller"])
