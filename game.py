import pygame
import colorsys
from queue import Queue
from enum import IntEnum

MAX_FPS = 240
SCREEN_WIDTH, SCREEN_HEIGHT = 1080, 770
NEIGHBORS = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]
TIMER_EVENT = pygame.USEREVENT + 1

tools = {}
sliders = {}
display = {}
game_variables = {}


def remap(oldLow, oldHigh, newLow, newHigh, value):
    oldRange = (oldHigh - oldLow)
    newRange = (newHigh - newLow)
    newVal = int((((value - oldLow) * newRange) / oldRange) + newLow)
    return max(newLow, min(newHigh, newVal))


def neighbors(x, y, directions=4, step=1):
    pos = []
    for dx, dy in NEIGHBORS[:directions]:
        for s in range(1, step + 1):
            pos.append((x + dx * s, y + dy * s))
    return pos


def draw_walls(screen):
    grid = display["grid"]
    cell_count = grid.cell_count
    cell_size = grid.cell_size
    wall_color = (50, 50, 50)
    wall_thickness = 4

    pygame.draw.rect(screen, (150, 150, 150),
                     (cell_count * cell_size, 0, SCREEN_WIDTH - cell_count * cell_size, cell_count * cell_size))
    pygame.draw.rect(screen, (80, 80, 80),
                     (0, cell_count * cell_size, SCREEN_WIDTH, SCREEN_HEIGHT - cell_count * cell_size))

    pygame.draw.rect(screen, wall_color,
                     (cell_count * cell_size, 0, wall_thickness, cell_count * cell_size))
    pygame.draw.rect(screen, wall_color,
                     (0, cell_count * cell_size - wall_thickness, SCREEN_WIDTH, wall_thickness))

    pygame.draw.rect(screen, wall_color, (0, 0, SCREEN_WIDTH, wall_thickness))
    pygame.draw.rect(screen, wall_color, (SCREEN_WIDTH - wall_thickness, 0, wall_thickness, SCREEN_HEIGHT))
    pygame.draw.rect(screen, wall_color, (0, 0, wall_thickness, SCREEN_HEIGHT))
    pygame.draw.rect(screen, wall_color, (0, SCREEN_HEIGHT - wall_thickness, SCREEN_WIDTH, wall_thickness))


def draw_current_color(screen):
    color = game_variables["selected_color"]
    pygame.draw.rect(screen, (235, 235, 235), (905, 700, 40, 40))
    pygame.draw.rect(screen, color, (910, 705, 30, 30))


def draw_palette(screen):
    hue = sliders["hue"].slide_val

    pygame.draw.rect(screen, (235, 235, 235), (815, 350, 220, 220))
    palette = display['palette']

    for x in range(200):
        for y in range(200):
            palette.set_at((x, y), tuple(int(255 * i) for i in colorsys.hls_to_rgb(hue / 360, 1 - y / 200, x / 200)))
    screen.blit(palette, (825, 360))


class ColorGrid:
    class ColorCell:
        def __init__(self, pos, size, color):
            self.pos = pos
            self.size = size
            self.color = color
            self.subsurface = pygame.Surface((self.size, self.size))
            self.subsurface.fill(self.color)

        def change_color(self, new_color):
            self.color = new_color
            self.subsurface.fill(self.color)

        def draw(self, screen):
            screen.blit(self.subsurface, self.pos)

    def __init__(self, pos, cell_count, cell_size, color):
        self.pos = pos
        self.cell_count = cell_count
        self.cell_size = cell_size
        self.color = color
        self.grid = [[ColorGrid.ColorCell(pos=(self.pos[0] + self.cell_size * j, self.pos[1] + self.cell_size * i),
                                          size=self.cell_size,
                                          color=self.color) for i in range(cell_count)] for j in range(cell_count)]

    def __getitem__(self, idx):
        return self.grid[idx]

    def draw(self, screen):
        for row in self.grid:
            for cell in row:
                cell.draw(screen)

    def clean(self):
        for row in self.grid:
            for cell in row:
                cell.change_color(self.color)


class Component:
    def __init__(self, pos, width, height, surface_color):
        self.pos = pos
        self.init_pos = pos.copy()
        self.width, self.height = width, height
        self.surface_color = surface_color
        self.subsurface = pygame.Surface((self.width, self.height))
        self.subsurface.fill(self.surface_color)
        self.hovered = False
        self.clicked = False

    def draw(self, screen):
        screen.blit(self.subsurface, self.pos)


class Slider(Component):
    def __init__(self, pos, width, height, surface_color, val_range, text, font_size, font_color):
        super().__init__(pos, width, height, surface_color)
        self.slide_val = 0
        self.val_min, self.val_max = val_range
        self.font = pygame.font.SysFont("Consolas", font_size)
        self.text_render = self.font.render(text, True, font_color)
        self.val_render = self.font.render(str(self.slide_val), True, (30, 30, 30))

    def draw(self, screen):
        initX, initY = self.init_pos
        self.slide_val = remap(-90, 90, self.val_min, self.val_max, (self.pos[0] - initX))
        self.val_render = self.font.render(str(self.slide_val), True, (30, 30, 30))

        # draw the background surface for slide val
        surface_width = 240
        pygame.draw.rect(screen, (190, 190, 190), (initX - surface_width // 2, initY - 30, surface_width, 60))

        # draw the long bar [==========]
        pygame.draw.rect(screen, (140, 140, 140), (initX - 80, initY + self.height // 3, 180, self.height // 2))

        # draw the subsurface behind the slide_val
        pygame.draw.rect(screen, (220, 220, 220), (initX - 110, initY + 1, 20, 20))

        screen.blit(self.val_render, (initX - 105, initY + 3))
        screen.blit(self.text_render, (initX - 110, initY - 25))
        super().draw(screen)


class ColorSlider(Component):
    def __init__(self, pos, width, height, surface_color, val_range):
        super().__init__(pos, width, height, surface_color)
        self.val_min, self.val_max = val_range
        self.slide_val = remap(-90, 90, self.val_min, self.val_max, 0)
        self.slide_bar = pygame.Surface((180, self.height // 2))

    def draw(self, screen):
        initX, initY = self.init_pos
        self.slide_val = remap(-90, 90, self.val_min, self.val_max, (self.pos[0] - initX))

        # draw the background surface for slide val
        surface_width = 240
        pygame.draw.rect(screen, (190, 190, 190), (initX - surface_width // 2, initY - 30, surface_width, 60))

        # draw the long bar [==========]
        for i in range(180):
            for j in range(self.height // 2):
                self.slide_bar.set_at((i, j),
                                      tuple(int(255 * i) for i in colorsys.hls_to_rgb(i / 180, 0.5, 1)))
        screen.blit(self.slide_bar, (initX - 80, initY + self.height // 3))

        # draw the subsurface behind the slide_val
        pygame.draw.rect(screen, tuple(int(255 * i) for i in colorsys.hls_to_rgb(self.slide_val / 360, 0.5, 1)),
                         (initX - 110, initY, 20, 20))

        super().draw(screen)


class Button(Component):
    def __init__(self, pos, width, height, surface_color):
        super().__init__(pos, width, height, surface_color)

    def draw(self, screen):
        if self.hovered:
            self.subsurface.set_alpha(100)
        elif self.clicked:
            self.subsurface.set_alpha(255)
        else:
            self.subsurface.set_alpha(150)

        super().draw(screen)


class ToolType(IntEnum):
    BRUSH_TOOL = 0
    ERASER_TOOL = 1
    FILL_TOOL = 2
    EYEDROPPER_TOOL = 3


class PaintTool:
    def __init__(self, icon_path, bind_key, button):
        self.icon = pygame.transform.scale(pygame.image.load(f"assets/{icon_path}"), (100, 100))
        self.bind_key = bind_key
        self.button = button


def is_within_grid(x, y):
    tool = game_variables["current_tool"]
    size = 22
    if tool == ToolType.BRUSH_TOOL:
        size = game_variables["brush_size"] * 6
    elif tool == ToolType.ERASER_TOOL:
        size = game_variables["eraser_size"] * 6
    boundary = display["grid"].cell_count * display["grid"].cell_size - size
    return x < boundary and y < boundary


def tool_activate():
    cur_tool = game_variables["current_tool"]
    if cur_tool == ToolType.ERASER_TOOL:
        game_variables["current_color"] = display["grid"].color
    else:
        game_variables["current_color"] = game_variables["selected_color"]


def switch_tool():
    cur_tool = game_variables["current_tool"]
    if cur_tool == ToolType.ERASER_TOOL:
        sliders["brush"].pos[0] = sliders["brush"].init_pos[0] + int(180 / 5) * game_variables["eraser_size"] - 90
    else:
        sliders["brush"].pos[0] = sliders["brush"].init_pos[0] + int(180 / 5) * game_variables["brush_size"] - 90


def fill(pos, cur_color, fill_color):
    grid = display["grid"]
    cell_count = grid.cell_count
    visited = set()

    q = Queue()
    q.put(pos)
    while not q.empty():
        x, y = q.get()
        if x < 0 or y < 0 or x >= cell_count or y >= cell_count:
            continue
        if grid[x][y].color != cur_color:
            continue
        if (x, y) in visited:
            continue
        visited.add((x, y))
        grid[x][y].change_color(fill_color)
        for nx, ny in neighbors(x, y):
            if (nx, ny) not in visited:
                q.put((nx, ny))


def paint(pos, color, size):
    posX, posY = pos
    grid = display["grid"]
    cell_count = grid.cell_count
    cell_size = grid.cell_size

    gridX = remap(0, cell_count * cell_size, 0, cell_count, posX)
    gridY = remap(0, cell_count * cell_size, 0, cell_count, posY)

    positions = set()
    positions.add((gridX, gridY))
    if size == 2:
        positions.update(neighbors(gridX, gridY, directions=4))
    elif size == 3:
        positions.update(neighbors(gridX, gridY, directions=8))
    elif size == 4:
        positions.update(neighbors(gridX, gridY, directions=4, step=2))
        positions.update(neighbors(gridX, gridY, directions=8))
    elif size == 5:
        offsets = [0, -1, 1, -2, 2]
        for dx in offsets:
            for dy in offsets:
                positions.add((gridX + dx, gridY + dy))

    for x, y in positions:
        if x < 0 or y < 0 or x >= cell_count or y >= cell_count:
            continue
        grid[x][y].change_color(color)


def init_variables():
    tools[ToolType.BRUSH_TOOL] = PaintTool(icon_path="brush.png",
                                           bind_key=pygame.K_b,
                                           button=Button([880, 60], 30, 30, (80, 80, 80)))
    tools[ToolType.ERASER_TOOL] = PaintTool(icon_path="eraser.png",
                                            bind_key=pygame.K_e,
                                            button=Button([930, 60], 30, 30, (80, 80, 80)))
    tools[ToolType.FILL_TOOL] = PaintTool(icon_path="fill.png",
                                          bind_key=pygame.K_f,
                                          button=Button([880, 110], 30, 30, (80, 80, 80)))
    tools[ToolType.EYEDROPPER_TOOL] = PaintTool(icon_path="eyedropper.png",
                                                bind_key=pygame.K_i,
                                                button=Button([930, 110], 30, 30, (80, 80, 80)))

    sliders["brush"] = Slider([925, 240], 15, 20, (240, 240, 240), (1, 5), "Brush Size", 18, (0, 0, 0))
    sliders["hue"] = ColorSlider([925, 630], 15, 20, (240, 240, 240), (0, 360))

    display["grid"] = ColorGrid([0, 0], 64, 12, (255, 255, 255))
    display['palette'] = pygame.Surface((200, 200))

    game_variables["current_color"] = (128, 30, 30)
    game_variables["selected_color"] = (128, 30, 30)
    game_variables["current_tool"] = ToolType.BRUSH_TOOL
    game_variables["previous_tool"] = ToolType.BRUSH_TOOL
    game_variables["brush_size"] = 3
    game_variables["eraser_size"] = 3
    game_variables["locked"] = False
    game_variables["timer"] = 9999


def send_packet(conn, pos, color, tool_size):
    x, y = pos
    color_str = ",".join([str(_) for _ in color[:3]])
    content = f"G PAINT,{x},{y},{color_str},{tool_size}@"
    conn.sendall(content.encode())


def decode_message(msg, screen):
    if msg == "CLEAR":
        display["grid"].clean()
    elif msg.startswith("PAINT"):
        s = msg.split(",")
        paint((int(s[1]), int(s[2])), (int(s[3]), int(s[4]), int(s[5])), int(s[6]))
    elif msg == "LOCK":
        game_variables["locked"] = True
    elif msg == "TURN":
        game_variables["locked"] = False
        draw_toolbar(screen)
        start_counter()


def start_counter():
    game_variables["timer"] = 60
    pygame.time.set_timer(TIMER_EVENT, 1000)


def update_tools(screen):
    tool_activate()
    pygame.draw.rect(screen, (180, 180, 180), (860, 50, 120, 100))
    for idx, tool in tools.items():
        button = tool.button
        button.clicked = (game_variables["current_tool"] == idx)
        button.draw(screen)
        screen.blit(pygame.transform.scale(tool.icon, (22, 22)), (button.pos[0] + 3, button.pos[1] + 3))


def update_sliders(screen):
    for slider in sliders.values():
        slider.draw(screen)


def draw_toolbar(screen):
    toolbar_font = pygame.font.SysFont("Consolas", 20)

    screen.fill((255, 255, 255))
    draw_walls(screen)
    draw_palette(screen)

    screen.blit(toolbar_font.render("Tools", True, (50, 50, 50)), (780, 20))
    update_tools(screen)

    screen.blit(toolbar_font.render("Size Settings", True, (50, 50, 50)), (780, 170))
    update_sliders(screen)
    screen.blit(toolbar_font.render("Colors", True, (50, 50, 50)), (780, 300))


def main(msg_queue, conn):
    pygame.init()
    init_variables()

    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("SoulPainter")
    pygame.display.set_icon(pygame.image.load("assets/icon.png"))

    clock = pygame.time.Clock()
    clicking = False

    grid = display["grid"]
    cell_count = grid.cell_count
    cell_size = grid.cell_size

    toolbar_font = pygame.font.SysFont("Consolas", 20)
    draw_toolbar(screen)

    while True:
        while not msg_queue.empty():
            msg = msg_queue.get()
            decode_message(msg, screen)
        clock.tick(MAX_FPS)
        if game_variables["locked"]:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    if conn: conn.close()
                    return
            screen.fill((255, 255, 255))
            draw_walls(screen)
            pygame.mouse.set_visible(True)
            grid.draw(screen)
            pygame.display.update()
            continue
        cur_pos = pygame.mouse.get_pos()
        cursorX, cursorY = cur_pos
        cur_tool = game_variables["current_tool"]
        color = game_variables["current_color"]
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                if conn: conn.close()
                return
            elif event.type == TIMER_EVENT:
                if game_variables["timer"] == 0:
                    pygame.time.set_timer(TIMER_EVENT, 0)
                    conn.sendall(f"G TIME_UP".encode())
                else:
                    game_variables["timer"] -= 1
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 3:  # right click
                    game_variables["previous_tool"] = cur_tool
                    game_variables["current_tool"] = ToolType.ERASER_TOOL
                    switch_tool()
                    update_sliders(screen)
                elif event.button == 1:  # left click
                    if is_within_grid(cursorX, cursorY):
                        if cur_tool == ToolType.BRUSH_TOOL or cur_tool == ToolType.ERASER_TOOL:
                            tool_size = game_variables["brush_size"] if cur_tool == ToolType.BRUSH_TOOL else \
                                game_variables[
                                    "eraser_size"]
                            send_packet(conn, cur_pos, color, tool_size)
                            paint(cur_pos, color, tool_size)
                            clicking = True
                            continue
                        gridX = remap(0, cell_count * cell_size, 0, cell_count, cursorX)
                        gridY = remap(0, cell_count * cell_size, 0, cell_count, cursorY)
                        cursor_color = grid[gridX][gridY].color
                        if cur_tool == ToolType.FILL_TOOL:
                            fill((gridX, gridY), cursor_color, color)
                        elif cur_tool == ToolType.EYEDROPPER_TOOL:
                            game_variables["selected_color"] = cursor_color
                    else:
                        palette = display["palette"]
                        px, py = 825, 360
                        if px <= cursorX <= px + 200 and py <= cursorY <= py + 200:
                            game_variables["selected_color"] = palette.get_at((cursorX - px, cursorY - py))
                            draw_current_color(screen)
                            continue

                        for slider in sliders.values():
                            top_left = (slider.pos[0], slider.pos[1])
                            if slider.subsurface.get_rect(topleft=top_left).collidepoint((cursorX, cursorY)):
                                slider.clicked = True
                                slider.subsurface.set_alpha(100)
                                slider.draw(screen)
                            else:
                                slider.clicked = False

                        for idx, tool in tools.items():
                            if tool.button.hovered:
                                game_variables["current_tool"] = idx
                                update_tools(screen)
                                break
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 3:
                    game_variables["current_tool"] = game_variables["previous_tool"]
                    switch_tool()
                elif event.button == 1:
                    clicking = False
                    for slider in sliders.values():
                        slider.clicked = False
                        slider.subsurface.set_alpha(255)
                update_sliders(screen)

            elif event.type == pygame.MOUSEMOTION:
                if is_within_grid(cursorX, cursorY):
                    pygame.mouse.set_visible(False)
                else:
                    pygame.mouse.set_visible(True)
                if clicking:
                    if is_within_grid(cursorX, cursorY) and (
                            cur_tool == ToolType.BRUSH_TOOL or cur_tool == ToolType.ERASER_TOOL):
                        tool_size = game_variables["brush_size"] if cur_tool == ToolType.BRUSH_TOOL else game_variables[
                            "eraser_size"]
                        send_packet(conn, cur_pos, color, tool_size)
                        paint(cur_pos, color, tool_size)
                else:
                    for tool in tools.values():
                        button = tool.button
                        if button.subsurface.get_rect(topleft=button.pos).collidepoint(cur_pos):
                            button.hovered = True
                        else:
                            button.hovered = False
                    for name, slider in sliders.items():
                        if slider.clicked:
                            if name == "brush":
                                if game_variables["current_tool"] == ToolType.BRUSH_TOOL:
                                    game_variables["brush_size"] = slider.slide_val
                                elif game_variables["current_tool"] == ToolType.ERASER_TOOL:
                                    game_variables["eraser_size"] = slider.slide_val
                            elif name == "hue":
                                draw_palette(screen)
                            slider.pos[0] = max(slider.init_pos[0] - 80, min(cursorX, slider.init_pos[0] + 90))
                            slider.draw(screen)

        tool_activate()
        grid.draw(screen)

        cur_tool = game_variables["current_tool"]
        color = game_variables["current_color"]

        if is_within_grid(cursorX, cursorY):
            if cur_tool == ToolType.BRUSH_TOOL:
                pygame.draw.circle(screen, color, cur_pos, game_variables["brush_size"] * 6)
            elif cur_tool == ToolType.ERASER_TOOL:
                pygame.draw.circle(screen, (50, 50, 50), cur_pos, game_variables["eraser_size"] * 6)
            elif cur_tool == ToolType.FILL_TOOL:
                screen.blit(pygame.transform.scale(tools[cur_tool].icon, (22, 22)), (cursorX, cursorY - 35))
            elif cur_tool == ToolType.EYEDROPPER_TOOL:
                screen.blit(pygame.transform.scale(tools[cur_tool].icon, (22, 22)), (cursorX, cursorY - 30))

        pygame.draw.rect(screen, (150, 150, 150), (820, 700, SCREEN_WIDTH - 830, SCREEN_HEIGHT - 710))
        screen.blit(toolbar_font.render(f"Time remaining: {game_variables['timer']}", True, (50, 50, 50)), (820, 700))

        pygame.display.update()


if __name__ == "__main__":
    queue = Queue()
    main(queue, None)
