from datetime import date, timedelta, datetime
from os import path, makedirs
from shutil import copyfile
from threading import Thread

from exporter import HTMLTLWriter
from tl_database import TLDatabase

class Exporter:
    """Class used to export database files"""

    # Default output directory for all the exported backups
    export_dir = 'backups/exported'

    def __init__(self, db_file, name):
        self.db_file = db_file
        self.name = name
        self.output_dir = path.join(Exporter.export_dir, name)

    #region Exporting databases

    def export(self, callback=None):
        """Exports the given database with the specified name.
           An optional callback function can be given with one
           dictionary parameter containing progress information
           (saved_msgs, total_msgs, etl)"""

        Thread(target=self.export_thread, kwargs={ 'callback': callback }).start()

    def copy_default_media(self):
        """Copies the default media and style sheets to the output directory"""

        makedirs(self.output_dir, exist_ok=True)
        copyfile('exporter/resources/style.css', path.join(self.output_dir, 'style.css'))

        makedirs(self.get_media_file('profile_photos'), exist_ok=True)
        copyfile('exporter/resources/default_propic.png',
                 path.join(self.get_media_file('profile_photos'), 'default.png'))

        makedirs(self.get_media_file('photos'), exist_ok=True)
        copyfile('exporter/resources/default_photo.png',
                 path.join(self.get_media_file('photos'), 'default.png'))

    def export_thread(self, callback):
        """The exporting a conversation method (should be ran in a different thread)"""

        # First copy the default media files
        self.copy_default_media()

        with TLDatabase(self.db_file) as db:
            progress = {
                'exported': 0,
                'total': db.count('messages'),
                'etl': 'Unknown'
            }

            # The first date will obviously be the first day
            previous_date = self.get_message_date(db.query_message('order by id asc'))

            # Also find the next day
            following_date = self.get_previous_and_next_day(db, previous_date)[1]

            # Set the first writer (which will have the "previous" date, the first one)
            writer = HTMLTLWriter(previous_date, self.get_output_file, self.get_media_file,
                                  following_date=following_date)

            # Keep track from when we started to determine the estimated time left
            start = datetime.now()

            # Iterate over all the messages to export them in their respective days
            for msg in db.query_messages('order by id asc'):
                msg_date = self.get_message_date(msg)
                progress['exported'] += 1

                # As soon as we're in the next day, update the output the writer
                if msg_date != previous_date:
                    # Exit the previous writer to end the header
                    writer.__exit__(None, None, None)

                    # Update date values and create a new instance
                    previous_date, following_date =\
                        self.get_previous_and_next_day(db, msg_date)

                    writer = HTMLTLWriter(msg_date, self.get_output_file, self.get_media_file,
                                          previous_date=previous_date,
                                          following_date=following_date)
                    # Call the callback
                    if callback:
                        progress['etl'] = self.calculate_etl(start, progress['exported'], progress['total'])
                        callback(progress)
                    else:
                        print(progress)

                writer.write_message(msg, db)
                previous_date = msg_date

            # Always exit at the end
            writer.__exit__(None, None, None)
            # Call the callback to notify we've finished
            if callback:
                progress['etl'] = timedelta(seconds=0)
                callback(progress)

    #endregion

    #region Utilities

    def get_output_file(self, date):
        """Retrieves the output file for the backup with the given name, in the given date.
           An example might be 'backups/exported/year/MM/dd.html'"""
        if date:
            return path.abspath(path.join(self.output_dir,
                                          str(date.year),
                                          str(date.month),
                                          '{}.html'.format(date.day)))

    def get_media_file(self, media_type, filename=''):
        return path.abspath(path.join(self.output_dir, 'media', media_type, filename))

    @staticmethod
    def get_previous_and_next_day(db, message_date):
        """Gets the previous and following saved days given the day in between in the database"""
        previous = db.query_message("where date < '{}' order by id desc"
                                    .format(message_date))
        following = db.query_message("where date >= '{}' order by id asc"
                                     .format(message_date+timedelta(days=1)))

        return Exporter.get_message_date(previous), Exporter.get_message_date(following)

    @staticmethod
    def calculate_etl(start, saved, total):
        """Calculates the estimated time left, based on how long it took us
           to reach "saved" and how many messages we have left"""
        delta_time = (datetime.now() - start).total_seconds() / saved
        left = total - saved
        return timedelta(seconds=round(left * delta_time, 1))

    @staticmethod
    def get_message_date(message):
        """Retrieves the given message DATE, ignoring the time (hour, minutes, seconds, etc.)"""
        if message:
            return date(year=message.date.year, month=message.date.month, day=message.date.day)

    #endregion
