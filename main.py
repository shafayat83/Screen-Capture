import sys
import os
import time
import cv2
import mss
import numpy as np
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QFrame, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QPoint
from PyQt6.QtGui import QColor

# --- CONFIGURATION & PATHS ---
VIDEO_PATH = r"C:\Users\shafa\Videos\Screen Recorder"
IMAGE_PATH = r"C:\Users\shafa\OneDrive\Pictures\screenshort"

# Ensure directories exist
os.makedirs(VIDEO_PATH, exist_ok=True)
os.makedirs(IMAGE_PATH, exist_ok=True)


class RecorderWorker(QThread):
    update_time = pyqtSignal(str)
    finished = pyqtSignal(str)

    def __init__(self, fps=24.0):
        super().__init__()
        self.fps = fps
        self.running = False
        self.paused = False

    def run(self):
        with mss.mss() as sct:
            # Get primary monitor metrics
            monitor = sct.monitors[1]
            width = monitor["width"]
            height = monitor["height"]

            # Setup Video File Path
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"Recording_{timestamp}.mp4"
            full_path = os.path.join(VIDEO_PATH, filename)

            # Codec and Writer
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(full_path, fourcc, self.fps, (width, height))

            start_time = time.time()
            pause_offset = 0

            while self.running:
                loop_start = time.time()

                if not self.paused:
                    # Capture and Process Frame
                    img = sct.grab(monitor)
                    frame = np.array(img)
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)  # Convert for MP4

                    # Safety check for resolution consistency
                    if frame.shape[1] != width or frame.shape[0] != height:
                        frame = cv2.resize(frame, (width, height))

                    out.write(frame)

                    # Update UI Timer
                    current_elapsed = (time.time() - start_time) - pause_offset
                    self.update_time.emit(self.format_time(current_elapsed))
                else:
                    # Keep track of time spent while paused
                    pause_offset += (time.time() - loop_start)

                # Precision FPS Control
                elapsed = time.time() - loop_start
                wait_time = max(1 / self.fps - elapsed, 0)
                time.sleep(wait_time)

            out.release()
            self.finished.emit(full_path)

    def format_time(self, seconds):
        mins, secs = divmod(int(seconds), 60)
        return f"{mins:02d}:{secs:02d}"

    def stop(self):
        self.running = False


# --- UI COMPONENTS ---

class GlassButton(QPushButton):
    def __init__(self, text, color="#3498db"):
        super().__init__(text)
        self.setFixedSize(100, 45)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(255, 255, 255, 15);
                border: 1px solid rgba(255, 255, 255, 30);
                border-radius: 12px;
                color: white;
                font-weight: bold;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: {color};
                border: 1px solid white;
            }}
            QPushButton:disabled {{
                color: rgba(255,255,255,50);
                background-color: rgba(0,0,0,20);
            }}
        """)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)


class ModernRecorderUI(QWidget):
    def __init__(self):
        super().__init__()
        self.is_recording = False
        self.worker = None
        self.initUI()

    def initUI(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(480, 220)

        # Main Visual Container
        self.container = QFrame(self)
        self.container.setGeometry(10, 10, 460, 200)
        self.container.setStyleSheet("""
            QFrame {
                background-color: rgba(25, 25, 30, 230);
                border-radius: 30px;
                border: 1px solid rgba(255, 255, 255, 12);
            }
        """)

        layout = QVBoxLayout(self.container)

        # Header Area
        header = QHBoxLayout()
        title = QLabel("NEON ENGINE 3D")
        title.setStyleSheet("color: #555; font-weight: bold; font-size: 10px; letter-spacing: 4px;")
        header.addStretch()
        header.addWidget(title)

        close_btn = QPushButton("×")
        close_btn.setFixedSize(30, 30)
        close_btn.clicked.connect(self.close)
        close_btn.setStyleSheet("background: none; color: #555; font-size: 20px; border: none;")
        header.addWidget(close_btn)
        layout.addLayout(header)

        # Timer Display
        self.timer_label = QLabel("00:00")
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timer_label.setStyleSheet("color: white; font-size: 55px; font-weight: 200; margin-bottom: 5px;")
        layout.addWidget(self.timer_label)

        # Control Panel
        btns = QHBoxLayout()
        btns.setSpacing(15)

        self.btn_rec = GlassButton("START", "#e74c3c")
        self.btn_rec.clicked.connect(self.toggle_recording)

        self.btn_pause = GlassButton("PAUSE", "#f39c12")
        self.btn_pause.setEnabled(False)
        self.btn_pause.clicked.connect(self.toggle_pause)

        self.btn_shot = GlassButton("SHOT", "#2ecc71")
        self.btn_shot.clicked.connect(self.take_screenshot)

        btns.addWidget(self.btn_rec)
        btns.addWidget(self.btn_pause)
        btns.addWidget(self.btn_shot)
        layout.addLayout(btns)

        # Storage Indicator
        self.path_label = QLabel(f"Saving to: ...\\Videos\\Screen Recorder")
        self.path_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.path_label.setStyleSheet("color: #444; font-size: 9px;")
        layout.addWidget(self.path_label)

        self._drag_pos = QPoint()

    def toggle_recording(self):
        if not self.is_recording:
            # START RECORDING
            self.is_recording = True
            self.btn_rec.setText("STOP")
            self.btn_pause.setEnabled(True)
            self.timer_label.setStyleSheet("color: #e74c3c; font-size: 55px; font-weight: 200;")

            self.worker = RecorderWorker(fps=24.0)
            self.worker.update_time.connect(self.update_timer)
            self.worker.finished.connect(self.on_video_saved)
            self.worker.running = True
            self.worker.start()
        else:
            # STOP RECORDING
            self.is_recording = False
            self.btn_rec.setText("START")
            self.btn_pause.setEnabled(False)
            self.worker.stop()

    def toggle_pause(self):
        if self.worker:
            self.worker.paused = not self.worker.paused
            if self.worker.paused:
                self.btn_pause.setText("RESUME")
                self.timer_label.setStyleSheet("color: #f39c12; font-size: 55px; font-weight: 200;")
            else:
                self.btn_pause.setText("PAUSE")
                self.timer_label.setStyleSheet("color: #e74c3c; font-size: 55px; font-weight: 200;")

    def take_screenshot(self):
        with mss.mss() as sct:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"Shot_{timestamp}.png"
            full_path = os.path.join(IMAGE_PATH, filename)

            sct.shot(mon=-1, output=full_path)

            # Flash Feedback
            original_text = self.timer_label.text()
            self.timer_label.setText("SAVED")
            self.timer_label.setStyleSheet("color: #2ecc71; font-size: 55px;")
            QTimer.singleShot(1000, lambda: self.reset_label_style(original_text))

    def update_timer(self, val):
        self.timer_label.setText(val)

    def on_video_saved(self, path):
        self.timer_label.setText("FINISH")
        self.timer_label.setStyleSheet("color: #2ecc71; font-size: 45px;")
        print(f"Video recorded to: {path}")
        QTimer.singleShot(3000, lambda: self.reset_label_style("00:00"))

    def reset_label_style(self, text):
        self.timer_label.setText(text)
        color = "white" if not self.is_recording else "#e74c3c"
        self.timer_label.setStyleSheet(f"color: {color}; font-size: 55px; font-weight: 200;")

    # Window Movement Logic
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ModernRecorderUI()
    window.show()
    sys.exit(app.exec())
