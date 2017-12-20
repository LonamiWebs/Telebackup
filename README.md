# Project Abandoned

Please refer to [**@expectocode**'s `telegram-export`](https://github.com/expectocode/telegram-export/) from now on.

You can still read the old `README` below, but this project is broken and I don't plan on fixing it.

## Telebackup
Telebackup is the original purpose for which [Telethon](https://github.com/LonamiWebs/Telethon) was made.
The application's main purpose is to backup any conversation from Telegram, and save them in your disk.

Please note that a lot needs to be done! This application also requires the `telethon` module, installable via `pip`.
This application also has the exact same setup as `telethon` (copy `settings_example` to `settings` and fill in your values).

### Requirements
You need the following Python packages in order for Telebackup to work:
- `telethon` ([GitHub](https://github.com/LonamiWebs/Telethon), [PyPi](https://pypi.python.org/pypi/Telethon/))
- `pillow` ([GitHub](https://github.com/python-pillow/Pillow/), [PyPi](https://pypi.python.org/pypi/Pillow/))

In case you encounter the error "ImportError: No module named 'PIL'", you may need to reinstall `pillow`.

## Important notes
Please note that this program will **not** update those messages which were edited (as of now)! This is, after you
backup a conversation, if you edit messages which were included in the backup, they will not be updated.
This, however, should be no issue.

### FAQ
#### The exported backups don't look right
Please make sure you have enabled _JavaScript_ for local files.
Also, Firefox does not support `.webp` files, which is the stickers' format.
You shall consider using another web browser, such as _Chromium_
(at least when viewing the backups), which can display these files.

### How does it work?
Every dialog (let it be an user, a chat, or a channel) is stored in its own database (SQLite). This database includes all
the users and channels who have participated in it, and all the messages related to that dialog. This means that
you will do get duplicates if, for example, an user talked in two chats; however, this highly simplifies everything,
by not adding another unique database for users, chats and channels, which multiple threads may need access to.

Some parts of these messages are saved as blobs, such as the lists of entities in a message (i.e., when you talk via
[@bold](https://telegram.me/bold)) or message media (which can be a document, a photo...). Creating tables for these
would absolutely be crazy, because there are many different types. Instead, they're saved as blobs _and_ the media
constructor ID as a separate column, so you can still query for which messages have a photo, and which have a document.
