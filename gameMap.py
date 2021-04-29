import tile


class GameMap:
    def __init__(self, mapwidth, mapheight):
        self.width = mapwidth
        self.height = mapheight
        self.tiles = self.initialize_tiles()

    def initialize_tiles(self):
        tiles = [[tile.Tile(True) for _ in range(self.height)] for _ in range(self.width)]

        return tiles
