from datetime import date, timedelta, datetime
from os import path, makedirs
from shutil import copyfile
from threading import Thread

from os.path import isfile
from telethon.tl.types import MessageMediaPhoto

from exporter import HTMLTLWriter
from media_handler import MediaHandler
from tl_database import TLDatabase

class Exporter:
    """Class used to export database files"""

    # Default output directory for all the exported backups
    export_dir = 'backups/exported'

    def __init__(self, backups_dir, name):
        self.backups_dir = backups_dir
        self.name = name
        self.output_dir = path.join(Exporter.export_dir, name)
        self.media_handler = MediaHandler(self.output_dir)

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

        self.media_handler.make_tree()
        copyfile('exporter/resources/default_propic.png',
                 self.media_handler.get_default_file('propics'))

        copyfile('exporter/resources/default_photo.png',
                 self.media_handler.get_default_file('photos'))

    def export_thread(self, callback):
        """The exporting a conversation method (should be ran in a different thread)"""

        with TLDatabase(self.backups_dir) as db:
            db_media_handler = MediaHandler(self.backups_dir)

            # First copy the default media files
            self.copy_default_media()

            progress = {
                'exported': 0,
                'total': db.count('messages'),
                'etl': 'Unknown'
            }

            # The first date will obviously be the first day
            # TODO This fails if there are 0 messages in the database, export should be disabled!
            previous_date = self.get_message_date(db.query_message('order by id asc'))

            # Also find the next day
            following_date = self.get_previous_and_next_day(db, previous_date)[1]

            # Set the first writer (which will have the "previous" date, the first one)
            writer = HTMLTLWriter(previous_date, self.media_handler,
                                  following_date=following_date)

            # Keep track from when we started to determine the estimated time left
            start = datetime.now()

            # Export the profile photos, from users chats and channels
            # TODO This should also have a progress if we have a backup of thousands of files!
            for user in db.query_users():
                if user.photo:
                    source = db_media_handler.get_propic_path(user)
                    output = self.media_handler.get_propic_path(user)
                    if isfile(source):
                        copyfile(source, output)

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

                    writer = HTMLTLWriter(msg_date, self.media_handler,
                                          previous_date=previous_date,
                                          following_date=following_date)
                    # Call the callback
                    if callback:
                        progress['etl'] = self.calculate_etl(start, progress['exported'], progress['total'])
                        callback(progress)
                    else:
                        print(progress)

                writer.write_message(msg, db)
                # If the message has media, we need to copy it so it's accessible by the exported HTML
                if msg.media:
                    source = db_media_handler.get_msg_media_path(msg)
                    output = self.media_handler.get_msg_media_path(msg)
                    # Source may be None if the media is unsupported (i.e. a webpage)
                    if source and isfile(source):
                        copyfile(source, output)

                previous_date = msg_date

            # Always exit at the end
            writer.__exit__(None, None, None)
            # Call the callback to notify we've finished
            if callback:
                progress['etl'] = timedelta(seconds=0)
                callback(progress)

    #endregion

    #region Utilities

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
