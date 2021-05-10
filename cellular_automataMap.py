import sys
from math import sqrt
import random

from gameMap import GameMap
from metrics import Metrics, SheetColumns


class CellularAutomata:

    def __init__(self, map_width, map_height):
        self.game_map = GameMap(mapwidth=map_width, mapheight=map_height)
        self.current_floor_count = 0
        self.saved_build_seed = 0
        self.build_seed = self.generate_random_seed()
        self.unused_tiles = 0
        self.corridor_count = -1
        self.room_count = -1
        self.wall_count = 0
        self.current_floor_count = 0

        self.iterations = 30000
        self.neighbors = 4  # number of neighboring walls for this cell to become a wall
        # the initial probability of a cell becoming a wall, recommended to be between .35 and .55
        self.wall_probability = 0.47
        # size in total number of cells, not dimensions
        self.ROOM_MIN_SIZE = 16
        # size in total number of cells, not dimensions
        self.ROOM_MAX_SIZE = 500
        self.smooth_edges = False
        self.smoothing = 0
        self.caves = []

    def generate_random_seed(self):
        if self.saved_build_seed == 0:
            seed_value = random.randrange(sys.maxsize)
        else:
            seed_value = self.saved_build_seed
        return seed_value

    def generate_level(self):
        current_workbook, current_worksheet = Metrics.initialise()
        # store build id
        this_build_id = Metrics.update_build_id(worksheet=current_worksheet)
        this_sheet_row_id = Metrics.set_current_sheet_row_id(this_build_id=this_build_id)
        build_column = SheetColumns.build_id.value
        Metrics.update_worksheet(sheet=current_worksheet, row=this_sheet_row_id, column=build_column,
                                 value=this_build_id)
        #  store build seed
        build_seed_column = SheetColumns.build_seed.value
        Metrics.update_worksheet(sheet=current_worksheet, row=this_sheet_row_id, column=build_seed_column,
                                 value=self.build_seed)
        Metrics.set_build_seed_cell(sheet=current_worksheet, row=this_sheet_row_id, column=build_seed_column)

        # store start time for build
        time_start_string = Metrics.get_time_string()
        build_started_column = SheetColumns.build_started.value
        Metrics.update_worksheet(sheet=current_worksheet, row=this_sheet_row_id, column=build_started_column,
                                 value=time_start_string)
        Metrics.set_cell_to_time_format(sheet=current_worksheet, column=build_started_column, row=this_sheet_row_id)
        Metrics.save_workbook(workbook=current_workbook)

        # initialise new dungeon - everywhere is an obstacle/unused tile
        random.seed(self.build_seed)
        self.unused_tiles = self.game_map.width * self.game_map.height
        self.clear_map_to_floor()
        self.fill_map_with_walls()
        self.create_caves()
        self.get_caves()
        self.connect_caves()
        self.create_false_border_for_game_map()
        self.clean_up_map()
        self.metrics_count()

        # write out metrics for this dungeon build
        # capture time this build ended
        time_end_string = Metrics.get_time_string()
        build_ended_column = SheetColumns.build_ended.value
        Metrics.update_worksheet(sheet=current_worksheet, row=this_sheet_row_id, column=build_ended_column,
                                 value=time_end_string)
        Metrics.set_cell_to_time_format(sheet=current_worksheet, column=build_ended_column, row=this_sheet_row_id)

        # build duration
        build_duration_column = SheetColumns.build_duration.value
        Metrics.update_worksheet(sheet=current_worksheet, row=this_sheet_row_id, column=build_duration_column,
                                 value="=sum(D" + str(this_sheet_row_id) + "-" + "C" + str(
                                     this_sheet_row_id) + ")")
        Metrics.set_cell_to_time_format(sheet=current_worksheet, column=build_duration_column, row=this_sheet_row_id)

        #  type of dungeon builder used
        build_type_column = SheetColumns.build_type.value
        Metrics.update_worksheet(sheet=current_worksheet, row=this_sheet_row_id, column=build_type_column,
                                 value='Cellular')

        # total tile count for this dungeon
        tile_count = self.game_map.width * self.game_map.height
        build_tile_count_column = SheetColumns.total_tile_count.value
        Metrics.update_worksheet(sheet=current_worksheet, row=this_sheet_row_id, column=build_tile_count_column,
                                 value=tile_count)

        # total wall count
        wall_count_column = SheetColumns.total_wall_count.value
        Metrics.update_worksheet(sheet=current_worksheet, row=this_sheet_row_id, column=wall_count_column,
                                 value=self.wall_count)

        # total obstacle count
        build_obstacle_count_column = SheetColumns.total_obstacle_count.value
        Metrics.update_worksheet(sheet=current_worksheet, row=this_sheet_row_id, column=build_obstacle_count_column,
                                 value=self.unused_tiles)
        # total floor count
        build_floor_count_column = SheetColumns.total_floor_count.value
        Metrics.update_worksheet(sheet=current_worksheet, row=this_sheet_row_id, column=build_floor_count_column,
                                 value=self.current_floor_count)
        # total corridor count
        build_corridor_count_column = SheetColumns.total_corridor_count.value
        Metrics.update_worksheet(sheet=current_worksheet, row=this_sheet_row_id, column=build_corridor_count_column,
                                 value=self.corridor_count)

        # total room count
        build_room_count_column = SheetColumns.total_room_count.value
        Metrics.update_worksheet(sheet=current_worksheet, row=this_sheet_row_id, column=build_room_count_column,
                                 value=self.room_count)

        Metrics.save_workbook(workbook=current_workbook)

        return self.game_map

    def metrics_count(self):
        tile_type_floor = 1
        tile_type_wall = 5
        for y in range(1, self.game_map.height - 1):
            for x in range(1, self.game_map.width - 1):
                tile = self.game_map.tiles[x][y].type_of_tile
                if tile == tile_type_floor:
                    self.current_floor_count += 1

                if tile == tile_type_wall:
                    self.wall_count += 1
        self.unused_tiles -= (self.current_floor_count + self.wall_count)

    def clear_map_to_floor(self):
        tile_type_floor = 1
        for y in range(1, self.game_map.height - 1):
            for x in range(1, self.game_map.width - 1):
                self.game_map.tiles[x][y].type_of_tile = tile_type_floor

    def create_false_border_for_game_map(self):
        tile_type_wall = 5
        for y in range(self.game_map.height):
            for x in range(self.game_map.width):
                if (y == 0 or y == self.game_map.height - 1) and x > 0:
                    self.game_map.tiles[x][y].type_of_tile = tile_type_wall

                if x == 0 or x == self.game_map.width - 1:
                    self.game_map.tiles[x][y].type_of_tile = tile_type_wall

    def fill_map_with_walls(self):
        tile_type_wall = 5
        for y in range(1, self.game_map.height - 1):
            for x in range(1, self.game_map.width - 1):
                if random.random() >= self.wall_probability:
                    self.game_map.tiles[x][y].type_of_tile = tile_type_wall

    def create_caves(self):
        # ==== Create distinct caves ====
        tile_type_wall = 5
        tile_type_floor = 1
        for i in range(0, self.iterations):
            # Pick a random point with a buffer around the edges of the map
            tile_x = random.randint(1, self.game_map.width - 2)  # (2,mapWidth-3)
            tile_y = random.randint(1, self.game_map.height - 2)  # (2,mapHeight-3)

            # if the cell's neighboring walls > self.neighbors, set it to 1
            if self.getAdjacentWalls(tile_x, tile_y) > self.neighbors:
                self.game_map.tiles[tile_x][tile_y].type_of_tile = tile_type_wall
            # or set it to 0
            elif self.getAdjacentWalls(tile_x, tile_y) < self.neighbors:
                self.game_map.tiles[tile_x][tile_y].type_of_tile = tile_type_floor

        # ==== Clean Up Map ====
        self.clean_up_map()

    def clean_up_map(self):
        tile_type_wall = 5
        tile_type_floor = 1
        if self.smooth_edges:
            for i in range(0, 5):
                # Look at each cell individually and check for smoothness
                for x in range(1, self.game_map.width - 1):
                    for y in range(1, self.game_map.height - 1):
                        if (self.game_map.tiles[x][y].type_of_tile == tile_type_wall) and (self.get_adjacent_walls_simple(x, y) <= self.smoothing):
                            self.game_map.tiles[x][y].type_of_tile = tile_type_floor

    def create_tunnel(self, point1, point2, current_cave):
        tile_type_wall = 5
        tile_type_floor = 1
        # run a heavily weighted random Walk
        # from point1 to point1
        drunkard_x = point2[0]
        drunkard_y = point2[1]
        while (drunkard_x, drunkard_y) not in current_cave:
            # ==== Choose Direction ====
            north = 1.0
            south = 1.0
            east = 1.0
            west = 1.0

            weight = 1

            # weight the random walk against edges
            if drunkard_x < point1[0]:  # drunkard is left of point1
                east += weight
            elif drunkard_x > point1[0]:  # drunkard is right of point1
                west += weight
            if drunkard_y < point1[1]:  # drunkard is above point1
                south += weight
            elif drunkard_y > point1[1]:  # drunkard is below point1
                north += weight

            # normalize probabilities so they form a range from 0 to 1
            total = north + south + east + west
            north /= total
            south /= total
            east /= total
            west /= total

            # choose the direction
            choice = random.random()
            if 0 <= choice < north:
                dx = 0
                dy = -1
            elif north <= choice < (north + south):
                dx = 0
                dy = 1
            elif (north + south) <= choice < (north + south + east):
                dx = 1
                dy = 0
            else:
                dx = -1
                dy = 0

            # ==== Walk ====
            # check colision at edges
            if (0 < drunkard_x + dx < self.game_map.width - 1) and (0 < drunkard_y + dy <  self.game_map.height - 1):
                drunkard_x += dx
                drunkard_y += dy
                if self.game_map.tiles[drunkard_x][drunkard_y].type_of_tile == tile_type_wall:
                    self.game_map.tiles[drunkard_x][drunkard_y].type_of_tile = tile_type_floor

    def get_adjacent_walls_simple(self, x, y):  # finds the walls in four directions
        wallCounter = 0
        tile_type_wall = 5
        if self.game_map.tiles[x][y - 1].type_of_tile == tile_type_wall:  # Check north
            wallCounter += 1
        if self.game_map.tiles[x][y + 1].type_of_tile == tile_type_wall:  # Check south
            wallCounter += 1
        if self.game_map.tiles[x - 1][y].type_of_tile == tile_type_wall:  # Check west
            wallCounter += 1
        if self.game_map.tiles[x + 1][y].type_of_tile == tile_type_wall:  # Check east
            wallCounter += 1

        return wallCounter

    def getAdjacentWalls(self, tile_x, tile_y):  # finds the walls in 8 directions
        wall_counter = 0
        tile_type_wall = 5
        for x in range(tile_x - 1, tile_x + 2):
            for y in range(tile_y - 1, tile_y + 2):
                if self.game_map.tiles[x][y].type_of_tile == tile_type_wall:
                    if (x != tile_x) or (y != tile_y):  # exclude (tileX,tileY)
                        wall_counter += 1
        return wall_counter

    def get_caves(self):
        tile_type_floor = 1
        # locate all the caves within self.game_map and store them in self.caves
        for x in range(0,  self.game_map.width):
            for y in range(0,  self.game_map.height):
                if self.game_map.tiles[x][y].type_of_tile == tile_type_floor:
                    self.flood_fill(x, y)

        for my_set in self.caves:
            for tile in my_set:
                self.game_map.tiles[tile[0]][tile[1]].type_of_tile = tile_type_floor

    def flood_fill(self, x, y):
        tile_type_wall = 5
        tile_type_floor = 1
        # 		flood fill the separate regions of the level, discard
        # 		the regions that are smaller than a minimum size, and
        # 		create a reference for the rest.

        cave = set()
        tile = (x, y)
        to_be_filled = set([tile])
        while to_be_filled:
            tile = to_be_filled.pop()

            if tile not in cave:
                cave.add(tile)

                self.game_map.tiles[tile[0]][tile[1]].type_of_tile = tile_type_wall

                # check adjacent cells
                x = tile[0]
                y = tile[1]
                north = (x, y - 1)
                south = (x, y + 1)
                east = (x + 1, y)
                west = (x - 1, y)

                for direction in [north, south, east, west]:

                    if self.game_map.tiles[direction[0]][direction[1]].type_of_tile == tile_type_floor:
                        if direction not in to_be_filled and direction not in cave:
                            to_be_filled.add(direction)

        if len(cave) >= self.ROOM_MIN_SIZE:
            self.caves.append(cave)

    def connect_caves(self):
        # Find the closest cave to the current cave
        for current_cave in self.caves:
            for point1 in current_cave: break  # get an element from cave1
            point2 = None
            distance = 0
            for next_cave in self.caves:
                if next_cave != current_cave and not self.check_connectivity(current_cave, next_cave):
                    # choose a random point from nextCave
                    for next_point in next_cave: break  # get an element from cave1
                    # compare distance of point1 to old and new point2
                    new_distance = self.distance_formula(point1, next_point)
                    if (new_distance < distance) or distance == 0:
                        point2 = next_point
                        distance = new_distance

            if point2:  # if all tunnels are connected, point2 == None
                self.create_tunnel(point1, point2, current_cave)

    def distance_formula(self, point1, point2):
        d = sqrt((point2[0] - point1[0]) ** 2 + (point2[1] - point1[1]) ** 2)
        return d

    def check_connectivity(self, cave1, cave2):
        # floods cave1, then checks a point in cave2 for the flood
        tile_type_floor = 1
        connected_region = set()
        for start in cave1: break  # get an element from cave1

        to_be_filled = set([start])
        while to_be_filled:
            tile = to_be_filled.pop()

            if tile not in connected_region:
                connected_region.add(tile)

                # check adjacent cells
                x = tile[0]
                y = tile[1]
                north = (x, y - 1)
                south = (x, y + 1)
                east = (x + 1, y)
                west = (x - 1, y)

                for direction in [north, south, east, west]:

                    if self.game_map.tiles[direction[0]][direction[1]].type_of_tile == tile_type_floor:
                        if direction not in to_be_filled and direction not in connected_region:
                            to_be_filled.add(direction)

        for end in cave2: break  # get an element from cave2

        if end in connected_region:
            return True

        else:
            return False
