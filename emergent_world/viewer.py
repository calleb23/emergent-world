"""A pygame window for watching the world and following one agent's life.

Controls: click an agent to follow them, SPACE pause, UP/DOWN change speed,
ESC or close the window to quit. When the followed agent dies, the view moves
to their oldest living child (or other family, or the oldest agent).
"""

import textwrap

import pygame

from emergent_world.config import format_time
from emergent_world.sim import Simulation
from emergent_world.world.grid import FOOD, POISON, WATER

CELL = 10
PANEL = 380
GRASS_COLOR = (34, 52, 30)
WATER_COLOR = (40, 90, 160)
TEXT_COLOR = (230, 230, 230)
DIM_TEXT = (150, 150, 160)
BG_COLOR = (18, 18, 22)
FOLLOW_RING = (255, 210, 60)
BAR_COLORS = {"Energy": (220, 170, 60), "Water": (80, 150, 230), "Health": (90, 200, 110)}


def _agent_color(health: float, max_health: float) -> tuple:
    """Bright white when healthy, fading to red as health drops."""
    share = max(0.0, min(1.0, health / max_health))
    return (255, int(80 + 175 * share), int(80 + 175 * share))


def run_viewer(sim: Simulation, max_ticks: int):
    pygame.init()
    width = sim.world.width * CELL + PANEL
    height = max(sim.world.height * CELL, 640)
    screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption(f"Emergent World (seed {sim.seed})")
    font = pygame.font.SysFont("consolas", 15)
    clock = pygame.time.Clock()

    ticks_per_second = 24  # one simulated day per real second
    paused = False
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_UP:
                    ticks_per_second = min(1000, ticks_per_second * 2)
                elif event.key == pygame.K_DOWN:
                    ticks_per_second = max(1, ticks_per_second // 2)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                _follow_clicked(sim, event.pos)

        if not paused and sim.living and sim.tick_count < max_ticks:
            sim.tick()

        _draw(screen, font, sim, ticks_per_second, paused)
        pygame.display.flip()
        clock.tick(ticks_per_second)

    pygame.quit()


def _follow_clicked(sim: Simulation, pos: tuple):
    x, y = pos[0] // CELL, pos[1] // CELL
    if not sim.world.in_bounds(x, y):
        return
    nearest = min(sim.living, key=lambda a: abs(a.x - x) + abs(a.y - y), default=None)
    if nearest is not None and abs(nearest.x - x) + abs(nearest.y - y) <= 2:
        sim.follow(nearest)


def _draw(screen, font, sim: Simulation, speed: int, paused: bool):
    screen.fill(BG_COLOR)
    world = sim.world
    c = sim.config

    for x in range(world.width):
        for y in range(world.height):
            rect = (x * CELL, y * CELL, CELL, CELL)
            if world.terrain[x, y] == WATER:
                pygame.draw.rect(screen, WATER_COLOR, rect)
                continue
            pygame.draw.rect(screen, GRASS_COLOR, rect)
            plant = world.plants[x, y]
            if plant == FOOD:
                pygame.draw.rect(screen, c.food_color, (x * CELL + 2, y * CELL + 2, CELL - 4, CELL - 4))
            elif plant == POISON:
                pygame.draw.rect(screen, c.poison_color, (x * CELL + 2, y * CELL + 2, CELL - 4, CELL - 4))

    followed = sim.by_id.get(sim.followed_id) if sim.followed_id is not None else None
    for agent in sim.living:
        center = (agent.x * CELL + CELL // 2, agent.y * CELL + CELL // 2)
        pygame.draw.circle(screen, _agent_color(agent.health, c.max_health), center, CELL // 2)
    if followed is not None and followed.alive:
        center = (followed.x * CELL + CELL // 2, followed.y * CELL + CELL // 2)
        pygame.draw.circle(screen, FOLLOW_RING, center, CELL, 2)
        pygame.draw.circle(screen, FOLLOW_RING, center, c.vision_range * CELL, 1)  # how far they see

    _draw_panel(screen, font, sim, followed, speed, paused)


def _draw_panel(screen, font, sim, followed, speed, paused):
    c = sim.config
    x0 = sim.world.width * CELL + 14
    y = 12

    def line(text, color=TEXT_COLOR):
        nonlocal y
        screen.blit(font.render(text, True, color), (x0, y))
        y += 19

    line(f"{format_time(sim.tick_count).capitalize()}   {len(sim.living)} alive")
    line(f"{speed} hours/sec" + ("   [PAUSED]" if paused else ""), DIM_TEXT)
    y += 8

    if followed is None:
        line("Click an agent to follow them.", DIM_TEXT)
        return

    line(f"Following #{followed.id}", FOLLOW_RING)
    line(f"Age {followed.age // 24} days of ~{followed.lifespan // 24}   generation {followed.generation}")
    family = [sim.by_id[i] for i in followed.kin if i in sim.by_id and sim.by_id[i].alive]
    line(f"Children {followed.children}   living family {len(family)}")
    y += 4
    for label, value, top in (("Energy", followed.energy, c.max_energy),
                              ("Water", followed.water, c.max_water),
                              ("Health", followed.health, c.max_health)):
        screen.blit(font.render(f"{label:<7}", True, DIM_TEXT), (x0, y))
        pygame.draw.rect(screen, (50, 50, 58), (x0 + 70, y + 3, 200, 11))
        pygame.draw.rect(screen, BAR_COLORS[label], (x0 + 70, y + 3, int(200 * max(0, value) / top), 11))
        y += 19
    if any(s.felt for s in followed.sicknesses):
        line("Feeling sick", (230, 120, 90))
    y += 6

    line("Wary of:", DIM_TEXT)
    wary = sorted(followed.memory.aversion.items(), key=lambda kv: -kv[1])
    if not wary:
        line("  nothing yet")
    for color, level in wary:
        line(f"  {sim.look_name(color):<20} {'#' * max(1, round(level * 10))}")
    y += 6

    line("Life so far (latest first):", DIM_TEXT)
    for tick, text in reversed(followed.events[-12:]):
        stamp = f"y{tick // (24 * 365) + 1} d{tick // 24 % 365 + 1}"
        wrapped = textwrap.wrap(text, 30) or [""]
        line(f"{stamp:<9} {wrapped[0]}")
        for extra in wrapped[1:]:
            line(f"{'':<9} {extra}")
        if y > screen.get_height() - 40:
            break

    y = screen.get_height() - 26
    line("Click: follow  SPACE: pause  UP/DOWN", DIM_TEXT)
