import json
from time import sleep
from datetime import timedelta
from os import makedirs, path
from telethon.tl.functions.messages import GetHistoryRequest

from tl_database import TLDatabase

# Load the current scheme layer
import telethon.tl.all_tlobjects as all_tlobjects
scheme_layer = all_tlobjects.layer
del all_tlobjects


class Backuper:

    # region Initialize

    def __init__(self, client, download_delay=1, download_chunk_size=100, backups_dir='backups'):
        """
        :param client:              An initialized TelegramClient, which will be used to download the messages
        :param download_delay:      The download delay, in seconds, after a message chunk is downloaded
        :param download_chunk_size: The chunk size (i.e. how many messages do we download every time)
                                    The maximum allowed by Telegram is 100
        :param backups_dir:         Where the backups will be stored
        """
        self.client = client
        self.download_delay = download_delay
        self.download_chunk_size = download_chunk_size
        self.backups_dir = backups_dir

        self.db = None  # This will be loaded later

    # endregion

    @staticmethod
    def get_peer_id(peer):
        """Gets the peer ID for a given peer (which can be an user, a chat or a channel)
           If the peer is neither of these, no error will be rose"""
        peer_id = getattr(peer, 'user_id', None)
        if not peer_id:
            peer_id = getattr(peer, 'chat_id', None)
            if not peer_id:
                peer_id = getattr(peer, 'channel_id', None)

        return peer_id

    def save_metadata(self, peer, peer_name, resume_msg_id):
        """Saves the metadata for the current peer"""
        peer_id = self.get_peer_id(peer)
        with open(path.join(self.backups_dir, '{}.meta'.format(peer_id)), 'w') as file:
            json.dump({
                'peer_id': peer_id,
                'peer_name': peer_name,
                'peer_constructor': peer.constructor_id,
                'resume_msg_id': resume_msg_id,
                'scheme_layer': scheme_layer
            }, file)

    def load_metadata(self, peer_id):
        """Loads the metadata of the current peer"""
        file_path = path.join(self.backups_dir, '{}.meta'.format(peer_id))
        if not path.isfile(file_path):
            return None
        else:
            with open(file_path, 'r') as file:
                return json.load(file)

    # region Making backups

    def begin_backup(self, input_peer, peer_name):
        """Begins the backup on the given peer"""

        # Ensure the directory for the
        makedirs(self.backups_dir, exist_ok=True)

        # Create a connection to the database
        peer_id = self.get_peer_id(input_peer)
        db_file = path.join(self.backups_dir, '{}.tlo'.format(peer_id))
        self.db = TLDatabase(db_file)

        # Load the previous data
        # We need to know the latest message ID so we can resume the backup
        metadata = self.load_metadata(peer_id)
        if metadata:
            last_id = metadata.get('resume_msg_id')

            # Also check for scheme layer consistency
            if metadata.get('scheme_layer', scheme_layer) != scheme_layer:
                raise InterruptedError('The backup was interrupted to prevent damage, '
                                       'because the used scheme layers are different.')
        else:
            last_id = 0

        # Determine whether we started making the backup from the very first message or not.
        # If this is the case:
        #   We won't need to come back to the first message again after we've finished downloading
        #   them all, since that first message will already be in backup.
        #
        # Otherwise, if we did not start from the first message:
        #   More messages were in the backup already, and after we backup those "left" ones,
        #   we must return to the first message and backup until where we started.
        started_at_0 = last_id == 0

        # Keep an internal downloaded count for it to be faster
        downloaded_count = self.db.count('messages')

        # Make the backup
        try:
            while True:
                result = self.client.invoke(GetHistoryRequest(
                    peer=input_peer,
                    offset_id=last_id,
                    limit=self.download_chunk_size,
                    offset_date=None,
                    add_offset=0,
                    max_id=0,
                    min_id=0
                ))
                total_messages = getattr(result, 'count', len(result.messages))

                # First add users and chats, replacing any previous value
                for user in result.users:
                    self.db.add_object(user, replace=True)
                for chat in result.chats:
                    self.db.add_object(chat, replace=True)

                # Then add the messages to the backup
                for msg in result.messages:
                    if self.db.in_table(msg.id, 'messages'):
                        # If the message we retrieved was already saved, this means that we're
                        # done because we have the rest of the messages!
                        # Clear the list so we enter the next if, and break to early terminate
                        last_id = result.messages[-1].id
                        del result.messages[:]
                        break
                    else:
                        self.db.add_object(msg)
                        downloaded_count += 1
                        last_id = msg.id

                # Always commit at the end to save changes
                self.db.commit()
                self.save_metadata(peer=input_peer, peer_name=peer_name, resume_msg_id=last_id)

                if result.messages:
                    # We downloaded and added more messages, so print progress
                    print('[{:.2%}, ETA: {}] Downloaded {} out of {} messages'.format(
                        downloaded_count / total_messages,
                        self.calculate_eta(downloaded_count, total_messages),
                        downloaded_count,
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
            # Also commit here, we don't want to lose any information!
            self.db.commit()
            self.save_metadata(peer=input_peer, peer_name=peer_name, resume_msg_id=last_id)

    # endregion

    def calculate_eta(self, downloaded, total):
        """Calculates the Estimated Time of Arrival (ETA)"""
        left = total - downloaded
        chunks_left = (left + self.download_chunk_size - 1) // self.download_chunk_size
        eta = chunks_left * self.download_delay
        return timedelta(seconds=eta)
