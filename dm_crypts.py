import random
import cell
import json_utilities
from gameMap import GameMap
from dungeon_utilities import GenerateRandomSeed, TidyDungeon
from loguru import logger


class DungeonGrid:
    def __init__(self, width, height, cell_size):
        self.width = int(width / cell_size)
        self.height = int(height / cell_size)
        self.grid_cells = self.initialise_cells()

    def initialise_cells(self):
        cells = [[cell.Cell(template_id=-1) for _ in range(self.height)] for _ in range(self.width)]
        return cells


class DMCrypts:
    def __init__(self, map_width, map_height):
        self.game_map = GameMap(mapwidth=map_width, mapheight=map_height)
        self.room = None
        self.room_count = 0
        self.template_width = 9
        self.template_height = 9
        self.dungeon_grid = DungeonGrid(width=map_width, height=map_height, cell_size=self.template_height)
        # this is the number of rooms including the starter room
        self.room_goal_count = 30
        self.saved_build_seed = 0
        # self.saved_build_seed = 8386549001076506666
        # self.saved_build_seed = 5448451225749435205
        self.number_of_tries = 100
        self.templates_with_north_exit = []
        self.templates_with_east_exit = []
        self.templates_with_south_exit = []
        self.templates_with_west_exit = []
        self.stored_start_room_templates = self.load_dungeonmans_starter_rooms()
        self.placed_rooms = []
        self.candidates = []
        self.candidates_already_chosen = []
        self.generated_dungeon_seed = self.generate_random_seed()

    def generate_random_seed(self):
        dungeon_seed_object = GenerateRandomSeed(saved_build_seed=self.saved_build_seed)
        returned_seed = dungeon_seed_object.generate_random_seed()
        return returned_seed

    def generate_level(self):
        logger.info('Dungeon seed used {}', self.generated_dungeon_seed)
        self.initialise_dungeon_grid()
        self.load_dungeonmans_templates()
        self.place_starter_room()
        self.room_count += 1
        dungeon_build_failed = False
        available_cells = True

        while (self.room_count < self.room_goal_count) and available_cells:
            room_placed = False
            # a candidate is a dungeon cell that has a room already placed there
            self.calculate_cells_with_rooms()
            number_of_cells_with_rooms = len(self.candidates)

            logger.info('Number of grid cells with rooms {}', number_of_cells_with_rooms)

            if number_of_cells_with_rooms > 0:
                candidate_dungeon_cell = self.pick_random_dungeon_cell()

                while number_of_cells_with_rooms > 0 and not room_placed:
                    logger.info('Random candidate id {} - coords are {}', self.room_count, candidate_dungeon_cell)

                    # identify available exits from this cell
                    cell_x = candidate_dungeon_cell[0]
                    cell_y = candidate_dungeon_cell[1]

                    # grab the exits from the selected cell
                    cell_exits = self.dungeon_grid.grid_cells[cell_x][cell_y].available_exits
                    logger.info('Available exits from this cell are {}', cell_exits)

                    # choose a random template that matches the available cell exits
                    available_template = self.pick_random_template(available_exits=cell_exits)

                    if cell_exits != '000':
                        template_can_be_placed, selected_cell_coords = self.confirm_if_template_can_be_placed(
                            location=candidate_dungeon_cell, template_information=available_template)
                        if template_can_be_placed:
                            self.actually_place_the_room(grid_location=selected_cell_coords,
                                                         template_information=available_template,
                                                         room_id=self.room_count)
                            room_placed = True
                            self.room_count += 1
                            self.placed_rooms.append((selected_cell_coords, available_template['name']))
                        else:
                            cand_list = self.candidates
                            logger.debug('Failed to place template - debugging stuff')
                            logger.info('Number of candidate cells (before manipulation) is {}', len(cand_list))
                            cand_list.remove((cell_x, cell_y))
                            self.candidates = cand_list
                            number_of_cells_with_rooms -= 1
                            if number_of_cells_with_rooms > 0:
                                logger.info('Number of cells with rooms (after manipulation) is {}',
                                            number_of_cells_with_rooms)
                                candidate_dungeon_cell = self.pick_random_dungeon_cell()
                            else:
                                logger.debug('Number of available cells is {}', number_of_cells_with_rooms)
                    else:
                        logger.info('No available exits from cell {}', candidate_dungeon_cell)
                        cand_list = self.candidates
                        cand_list.pop(candidate_dungeon_cell)
                        self.candidates = cand_list

                if not room_placed:
                    logger.warning('No suitable room candidates were found!!')
                    dungeon_build_failed = True
                    available_cells = False
            else:
                available_cells = False
                break

        if not available_cells:
            logger.debug('Dungeon build ended because there are no available cells')

        logger.info('Dungeon seed used {}', self.generated_dungeon_seed)
        logger.info('Number of available candidates are {}', len(self.candidates))
        decorate_map = TidyDungeon(game_map=self.game_map)
        decorate_map.add_walls()
        decorate_map.erase_hanging_ddors()
        return self.game_map, dungeon_build_failed

    def initialise_dungeon_grid(self):
        max_cells_across = self.dungeon_grid.width
        max_cells_down = self.dungeon_grid.height
        for x in range(max_cells_across):
            if x == 0:
                calc_x = 1
            else:
                x_factor = self.template_width - 1
                calc_x = x * x_factor
            for y in range(max_cells_down):
                if y == 0:
                    calc_y = 1
                else:
                    y_factor = self.template_height - 1
                    calc_y = y * y_factor
                self.dungeon_grid.grid_cells[x][y].startx = calc_x
                self.dungeon_grid.grid_cells[x][y].starty = calc_y

    def confirm_if_template_can_be_placed(self, location, template_information):
        template_can_been_placed = True
        selected_cell_coords = None

        # convert map coords to grid cell
        cell_x = location[0]
        cell_y = location[1]

        logger.info('Working with template:{}', template_information['name'])
        logger.info('Available exits for this template:{}', template_information['layout'][0]['exits'])

        # would the candidate room be placed outside the game map
        if cell_x - 1 < 1 or cell_x > self.dungeon_grid.width:
            template_can_been_placed = False

        if cell_y < 1 or cell_y > self.dungeon_grid.height:
            template_can_been_placed = False

        # is there any space around the current cell
        cell_space_available, available_cells = self.check_if_space_around_current_cell(cell_x=cell_x, cell_y=cell_y,
                                                                                        template_information=template_information)

        if cell_space_available:
            if len(available_cells) > 0:
                if len(available_cells) == 1:
                    random_cell = 0
                else:
                    random_cell = random.randrange(len(available_cells))

                selected_cell_coords = available_cells[random_cell]
        else:
            template_can_been_placed = False
            logger.info('No space around target cell {}/{} for template', cell_x, cell_y, template_information['name'])

        logger.info('Can template be placed {}', cell_space_available)
        return template_can_been_placed, selected_cell_coords

    def check_if_space_around_current_cell(self, cell_x, cell_y, template_information):
        cell_space_available = False
        available_cells = []
        cell_x_min = 2
        cell_x_max = self.dungeon_grid.width - 1
        cell_y_min = 2
        cell_y_max = self.dungeon_grid.height - 1
        template_exits_string = template_information['layout'][0]['exits']
        cell_exits_string = self.dungeon_grid.grid_cells[cell_x][cell_y].available_exits

        # check north of current cell
        if cell_y > cell_y_min and cell_exits_string[0] == '1' and self.dungeon_grid.grid_cells[cell_x][
            cell_y - 1].room_id == - 1 and template_exits_string[2] == '1':
            cell_space_available = True
            available_cells.append((cell_x, cell_y - 1))

        # check east of current cell
        if cell_x < cell_x_max and cell_exits_string[1] == '1' and self.dungeon_grid.grid_cells[cell_x + 1][
            cell_y].room_id == - 1 and template_exits_string[3] == '1':
            cell_space_available = True
            available_cells.append((cell_x + 1, cell_y))

        # check south of current cell
        if cell_y < cell_y_max and cell_exits_string[2] == '1' and self.dungeon_grid.grid_cells[cell_x][
            cell_y + 1].room_id == - 1 and template_exits_string[0] == '1':
            cell_space_available = True
            available_cells.append((cell_x, cell_y + 1))

        # check west of current cell
        if cell_x > cell_x_min and cell_exits_string[3] == '1' and self.dungeon_grid.grid_cells[cell_x - 1][
            cell_y].room_id == - 1 and template_exits_string[2] == '1':
            cell_space_available = True
            available_cells.append((cell_x - 1, cell_y))

        return cell_space_available, available_cells

    def dump_dungeon_info(self):
        logger.debug('*** STARTING PLACED ROOMS DUMP ***')
        logger.info('Total room count {}', self.room_count)
        logger.info('Total rooms placed {}', len(self.placed_rooms))

        for a in range(self.room_goal_count):
            room = self.placed_rooms[a]
            template_name = room[1]
            location = room[0]
            gx = location[0]
            gy = location[1]
            logger.info('Room:{} template name:{} grid x/y {}/{}', a, template_name, gx, gy)

    def load_dungeonmans_starter_rooms(self):
        filename = 'dm_crypts_starter_rooms.json'
        template_list = json_utilities.read_json_file(filename)

        return template_list

    def load_dungeonmans_templates(self):
        filename = 'dm_crypts_rooms.json'
        template_list = json_utilities.read_json_file(filename)
        for template in template_list:
            template_exits = template['layout'][0]['exits']
            if template_exits[0] == "1":
                self.templates_with_north_exit.append(template)
            if template_exits[1] == "1":
                self.templates_with_east_exit.append(template)
            if template_exits[2] == "1":
                self.templates_with_south_exit.append(template)
            if template_exits[3] == "1":
                self.templates_with_west_exit.append(template)

        return template_list

    def place_starter_room(self):
        max_x_cells = self.dungeon_grid.width
        max_y_cells = self.dungeon_grid.height

        # for now, hardcode which starter room template to use
        this_room = 0

        # choose grid cell to place starter room
        grid_cell_x = random.randrange(3, max_x_cells)
        grid_cell_y = random.randrange(3, max_y_cells)
        grid_x = grid_cell_x
        grid_y = grid_cell_y

        self.actually_place_the_room(grid_location=(grid_x, grid_y),
                                     template_information=self.stored_start_room_templates[this_room], room_id=1)
        self.placed_rooms.append(((grid_x, grid_y), self.stored_start_room_templates[this_room]['name']))

    def calculate_cells_with_rooms(self):
        # this cycles through the dungeon grid cells and looks for any cells that contain
        # a template, aka a room already exists there.

        self.candidates = []

        max_x_cells = self.dungeon_grid.width
        max_y_cells = self.dungeon_grid.height

        for x in range(max_x_cells):
            for y in range(max_y_cells):
                if self.dungeon_grid.grid_cells[x][y].room_id > 0:
                    self.candidates.append((x, y))

    def pick_random_dungeon_cell(self):
        number_of_candidates = len(self.candidates)
        selected_candidate = random.randrange(number_of_candidates)
        return self.candidates[selected_candidate]

    def pick_random_template(self, available_exits):
        # currently this function creates a list of ALL templates that match
        # ALL available exits from the cell. IT then picks a random list AND then
        # picks a random template
        #
        # What I'm thinking is PICK a random cell exit
        # THEN create a list of available templates for that cell exit
        # THEN pick a random template
        #
        selected_exit = False
        e = 0
        while not selected_exit:
            e = random.randrange(0, 4)
            if available_exits[e] == '1':
                selected_exit = True

        available_templates = []
        if e == 0:
            available_templates = self.templates_with_south_exit
            logger.info('Compiling a list of templates that have exits to the south')
        if e == 2:
            available_templates = self.templates_with_north_exit
            logger.info('Compiling a list of templates that have exits to the north')
        if e == 1:
            available_templates = self.templates_with_west_exit
            logger.info('Compiling a list of templates that have exits to the west')
        if e == 3:
            available_templates = self.templates_with_east_exit
            logger.info('Compiling a list of templates that have exits to the east')

        # we now have a list of lists holding available templates from this cell
        # now choose from that available list
        # if len(available_templates) == 1:
        #     template_list_id = 0
        # else:
        # template_list_id = random.randrange(len(available_templates))
        # template_list = available_templates[template_list_id]
        # template_id = random.randrange(len(template_list))

        logger.info('Number of templates available for selection is {}', len(available_templates))
        template_id = random.randrange(len(available_templates))
        logger.info('Selected template id is {} and name is {}', template_id, available_templates[template_id]['name'])

        available_template = available_templates[template_id]

        return available_template

    def actually_place_the_room(self, grid_location, template_information, room_id):
        tile_type_floor = 1
        tile_type_door = 3
        tile_type_wall = 5
        rc = 1
        yz = 0
        room_layout = template_information['layout']
        room_exits = template_information['layout'][0]['exits']
        grid_cell_x = grid_location[0]
        grid_cell_y = grid_location[1]
        map_x = self.dungeon_grid.grid_cells[grid_cell_x][grid_cell_y].startx
        map_y = self.dungeon_grid.grid_cells[grid_cell_x][grid_cell_y].starty
        rows = self.template_width
        columns = self.template_height

        logger.info('Placing room at grid cell {}/{}', grid_cell_x, grid_cell_y)
        logger.info('Placing room at map coords {}/{}', map_x, map_y)

        if room_exits[0] == "1":
            str1 = self.dungeon_grid.grid_cells[grid_cell_x][grid_cell_y].available_exits
            str2 = str1[:0] + '1' + str1[1:]
            self.dungeon_grid.grid_cells[grid_cell_x][grid_cell_y].available_exits = str2
        if room_exits[1] == "1":
            str1 = self.dungeon_grid.grid_cells[grid_cell_x][grid_cell_y].available_exits
            str2 = str1[:1] + '1' + str1[2:]
            self.dungeon_grid.grid_cells[grid_cell_x][grid_cell_y].available_exits = str2
        if room_exits[2] == "1":
            str1 = self.dungeon_grid.grid_cells[grid_cell_x][grid_cell_y].available_exits
            str2 = str1[:2] + '1' + str1[3:]
            self.dungeon_grid.grid_cells[grid_cell_x][grid_cell_y].available_exits = str2
        if room_exits[3] == "1":
            str1 = self.dungeon_grid.grid_cells[grid_cell_x][grid_cell_y].available_exits
            str2 = str1[:3] + '1'
            self.dungeon_grid.grid_cells[grid_cell_x][grid_cell_y].available_exits = str2

        grid_x = grid_cell_x
        grid_y = grid_cell_y

        self.dungeon_grid.grid_cells[grid_x][grid_y].room_id = room_id

        for _ in range(columns):
            xz = 0
            this_row = "row_" + str(rc)
            row_data = room_layout[0][this_row]
            for _ in range(rows):
                this_row_data = row_data[xz]
                if this_row_data == '.':
                    self.game_map.tiles[map_x + xz][map_y + yz].type_of_tile = tile_type_floor
                if this_row_data == '+':
                    self.game_map.tiles[map_x + xz][map_y + yz].type_of_tile = tile_type_door
                if this_row_data == '#':
                    self.game_map.tiles[map_x + xz][map_y + yz].type_of_tile = tile_type_wall
                xz += 1
            yz += 1
            rc += 1
