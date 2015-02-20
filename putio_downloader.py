__author__ = 'stefanofranz'

import getopt
import sys

from putio import Client


if __name__ == "__main__":
    optlist, args = getopt.getopt(sys.argv[1:], '', ['api_key=', 'output-directory=', 'number_of_connections=',
                                                     'delete_after_download', 'exclude_pattern=', 'help'])

    parsed_args = {}
    for opt in optlist:
        arg_key = opt[0].replace('--', '')

        if arg_key in parsed_args:
            arg_list = [parsed_args[arg_key], opt[1]]
            parsed_args[arg_key] = arg_list
        else:
            parsed_args[arg_key] = opt[1]

    if 'api_key' not in parsed_args or 'help' in parsed_args:
        print "usage: ./putio.py --api_key=<API_KEY> [--output_directory=<dir> " \
              "--number_of_connections=<N> --exclude_pattern --delete_after_download]"

    client = Client(parsed_args['api_key'])
    output_directory = parsed_args['output_directory'] if 'output_directory' in parsed_args else '.'
    delete_after_download = True if 'delete_after_download' in parsed_args else False
    number_of_connections = parsed_args['number_of_connections'] if 'number_of_connections' in parsed_args else 1
    strings_to_filter = parsed_args['exclude_pattern'] if 'exclude_pattern' in parsed_args else []

    for FILE in client.File.list():

        was_filtered = False

        for string_to_filter in (strings_to_filter if isinstance(strings_to_filter, list) else [strings_to_filter]):
            if string_to_filter in FILE.name:
                was_filtered = True
                break
        try:
            if not was_filtered:
                FILE.download(dest=output_directory, delete_after_download=delete_after_download,
                              number_of_connections=number_of_connections)
        except Exception, e:
            print "FATAL: FAILED TO DOWNLOAD " + FILE.name + " due to " + e.message
