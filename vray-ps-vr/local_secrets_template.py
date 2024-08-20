#!/usr/bin/env/ python3
'''
Author: Matthias Kneidinger
Copyright: 2024, GPLv3
Constant strings that should not be uploaded to GitHub.
Provides enviroment data for the project.

Rename this file to local_secrets.py and enter your own paths.
'''

BASE_PATH = "path"
CARRIER = ('NAME1', 'NAME2', 'BACKGROUNDS', 'ALL')
KRPANO_PATH = "path"
VR_SETTINGS_PATH = "path.vropt"
STD_SETTINGS_PATH = "path.vropt"

if __name__ == "__main__":
    print("This are the local settings for this machine")
    print(BASE_PATH)
    print(CARRIER)
    print(KRPANO_PATH)
    print(VR_SETTINGS_PATH)
    print(STD_SETTINGS_PATH)
