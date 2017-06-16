from backuper import Backuper
from utils import create_client


def main(client):
    """Main method"""
    '''
    entity = client.get_dialogs(1)[1][0]
    backuper = Backuper(client, entity)
    backuper.start_backup()
    '''


if __name__ == '__main__':
    client = None
    try:
        client = create_client()
        main(client)
    finally:
        if client:
            client.disconnect()
