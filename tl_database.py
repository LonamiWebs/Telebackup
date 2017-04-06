import sqlite3

from os import path, makedirs
from telethon.tl.types import \
    Message, MessageService, \
    User, UserEmpty, \
    Chat, ChatEmpty, ChatForbidden, \
    Channel, ChannelForbidden

from telethon.utils import BinaryReader, BinaryWriter


class TLDatabase:

    #region Initialization

    def __init__(self, directory):
        """Loads (or creates) a TLDatabase (for storing TLObjects) for the given file path"""

        # Register adapters and converters
        sqlite3.register_adapter(bool, self.adapt_boolean)
        sqlite3.register_converter('bool', self.convert_boolean)

        # Create a connection
        makedirs(directory, exist_ok=True)
        self.con = sqlite3.connect(path.join(directory, 'db.sqlite'),
                                   detect_types=sqlite3.PARSE_DECLTYPES)

        # We store the media, entities and action as blobs, because they're hardly encoded
        # However, we do store the media ID, so we can query, for example, which messages have photos
        #
        # Action is only part of MessageService
        #
        # We do not store `to_id` because our messages aren't all saved in one single place,
        # but rather in different databases (so it's impossible that `to_id` would vary)
        #
        # Note that `message` may not contain the real message text, but rather a
        # document or a photo caption, which makes sense. If we didn't store the caption
        # under `message`, then it wouldn't be searchable
        self.con.execute("""create table if not exists messages (
        id integer primary key,     -- 0
        message text,               -- 1

        from_id integer,            -- 2
        out bool,                   -- 3
        date timestamp,             -- 4
        edit_date timestamp,        -- 5

        fwd_from text,              -- 6
        via_bot_id integer,         -- 7
        reply_to_msg_id integer,    -- 8

        media blob,                 -- 9
        media_id integer,           -- 10
        entities blob,              -- 11

        action blob,                -- 12
        action_id integer           -- 13
        )""")

        self.con.execute("""create table if not exists users (
        id integer primary key,     -- 0
        access_hash integer,        -- 1

        is_self bool,               -- 2
        is_contact bool,            -- 3
        is_mutual_contact bool,     -- 4
        is_deleted bool,            -- 5
        is_bot bool,                -- 6

        first_name text,            -- 7
        last_name text,             -- 8
        username text,              -- 9
        phone text,                 -- 10

        photo blob                  -- 11
        )""")

        self.con.execute("""create table if not exists chats (
        id integer primary key,     -- 0
        creation_date timestamp,    -- 1
        is_creator bool,            -- 2

        title text,                 -- 3
        participants_count integer, -- 4

        photo blob                  -- 5
        )""")

        self.con.execute("""create table if not exists channels (
        id integer primary key,     -- 0
        access_hash integer,        -- 1
        is_megagroup bool,          -- 2

        creation_date timestamp,    -- 3
        is_creator bool,            -- 4

        title text,                 -- 5
        username text,              -- 6
        photo blob                  -- 7
        )""")

    #endregion

    #region Python -> SQL types

    @staticmethod
    def adapt_boolean(boolean):
        """Adapts a boolean value to an sql type"""
        return b'\x01' if boolean else None

    @staticmethod
    def adapt_object(tlobject):
        """Adapts a TLObject to an sql type"""
        if not tlobject:
            return None

        with BinaryWriter() as writer:
            writer.tgwrite_object(tlobject)
            return writer.get_bytes()

    @staticmethod
    def adapt_vector(vector):
        """Adapts a vector of TLObjects to an sql type"""
        with BinaryWriter() as writer:
            writer.tgwrite_vector(vector if vector is not None else [])
            return writer.get_bytes()

    #endregion

    #region SQL -> Python types

    @staticmethod
    def convert_boolean(sql):
        """Converts an sql blob back to a boolean value"""
        return False if sql == b'\x00' else True

    @staticmethod
    def convert_object(blob):
        """Converts an sql blob back to a TLObject"""
        if not blob:
            return None

        with BinaryReader(blob) as reader:
            return reader.tgread_object()

    @staticmethod
    def convert_vector(blob):
        """Converts an sql blob back to vector of TLObjects"""
        if not blob:
            return []

        with BinaryReader(blob) as reader:
            return reader.tgread_vector()

    #endregion

    #region Conversion from SQL tuples to TLObjects

    @staticmethod
    def convert_message(sql_tuple):
        """Converts an sql tuple back to a message TLObject"""

        # Check whether it is a service message
        if sql_tuple[13]:
            return MessageService(id=sql_tuple[0],
                                  from_id=sql_tuple[2],
                                  out=sql_tuple[3],
                                  to_id=None,  # This will always be the same, thus it wasn't saved
                                  date=sql_tuple[4],
                                  reply_to_msg_id=sql_tuple[8],
                                  action=TLDatabase.convert_object(sql_tuple[12]))
        else:
            return Message(id=sql_tuple[0],
                           message=sql_tuple[1],
                           from_id=sql_tuple[2],
                           to_id=None,  # This will always be the same, thus it wasn't saved
                           out=sql_tuple[3],
                           date=sql_tuple[4],
                           edit_date=sql_tuple[5],
                           fwd_from=TLDatabase.convert_object(sql_tuple[6]),
                           via_bot_id=sql_tuple[7],
                           reply_to_msg_id=sql_tuple[8],
                           media=TLDatabase.convert_object(sql_tuple[9]),
                           entities=TLDatabase.convert_vector(sql_tuple[11]))

    @staticmethod
    def convert_user(sql_tuple):
        """Converts an sql tuple back to an user TLObject"""
        return User(id=sql_tuple[0],
                    access_hash=sql_tuple[1],
                    is_self=sql_tuple[2],
                    contact=sql_tuple[3],
                    mutual_contact=sql_tuple[4],
                    deleted=sql_tuple[5],
                    bot=sql_tuple[6],
                    first_name=sql_tuple[7],
                    last_name=sql_tuple[8],
                    username=sql_tuple[9],
                    phone=sql_tuple[10],
                    photo=TLDatabase.convert_object(sql_tuple[11]))

    @staticmethod
    def convert_chat(sql_tuple):
        """Converts an sql tuple back to a chat TLObject"""
        return Chat(id=sql_tuple[0],
                    date=sql_tuple[1],
                    creator=sql_tuple[2],
                    title=sql_tuple[3],
                    participants_count=sql_tuple[4],
                    photo=TLDatabase.convert_object(sql_tuple[5]),
                    version=None)  # We don't care about the version in a chat backup

    @staticmethod
    def convert_channel(sql_tuple):
        """Converts an sql tuple back to a channel TLObject"""
        return Channel(id=sql_tuple[0],
                       access_hash=sql_tuple[1],
                       megagroup=sql_tuple[2],
                       date=sql_tuple[3],
                       creator=sql_tuple[4],
                       title=sql_tuple[5],
                       username=sql_tuple[6],
                       photo=TLDatabase.convert_object(sql_tuple[7]),
                       version=None)  # We don't care about the version in a channel backup

    #endregion

    #region Adding objects

    def add_object(self, tlobject, replace=False):
        """Adds a Telegram object (TLObject) to its corresponding table"""

        if isinstance(tlobject, Message):              # Adding a message
            self.add_message(tlobject, replace=replace)
        elif isinstance(tlobject, MessageService):     # Adding a message service
            self.add_message_service(tlobject, replace=replace)

        elif isinstance(tlobject, User):               # Adding an user
            self.add_user(tlobject, replace=replace)
        elif isinstance(tlobject, UserEmpty):          # Adding an empty user
            self.add_user(tlobject, replace=replace)

        elif isinstance(tlobject, Chat):               # Adding a chat
            self.add_chat(tlobject, replace=replace)
        elif isinstance(tlobject, ChatEmpty):          # Adding an empty chat
            self.add_chat(tlobject, replace=replace)
        elif isinstance(tlobject, ChatForbidden):      # Adding a forbidden chat
            self.add_chat(tlobject, replace=replace)

        elif isinstance(tlobject, Channel):            # Adding a channel
            self.add_channel(tlobject, replace=replace)
        elif isinstance(tlobject, ChannelForbidden):   # Adding a forbidden channel
            self.add_channel(tlobject, replace=replace)
        else:
            raise ValueError('Unknown type {}'.format(type(tlobject).__name__))

    def add_message(self, msg, replace=False):
        """Adds a message TLObject to its table"""
        c = self.con.cursor()
        if replace:
            query = 'insert or replace into messages values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
        else:
            query = 'insert into messages values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'

        if msg.message:
            message = msg.message
        elif msg.media:
            # If there is no message, then it probably was a caption
            # Given that we may want to search for the message (the "caption"),
            # store it under "message" so its searchable
            message = getattr(msg.media, 'caption', None)
        else:
            message = None

        c.execute(query,
                  (msg.id,
                   message,
                   msg.from_id,
                   msg.out,
                   msg.date,
                   msg.edit_date,
                   self.adapt_object(msg.fwd_from),
                   msg.via_bot_id,
                   msg.reply_to_msg_id,
                   self.adapt_object(msg.media),
                   type(msg.media).constructor_id if msg.media else None,
                   self.adapt_vector(msg.entities),
                   None,
                   None))

    def add_message_service(self, msg, replace=False):
        """Adds a message service TLObject to its table"""
        c = self.con.cursor()
        if replace:
            query = 'insert or replace into messages values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
        else:
            query = 'insert into messages values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
        c.execute(query,
                  (msg.id,
                   None,
                   msg.from_id,
                   msg.out,
                   msg.date,
                   None,
                   None,
                   None,
                   msg.reply_to_msg_id,
                   None,
                   None,
                   None,
                   self.adapt_object(msg.action),
                   type(msg.action).constructor_id if msg.action else None))

    def add_user(self, user, replace=False):
        """Adds an user TLObject to its table"""
        c = self.con.cursor()
        if replace:
            query = 'insert or replace into users values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
        else:
            query = 'insert into users values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'

        if isinstance(user, User):
            c.execute(query,
                      (user.id,
                       user.access_hash,
                       user.is_self,
                       user.contact,
                       user.mutual_contact,
                       user.deleted,
                       user.bot,
                       user.first_name,
                       user.last_name,
                       user.username,
                       user.phone,
                       self.adapt_object(user.photo)))
        elif isinstance(user, UserEmpty):
            c.execute(query, (user.id,
                              None, None, None, None, None, None, None, None, None, None, None))
        else:
            raise  ValueError('The user must either be an User or an UserEmpty')

    def add_chat(self, chat, replace=False):
        """Adds a chat TLObject to its table"""
        c = self.con.cursor()
        if replace:
            query = 'insert or replace into chats values (?, ?, ?, ?, ?, ?)'
        else:
            query = 'insert into chats values (?, ?, ?, ?, ?, ?)'

        # We need to use getattr because it may be a ChatEmpty or ChatForbidden
        c.execute(query,
                  (chat.id,
                   getattr(chat, 'date'),
                   getattr(chat, 'creator'),
                   getattr(chat, 'title'),
                   getattr(chat, 'participants_count'),
                   self.adapt_object(getattr(chat, 'photo'))))

    def add_channel(self, channel, replace=False):
        """Adds a channel TLObject to its table"""
        c = self.con.cursor()
        if replace:
            query = 'insert or replace into channels values (?, ?, ?, ?, ?, ?, ?, ?)'
        else:
            query = 'insert into channels values (?, ?, ?, ?, ?, ?, ?, ?)'

        # We need to use getattr because it may be a ChannelForbidden
        c.execute(query,
                  (channel.id,
                   channel.access_hash,
                   getattr(channel, 'megagroup'),
                   getattr(channel, 'date'),
                   getattr(channel, 'creator'),
                   channel.title,
                   getattr(channel, 'username'),
                   self.adapt_object(getattr(channel, 'photo'))))

    #endregion

    #region Counting objects

    def count(self, tablename):
        """Returns the count of items in the specified table"""
        c = self.con.cursor()
        return c.execute('select count(*) from {}'.format(tablename)).fetchone()[0]

    #endregion

    #region In table

    def in_table(self, tlobject_id, tablename):
        """Determines whether a TLObject, given its ID, is in the specified table"""
        c = self.con.cursor()
        item_id = c.execute('select id from {} where id=?'.format(tablename), (tlobject_id,)).fetchone()
        return item_id is not None

    #endregion

    #region Querying

    #region Querying multiple

    def query_messages(self, query=''):
        """Query example: `order by id asc`"""
        return self.query_many('messages', query, convert_function=self.convert_message)

    def query_users(self, query=''):
        """Query example: `order by id asc`"""
        return self.query_many('users', query, convert_function=self.convert_user)

    def query_chats(self, query=''):
        """Query example: `order by id asc`"""
        return self.query_many('chats', query, convert_function=self.convert_chat)

    def query_channels(self, query=''):
        """Query example: `order by id asc`"""
        return self.query_many('channels', query, convert_function=self.convert_channel)

    def query_many(self, tablename, query, convert_function):
        """Queries the given table with the ending specified query, and yields multiple items.
           The tuples returned from the query are converted by the convert_function"""
        c = self.con.cursor()
        for item in c.execute('select * from {} {}'.format(tablename, query)):
            yield convert_function(item)

    #endregion

    #region Querying single

    def query_message(self, query=''):
        """Query example: `where id=123456789`"""
        return self.query_single('messages', query, convert_function=self.convert_message)

    def query_user(self, query=''):
        """Query example: `where id=123456789`"""
        return self.query_single('users', query, convert_function=self.convert_user)

    def query_chat(self, query=''):
        """Query example: `where id=123456789`"""
        return self.query_single('chats', query, convert_function=self.convert_chat)

    def query_channel(self, query=''):
        """Query example: `where id=123456789`"""
        return self.query_single('channels', query, convert_function=self.convert_channel)

    def query_single(self, tablename, query, convert_function):
        """Queries the given table with the ending specified query, and returns a single item.
           The tuples returned from the query are converted by the convert_function"""
        c = self.con.cursor()
        for item in c.execute('select * from {} {}'.format(tablename, query)):
            return convert_function(item)

    #endregion

    #endregion

    def commit(self):
        """Commit changes to the database"""
        self.con.commit()

    def close(self):
        self.con.close()

    #region `with` block

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    #endregion
