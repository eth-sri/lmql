class _Interrupt:
    def __init__(self):
        self.interrupt = 0

    def set(self):
        self.interrupt = 1

    def clear(self):
        self.interrupt = 0
    
    def check(self):
        return self.interrupt
    
interrupt = _Interrupt()