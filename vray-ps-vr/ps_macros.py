#!/usr/bin/env/ python3
# mypy: disable-error-code="attr-defined"

'''
Author: Matthias Kneidinger
Copyright: 2024, GPLv3

This module provides functions to connect to photoshop
and run certain actions inside it.

Warnings
--------
This module uses win32 and only works on windows.
make sure to: pip install pywin32

See Also
--------
https://github.com/lohriialo/photoshop-scripting-python

Functions
---------
update_all_smartlayer()
    Opens a psd file, searches for specified group name
    and layer name and then replaces the layer with the
    latest available rendering
create_new_psd()
    Collects rendering files from the base path, creates
    a new file with smart object layers and inserts the
    renderings with the correct settings

'''

import os
import os.path
import logging
from typing import Optional, Callable

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
PS_LOWERCASE = 2
PS_JPEG_SAVE = 6
PS_NO_MATTE = 1
PS_WHITE_MATTE = 4
PS_OPTIMIZED_BASELINE = 2

def save_jpeg(psd_file: os.DirEntry,
              log: logging.Logger,
              output_dir: str = '') -> str:

    '''
    Saves a given .psd as a .jpg.
    JPEG options are static for this usecase.

    Parameters
    ----------
    psd_file: os.DirEntry
        Which psd to save as jpeg
    log: logging.Logger
    output_dir: str
        Optional output directory path
        Otherwise same as input path

    Returns
    -------
    None
    '''

    app = _prepare_photoshop(log)
    if not app:
        return ''
    doc = app.Open(psd_file.path)

    if output_dir:
        output_path = os.path.join(output_dir, psd_file.name[:-4] + '.jpg')
    else:
        output_path = psd_file.path[:-4] + '.jpg'

    _save_as_jpg(doc, output_path, log)

    doc.Close()

    return output_path

def _save_as_jpg(ps_doc,
                 output_file_path,
                 log: logging.Logger) -> None:

    if not os.path.isdir(os.path.dirname(output_file_path)):
        os.mkdir(os.path.dirname(output_file_path))

    jpeg_options = win32.gencache.EnsureDispatch('Photoshop.JPEGSaveOptions')
    jpeg_options.EmbedColorProfile = True
    jpeg_options.FormatOptions = PS_OPTIMIZED_BASELINE
    jpeg_options.Matte = PS_WHITE_MATTE
    jpeg_options.Quality = 12

    ps_doc.SaveAs(output_file_path, jpeg_options, AsCopy=True, ExtensionType=PS_LOWERCASE)
    log.debug("Saved file: %s" % output_file_path)

def update_all_smartlayer(psd_file: os.DirEntry,
                          img_layers: dict[str, os.DirEntry],
                          log: logging.Logger,
                          background: bool = False) -> bool:
    '''
    Replace the images of all specified smart object layers

    Parameters
    ----------
    psd_file: os.DirEntry
        Which psd to update
    img_layers: dict[str, os.DirEntry]
        A dictionary with different layers of a rendering
    log: logging.Logger
    background: bool = False
        If True, updates the background group, otherwise
        the main content group

    Returns
    -------
    bool
    '''

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

    output_name = psd_file.name[:-4] + '.jpg'
    output_path = os.path.join(os.path.dirname(psd_file.path), 'JPEG', output_name)
    _save_as_jpg(doc, output_path, log)

    doc.Close()

    return True

def create_new_psd(img_layers: dict[str, os.DirEntry],
                   output_path: str,
                   log: logging.Logger,
                   bg_layers: Optional[dict[str, os.DirEntry]] = None) -> bool:
    '''
    Creates a new psd file in the right directory based
    on the latest rendered images

    Parameters
    ----------
    img_layers: dict[str, os.DirEntry]
        A dictionary with different layers of a rendering
    output_path: str
    log: logging.Logger
    bg_layers: Optional[dict[str, os.DirEntry]]
        Also add a background group to the psd file

    Returns
    -------
    bool
    '''

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

    if bg_layers:
        _insert_render_stack(app, doc_ref, bg_layers, 'background', log)

    _insert_render_stack(app, doc_ref, img_layers, 'content', log)

    doc_ref.SaveAs(output_path)

    output_jpg = os.path.join(output_path, 'JPEG', filename + '.jpg')
    _save_as_jpg(doc_ref, output_jpg, log)

    doc_ref.Close()
    log.info("Created and saved file: %s.psd" % filename)

    # Make sure to set the ruler units prior to creating the document.
    app.Preferences.RulerUnits = start_ruler_units

    return True


def _prepare_photoshop(log: logging.Logger) -> Optional[Callable]:
    try:
        app = win32.gencache.EnsureDispatch("Photoshop.Application")
    except com_error:
        log.warning("Photoshop Error: Couldn't access Photoshop. Please make sure that the application is running.")
        return None

    log.debug("Successfully attached photoshop.")

    try:
        app.DisplayDialogs = PS_DISPLAY_NO_DIALOGS
    except com_error:
        log.warning("Photoshop Error: Please make sure that photoshop is running and that you are logged in.")
        return None

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

    TEST_FILE = '\\\\192.168.0.137\\office\\Projects\\240425_Tramtrain_Innotr\\grafik\\05_VR-Touren\\SAAR\\psds\\b.psd'
    OUT = "\\\\192.168.0.137\\office\\Projects\\200922_Stadler_VDV\\grafik\\02_Layout\\OUT_alle\\JPGs"

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger('ps_macros')
    logger.setLevel(logging.DEBUG)

    class PseudoDirEntry:
        def __init__(self, path):
            self.path = os.path.realpath(path)
            self.name = os.path.basename(self.path)
            self.is_dir = os.path.isdir(self.path)
            self.stat = lambda: os.stat(self.path)

    test_entry = PseudoDirEntry(TEST_FILE)
    # create_new_psd(layers, OUT_PATH, logger)  # type: ignore
    save_jpeg(test_entry, logger, OUT)
