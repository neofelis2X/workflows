#!/usr/bin/env/ python3

import os.path
from datetime import datetime
import logging

import rhinoscriptsyntax as rs
import rh8VRay as vray

import local_secrets as secrets

VRTOUR_RENDERSETTINGS = ""
BASE_PATH = os.path.normpath(secrets.BASE_PATH)
CARRIER = secrets.CARRIER
FILENAME = rs.DocumentName()
FILEPATH = rs.DocumentPath()

# https://docs.chaos.com/display/VRHINO/V-Ray+Script+Access
# To use the V-Ray for Rhino wrapper module, add a new Python
# Module Search path (Tools/Options/Python 3) pointing to:
# C:\Program Files\Chaos Group\V-Ray\V-Ray for Rhinoceros

# RenderModes
# RM_PRODUCTION     0   Renders in production mode
# RM_INTERACTIVE    1   Renders in interactive mode
# RM_CLOUD          2   Starts the current render job on the Cloud
# RM_LAST           3   Repeats the last render

# RenderEngines
# RE_CPU    0   Renders on the CPU
# RE_CUDA   1   Renders on the GPU and/or CPU using CUDA
# RE_RTX    2   Renders on the GPU using RTX Optix

def render_view(log: logging.Logger):
    t_start = datetime.now()
    log.info(f"Start render at: {t_start}")

    vray.Render(0, 1, -1)

    t_end = datetime.now()
    log.info(f"Finished render at: {t_end}")
    diff = t_end - t_start
    log.info(f"Render took: {round(diff.total_seconds(), 2)} s")

    vray.RefreshUI()

def change_save_path(filename: str, fileending: str, log: logging.Logger):
    path = os.path.join(BASE_PATH, filename + fileending)
    log.debug("Output file path: %s", path)

    with vray.Scene.Transaction() as t:
        vray.Scene.SettingsOutput.save_render_path = path
        vray.Scene.SettingsOutput.img_file = path
        vray.Scene.SettingsOutput.img_dir = path

def determine_carrier(filename: str, log: logging.Logger) -> str:
    segments = filename.split('_')
    carrier = segments[1]
    if carrier in CARRIER:
        log.info("Current carrier: ", carrier)
        return carrier
    return ''

def get_date_formatted(log: logging.Logger) -> str:
    current_datetime = datetime.now()
    current_day_date = current_datetime.strftime("%y%m%d")
    log.info("Formatted date: %s", current_day_date)

def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s: %(name)s: %(levelname)s: %(message)s')
    logger = logging.getLogger('vray-mang')


    logger.info("VRay Version: %s, Core: %s", vray.Version, vray.VRayVersion)

    cudaDevices = vray.GetDeviceList(vray.RenderEngines.RE_CUDA)

    for device in cudaDevices:
        logger.debug("Found render device: %s", device.Name)
        if 'NVIDIA' in device.Name:
            use = device.UseForRendering

    # success = vray.Scene.LoadSettings(VRTOUR_RENDERSETTINGS)

    params = vray.Scene.SettingsOutput.ParamNames
    for par in params:
        pass
        #print(par)

    with vray.Scene.Transaction() as tr:
        vray.Scene.SettingsOutput.img_width = 800
        vray.Scene.SettingsOutput.img_height = 400
        vray.Scene.SettingsOutput.save_render = 1
        vray.Scene.SettingsOutput.img_noAlpha = 0

    success = vray.SetDeviceList(vray.RenderEngines.RE_CUDA, [0, 1])

    views = rs.NamedViews()
    if views:
        for view in views:
            logger.debug("Current view: %s", view)
            change_save_path(view, '.png', logger)
            rs.RestoreNamedView(view)
            rs.Redraw()
            render_view(logger)

main()

if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger('vray-mang')
    logger.setLevel(logging.DEBUG)

    get_date_formatted(logger)
