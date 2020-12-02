import pygame
import level
import collision
import character.player as player
import json
import hud.menu as _menu
import time

screen = None

CASE_SIZE = 32
SCREEN_SIZE = (1600, 900)
SURFACE_SIZE = (1060, 600)

DIRECTION = ["top", "left", "down", "right"]

game_instance = None

FONT_16: pygame.font.Font = None
FONT_24: pygame.font.Font = None
FONT_SIZE_16 = (0, 0)
FONT_SIZE_24 = (0, 0)

came_scroll = (0, 0)

class Cache(object):

    def __init__(self):
        self.cache = {}

    def clear(self):
        self.cache.clear()

    def put(self, key, value):
        self.cache[key] = value

    def have(self, key):
        return key in self.cache

    def get(self, key):
        if key in self.cache:
            return self.cache[key]
        else:
            raise KeyError("No value load for key {}".format(key))


IMAGE_CACHE = Cache()
DISPLAYER_CACHE = Cache()

class Game(object):

    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Test Pokemon")

        # asset load
        global FONT_16, FONT_SIZE_16, FONT_24, FONT_SIZE_24
        FONT_16 = pygame.font.Font("assets/font/MyFont-Regular.otf", 16)
        FONT_24 = pygame.font.Font("assets/font/MyFont-Regular.otf", 24)
        FONT_SIZE_16 = FONT_16.size('X')
        FONT_SIZE_24 = FONT_16.size('X')
        self.lang = {}
        self.save_name = ""
        self._save = {}
        self.load_save("save")
        self.load_lang("en")
        player.load_hud_item()
        # ============

        global game_instance
        game_instance = self
        self.screen = pygame.display.set_mode(SCREEN_SIZE)
        self.display = pygame.Surface(SURFACE_SIZE)
        self.player = player.Player()

        self.floor_cache = Cache()
        self.layer_cache = Cache()
        self.trigger_cache = Cache()

        self.level = None
        load_coord = self.get_save_value("last_level_coord", [100, 100])
        self.load_level(self.get_save_value("last_level", "level_1"), load_coord[0], load_coord[1])

        self.clock = pygame.time.Clock()
        self.collision = collision.Collision()
        self.debug = False
        self.ignore_collision = False

        running = True

        while running:
            running = self.tick()
            self.clock.tick(60)

    def load_lang(self, lang):
        with open("assets/lang/{}.json".format(lang), 'r', encoding='utf-8') as file:
            self.lang = json.load(file)

    def load_save(self, save):
        with open("data/save/{}.json".format(save), 'r', encoding='utf-8') as file:
            self._save = json.load(file)
        self.save_name = save
        if self.get_save_value("last_save", 0) == 0:
            self.save_data("last_save", int(time.time()))

    def save(self):
        save = self.get_save_value("last_save", 0)
        ct = int(time.time())
        tp = self.get_save_value("time_played", 0)
        self.save_data("time_played", tp + ct - save)
        self.save_data("last_save", ct)
        with open("data/save/{}.json".format(self.save_name), 'w', encoding='utf-8') as file:
            # copy to escape current modification
            json.dump(self._save.copy(), file)

    def get_save_value(self, key, default):
        if key in self._save:
            return self._save[key]
        else:
            return default

    def save_data(self, key, value):
        if value:
            self._save[key] = value
        elif key in self._save:
            del self._save[key]

    def get_message(self, key):
        if key in self.lang:
            return self.lang[key]
        else:
            return key

    def unload_level(self):
        self.player.freeze_time = -1
        self.layer_cache.clear()
        self.floor_cache.clear()
        self.trigger_cache.clear()
        global IMAGE_CACHE
        IMAGE_CACHE.clear()
        DISPLAYER_CACHE.clear()

    def load_level(self, name, x, y):
        self.player.freeze_time = 10
        self.level = level.Level(name)
        self.level.floor.load_asset(self.floor_cache)
        self.level.layer_1.load_asset(self.layer_cache)
        self.level.load_asset(self.trigger_cache)
        self.player.set_pos((x, y))
        self.save_data("last_level", name)
        self.save_data("last_level_coord", [x, y])

    def render(self):

        self.collision.clear()
        self.display.fill((0, 0, 0))

        if self.player.have_open_menu():
            self.player.current_menu.render(self.display)
        else:
            start = self.player.get_scroll_start()
            global came_scroll
            came_scroll = start
            end = self.player.get_scroll_end()
            self.level.floor.render(start[0], start[1], end[0], end[1], self.floor_cache, self.display, self.collision,
                                    [])
            # self.player.render(self.display)
            self.level.layer_1.render(start[0], start[1], end[0], end[1], self.layer_cache, self.display,
                                      self.collision, [[self.player.get_render_y(), self.player.render]])

            self.level.npc_render(self.display, self.collision)
            self.level.load_trigger(start[0], start[1], end[0], end[1], self.trigger_cache, self.collision)

            if self.debug:
                self.render_collision()

            self.render_hud(self.display)

            if self.debug:
                p_pos = self.player.get_pos()
                surf = FONT_16.render("x: {:+.4f}, y: {:+.4f}".format(p_pos[0], p_pos[1]), True, (255, 255, 255))

                # back_ground = pygame.Surface(surf.get_rect().size)
                # back_ground.fill((0, 0, 0))
                # back_ground.set_alpha(200)
                # self.display.blit(back_ground, (0, 0))
                self.display.blit(surf, (0, 0))

        self.screen.blit(pygame.transform.scale(self.display, SCREEN_SIZE), (0, 0))
        pygame.display.update()

    def render_hud(self, display):
        """

        :type display: pygame.Surface
        """
        if self.player.current_dialogue:
            self.player.current_dialogue.render(display)


    def render_collision(self):
        self.collision.debug_render(self.display)
        self.player.get_box().debug_render(self.display)

    def tick(self):
        if self.player.freeze_time == -1:
            self.collision.clear()
            self.display.fill((0, 0, 0))
            self.screen.blit(pygame.transform.scale(self.display, SCREEN_SIZE), (0, 0))
            pygame.display.update()
            return True

        self.render()

        if self.player.freeze_time == 0:
            self.player.move(self.collision)
        elif self.player.freeze_time > 0:
            self.player.freeze_time -= 1

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return False
            if event.type == pygame.KEYDOWN or event.type == pygame.KEYUP:
                if event.key == pygame.K_w:
                    self.player.on_key_y(-1, event.type == pygame.KEYUP)
                if event.key == pygame.K_s:
                    self.player.on_key_y(1, event.type == pygame.KEYUP)
                if event.key == pygame.K_d:
                    self.player.on_key_x(1, event.type == pygame.KEYUP)
                if event.key == pygame.K_a:
                    self.player.on_key_x(-1, event.type == pygame.KEYUP)
                if event.key == pygame.K_F3 and event.type == pygame.KEYDOWN:
                    self.debug = not self.debug
                if event.key == pygame.K_F4 and event.type == pygame.KEYDOWN:
                    self.ignore_collision = not self.ignore_collision
                if event.key == pygame.K_e and event.type == pygame.KEYDOWN:
                    if self.player.current_menu:
                        self.player.close_menu()
                    else:
                        self.player.open_menu(_menu.MainMenu(self.player))
                if event.key == pygame.K_F5 and event.type == pygame.KEYDOWN and self.player.freeze_time == 0:
                    x, y = self.player.rect.x, self.player.rect.y
                    path = self.level.path
                    self.unload_level()
                    self.load_level(path, x, y)
                if event.key == pygame.K_SPACE:
                    if event.type == pygame.KEYDOWN:
                        self.player.action_press()
                    elif event.type == pygame.KEYUP:
                        self.player.action_unpress()
        return True


def get_game_instance():
    """
    :rtype: Game
    """
    return game_instance

