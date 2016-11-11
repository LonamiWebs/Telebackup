from os import makedirs
from os.path import dirname

from exporter import HTMLFormatter


class HTMLTLWriter:
    """Class implementing HTML Writer able to also write TLObjects"""

    def __init__(self, current_date, out_file_func, out_media_func,
                 previous_date=None, following_date=None):
        """Initializes a new HTMLTLWriter for a current day which outputs to
           out_file_func(current_date). The out_file_func must be a function
           which takes a date as argument, and returns an .html file location.

           Similarly, the out_media_func must be a function that takes a media
           type as required parameter and an optional file name, returning
           where that filename should be located depending on the media type.

           Two optional previous/following dates parameters can be given which
           dates should correspond to the previous and following days"""
        self.current_date = current_date
        self.formatter = HTMLFormatter(out_file_func, out_media_func)

        # Open the current output file and store its handle
        output_file = out_file_func(current_date)
        makedirs(dirname(output_file), exist_ok=True)
        self.handle = open(output_file, 'w')

        # Begin the header before writing any Telegram message
        self.start_header(current_date=current_date,
                          previous_date=previous_date,
                          following_date=following_date)

    def start_header(self, current_date, previous_date=None, following_date=None):
        """Starts the "header" of the HTML file (containing head, style and body beginning)"""
        self.handle.write(self.formatter.get_beginning(
            current_date, previous_date=previous_date, following_date=following_date))

    def end_header(self):
        """Ends the previously started "header" closing the three last tags"""
        self.handle.write(self.formatter.get_end())

    def write_message(self, msg, db):
        """Writes a Telegram message to the output file"""
        self.handle.write(self.formatter.get_message(msg, db))

    # `with` block

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_header()
        self.handle.close()

    #endregion
