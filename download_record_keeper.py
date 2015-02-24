__author__ = 'stefanofranz'
import sqlite3
import time


YES_MAN = type('RecordKeeper', (object,), {"record_completion": lambda s: None, "should_download": lambda s: True})
create_table_string = "CREATE TABLE IF NOT EXISTS DOWNLOADS(file_name TEXT PRIMARY KEY, download_date NUM)"


class RecordKeeper(object):
    def __init__(self, days_to_keep):
        self.days_to_keep = days_to_keep
        self.conn = sqlite3.connect('download_records.db')
        self.setup_tables()
        self.seconds_to_keep = self.days_to_keep * 24 * 60 * 60

    def record_completion(self, file_name):
        print("Marked: {0} as downloaded", file_name)
        insert_string = """
                        INSERT or REPLACE into DOWNLOADS (file_name, download_date) values
                        ( ? , ?)
                        """

        self.conn.execute(insert_string, (file_name, time.time()))
        self.conn.commit()

    def should_download(self, file_name):
        cursor = self.conn.cursor()
        cursor.execute("SELECT download_date FROM DOWNLOADS WHERE file_name=?", (file_name,))
        result = cursor.fetchone()

        if result is None:
            return True
        else:
            return (time.time() - result[0]) > self.seconds_to_keep

    def setup_tables(self):
        self.conn.execute(create_table_string)


if __name__ == "__main__":
    record_keeper = RecordKeeper(8)
    record_keeper.record_completion("this_is_a_fake")
    print record_keeper.should_download("this_is_a_fake")