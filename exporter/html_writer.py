class HTMLWriter:
    """Class used to write HTML documents"""

    def __init__(self, file_path):
        self.handle = open(file_path, 'w')
        self.tags = []

    def close(self):
        self.handle.close()

    def write(self, html):
        self.handle.write(html)

    def write_text(self, text):
        if text:
            self.write(text
                       .replace('<', '&lt;')
                       .replace('>', '&gt;')
                       .replace('\n', '<br/>'))

    def tag(self, tag_name, **attributes):
        """Opens a tag which is automatically closed, with optional named attributes"""
        self.open_tag(tag_name, auto_close=True, **attributes)

    def open_tag(self, tag_name, auto_close=False, **attributes):
        """Opens a tag, with optional attributes (use named arguments)"""
        if attributes:
            # Write <tag_name attr1="value1" attr2="value2" ...>
            # Strip _ from the tag name because, for example, "class" is reserved so "_class" may be used
            self.write('<{} {}'.format(tag_name,
                                       ' '.join('{}="{}"'.format(k.strip('_'), v) for k, v in attributes.items())))
        else:
            # Write <tag>
            self.write('<{}'.format(tag_name))

        # The end of the tag will be different, based on whether it will auto-close or not
        if auto_close:
            self.write('/>')
        else:
            self.tags.append(tag_name)
            self.write('>')

    def close_tag(self):
        """Closes the latest open tag"""
        tag = self.tags.pop()
        self.write('</{}>'.format(tag))
        return tag

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
