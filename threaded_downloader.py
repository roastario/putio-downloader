import urllib2
import Queue
import threading
import time

import os
import sys
import zlib
from cgi import parse_header


class DiskWriter(object):
    def __init__(self):
        self.last_resize_check_time = 0
        self.rows = 80
        self.columns = 80
        self.success = False

    def writer(self, queue, file_name, file_size, crc32):
        written_bytes = 0
        f = open(file_name, 'wb')
        print "Saving to: {0}".format(file_name)
        while True:
            item = queue.get()
            if item is None:
                break
            f.seek(item['offset'])
            f.write(item['buffer'])
            f.flush()
            written_bytes += len(item['buffer'])
            self.print_progress(bytes_written=written_bytes, file_size=file_size)

        f.close()
        print "\nFinished Writing {0}".format(file_name)
        print "Verifying {0}".format(file_name)
        crc_pass = self.crc(file_name=file_name, crc_value=crc32)
        if not crc_pass:
            print "Failed to verify{0}".format(file_name)

    @staticmethod
    def read_in_chunks(file_object, chunk_size=1024):
        """Lazy function (generator) to read a file piece by piece.
        Default chunk size: 1k."""
        while True:
            data = file_object.read(chunk_size)
            if not data:
                break
            yield data

    def crc(self, file_name, crc_value):
        if crc_value is None:
            self.success = True
            return self.success
        prev = 0
        file_to_check = open(file_name, "rb")
        for chunk in self.read_in_chunks(file_to_check, chunk_size=1024 * 512):
            prev = zlib.crc32(chunk, prev)
        self.success = ("%X" % (prev & 0xFFFFFFFF)).lower() == crc_value.lower()
        return self.success

    def print_progress(self, bytes_written, file_size):
        if (time.time() - self.last_resize_check_time) > 10:
            try:
                self.rows, self.columns = os.popen('stty size', 'r').read().split()
                self.last_resize_check_time = time.time()
            except ValueError:
                # This is when the console has been opened from a non-standard terminal, do not try again
                self.last_resize_check_time = sys.maxint
        sys.stdout.write("\r")
        sys.stdout.write('#' * int(int(self.columns) * (bytes_written / float(file_size))))
        sys.stdout.flush()


class ThreadedDownloader(object):
    def __init__(self, download_dir, number_of_connections=5):
        self.download_dir = download_dir
        self.number_of_connections = int(number_of_connections)
        self.queue = Queue.Queue(10)  # create back pressure on the downloading threads if we are slow to write to disk

    def create_chunks(self, file_size):
        chunks = []
        remaining = file_size
        for i in range(self.number_of_connections):
            chunk_size = file_size // self.number_of_connections
            chunks.append({'bytes': chunk_size, 'offset': file_size - remaining})
            remaining = remaining - chunk_size

        if remaining > 0:
            chunks.append({'bytes': remaining, 'offset': file_size - remaining})
        return chunks

    def create_downloading_threads(self, chunks, url):
        downloading_threads = []
        for chunk in chunks:
            download_thread = threading.Thread(target=self.download_part, args=(chunk, url))
            download_thread.setDaemon(True)
            downloading_threads.append(download_thread)
        return downloading_threads

    @staticmethod
    def start_and_wait_for_download(downloading_threads):
        for downloading_thread in downloading_threads:
            downloading_thread.start()
        for thread in downloading_threads:
            thread.join()

    def wait_for_writer_to_finish(self, writer_thread):
        self.queue.put(None)
        writer_thread.join()

    def create_and_start_writing_thread(self, dest, file_info, writer):
        dest = os.path.join(dest, file_info.name.encode('ascii', 'replace'))
        writer_thread = threading.Thread(target=writer.writer,
                                         args=(self.queue, dest, file_info.size, file_info.crc32))
        writer_thread.setDaemon(True)
        writer_thread.start()
        return writer_thread

    def multi_part_download_file(self, dest, url, file_info=None):
        if file_info is None:
            file_info = self.build_file(url)
        file_size = file_info.size
        chunks = self.create_chunks(file_size)
        downloading_threads = self.create_downloading_threads(chunks, url)
        writer = DiskWriter()
        writer_thread = self.create_and_start_writing_thread(dest, file_info, writer)
        self.start_and_wait_for_download(downloading_threads)
        self.wait_for_writer_to_finish(writer_thread)

        if not writer.success:
            raise RuntimeError("crc mismatch")


    def download_part(self, chunk, url, recurse_count=0):
        if recurse_count > 4:
            return
        try:
            start_byte = chunk['offset']
            end_byte = start_byte + chunk['bytes'] - 1
            opener = urllib2.build_opener()
            headers = [('Range', 'bytes={0}-{1}'.format(start_byte, end_byte))]
            opener.addheaders = headers
            opened_url = opener.open(url)
            block_sz = 1024 * 256  # (256K)
            bytes_downloaded = 0
            while True:
                temp_buffer = opened_url.read(block_sz)
                if not temp_buffer:
                    break
                current_offset = start_byte + bytes_downloaded
                bytes_in_buffer = len(temp_buffer)
                bytes_downloaded = bytes_downloaded + bytes_in_buffer
                self.queue.put({'buffer': temp_buffer, 'offset': current_offset})
        except:
            self.download_part(chunk=chunk, url=url, recurse_count=(recurse_count + 1))


    def build_file(self, url):
        request = urllib2.Request(url)
        request.get_method = lambda: 'HEAD'

        response = urllib2.urlopen(request, timeout=5)
        headers = response.headers

        might_support_ranges = False if 'Accept-Ranges' in headers and headers['Accept-Ranges'] == 'none' else True
        definitely_supports_ranges = True if 'Accept-Ranges' in headers and headers[
                                                                                'Accept-Ranges'] == 'bytes' else False
        file_size = headers['Content-Length'] if 'Content-Length' in headers else -1
        file_name = None
        if 'Content-Disposition' in headers:
            parsed_content_disposition = parse_header(headers['Content-Disposition'])
            for content_info in parsed_content_disposition:
                if 'filename' in content_info:
                    file_name = content_info['filename']
                    break

        if file_name is None:
            file_name = url.split('/')[-1]

        if not definitely_supports_ranges and might_support_ranges:
            print "Unsure if multi-threaded downloading supported, performing check"
            opener = urllib2.build_opener()
            headers = [('Range', 'bytes={0}-{1}'.format(0, 1))]
            opener.addheaders = headers
            opened_url = opener.open(url)
            ## if we reach here, we have not encountered an error - so supports multiple connections
            definitely_supports_ranges = True

        if not definitely_supports_ranges:
            raise Exception("Cannot download using multiple connections")

        file_object = type('File', (object,), {'size': int(file_size), 'name': file_name, 'crc32': None})
        return file_object


if __name__ == "__main__":
    url = sys.argv[1]
    downloader____build_file = ThreadedDownloader('.').multi_part_download_file('./', url)
