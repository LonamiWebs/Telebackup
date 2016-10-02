from os import path, makedirs
from shutil import copyfile

from exporter.html_tl_writer import HTMLTLWriter
from tl_database import TLDatabase


class Exporter:
    def __init__(self, output_dir='backups/exported'):
        self.output_dir = output_dir

        # Copy the required default resources
        makedirs(output_dir, exist_ok=True)
        copyfile('exporter/resources/style.css', path.join(output_dir, 'style.css'))

        makedirs(path.join(output_dir, 'media/profile_photos'), exist_ok=True)
        copyfile('exporter/resources/default_propic.png', path.join(output_dir, 'media/profile_photos/default.png'))

        makedirs(path.join(output_dir, 'media/photos'), exist_ok=True)
        copyfile('exporter/resources/default_photo.png', path.join(output_dir, 'media/photos/default.png'))

    # region Exporting databases

    def export(self, db_file, name):
        output_path = path.join(self.output_dir, name+'.html')
        with TLDatabase(db_file) as db:
            with HTMLTLWriter(output_path) as writer:
                # ascendant order = older messages -> newer messages (latest)
                for msg in db.query_messages('order by id asc'):
                    writer.write_message(msg, db)

    # endregion
