import random
import sys

from loguru import logger

import configUtilities


def dump_rectangle(room):
    logger.info('X1:{}', room.x1)
    logger.info('X2:{}', room.x2)
    logger.info('Y1:{}', room.y1)
    logger.info('Y2:{}', room.y2)


class Rect:
    def __init__(self, startx, starty, width, height):
        self.x1 = startx
        self.y1 = starty
        self.x2 = startx + width
        self.y2 = starty + height

    def center(self):
        center_x = (self.x1 + self.x2) / 2
        center_y = (self.y1 + self.y2) / 2
        return center_x, center_y

    def is_there_a_map_tile_inside_this_rectangle(self, game_map):
        map_tile_found = False
        tile_type_floor = 1
        for y in range(self.y1, self.y2):
            for x in range(self.x1, self.x2):
                tile = game_map.tiles[x][y].type_of_tile
                if tile == tile_type_floor:
                    map_tile_found = True
                    # logger.debug('Overlap x/y are {}/{}', x, y)
            if map_tile_found:
                break
        return map_tile_found

    def outside_of_game_map(self, game_map):
        if self.x1 <= 1 or self.x2 >= game_map.width or self.y1 <= 1 or self.y2 >= game_map.height:
            return True
        else:
            return False


class GenerateRandomSeed:
    def __init__(self, saved_build_seed):
        self.saved_build_seed = saved_build_seed

    def generate_random_seed(self):
        if self.saved_build_seed == 0:
            seed_value = random.randrange(sys.maxsize)
        else:
            seed_value = self.saved_build_seed
        random.seed(seed_value)
        return seed_value


class TidyDungeon:
    def __init__(self, game_map):
        self.game_map = game_map
        self.placed_doors = []
        game_config = configUtilities.load_config()
        self.game_map = game_map
        self.tile_type_wall = configUtilities.get_config_value_as_integer(configfile=game_config, section='dungeon',
                                                                          parameter='TILE_TYPE_WALL')
        self.tile_type_floor = configUtilities.get_config_value_as_integer(configfile=game_config, section='dungeon',
                                                                           parameter='TILE_TYPE_FLOOR')
        self.tile_type_door = configUtilities.get_config_value_as_integer(configfile=game_config, section='dungeon',
                                                                           parameter='TILE_TYPE_DOOR')
        self.tile_type_obstacle = configUtilities.get_config_value_as_integer(configfile=game_config, section='dungeon',
                                                                              parameter='TILE_TYPE_OBSTACLE')
        self.dungeon_width = configUtilities.get_config_value_as_integer(configfile=game_config, section='dungeon',
                                                                         parameter='max_width')
        self.dungeon_height = configUtilities.get_config_value_as_integer(configfile=game_config, section='dungeon',
                                                                          parameter='max_height')

    def erase_hanging_ddors(self):
        # remove the 'hanging end square' from a corridor
        for x in range(self.game_map.width - 2):
            for y in range(self.game_map.height - 2):
                tile = self.game_map.tiles[x][y].type_of_tile
                north_of_tile = self.game_map.tiles[x][y - 1].type_of_tile
                east_of_tile = self.game_map.tiles[x + 1][y].type_of_tile
                south_of_tile = self.game_map.tiles[x][y + 1].type_of_tile
                west_of_tile = self.game_map.tiles[x - 1][y].type_of_tile
                north_east_of_tile = self.game_map.tiles[x + 1][y - 1].type_of_tile
                south_east_of_tile = self.game_map.tiles[x + 1][y + 1].type_of_tile
                south_west_of_tile = self.game_map.tiles[x - 1][y + 1].type_of_tile
                north_west_of_tile = self.game_map.tiles[x - 1][y - 1].type_of_tile

                if tile == self.tile_type_wall:
                    # checks for hanging wall tile on the horizontal axis of the target tile
                    if north_of_tile == self.tile_type_obstacle and east_of_tile == self.tile_type_obstacle and south_of_tile == self.tile_type_obstacle:
                        if west_of_tile == self.tile_type_floor:
                            self.game_map.tiles[x - 1][y].type_of_tile = self.tile_type_wall
                            self.game_map.tiles[x][y].type_of_tile = self.tile_type_obstacle
                    # checks for hanging wall to the west of the target tile
                    if north_of_tile == self.tile_type_obstacle and west_of_tile == self.tile_type_obstacle and south_of_tile == self.tile_type_obstacle:
                        if east_of_tile == self.tile_type_floor:
                            self.game_map.tiles[x + 1][y].type_of_tile = self.tile_type_wall
                            self.game_map.tiles[x][y].type_of_tile = self.tile_type_obstacle

                    # checks for hanging wall tile on the vertical axis of the target tile

                    # checks for hanging wall to the north of the target tile
                    if north_of_tile == self.tile_type_obstacle and east_of_tile == self.tile_type_obstacle and west_of_tile == self.tile_type_obstacle:
                        if south_of_tile == self.tile_type_floor:
                            self.game_map.tiles[x][y + 1].type_of_tile = self.tile_type_wall
                            self.game_map.tiles[x][y].type_of_tile = self.tile_type_obstacle

                    # checks for hanging wall to the south of the target tile
                    if east_of_tile == self.tile_type_obstacle and west_of_tile == self.tile_type_obstacle and south_of_tile == self.tile_type_obstacle:
                        if north_of_tile == self.tile_type_floor:
                            self.game_map.tiles[x][y - 1].type_of_tile = self.tile_type_wall
                            self.game_map.tiles[x][y].type_of_tile = self.tile_type_obstacle

    def open_up_double_walls(self):
        double_wall_horizontal_list = []
        double_wall_vertical_list = []
        for x in range(self.game_map.width - 2):
            for y in range(self.game_map.height - 2):
                tile = self.game_map.tiles[x][y].type_of_tile
                north_of_tile = self.game_map.tiles[x][y - 1].type_of_tile
                east_of_tile = self.game_map.tiles[x + 1][y].type_of_tile
                south_of_tile = self.game_map.tiles[x][y + 1].type_of_tile
                west_of_tile = self.game_map.tiles[x - 1][y].type_of_tile
                north_east_of_tile = self.game_map.tiles[x + 1][y - 1].type_of_tile
                south_east_of_tile = self.game_map.tiles[x + 1][y + 1].type_of_tile
                south_west_of_tile = self.game_map.tiles[x - 1][y + 1].type_of_tile
                north_west_of_tile = self.game_map.tiles[x - 1][y - 1].type_of_tile
                # looks for 'double walls' checks tiles east of target tile
                if east_of_tile == self.tile_type_wall and west_of_tile == self.tile_type_floor:
                    if north_of_tile == self.tile_type_wall and south_of_tile == self.tile_type_wall:
                        if north_east_of_tile == self.tile_type_wall and south_east_of_tile == self.tile_type_wall:
                            double_wall = (x, y)
                            double_wall_horizontal_list.append(double_wall)

                # looks for 'double walls' to the south of target tile
                if south_of_tile == self.tile_type_wall and north_of_tile == self.tile_type_floor:
                    if east_of_tile == self.tile_type_wall and west_of_tile == self.tile_type_wall:
                        if south_east_of_tile == self.tile_type_wall and south_west_of_tile == self.tile_type_wall:
                            double_wall = (x, y)
                            double_wall_vertical_list.append(double_wall)

        # For all vertical double walls there's a 30% chance of them being opened up
        for z in double_wall_horizontal_list:
            r = random.randrange(0, 100)
            logger.info('[hor]Looking at {} random point is {}', z, r)
            if r < 30:
                x = z[0]
                y = z[1]
                self.game_map.tiles[x][y].type_of_tile = self.tile_type_floor
                self.game_map.tiles[x + 1][y].type_of_tile = self.tile_type_floor

        # For all horizontal double walls there's a 30% chance of them being opened up
        for z in double_wall_vertical_list:
            r = random.randrange(0, 100)
            logger.info('[vert] Looking at {} random point is {}', z, r)
            if r < 30:
                x = z[0]
                y = z[1]
                self.game_map.tiles[x][y].type_of_tile = self.tile_type_floor
                self.game_map.tiles[x][y + 1].type_of_tile = self.tile_type_floor

    def open_up_hallways(self):
        end_of_halway_list = []
        for x in range(self.game_map.width - 2):
            for y in range(self.game_map.height - 2):
                tile = self.game_map.tiles[x][y].type_of_tile
                north_of_tile = self.game_map.tiles[x][y - 1].type_of_tile
                east_of_tile = self.game_map.tiles[x + 1][y].type_of_tile
                south_of_tile = self.game_map.tiles[x][y + 1].type_of_tile
                west_of_tile = self.game_map.tiles[x - 1][y].type_of_tile
                north_east_of_tile = self.game_map.tiles[x + 1][y - 1].type_of_tile
                south_east_of_tile = self.game_map.tiles[x + 1][y + 1].type_of_tile
                south_west_of_tile = self.game_map.tiles[x - 1][y + 1].type_of_tile
                north_west_of_tile = self.game_map.tiles[x - 1][y - 1].type_of_tile

                # look for the 'end of a hallway' that backs on to another room and possibly open it up
                if north_of_tile == self.tile_type_wall and south_of_tile == self.tile_type_wall and north_east_of_tile == self.tile_type_wall and south_east_of_tile == self.tile_type_wall:
                    if west_of_tile == self.tile_type_floor and east_of_tile == self.tile_type_floor:
                        end_hallway = (x, y)
                        end_of_halway_list.append(end_hallway)

        # for all end of hallways there's a 30% chance of them being opened up
        for z in end_of_halway_list:
            r = random.randrange(0, 100)
            logger.info('[EoH] Looking at {} random point is {}', z, r)
            if r < 50:
                x = z[0]
                y = z[1]
                self.game_map.tiles[x][y].type_of_tile = self.tile_type_floor

    def add_walls(self):
        wall_count = 0
        for scr_pos_y in range(self.dungeon_height - 1):
            for scr_pos_x in range(self.dungeon_width - 1):

                tile = self.game_map.tiles[scr_pos_x][scr_pos_y].type_of_tile
                if tile == self.tile_type_floor:
                    wall_count += 1
                    TidyDungeon.add_wall_horizontal(self, x=scr_pos_x, y=scr_pos_y)
                    TidyDungeon.add_wall_vertical(self, x=scr_pos_x, y=scr_pos_y)
        return wall_count

    def add_wall_horizontal(self, x, y):
        # west
        if self.game_map.tiles[x - 1][y].type_of_tile == self.tile_type_obstacle:
            self.game_map.tiles[x - 1][y].type_of_tile = self.tile_type_wall
            self.game_map.tiles[x - 1][y].blocked = True
        # east
        if self.game_map.tiles[x + 1][y].type_of_tile == self.tile_type_obstacle:
            self.game_map.tiles[x + 1][y].type_of_tile = self.tile_type_wall
            self.game_map.tiles[x + 1][y].blocked = True

    def add_wall_vertical(self, x, y):
        # north
        if self.game_map.tiles[x][y - 1].type_of_tile == self.tile_type_obstacle:
            self.game_map.tiles[x][y - 1].type_of_tile = self.tile_type_wall
            self.game_map.tiles[x][y - 1].blocked = True
        # south
        if self.game_map.tiles[x][y + 1].type_of_tile == self.tile_type_obstacle:
            self.game_map.tiles[x][y + 1].type_of_tile = self.tile_type_wall
            self.game_map.tiles[x][y + 1].blocked = True

    def remove_wall_islands(self):
        removed_wall_count = 0
        added_floor_count = 0
        for scr_pos_y in range(self.dungeon_height - 1):
            for scr_pos_x in range(self.dungeon_width - 1):

                tile = self.game_map.tiles[scr_pos_x][scr_pos_y].type_of_tile
                if tile == self.tile_type_wall:
                    tile_north = self.game_map.tiles[scr_pos_x][scr_pos_y - 1].type_of_tile
                    tile_east = self.game_map.tiles[scr_pos_x + 1][scr_pos_y].type_of_tile
                    tile_south = self.game_map.tiles[scr_pos_x][scr_pos_y + 1].type_of_tile
                    tile_west = self.game_map.tiles[scr_pos_x - 1][scr_pos_y].type_of_tile

                    if tile_north == self.tile_type_floor and tile_east == self.tile_type_floor and tile_south == self.tile_type_floor and tile_west == self.tile_type_floor:
                        self.game_map.tiles[scr_pos_x][scr_pos_y].type_of_tile = self.tile_type_floor
                        removed_wall_count += 1
                        added_floor_count += 1
        return removed_wall_count, added_floor_count
