from telethon.tl.types import Message, MessageMediaPhoto

# Message entities
from telethon.tl.types import \
    MessageEntityBold, MessageEntityItalic, \
    MessageEntityPre, MessageEntityCode, \
    MessageEntityUrl, MessageEntityTextUrl, MessageEntityEmail, \
    MessageEntityHashtag, MessageEntityMention, MessageEntityMentionName

# Message service actions
from telethon.tl.types import MessageService
from telethon.tl.types import \
    MessageActionChannelCreate, MessageActionChannelMigrateFrom, \
    MessageActionChatAddUser, MessageActionChatCreate, \
    MessageActionChatDeletePhoto, MessageActionChatDeleteUser, \
    MessageActionChatEditPhoto, MessageActionChatEditTitle, \
    MessageActionChatJoinedByLink, MessageActionChatMigrateTo, \
    MessageActionEmpty, MessageActionGameScore, \
    MessageActionHistoryClear, MessageActionPinMessage

from exporter.html_content import *
from io import StringIO


class HTMLFormatter:
    """Class with the ability to format HTML content constants,
       provided the appropriated values"""

    def __init__(self, media_handler):
        """Initializes the HTML Formatter. A media handler must be given"""
        self.media_handler = media_handler

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
                return HTMLFormatter.sanitize_text('{} {}'.format(user.first_name, user.last_name))
            else:
                return HTMLFormatter.sanitize_text(user.first_name)

        if chat:
            if not chat.title:
                return '{Unknown chat}'
            return HTMLFormatter.sanitize_text(chat.title)

    def get_reply_content(self, msg):
        """Gets the display when replying to a message
           (which may only be media, a document, a photo with caption...)"""
        if msg.media:
            if isinstance(msg.media, MessageMediaPhoto):
                return REPLIED_CONTENT_IMG.format(img=self.get_msg_img(msg),
                                                  replied_content=msg.message)
            # TODO handle more media types

        return REPLIED_CONTENT.format(replied_content=msg.message)

    # String replacements when sanitizing text
    sanitize_dict = {
        '&': '&amp;',
        '"': '&quot;',
        "'": '&#39;',
        '<': '&lt;',
        '>': '&gt;',
        '\n': '<br/>'
    }

    @staticmethod
    def sanitize_text(text):
        """Sanitizes a normal string to be writeable into HTML"""
        with StringIO() as result:
            for c in text:
                result.write(HTMLFormatter.sanitize_dict.get(c, c))

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

    def get_date(self, date, edit_date=None):
        """Formats a date into HTML content"""
        if edit_date:
            return DATE_EDIT.format(
                long_date=self.get_long_date(date),
                short_date=self.get_short_date(date),
                long_edit_date=self.get_long_date(edit_date),
                short_edit_date=self.get_short_date(edit_date)
            )
        else:
            return DATE.format(long_date=self.get_long_date(date),
                               short_date=self.get_short_date(date))

    def get_link_date(self, date):
        """Retrieves the date as a link to navigate to the file specified by the date"""
        return LINK_DATE.format(uri=self.media_handler.get_html_uri(date),
                                date=str(date))

    #endregion

    #region Images

    def get_msg_img(self, msg):
        """Formats the given name as media type, with a default fallback"""
        return IMG.format(file=self.media_handler.get_msg_media_path(msg),
                          fallback=self.media_handler.get_default_file('photos'))

    def get_propic_img(self, user_id):
        return IMG.format(file=self.media_handler.get_propic_path(user_id),
                          fallback=self.media_handler.get_default_file('propics'))

    def get_propic(self, msg=None):
        """Retrieves the profile picture table cell, if any message is given.
           Otherwise, the <td/> will be empty"""
        if msg:
            return PROPIC.format(img=self.get_propic_img(msg.from_id))
        else:
            return PROPIC_EMPTY

    #endregion

    #region Message header

    def get_message_header(self, msg, db):
        """Retrieves the message header given a message (and a database to look up additional details)"""
        sender = db.query_user('where id={}'.format(msg.from_id))

        result = ''
        if msg.via_bot_id:
            bot = db.query_user('where id={}'.format(msg.via_bot_id))
            if bot:
                result += MESSAGE_VIA.format(bot=bot.username)

        if msg.reply_to_msg_id:
            reply_msg = db.query_message('where id={}'.format(msg.reply_to_msg_id))
            if reply_msg:
                # TODO replies to channels work, don't they?
                replied_sender = db.query_user('where id={}'.format(reply_msg.from_id))

                # Always write the absolute file path so we can navigate between different days
                replied_id_link = '{}#msg-id-{}'.format(
                    self.media_handler.get_html_uri(reply_msg.date), msg.reply_to_msg_id)

                result += MESSAGE_HEADER_REPLY.format(
                    sender=self.get_display(user=sender),
                    replied_sender=self.get_display(user=replied_sender),
                    replied_id_link=replied_id_link,
                    replied_content=self.get_reply_content(reply_msg)  # TODO handle showing photo preview
                )
            else:
                result += MESSAGE_HEADER_REPLY.format(
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

            result += MESSAGE_HEADER_FWD.format(
                sender=self.get_display(user=sender),
                original_sender=original_sender,
                date=self.get_date(msg.fwd_from.date)
            )

        else:
            result += MESSAGE_HEADER.format(sender=self.get_display(user=sender))

        return result

    #endregion

    #region Messages

    def get_message_entities(self, msg):
        # List that will store (index, 'tag') for all the entities
        entities = []
        # Load the entities from the message into tags
        for e in msg.entities:
            if isinstance(e, MessageEntityBold):
                entities.append((e.offset, '<b>'))
                entities.append((e.offset + e.length, '</b>'))

            elif isinstance(e, MessageEntityItalic):
                entities.append((e.offset, '<i>'))
                entities.append((e.offset + e.length, '</i>'))

            elif isinstance(e, MessageEntityPre) or \
                    isinstance(e, MessageEntityCode):
                # TODO pre has language, use code or pre tag? Add syntax highlight?:
                # https://highlightjs.org/ or https://github.com/google/code-prettify
                entities.append((e.offset, '<code>'))
                entities.append((e.offset + e.length, '</code>'))

            elif isinstance(e, MessageEntityUrl):
                href = msg.message[e.offset:e.offset+e.length]
                entities.append((e.offset, '<a href="{}" target="_blank">'.format(href)))
                entities.append((e.offset + e.length, '</a>'))

            elif isinstance(e, MessageEntityTextUrl):
                entities.append((e.offset, '<a href="{}" target="_blank">'.format(e.url)))
                entities.append((e.offset + e.length, '</a>'))

            elif isinstance(e, MessageEntityEmail):
                mail = msg.message[e.offset:e.offset+e.length]
                entities.append((e.offset, '<a href="mailto:{}" target="_blank">'.format(mail)))
                entities.append((e.offset + e.length, '</a>'))

            # TODO No support for searching for messages yet
            # Maybe launch a python script which searches for a message and creates an HTML with them
            # elif isinstance(e, MessageEntityHashtag)
            # elif isinstance(e, MessageEntityMention)
            # elif isinstance(e, MessageEntityMentionName)

        return entities

    # TODO Should replies also have formatting?
    def get_message_content(self, msg):
        """Formats a message into message content, (including photos, captions, text only...)"""

        with StringIO() as result:
            if msg.media:
                if isinstance(msg.media, MessageMediaPhoto):
                    result.write(self.get_msg_img(msg))
                    # TODO handle more media types

            if msg.message:
                result.write('<p>')
                entities = self.get_message_entities(msg)
                # We need to go character by character to know when to insert bold text, etc
                for i, c in enumerate(msg.message):
                    # Iterate the entities in reverse order to be able to pop them
                    for j in range(len(entities)-1, -1, -1):
                        e, tag = entities[j]
                        if e == i:
                            entities.pop(j)
                            result.write(tag)

                    # Write the sanitized message string (curret character)
                    result.write(self.sanitize_dict.get(c, c))

                # If there are entities left, they're at the end of the string
                # Close them all
                for e, tag in entities:
                    result.write(tag)

                result.write('</p>')

            return result.getvalue()

    def get_message(self, msg, db):
        """Formats a full message into HTML content, given the message itself and
           a database to look up for additional information"""

        if isinstance(msg, MessageService):
            return MESSAGE_SERVICE.format(
                id=msg.id,
                content=self.action_to_string(msg, db),
                date=self.get_date(msg.date)
            )
        else:
            result = '<tr>'  # Every message is a different row in the table
            result += self.get_propic(msg=None if msg.out else msg)

            result += MESSAGE.format(
                in_out='out' if msg.out else 'in',
                id=msg.id,
                header=self.get_message_header(msg, db),
                content=self.get_message_content(msg),
                date=self.get_date(msg.date, msg.edit_date)
            )

            result += self.get_propic(msg=msg if msg.out else None)
            result += '</tr>'

            return result

    #endregion

    #region Message service

    def action_to_string(self, msg, db):
        """Converts a MessageService and its action to a string"""
        action = msg.action
        who = self.get_who(msg, db)

        # Create channel
        if isinstance(action, MessageActionChannelCreate):
            return '<p>{} created the channel "{}"</p>'.format(who, action.title)

        # Migrated channel from a chat
        if isinstance(action, MessageActionChannelMigrateFrom):
            chat = db.query_chat('where id={}'.format(action.chat_id))
            if chat:
                return '<p>{} migrated channel "{}" migrated from chat "{}"</p>'\
                    .format(who, action.title, chat.title)
            else:
                return '<p>{} migrated channel "{}" from a chat</p>'.format(who, action.title)

        # Added users into a chat
        if isinstance(action, MessageActionChatAddUser):
            users = []
            for user_id in action.users:
                user = db.query_user('where id={}'.format(user_id))
                if user:
                    users.append(self.get_display(user=user))
                else:
                    users.append('{Unknown user}')
            return '<p>{} added {}</p>'.format(who, ', '.join(users))

        # Chat created
        if isinstance(action, MessageActionChatCreate):
            # TODO Should this display group members (users)?
            return '<p>{} created group "{}"</p>'.format(who, action.title)

        # Chat photo removed
        if isinstance(action, MessageActionChatDeletePhoto):
            return '<p>{} removed group photo</p>'.format(who)

        # Removed user from chat
        if isinstance(action, MessageActionChatDeleteUser):
            user = db.query_user('where id={}'.format(action.user_id))
            if user:
                return '<p>{} removed {}</p>'.format(who, action.user_id)
            else:
                return '<p>{} removed an user</p>'.format(who)

        # Updated chat photo
        if isinstance(action, MessageActionChatEditPhoto):
            # TODO What photo? Is this one backed up? No right?
            return '<p>{} updated group photo</p>'.format(who)

        # Updated chat title
        if isinstance(action, MessageActionChatEditTitle):
            return '<p>{} changed group name to "{}"</p>'.format(who, action.title)

        # Joining by link
        if isinstance(action, MessageActionChatJoinedByLink):
            return '<p>{} joined by link ID {}</p>'.format(who, action.inviter_id)

        # Chat migrated to a channel
        if isinstance(action, MessageActionChatMigrateTo):
            channel = db.query_channel('where id={}'.format(action.channel_id))
            if channel:
                return '<p>{} migrated the chat to channel "{}"</p>'.format(who, channel.title)
            else:
                return '<p>{} migrated the chat to a channel</p>'.format(who)

        # Game score
        if isinstance(action, MessageActionGameScore):
            # TODO Do we have backups for games?
            return '<p>{} scored {} at Game#{}</p>'.format(who, action.score, action.game_id)

        # History cleared
        if isinstance(action, MessageActionHistoryClear):
            return '<p>{} cleared chat history</p>'.format(who)

        # Message pinned
        if isinstance(action, MessageActionPinMessage):
            return '<p>{} pinned a new message</p>'.format(who)

        # No action (when does this even happen?)
        # if isinstance(action, MessageActionEmpty):
        return '<p>No action</p>'

    def get_who(self, msg, db):
        """Returns "who" (You or someone else) performed an action"""
        if msg.out:
            return 'You'
        else:
            user = db.query_user('where id={}'.format(msg.from_id))
            if user:
                return self.get_display(user=user)
            else:
                return '{Unknown user}'

    #endregion

    #endregion
