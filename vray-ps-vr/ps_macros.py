#!/usr/bin/env/ python3

# pip install pypiwin32
from win32com.client import Dispatch, GetActiveObject
import os.path
import logging

PS_MM = 4
PS_PIXEL = 1
PS_NORMAL_LAYER = 1
PS_LAYERSET_LAYER = 2
PS_SMART_OBJECT_LAYER = 17
PS_DISPLAY_NO_DIALOGS = 3
PS_BLEND_MODE_SCREEN = 9
PS_BLEND_MODE_MULTIPLY = 5
PS_PHOTOSHOP_SAVE = 1

def update_all_smartlayer(psd_file, img_layers, log, background = False):
    app = _prepare_photoshop(log)
    if not app:
        return

    doc = app.Open(psd_file.path)

    group = None
    group_to_find = 'background' if background else 'content'

    for ls in doc.LayerSets:
        if ls.Name == group_to_find:
            group = ls
            break

    if not group:
        doc.Close()
        return False

    else:
        for layer in group.ArtLayers:
            doc.ActiveLayer = layer
            if layer.Name == 'base':
                _replace_image_smart_layer(app, img_layers['base'].path)
            elif layer.Name == 'glare':
                _replace_image_smart_layer(app, img_layers['Glare'].path)
            elif layer.Name == 'ambient':
                _replace_image_smart_layer(app, img_layers['Ambient_Occlusion'].path)

    doc.Save()
    doc.Close()

    return True

def create_new_psd(img_layers, output_path, log, bg_layers = None):
    app = _prepare_photoshop(log)
    if not app:
        return

    filename = os.path.basename(img_layers['base'])
    filename = os.path.splitext(filename)[0]
    output_file = os.path.join(output_path, filename + '.psd')

    if os.path.isfile(output_file):
        log.error("Attention: This file already exists! Overwriting is not allowed.")
        log.error("Please check the file and rename or delete it manually.")
        log.error(output_file)
        return False

    start_ruler_units = app.Preferences.RulerUnits
    app.Preferences.RulerUnits = PS_PIXEL

    # Open image file to get its resolution via photoshop
    doc = app.Open(img_layers['base'].path)
    width, height = doc.Width, doc.Height
    doc.Close()

    doc_ref = app.Documents.Add(width, height, 72.0, filename)
    log.debug("Created new document in photoshop with the name: '%s'" % filename)

    _insert_render_stack(app, doc_ref, img_layers, 'content', log)

    if bg_layers:
        _insert_render_stack(app, doc_ref, bg_layers, 'background', log)

    doc_ref.SaveAs(output_path)
    doc_ref.Close()
    log.info("Created and saved file: %s.psd" % filename)

    # Make sure to set the ruler units prior to creating the document.
    app.Preferences.RulerUnits = start_ruler_units

    return True


def _prepare_photoshop(log):
    try:
        app = GetActiveObject("Photoshop.Application")
    except:
        log.warning("Couldn't access Photoshop. Please make sure that the application is running!")
        return False

    log.debug("Successfully attached photoshop.")

    app.DisplayDialogs = PS_DISPLAY_NO_DIALOGS

    return app

def _insert_render_stack(app, doc, layers, groupname:str, log):
    base_group = _create_new_group(doc, groupname, log)
    base_layer = _create_new_smart_layer(app, doc, base_group, 'base', log)
    _replace_image_smart_layer(app, layers['base'].path)

    if 'Ambient_Occlusion' in layers:
        ambient_layer = _create_new_smart_layer(app, doc, base_group, 'ambient', log)
        _replace_image_smart_layer(app, layers['Ambient_Occlusion'].path)
        ambient_layer.BlendMode = PS_BLEND_MODE_MULTIPLY
        ambient_layer.Opacity = 70.0

    if 'Glare' in layers:
        glare_layer = _create_new_smart_layer(app, doc, base_group, 'glare', log)
        _replace_image_smart_layer(app, layers['Glare'].path)
        glare_layer.BlendMode = PS_BLEND_MODE_SCREEN
        glare_layer.Opacity = 40.0

    return [groupname, base_group, base_layer, ambient_layer, glare_layer]


def _create_new_group(doc, name:str, log):
    group_ref = doc.LayerSets.Add()
    group_ref.Name = name

    return group_ref

def _create_new_smart_layer(app, doc, group, name:str, log):
    layer_ref = group.ArtLayers.Add()
    layer_ref.Kind = PS_NORMAL_LAYER

    desc = Dispatch('Photoshop.ActionDescriptor')  # empty descriptor
    app.ExecuteAction(app.StringIDToTypeID("newPlacedLayer"), desc, PS_DISPLAY_NO_DIALOGS)

    layer_ref = doc.ActiveLayer
    layer_ref.name = name

    return layer_ref

def _replace_image_smart_layer(app, new_img_path: str):
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

