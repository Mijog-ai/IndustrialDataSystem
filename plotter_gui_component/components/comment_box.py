from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QTextEdit

class CommentBox(QGroupBox):
    def __init__(self, parent):
        super().__init__("Comments", parent)
        self.layout = QVBoxLayout()
        self.setup_ui()

    def setup_ui(self):
        self.comment_box = QTextEdit()
        self.layout.addWidget(self.comment_box)

        self.setLayout(self.layout)

    def get_comments(self):
        return self.comment_box.toPlainText()

    def set_comments(self, comments):
        self.comment_box.setPlainText(comments)

    def clear(self):
        self.comment_box.clear()