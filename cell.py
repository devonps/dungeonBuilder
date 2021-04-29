
class Cell:
    def __init__(self, template_id):
        self.grid_posx = 0
        self.grid_posy = 0
        self.startx = 0
        self.starty = 0
        self.width = 0
        self.height = 0
        self.template_id = template_id
        self.room_id = -1
        self.available_exits = '0000'
