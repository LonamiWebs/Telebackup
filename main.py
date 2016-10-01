from telethon import TelegramClient
from backuper import Backuper


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


def main():
    print('Loading Telebackup...')

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

    # Retrieve the top dialogs
    dialogs, displays, inputs = client.get_dialogs(10)

    # Display them so the user can choose
    for i, display in enumerate(displays):
        print('{}. {}'.format(i+1, display))

    # Let the user decide who they want to backup
    i = int(input('What chat do you want to backup (0 to exit)?: ')) - 1

    if 0 <= i < 10:
        # Retrieve the selected user
        input_peer = inputs[i]

        backuper = Backuper(client)
        backuper.begin_backup(input_peer)

    print('Exiting...')
    client.disconnect()

if __name__ == '__main__':
    main()

