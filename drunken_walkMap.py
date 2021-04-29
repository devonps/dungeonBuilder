import random
import sys

from dungeon_utilities import TidyDungeon
from gameMap import GameMap
from metrics import Metrics, SheetColumns


class DrunkardsWalk:
    def __init__(self, map_width, map_height):
        self.game_map = GameMap(mapwidth=map_width, mapheight=map_height)
        self.previous_direction = None
        self.current_floor_count = 0
        self.saved_build_seed = 0
        # self.saved_build_seed = 2.07727622288305E+018
        self.build_seed = self.generate_random_seed()
        self.unused_tiles = 0
        self._filled = 0
        self.percent_goal = .4
        self.walk_iterations = 25000  # cut off in case _percentGoal in never reached
        self.weighted_toward_center = 0.17
        self.weighted_toward_previous_direction = 0.6
        self.drunkard_x = 0
        self.drunkard_y = 0
        self.filled_goal = 0
        self.corridor_count = -1
        self.room_count = -1

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

        # Creates an empty 2D array or clears existing array
        self.walk_iterations = max(self.walk_iterations, (self.game_map.width * self.game_map.height * 10))

        # initialise new dungeon - everywhere is an obstacle/unused tile
        random.seed(self.build_seed)
        self.unused_tiles = self.game_map.width * self.game_map.height

        self.drunkard_x = random.randint(2, self.game_map.width - 2)
        self.drunkard_y = random.randint(2, self.game_map.height - 2)
        self.filled_goal = self.game_map.width * self.game_map.height * self.percent_goal

        for _ in range(self.walk_iterations):
            self.walk()
            if self._filled >= self.filled_goal:
                break

        #  add walls around floor spaces
        decorate_map = TidyDungeon(game_map=self.game_map)
        total_wall_count = decorate_map.add_walls()
        self.unused_tiles -= total_wall_count
        removed_wall_count, added_floor_count = decorate_map.remove_wall_islands()
        total_wall_count -= removed_wall_count
        self.current_floor_count += added_floor_count

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
        Metrics.update_worksheet(sheet=current_worksheet, row=this_sheet_row_id, column=build_type_column, value='Drunkard')

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

    def walk(self):
        # ==== Choose Direction ====
        north = 1.0
        south = 1.0
        east = 1.0
        west = 1.0

        # weight the random walk against edges
        if self.drunkard_x < self.game_map.width * 0.25:  # drunkard is at far left side of map
            east += self.weighted_toward_center
        elif self.drunkard_x > self.game_map.width * 0.75:  # drunkard is at far right side of map
            west += self.weighted_toward_center
        if self.drunkard_y < self.game_map.height * 0.25:  # drunkard is at the top of the map
            south += self.weighted_toward_center
        elif self.drunkard_y > self.game_map.height * 0.75:  # drunkard is at the bottom of the map
            north += self.weighted_toward_center

        # weight the random walk in favor of the previous direction
        if self.previous_direction == "north":
            north += self.weighted_toward_previous_direction
        if self.previous_direction == "south":
            south += self.weighted_toward_previous_direction
        if self.previous_direction == "east":
            east += self.weighted_toward_previous_direction
        if self.previous_direction == "west":
            west += self.weighted_toward_previous_direction

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
            direction = "north"
        elif north <= choice < (north + south):
            dx = 0
            dy = 1
            direction = "south"
        elif (north + south) <= choice < (north + south + east):
            dx = 1
            dy = 0
            direction = "east"
        else:
            dx = -1
            dy = 0
            direction = "west"

        # ==== Walk ====
        # check colision at edges TODO: change so it stops one tile from edge
        tile_type_floor = 1
        tile_type_obstacle = 6
        if (0 < self.drunkard_x + dx < self.game_map.width - 2) and (0 < self.drunkard_y + dy < self.game_map.height - 2):
            self.drunkard_x += dx
            self.drunkard_y += dy
            if self.game_map.tiles[self.drunkard_x][self.drunkard_y].type_of_tile == tile_type_obstacle:
                self.game_map.tiles[self.drunkard_x][self.drunkard_y].type_of_tile = tile_type_floor
                self._filled += 1
                self.current_floor_count += 1
                self.unused_tiles -= 1
            self.previous_direction = direction
