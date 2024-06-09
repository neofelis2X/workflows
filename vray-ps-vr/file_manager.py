#!/usr/bin/env/ python3

import os.path
import os
import argparse
import logging

import local_secrets
import ps_macros

BASE_PATH = os.path.normpath(local_secrets.BASE_PATH)
CARRIER = local_secrets.CARRIER
LAYER = ['ambient', 'glare', 'depth']

def setup_argparse():
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

    parser.add_argument('-v', '--verbose',
                        help="print detailed information during the process",
                        action="store_true")
    parser.add_argument('-d', '--debug',
                        help="print the most detailed information",
                        action="store_true")

    return parser

def setup_logger(arguments):
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

def check_carrier(arguments, logger) -> str:
    if arguments.carrier not in CARRIER:
        logger.error("Only those carriers are currently supported: %s" % CARRIER)
        return ''
    return arguments.carrier

def output_info(carrier: str, log):
    '''
    Collect relevant information about the latest
    created folder of the currently selected carrier.
    Output the information via logs.
    '''
    search_path = os.path.join(BASE_PATH, carrier)
    search_path = get_latest_entry(search_path)
    infos = {'count': 0, 'names': [], 'extra': []}
    with os.scandir(search_path) as it:
        for entry in it:
            if not entry.name.startswith('.') and entry.is_file():
                segments = entry.name.split('.')
                if len(segments) > 2:
                    if not segments[1] in infos['extra']:
                        infos['extra'].append(segments[1])
                else:
                    infos['count'] += 1
                    infos['names'].append(segments[0])

    log.info("%i Files: %s\n%s" % (infos['count'], infos['names'], infos['extra']))

def get_latest_entry(carrier_path: str):
    entry_list = []
    with os.scandir(carrier_path) as it:
        for entry in it:
            if entry.is_dir():
                entry_list.append(entry.path)

    entry_list.sort(reverse=True)
    return entry_list[0]

def get_psds(carrier: str, log):
    '''
    Collect .psd file of the provided carrier.
    '''
    psd_list = []
    search_path = os.path.join(BASE_PATH, carrier)

    with os.scandir(search_path) as it:
        for entry in it:
            if not entry.name.startswith('.') and entry.is_file():
                if entry.name.endswith('.psd'):
                    psd_list.append(entry)
                    log.debug('Found file: %s' % entry.name)

    return psd_list

def get_rendered_imgs(carrier: str, log):
    '''
    Collect all images that are in the latest render folder.
    '''
    file_tree = {}
    search_path = os.path.join(BASE_PATH, carrier)
    search_path = get_latest_entry(search_path)
    with os.scandir(search_path) as it:
        for entry in it:
            if not entry.name.startswith('.') and entry.is_file():
                segments = entry.name.split('.')
                if segments[0] not in file_tree:
                    file_tree[segments[0]] = {}
                if len(segments) > 2 and segments[1] in LAYER:
                    file_tree[segments[0]][segments[1]] = entry
                    log.debug("Found layer file: %s" % entry.name)
                else:
                    file_tree[segments[0]]['std'] = entry
                    log.debug("Found file: %s" % entry.name)

    log.debug("Collected %i render files." % len(file_tree))
    return file_tree

def main():
    parser = setup_argparse()
    args = parser.parse_args()

    log = setup_logger(args)

    log.info("Base Path: %s" % BASE_PATH)
    log.debug("Arguments given: %s" % args)

    active_carrier = check_carrier(args, log)
    if not active_carrier:
        log.info("Please provide a correct carrier")
        return
    log.info("Carrier: %s" % active_carrier)

    if args.info:
        output_info(active_carrier, log)
        return

    renderings = get_rendered_imgs(active_carrier, log)

    if args.update:
        psd_files = get_psds(active_carrier, log)
        for file in psd_files:
            ps_macros.update_all_smartlayer(file, renderings, log)
    elif args.create:
        for file in renderings:
            ps_macros.create_new_psd(renderings, log)


if __name__ == "__main__":
    main()

