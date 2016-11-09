import json
from glob import glob
from os import path

from telethon import TelegramClient

from gui import start_app

cached_client = None


def load_settings(path='api/settings'):
    """Loads the user settings located under `api/`"""
    settings = {}
    with open(path, 'r', encoding='utf-8') as file:
        for line in file:
            value_pair = line.split('=')
            left = value_pair[0].strip()
            right = value_pair[1].strip()
            if right.isnumeric():
                settings[left] = int(right)
            else:
                settings[left] = right

    return settings


def sanitize_string(string):
    """Sanitizes a string for it to be between U+0000 and U+FFFF"""
    return ''.join(c for c in string if ord(c) <= 0xFFFF).strip()


def get_integer(message, minimum, maximum):
    """Retrieves an integer value, in such a way that `minimum ≤ value ≤ maximum`"""
    while True:
        try:
            value = int(input(message))
            if not minimum <= value <= maximum:
                raise ValueError()

            return value
        except ValueError:
            print('Please enter an integer value between {} and {}'.format(minimum, maximum))


def get_metadata(db_id):
    """Gets the metadata for the specified backup database ID"""
    with open('backups/{}.meta'.format(db_id), 'r') as file:
        return json.load(file)


def size_to_str(size):
    """Converts a size, given in bytes length, to a string representation"""
    #                                             Only to keep us covered (1024^8)
    sizes = ['bytes', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB']
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


def get_cached_client():
    """Gets an authorized TelegramClient, performing
       the authorization process if it's the first time"""
    global cached_client
    if not cached_client:
        print('Loading client...')
        settings = load_settings()
        cached_client = TelegramClient(session_user_id=settings.get('session_name', 'anonymous'),
                                api_id=settings['api_id'],
                                api_hash=settings['api_hash'])
        cached_client.connect()

        # Then, ensure we're authorized and have access
        if not cached_client.is_user_authorized():
            # Import the login window locally to avoid cyclic dependencies
            from gui.windows import LoginWindow

            print('First run, client not authorized. Sending code request.')
            cached_client.send_code_request(str(settings['user_phone']))
            start_app(LoginWindow, client=cached_client, phone=settings['user_phone'])

            del LoginWindow

        print('Client loaded and authorized.')
    return cached_client
