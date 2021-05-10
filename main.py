import configUtilities
import renderGameMap
import roomsCorridorsMap
from bearlibterminal import terminal
from loguru import logger

from binary_space_partitionMap import BSPTree
from cellular_automataMap import CellularAutomata
from city_wallsMap import CityWalls
from dm_crypts import DMCrypts
from drunken_walkMap import DrunkardsWalk
from dungeon_utilities import TidyDungeon
from dungeonmanns import DungeonManns
from floorplanMap import Floorplan


def main():
    terminal.open()
    logger.info('Dungeon building has started')
    game_config = configUtilities.load_config()

    dungeon_width = configUtilities.get_config_value_as_integer(configfile=game_config, section='dungeon',
                                                                parameter='max_width')

    dungeon_height = configUtilities.get_config_value_as_integer(configfile=game_config, section='dungeon',
                                                                 parameter='max_height')

    game_map = None
    map_type = 3
    if map_type == 0:
        game_map = roomsCorridorsMap.RoomsCorridors.generate_rooms_and_corridors_map()

    if map_type == 1:
        bsp_map = BSPTree(map_width=dungeon_width, map_height=dungeon_height)
        game_map = bsp_map.generate_level()

    if map_type == 2:
        drunk_walk = DrunkardsWalk(map_width=dungeon_width, map_height=dungeon_height)
        game_map = drunk_walk.generate_level()

    if map_type == 3:
        cellular_map = CellularAutomata(map_width=dungeon_width, map_height=dungeon_height)
        game_map = cellular_map.generate_level()

    if map_type == 4:
        city_walls_map = CityWalls(map_width=dungeon_width, map_height=dungeon_height)
        game_map = city_walls_map.generate_level()

    if map_type == 5:
        floor_plan = Floorplan(map_width=dungeon_width, map_height=dungeon_height)
        game_map = floor_plan.generate_level()

    if map_type == 6:
        dungeon_build_failed = True
        dungeon_build_count = 1
        while dungeon_build_failed:
            dungeonman_map = DungeonManns(map_width=dungeon_width, map_height=dungeon_height)
            game_map, dungeon_build_failed = dungeonman_map.generate_level()
            if dungeon_build_failed:
                logger.warning('Dungeon build {} failed, restarting', dungeon_build_count)
                dungeon_build_count += 1

    if map_type == 7:
        dungeon_build_failed = True
        dungeon_build_count = 1
        while dungeon_build_failed:
            dungeonman_map = DMCrypts(map_width=dungeon_width, map_height=dungeon_height)
            game_map, dungeon_build_failed = dungeonman_map.generate_level()
            if dungeon_build_failed:
                logger.warning('Dungeon build {} failed, stopping', dungeon_build_count)
                dungeon_build_count += 1

    logger.info('Rendering the dungeon')
    renderGameMap.RenderUI.render_map(game_map=game_map)
    terminal.refresh()
    key_pressed = False

    while not key_pressed:
        # if terminal.has_input():
        key = terminal.read()
        if key == terminal.TK_ESCAPE:
            key_pressed = True
        if key == terminal.TK_M:

            logger.debug('Dungeon building has started')
            if map_type == 0:
                game_map = roomsCorridorsMap.RoomsCorridors.generate_rooms_and_corridors_map()
            if map_type == 1:
                bsp_map = BSPTree(map_width=dungeon_width, map_height=dungeon_height)
                game_map = bsp_map.generate_level()
            if map_type == 2:
                drunk_walk = DrunkardsWalk(map_width=dungeon_width, map_height=dungeon_height)
                game_map = drunk_walk.generate_level()

            if map_type == 3:
                cellular_map = CellularAutomata(map_width=dungeon_width, map_height=dungeon_height)
                game_map = cellular_map.generate_level()

            if map_type == 4:
                city_walls_map = CityWalls(map_width=dungeon_width, map_height=dungeon_height)
                game_map = city_walls_map.generate_level()

            if map_type == 5:
                floor_plan = Floorplan(map_width=dungeon_width, map_height=dungeon_height)
                game_map = floor_plan.generate_level()

            if map_type == 6:
                dungeonman_map = DungeonManns(map_width=dungeon_width, map_height=dungeon_height)
                dungeon_build_failed = True
                while dungeon_build_failed:
                    game_map, dungeon_build_failed = dungeonman_map.generate_level()

            if map_type == 7:
                dungeon_build_failed = True
                dungeon_build_count = 1
                while dungeon_build_failed:
                    dungeonman_map = DMCrypts(map_width=dungeon_width, map_height=dungeon_height)
                    game_map, dungeon_build_failed = dungeonman_map.generate_level()
                    if dungeon_build_failed:
                        logger.warning('Dungeon build {} failed, restarting', dungeon_build_count)
                        dungeon_build_count += 1

            dungeon_tidy = TidyDungeon(game_map=game_map)
            dungeon_tidy.erase_hanging_ddors()
            logger.debug('Rendering the dungeon')
            renderGameMap.RenderUI.render_map(game_map=game_map)
            terminal.refresh()


if __name__ == '__main__':
    main()

