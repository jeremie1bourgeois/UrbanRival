
class Capacity:
    def __init__(self, target, type, value, how, borne):
        self.target = target
        self.type = type
        self.value = value
        self.how = how
        self.borne = borne
        self.condition_effect = None
        self.lvl_priority = 0
