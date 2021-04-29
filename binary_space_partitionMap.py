import random
import sys

from loguru import logger

from gameMap import GameMap
from metrics import Metrics, SheetColumns
from dungeon_utilities import Rect, TidyDungeon


class BSPTree:
    def __init__(self, map_width, map_height):
        self._leafs = []
        self.game_map = GameMap(mapwidth=map_width, mapheight=map_height)
        self.room = None
        self.MAX_LEAF_SIZE = 48
        self.ROOM_MAX_SIZE = 40
        self.ROOM_MIN_SIZE = 19
        self.current_floor_count = 0
        self.corridor_count = 0
        self.room_count = 0
        self.saved_build_seed = 0
        self.build_seed = self.generate_random_seed()
        self.unused_tiles = 0

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

        root_leaf = Leaf(0, 0, self.game_map.width, self.game_map.height)
        self._leafs.append(root_leaf)

        split_successfully = True
        # loop through all leaves until they can no longer split successfully
        while split_successfully:
            split_successfully = False
            for loop_object in self._leafs:
                if (loop_object.child_1 is None) and (loop_object.child_2 is None):
                    if ((loop_object.width > self.MAX_LEAF_SIZE) or
                            (loop_object.height > self.MAX_LEAF_SIZE) or
                            (random.random() > 0.8)):
                        if loop_object.split_leaf():  # try to split the leaf
                            self._leafs.append(loop_object.child_1)
                            self._leafs.append(loop_object.child_2)
                            split_successfully = True

        root_leaf.create_rooms(self)

        #  add walls around floor spaces
        decorate_map = TidyDungeon(game_map=self.game_map)
        total_wall_count = decorate_map.add_walls()

        self.unused_tiles -= total_wall_count
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
        Metrics.update_worksheet(sheet=current_worksheet, row=this_sheet_row_id, column=build_type_column, value='BSP')

        # total tile count for this dungeon
        tile_count = self.game_map.width * self.game_map.height
        build_tile_count_column = SheetColumns.total_tile_count.value
        Metrics.update_worksheet(sheet=current_worksheet, row=this_sheet_row_id, column=build_tile_count_column,
                                 value=tile_count)

        # total wall count
        wall_count_column = SheetColumns.total_wall_count.value
        Metrics.update_worksheet(sheet=current_worksheet, row=this_sheet_row_id, column=wall_count_column,
                                 value=total_wall_count)

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

    def create_room(self, room):
        # set all tiles within a rectangle to 1
        tile_type_floor = 1
        self.room_count += 1
        logger.info('Room id {}', self.room_count)
        logger.info('Room coords x/y: {} {} / {} {}', room.x1, room.x2, room.y1, room.y2)
        logger.info('Game map dimensions are {} / {}', self.game_map.width, self.game_map.height)
        for x in range(room.x1 + 1, room.x2):
            for y in range(room.y1 + 1, room.y2):
                self.game_map.tiles[x][y].type_of_tile = tile_type_floor
                self.current_floor_count += 1
                self.unused_tiles -= 1

    def create_hall(self, room1, room2):
        # connect two rooms by hallways
        x1, y1 = room1.center()
        x2, y2 = room2.center()
        # 50% chance that a tunnel will start horizontally
        if random.randint(0, 1) == 1:
            self.create_hor_tunnel(int(x1), int(x2), int(y1))
            self.create_ver_tunnel(int(y1), int(y2), int(x2))

        else:  # else it starts vertically
            self.create_ver_tunnel(int(y1), int(y2), int(x1))
            self.create_hor_tunnel(int(x1), int(x2), int(y2))

    def create_hor_tunnel(self, x1, x2, y):
        tile_type_floor = 1
        self.corridor_count += 1
        for x in range(min(x1, x2), max(x1, x2) + 1):
            self.game_map.tiles[x][y].type_of_tile = tile_type_floor
            self.current_floor_count += 1
            self.unused_tiles -= 1

    def create_ver_tunnel(self, y1, y2, x):
        tile_type_floor = 1
        self.corridor_count += 1
        for y in range(min(y1, y2), max(y1, y2) + 1):
            self.game_map.tiles[x][y].type_of_tile = tile_type_floor
            self.current_floor_count += 1
            self.unused_tiles -= 1


class Leaf:  # used for the BSP tree algorithm
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.MIN_LEAF_SIZE = 15
        self.child_1 = None
        self.child_2 = None
        self.room = None
        self.hall = None

    def split_leaf(self):
        # begin splitting the leaf into two children
        if (self.child_1 is not None) or (self.child_2 is not None):
            return False  # This leaf has already been split

        '''
        ==== Determine the direction of the split ====
        If the width of the leaf is >25% larger than the height,
        split the leaf vertically.
        If the height of the leaf is >25 larger than the width,
        split the leaf horizontally.
        Otherwise, choose the direction at random.
        '''
        split_horizontally = random.choice([True, False])
        if self.width / self.height >= 1.25:
            split_horizontally = False
        elif self.height / self.width >= 1.25:
            split_horizontally = True

        if split_horizontally:
            my_max = self.height - self.MIN_LEAF_SIZE
        else:
            my_max = self.width - self.MIN_LEAF_SIZE

        if my_max <= self.MIN_LEAF_SIZE:
            return False  # the leaf is too small to split further

        split = random.randint(self.MIN_LEAF_SIZE, my_max)  # determine where to split the leaf

        if split_horizontally:
            self.child_1 = Leaf(self.x, self.y, self.width, split)
            self.child_2 = Leaf(self.x, self.y + split, self.width, self.height - split)
        else:
            self.child_1 = Leaf(self.x, self.y, split, self.height)
            self.child_2 = Leaf(self.x + split, self.y, self.width - split, self.height)

        return True

    def create_rooms(self, bsp_tree):
        if self.child_1 or self.child_2:
            # recursively search for children until you hit the end of the branch
            if self.child_1:
                self.child_1.create_rooms(bsp_tree)
            if self.child_2:
                self.child_2.create_rooms(bsp_tree)

            if self.child_1 and self.child_2:
                bsp_tree.create_hall(self.child_1.get_room(), self.child_2.get_room())

        else:
            # Create rooms in the end branches of the bsp tree
            w = random.randint(bsp_tree.ROOM_MIN_SIZE, min(bsp_tree.ROOM_MAX_SIZE, self.width - 1))
            h = random.randint(bsp_tree.ROOM_MIN_SIZE, min(bsp_tree.ROOM_MAX_SIZE, self.height - 1))
            x = random.randint(self.x, self.x + (self.width - 1) - w)
            y = random.randint(self.y, self.y + (self.height - 1) - h)

            w = 20
            h = 20
            x = self.x
            y = self.y

            if y + h > 50:
                h = 10

            self.room = Rect(startx=x, starty=y, width=w, height=h)
            bsp_tree.create_room(self.room)

    def get_room(self):
        if self.room:
            return self.room

        else:
            if self.child_1:
                self.room_1 = self.child_1.get_room()
            if self.child_2:
                self.room_2 = self.child_2.get_room()

            if not self.child_1 and not self.child_2:
                # neither room_1 nor room_2
                return None

            elif not self.room_2:
                # room_1 and !room_2
                return self.room_1

            elif not self.room_1:
                # room_2 and !room_1
                return self.room_2

            # If both room_1 and room_2 exist, pick one
            elif random.random() < 0.5:
                return self.room_1
            else:
                return self.room_2
