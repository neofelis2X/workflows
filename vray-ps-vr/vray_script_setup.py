#!/usr/bin/env/ python3
'''
Author: Matthias Kneidinger
Copyright: 2024, GPLv3

This script is intended to run inside Rhino3D and access the VRay
rendering module.
Carrier names, base path and settings file path have to be provided
via the local_secrets module as string constants.
The script checks which vendor/carrier is currently loaded. Then checks
the latest folder with renderings and creates a new folder.
Loads the specified render settings.
Then it lists all saved views that start with 'r_' and renders them
to the created folder.

https://docs.chaos.com/display/VRHINO/V-Ray+Script+Access
To use the V-Ray for Rhino wrapper module, add a new Python
Module Search path (Tools/Options/Python 3) pointing to:
"C:\\Program Files\\Chaos Group\\V-Ray\\V-Ray for Rhinoceros"

RenderModes
RM_PRODUCTION     0   Renders in production mode
RM_INTERACTIVE    1   Renders in interactive mode
RM_CLOUD          2   Starts the current render job on the Cloud
RM_LAST           3   Repeats the last render

RenderEngines
RE_CPU    0   Renders on the CPU
RE_CUDA   1   Renders on the GPU and/or CPU using CUDA
RE_RTX    2   Renders on the GPU using RTX Optix

Functions
---------
render_scene(bool)
    Runs the whole script
'''

import os.path
from datetime import datetime
import logging

import rhinoscriptsyntax as rs
import rh8VRay as vray

import local_secrets as secrets

VR_RENDERSETTINGS = os.path.normpath(secrets.VR_SETTINGS_PATH)
NORMAL_RENDERSETTINGS = os.path.normpath(secrets.STD_SETTINGS_PATH)
BASE_PATH = os.path.normpath(secrets.BASE_PATH)
CARRIER = secrets.CARRIER
FILENAME = rs.DocumentName()
FILEPATH = rs.DocumentPath()

def _setup_logging(dir_path: str) -> logging.Logger:
    logger = logging.getLogger('vray-mang')
    logger.setLevel(logging.DEBUG)

    log_path = os.path.join(dir_path, 'vray_render.log')
    handler = logging.FileHandler(log_path, mode='a')
    formatter = logging.Formatter('%(asctime)s: %(name)s: %(levelname)s: %(message)s')

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    logger.debug("Logger has been set up. Path to log file:")
    logger.debug(log_path)

    return logger

def _close_logging(log: logging.Logger) -> None:
    log.debug("Closing logger, final message.")

    for handler in log.handlers:
        log.removeHandler(handler)
        handler.close()

def _render_view(view: str, log: logging.Logger) -> None:
    rs.RestoreNamedView(view)
    rs.Redraw()

    t_start = datetime.now()
    log.info(f"Start render at: {t_start}")

    vray.Render(0, 1, -1)

    t_end = datetime.now()
    log.info(f"Finished render at: {t_end}")
    diff = t_end - t_start
    log.info(f"Render took: {round(diff.total_seconds(), 2)} s")

    vray.RefreshUI()

def _change_save_path(dirpath: str, filename: str, fileending: str, log: logging.Logger) -> None:
    path = os.path.join(dirpath, filename + fileending)
    log.info("Output file name: %s", filename + fileending)
    log.debug("Output file path: %s", path)

    with vray.Scene.Transaction() as t:
        vray.Scene.SettingsOutput.save_render_path = path
        vray.Scene.SettingsOutput.img_file = path
        vray.Scene.SettingsOutput.img_dir = path

def _determine_carrier(filename: str) -> str:
    segments = filename.split('_')
    carrier = segments[1]

    if not carrier in CARRIER:
        return ''

    return carrier

def _get_date_formatted() -> str:
    current_datetime = datetime.now()
    current_day_date = current_datetime.strftime("%y%m%d")

    return current_day_date

def _get_output_path() -> str:
    index = 0
    carrier = _determine_carrier(FILENAME)
    if not carrier:
        print("ERROR: Could not determine a valid carrier.")
        return ''

    print("INFO: Current carrier is: ", carrier )

    current_date = _get_date_formatted()
    out_dir = ''.join((current_date, 'v', str(index)))
    out_path = os.path.join(BASE_PATH, carrier, 'renderings', out_dir)

    if os.path.isdir(out_path):
        print('INFO: This directory already exists. A new version will be created.')
        index = _determine_version_number(carrier)
        out_dir = ''.join((current_date, 'v', str(index)))
        out_path = os.path.join(BASE_PATH, carrier, 'renderings', out_dir)
        print('INFO: Changed directory name to: ', out_dir)

    return out_path

def _determine_version_number(carrier: str) -> int:
    latest_dir = _get_latest_entry(os.path.join(BASE_PATH, carrier, 'renderings'))
    latest_index = int(latest_dir[7])
    return latest_index + 1

def _get_latest_entry(path: str) -> str:
    entry_list = []
    with os.scandir(path) as it:
        for entry in it:
            if entry.is_dir():
                entry_list.append(entry.name)

    if not entry_list:
        return ''

    entry_list.sort(reverse=True)

    return entry_list[0]

def _get_renderfile_name(viewname: str) -> str:
    segments = viewname.split('_')
    return segments[2]

def _restore_layer_state(state: str) -> bool:
    # RestoreLayerState currently does not work in Rh8!
    plugin = rs.GetPlugInObject("Rhino Bonus Tools")
    print(plugin)
    if plugin is not None:
        # plugin.RestoreLayerState(state, 0)
        return True
    return False

def _load_vray_settings(filepath: str, log: logging.Logger) -> bool:
    success = vray.Scene.LoadSettings(filepath)
    filename = os.path.basename(filepath)

    if not success:
        log.debug("Failed to load settings file: %s", filename)
        return False

    log.debug("Successfully loaded settings file: %s", filename)
    return True

def render_scene(do_render: bool = False) -> bool:
    '''
    Create a new directory for today and render
    all views that are marked with 'r_'.

    Parameters
    ----------
    do_render : bool
        Set to false to skip the actual rendering step, useful for testing

    Returns
    -------
    bool
        True on success, False on error
    '''
    print('Starting rendering script. Logging to file.')

    path = _get_output_path()
    if not path:
        return False

    os.mkdir(path)

    logger = _setup_logging(path)
    logger.info("VRay Version: %s, Core: %s", vray.Version, vray.VRayVersion)

    cuda_devices = vray.GetDeviceList(vray.RenderEngines.RE_CUDA)

    for device in cuda_devices:
        logger.info("Found render device: %s", device.Name)
        if 'NVIDIA' in device.Name or 'CPU' in device.Name:
            use = device.UseForRendering
            logger.debug("Device is marked for use: %s - %s", device.Name, use)

    _load_vray_settings(VR_RENDERSETTINGS, logger)

    #params = vray.Scene.SettingsOutput.ParamNames
    #for par in params:
    #    print(par)

    with vray.Scene.Transaction() as tr:
        #vray.Scene.SettingsOutput.img_width = 384
        #vray.Scene.SettingsOutput.img_height = 64
        vray.Scene.SettingsOutput.save_render = 1
        vray.Scene.SettingsOutput.img_noAlpha = 0

    success = vray.SetDeviceList(vray.RenderEngines.RE_CUDA, [0, 1])

    _restore_layer_state('ex')

    views = rs.NamedViews()
    if views:
        for view in views:
            if view.startswith('r_') and '_ex_' in view:
                logger.info("Setting up view: %s", view)
                out_name = _get_renderfile_name(view)
                _change_save_path(path, out_name, '.png', logger)
                if do_render:
                    _render_view(view, logger)

    _load_vray_settings(NORMAL_RENDERSETTINGS, logger)
    _close_logging(logger)
    print('Finishing rendering script.')
    return True

render_scene(True)
# _restore_layer_state('str')

if __name__ == "__main__":
    pass
