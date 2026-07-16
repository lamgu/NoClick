from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QDoubleSpinBox, QSlider, QComboBox, 
                             QPushButton, QGroupBox, QFormLayout, QKeySequenceEdit)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QFont, QPixmap

class ControlPanel(QMainWindow):
    config_saved = Signal(dict)
    engine_started = Signal()
    engine_stopped = Signal()
    preview_toggled = Signal(bool) # Signal baru untuk memberi tahu thread kamera

    def __init__(self, current_config: dict):
        super().__init__()
        self.setWindowTitle("Gesture Presenter - Control Panel")
        self.setMinimumWidth(450)
        self.current_config = current_config
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setSpacing(15)

        title = QLabel("Gesture Presenter Configuration")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(title)

        # --- GROUP 1: GESTURE CALIBRATION ---
        calibration_group = QGroupBox("Gesture Calibration")
        calibration_layout = QFormLayout()

        self.hold_input = QDoubleSpinBox()
        self.hold_input.setRange(0.2, 5.0)
        self.hold_input.setSingleStep(0.1)
        self.hold_input.setSuffix(" sec")
        self.hold_input.setValue(self.current_config.get('activation_hold_duration', 1.5))
        calibration_layout.addRow("Palm Hold Duration:", self.hold_input)

        self.swipe_slider = QSlider(Qt.Horizontal)
        self.swipe_slider.setRange(5, 40)
        self.swipe_slider.setValue(int(self.current_config.get('swipe_distance', 0.15) * 100))
        self.swipe_label = QLabel(f"{self.swipe_slider.value()}%")
        self.swipe_slider.valueChanged.connect(lambda v: self.swipe_label.setText(f"{v}%"))
        
        swipe_container = QHBoxLayout()
        swipe_container.addWidget(self.swipe_slider)
        swipe_container.addWidget(self.swipe_label)
        calibration_layout.addRow("Swipe Distance Threshold:", swipe_container)

        self.cooldown_input = QDoubleSpinBox()
        self.cooldown_input.setRange(0.5, 4.0)
        self.cooldown_input.setSuffix(" sec")
        self.cooldown_input.setValue(self.current_config.get('cooldown_duration', 1.0))
        calibration_layout.addRow("Action Cooldown:", self.cooldown_input)

        calibration_group.setLayout(calibration_layout)
        self.main_layout.addWidget(calibration_group)

        # --- GROUP 2: SYSTEM & HARDWARE ---
        system_group = QGroupBox("System & Hardware")
        system_layout = QFormLayout()

        self.cam_combo = QComboBox()
        self.cam_combo.addItems(["Camera 0 (Default/Built-in)", "Camera 1 (External USB)", "Camera 2"])
        self.cam_combo.setCurrentIndex(self.current_config.get('camera_index', 0))
        system_layout.addRow("Select Camera:", self.cam_combo)

        self.hotkey_edit = QKeySequenceEdit(QKeySequence(self.current_config.get('hotkey', 'F8')))
        system_layout.addRow("Toggle Hotkey:", self.hotkey_edit)

        system_group.setLayout(system_layout)
        self.main_layout.addWidget(system_group)

        # --- EMBEDDED CAMERA PREVIEW BOX ---
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("background-color: #1e272e; border: 2px solid #2f3542; border-radius: 6px;")
        self.preview_label.setFixedHeight(280)
        self.preview_label.hide() # Tersembunyi rapi saat start awal
        self.main_layout.addWidget(self.preview_label)

        # --- ACTION BUTTONS ---
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("START ENGINE")
        self.start_btn.setFixedHeight(40)
        self.start_btn.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; border-radius: 4px;")
        self.start_btn.clicked.connect(self.emit_start)

        self.stop_btn = QPushButton("STOP ENGINE")
        self.stop_btn.setFixedHeight(40)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("background-color: #c0392b; color: white; font-weight: bold; border-radius: 4px;")
        self.stop_btn.clicked.connect(self.emit_stop)

        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
        self.main_layout.addLayout(btn_layout)

        # Tombol Khusus Kendali Preview Tangan
        self.preview_btn = QPushButton("SHOW CAMERA PREVIEW")
        self.preview_btn.setFixedHeight(35)
        self.preview_btn.setEnabled(False) 
        self.preview_btn.setStyleSheet("background-color: #2f3542; color: #a4b0be; font-weight: bold; border-radius: 4px;")
        self.preview_btn.clicked.connect(self.toggle_preview_view)
        self.main_layout.addWidget(self.preview_btn)

        self.preview_active = False

    def toggle_preview_view(self):
        self.preview_active = not self.preview_active
        if self.preview_active:
            self.preview_label.show()
            self.preview_btn.setText("HIDE CAMERA PREVIEW")
            self.preview_btn.setStyleSheet("background-color: #d35400; color: white; font-weight: bold; border-radius: 4px;")
        else:
            self.preview_label.hide()
            self.preview_btn.setText("SHOW CAMERA PREVIEW")
            self.preview_btn.setStyleSheet("background-color: #2f3542; color: white; font-weight: bold; border-radius: 4px;")
            self.preview_label.clear()
        
        self.preview_toggled.emit(self.preview_active)

    def update_preview_frame(self, q_img):
        """Menerima kiriman QImage dari thread kamera dan memasangnya ke label preview"""
        if self.preview_active and not q_img.isNull():
            pixmap = QPixmap.fromImage(q_img)
            # Scaling responsif menjaga aspect ratio agar tidak lonjong/gepeng
            scaled = pixmap.scaled(self.preview_label.width(), self.preview_label.height(), 
                                   Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.preview_label.setPixmap(scaled)

    def get_latest_settings(self) -> dict:
        return {
            "activation_hold_duration": self.hold_input.value(),
            "swipe_distance": self.swipe_slider.value() / 100.0,
            "cooldown_duration": self.cooldown_input.value(),
            "camera_index": self.cam_combo.currentIndex(),
            "hotkey": self.hotkey_edit.keySequence().toString()
        }

    def emit_start(self):
        self.config_saved.emit(self.get_latest_settings())
        self.engine_started.emit()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.preview_btn.setEnabled(True)
        self.preview_btn.setStyleSheet("background-color: #2f3542; color: white; font-weight: bold; border-radius: 4px;")
        
        self.hold_input.setEnabled(False)
        self.swipe_slider.setEnabled(False)
        self.cooldown_input.setEnabled(False)
        self.cam_combo.setEnabled(False)
        self.hotkey_edit.setEnabled(False)

    def emit_stop(self):
        if self.preview_active:
            self.toggle_preview_view()
        self.engine_stopped.emit()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.preview_btn.setEnabled(False)
        self.preview_btn.setStyleSheet("background-color: #2f3542; color: #a4b0be; font-weight: bold; border-radius: 4px;")
        
        self.hold_input.setEnabled(True)
        self.swipe_slider.setEnabled(True)
        self.cooldown_input.setEnabled(True)
        self.cam_combo.setEnabled(True)
        self.hotkey_edit.setEnabled(True)