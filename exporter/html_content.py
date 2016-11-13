"""
This file contains constant values representing the HTML contents from an exported backup.
You shall modify this file if you wish to change the appearance of the exported backup, although
some additional changes may be required on the HTMLFormatter (i.e. adding new fields).
"""

# TODO Maybe a get_content which could take EVERY parameter and only set those required?
# This would give more power when editing this file, since every replace-field would be available everywhere
# For example, '1 {a} 3 {b} 5'.format(a=2, b=4, c=6) would only use 'a' and 'b'

#region Beginning and ending

BEGINNING = \
    """
    <!DOCTYPE html>
    <html>
    <head>
        <link rel="stylesheet" type="text/css" href="../../style.css">
        <meta charset="utf-8">
    </head>
    <body>
        <div style="display:inline-block; width:100%;">
            <div class="date">
                <p>{dates}</p>
            </div>
        </div>
        <table id="messages" width="100%">
    """.strip()

END = \
    """
        </table>
    </body>
    </html>
    """.strip()

#endregion

#region Dates

LINK_DATE = \
    """
    <a href="{file}" class="date">{date}</a>
    """.strip()

DATE = \
    """
    <span title="{long_date}">{short_date}</span>
    """.strip()

#endregion

#region Images

IMG = \
    """
    <img src="{file}" onerror="if (this.src != '{fallback}') this.src = '{fallback}';">
    """.strip()

PROPIC_EMPTY = \
    """
    <td class="propic"/>
    """.strip()

PROPIC = \
    """
    <td class="propic">{img}</td>
    """.strip()

#endregion

#region Messages

MESSAGE_HEADER = \
    """
    <p class="msg-header"><b>{sender}</b></p>
    """.strip()

MESSAGE_HEADER_FWD = \
    """
    <p class="msg-header"><b>{sender}</b>, forwarded from <b>{original_sender}</b> at {date}</p>
    """.strip()

MESSAGE_HEADER_REPLY = \
    """
        <p class="msg-header"><b>{sender}</b>, in reply to <b>{replied_sender}</b> who said:</p>
        <a href="{replied_id_link}" class="reply"><p>{replied_content}</p></a>
        <hr />
    """.strip()

REPLIED_CONTENT = \
    """
        <p>{replied_content}</p>
    """.strip()

REPLIED_CONTENT_IMG = \
    """
        <table>
        <tr>
            <td>{img}</td>
            <td><p>{replied_content}</p></td>
        </tr>
        </table>
    """.strip()

# Note that the messages should be encapsulated in table rows ('<tr/>')
MESSAGE = \
    """
        <td>
            <div class="msg {in_out}" id="msg-id-{id}">
                {header}
                {content}
                <p class="time">{date}</p>
            </div>
        </td>
    """.strip()

#endregion

#region Messsage service

MESSAGE_SERVICE = \
    """
        <tr>
            <td />
            <td>
                <div class="service" id="msg-id-{id}">
                    {content}
                    <p class="time">{date}</p>
                </div>
            </td>
            <td />
        </tr>
    """

#endregion
