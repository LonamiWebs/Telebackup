from datetime import datetime
from os import path, makedirs
from shutil import copyfile

from exporter import HTMLTLWriter
from tl_database import TLDatabase


class Exporter:
    """Class used to export database files"""
    def __init__(self, output_dir='backups/exported'):
        self.output_dir = output_dir

        # Copy the required default resources
        makedirs(output_dir, exist_ok=True)
        copyfile('exporter/resources/style.css', path.join(output_dir, 'style.css'))

        makedirs(path.join(output_dir, 'media/profile_photos'), exist_ok=True)
        copyfile('exporter/resources/default_propic.png', path.join(output_dir, 'media/profile_photos/default.png'))

        makedirs(path.join(output_dir, 'media/photos'), exist_ok=True)
        copyfile('exporter/resources/default_photo.png', path.join(output_dir, 'media/photos/default.png'))

    #region Exporting databases

    def export(self, db_file, name):
        # TODO report progress every time a day changes
        with TLDatabase(db_file) as db:
            # First find the first date
            previous_date = self.get_message_date(db.query_message('order by id asc'))

            # Determine the first output date and the first writer
            output_path = self.get_output_dir(name, previous_date)
            writer = HTMLTLWriter(output_path)

            # Iterate over all the messages to export them in their respective days
            for msg in db.query_messages('order by id asc'):
                msg_date = self.get_message_date(msg)

                # As soon as we're in the next day, update the output path and the writer
                if msg_date != previous_date:
                    writer.__exit__(None, None, None)
                    output_path = self.get_output_dir(name, previous_date)
                    writer = HTMLTLWriter(output_path)

                writer.write_message(msg, db)
                previous_date = msg_date

            # Always exit at the end
            writer.__exit__(None, None, None)

    #endregion

    #region Utilities

    def get_output_dir(self, name, date):
        """Retrieves the output file for the backup with the given name, in the given date.
           An example might be 'backups/exported/year/MM/dd.html'"""
        return path.join(self.output_dir,
                         name,
                         str(date.year),
                         str(date.month),
                         '{}.html'.format(date.day))

    @staticmethod
    def get_message_date(message):
        """Retrieves the given message DATE, ignoring the time (hour, minutes, seconds, etc.)"""
        return datetime(year=message.date.year, month=message.date.month, day=message.date.day)

    #endregion
