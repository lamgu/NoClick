import cv2
import mediapipe as mp
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage
import time

class CameraThread(QThread):
    frame_ready = Signal(QImage)
    landmarks_ready = Signal(list)
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.running = False
        self.show_preview = False  # Flag untuk mengaktifkan/menonaktifkan gambar kerangka
        
        # Inisialisasi MediaPipe Hands & Drawing Utils
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.hands = self.mp_hands.Hands(
            min_detection_confidence=self.config.get('min_detection_confidence', 0.7),
            min_tracking_confidence=self.config.get('min_tracking_confidence', 0.5)
        )

    def run(self):
        self.running = True
        cap = cv2.VideoCapture(self.config.get('camera_index', 0))
        
        while self.running and cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                continue

            frame = cv2.flip(frame, 1)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            results = self.hands.process(rgb_frame)
            landmarks_data = []
            
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    # Ambil koordinat mentah untuk diproses oleh Gesture Engine
                    landmarks_data = [(lm.x, lm.y) for lm in hand_landmarks.landmark]
                    
                    # JIKA preview diaktifkan, gambar objek kerangka tangan di atas frame
                    if self.show_preview:
                        self.mp_drawing.draw_landmarks(
                            rgb_frame, 
                            hand_landmarks, 
                            self.mp_hands.HAND_CONNECTIONS,
                            self.mp_drawing.DrawingSpec(color=(0, 255, 204), thickness=2, circle_radius=2), # Titik
                            self.mp_drawing.DrawingSpec(color=(241, 196, 15), thickness=2) # Garis penghubung
                        )
                    break 
            
            self.landmarks_ready.emit(landmarks_data)
            
            # Konversi frame hasil olahan (termasuk kerangka jika aktif) ke QImage
            h, w, ch = rgb_frame.shape
            bytes_per_line = ch * w
            q_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
            self.frame_ready.emit(q_img)
            
            time.sleep(0.03) # Batasi kisaran ~30 FPS agar CPU ringan

        cap.release()

    def stop(self):
        self.running = False
        self.wait()