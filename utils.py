import json
from glob import glob
from os import path

from telethon import TelegramClient
from telethon.utils import get_display_name


def load_settings(path='api/settings'):
    """Loads the user settings located under `api/`"""
    with open(path, 'r', encoding='utf-8') as file:
        return {
            l.strip(): r.strip()
            for l, r in (l.split('=') for l in file if l.strip())
        }


def sanitize_string(string):
    """Sanitizes a string for it to be between U+0000 and U+FFFF"""
    if string:
        return ''.join(c for c in string if ord(c) <= 0xFFFF).strip()


def get_integer(message, minimum, maximum):
    """Retrieves an integer value prompted from console,
       in such a way that `minimum ≤ value ≤ maximum`
    """
    while True:
        try:
            value = int(input(message))
            if not minimum <= value <= maximum:
                raise ValueError()

            return value
        except ValueError:
            print('Please enter an integer value between {} and {}'
                  .format(minimum, maximum))


def get_metadata(db_id):
    """Gets the metadata for the specified backup database ID"""
    with open('backups/{}.meta'.format(db_id), 'r', encoding='utf-8') as file:
        return json.load(file)


def size_to_str(size):
    """Converts a size, given in bytes length, to a string representation"""
    sizes = ['bytes', 'KiB', 'MiB', 'GiB', 'TiB']
    pos = 0
    while size >= 1024:
        size /= 1024
        pos += 1

    return '{:.2f} {}'.format(size, sizes[pos])


def prompt_pick_backup(message):
    """Prompts the user to pick an existing database, and returns the
       selected choice database ID and its metadata"""

    # First load all the saved databases (splitting extension and path)
    saved_db = [path.splitext(path.split(f)[1])[0] for f in glob('backups/*.tlo')]

    # Then prompt the user
    print('Available backups databases:')
    for i, db_id in enumerate(saved_db):
        metadata = get_metadata(db_id)
        print('{}. {}, ID: {}'.format(i + 1,
                                      metadata.get('peer_name', '???'),
                                      db_id))

    db_id = saved_db[get_integer(message, 1, len(saved_db)) - 1]
    return db_id, get_metadata(db_id)


def get_display(entity):
    if hasattr(entity, 'deleted') and entity.deleted:
        return '(deleted user %d)' % entity.id
    else:
        return sanitize_string(get_display_name(entity))


def create_client():
    """Gets an authorized TelegramClient, performing
       the authorization process if it's the first time"""
    print('Loading client...')
    settings = load_settings()
    client = TelegramClient(
        settings.get('session_name', 'anonymous'),
        settings['api_id'], settings['api_hash']
    )

    print('Connecting...')
    client.connect()
    if not client.is_user_authorized():
        print('Sending code request...')
        client.send_code_request(settings['user_phone'])
        code = input('Enter the code: ')
        client.sign_in(settings['user_phone'], code)

    print('Client loaded.')
    return client
