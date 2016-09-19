from time import sleep
from datetime import timedelta
from os import makedirs, path
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.types import InputPeerSelf
from telethon.utils import BinaryReader, BinaryWriter


class Backuper:

    # region Initialize

    def __init__(self, client, download_delay=1, download_chunk_size=100):
        self.client = client

        # How long should we sleep every time we download messages?
        self.download_delay = download_delay

        # How many messages do we download every time?
        self.download_chunk_size = download_chunk_size

        # Store the file paths for easy access
        self.msgs_path = 'backups/messages/{}.tlo'  # Messages belong to a specific peer
        self.peer_path = 'backups/messages/{}.peer.tlo'  # Save information about the peer
        self.users_path = 'backups/users.tlo'
        self.chats_path = 'backups/chats.tlo'

        # Store what messages, users and chats we already have a backup of
        self.saved_msg_ids = set()
        self.saved_user_ids = set()
        self.saved_chat_ids = set()

    # endregion

    # region Utilities

    @staticmethod
    def get_file_handle(file_path, mode):
        """Gets a file handle for the specified file path.
           Creates parent directories, and the file itself, if necessary.
           The mode can be either read, append or write"""
        folder = path.dirname(file_path)
        if not path.isdir(folder):
            makedirs(folder)

        if mode.startswith('r'):
            if not path.isfile(file_path):
                open(file_path, 'ab').close()
            return BinaryReader(stream=open(file_path, 'rb'))

        elif mode.startswith('a'):
            return BinaryWriter(stream=open(file_path, 'ab'))

        elif mode.startswith('w'):
            return BinaryWriter(stream=open(file_path, 'wb'))

        else:
            raise ValueError('mode must be either "read", "append" or "write"')


    @staticmethod
    def find_peer_id(peer):
        """Finds the peer ID for the given peer. Returns 0 if the user is yourself"""
        # First attempt at getting the user ID
        peer_id = getattr(peer, 'user_id', None)
        if not peer_id:
            # It wasn't an user? Then it may be a chat
            peer_id = getattr(peer, 'chat_id', None)
            if not peer_id:
                # It wasn't a chat? Not our day; Is it a channel?
                peer_id = getattr(peer, 'channel_id', None)
                if not peer_id:
                    # Well, we don't have many choices left!
                    if peer is InputPeerSelf:
                        peer_id = 0
                    else:
                        raise ValueError('Invalid peer {}'.format(type(peer)))

        return peer_id

    # endregion

    # region Loading backups

    def load_saved(self, peer_file):
        """Loads the saved messages, users and chats and returns the latest message ID"""

        # First clear any previously loaded messages
        # There is no need to clear user and chat IDs, since those are common
        self.saved_msg_ids.clear()

        # Then load all the values for the current peer
        last_id = 0
        with self.get_file_handle(peer_file, mode='r') as reader:
            try:
                while True:
                    msg = reader.tgread_object()
                    self.saved_msg_ids.add(msg.id)
                    # We assume that the latest message is always the latest
                    # saved one, hence the ID from which we must continue our backup
                    last_id = msg.id
            except BufferError: "No more data to read"

        # Also load all the saved users and chats, so we know which one
        # are new (and hence, which are the ones we need to save)
        # Load users
        with self.get_file_handle(self.users_path, mode='r') as reader:
            try:
                while True:
                    self.saved_user_ids.add(reader.tgread_object().id)
            except BufferError: "No more data to read"

        # Load chats
        with self.get_file_handle(self.chats_path, mode='r') as reader:
            try:
                while True:
                    self.saved_chat_ids.add(reader.tgread_object().id)
            except BufferError: "No more data to read"

        return last_id

    # endregion

    # region Making backups

    def begin_backup(self, peer):
        """Begins the backup on the given peer"""

        # Find the current peer ID, so we can determine its file
        peer_id = self.find_peer_id(peer)

        # Update peer info
        with self.get_file_handle(self.peer_path.format(peer_id), mode='w') as peer_handle:
            peer.on_send(peer_handle)

        # Determine the backup folder and file
        peer_file = self.msgs_path.format(str(peer_id))

        # Load the previous data
        last_id = self.load_saved(peer_file)

        # Determine whether we started making the backup from the very first message
        # If this is the case, then we won't need to come back to the first message
        # again (since it will be added to the backup)
        # On the other hand, if we haven't started from 0, more messages were in the
        # backup already, and after we backup those "left" ones, we must return to the
        # first message and backup until where we started.
        started_at_0 = last_id == 0

        with self.get_file_handle(peer_file, mode='a') as msgs_handle, \
            self.get_file_handle(self.users_path, mode='a') as users_handle, \
                self.get_file_handle(self.chats_path, mode='a') as chats_handle:
            # Make the backup
            try:
                while True:
                    result = self.client.invoke(GetHistoryRequest(
                        peer=peer,
                        offset_id=last_id,
                        limit=self.download_chunk_size,
                        offset_date=None,
                        add_offset=0,
                        max_id=0,
                        min_id=0
                    ))
                    total_messages = getattr(result, 'count', len(result.messages))

                    # First add users and chats
                    for user in result.users:
                        self.add_user(users_handle, user)
                    for chat in result.chats:
                        self.add_user(chats_handle, chat)

                    # Then add the messages to the backup
                    for msg in result.messages:
                        if not self.add_message(msgs_handle, msg):
                            # If the message we retrieved was already saved, this means that we're
                            # done because we have the rest of the messages!
                            # Clear the list so we enter the next if, and break to early terminate
                            del result.messages[:]
                            break

                    if result.messages:
                        # We downloaded and added more messages, so print progress
                        last_id = result.messages[-1].id
                        print('[{:.2%}, ETA: {}] Downloaded {} out of {} messages'.format(
                            len(self.saved_msg_ids) / total_messages,
                            self.calculate_eta(len(self.saved_msg_ids), total_messages),
                            len(self.saved_msg_ids),
                            total_messages))
                    else:
                        # We've downloaded all the messages since the last backup
                        if started_at_0:
                            # And since we started from the very first message, we have them all
                            print('Downloaded all {}'.format(total_messages))
                            break
                        else:
                            # We need to start from the first message (latest sent message)
                            # and backup again until we have them all
                            last_id = 0
                            started_at_0 = True

                    # Always sleep a bit, or Telegram will get angry and tell us to chill
                    sleep(self.download_delay)

                pass  # end while

            except KeyboardInterrupt:
                print('Operation cancelled, not downloading more messages!')

        pass  # end with

    # endregion

    # region Adding items to the backups

    def add_message(self, handle, message):
        """Adds a message to the specified writer handle IF it hasn't been added yet.
           If the message is added, True is returned; False otherwise"""
        if message.id in self.saved_msg_ids:
            return False
        else:
            message.on_send(handle)
            self.saved_msg_ids.add(message.id)
            return True

    def add_user(self, handle, user):
        """Adds an user to the specified writer handle IF it hasn't been added yet.
           If the user is added, True is returned; False otherwise"""
        if user.id in self.saved_user_ids:
            return False
        else:
            user.on_send(handle)
            self.saved_user_ids.add(user.id)
            return True

    def add_chat(self, handle, chat):
        """Adds a chat to the specified writer handle IF it hasn't been added yet.
           If the chat is added, True is returned; False otherwise"""
        if chat.id in self.saved_chat_ids:
            return False
        else:
            chat.on_send(handle)
            self.saved_chat_ids.add(chat.id)
            return True

    # endregion

    def calculate_eta(self, downloaded, total):
        left = total - downloaded
        chunks_left = (left + self.download_chunk_size - 1) // self.download_chunk_size
        eta = chunks_left * self.download_delay
        return timedelta(seconds=eta)
