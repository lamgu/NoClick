import time
from PySide6.QtCore import QObject, Signal

class GestureEngine(QObject):
    gesture_detected = Signal(str)
    status_changed = Signal(str)   
    # SIGNAL BARU: Mengirim nilai desimal (-1.0 sampai 1.0) untuk posisi ikon tangan
    swipe_progress = Signal(float) 

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.enabled = False  
        
        self.is_active = False
        self.palm_detect_start_time = 0
        self.last_action_time = 0
        
        self.prev_x = None
        self.tab_switching_active = False
        self.fist_start_x = None

    def toggle_enabled(self, state: bool):
        self.enabled = state
        self.is_active = False
        self.tab_switching_active = False
        self.fist_start_x = None
        if not state:
            self.palm_detect_start_time = 0
            self.swipe_progress.emit(0.0) # Reset ke tengah
        self.status_changed.emit("ENABLED" if state else "DISABLED")

    def _check_fist(self, landmarks) -> bool:
        tips = [8, 12, 16, 20]
        pips = [6, 10, 14, 18]
        folded_count = 0
        for tip, pip in zip(tips, pips):
            if landmarks[tip][1] > landmarks[pip][1]:
                folded_count += 1
        return folded_count == 4

    def process_landmarks(self, landmarks):
        if not self.enabled:
            if not landmarks:
                if self.tab_switching_active:
                    self.tab_switching_active = False
                    self.gesture_detected.emit("TAB_SWITCH_END")
                    self.status_changed.emit("DISABLED")
                return

            is_fist = self._check_fist(landmarks)
            wrist_x = landmarks[0][0]

            if not self.tab_switching_active:
                if is_fist:
                    self.tab_switching_active = True
                    self.fist_start_x = wrist_x
                    self.gesture_detected.emit("TAB_SWITCH_START")
                    self.status_changed.emit("TAB_SWITCH_ACTIVE")
            else:
                if is_fist:
                    swipe_dist = wrist_x - self.fist_start_x
                    threshold = self.config.get('tab_swipe_distance', 0.06)
                    
                    if swipe_dist > threshold:
                        self.gesture_detected.emit("TAB_SWITCH_RIGHT")
                        self.fist_start_x = wrist_x
                    elif swipe_dist < -threshold:
                        self.gesture_detected.emit("TAB_SWITCH_LEFT")
                        self.fist_start_x = wrist_x
                else:
                    self.tab_switching_active = False
                    self.gesture_detected.emit("TAB_SWITCH_END")
                    self.status_changed.emit("DISABLED")
            return
            
        if not landmarks:
            # Jika tangan tiba-tiba keluar dari frame, reset progres ke tengah
            self.swipe_progress.emit(0.0)
            return

        current_time = time.time()
        cooldown_dur = self.config.get('cooldown_duration', 1.0)
        
        # Logika Cooldown
        elapsed_cooldown = current_time - self.last_action_time
        if elapsed_cooldown < cooldown_dur:
            self.status_changed.emit("COOLDOWN")
            remaining_cooldown = max(0.0, cooldown_dur - elapsed_cooldown)
            self.gesture_detected.emit(f"Wait: {remaining_cooldown:.1f}s")
            self.swipe_progress.emit(0.0)
            return

        is_open_palm = self._check_open_palm(landmarks)
        wrist_x = landmarks[0][0] 

        if not self.is_active:
            self.swipe_progress.emit(0.0) # Belum aktif, ikon tetap di tengah
            
            if is_open_palm:
                if self.palm_detect_start_time == 0:
                    self.palm_detect_start_time = current_time
                
                elapsed_hold = current_time - self.palm_detect_start_time
                hold_dur = self.config.get('activation_hold_duration', 1.5)
                
                if elapsed_hold >= hold_dur:
                    self.is_active = True
                    self.prev_x = wrist_x # Mengunci posisi awal pergelangan tangan
                    self.status_changed.emit("ACTIVE")
                    self.gesture_detected.emit("READY TO SWIPE!")
                else:
                    self.status_changed.emit("HOLDING")
                    remaining_hold = max(0.0, hold_dur - elapsed_hold)
                    self.gesture_detected.emit(f"Hold: {remaining_hold:.1f}s")
            else:
                self.palm_detect_start_time = 0
                self.status_changed.emit("WAITING PALM")
                self.gesture_detected.emit("---")
        else:
            # MODE ACTIVE: Menghitung pergerakan tangan secara dinamis
            if self.prev_x is not None:
                swipe_dist = wrist_x - self.prev_x
                threshold = self.config.get('swipe_distance', 0.15)
                
                # Hitung rasio progres pergerakan (-1.0 sampai 1.0)
                progress = swipe_dist / threshold
                # Batasi (clamp) agar nilai tidak melompat melebihi batas -1.0 dan 1.0
                progress = max(-1.0, min(1.0, progress))
                
                # Kirim data pergerakan ke overlay untuk menggeser ikon tangan
                self.swipe_progress.emit(progress)
                
                # Trigger perpindahan jika melewati batas threshold (100% progress)
                if swipe_dist > threshold:
                    self._trigger_action("NEXT SLIDE")
                elif swipe_dist < -threshold:
                    self._trigger_action("PREVIOUS SLIDE")

    def _trigger_action(self, action_name):
        self.gesture_detected.emit(action_name)
        self.swipe_progress.emit(0.0) # Reset ikon ke tengah setelah swipe sukses
        self.last_action_time = time.time()
        self.is_active = False
        self.palm_detect_start_time = 0
        self.prev_x = None

    def _check_open_palm(self, landmarks) -> bool:
        tips = [8, 12, 16, 20]
        pips = [6, 10, 14, 18]
        for tip, pip in zip(tips, pips):
            if landmarks[tip][1] > landmarks[pip][1]: 
                return False
        return True