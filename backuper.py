import json
import shutil
from datetime import timedelta, datetime
from os import path, listdir, remove
from os.path import isfile, isdir
from threading import Thread
from time import sleep

import telethon.tl.all_tlobjects as all_tlobjects
from telethon import RPCError
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument
from telethon.tl.types.messages import Messages, MessagesSlice

from telethon.utils import \
    BinaryReader, BinaryWriter, \
    get_input_peer

from media_handler import MediaHandler
from tl_database import TLDatabase

scheme_layer = all_tlobjects.layer
del all_tlobjects


AVERAGE_PROPIC_SIZE = 128 * 1024  # KB -> Bytes


class Backuper:
    # Default output directory for all the made backups
    backups_dir = 'backups'

    #region Initialize

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
        self.media_handler = MediaHandler(self.backup_dir)

        # Open and close the database to create the require directories
        TLDatabase(self.backup_dir).close()

        # Set up all the directories and files that we'll be needing
        self.files = {
            'entity': path.join(self.backup_dir, 'entity.tlo'),
            'metadata': path.join(self.backup_dir, 'metadata.json')
        }
        # TODO Crashes if the other user got us blocked (AttributeError: 'NoneType' object has no attribute 'photo_big')

        # Is the backup running (are messages being downloaded?)
        self.backup_running = False

        # Event that gets fired when metadata is saved
        self.on_metadata_change = None

        # Save the entity and load the metadata
        with open(self.files['entity'], 'wb') as file:
            with BinaryWriter(file) as writer:
                entity.on_send(writer)
        self.metadata = self.load_metadata()

    #endregion

    #region Metadata handling

    def save_metadata(self):
        """Saves the metadata for the current entity"""
        with open(self.files['metadata'], 'w', encoding='utf-8') as file:
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
            with open(self.files['metadata'], 'r', encoding='utf-8') as file:
                return json.load(file)

    def update_total_messages(self):
        """Updates the total messages with the current peer"""

        result = self.client.invoke(GetHistoryRequest(
            peer=get_input_peer(self.entity),
            # No offset, we simply want the total messages count
            offset_id=0, limit=0, offset_date=None,
            add_offset=0, max_id=0, min_id=0
        ))
        self.metadata['total_msgs'] = getattr(result, 'count', len(result.messages))
        self.metadata['etl'] = str(self.calculate_etl(
            self.metadata['saved_msgs'], self.metadata['total_msgs']))

        self.save_metadata()

    #endregion

    #region Backups listing

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

    #endregion

    #region Backup exists and deletion

    @staticmethod
    def exists_backup(entity_id):
        return isdir(path.join(Backuper.backups_dir, str(entity_id)))

    def delete_backup(self):
        """Deletes the backup with the current peer from disk and sets
           everything to None (the backup becomes unusable)"""
        shutil.rmtree(self.backup_dir)

    #endregion

    #region Backups generation

    def start_backup(self):
        """Begins the backup on the given peer"""
        Thread(target=self.backup_messages_thread).start()

    def start_media_backup(self, **kwargs):
        """Begins the media backup on the given peer.
           The valid named arguments are:

           dl_propics: Boolean value determining whether profile pictures should be downloaded
           dl_photos: Boolean value determining whether photos should be downloaded
           dl_docs: Boolean value determining whether documents (and gifs, and stickers) should be downloaded

           docs_max_size: If specified, determines the maximum document size allowed in bytes
           after_date: If specified, only media after this date will be downloaded
           before_date: If specified, only media before this date will be downloaded

           progress_callback: If specified, current download progress will be reported here
                              invoking progress_callback(saved bytes, total bytes, estimated time left)"""
        Thread(target=self.backup_media_thread, kwargs=kwargs).start()

    def stop_backup(self):
        """Stops the backup (either messages or media) on the given peer"""
        self.backup_running = False

    #region Messages backup

    def backup_messages_thread(self):
        """This method backups the messages and should be ran in a different thread"""
        self.backup_running = True

        # Create a connection to the database
        db = TLDatabase(self.backup_dir)

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
        self.metadata['saved_msgs'] = db.count('messages')

        # We also need to keep track of how many messages we've downloaded now
        # in order to calculate the estimated time left properly
        saved_msgs_now = 0

        # Make the backup
        try:
            # We need this to invoke GetHistoryRequest
            input_peer = get_input_peer(self.entity)

            # Keep track from when we started to determine the estimated time left
            start = datetime.now()

            # Enter the download-messages main loop
            while self.backup_running:
                # Invoke the GetHistoryRequest to get the next messages after those we have
                result = self.client.invoke(GetHistoryRequest(
                    peer=input_peer,
                    offset_id=self.metadata['resume_msg_id'],
                    limit=self.download_chunk_size,
                    offset_date=None,
                    add_offset=0,
                    max_id=0,
                    min_id=0
                ))
                # For some strange reason, GetHistoryRequest might return upload.file.File
                # Ensure we retrieved Messages or MessagesSlice
                if not isinstance(result, Messages) and not isinstance(result, MessagesSlice):
                    print('Invalid result type when downloading messages:', type(result))
                    sleep(self.download_delay)
                    continue

                self.metadata['total_msgs'] = getattr(result, 'count', len(result.messages))

                # First add users and chats, replacing any previous value
                for user in result.users:
                    db.add_object(user, replace=True)
                for chat in result.chats:
                    db.add_object(chat, replace=True)

                # Then add the messages to the backup
                for msg in result.messages:
                    if db.in_table(msg.id, 'messages'):
                        # If the message we retrieved was already saved, this means that we're
                        # done because we have the rest of the messages.
                        # Clear the list so we enter the next if, and break to early terminate
                        self.metadata['resume_msg_id'] = result.messages[-1].id
                        del result.messages[:]
                        break
                    else:
                        db.add_object(msg)
                        saved_msgs_now += 1
                        self.metadata['saved_msgs'] += 1
                        self.metadata['resume_msg_id'] = msg.id

                self.metadata['etl'] = str(self.calculate_etl(
                    saved_msgs_now, self.metadata['total_msgs'],
                    start=start))

                # Always commit at the end to save changes
                db.commit()
                self.save_metadata()

                # The list can be empty because we've either used a too big offset
                # (in which case we have all the previous messages), or we've reached
                # a point where we have the upcoming messages (so there's no need to
                # download them again and we stopped)
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
            db.commit()
            self.save_metadata()

        finally:
            self.backup_running = False

    #endregion

    #region Media backups

    def backup_propic(self):
        """Backups the profile picture for the given
           entity as the current peer profile picture, returning its path"""

        # Allow multiple versions of the profile picture
        # TODO Maybe this should be another method, because when downloading media... We also have multiple versions
        filename = self.media_handler.get_propic_path(self.entity, allow_multiple=True)
        generic_filename = self.media_handler.get_propic_path(self.entity)
        if filename:  # User may not have a profile picture
            if not isfile(filename):
                # Only download the file if it doesn't exist yet
                self.client.download_profile_photo(self.entity.photo,
                                                   file_path=filename,
                                                   add_extension=False)
                # If we downloaded a new version, copy it to the "default" generic file
                if isfile(generic_filename):
                    remove(generic_filename)
                shutil.copy(filename, generic_filename)

            # The user may not have a profile picture
            return generic_filename

    def calculate_download_size(self, dl_propics, dl_photos, dl_docs,
                                docs_max_size=None, before_date=None, after_date=None):
        """Estimates the download size, given some parameters"""
        with TLDatabase(self.backup_dir) as db:
            total_size = 0

            # TODO How does Telegram Desktop find out the profile photo size?
            if dl_propics:
                total_size += db.count('users where photo not null') * AVERAGE_PROPIC_SIZE

            if dl_photos:
                for msg in db.query_messages(self.get_query(MessageMediaPhoto, before_date, after_date)):
                    total_size += msg.media.photo.sizes[-1].size

            if dl_docs:
                for msg in db.query_messages(self.get_query(MessageMediaDocument, before_date, after_date)):
                    if not docs_max_size or msg.media.document.size <= docs_max_size:
                        total_size += msg.media.document.size

            return total_size

    def backup_media_thread(self, dl_propics, dl_photos, dl_docs,
                            docs_max_size=None, before_date=None, after_date=None,
                            progress_callback=None):
        """Backups the specified media contained in the given database file"""
        self.backup_running = True

        # Create a connection to the database
        db = TLDatabase(self.backup_dir)

        # Store how many bytes we have/how many bytes there are in total
        current = 0
        total = self.calculate_download_size(dl_propics, dl_photos, dl_docs,
                                             docs_max_size, after_date, before_date)

        # Keep track from when we started to determine the estimated time left
        start = datetime.now()

        if dl_propics:
            # TODO Also query chats and channels
            for user in db.query_users('where photo not null'):
                if not self.backup_running:
                    return
                # Try downloading the photo
                output = self.media_handler.get_propic_path(user)
                try:
                    if not self.valid_file_exists(output):
                        self.client.download_profile_photo(
                            user.photo, add_extension=False, file_path=output)
                        sleep(self.download_delay)

                except RPCError as e:
                    print('Error downloading profile photo:', e)
                finally:
                    current += AVERAGE_PROPIC_SIZE
                    if progress_callback:
                        progress_callback(current, total, self.calculate_etl(current, total, start))

        if dl_photos:
            for msg in db.query_messages(self.get_query(MessageMediaPhoto, before_date, after_date)):
                if not self.backup_running:
                    return
                # Try downloading the photo
                output = self.media_handler.get_msg_media_path(msg)
                try:
                    if not self.valid_file_exists(output):
                        self.client.download_msg_media(
                            msg.media, add_extension=False, file_path=output)
                        sleep(self.download_delay)

                except RPCError as e:
                    print('Error downloading photo:', e)
                finally:
                    current += msg.media.photo.sizes[-1].size
                    if progress_callback:
                        progress_callback(current, total, self.calculate_etl(current, total, start))

        # TODO Add an internal callback to determine how the current document download is going,
        # and update our currently saved bytes count based on that
        if dl_docs:
            for msg in db.query_messages(self.get_query(MessageMediaDocument, before_date, after_date)):
                if not self.backup_running:
                    return

                if not docs_max_size or msg.media.document.size <= docs_max_size:
                    # Try downloading the document
                    output = self.media_handler.get_msg_media_path(msg)
                    try:
                        if not self.valid_file_exists(output):
                            self.client.download_msg_media(
                                msg.media, add_extension=False, file_path=output)
                        sleep(self.download_delay)

                    except RPCError as e:
                        print('Error downloading document:', e)
                    finally:
                        current += msg.media.document.size
                        if progress_callback:
                            progress_callback(current, total, self.calculate_etl(current, total, start))
        db.close()

    #endregion

    #endregion

    #region Utilities

    def calculate_etl(self, downloaded, total, start=None):
        """Calculates the estimated time left, based on how long it took us
           to reach "downloaded" and how many messages we have left.

           If no start time is given, the time will simply by estimated by how
           many chunks are left, which will NOT work if what is being downloaded is media"""
        left = total - downloaded
        if not start:
            # We add chunk size - 1 because division will truncate the decimal places,
            # so for example, if we had a chunk size of 8:
            #   7 messages + 7 = 14 -> 14 // 8 = 1 chunk download required
            #   8 messages + 7 = 15 -> 15 // 8 = 1 chunk download required
            #   9 messages + 7 = 16 -> 16 // 8 = 2 chunks download required
            #
            # Clearly, both 7 and 8 fit in one chunk, but 9 doesn't.
            chunks_left = (left + self.download_chunk_size - 1) // self.download_chunk_size
            etl = chunks_left * self.download_delay
        else:
            if downloaded:
                delta_time = (datetime.now() - start).total_seconds() / downloaded
                etl = left * delta_time
            else:
                etl = 0

        return timedelta(seconds=round(etl, 1))

    @staticmethod
    def get_query(clazz, before_date=None, after_date=None):
        """Returns a database query filtering by media_id (its class),
           and optionally range dates"""
        filters = 'where media_id = {}'.format(clazz.constructor_id)
        if before_date:
            filters += " and date <= '{}'".format(before_date)
        if after_date:
            filters += " and date >= '{}'".format(after_date)
        return filters

    @staticmethod
    def valid_file_exists(file):
        """Determines whether a file exists and its "valid"
           (i.e., the file size is greater than 0; if it's 0, it probably faild dueto an RPC error)"""
        return path.isfile(file) and path.getsize(file) > 0

    #endregion
