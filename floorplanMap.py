import random
import sys
from enum import IntEnum

import json_utilities

from loguru import logger
from gameMap import GameMap
from metrics import Metrics, SheetColumns
from dungeon_utilities import Rect, TidyDungeon


class Room:
    def __init__(self, cell_id, template, last_cell):
        self.template = template
        self.id = cell_id
        self.last_cell = last_cell


class FloormapTemplates(IntEnum):
    room_square = 0
    hallway_vertical = 1
    hallway_horizontal = 2
    hallway_cross = 3
    hallway_vertical_east = 4
    hallway_vertical_west = 5


class Floorplan:
    def __init__(self, map_width, map_height):
        self.game_map = GameMap(mapwidth=map_width, mapheight=map_height)
        self.cell_size_x = 11
        self.cell_size_y = 11
        self.cell_down_jump = 0
        self.maximum_rooms = 20
        self.stored_rooms = None
        self.neighbour_restriction_count = 2
        self.cells_to_be_checked = []
        self.placed_cells = []
        self.original_placed_cells = []
        self.saved_build_seed = 8246014785348617086
        # self.saved_build_seed = 0
        self.build_seed = self.generate_random_seed()
        self.stored_templates = self.load_floormap_templates()
        self.cell_coords = self.generate_cell_coords()
        self.starting_cell = 60

    def generate_cell_coords(self):
        # currently this set up creates a 1 char gap between cells
        # this isn't expected behaviour - there should be a zero gap
        logger.warning('Dungeon seed is {}', self.build_seed)
        cell_grid = []
        max_x_cells = int((self.game_map.width - 1) / self.cell_size_x)
        max_y_cells = int((self.game_map.height - 1) / self.cell_size_y)
        logger.info('Max X cells {}', max_x_cells)
        logger.info('Max Y cells {}', max_y_cells)
        self.cell_down_jump = max_x_cells
        self.stored_rooms = [Room(cell_id=i, template=FloormapTemplates.room_square, last_cell=0) for i in range(max_x_cells * max_y_cells)]
        grid_y = 1
        for _ in range(max_y_cells):
            grid_x = 1
            for _ in range(max_x_cells):
                z = {'start_x': grid_x, 'start_y': grid_y}
                grid_x += self.cell_size_x - 1
                cell_grid.append(z)
            grid_y += self.cell_size_y - 1
        # logger.info(cell_grid)
        return cell_grid

    def load_floormap_templates(self):
        template_list = json_utilities.read_json_file("floorplan_templates.json")
        return template_list

    def generate_random_seed(self):
        if self.saved_build_seed == 0:
            seed_value = random.randrange(sys.maxsize)
        else:
            seed_value = self.saved_build_seed
        return seed_value

    def is_target_cell_populated(self, cell):
        for i in range(len(self.placed_cells)):
            if self.placed_cells[i] == cell:
                return True
        return False

    def floorplan_create_room(self, room, floorplan_walkable_area, rows, columns):
        tile_type_floor = 1
        tile_type_door = 3
        tile_type_wall = 5
        yz = 0
        rc = 1
        # Build Interior of cell with floors and any doors in fixed locations - based off template
        for y in range(columns):
            xz = 0
            this_row = "row_" + str(rc)
            row_data = floorplan_walkable_area[0][this_row]
            for x in range(rows):
                this_row_data = row_data[xz]
                if this_row_data == '.':
                    self.game_map.tiles[room.x1 + xz][room.y1 + yz].type_of_tile = tile_type_floor
                if this_row_data == '+':
                    self.game_map.tiles[room.x1 + xz][room.y1 + yz].type_of_tile = tile_type_floor
                    if y == 0:
                        self.game_map.tiles[room.x1 + xz][room.y1 - 1].type_of_tile = tile_type_door
                    if y == columns - 1:
                        self.game_map.tiles[room.x1 + xz][room.y1 + columns].type_of_tile = tile_type_door
                    if x == 0:
                        self.game_map.tiles[room.x1 - 1][room.y1 + yz].type_of_tile = tile_type_door
                    if x == rows - 1:
                        self.game_map.tiles[room.x1 + rows][room.y1 + yz].type_of_tile = tile_type_door
                if this_row_data == '#':
                    self.game_map.tiles[room.x1 + xz][room.y1 + yz].type_of_tile = tile_type_wall
                xz += 1
            yz += 1
            rc += 1

    def generate_level(self):
        # generate the floor plan
        random.seed(self.build_seed)
        self.boi_placement()
        self.original_placed_cells = self.placed_cells

        logger.info('------- Finished placing cells')
        logger.info('Total cells placed {}', len(self.placed_cells))
        logger.info('Maximum number of cells {}', self.maximum_rooms)
        logger.info('List of cells placed {}', self.placed_cells)
        logger.info('Count of remaining cells that could not be placed is {}', len(self.cells_to_be_checked))

        decorate_map = TidyDungeon(game_map=self.game_map)
        # and then the cell is populated based on that room template
        while len(self.placed_cells) > 0:
            # which cell are we working with
            this_cell = self.placed_cells.pop(0)
            logger.info('Cell {} popped off the list', this_cell)
            cell_coords = self.cell_coords[this_cell]
            start_x = cell_coords['start_x']
            start_y = cell_coords['start_y']
            template_selected = int(self.choose_room_template(current_cell=this_cell))
            room_selected = self.stored_templates[template_selected]
            room_selected_walkable_area = room_selected['walkable_area']
            vert = int(room_selected_walkable_area[0]['vertical'])
            horz = int(room_selected_walkable_area[0]['horizontal'])

            logger.info('For cell {} the calculated x/y is {}/{}', this_cell, start_x, start_y)
            this_room = Rect(startx=start_x, starty=start_y, width=horz, height=vert)
            self.floorplan_create_room(room=this_room, floorplan_walkable_area=room_selected_walkable_area, rows=vert,
                                       columns=horz)

            logger.info('--- Current Cell is {}', this_cell)
            if this_cell > 17 and self.is_cell_populated(cell=this_cell - 17):
                logger.info('Cell {} above it is populated with template {}', this_cell - 17, self.stored_rooms[this_cell - 17].template)


        #  add walls around floor spaces
        _ = decorate_map.add_walls()

        return self.game_map

    def add_doors(self):
        north_of_this_cell = - self.cell_down_jump
        south_of_this_cell = self.cell_down_jump
        east_of_this_cell = 1
        west_of_this_cell = -1
        tile_type_door = 3
        for a in range(len(self.stored_rooms)):
            this_room = self.stored_rooms[a]
            if a == 0:
                # This is the starting room - decorate it with the player
                pass
            else:
                previous_cell = this_room.last_cell
                if previous_cell > 0:
                    logger.info('Room {} came from {}', this_room.id, previous_cell)
                    # if self.stored_rooms[this_room.id].template == Templates.room_square:
                    if (this_room.id - previous_cell) == north_of_this_cell:
                        cell_coords = self.cell_coords[this_room.id]
                        start_x = cell_coords['start_x']
                        start_y = cell_coords['start_y']
                        self.game_map.tiles[start_x + 4][start_y + 9].type_of_tile = tile_type_door

    def choose_room_template(self, current_cell):
        selected_template = 0
        if current_cell != self.starting_cell:
            # how many neighbours does this cell have
            neighbour_cell_count = self.count_neighbours_for_this_cell(this_cell=current_cell)
            if neighbour_cell_count == 1:
                # possibly reached a dead end cell
                pass
            chance_to_select_hallway = 110
            r = random.randrange(0, 100)
            if r < chance_to_select_hallway:
                # is it possible to choose a horizontal hallway
                east_of_this_cell = current_cell + 1
                west_of_this_cell = current_cell - 1
                east_cell_populated = self.is_cell_populated(cell=east_of_this_cell)
                west_cell_populated = self.is_cell_populated(cell=west_of_this_cell)
                if east_cell_populated > 0 and west_cell_populated > 0:
                    selected_template = FloormapTemplates.hallway_horizontal
                    logger.debug('Horizontal corridor should be created at {}', current_cell)
                # is it possible to choose a vertical hallway
                if selected_template == FloormapTemplates.room_square and current_cell > 17:
                    north_of_this_cell = current_cell + (- self.cell_down_jump)
                    south_of_this_cell = current_cell + self.cell_down_jump
                    north_cell_populated = self.is_cell_populated(cell=north_of_this_cell)
                    south_cell_populated = self.is_cell_populated(cell=south_of_this_cell)
                    if north_cell_populated > 0 and south_cell_populated > 0:
                        selected_template = FloormapTemplates.hallway_vertical
                        logger.debug('Vertical corridor should be created at {}', current_cell)

        self.stored_rooms[current_cell].template = selected_template
        logger.warning('Room {} is using template id {}', current_cell, self.stored_rooms[current_cell].template)
        return selected_template

    def is_cell_populated(self, cell):
        for i in range(len(self.original_placed_cells)):
            if self.original_placed_cells[i] == cell:
                return True
        return False

    def boi_placement(self):
        self.cells_to_be_checked.append(self.starting_cell)
        self.placed_cells.append(self.starting_cell)
        north_of_this_cell = - self.cell_down_jump
        south_of_this_cell = self.cell_down_jump
        east_of_this_cell = 1
        west_of_this_cell = -1

        while len(self.cells_to_be_checked) > 0:
            this_cell = self.cells_to_be_checked.pop(0)
            logger.info('Checking cell {}', this_cell)
            # check north of current cell
            if (this_cell + north_of_this_cell) > 2:
                self.boi_cell_placement_restrictions_check(this_cell=this_cell,
                                                           target_cell=this_cell + north_of_this_cell,
                                                           direction='north')
            else:
                logger.info('Cell {} failed basic grid placement to the north check', this_cell)

            # check east of the current cell
            if (this_cell + east_of_this_cell) < self.game_map.width - 1:
                self.boi_cell_placement_restrictions_check(this_cell=this_cell,
                                                           target_cell=this_cell + east_of_this_cell,
                                                           direction='east')
            else:
                logger.info('Cell {} failed basic grid placement to the east check', this_cell)

            # check south of the current cell
            if (this_cell + south_of_this_cell) < self.game_map.height:
                self.boi_cell_placement_restrictions_check(this_cell=this_cell,
                                                           target_cell=this_cell + south_of_this_cell,
                                                           direction='south')
            else:
                logger.info('Cell {} failed basic grid placement to the south check', this_cell)

            # check west of the current cell
            if this_cell + west_of_this_cell > 0:
                self.boi_cell_placement_restrictions_check(this_cell=this_cell,
                                                           target_cell=this_cell + west_of_this_cell,
                                                           direction='west')
            else:
                logger.info('Cell {} failed basic grid placement to the south check', this_cell)

    def boi_cell_placement_restrictions_check(self, this_cell, target_cell, direction):

        place_this_cell = True
        if len(self.placed_cells) > 0:
            # check if neighbour cell has already been selected
            if self.is_target_cell_populated(cell=target_cell):
                place_this_cell = False
            # have we reached our maximum number of cells
            if place_this_cell and len(self.placed_cells) > self.maximum_rooms:
                place_this_cell = False
                logger.info('Maximum rooms reached for cell {} whilst checking {}', this_cell, direction)
            # give up placement 50% of the time
            if place_this_cell and random.randrange(0, 100) > 75:
                place_this_cell = False
                logger.info('Randomly giving up placing cell {}', this_cell)
            # If the neighbour cell itself has more than one filled neighbour, give up.
            if place_this_cell:
                neighbour_cell_count = self.count_neighbours_for_this_cell(this_cell=this_cell)
                if neighbour_cell_count > 1:
                    place_this_cell = False
                    logger.info('Too many neighbours for {}', this_cell)

        if place_this_cell:
            self.cells_to_be_checked.append(target_cell)
            self.placed_cells.append(target_cell)
            self.stored_rooms[target_cell].last_cell = this_cell
            logger.info('Target cell {} populated, it came from cell {}', target_cell, this_cell)
        else:
            logger.info('From cell {} cannot place to the {} cell {}', this_cell, direction, target_cell)

    def count_neighbours_for_this_cell(self, this_cell):
        north_of_this_cell = - self.cell_down_jump
        south_of_this_cell = self.cell_down_jump
        east_of_this_cell = 1
        west_of_this_cell = -1
        neighbour_cell_count = 0
        look_north = this_cell + north_of_this_cell
        look_east = this_cell + east_of_this_cell
        look_south = this_cell + south_of_this_cell
        look_west = this_cell + west_of_this_cell
        if self.is_cell_populated(cell=look_north):
            neighbour_cell_count += 1
        if self.is_cell_populated(cell=look_east):
            neighbour_cell_count += 1
        if self.is_cell_populated(cell=look_south):
            neighbour_cell_count += 1
        if self.is_cell_populated(cell=look_west):
            neighbour_cell_count += 1

        return neighbour_cell_count
