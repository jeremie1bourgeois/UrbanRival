class Round:
    
    class Ally:
        def __init__(self):
            self.card = None
            self.win = False
    
    class Enemy:
        def __init__(self):
            self.card = None
            self.win = False

    def __init__(self):
        self.ally: self.Ally = self.Ally()
        self.enemy: self.Enemy = self.Enemy()
