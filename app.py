import os
import sys
import shutil
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
import base64
from PySide6.QtCore import Qt, Signal, QEvent
from PySide6.QtGui import QPixmap, QGuiApplication, QAction, QIcon
from PySide6.QtWidgets import (
    QMainWindow, QApplication, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, QFileDialog, QDialog,
    QStackedWidget, QWidget, QSpacerItem, QSizePolicy, QListWidget, QToolBar, QInputDialog, QDialogButtonBox
)


load_dotenv()
api_key = os.getenv("OPENAI_API")
client = OpenAI(api_key=api_key)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Gen v1.0.0")
        self.setFixedSize(400, 200)

        self.image_window = None

        self.stack = QStackedWidget()

        self.prompt_page = QWidget()
        self.prompt_page.installEventFilter(self)
        
        self.image_repo = QWidget()

        self.build_image_gen()
        self.build_image_list()

        self.stack.addWidget(self.prompt_page)
        self.stack.addWidget(self.image_repo)
        self.setCentralWidget(self.stack)


    def build_image_gen(self):
        layout = QVBoxLayout()

        self.title = QLabel("Image Generator")
        self.title.setStyleSheet("font-size: 30px; font-style: italic; font-style: bold;")

        self.subtitle = QLabel("Press 'F2' to upload an image")
        self.subtitle.setStyleSheet("font-size: 11px; font-style: italic;")

        spacer = QSpacerItem(20, 15, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        self.prompt_input = QLineEdit()
        self.prompt_input.setPlaceholderText("Describe your image...")
        self.prompt_input.setFixedWidth(350)
        self.prompt_input.installEventFilter(self)

        self.upload_btn = QPushButton("Add File")
        self.upload_btn.setFixedWidth(60)
        self.upload_btn.hide()
        self.upload_btn.clicked.connect(self.upload_file)

        self.hbox = QHBoxLayout()
        self.hbox.addWidget(self.prompt_input)
        self.hbox.addWidget(self.upload_btn)

        self.submit_prompt = QPushButton("✨ Generate ✨")
        self.submit_prompt.setFixedWidth(150)

        self.submit_prompt.clicked.connect(self.on_generate_press)

        spacer2 = QSpacerItem(20, 10, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        go_saved_images = QPushButton("Saved Images")
        go_saved_images.setFixedWidth(150)
        go_saved_images.clicked.connect(lambda: self.stack.setCurrentWidget(self.image_repo))

        layout.addWidget(self.title, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.subtitle, alignment=Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignTop)
        layout.addItem(self.hbox)
        layout.addItem(spacer)
        layout.addWidget(self.submit_prompt, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(go_saved_images, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addItem(spacer2)

        self.prompt_page.setLayout(layout)

    def eventFilter(self, obj, event):
        self.is_image_added:bool

        if obj in (self.prompt_input, self.prompt_page) and event.type() == QEvent.KeyPress:
            key_event = event

            if key_event.key() == Qt.Key_F2 and self.upload_btn.isHidden() == False:
                print("F2 pressed! Hiding upload button")
                self.is_image_added = False
                self.upload_btn.hide()
                self.prompt_input.setFixedWidth(350)
                self.hbox.update()
                return True
            
            elif key_event.key() == Qt.Key_F2 and self.upload_btn.isHidden() == True:
                print("F2 pressed! Unhidding upload button")
                self.is_image_added = True
                self.upload_btn.show()
                self.prompt_input.setFixedWidth(300)
                self.hbox.update()
                return True

        return super().eventFilter(obj, event)
    
    def upload_file(self):
        self.uploaded_file, _ = QFileDialog.getOpenFileName(self, "QFileDialog.getOpenFileName()", "", "All Files (*);;Text Files (*.txt)")
        if self.uploaded_file:
            self.upload_btn.setEnabled(False)
            self.upload_btn.setStyleSheet("background-color: green;")
            self.upload_btn.setText("Added!")

    def on_generate_press(self):
        prompt = self.prompt_input.text()

        if prompt: 

            print(f"Prompt: {prompt}")

            today = datetime.now().strftime("%m.%d.%y_%H:%M")
            file_name = os.path.join("images", f"{today}.png")

            try:
                if self.is_image_added: 
                    print(f"Submitting prompt with {os.path.splitext(os.path.basename(self.uploaded_file))[0]}")
                    result = client.images.edit(
                        model="gpt-image-1",
                        image=open(self.uploaded_file, "rb"),
                        prompt=prompt
                    )

                else:
                    print("Submitting prompt with no image")
                    result = client.images.generate(
                        model="gpt-image-1",
                        prompt=prompt
                    )
            
                image_base64 = result.data[0].b64_json
                image_bytes = base64.b64decode(image_base64)

                with open(file_name, "wb") as f:
                    f.write(image_bytes)
                
                print("File added")
                self.prompt_input.clear()

                self.open_after_gen(file_name)
                self.refresh_image_list()
                print("Image page showing")

            except Exception as e:
                print("There was an error generating the image:", e)

        else:
            msg = "Please enter a prompt"
            dlg = DialogueBox(msg, self)
            dlg.exec()


    def open_after_gen(self, item):
        if self.image_window is None or not self.image_window.isVisible():
            self.image_window = ImageWindow(item)
            self.image_window.file_changed.connect(self.refresh_image_list)
        self.image_window.show()
        self.image_window.raise_()
        self.image_window.activateWindow()


    def open_image(self, item):
        image = os.path.join("images", item.text())

        if self.image_window is None or not self.image_window.isVisible():
            self.image_window = ImageWindow(image)
            self.image_window.file_changed.connect(self.refresh_image_list)
        self.image_window.show()
        self.image_window.raise_()
        self.image_window.activateWindow()

    
    def refresh_image_list(self):
        self.saved_images.clear()
        self.saved_images.addItems([f for f in os.listdir("images") if f != ".gitkeep"])
        print("Image list refreshed")


    def build_image_list(self):
        layout = QVBoxLayout()

        #title = QLabel("Images")
        #title.setStyleSheet("font-size: 14px; font-style: bold;")

        self.saved_images = QListWidget()
        self.saved_images.addItems([f for f in os.listdir("images") if f != ".gitkeep"])


        self.saved_images.itemDoubleClicked.connect(self.open_image)

        back_btn = QPushButton("Back")
        back_btn.clicked.connect(lambda: self.stack.setCurrentWidget(self.prompt_page))

        #layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.saved_images)
        layout.addWidget(back_btn, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.image_repo.setLayout(layout)


class ImageWindow(QMainWindow):

    file_changed = Signal()

    def __init__(self, image):
        super().__init__()

        self.image = image
        
        self.stack = QStackedWidget()
        self.image_page = QWidget()

        tool_bar = QToolBar()
        tool_bar.setMovable(False)
        self.addToolBar(tool_bar)

        download_image = QAction("Download Image", self)
        download_image.triggered.connect(self.download_file)
        tool_bar.addAction(download_image)

        edit_file_name = QAction("Change Filename", self)
        edit_file_name.triggered.connect(self.edit_file_name)
        tool_bar.addAction(edit_file_name)

        delete_image = QAction("Delete Image", self)
        delete_image.triggered.connect(self.delete_image)
        tool_bar.addAction(delete_image)

        self.build_image_page()

        self.stack.addWidget(self.image_page)
        self.setCentralWidget(self.stack)


    def build_image_page(self):
        layout = QVBoxLayout()
        image_label = QLabel()

        print("Opening File:", self.image)

        gen_image = QPixmap(self.image)
        screen = QGuiApplication.primaryScreen()
        ratio = screen.devicePixelRatio()
        gen_image.setDevicePixelRatio(ratio)

        logical_size = gen_image.size() / ratio
        self.setFixedSize(logical_size)

        image_label.setPixmap(gen_image)
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image_label.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(image_label)
        layout.setContentsMargins(0, 0, 0, 0)
        self.image_page.setLayout(layout)


    def download_file(self):
        dst, _ = QFileDialog.getSaveFileName(
            self,
            "Save Image As…",
            "",
            "PNG Files (*.png);;JPEG Files (*.jpg);;All Files (*)"
        )
        if dst:
            shutil.copy(self.image, dst)
            self.statusBar().showMessage(f"Saved to {dst}", 3000)

    def edit_file_name(self):
        # prompt for a name only
        name, ok = QInputDialog.getText(self, "File Name", "Enter filename:")
        if not ok or not name.strip():
            return

        try:
            os.rename(self.image, f"images/{name.strip()}.png")
            self.file_changed.emit()

        except OSError as e:
            self.statusBar().showMessage(f"Rename failed: {e}", 5000)
            return


    def delete_image(self):        
        if DeleteDialogueBox(self.image, self).exec() == QDialog.Accepted:
            try:
                os.remove(self.image)
                print(f"{os.path.basename(self.image)} Deleted")
                self.file_changed.emit()
                self.close()

            except OSError as e:
                self.statusBar().showMessage(f"Deletion failed: {e}", 5000)
        else:
            return

class DialogueBox(QDialog):
    def __init__(self, dialogue, parent):
        super().__init__(parent)

        self.setFixedSize(200, 100)

        QBtn = QDialogButtonBox.Ok

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        layout = QVBoxLayout()
        message = QLabel(f"{dialogue}")
        layout.addWidget(message, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.buttonBox, alignment=Qt.AlignmentFlag.AlignHCenter)
        self.setLayout(layout)


class DeleteDialogueBox(QDialog):
    def __init__(self, image, parent):
        super().__init__(parent)

        image_name = os.path.basename(image)

        self.setFixedHeight(100)
        self.setWindowTitle("Delete File")
        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        layout = QVBoxLayout()
        message = QLabel(f"Are you sure you want to delete '{os.path.splitext(image_name)[0]}'?")
        layout.addWidget(message, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.buttonBox, alignment=Qt.AlignmentFlag.AlignHCenter)
        self.setLayout(layout)

        self.adjustSize()

        self.setFixedWidth(self.width())


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setApplicationName("Image Gen")
    app.setWindowIcon(QIcon("icon.icns"))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())