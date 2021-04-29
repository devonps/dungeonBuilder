import configUtilities
from bearlibterminal import terminal


class RenderUI:

    @staticmethod
    def render_map(game_map):
        game_config = configUtilities.load_config()
        tile_type_wall = configUtilities.get_config_value_as_integer(configfile=game_config, section='dungeon',
                                                                     parameter='TILE_TYPE_WALL')
        tile_type_door = configUtilities.get_config_value_as_integer(configfile=game_config, section='dungeon',
                                                                     parameter='TILE_TYPE_DOOR')
        tile_type_floor = configUtilities.get_config_value_as_integer(configfile=game_config, section='dungeon',
                                                                      parameter='TILE_TYPE_FLOOR')
        tile_type_obstacle = configUtilities.get_config_value_as_integer(configfile=game_config, section='dungeon',
                                                                      parameter='TILE_TYPE_OBSTACLE')
        dungeon_width = configUtilities.get_config_value_as_integer(configfile=game_config, section='dungeon',
                                                                    parameter='max_width')

        dungeon_height = configUtilities.get_config_value_as_integer(configfile=game_config, section='dungeon',
                                                                     parameter='max_height')
        config_prefix = 'ASCII_'
        config_prefix_wall = config_prefix + 'WALL_'
        config_prefix_floor = config_prefix + 'FLOOR_'
        config_prefix_door = config_prefix + 'DOOR_'

        screen_offset_x = 1
        screen_offset_y = 1

        for scr_pos_y in range(dungeon_height):
            for scr_pos_x in range(dungeon_width):
                tile = game_map.tiles[scr_pos_x][scr_pos_y].type_of_tile

                if tile == tile_type_floor:
                    colour_code = "[color=DUNGEON_FLOOR]"
                    char_to_display = "0x" + configUtilities.get_config_value_as_string(configfile=game_config,
                                                                                  section='dungeon',
                                                                                  parameter=config_prefix_floor + '0')

                if tile == tile_type_wall:
                    char_to_display = "0x" + configUtilities.get_config_value_as_string(configfile=game_config,
                                                                                        section='dungeon',
                                                                                        parameter=config_prefix_wall + '0')
                    colour_code = "[color=CORRIDOR_WALLS]"

                if tile == tile_type_door:
                    char_to_display = "0x" + configUtilities.get_config_value_as_string(configfile=game_config,
                                                                                        section='dungeon',
                                                                                        parameter=config_prefix_door + '0')
                    colour_code = "[color=DUNGEON_DOOR]"

                if tile == tile_type_obstacle:
                    char_to_display = "0x" + configUtilities.get_config_value_as_string(configfile=game_config,
                                                                                        section='dungeon',
                                                                                        parameter=config_prefix_wall + '0')
                    colour_code = "[color=INITIAL_DUNGEON_WALLS]"

                RenderUI.print_char_to_the_screen(tile=tile, colour_code=colour_code,
                                                  char_to_display=char_to_display,
                                                  scr_pos_x=scr_pos_x + screen_offset_x,
                                                  scr_pos_y=scr_pos_y + screen_offset_y)


    @staticmethod
    def print_char_to_the_screen(tile, colour_code, char_to_display, scr_pos_x, scr_pos_y):
        if tile > 0:
            string_to_print = colour_code + '[' + char_to_display + ']'
            terminal.printf(x=scr_pos_x, y=scr_pos_y, s=string_to_print)