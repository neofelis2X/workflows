#!/usr/bin/env/ python3
# Create a new art layer and convert it to a text layer.
# Set its contents, size and color.
# make sure to: pip install pywin32
import win32com.client as win32

def add_lensflare_to_layer():
    # Start up Photoshop application
    # Or get Reference to already running Photoshop application instance
    app = win32.gencache.EnsureDispatch("Photoshop.Application")

    if len([(i, x) for i, x in enumerate(app.Documents, 1)]) < 1:
        sys.exit()
    else:
        docRef = app.ActiveDocument

    active_layer = docRef.ActiveLayer

    psNormalLayer = 1  # from enum PsLayerKind
    psSmartObjectLayer = 17  # from enum PsLayerKind

    psMoviePrime = 5  # from enum PsLensType
    psPrime105 = 3  # from enum PsLensType
    psPrime35 = 2  # from enum PsLensType
    psZoomLens = 1  # from enum PsLensType

    blend_brightness = 10  # in percent
    blend_pos = (0, 0)

    if active_layer.Kind in (psNormalLayer, psSmartObjectLayer):
        for item in docRef.CountItems:
            blend_pos = item.Position
            active_layer.ApplyLensFlare(blend_brightness, blend_pos, psPrime105)
            blend_brightness -= 0


if __name__ == "__main__":
    add_lensflare_to_layer()
    print('Script completed.')
