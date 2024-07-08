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
import argparse
import logging

import local_secrets as secrets
import ps_macros

BASE_PATH = os.path.normpath(secrets.BASE_PATH)
CARRIER = secrets.CARRIER
LAYER = ['Ambient_Occlusion', 'Glare']

def _setup_argparse() -> argparse.ArgumentParser:
    '''
    Setup and return the argument parser.
    '''
    parser = argparse.ArgumentParser()
    parser.add_argument('carrier', help="which carrier should be processed", type=str)

    parser.add_argument('-i', '--info',
                        help="print information about the latest renderings",
                        action="store_true")
    parser.add_argument('-c', '--create',
                        help="creates new .psd files from the given renderings",
                        action="store_true")
    parser.add_argument('-u', '--update',
                        help="updates the existing .psd files with the latest renderings",
                        action="store_true")
    parser.add_argument('-ub', '--update_backgrounds',
                        help="updates the existing .psd files with the latest backgrounds",
                        action="store_true")

    parser.add_argument('-v', '--verbose',
                        help="print detailed information during the process",
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
    logging.basicConfig(
        level=logging_level,
        format='%(asctime)s: %(name)s: %(levelname)s: %(message)s')
    logger = logging.getLogger('psd-mang')

    return logger

def _check_carrier(arguments: argparse.Namespace,
                  logger: logging.Logger) -> str:

    if arguments.carrier not in CARRIER:
        logger.error("Only those carriers are currently supported: %s", CARRIER)
        return ''

    return arguments.carrier

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

def _update_vrtour(carrier: str, log: logging.Logger):
    # This is a prototype
    pass

    # locate psd files of carrier and save them as jpeg
    # locate vrtour on server an backup the panos folder
    # copy jpeg files to a temp directory on the harddrive (not network)
    # create a new vrtour with the needed settings using krpano
    # copy the new panos folder into the tour on the server
    # purge the temp folder
    # open the folder the contain the vrtour in explorer
    # delete old panos folder by hand?

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

    active_carrier = _check_carrier(args, log)
    if not active_carrier:
        log.info("Please provide a correct carrier")
        return
    log.info("Carrier: %s", active_carrier)

    if args.info:
        _output_info(active_carrier, log)
        return

    renderings = _get_rendered_imgs(active_carrier, log)
    backgrounds = _get_rendered_imgs('BACKGROUNDS', log)

    if args.update:
        psd_files = _get_psds(active_carrier, log)
        for psdfile in psd_files:
            psd_name = os.path.splitext(psdfile.name)[0]
            ps_macros.update_all_smartlayer(psdfile, renderings[psd_name], log)

    elif args.update_backgrounds:
        psd_files = _get_psds(active_carrier, log)
        for psdfile in psd_files:
            psd_name = os.path.splitext(psdfile.name)[0]
            ps_macros.update_all_smartlayer(psdfile, renderings[psd_name], log, True)

    elif args.create:
        for file_key, file_entry in renderings.items():
            out_path = os.path.join(BASE_PATH, active_carrier, 'psds')
            bg_file = backgrounds.get(file_key, None)

            status = ps_macros.create_new_psd(file_entry, out_path, log, bg_file)
            if not status:
                break

            log.info("Created psd-file: %s", os.path.basename(out_path))
        log.info("All psd-files are done")


if __name__ == "__main__":
    main()

