from datetime import date, timedelta
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
            # The first date will obviously be the first day
            previous_date = self.get_message_date(db.query_message('order by id asc'))

            # Also find the next day
            following_date = self.get_previous_and_next_day(db, previous_date)[1]

            # Set the first writer (which will have the "previous" date, the first one)
            writer = HTMLTLWriter(self.get_output_dir(name, previous_date), previous_date,
                                  following_date=(following_date, self.get_output_dir(name, following_date)))

            # Iterate over all the messages to export them in their respective days
            for msg in db.query_messages('order by id asc'):
                msg_date = self.get_message_date(msg)

                # As soon as we're in the next day, update the output the writer
                if msg_date != previous_date:
                    # Exit the previous writer to end the header
                    writer.__exit__(None, None, None)

                    # Update date values and create a new instance
                    previous_date, following_date =\
                        self.get_previous_and_next_day(db, msg_date)

                    writer = HTMLTLWriter(self.get_output_dir(name, msg_date), msg_date,
                                          previous_date=(previous_date, self.get_output_dir(name, previous_date)),
                                          following_date=(following_date, self.get_output_dir(name, following_date)))

                writer.write_message(msg, db)
                previous_date = msg_date

            # Always exit at the end
            writer.__exit__(None, None, None)

    #endregion

    #region Utilities

    def get_output_dir(self, name, date):
        """Retrieves the output file for the backup with the given name, in the given date.
           An example might be 'backups/exported/year/MM/dd.html'"""
        if date:
            return path.abspath(path.join(self.output_dir,
                                          name,
                                          str(date.year),
                                          str(date.month),
                                          '{}.html'.format(date.day)))

    @staticmethod
    def get_previous_and_next_day(db, message_date):
        """Gets the previous and following saved days given the day in between in the database"""
        previous = db.query_message("where date < '{}' order by id desc"
                                    .format(message_date))
        following = db.query_message("where date >= '{}' order by id asc"
                                     .format(message_date+timedelta(days=1)))

        return Exporter.get_message_date(previous), Exporter.get_message_date(following)

    @staticmethod
    def get_message_date(message):
        """Retrieves the given message DATE, ignoring the time (hour, minutes, seconds, etc.)"""
        if message:
            return date(year=message.date.year, month=message.date.month, day=message.date.day)

    #endregion
