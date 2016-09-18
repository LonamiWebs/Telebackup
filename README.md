# Telebackup
Telebackup is the original purpose for which [Telethon](https://github.com/LonamiWebs/Telethon) was made.
The application's main purpose is to backup any conversation from Telegram, and save them in your disk.

Please note that a lot needs to be done! This application also requires the `telethon` module, installable via `pip`.
This application also has the exact same setup as `telethon` (copy `settings_example` to `settings` and fill in your values).

## Why doesn't this application use a normal database?
There are multiple reasons not to use one:
- There are many, many different Telegram objects. Each would require a unique table!
- Not only there are many objects, but also many relations which would need to be written be hand.
- Telegram's scheme changes over time. This means that the database would need to be rewritten every time.

On the other hand, by taking advantage of the fact that TLObjects can be serialized:
- The resulting backup is smaller.
- It's easier to implement.
- It's easier to migrate. All one needs is both versions of the scheme, old and new,
  and simply take the properties which didn't change.
