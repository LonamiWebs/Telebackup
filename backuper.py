import json
from time import sleep
from datetime import timedelta
from os import makedirs, path, listdir

from os.path import isfile, isdir
from telethon import RPCError
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument
from telethon.utils import \
    BinaryReader, BinaryWriter, \
    get_display_name, get_extension, get_input_peer

from tl_database import TLDatabase

# Load the current scheme layer
import telethon.tl.all_tlobjects as all_tlobjects
scheme_layer = all_tlobjects.layer
del all_tlobjects


class Backuper:

    backups_dir = 'backups'

    # region Initialize

    def __init__(self, client, entity,
                 download_delay=1,
                 download_chunk_size=100):
        """
        :param client:              An initialized TelegramClient, which will be used to download the messages
        :param entity:              The entity (user, chat or channel) from which the backup will be made
        :param download_delay:      The download delay, in seconds, after a message chunk is downloaded
        :param download_chunk_size: The chunk size (i.e. how many messages do we download every time)
                                    The maximum allowed by Telegram is 100
        """
        self.client = client
        self.entity = entity

        self.download_delay = download_delay
        self.download_chunk_size = download_chunk_size
        self.backup_dir = path.join(Backuper.backups_dir, str(entity.id))
        self.propic_path = path.join(self.backup_dir, 'propic.jpg')

        # Ensure the directory for the backups
        makedirs(self.backup_dir, exist_ok=True)

        # Pickle the entity
        with open(path.join(self.backup_dir, 'entity.tlo'), 'wb') as file:
            with BinaryWriter(file) as writer:
                entity.on_send(writer)

        self.db = None  # This will be loaded later

    # endregion

    @staticmethod
    def enumerate_backups_entites():
        """Enumerates the entities of all the available backups"""
        if isdir(Backuper.backups_dir):

            # Look for subdirectories
            for directory in listdir(Backuper.backups_dir):
                entity_file = path.join(Backuper.backups_dir, directory, 'entity.tlo')

                # Ensure the entity.pickle file exists
                if isfile(entity_file):

                    # Load and yield it
                    with open(entity_file, 'rb') as file:
                        with BinaryReader(stream=file) as reader:
                            yield reader.tgread_object()
        # End of the function

    @staticmethod
    def exists_backup(entity_id):
        return isdir(path.join(Backuper.backups_dir, str(entity_id)))

    def save_metadata(self, resume_msg_id):
        """Saves the metadata for the current entity"""
        with open(path.join(self.backup_dir, 'metadata.json'), 'w') as file:
            json.dump({
                'entity_id': self.entity.id,
                'entity_name': get_display_name(self.entity),
                'entity_constructor': self.entity.constructor_id,
                'resume_msg_id': resume_msg_id,
                'scheme_layer': scheme_layer
            }, file)

    def load_metadata(self):
        """Loads the metadata of the current entity"""
        file_path = path.join(self.backup_dir, 'metadata.json')
        if not path.isfile(file_path):
            return None
        else:
            with open(file_path, 'r') as file:
                return json.load(file)

    def get_create_media_dirs(self):
        """Retrieves the paths for the profile photos, photos,
           documents and stickers backups directories, creating them too"""
        directories = []
        for directory in ('profile_photos', 'photos', 'documents', 'stickers'):
            current = path.join(self.backup_dir, 'media', directory)
            makedirs(current, exist_ok=True)
            directories.append(current)

        return directories

    # region Making backups

    # TODO manage multiple photo versions in another subdirectory,
    # with a method to get the latest path
    def backup_propic(self):
        """Backups the profile picture for the given
           entity as the current peer profile picture, returning its path"""
        self.client.download_profile_photo(self.entity.photo,
                                           file_path=self.propic_path,
                                           add_extension=False)

        return self.propic_path

    def begin_backup(self):
        """Begins the backup on the given peer"""

        # Create a connection to the database
        db_file = path.join(self.backup_dir, 'backup.sqlite')
        self.db = TLDatabase(db_file)

        # Load the previous data
        # We need to know the latest message ID so we can resume the backup
        metadata = self.load_metadata()
        if metadata:
            last_id = metadata.get('resume_msg_id')
            # Do not check for the scheme layers to be the same,
            # the database is meant to be consistent always
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
            input_peer = get_input_peer(self.entity)
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
                self.save_metadata(resume_msg_id=last_id)

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
            self.save_metadata(resume_msg_id=last_id)

    def begin_backup_media(self, db_file, dl_propics, dl_photos, dl_documents):
        propics_dir, photos_dir, documents_dir, stickers_dir = \
            self.get_create_media_dirs()

        db = TLDatabase(db_file)

        # TODO Spaghetti code, refactor
        if dl_propics:
            total = db.count('users where photo not null')
            print("Starting download for {} users' profile photos..".format(total))
            for i, user in enumerate(db.query_users('where photo not null')):
                output = path.join(propics_dir, '{}{}'
                                   .format(user.photo.photo_id, get_extension(user.photo)))

                # Try downloading the photo
                try:
                    if path.isfile(output):
                        ok = True
                    else:
                        ok = self.client.download_profile_photo(user.photo,
                                                                add_extension=False,
                                                                file_path=output)
                except RPCError:
                    ok = False

                # Show the corresponding message
                if ok:
                    print('Downloaded {} out of {}, now for profile photo for "{}"'
                          .format(i, total, get_display_name(user)))
                else:
                    print('Downloaded {} out of {}, could not download profile photo for "{}"'
                          .format(i, total, get_display_name(user)))

        if dl_photos:
            total = db.count('messages where media_id = {}'.format(MessageMediaPhoto.constructor_id))
            print("Starting download for {} photos...".format(total))
            for i, msg in enumerate(db.query_messages('where media_id = {}'.format(MessageMediaPhoto.constructor_id))):
                output = path.join(photos_dir, '{}{}'
                                   .format(msg.media.photo.id, get_extension(msg.media)))

                # Try downloading the photo
                try:
                    if path.isfile(output):
                        ok = True
                    else:
                        ok = self.client.download_msg_media(msg.media,
                                                            add_extension=False,
                                                            file_path=output)
                except RPCError:
                    ok = False

                # Show the corresponding message
                if ok:
                    print('Downloaded {} out of {} photos'.format(i, total))
                else:
                    print('Photo {} out of {} download failed'.format(i, total))

        if dl_documents:
            total = db.count('messages where media_id = {}'.format(MessageMediaDocument.constructor_id))
            print("Starting download for {} documents...".format(total))
            for i, msg in enumerate(db.query_messages('where media_id = {}'.format(MessageMediaDocument.constructor_id))):
                output = path.join(documents_dir, '{}{}'
                                   .format(msg.media.document.id, get_extension(msg.media)))

                # Try downloading the document
                try:
                    if path.isfile(output):
                        ok = True
                    else:
                        ok = self.client.download_msg_media(msg.media,
                                                            add_extension=False,
                                                            file_path=output)
                except RPCError:
                    ok = False

                # Show the corresponding message
                if ok:
                    print('Downloaded {} out of {} documents'.format(i, total))
                else:
                    print('Document {} out of {} download failed'.format(i, total))

    # endregion

    def calculate_eta(self, downloaded, total):
        """Calculates the Estimated Time of Arrival (ETA)"""
        left = total - downloaded
        chunks_left = (left + self.download_chunk_size - 1) // self.download_chunk_size
        eta = chunks_left * self.download_delay
        return timedelta(seconds=eta)
