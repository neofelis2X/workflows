#!/usr/bin/env/ python3

# pip install pypiwin32
#from comtypes.client import GetActiveObject
from win32com.client import Dispatch, GetActiveObject
import logging

PS_MM = 4
PS_PIXEL = 1
PS_NORMAL_LAYER = 1
PS_SMART_OBJECT_LAYER = 17
PS_DISPLAY_NO_DIALOGS = 3

def update_all_smartlayer(file, images, log):
    raise NotImplementedError

def create_new_psd(image_layers, log):
    app = _prepare_photoshop(log)
    if not app:
        return

    start_ruler_units = app.Preferences.RulerUnits
    app.Preferences.RulerUnits = PS_PIXEL

    filename = "my test doc"
    docRef = app.Documents.Add(40, 40, 72.0, filename)
    log.debug("Created new document in photoshop with the name: '%s'" % filename)

    new_layer = _create_new_smart_layer(app, docRef, 'smartlayer', log)

    #new_layer.blendMode = 3

    new_path = "c:\\Users\\Matthias Kneidinger\\Downloads\\4795-specstrength.jpg"
    _replace_image_smart_layer(app, new_layer, new_path)

    # Make sure to set the ruler units prior to creating the document.
    app.Preferences.RulerUnits = start_ruler_units


def _prepare_photoshop(log):
    try:
        app = GetActiveObject("Photoshop.Application")

    except:
        log.warning("Couldn't access Photoshop. Please make sure the application is running!")
        return False

    log.debug("Successfully attached photoshop.")


    app.displayDialogs = PS_DISPLAY_NO_DIALOGS

    return app

def _create_new_smart_layer(app, doc, name:str, log):
    layerRef = doc.ArtLayers.Add()
    layerRef.name = name
    layerRef.Kind = PS_NORMAL_LAYER

    desc = Dispatch('Photoshop.ActionDescriptor')  # empty descriptor
    app.ExecuteAction(app.StringIDToTypeID("newPlacedLayer"), desc, PS_DISPLAY_NO_DIALOGS)

    return layerRef

def _replace_image_smart_layer(app, layer, new_img_path: str):
    id_replace = app.StringIDToTypeID('placedLayerReplaceContents');
    desc = Dispatch('Photoshop.ActionDescriptor')  # empty descriptor
    desc.PutPath(app.CharIDToTypeID('null'), new_img_path)
    app.ExecuteAction(id_replace, desc, PS_DISPLAY_NO_DIALOGS);


if __name__ == "__main__":

    layers = []

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger('ps_macros')
    logger.setLevel(logging.DEBUG)

    create_new_psd(layers, logger)

