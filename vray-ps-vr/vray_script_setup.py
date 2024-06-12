#!/usr/bin/env/ python3

import os.path
import time
from datetime import datetime

import rhinoscriptsyntax as rs
import rh8VRay as vray

print("VRay Version: ", vray.Version, "Core: ", vray.VRayVersion)

VRTOUR_RENDERSETTINGS = ""
OUTPUT_PATH = os.path.normpath(
              "C:\\Users\\Matthias Kneidinger\\Downloads\\photoshop_python\\test\\")

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

def render_view():
    t_start = datetime.now()
    print(f"Start render at: {t_start}")

    vray.Render(0, 1, -1)

    t_end = datetime.now()
    print(f"Finished render at: {t_end}")
    diff = t_end - t_start
    print(f"Render took: {round(diff.total_seconds(), 2)} s")

    vray.RefreshUI()

def change_save_path(filename: str, fileending: str):
    path = os.path.join(OUTPUT_PATH, filename + fileending)
    print(path)

    with vray.Scene.Transaction() as t:
        vray.Scene.SettingsOutput.save_render_path = path
        vray.Scene.SettingsOutput.img_file = path
        vray.Scene.SettingsOutput.img_dir = path

cudaDevices = vray.GetDeviceList(vray.RenderEngines.RE_CUDA)

for device in cudaDevices:
    print(device.Name)
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
        print(f"Current view: {view}")
        change_save_path(view, '.png')
        rs.RestoreNamedView(view)
        rs.Redraw()
        render_view()

