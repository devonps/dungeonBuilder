import random
from enum import IntEnum
import json_utilities
from gameMap import GameMap
from dungeon_utilities import Rect, GenerateRandomSeed, TidyDungeon
from loguru import logger


class DungeonmansTemplates(IntEnum):
    start_room = 0
    square_standard = 1


class DungeonmansPlacedRooms:
    def __init__(self, startx, starty, width, height, template):
        self.startx = startx
        self.starty = starty
        self.width = width
        self.height = height
        self.template = template


class DungeonManns:
    def __init__(self, map_width, map_height):
        self.game_map = GameMap(mapwidth=map_width, mapheight=map_height)
        self.room = None
        self.room_count = 0
        # this is the number of rooms including the starter room
        self.room_goal_count = 15
        self.saved_build_seed = 0
        # self.saved_build_seed = 115594251908178054
        # self.saved_build_seed = 7787385706151512394
        self.number_of_tries = 100
        self.stored_templates = self.load_dungeonmans_templates(filename='dungeonmans_templates.json')
        self.stored_start_room_templates = self.load_dungeonmans_templates(
            filename='dungeonmans_start_room_templates.json')
        self.stored_hallways = self.load_dungeonmans_templates(filename='dungeonmans_hallway_templates.json')
        self.placed_rooms = []
        self.candidates = []
        self.candidates_already_chosen = []
        self.generated_dungeon_seed = self.generate_random_seed()

    def generate_random_seed(self):
        dungeon_seed_object = GenerateRandomSeed(saved_build_seed=self.saved_build_seed)
        returned_seed = dungeon_seed_object.generate_random_seed()
        logger.info('Dungeon Build seed {}', returned_seed)
        return returned_seed

    def generate_level(self):
        number_attempts = 0
        tile_type_door = 3
        decorate_map = TidyDungeon(game_map=self.game_map)
        self.place_starter_room()
        #  add walls around floor spaces
        _ = decorate_map.add_walls()
        logger.info('walls added for room {}', self.room_count)
        self.room_count += 1
        dungeon_build_failed = False

        while (self.room_count < self.room_goal_count) & (number_attempts < self.number_of_tries):
            number_attempts += 1
            room_placed = False
            #  add every wall tile with 2 adjacant wall tiles on the same axis and one side exposed to unused space
            #  repeat this for every wall in every room
            self.recalculate_candidates()

            logger.info('Number of candidates is {}', len(self.candidates))
            logger.info('Count of rooms placed is {}', self.room_count)
            inner_room_count = 0
            while not room_placed and inner_room_count < 30:
                inner_room_count += 1
                logger.info('--- Inner Room Count {}', inner_room_count)
                candidate_coords_chosen = self.pick_random_candidate()
                logger.info('Random candidate id {} - coords are {}', candidate_coords_chosen,
                            self.candidates[candidate_coords_chosen])

                selected_template_to_place, template_type = self.pick_random_template(
                    coordinate_set=candidate_coords_chosen)
                logger.info('Room template {} has been selected', selected_template_to_place)
                logger.info('Template type is {}', template_type)
                if template_type == 'hallway':
                    template_info = self.stored_hallways[selected_template_to_place]
                    template_name = template_info['name']
                    logger.info('and to confirm the hallway template name is {}', template_name)
                room_placed = self.check_if_candidate_room_can_be_placed(candidate_room=selected_template_to_place,
                                                                         location=candidate_coords_chosen,
                                                                         template_type=template_type)

                if room_placed:
                    xpos = self.candidates[candidate_coords_chosen][0]
                    ypos = self.candidates[candidate_coords_chosen][1]
                    self.game_map.tiles[xpos][ypos].type_of_tile = tile_type_door
                    self.candidates_already_chosen.append(self.candidates[candidate_coords_chosen])
                    #  add walls around floor spaces
                    _ = decorate_map.add_walls()
                    logger.info('walls added for room {}', self.room_count)
                    self.room_count += 1
                logger.info('Attempt {} completed', number_attempts)
        # self.dump_dungeon_info()
        if number_attempts >= self.number_of_tries:
            dungeon_build_failed = True
        else:
            self.tidy_dungeon()
        logger.info('Dungeon seed used {}', self.generated_dungeon_seed)
        return self.game_map, dungeon_build_failed

    def tidy_dungeon(self):
        # The idea is for this method to make the dungeon a look little better
        tile_type_wall = 5
        tile_type_floor = 1
        tile_type_obstacle = 6

        double_wall_horizontal_list = []
        double_wall_vertical_list = []
        end_of_halway_list = []

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

                if tile == tile_type_wall:
                    # checks for hanging wall tile on the horizontal axis of the target tile
                    if north_of_tile == tile_type_obstacle and east_of_tile == tile_type_obstacle and south_of_tile == tile_type_obstacle:
                        if west_of_tile == tile_type_floor:
                            self.game_map.tiles[x - 1][y].type_of_tile = tile_type_wall
                            self.game_map.tiles[x][y].type_of_tile = tile_type_obstacle
                    # checks for hanging wall to the west of the target tile
                    if north_of_tile == tile_type_obstacle and west_of_tile == tile_type_obstacle and south_of_tile == tile_type_obstacle:
                        if east_of_tile == tile_type_floor:
                            self.game_map.tiles[x + 1][y].type_of_tile = tile_type_wall
                            self.game_map.tiles[x][y].type_of_tile = tile_type_obstacle

                    # checks for hanging wall tile on the vertical axis of the target tile

                    # checks for hanging wall to the north of the target tile
                    if north_of_tile == tile_type_obstacle and east_of_tile == tile_type_obstacle and west_of_tile == tile_type_obstacle:
                        if south_of_tile == tile_type_floor:
                            self.game_map.tiles[x][y + 1].type_of_tile = tile_type_wall
                            self.game_map.tiles[x][y].type_of_tile = tile_type_obstacle

                    # checks for hanging wall to the south of the target tile
                    if east_of_tile == tile_type_obstacle and west_of_tile == tile_type_obstacle and south_of_tile == tile_type_obstacle:
                        if north_of_tile == tile_type_floor:
                            self.game_map.tiles[x][y - 1].type_of_tile = tile_type_wall
                            self.game_map.tiles[x][y].type_of_tile = tile_type_obstacle

                    # looks for 'double walls' checks tiles east of target tile
                    if east_of_tile == tile_type_wall and west_of_tile == tile_type_floor:
                        if north_of_tile == tile_type_wall and south_of_tile == tile_type_wall:
                            if north_east_of_tile == tile_type_wall and south_east_of_tile == tile_type_wall:
                                double_wall = (x, y)
                                double_wall_horizontal_list.append(double_wall)

                    # looks for 'double walls' to the south of target tile
                    if south_of_tile == tile_type_wall and north_of_tile == tile_type_floor:
                        if east_of_tile == tile_type_wall and west_of_tile == tile_type_wall:
                            if south_east_of_tile == tile_type_wall and south_west_of_tile == tile_type_wall:
                                double_wall = (x, y)
                                double_wall_vertical_list.append(double_wall)

                    # look for the 'end of a hallway' that backs on to another room and possibly open it up
                    if north_of_tile == tile_type_wall and south_of_tile == tile_type_wall and north_east_of_tile == tile_type_wall and south_east_of_tile == tile_type_wall:
                        if west_of_tile == tile_type_floor and east_of_tile == tile_type_floor:
                            end_hallway = (x, y)
                            end_of_halway_list.append(end_hallway)

        # for all end of hallways there's a 30% chance of them being opened up
        for z in end_of_halway_list:
            r = random.randrange(0, 100)
            logger.info('[EoH] Looking at {} random point is {}', z, r)
            if r < 50:
                x = z[0]
                y = z[1]
                self.game_map.tiles[x][y].type_of_tile = tile_type_floor

        # For all vertical double walls there's a 30% chance of them being opened up
        for z in double_wall_horizontal_list:
            r = random.randrange(0, 100)
            logger.info('[hor]Looking at {} random point is {}', z, r)
            if r < 30:
                x = z[0]
                y = z[1]
                self.game_map.tiles[x][y].type_of_tile = tile_type_floor
                self.game_map.tiles[x + 1][y].type_of_tile = tile_type_floor

        # For all horizontal double walls there's a 30% chance of them being opened up
        for z in double_wall_vertical_list:
            r = random.randrange(0, 100)
            logger.info('[vert] Looking at {} random point is {}', z, r)
            if r < 30:
                x = z[0]
                y = z[1]
                self.game_map.tiles[x][y].type_of_tile = tile_type_floor
                self.game_map.tiles[x][y + 1].type_of_tile = tile_type_floor


    def dump_dungeon_info(self):
        logger.debug('*** STARTING PLACED ROOMS DUMP ***')
        logger.info('Total room count {}', self.room_count)
        logger.info('Total rooms placed {}', len(self.placed_rooms))
        logger.info('Total candidates available {}', len(self.candidates))

        for a in range(self.room_goal_count):
            room = self.placed_rooms[a]
            logger.info('Room {}', a)
            logger.info('Room template used:{}', room.template)
            logger.info('Room template start x/y:{}/{}', room.startx, room.starty)
            logger.info('Room template width/height:{}/{}', room.width, room.height)

        for b in range(len(self.candidates_already_chosen)):
            logger.info('Candidate {}, stored {}', b, self.candidates_already_chosen[b])

    def load_dungeonmans_templates(self, filename):
        template_list = json_utilities.read_json_file(filename)
        return template_list

    def place_starter_room(self):
        this_room = int(DungeonmansTemplates.start_room)
        room_selected = self.stored_start_room_templates[this_room]
        room_width = int(self.stored_start_room_templates[this_room]['dimensions'][0]['width'])
        room_height = int(self.stored_start_room_templates[this_room]['dimensions'][0]['height'])
        room_layout = self.stored_start_room_templates[this_room]['layout']

        min_x = room_width
        max_x = (self.game_map.width - room_width) + 2

        min_y = room_height
        max_y = (self.game_map.height - room_height) - 2

        map_x = random.randrange(min_x, max_x)
        map_y = random.randrange(min_y, max_y)
        logger.info('Starting Room placed at {}/{}', map_x, map_y)
        room_as_rectangle = Rect(startx=map_x, starty=map_y, width=room_width, height=room_height)
        self.actually_place_the_room(room_data=room_as_rectangle, location=(map_x, map_y),
                                     template_information=room_layout,
                                     rows=room_width, columns=room_height, room_id=self.room_count)

        placed_room = DungeonmansPlacedRooms(startx=map_x, starty=map_y, width=room_width, height=room_height,
                                             template=this_room)
        logger.info('Starting Room info')
        logger.info('Starting Room start_x/start_y {}/{}', placed_room.startx, placed_room.starty)
        logger.info('Starting Room width/height {}/{}', placed_room.width, placed_room.height)
        self.placed_rooms.append(placed_room)

    def recalculate_candidates(self):
        tile_type_wall = 5
        self.candidates = []
        # check vertical candidates
        for x in range(self.game_map.width):
            for y in range(self.game_map.height):
                tile = self.game_map.tiles[x][y].type_of_tile
                if tile == tile_type_wall:
                    valid_candidate, axis_side = self.is_this_a_valid_candidate(x=x, y=y, direction='vertical')
                    if valid_candidate:
                        if self.game_map.tiles[x][y - 1].type_of_tile == tile_type_wall and self.game_map.tiles[x][y + 1].type_of_tile == tile_type_wall:
                            self.candidates.append((x, y, 'vertical', axis_side))
        # check horizontal candidates
        for y in range(self.game_map.height - 2):
            for x in range(self.game_map.width - 2):
                tile = self.game_map.tiles[x][y].type_of_tile
                if tile == tile_type_wall:
                    valid_candidate, axis_side = self.is_this_a_valid_candidate(x=x, y=y, direction='horizontal')
                    if valid_candidate:
                        if self.game_map.tiles[x - 1][y].type_of_tile == tile_type_wall and self.game_map.tiles[x + 1][y].type_of_tile == tile_type_wall:
                            self.candidates.append((x, y, 'horizontal', axis_side))

    def is_this_a_valid_candidate(self, x, y, direction):
        tile_type_obstacle = 6
        tile_type_floor = 1
        valid_candidate = False
        axis_side = '-none'
        if direction == 'vertical':
            # check if the left is unused and the right is a placed room
            if self.game_map.tiles[x - 1][y].type_of_tile == tile_type_obstacle and self.game_map.tiles[x + 1][y].type_of_tile == tile_type_floor:
                valid_candidate = True
                axis_side = 'left'
            # check if the right is unused and the left is a placed room
            if self.game_map.tiles[x + 1][y].type_of_tile == tile_type_obstacle and self.game_map.tiles[x - 1][
                y].type_of_tile == tile_type_floor:
                valid_candidate = True
                axis_side = 'right'

        if direction == 'horizontal':
            # check if above is unused and below is a placed room
            if self.game_map.tiles[x][y - 1].type_of_tile == tile_type_obstacle and self.game_map.tiles[x][y + 1].type_of_tile == tile_type_floor:
                valid_candidate = True
                axis_side = 'top'
            # check if below is unused and above is a placed room
            if self.game_map.tiles[x][y + 1].type_of_tile == tile_type_obstacle and self.game_map.tiles[x][
                y + 1].type_of_tile == tile_type_floor:
                valid_candidate = True
                axis_side = 'bottom'

        return valid_candidate, axis_side

    def pick_random_candidate(self):
        number_of_candidates = len(self.candidates)
        selected_candidate = random.randrange(number_of_candidates)
        return selected_candidate

    def pick_random_template(self, coordinate_set):
        # want to choose between hallways and rooms
        cand_direction = self.candidates[coordinate_set][2]
        template_type = 'room'
        template_choice = random.randrange(0, 100)

        if template_choice > 85:
            # hallway chosen
            template_type = 'hallway'
            if cand_direction == 'vertical':
                selected_room_id = 1  # use a horizontal hallway
                logger.info('Horizontal hallway template selected')
            else:
                selected_room_id = 0  # use a vertical hallway
                logger.info('Vertical hallway template selected')
        else:
            # room chosen
            number_of_rooms_to_choose_from = len(self.stored_templates)
            selected_room_id = -99
            chosen_room = False
            while not chosen_room:
                selected_room_id = random.randrange(number_of_rooms_to_choose_from)
                if selected_room_id != -99:
                    chosen_room = True

        return selected_room_id, template_type

    def check_if_candidate_room_can_be_placed(self, candidate_room, location, template_type):
        # candidate_room is an integer that points to the stored template to place on the map
        # location holds a tuple that points to a possible door/link from a placed room to the candidate room
        room_has_been_placed = False
        candidate_door_xpos = self.candidates[location][0]
        candidate_door_ypos = self.candidates[location][1]
        axis = self.candidates[location][2]
        axis_side = self.candidates[location][3]
        if template_type == 'room':
            template_room_data = self.stored_templates[candidate_room]
            room_layout = self.stored_templates[candidate_room]['layout']
        else:
            template_room_data = self.stored_hallways[candidate_room]
            room_layout = self.stored_hallways[candidate_room]['layout']

        cand_width = template_room_data['dimensions'][0]['width']
        cand_height = template_room_data['dimensions'][0]['height']
        cand_start_x = 0
        cand_start_y = 0

        if axis == 'vertical':
            if axis_side == 'left':
                # this 'pushes' the start X of the candidate room to the left of the proposed door X position
                cand_start_x = candidate_door_xpos - cand_width
            else:
                # this 'pushes' the start X of the candidate room to the right of the proposed door X position
                cand_start_x = candidate_door_xpos + 1
            # in effect this 'pushes' the start of the candidate room above the proposed door Y position
            cand_start_y = candidate_door_ypos - (int(cand_height / 2))

        if axis == 'horizontal':
            if axis_side == 'top':
                cand_start_y = (candidate_door_ypos - cand_height)
                cand_start_x = candidate_door_xpos - (int(cand_width / 2)) + 1
            else:
                cand_start_y = (candidate_door_ypos + cand_height)
                cand_start_x = candidate_door_xpos - (int(cand_width / 2))
            if template_type == 'hallway':
                cand_start_x -= 1

        # would the candidate room be placed outside the game map
        cand_rect = Rect(startx=cand_start_x, starty=cand_start_y, width=cand_width, height=cand_height)
        outside_game_map = Rect.outside_of_game_map(cand_rect, game_map=self.game_map)
        if outside_game_map:
            logger.debug('Candidate room would be outside of game map')
        else:
            # would the candidate room intersect an already placed room - for now do nothing
            room_intersects_with_another_feature = Rect.is_there_a_map_tile_inside_this_rectangle(cand_rect,
                                                                                                  self.game_map)
            if not room_intersects_with_another_feature:
                width = template_room_data['dimensions'][0]['width']
                height = template_room_data['dimensions'][0]['height']
                self.actually_place_the_room(room_data=cand_rect, location=(candidate_door_xpos, candidate_door_ypos),
                                             template_information=room_layout, rows=width, columns=height,
                                             room_id=self.room_count)
                room_has_been_placed = True
                room_info = DungeonmansPlacedRooms(startx=cand_start_x, starty=cand_start_y, width=cand_width,
                                                   height=cand_height, template=1)
                self.placed_rooms.append(room_info)
            else:
                logger.debug('Candidate room could not be legally placed')
                # delete these candidate coords so they can't be chosen during this round.
                self.candidates.pop(location)

        return room_has_been_placed

    def actually_place_the_room(self, room_data, location, template_information, rows, columns, room_id):
        tile_type_floor = 1
        tile_type_door = 3
        rc = 1
        yz = 0
        door_xpos = location[0]
        door_ypos = location[1]
        logger.info('Placing room {} at {}/{}', room_id, door_xpos, door_ypos)
        for _ in range(columns):
            xz = 0
            this_row = "row_" + str(rc)
            row_data = template_information[0][this_row]
            for _ in range(rows):
                this_row_data = row_data[xz]
                if this_row_data == '.':
                    self.game_map.tiles[room_data.x1 + xz][room_data.y1 + yz].type_of_tile = tile_type_floor
                if this_row_data == '+':
                    self.game_map.tiles[room_data.x1 + xz][room_data.y1 + yz].type_of_tile = tile_type_door

                xz += 1
            yz += 1
            rc += 1
        return True
