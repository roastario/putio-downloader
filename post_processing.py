from tvnamer.tvnamer.tvnamer_exceptions import DataRetrievalError, ShowNotFound, EpisodeNotFound, EpisodeNameNotFound, \
    SeasonNotFound

__author__ = 'stefanofranz'

from tvdb_api.tvdb_api import Tvdb
import tvnamer.tvnamer.utils as utils
import os
import shutil
import optparse


def create_dir(target):
    if not os.path.exists(target):
        os.makedirs(target)


def selectSeries(instance, serieses):
    print "Found {0} matching series".format(len(serieses))
    for sery in serieses:
        series = type('TvSeries', (object,), sery)
        print "\tFound: {0}, with airdate: {1}".format(series.seriesname, series.firstaired)

    selected = sorted(serieses, key=lambda s: type('TvSeries', (object,), s).firstaired, reverse=True)[0]
    print "Selecting: " + selected['seriesname']
    return selected

CUSTOM_UI = type('DUMMY', (object,), {"selectSeries": selectSeries, '__init__': lambda *args, **kwargs: None})


class TVPostProcessor(object):
    def __init__(self, base_directory):
        self.tvdb_instance = Tvdb(interactive=False, search_all_languages=False, language='en', custom_ui=CUSTOM_UI)
        self.target_dir = base_directory

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


def get_command_args():
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
    pp = TVPostProcessor(opts.destination)
    pp.rename_file("battlestar.galactica.s02e12.avi")