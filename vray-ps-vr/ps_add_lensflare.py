#!/usr/bin/env/ python3
# Create a new art layer and convert it to a text layer.
# Set its contents, size and color.
# make sure to: pip install pywin32
import win32com.client as win32
from pywintypes import com_error  # pylint: disable=E0611

PS_NORMAL_LAYER = 1  # from enum PsLayerKind
PS_SMART_OBJECTLAYER = 17  # from enum PsLayerKind

PS_MOVIE_PRIME = 5  # from enum PsLensType
PS_PRIME_105 = 3  # from enum PsLensType
PS_PRIME_35 = 2  # from enum PsLensType
PS_ZOOM_LENS = 1  # from enum PsLensType

def add_lensflare_to_layer():
    # Start up Photoshop application
    # Or get Reference to already running Photoshop application instance
    app = win32.gencache.EnsureDispatch("Photoshop.Application")

    try:
        doc_ref = app.ActiveDocument
    except com_error:
        print('No active document.')
        return False

    active_layer = doc_ref.ActiveLayer

    blend_brightness = 10  # in percent
    blend_pos = (0, 0)

    if active_layer.Kind in (PS_NORMAL_LAYER, PS_SMART_OBJECTLAYER):
        for item in doc_ref.CountItems:
            blend_pos = item.Position
            active_layer.ApplyLensFlare(blend_brightness, blend_pos, PS_PRIME_105)
            blend_brightness -= 0

    return True


if __name__ == "__main__":
    success = add_lensflare_to_layer()

    if success:
        print('Script completed.')
    else:
        print('Attention: Script failed.')
