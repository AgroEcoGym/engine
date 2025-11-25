
class Plot:
    def __init__(self, field, position, type="base"):
        self.field = field
        self.position = position  # x,y
        assert type in ["base", "edge"]
        self.type = type

    def __str__(self):
        return "'" + str(self.position) + ":" + self.type + "'"