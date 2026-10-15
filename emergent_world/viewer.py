"""A pygame window for watching the world live.

Controls: SPACE pause, UP/DOWN change speed, ESC or close window to quit.
"""

import pygame

from emergent_world.sim import Simulation
from emergent_world.world.grid import FOOD, POISON, WATER

CELL = 10
PANEL = 220
GRASS_COLOR = (34, 52, 30)
WATER_COLOR = (40, 90, 160)
TEXT_COLOR = (230, 230, 230)
BG_COLOR = (18, 18, 22)


def _agent_color(health: float, max_health: float) -> tuple:
    """Bright white when healthy, fading to red as health drops."""
    share = max(0.0, min(1.0, health / max_health))
    return (255, int(80 + 175 * share), int(80 + 175 * share))


def run_viewer(sim: Simulation, max_ticks: int):
    pygame.init()
    width = sim.world.width * CELL + PANEL
    height = max(sim.world.height * CELL, 300)
    screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption(f"Emergent World (seed {sim.seed})")
    font = pygame.font.SysFont("consolas", 16)
    clock = pygame.time.Clock()

    ticks_per_second = 20
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
                    ticks_per_second = min(500, ticks_per_second * 2)
                elif event.key == pygame.K_DOWN:
                    ticks_per_second = max(1, ticks_per_second // 2)

        if not paused and sim.living and sim.tick_count < max_ticks:
            sim.tick()

        _draw(screen, font, sim, ticks_per_second, paused)
        pygame.display.flip()
        clock.tick(ticks_per_second)

    pygame.quit()


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

    for agent in sim.living:
        center = (agent.x * CELL + CELL // 2, agent.y * CELL + CELL // 2)
        pygame.draw.circle(screen, _agent_color(agent.health, c.max_health), center, CELL // 2)

    deaths = sim.stats.deaths_by_cause()
    plants = world.plant_counts()
    lines = [
        f"Tick: {sim.tick_count}",
        f"Speed: {speed} t/s" + ("  [PAUSED]" if paused else ""),
        f"Difficulty: {sim.difficulty:.2f}",
        f"Alive: {len(sim.living)}",
        f"Max generation: {max((a.generation for a in sim.living), default=0)}",
        f"Births: {sim.stats.births}",
        f"Food plants: {plants['food']}",
        f"Poison plants: {plants['poison']}",
        "",
        "Deaths:",
    ] + [f"  {cause}: {n}" for cause, n in deaths.most_common()] + [
        "",
        "SPACE pause",
        "UP/DOWN speed",
        "ESC quit",
    ]
    x0 = world.width * CELL + 12
    for i, line in enumerate(lines):
        screen.blit(font.render(line, True, TEXT_COLOR), (x0, 12 + i * 20))
