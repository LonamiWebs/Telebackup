from time import sleep
from datetime import timedelta
from os import makedirs, path
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.utils import BinaryReader, BinaryWriter


class Backuper:
    def __init__(self, client, download_delay=1, download_chunk_size=100):
        self.client = client
        self.download_delay = download_delay  # How long should we sleep every time we download messages?
        self.download_chunk_size = download_chunk_size  # How many messages do we download every time?
        self.backup_folder = 'backups'

    def do_backup(self, peer):
        # First load any previous backup
        saved_ids = set()
        last_id = 0

        # We don't support making chat backups yet
        peer_id = peer.user_id

        # Determine the backup folder and file
        peer_folder = path.join(self.backup_folder, str(peer_id))
        peer_file = path.join(peer_folder, 'messages.tlo')

        if not path.isdir(peer_folder):
            # No previous folder nor file, create it
            makedirs(peer_folder)
            open(peer_file, 'ab').close()

        else:
            # There was a previous folder, load the backup message IDs
            with open(peer_file, 'rb') as file:
                with BinaryReader(stream=file) as reader:
                    try:
                        while True:
                            msg = reader.tgread_object()
                            saved_ids.add(msg.id)
                            # We assume that the latest message is always the latest
                            # saved one, hence the ID from which we must continue our backup
                            last_id = msg.id
                    except BufferError:
                        "No more data to read"

        # Determine whether we started making the backup from the very first message
        # If this is the case, then we won't need to come back to the first message
        # again (since it will be added to the backup)
        # On the other hand, if we haven't started from 0, more messages were in the
        # backup already, and after we backup those "left" ones, we must return to the
        # first message and backup until where we started.
        started_at_0 = last_id == 0

        # Make the backup
        with open(peer_file, 'ab') as file:
            with BinaryWriter(stream=file) as writer:
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

                        for msg in result.messages:
                            # If the message we retrieved was already saved, this means that we're
                            # done because we have the rest of the messages! Clear the list so we enter the next if
                            if msg.id in saved_ids:
                                del result.messages[:]
                                break
                            else:
                                msg.on_send(writer)
                                saved_ids.add(msg.id)

                        if result.messages:
                            # We downloaded and added more messages, so print progress
                            last_id = result.messages[-1].id
                            print('[{:.2%}, ETA: {}] Downloaded {} out of {} messages'.format(
                                len(saved_ids) / total_messages,
                                self.calculate_eta(len(saved_ids), total_messages),
                                len(saved_ids),
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
                                continue

                        # Always sleep a bit, or Telegram will get angry and tell us to chill
                        sleep(self.download_delay)

                    pass  # end while

                except KeyboardInterrupt:
                    print('Operation cancelled, not downloading more messages!')

    def calculate_eta(self, downloaded, total):
        left = total - downloaded
        chunks_left = (left + self.download_chunk_size - 1) // self.download_chunk_size
        eta = chunks_left * self.download_delay
        return timedelta(seconds=eta)
