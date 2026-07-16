from pynput.keyboard import Controller, Key

class KeyboardController:
    def __init__(self):
        self.keyboard = Controller()

    def press_right(self):
        self.keyboard.press(Key.right)
        self.keyboard.release(Key.right)

    def press_left(self):
        self.keyboard.press(Key.left)
        self.keyboard.release(Key.left)

    def press_win_tab(self):
        with self.keyboard.pressed(Key.cmd):
            self.keyboard.press(Key.tab)
            self.keyboard.release(Key.tab)

    def press_enter(self):
        self.keyboard.press(Key.enter)
        self.keyboard.release(Key.enter)