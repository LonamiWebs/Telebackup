from telethon.tl.types import MessageMediaPhoto
from exporter import HTMLWriter


class HTMLTLWriter(HTMLWriter):
    """Class implementing HTML Writer able to also write TLObjects"""

    def __init__(self, current_date, out_file_func,
                 previous_date=None, following_date=None):
        """Initializes a new HTMLTLWriter for a current day which outputs to
           out_file_func(current_date). The out_file_func must be a function
           which takes a date as argument, and returns an .html file location.

           Two optional previous/following dates parameters can be given which
           dates should correspond to the previous and following days"""
        self.current_date = current_date
        self.out_file_func = out_file_func

        super().__init__(out_file_func(current_date))

        self.start_header(current_date=current_date,
                          previous_date=previous_date,
                          following_date=following_date)

    #region Formatting utils

    @staticmethod
    def get_long_date(date):
        """Returns a date string in long format (Weekday name, day of Month name, hour:min:sec)"""
        return date.strftime('%A %d of %B, %H:%M:%S')

    @staticmethod
    def get_short_date(date):
        """Returns a date string in short format (hour:min)"""
        return date.strftime('%H:%M')

    @staticmethod
    def get_display(user=None, chat=None):
        """Gets the display string for an user or chat"""
        if user:
            # Probably a deleted user
            if not user.first_name:
                return '{Unknown user}'

            if user.last_name:
                return '{} {}'.format(user.first_name, user.last_name)
            else:
                return user.first_name

        if chat:
            if not chat.title:
                return '{Unknown chat}'
            return chat.title

    @staticmethod
    def get_reply_display(msg):
        """Gets the display when replying to a message
           (which may only be media, a document, a photo with caption...)"""
        if msg.media:
            return '{Photo}'
            # TODO handle more media types

        return msg.message

    #endregion

    #region Header

    def start_header(self, current_date, previous_date=None, following_date=None):
        """Starts the "header" of the HTML file (containing head, style and body beginning)"""
        self.write('<!DOCTYPE html>')
        self.open_tag('html')
        self.open_tag('head')

        self.tag('link', rel='stylesheet', type='text/css', href='../../../style.css')
        self.tag('meta', charset='utf-8')

        self.close_tag()  # head
        self.open_tag('body')

        # Add the current day floating div
        self.open_tag('div', style='display:inline-block;width:100%;')
        self.open_tag('div', _class='date')
        self.open_tag('p')

        # Ensure that we both have a tuple and the tuple has two not-None values
        if previous_date:
            self.open_tag('a', href=self.out_file_func(previous_date), _class='date')
            self.write_text(str(previous_date))
            self.close_tag()  # a
            self.write_text(' | ')
        self.write_text(str(current_date))
        if following_date:
            self.write_text(' | ')
            self.open_tag('a', href=self.out_file_func(following_date), _class='date')
            self.write_text(str(following_date))
            self.close_tag()  # a

        self.close_tag()  # p
        self.close_tag()  # div
        self.close_tag()  # div
        self.open_tag('table', id='messages', width='100%')

    def end_header(self):
        """Ends the previously started "header" closing the three last tags"""
        self.close_tag()  # table
        self.close_tag()  # body
        self.close_tag()  # html

    #endregion

    #region Photos

    def write_img(self, path, fallback):
        """Writes an image located at the given path. '../../../' will be always prefixed"""
        path = '../../../'+path
        fallback = '../../../'+fallback
        self.tag('img',
                 src=path,
                 onerror="if (this.src.indexOf('{0}') == -1) this.src = '{0}';".format(fallback))

    def write_propic(self, msg=None, empty=False):
        """Writes the profile picture <td>. It may be empty, depending on the side its placed.
           This is because the messages are in a table [photo|msg|photo], so always 3 columns are required"""
        if empty:
            self.tag('td', _class='propic')
        else:
            self.open_tag('td', _class='propic')
            self.write_img('media/profile_photos/{}.jpg'.format(msg.from_id),
                           fallback='media/profile_photos/default.png')
            self.close_tag()  # td

    #endregion

    #region Messages

    def write_message(self, msg, db):
        """Writes a Telegram message to the output file"""

        # We need a TLDatabase for writing the user and chat names
        self.open_tag('tr')
        # If the message is out, the table will be [empty|msg|photo]
        # If it's not out the table will look like [photo|msg|empty]

        # Write the profile photo on the left
        if msg.out:
            self.write_propic(empty=True)
        else:
            self.write_propic(msg)

        # Write the message itself
        self.open_tag('td')
        if msg.out:
            self.open_tag('div', _class='msg out', id='msg-id-{}'.format(msg.id))
        else:
            self.open_tag('div', _class='msg in', id='msg-id-{}'.format(msg.id))

        # Write the header of the message
        self.open_tag('p', _class='msg-header')

        # The header has the entity display in bold
        self.open_tag('b')
        sender = db.query_user('where id={}'.format(msg.from_id))
        self.write_text(self.get_display(user=sender))
        self.close_tag()  # b

        # The header may also have a "forwarded from" part
        if msg.fwd_from:
            self.write_text(', forwarded from ')
            self.open_tag('b')
            sender = db.query_user('where id={}'.format(msg.fwd_from.from_id))
            self.write_text(self.get_display(user=sender))
            self.close_tag()  # b

            # When was the original message sent?
            self.write_text(' at ')
            self.open_tag('span', title=self.get_long_date(msg.fwd_from.date))
            self.write_text(self.get_short_date(msg.fwd_from.date))
            self.close_tag()  # span

        # This also handles closing the header, because we need to to write the reply message
        if msg.reply_to_msg_id:
            reply_msg = db.query_message('where id={}'.format(msg.reply_to_msg_id))
            if reply_msg:
                self.write_text(', in reply to ')
                # Write who we're replying to name
                self.open_tag('b')
                sender = db.query_user('where id={}'.format(reply_msg.from_id))
                self.write_text(self.get_display(user=sender))
                self.close_tag()  # b

                self.write_text(' who said:')
                self.close_tag()  # p

                # Always write the absolute file path so we can navigate between different days
                self.open_tag('a', _class='reply',
                              href='{}#msg-id-{}'.format(self.out_file_func(reply_msg.date),
                                                         msg.reply_to_msg_id))
                self.open_tag('p')
                self.write_text(self.get_reply_display(reply_msg))
                self.close_tag()  # p
                self.close_tag()  # a
                self.tag('hr')
                self.open_tag('p')
            else:
                self.write_text('{Reply message lacks of backup}')
                self.close_tag()  # p

        # No reply to message, we need to close the header
        else:
            self.close_tag()  # p

        # Write the message itself
        if msg.media:
            if isinstance(msg.media, MessageMediaPhoto):
                self.write_img(path='media/photos/{}.jpg'.format(msg.media.photo.id),
                               fallback='media/photos/default.png')
            # TODO handle more media types

        # Finally write the message content itself, if any
        if msg.message:
            self.open_tag('p')
            self.write_text(msg.message)
            self.close_tag()  # p

        # Write the message date
        self.open_tag('p', _class='time', title=self.get_long_date(msg.date))
        self.write_text(self.get_short_date(msg.date))
        self.close_tag()  # p

        self.close_tag()  # div
        self.close_tag()  # td

        # Write the profile photo on the right
        if msg.out:
            self.write_propic(msg)
        else:
            self.write_propic(empty=True)

        self.close_tag()  # tr

    #endregion

    # `with` block

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_header()
        self.close()

    #endregion
