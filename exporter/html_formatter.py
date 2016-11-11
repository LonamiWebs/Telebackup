from telethon.tl.types import MessageMediaPhoto
from exporter.html_content import *


class HTMLFormatter:
    """Class with the ability to format HTML content constants,
       provided the appropriated values"""

    def __init__(self, out_file_func, out_media_func):
        """Initializes the HTML Formatter. Two functions must be given:
            :param out_file_func: Takes a date as input and returns the output HTML file corresponding to it
            :param out_media_func: Takes a media type, and an optional file name,
                                   and returns the path to its corresponding media file
        """
        self.get_file_path = out_file_func
        self.get_media_path = out_media_func

    #region Internal formatting

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

    @staticmethod
    def sanitize_text(text):
        """Sanitizes a normal string to be writeable into HTML"""
        replacements = (
            ('&', '&amp;'),
            ('"', '&quot;'),
            ("'", '&#39;'),
            ('<', '&lt;'),
            ('>', '&gt;'),
            ('\n', '<br/>')
        )
        for s, r in replacements:
            text = text.replace(s, r)
        return text

    #endregion

    #region HTML Content formatting

    #region Beginning and end

    def get_beginning(self, current_date,
                      previous_date=None, following_date=None):
        """Formats the beginning (the "header") of the HTML file"""
        dates = ''

        # Append those dates that we have
        if previous_date:
            dates += self.get_link_date(previous_date)
            dates += ' | '
            dates += str(current_date)
        if following_date:
            dates += ' | '
            dates += self.get_link_date(following_date)

        return BEGINNING.format(dates=dates)

    def get_end(self):
        """Formats the end of the HTML file"""
        return END

    #endregion

    #region Dates

    def get_date(self, date):
        """Formats a date into HTML content"""
        return DATE.format(long_date=self.get_long_date(date),
                           short_date=self.get_short_date(date))

    def get_link_date(self, date):
        """Retrieves the date as a link to navigate to the file specified by the date"""
        return LINK_DATE.format(file=self.get_file_path(date),
                                date=str(date))

    #endregion

    #region Images

    def get_img(self, media_type, name, default='default.png'):
        """Formats the given name as media type, with a default fallback"""
        return IMG.format(file=self.get_media_path(media_type, name),
                          fallback=self.get_media_path(media_type, default))

    def get_propic(self, msg=None):
        """Retrieves the profile picture table cell, if any message is given.
           Otherwise, the <td/> will be empty"""
        if msg:
            return PROPIC.format(img=self.get_img('profile_photos', '{}.jpg'.format(msg.from_id)))
        else:
            return PROPIC_EMPTY

    #endregion

    #region Messages

    def get_message_header(self, msg, db):
        """Retrieves the message header given a message (and a database to look up additional details)"""
        sender = db.query_user('where id={}'.format(msg.from_id))

        if msg.reply_to_msg_id:
            reply_msg = db.query_message('where id={}'.format(msg.reply_to_msg_id))
            if reply_msg:
                # TODO replies to channels work, don't they?
                replied_sender = db.query_user('where id={}'.format(reply_msg.from_id))

                # Always write the absolute file path so we can navigate between different days
                replied_id_link = '{}#msg-id-{}'.format(self.get_file_path(reply_msg.date), msg.reply_to_msg_id)

                return MESSAGE_HEADER_REPLY.format(
                    sender=self.get_display(user=sender),
                    replied_sender=self.get_display(user=replied_sender),
                    replied_id_link=replied_id_link,
                    replied_content=self.get_reply_display(reply_msg)  # TODO handle showing photo preview
                )
            else:
                return MESSAGE_HEADER_REPLY.format(
                    sender=self.get_display(user=sender),
                    replied_sender='{Unknown}',
                    replied_id_link='#',
                    replied_content='{Reply message lacks of backup}'
                )

        elif msg.fwd_from:
            # The message could've been forwarded from either another user or from a channel
            if msg.fwd_from.from_id:
                original_sender = self.get_display(
                    user=db.query_user('where id={}'.format(msg.fwd_from.from_id)))
            else:
                original_sender = self.get_display(
                    chat=db.query_channel('where id={}'.format(msg.fwd_from.channel_id)))

            return MESSAGE_HEADER_FWD.format(
                sender=self.get_display(user=sender),
                original_sender=original_sender,
                date=self.get_date(msg.fwd_from.date)
            )

        else:
            return MESSAGE_HEADER.format(sender=self.get_display(user=sender))

    def get_message_content(self, msg):
        """Formats a message into message content, (including photos, captions, text only...)"""
        result = ''
        if msg.media:
            if isinstance(msg.media, MessageMediaPhoto):
                result += self.get_img('photos', '{}.jpg'.format(msg.media.photo.id))
                # TODO handle more media types

        if msg.message:
            result += '<p>' + self.sanitize_text(msg.message) + '</p>'

        return result

    def get_message(self, msg, db):
        """Formats a full message into HTML content, given the message itself and
           a database to look up for additional information"""

        result = '<tr>'  # Every message is a different row in the table
        result += self.get_propic(msg=None if msg.out else msg)

        result += MESSAGE.format(
            in_out='out' if msg.out else 'in',
            id=msg.id,
            header=self.get_message_header(msg, db),
            content=self.get_message_content(msg),
            date=self.get_date(msg.date)
        )

        result += self.get_propic(msg=msg if msg.out else None)
        result += '</tr>'

        return result

    #endregion
