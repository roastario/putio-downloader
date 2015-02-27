from tvnamer.tvnamer.tvnamer_exceptions import DataRetrievalError, ShowNotFound, EpisodeNotFound, EpisodeNameNotFound, \
    SeasonNotFound

__author__ = 'stefanofranz'

from tvdb_api.tvdb_api import Tvdb
import tvnamer.tvnamer.utils as utils
import os
import shutil
import optparse

video_formats = ['.avi', '.mkv', '.mp4']


def create_dir(target):
    if not os.path.exists(target):
        os.makedirs(target)


class TVPostProcessor(object):
    def __init__(self, input_directory, base_directory):
        self.input_directory = input_directory
        self.tvdb_instance = Tvdb(interactive=False, search_all_languages=False, language='en')
        self.target_dir = os.path.join(base_directory, "TV")

    def rename_file(self, file_name):
        create_dir(self.target_dir)

        episode = utils.FileParser(file_name).parse()
        if episode.seriesname is None:
            pass
        else:
            print "Processing {0}".format(episode.generateFilename())
            try:
                episode.populateFromTvdb(self.tvdb_instance)
                full_dir = os.path.join(self.target_dir,
                                        "{0}/Season {1}/".format(episode.seriesname, episode.seasonnumber))
                create_dir(full_dir)
                print("Moving {0} -> {1}".format(file_name, os.path.join(full_dir, episode.generateFilename())))
                shutil.move(file_name, os.path.join(full_dir, episode.generateFilename()))
            except (DataRetrievalError, ShowNotFound, SeasonNotFound, EpisodeNotFound, EpisodeNameNotFound), errormsg:
                print "Unable to rename {0} due to error: {1}".format(file_name, errormsg)
                return False

    def process_directory(self):
        for root, dirs, files in os.walk(self.input_directory):
            for name in files:
                fileName, fileExtension = os.path.splitext(name)
                if fileExtension.lower() in video_formats:
                    path = os.path.join(root, name)
                    print "P: ", path
                    try:
                        self.rename_file(path)
                    except Exception, ex:
                        print("Failed to process {0} due to error {1}".format(os.path.join(root, name), ex.message))
            for name in dirs:
                pass

def get_command_args():
    global parser, opts, args
    parser = optparse.OptionParser(usage="%prog --output_dir=<dir>", add_help_option=False)
    parser.add_option("-d", "--output_dir", action="store", dest="destination",
                      help="Destination to move files to")
    parser.add_option("-i", "--input_dir", action="store", dest="input",
                      help="Directory to move files from")
    opts, args = parser.parse_args()

    if opts.destination is None or opts.input is None:
        raise Exception("Please specify --output_dir=<dir> and --input_dir=<dir> when starting")
    else:
        return opts


if __name__ == "__main__":
    opts = get_command_args()
    pp = TVPostProcessor(opts.input, opts.destination)
    pp.process_directory()