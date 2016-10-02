import json
from glob import glob
from os import path

from telethon import TelegramClient
from backuper import Backuper
from exporter.exporter import Exporter


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


def get_integer(message, minimum, maximum):
    while True:
        try:
            value = int(input(message))
            if not minimum <= value <= maximum:
                raise ValueError()

            return value
        except ValueError:
            print('Please enter an integer value between {} and {}'.format(minimum, maximum))


def get_metadata(db_id):
    with open('backups/{}.meta'.format(db_id), 'r') as file:
        return json.load(file)


def get_client():
    """Initializes and returns a TelegramClient"""

    print('Loading client...')
    # First, initialize our TelegramClient and connect
    settings = load_settings()
    client = TelegramClient(session_user_id=settings.get('session_name', 'anonymous'),
                            api_id=settings['api_id'],
                            api_hash=settings['api_hash'])
    client.connect()

    # Then, ensure we're authorized and have access
    if not client.is_user_authorized():
        client.send_code_request(str(settings['user_phone']))

        code = input('Enter the code you just received: ')
        client.sign_in(str(settings['user_phone']), code)

    return client


def make_backup():
    """Action that performs a backup"""
    # Retrieve the top dialogs
    client = get_client()
    dialogs, displays, inputs = client.get_dialogs(10)

    # Display them so the user can choose
    for i, display in enumerate(displays):
        print('{}. {}'.format(i+1, display))

    # Let the user decide who they want to backup
    i = int(input('What chat do you want to backup (0 to exit)?: ')) - 1

    if 0 <= i < 10:
        # Retrieve the selected user
        display = displays[i]
        input_peer = inputs[i]

        backuper = Backuper(client)
        backuper.begin_backup(input_peer=input_peer, peer_name=display)

    print('Exiting...')
    client.disconnect()


def export_html():
    """Action that exports a backup to HTML"""
    # First load all the saved databases (splitting extension and path)
    saved_db = [path.splitext(path.split(f)[1])[0] for f in glob('backups/*.tlo')]

    # Then ask the user who they want to export
    print('Available exportable databases:')
    for i, db_id in enumerate(saved_db):
        metadata = get_metadata(db_id)
        print('{}. {}, ID: {}'.format(i + 1,
                                      metadata.get('peer_name', '???'),
                                      db_id))

    db_id = saved_db[get_integer('Which one do you want to export?: ', 1, len(saved_db)) - 1]
    metadata = get_metadata(db_id)
    backup_name = input('How do you want to name the backup (defaults to {}): '
                        .format(metadata.get('peer_name', 'unnamed')))

    if not backup_name:
        backup_name = metadata.get('peer_name', 'unnamed')

    # Then finally export
    Exporter().export('backups/{}.tlo'.format(db_id), name=backup_name)

options = (
    ('Make a backup of a conversation', make_backup),
    ('Export a backup into HTML format', export_html),
    ('Exit', None),
)


def main():
    print('Welcome to Telebackup, please select an option:')
    for i, option_method in enumerate(options):
        option, method = option_method
        print('  {}. {}'.format(i + 1, option))

    option = get_integer('Enter the option index: ', 1, len(options)) - 1
    method = options[option][1]
    if method:
        method()


if __name__ == '__main__':
    main()
