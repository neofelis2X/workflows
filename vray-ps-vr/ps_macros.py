#!/usr/bin/env/ python3
# mypy: disable-error-code="attr-defined"

import os.path
import logging
from typing import Optional, Callable

# pip install pywin32
import win32com.client as win32
from pywintypes import com_error  # pylint: disable=E0611

PS_MM = 4
PS_PIXEL = 1
PS_NORMAL_LAYER = 1
PS_LAYERSET_LAYER = 2
PS_SMART_OBJECT_LAYER = 17
PS_DISPLAY_NO_DIALOGS = 3
PS_BLEND_MODE_SCREEN = 9
PS_BLEND_MODE_MULTIPLY = 5
PS_PHOTOSHOP_SAVE = 1

def update_all_smartlayer(psd_file: os.DirEntry, img_layers: dict[str, os.DirEntry],
                          log: logging.Logger,
                          background: bool = False) -> bool:

    app = _prepare_photoshop(log)
    if not app:
        return False

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

def create_new_psd(img_layers: dict[str, os.DirEntry], output_path: str,
                   log: logging.Logger,
                   bg_layers: Optional[dict[str, os.DirEntry]] = None) -> bool:

    app = _prepare_photoshop(log)
    if not app:
        return False

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


def _prepare_photoshop(log: logging.Logger) -> Optional[Callable]:
    try:
        app = win32.gencache.EnsureDispatch("Photoshop.Application")
    except com_error:
        log.warning("Couldn't access Photoshop. Please make sure that the application is running!")
        return None

    log.debug("Successfully attached photoshop.")

    app.DisplayDialogs = PS_DISPLAY_NO_DIALOGS

    return app

def _insert_render_stack(app: Callable,
                         doc: Callable, img_layers: dict[str, os.DirEntry], groupname:str,
                         log: logging.Logger) -> tuple[str, Callable, Callable, Callable, Callable]:

    base_group = _create_new_group(doc, groupname, log)
    base_layer = _create_new_smart_layer(app, doc, base_group, 'base', log)
    _replace_image_smart_layer(app, img_layers['base'].path)

    if 'Ambient_Occlusion' in img_layers:
        ambient_layer = _create_new_smart_layer(app, doc, base_group, 'ambient', log)
        _replace_image_smart_layer(app, img_layers['Ambient_Occlusion'].path)
        ambient_layer.BlendMode = PS_BLEND_MODE_MULTIPLY
        ambient_layer.Opacity = 70.0

    if 'Glare' in img_layers:
        glare_layer = _create_new_smart_layer(app, doc, base_group, 'glare', log)
        _replace_image_smart_layer(app, img_layers['Glare'].path)
        glare_layer.BlendMode = PS_BLEND_MODE_SCREEN
        glare_layer.Opacity = 40.0

    return (groupname, base_group, base_layer, ambient_layer, glare_layer)


def _create_new_group(doc, name:str, log: logging.Logger) -> Callable:
    group_ref = doc.LayerSets.Add()
    group_ref.Name = name
    log.debug("Created a new group in the photoshop file with the name: %s", name)

    return group_ref

def _create_new_smart_layer(app, doc, group, name:str, log: logging.Logger) -> Callable:
    layer_ref = group.ArtLayers.Add()
    layer_ref.Kind = PS_NORMAL_LAYER

    desc = win32.gencache.EnsureDispatch('Photoshop.ActionDescriptor')  # empty descriptor
    app.ExecuteAction(app.StringIDToTypeID("newPlacedLayer"), desc, PS_DISPLAY_NO_DIALOGS)

    layer_ref = doc.ActiveLayer
    layer_ref.Name = name
    log.debug("Created a new smart object in the photoshop file with the name: %s", name)

    return layer_ref

def _replace_image_smart_layer(app: Callable, new_img_path: str) -> None:
    id_replace = app.StringIDToTypeID('placedLayerReplaceContents')
    desc = win32.gencache.EnsureDispatch('Photoshop.ActionDescriptor')  # empty descriptor
    desc.PutPath(app.CharIDToTypeID('null'), new_img_path)
    app.ExecuteAction(id_replace, desc, PS_DISPLAY_NO_DIALOGS)


if __name__ == "__main__":

    layers = {'base': '',}
    OUT_PATH = ""

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger('ps_macros')
    logger.setLevel(logging.DEBUG)

    create_new_psd(layers, OUT_PATH, logger)  # type: ignore
