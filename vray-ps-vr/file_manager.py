#!/usr/bin/env/ python3
'''
Author: Matthias Kneidinger
Copyright: 2024, GPLv3

Command line tool to create and update photoshop files
for specific carrier. Automatically picks up the latest
renderings. Run with --help to get more information.

local_secrets: Carrier names, base path and settings file
path have to be provided via the local_secrets module
as string constants.
'''

import os.path
import os
import subprocess
import shutil
import argparse
import logging
import tempfile

import local_secrets as secrets
import ps_macros

BASE_PATH = os.path.normpath(secrets.BASE_PATH)
CARRIER = secrets.CARRIER
KRPANO_PATH = secrets.KRPANO_PATH
LAYER = ['Ambient_Occlusion', 'Glare']

def _setup_argparse() -> argparse.ArgumentParser:
    '''
    Setup and return the argument parser.
    '''
    parser = argparse.ArgumentParser(prog='vtour File Manager',
                                     description='Creates and updates psd files and krpano vr tours.',
                                     epilog='Matthias Kneidinger (c) 2024 GPLv3')

    parser.add_argument('carrier',
                        help="which carrier should be processed, enter multiple if needed",
                        choices=CARRIER,
                        nargs='+',
                        type=str)

    parser.add_argument('-i', '--info',
                        help="print information about the latest renderings",
                        action="store_true")

    parser.add_argument('-c', '--create',
                        help="creates new .psd files or vtour from the given renderings",
                        choices=('images', 'vtour'),
                        type=str)

    parser.add_argument('-u', '--update',
                        help="updates the existing .psd files or vtour with the latest renderings",
                        choices=('images','backgrounds', 'vtour'),
                        type=str)

    parser.add_argument('-s', '--save',
                        help="save the existing .psd files as jpegs",
                        action="store_true")

    parser.add_argument('-v', '--verbose',
                        help="print information during the process",
                        action="store_true")

    parser.add_argument('-d', '--debug',
                        help="print the most detailed information",
                        action="store_true")

    return parser

def _setup_logger(arguments: argparse.Namespace) -> logging.Logger:
    if arguments.debug:
        logging_level = logging.DEBUG
    elif arguments.verbose or arguments.info:
        logging_level = logging.INFO
    else:
        logging_level = logging.WARNING

    log = logging.getLogger('psd-mang')
    log.setLevel(logging_level)

    # log_path = os.path.join(dir_path, 'vray_render.log')
    # handler = logging.FileHandler(log_path, mode='a')
    handler = logging.StreamHandler()
    log.addHandler(handler)

    formatter = logging.Formatter('%(asctime)s: %(name)s: %(levelname)s: %(message)s')
    handler.setFormatter(formatter)

    log.debug("Logger has been set up.")
    # log.debug("Logger has been set up. Path to log file:")
    # log.debug(log_path)

    return log

def _output_info(carrier: str,
                log: logging.Logger) -> bool:
    '''
    Collect relevant information about the latest
    created folder of the currently selected carrier.
    Output the information via logs.
    '''
    search_path = os.path.join(BASE_PATH, carrier, 'renderings')
    search_path = _get_latest_entry(search_path)

    if not search_path:
        log.warning("No renderings entry for %s exists!" % carrier)
        return False

    log.debug("Latest entry is: %s" % os.path.basename(search_path))
    count = 0
    names = []
    layer_files = []

    with os.scandir(search_path) as it:
        for entry in it:
            if not entry.name.startswith('.') and entry.is_file():
                segments = entry.name.split('.')
                if len(segments) > 2:
                    if not segments[1] in layer_files:
                        layer_files.append(segments[1])
                else:
                    count += 1
                    names.append(segments[0])

    log.info("%i Renderings:\nNames: %s\nLayers: %s" % (count,
                                                        names,
                                                        layer_files))
    return True

def _get_latest_entry(carrier_path: str) -> str:
    entry_list = []
    with os.scandir(carrier_path) as it:
        for entry in it:
            if entry.is_dir():
                entry_list.append(entry.path)

    if not entry_list:
        return ''

    entry_list.sort(reverse=True)

    return entry_list[0]

def _get_psds(carrier: str,
             log: logging.Logger) -> list[os.DirEntry]:
    '''
    Collect .psd file of the provided carrier.
    '''
    psd_list = []
    search_path = os.path.join(BASE_PATH, carrier, 'psds')

    with os.scandir(search_path) as it:
        for entry in it:
            if not entry.name.startswith('.') and entry.is_file():
                if entry.name.endswith('.psd'):
                    psd_list.append(entry)
                    log.debug('Found file: %s' % entry.name)

    return psd_list

def _get_rendered_imgs(carrier: str,
                       log: logging.Logger) -> dict[str, dict[str, os.DirEntry]]:
    '''
    Collect all images that are in the latest render folder.
    '''
    file_tree: dict[str, dict[str, os.DirEntry]] = {}

    search_path = os.path.join(BASE_PATH, carrier, 'renderings')
    search_path = _get_latest_entry(search_path)

    if not search_path:
        log.warning("No renderings entry for %s exists!" % carrier)
        return {}

    with os.scandir(search_path) as it:
        for entry in it:
            if not entry.name.startswith('.') and \
            entry.is_file() and \
            entry.name.endswith('.png'):  # currently we render in png anyway

                segments = entry.name.split('.')

                if segments[0] not in file_tree:
                    file_tree[segments[0]] = {}

                if len(segments) > 2 and segments[1] in LAYER:
                    file_tree[segments[0]][segments[1]] = entry
                    log.debug("Found layer file: %s" % entry.name)

                elif len(segments) == 2:
                    file_tree[segments[0]]['base'] = entry
                    log.debug("Found base file: %s" % entry.name)

    log.info("Collected %i render files." % len(file_tree))

    return file_tree

def _create_local_vrtour(image_list,
                         log: logging.Logger,
                         krpano_stdout: bool = False):

    krpano_exe = os.path.join(KRPANO_PATH, 'krpanotools.exe')
    krpano_config = os.path.join(KRPANO_PATH, 'templates', 'vtour-normal.config')

    process_return = subprocess.run([krpano_exe,
                                     'makepano',
                                     'config=',
                                     krpano_config,
                                     *image_list],
                                     check=True,
                                     shell=False,
                                     capture_output=True)

    if krpano_stdout:
        log.info(process_return.stdout.decode())

def _save_psds_as_jpgs(carrier: str,
                       log: logging.Logger) -> list[str]:

    psd_files = _get_psds(carrier, log)
    jpgs_remote = []

    jpeg_dir = os.path.join(BASE_PATH, carrier, 'psds', 'JPEG')

    if not os.path.isdir(jpeg_dir):
        os.mkdir(jpeg_dir)

    for psd in psd_files:
        jpgs_remote.append(ps_macros.save_jpeg(psd, log, jpeg_dir))

    return jpgs_remote

def _get_jpgs(carrier: str,
              log: logging.Logger) -> list[os.DirEntry[str]]:
    '''
    Collect .jpg files of the provided carrier.
    '''
    jpg_list = []
    search_path = os.path.join(BASE_PATH, carrier, 'psds', 'JPEG')

    with os.scandir(search_path) as it:
        for entry in it:
            if not entry.name.startswith('.') and entry.is_file():
                if entry.name.endswith('.jpg'):
                    jpg_list.append(entry)
                    log.debug('Found file: %s' % entry.name)

    return jpg_list

def _copy_vtour_to_remote(carrier: str,
                          log: logging.Logger,
                          temp_dir: str):

    vtour_dir = os.path.join(temp_dir, 'vtour')
    remote_dir = os.path.join(BASE_PATH, carrier, 'vtour')

    if os.listdir(remote_dir):
        log.error('Attention: The vtour directory must be empty, to copy a' \
                  ' new tour there. Please make sure there are no files in it!')
    else:
        shutil.copytree(vtour_dir, remote_dir, dirs_exist_ok=True)
        log.info('Successfully copied the the new tour.')

def _backup_panos_on_remote(carrier: str,
                            log: logging.Logger):

    remote_dir = os.path.join(BASE_PATH, carrier, 'vtour', 'panos')

    if os.path.isdir(remote_dir):

        backup_dir = remote_dir + '_backup'

        if os.path.isdir(backup_dir):
            shutil.rmtree(backup_dir)

        os.rename(remote_dir, backup_dir)

    os.mkdir(remote_dir)
    log.debug('Renamed panos folder to: %s' % backup_dir)

def _copy_panos_to_remote(carrier: str,
                          log: logging.Logger,
                          temp_dir: str):

    vtour_dir = os.path.join(temp_dir, 'vtour', 'panos')
    remote_dir = os.path.join(BASE_PATH, carrier, 'vtour', 'panos')

    if os.listdir(remote_dir):
        log.error('Attention: The vtour/panos directory must be empty, to copy' \
                  ' new panos there. Please make sure there are no files in it!')
    else:
        shutil.copytree(vtour_dir, remote_dir, dirs_exist_ok=True)
        log.info('Successfully copied the the new tour.')

def _copy_panos_to_combined(carrier: str,
                          log: logging.Logger,
                          temp_dir: str):

    vtour_dir = os.path.join(temp_dir, 'vtour', 'panos')
    dir_name = '_'.join(('panos', carrier.lower()))
    print(dir_name)
    remote_dir = os.path.join(BASE_PATH, 'COMBINED', 'vtour', dir_name)

    if os.listdir(remote_dir):
        log.warning('Attention: The exisiting vtour/panos directory must be deleted,' \
                  ' to copy new panos there.')
        shutil.rmtree(remote_dir)
        os.mkdir(remote_dir)

    shutil.copytree(vtour_dir, remote_dir, dirs_exist_ok=True)
    log.info('Successfully copied the the new tour to COMBINED.')

def _create_vrtour_to_remote(carrier: str,
                             log: logging.Logger):

    jpgs_remote = _get_jpgs(carrier, log)

    jpgs_local = []
    with tempfile.TemporaryDirectory() as tmpdir:
        for jpg in jpgs_remote:
            shutil.copy2(jpg, tmpdir)
            jpgs_local.append(os.path.join(tmpdir, os.path.basename(jpg)))

        _create_local_vrtour(jpgs_local, log, False)
        _copy_vtour_to_remote(carrier, log, tmpdir)

def _update_vrtour_on_remote(carrier: str,
                             log: logging.Logger):

    jpgs_remote = _get_jpgs(carrier, log)

    jpgs_local = []
    with tempfile.TemporaryDirectory() as tmpdir:
        for jpg in jpgs_remote:
            shutil.copy2(jpg, tmpdir)
            jpgs_local.append(os.path.join(tmpdir, os.path.basename(jpg)))

        _create_local_vrtour(jpgs_local, log, False)
        _backup_panos_on_remote(carrier, log)
        _copy_panos_to_remote(carrier, log, tmpdir)
        _copy_panos_to_combined(carrier, log, tmpdir)

        delete_backup = input("Do you want to delete the backup? (Y/N): ") or 'y'
        if delete_backup.lower() == 'y':
            backup_path = os.path.join(BASE_PATH, carrier, 'vtour', 'panos_backup')
            shutil.rmtree(backup_path)


def main() -> None:
    '''
    Run certain functions for the specified carrier
    based on the provided command line arguments.
    '''

    parser = _setup_argparse()
    args = parser.parse_args()

    log = _setup_logger(args)

    log.info("Base Path: %s", BASE_PATH)
    log.debug("Arguments given: %s", args)

    if 'ALL' in args.carrier:
        carrier_list = CARRIER[:-2]
    else:
        carrier_list = tuple(filter(lambda x: (x != 'BACKGROUNDS'), args.carrier))

    for carr in carrier_list:

        active_carrier = carr

        log.info("Carrier: %s", active_carrier)

        if args.info:
            _output_info(active_carrier, log)
            return

        renderings = _get_rendered_imgs(active_carrier, log)
        backgrounds = _get_rendered_imgs('BACKGROUNDS', log)

        if args.create == 'images':
            for file_key, file_entry in renderings.items():
                out_path = os.path.join(BASE_PATH, active_carrier, 'psds')
                bg_file = backgrounds.get(file_key, None)

                status = ps_macros.create_new_psd(file_entry, out_path, log, bg_file)
                if not status:
                    break

                log.info("Created psd-file: %s", os.path.basename(out_path))
            log.info("All psd-files are created.")

        elif args.create == 'vtour':
            _create_vrtour_to_remote(active_carrier, log)

        elif args.update == 'images':
            psd_files = _get_psds(active_carrier, log)
            for psdfile in psd_files:
                psd_name = os.path.splitext(psdfile.name)[0]
                if psd_name in renderings:
                    ps_macros.update_all_smartlayer(psdfile, renderings[psd_name], log)

        elif args.update == 'backgrounds':
            psd_files = _get_psds(active_carrier, log)
            for psdfile in psd_files:
                psd_name = os.path.splitext(psdfile.name)[0]
                if psd_name in renderings:
                    ps_macros.update_all_smartlayer(psdfile, renderings[psd_name], log, True)

        elif args.update == 'vtour':
            _update_vrtour_on_remote(active_carrier, log)

        elif args.save:
            _save_psds_as_jpgs(active_carrier, log)

    log.info("Script finished successfully.")


if __name__ == "__main__":
    main()

    #logging.basicConfig(level=logging.INFO)
    #logger = logging.getLogger('ps_macros')
    #logger.setLevel(logging.DEBUG)

    #_create_vrtour_to_remote('SAAR', logger)
