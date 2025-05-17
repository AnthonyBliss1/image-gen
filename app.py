import os
import sys
import shutil
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
import base64
from PySide6.QtCore import Qt, Signal, QEvent, QDir, QObject, QRunnable, QThreadPool, Slot, QTimer
from PySide6.QtGui import QPixmap, QGuiApplication, QAction, QIcon, QPainter, QColor
from PySide6.QtWidgets import (
    QMainWindow, QApplication, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, QFileDialog, QDialog,
    QStackedWidget, QWidget, QSpacerItem, QSizePolicy, QListWidget, QToolBar, QDialogButtonBox
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
        self.is_image_added = False

        self.stack = QStackedWidget()

        self.prompt_page = QWidget()
        self.prompt_page.installEventFilter(self)
        
        self.image_repo = QWidget()

        self.build_image_gen()
        self.build_image_list()
        self.build_spinner_overlay()

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
        if obj in (self.prompt_input, self.prompt_page) and event.type() == QEvent.KeyPress:
            key_event = event

            if key_event.key() == Qt.Key_F2 and self.upload_btn.isHidden() == False:
                #print("F2 pressed! Hiding upload button")
                self.reset_upload_btn()
                self.is_image_added = False
                self.upload_btn.hide()
                self.prompt_input.setFixedWidth(350)
                self.hbox.update()
                return True
            
            elif key_event.key() == Qt.Key_F2 and self.upload_btn.isHidden() == True:
                #print("F2 pressed! Unhidding upload button")
                self.is_image_added = True
                self.upload_btn.show()
                self.prompt_input.setFixedWidth(300)
                self.hbox.update()
                return True

        elif obj is self.prompt_page and event.type() in (QEvent.Resize, QEvent.Move):
            self.spinner_overlay.setGeometry(0, 0, self.prompt_page.width(), self.prompt_page.height())

        return super().eventFilter(obj, event)
    

    def reset_upload_btn(self):
        self.upload_btn.hide()
        self.prompt_input.setFixedWidth(350)
        self.hbox.update()
        self.uploaded_file = None
        self.upload_btn.setText("Add File")
        self.upload_btn.setEnabled(True)
        self.setStyleSheet("")
        self.upload_btn.setProperty("styleSheet", None)
        self.upload_btn.style().unpolish(self.upload_btn)
        self.upload_btn.style().polish(self.upload_btn)
        self.upload_btn.update()


    def upload_file(self):
        start_dir = QDir.homePath()
        self.uploaded_file, _ = QFileDialog.getOpenFileName(self, "Select an image…", start_dir, "Image Files (*.png *.jpg *.jpeg)")
        if self.uploaded_file:
            self.upload_btn.setEnabled(False)
            self.upload_btn.setStyleSheet("background-color: green;")
            self.upload_btn.setText("Added!")


    def on_generate_press(self):
        prompt = self.prompt_input.text()

        if prompt: 

            print(f"Prompt: {prompt}")

            self.prompt_input.setReadOnly(True)
            self.spinner_overlay.show()

            runnable = Worker(
            prompt = prompt,
            image_path = getattr(self, 'uploaded_file', None),
            is_image_added = self.is_image_added,
            client = client
            )

            runnable.signals.finished.connect(self.on_image_generated)
            runnable.signals.error.connect(self.on_generation_error)

            QThreadPool.globalInstance().start(runnable)

        else:
            msg = "Please enter a prompt"
            dlg = DialogueBox(msg, self)
            dlg.exec()


    @Slot(str)
    def on_image_generated(self, today):
        self.reset_upload_btn()
        self.prompt_input.clear()
        self.prompt_input.setReadOnly(False)
        self.spinner_overlay.hide()
        self.open_image(today)
        self.refresh_image_list()

    @Slot(Exception)
    def on_generation_error(self, ex):
        self.spinner_overlay.hide()
        print("Error:", ex)
        DialogueBox(f"Error generating image:\n{ex}", self).exec()


    def open_image(self, item):
        if type(item) is not str:
            image = os.path.join("images", f"{item.text()}.png")

        else:
            image = os.path.join("images", f"{item}.png")

        if self.image_window is None or not self.image_window.isVisible():
            self.image_window = ImageWindow(image)

        elif self.image_window.isVisible():
            self.image_window.close()
            self.image_window = ImageWindow(image)

        self.image_window.file_changed.connect(self.refresh_image_list)
        self.image_window.show()
        self.image_window.raise_()
        self.image_window.activateWindow()

    
    def refresh_image_list(self):
        self.saved_images.clear()

        items = [
        os.path.splitext(f)[0]
        for f in os.listdir("images") if f != ".gitkeep"
        ]

        self.saved_images.addItems(items)
        self.saved_images.sortItems()
        #print("Image list refreshed")


    def build_image_list(self):
        layout = QVBoxLayout()

        #title = QLabel("Images")
        #title.setStyleSheet("font-size: 14px; font-style: bold;")

        self.saved_images = QListWidget()

        items = [
        os.path.splitext(f)[0]
        for f in os.listdir("images") if f != ".gitkeep"
        ]

        self.saved_images.addItems(items)
        self.saved_images.sortItems()
        self.saved_images.itemDoubleClicked.connect(self.open_image)

        back_btn = QPushButton("Back")
        back_btn.clicked.connect(lambda: self.stack.setCurrentWidget(self.prompt_page))

        #layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.saved_images)
        layout.addWidget(back_btn, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.image_repo.setLayout(layout)


    def closeEvent(self, event):
        if self.image_window is not None:
            self.image_window.close()
            
        return super().closeEvent(event)


    def build_spinner_overlay(self):
        self.spinner_overlay = QWidget(self.prompt_page)
        self.spinner_overlay.setAttribute(Qt.WA_StyledBackground, True)
        self.spinner_overlay.setStyleSheet("background: rgba(255,255,255,200);")

        self.prompt_page.installEventFilter(self)

        layout = QVBoxLayout(self.spinner_overlay)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.spinner = CustomSpinner(self.spinner_overlay)
        layout.addWidget(self.spinner)

        self.spinner_overlay.setLayout(layout)

        self.spinner_overlay.hide()


class WorkerSignals(QObject):
    finished = Signal(str)
    error = Signal(Exception)


class Worker(QRunnable):
    def __init__(self, prompt, image_path, is_image_added, client):
        super().__init__()
        
        self.signals = WorkerSignals()
        self.prompt = prompt
        self.image_path = image_path
        self.is_image_added = is_image_added
        self.client = client
    
    def run(self):

        today = datetime.now().strftime("%m.%d.%y_%H:%M")
        file_name = os.path.join("images", today)

        try:
            if self.is_image_added and self.image_path is not None: 
                print(f"Submitting prompt with {os.path.splitext(os.path.basename(self.image_path))[0]}")
                result = client.images.edit(
                    model="gpt-image-1",
                    image=open(self.image_path, "rb"),
                    prompt=self.prompt
                )

            else:
                print("Submitting prompt with no image")
                result = client.images.generate(
                    model="gpt-image-1",
                    prompt=self.prompt
                )
        
            image_base64 = result.data[0].b64_json
            image_bytes = base64.b64decode(image_base64)

            with open(f"{file_name}.png", "wb") as f:
                f.write(image_bytes)
            
            self.signals.finished.emit(today)

        except Exception as e:
            self.signals.error.emit(e)


class ImageWindow(QMainWindow):

    file_changed = Signal()

    def __init__(self, image):
        super().__init__()

        self.image = image

        self.is_image_added = True
        
        self.stack = QStackedWidget()
        self.image_page = QWidget()

        tool_bar = QToolBar()
        tool_bar.setMovable(False)
        self.addToolBar(tool_bar)

        export_image = QAction("Export Image", self)
        export_image.triggered.connect(self.export_file)
        tool_bar.addAction(export_image)

        edit_file_name = QAction("Change Filename", self)
        edit_file_name.triggered.connect(self.edit_file_name)
        tool_bar.addAction(edit_file_name)

        delete_image = QAction("Delete Image", self)
        delete_image.triggered.connect(self.delete_image)
        tool_bar.addAction(delete_image)

        edit_image = QAction("Edit Image", self)
        edit_image.triggered.connect(self.edit_image)
        tool_bar.addAction(edit_image)

        self.build_image_page()
        self.build_spinner_overlay()

        self.stack.addWidget(self.image_page)
        self.setCentralWidget(self.stack)


    def build_image_page(self):
        layout = QVBoxLayout()
        image_label = QLabel()

        #print("Opening File:", self.image)

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


    def build_spinner_overlay(self):
        self.spinner_overlay = QWidget(self.image_page)
        self.spinner_overlay.setAttribute(Qt.WA_StyledBackground, True)
        self.spinner_overlay.setStyleSheet("background: rgba(255,255,255,200);")

        self.image_page.installEventFilter(self)

        layout = QVBoxLayout(self.spinner_overlay)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.spinner = CustomSpinner(self.spinner_overlay)
        layout.addWidget(self.spinner)

        self.spinner_overlay.setLayout(layout)

        self.spinner_overlay.hide()


    def eventFilter(self, obj, event):
        if obj is self.image_page and event.type() in (QEvent.Resize, QEvent.Move):
            self.spinner_overlay.setGeometry(0, 0, self.image_page.width(), self.image_page.height())

        return super().eventFilter(obj, event)


    def export_file(self):
        start_dir = QDir.homePath()
        dst, _ = QFileDialog.getSaveFileName(self, "Save Image As…", start_dir, "PNG Files (*.png)")
        if dst:
            shutil.copy(self.image, dst)
            self.statusBar().showMessage(f"Saved to {dst}", 3000)

    def edit_file_name(self):
        dlg = InputDialog("Change Filename", f"{os.path.splitext(os.path.basename(self.image))[0]}", self)
        dlg.setFixedWidth(300)
        dlg.user_input.setFixedWidth(250)
        result = dlg.exec()

        name = dlg.user_input.text().strip()

        if result != QDialog.Accepted or not name:
            return

        try:
            base_name = name.strip()
            full_name = f"images/{base_name}.png"
            
            os.rename(self.image, full_name)
            self.file_changed.emit()
            window.update()
            self.close()
            MainWindow.open_image(window, base_name)

        except OSError as e:
            self.statusBar().showMessage(f"Rename failed: {e}", 5000)
            return

    def delete_image(self):        
        if DeleteDialogBox(self.image, self).exec() == QDialog.Accepted:
            try:
                os.remove(self.image)
                print(f"{os.path.basename(self.image)} Deleted")
                self.file_changed.emit()
                window.update()
                self.close()

            except OSError as e:
                self.statusBar().showMessage(f"Deletion failed: {e}", 5000)
        else:
            return
        
    def edit_image(self):
        while True:
            dlg = InputDialog("Edit Image", "Enter Prompt to Edit Image", self)
            result = dlg.exec()

            if result != QDialog.Accepted:
                return

            prompt = dlg.user_input.text().strip()

            if prompt:
                break

            msg = "Please enter a prompt"
            dlg = DialogueBox(msg, self)
            dlg.exec()

        try:
            print(f"Prompt: {prompt}")

            self.spinner_overlay.show()

            runnable = Worker(
            prompt = prompt,
            image_path = self.image,
            is_image_added = self.is_image_added,
            client = client
            )

            runnable.signals.finished.connect(self.on_image_generated)
            runnable.signals.error.connect(self.on_generation_error)

            QThreadPool.globalInstance().start(runnable)

        except OSError as e:
            self.statusBar().showMessage(f"Edit failed: {e}", 5000)
            return
        
    @Slot(str)
    def on_image_generated(self, today):
        self.spinner_overlay.hide()
        self.file_changed.emit()
        window.update()
        self.close()
        MainWindow.open_image(window, today)

    @Slot(Exception)
    def on_generation_error(self, ex):
        self.spinner_overlay.hide()
        print("Error:", ex)
        DialogueBox(f"Error generating image:\n{ex}", self).exec()


class DialogueBox(QDialog):
    def __init__(self, dialogue, parent):
        super().__init__(parent)

        self.setFixedSize(200, 85)

        QBtn = QDialogButtonBox.Ok

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        layout = QVBoxLayout()
        message = QLabel(f"{dialogue}")
        layout.addWidget(message, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.buttonBox, alignment=Qt.AlignmentFlag.AlignHCenter)
        self.setLayout(layout)


class DeleteDialogBox(QDialog):
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


class InputDialog(QDialog):
    def __init__(self, title, placeholder_input, parent):
        super().__init__(parent)

        self.setFixedSize(400, 100)
        self.setWindowTitle(f"{title}")
        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        layout = QVBoxLayout()
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText(f"{placeholder_input}")
        self.user_input.setFixedWidth(350)
        
        layout.addWidget(self.user_input, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.buttonBox, alignment=Qt.AlignmentFlag.AlignHCenter)
        self.setLayout(layout)


class CustomSpinner(QWidget):
    def __init__(self, parent=None, line_count=10, line_length=10, line_width=10, radius=20, interval=80):
        super().__init__(parent)
        self._angle = 0
        self.line_count = line_count
        self.line_length = line_length
        self.line_width = line_width
        self.radius = radius

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._rotate)
        self._timer.start(interval)

        diameter = (radius + line_length) * 2
        self.setFixedSize(diameter, diameter)

    def _rotate(self):
        self._angle = (self._angle + (360 / self.line_count)) % 360
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.translate(self.width()/2, self.height()/2)
        painter.rotate(self._angle)

        for i in range(self.line_count):
            color = QColor(0, 0, 0) 
            color.setAlphaF((i + 1) / self.line_count)
            painter.setPen(Qt.NoPen)
            painter.setBrush(color)
            painter.drawRoundedRect(self.radius, -self.line_width/2, self.line_length, self.line_width, self.line_width/2, self.line_width/2)
            painter.rotate(360 / self.line_count)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setApplicationName("Image Gen")
    app.setWindowIcon(QIcon("icon.icns"))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())