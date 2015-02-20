import urllib2
import Queue
import threading

import os


class DiskWriter(object):
    @staticmethod
    def writer(queue, file_name):
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
            written_bytes = written_bytes + len(item['buffer'])

        print "Finished {0}".format(file_name)
        f.close()


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

    def create_and_start_writing_thread(self, dest, file_info):
        dest = os.path.join(dest, file_info.name.encode('ascii', 'replace'))
        writer_thread = threading.Thread(target=DiskWriter.writer, args=(self.queue, dest))
        writer_thread.start()
        return writer_thread

    def multi_part_download_file(self, dest, url, file_info=None):
        if file_info is None:
            file_info = self.build_file(url)
        file_size = file_info.size
        chunks = self.create_chunks(file_size)
        downloading_threads = self.create_downloading_threads(chunks, url)
        writer_thread = self.create_and_start_writing_thread(dest, file_info)
        self.start_and_wait_for_download(downloading_threads)
        self.wait_for_writer_to_finish(writer_thread)

    def download_part(self, chunk, url):
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


    def build_file(url):
        # TODO-- perform a HEAD request to get the file_size / support range / file_name

        opener = urllib2.build_opener()
        raise NotImplementedError("Not quite implemented yet!")
