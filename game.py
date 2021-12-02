import pygame
from enum import IntEnum

MAX_FPS = 240
NEIGHBORS = [(1, 0), (-1, 0), (0, 1), (0, -1)]

tools = {}
sliders = {}
display = {}
game_variables = {}


def remap(oldLow, oldHigh, newLow, newHigh, value):
    oldRange = (oldHigh - oldLow)
    newRange = (newHigh - newLow)
    newVal = int((((value - oldLow) * newRange) / oldRange) + newLow)
    return max(newLow, min(newHigh, newVal))


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
        self.grid = [ColorGrid.ColorCell(pos=(self.pos[0] + self.cell_size * i, self.pos[1] + self.cell_size * j),
                                         size=self.cell_size,
                                         color=self.color) for i in range(cell_count) for j in range(cell_count)]

    def __getitem__(self, idx):
        return self.grid[idx]

    def draw(self, screen):
        for cell in self.grid:
            cell.draw(screen)

    def clean(self):
        for cell in self.grid:
            cell.change_color(self.color)


class Component:
    def __init__(self, pos, width, height, surface_color):
        self.pos = pos
        self.init_pos = self.pos.copy()
        self.width, self.height = width, height
        self.surface_color = surface_color
        self.subsurface = pygame.Surface((self.width, self.height))
        self.subsurface.fill(self.surface_color)

    def draw(self, screen):
        screen.blit(self.subsurface, self.pos)


class Slider(Component):
    def __init__(self, pos, width, height, surface_color, text, font_size, font_color):
        super().__init__(pos, width, height, surface_color)
        self.slide_val = 0
        self.font = pygame.font.SysFont("Consolas", font_size)
        self.text_render = self.font.render(text, True, font_color)
        self.val_render = self.font.render(str(self.slide_val), True, (30, 30, 30))

    def draw(self, screen):
        initX, initY = self.init_pos
        self.slide_val = remap(-60, 60, 1, 5, (self.pos[0] - initX))
        self.val_render = self.font.render(str(self.slide_val), True, (30, 30, 30))

        # draw the long bar [==========]
        pygame.draw.rect(screen, (140, 140, 140), (initX - 60, initY + self.height // 3, 120, self.height // 2))

        # draw the button [====||====]
        pygame.draw.rect(screen, (190, 190, 190), (initX - 100, initY - 30, 168, 60))

        # draw the background surface for slide val
        pygame.draw.rect(screen, (220, 220, 220), (initX - 90, initY + 1, 20, 20))

        screen.blit(self.val_render, (initX - 85, initY + 3))
        screen.blit(self.text_render, (initX - 90, initY - 25))
        super().draw(screen)


class Button(Component):
    def __init__(self, pos, width, height, surface_color):
        super().__init__(pos, width, height, surface_color)
        self.hovered = False
        self.clicked = False

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
        self.icon = pygame.transform.scale(pygame.image.load(f"assets/{icon_path}"), (40, 40))
        self.bind_key = bind_key
        self.button = button


def is_within_grid(x, y):
    boundary = display["grid"].cell_count * display["grid"].cell_size
    return x < boundary and y < boundary


def fill(pos, cur_color, fill_color):
    x, y = pos
    grid = display["grid"]
    cell_count = grid.cell_count
    if x < 0 or y < 0 or x >= cell_count or y >= cell_count:
        return
    if grid[x][y].color != cur_color:
        return
    positions = game_variables["visited_fill_pos"]
    if pos in positions:
        return

    positions.append(pos)
    grid[x][y].change_color(fill_color)
    for dx, dy in NEIGHBORS:
        fill((x + dx, y + dy), cur_color, fill_color)


def paint(pos, color, tool, tool_size):
    # TODO
    return


def init_variables():
    tools[ToolType.BRUSH_TOOL] = PaintTool(icon_path="brush.png",
                                           bind_key=pygame.K_b,
                                           button=Button((825, 60), 30, 30, (80, 80, 80)))
    tools[ToolType.ERASER_TOOL] = PaintTool(icon_path="eraser.png",
                                            bind_key=pygame.K_e,
                                            button=Button((875, 60), 30, 30, (80, 80, 80)))
    tools[ToolType.FILL_TOOL] = PaintTool(icon_path="fill.png",
                                          bind_key=pygame.K_f,
                                          button=Button((825, 110), 30, 30, (80, 80, 80)))
    tools[ToolType.EYEDROPPER_TOOL] = PaintTool(icon_path="eyedropper.png",
                                                bind_key=pygame.K_i,
                                                button=Button((875, 110), 30, 30, (80, 80, 80)))

    sliders["brush"] = Slider((880, 305), 10, 20, (240, 240, 240), "Brush Size", 18, (0, 0, 0))
    sliders["eraser"] = Slider((880, 225), 10, 20, (240, 240, 240), "Eraser Size", 18, (0, 0, 0))

    display["grid"] = ColorGrid((0, 0), 64, 12, (255, 255, 255))

    game_variables["current_color"] = (128, 30, 30)
    game_variables["current_tool"] = ToolType.BRUSH_TOOL
    game_variables["previous_tool"] = ToolType.BRUSH_TOOL
    game_variables["brush_size"] = 3
    game_variables["eraser_size"] = 3
    game_variables["record"] = []
    game_variables["visited_fill_pos"] = set()


def main():
    pygame.init()
    init_variables()

    clock = pygame.time.Clock()
    clicking = False

    grid = display["grid"]
    cell_count = grid.cell_count
    cell_size = grid.cell_size

    while True:
        clock.tick(MAX_FPS)
        cursorX, cursorY = pygame.mouse.get_pos()
        tool = game_variables["current_tool"]
        color = game_variables["current_color"]
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 3:  # right click
                    game_variables["previous_tool"] = tool
                    game_variables["current_tool"] = ToolType.ERASER_TOOL
                elif event.button == 1:  # left click
                    if is_within_grid(cursorX, cursorY):
                        if tool == ToolType.BRUSH_TOOL or tool == ToolType.ERASER_TOOL:
                            tool_size = game_variables["brush_size"] if tool == ToolType.BRUSH_TOOL else game_variables[
                                "eraser_size"]
                            paint((cursorX, cursorY), color, tool, tool_size)
                            clicking = True
                            break
                        gridX = remap(0, cell_count * cell_size, 0, cell_count, cursorX)
                        gridY = remap(0, cell_count * cell_size, 0, cell_count, cursorY)
                        cursor_color = grid[gridX][gridY].color
                        if tool == ToolType.FILL_TOOL:
                            game_variables["visited_fill_pos"].clear()
                            fill((gridX, gridY), cursor_color, color)
                        elif tool == ToolType.EYEDROPPER_TOOL:
                            game_variables["current_color"] = cursor_color
                    else:
                        # TODO: other button functions
                        break
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 3:
                    game_variables["current_tool"] = game_variables["previous_tool"]
                elif event.button == 1:
                    clicking = False

            elif event.type == pygame.MOUSEMOTION:
                pygame.mouse.set_visible(is_within_grid(cursorX, cursorY))
                if clicking and is_within_grid(cursorX, cursorY):
                    if tool == ToolType.BRUSH_TOOL or tool == ToolType.ERASER_TOOL:
                        tool_size = game_variables["brush_size"] if tool == ToolType.BRUSH_TOOL else game_variables[
                            "eraser_size"]
                        paint((cursorX, cursorY), color, tool, tool_size)
                    else:
                        # TODO: button hovers
                        break
            # TODO: keyboard events
