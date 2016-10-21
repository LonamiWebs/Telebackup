import json
import shutil
from datetime import timedelta
from os import makedirs, path, listdir
from os.path import isfile, isdir
from threading import Thread
from time import sleep

import telethon.tl.all_tlobjects as all_tlobjects
from telethon import RPCError
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument
from telethon.utils import \
    BinaryReader, BinaryWriter, \
    get_display_name, get_extension, get_input_peer

from tl_database import TLDatabase

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

        self.directories = {
            'propics': path.join(self.backup_dir, 'propics'),

            'profile_photos': path.join(self.backup_dir, 'media', 'profile_photos'),
            'photos': path.join(self.backup_dir, 'media', 'photos'),
            'documents': path.join(self.backup_dir, 'media', 'documents'),
            'stickers': path.join(self.backup_dir, 'media', 'stickers')
        }

        self.files = {
            'entity': path.join(self.backup_dir, 'entity.tlo'),
            'metadata': path.join(self.backup_dir, 'metadata.json'),
            'database': path.join(self.backup_dir, 'backup.sqlite'),
            'propic': path.join(self.directories['propics'],
                                '{}.jpg'.format(self.entity.photo.photo_big.local_id))
        }

        # Is the backup running (are messages being downloaded?)
        self.backup_running = False

        # Event that gets fired when metadata is saved
        self.on_metadata_change = None

        # Ensure the directory for the backups
        makedirs(self.backup_dir, exist_ok=True)
        for directory in self.directories.values():
            makedirs(directory, exist_ok=True)

        # Save the entity and load the metadata
        with open(self.files['entity'], 'wb') as file:
            with BinaryWriter(file) as writer:
                entity.on_send(writer)
        self.metadata = self.load_metadata()

        self.db = None  # This will be loaded later

    # endregion

    def delete_backup(self):
        """Deletes the backup with the current peer from disk and sets
           everything to None (the backup becomes unusable)"""
        shutil.rmtree(self.backup_dir)

    @staticmethod
    def enumerate_backups_entities():
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

    def save_metadata(self):
        """Saves the metadata for the current entity"""
        with open(self.files['metadata'], 'w') as file:
            json.dump(self.metadata, file)

        if self.on_metadata_change:
            self.on_metadata_change()

    def load_metadata(self):
        """Loads the metadata of the current entity"""
        if not path.isfile(self.files['metadata']):
            return {
                'resume_msg_id': 0,
                'saved_msgs': 0,
                'total_msgs': 0,
                'etl': '???',
                'scheme_layer': scheme_layer
            }
        else:
            with open(self.files['metadata'], 'r') as file:
                return json.load(file)

    def get_create_media_dirs(self):
        """Retrieves the paths for the profile photos, photos,
           documents and stickers backups directories, creating them too"""
        directories = []
        for directory in ():
            current = path.join(self.backup_dir, 'media', directory)
            makedirs(current, exist_ok=True)
            directories.append(current)

        return directories

    # region Making backups

    def backup_propic(self):
        """Backups the profile picture for the given
           entity as the current peer profile picture, returning its path"""
        if not isfile(self.files['propic']):
            # Only download the file if it doesn't exist yet
            self.client.download_profile_photo(self.entity.photo,
                                               file_path=self.files['propic'],
                                               add_extension=False)
        return self.files['propic']

    def start_backup(self):
        """Begins the backup on the given peer"""
        Thread(target=self.backup_messages_thread).start()

    def stop_backup(self):
        """Stops the backup on the given peer"""
        self.backup_running = False

    def backup_messages_thread(self):
        """This method backups the messages and should be ran in a different thread"""
        self.backup_running = True

        # Create a connection to the database
        self.db = TLDatabase(self.files['database'])

        # Determine whether we started making the backup from the very first message or not.
        # If this is the case:
        #   We won't need to come back to the first message again after we've finished downloading
        #   them all, since that first message will already be in backup.
        #
        # Otherwise, if we did not start from the first message:
        #   More messages were in the backup already, and after we backup those "left" ones,
        #   we must return to the first message and backup until where we started.
        started_at_0 = self.metadata['resume_msg_id'] == 0

        # Keep an internal downloaded count for it to be faster
        # (instead of querying the database all the time)
        self.metadata['saved_msgs'] = self.db.count('messages')

        # Make the backup
        try:
            input_peer = get_input_peer(self.entity)
            while self.backup_running:
                result = self.client.invoke(GetHistoryRequest(
                    peer=input_peer,
                    offset_id=self.metadata['resume_msg_id'],
                    limit=self.download_chunk_size,
                    offset_date=None,
                    add_offset=0,
                    max_id=0,
                    min_id=0
                ))
                self.metadata['total_msgs'] = getattr(result, 'count', len(result.messages))

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
                        self.metadata['resume_msg_id'] = result.messages[-1].id
                        del result.messages[:]
                        break
                    else:
                        self.db.add_object(msg)
                        self.metadata['saved_msgs'] += 1
                        self.metadata['resume_msg_id'] = msg.id

                self.metadata['etl'] = str(self.calculate_etl(
                    self.metadata['saved_msgs'], self.metadata['total_msgs']))

                # Always commit at the end to save changes
                self.db.commit()
                self.save_metadata()

                if not result.messages:
                    # We've downloaded all the messages since the last backup
                    if started_at_0:
                        # And since we started from the very first message, we have them all
                        print('Downloaded all {}'.format(self.metadata['total_msgs']))
                        break
                    else:
                        # We need to start from the first message (latest sent message)
                        # and backup again until we have them all
                        self.metadata['resume_msg_id'] = 0
                        started_at_0 = True

                # Always sleep a bit, or Telegram will get angry and tell us to chill
                sleep(self.download_delay)

            pass  # end while

        except KeyboardInterrupt:
            print('Operation cancelled, not downloading more messages!')
            # Also commit here, we don't want to lose any information!
            self.db.commit()
            self.save_metadata()

        finally:
            self.backup_running = False

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

    def calculate_etl(self, downloaded, total):
        """Calculates the Estimated Time Left (ETL)"""
        left = total - downloaded
        chunks_left = (left + self.download_chunk_size - 1) // self.download_chunk_size
        eta = chunks_left * self.download_delay
        return timedelta(seconds=eta)
