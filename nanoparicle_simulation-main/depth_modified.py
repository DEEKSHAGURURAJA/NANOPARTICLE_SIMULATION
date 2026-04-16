
import pygame
import random
import math
import sys
import time
import pandas as pd

# -----------------------------
# Command-line args: lat lon measurement depth_value
# -----------------------------
lat, lon, measurement, depth_value = None, None, None, None
if len(sys.argv) >= 3:
    try:
        lat = float(sys.argv[1])
        lon = float(sys.argv[2])

        # Load dataset
        df = pd.read_csv("Microplastics_Clean_Essential.csv")
        df = df[df["is_land"] == False]

        # Find nearest row
        row = df.iloc[((df["Latitude_degree"]-lat)**2 + (df["Longitudedegree"]-lon)**2).argmin()]
        measurement = float(row["Microplastics_measurement"])
        depth_value = float(row["Water_Sample_Depth_m"])

        print(f"[INFO] Loaded from CSV: measurement={measurement}, depth={depth_value}")

    except Exception as e:
        print(f"[WARN] Invalid args or CSV issue ({e}), running with defaults.")
# -----------------------------
# Defaults & scaling
# -----------------------------
WIDTH, HEIGHT = 1000, 600
PARTICLE_COUNT = 250           # default
TOTAL_DEPTH = 5.0              # meters default
PARTICLE_SPEED = 1.5
FPS_TARGET = 60
SHOW_FPS = True
paused = False

# Scale with data
if measurement is not None:
    PARTICLE_COUNT = max(80, min(2000, int(200 + measurement * 2)))
if depth_value is not None:
    TOTAL_DEPTH = max(1.0, min(1000.0, float(depth_value)))  # clamp for sanity

# -----------------------------
# Pygame init
# -----------------------------
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Water Depth Nanoparticle Simulation")
clock = pygame.time.Clock()

# Colors
DEEP_BLUE = (5, 15, 40)
MID_BLUE = (10, 50, 100)
SHALLOW_BLUE = (30, 130, 200)
SAND_COLOR = (194, 178, 128)
TOXIC_GREEN = (100, 250, 130)
TOXIC_YELLOW = (250, 250, 100)
TOXIC_RED = (250, 100, 100)
BUBBLE_COLOR = (200, 230, 255)
NANO_COLOR = (180, 100, 250)
DEBRIS_COLOR = (139, 69, 19)
WHITE = (255, 255, 255)
PANEL_BG = (20, 30, 50)
SURFACE_BLUE = (85, 175, 255)

# Wave / surface params
SURFACE_Y = int(HEIGHT * 0.06)
WAVE_AMPLITUDE = 18
WAVE_LENGTH = 140
WAVE_SPEED = 0.08
WAVE_CHOPPINESS = 0.45
SURFACE_REFLECTION_LINES = True

# Cached assets
background = None
cached_rays = None
glow_base = None

# Utilities
def create_gradient_background():
    surf = pygame.Surface((WIDTH, HEIGHT)).convert()
    for y in range(HEIGHT):
        depth_factor = y / HEIGHT
        r = int(DEEP_BLUE[0] + (SHALLOW_BLUE[0] - DEEP_BLUE[0]) * (1 - depth_factor))
        g = int(DEEP_BLUE[1] + (SHALLOW_BLUE[1] - DEEP_BLUE[1]) * (1 - depth_factor))
        b = int(DEEP_BLUE[2] + (SHALLOW_BLUE[2] - DEEP_BLUE[2]) * (1 - depth_factor))
        pygame.draw.line(surf, (r, g, b), (0, y), (WIDTH, y))
    # Sand
    for i in range(0, WIDTH, 4):
        height_var = random.randint(-3, 3)
        pygame.draw.rect(surf, SAND_COLOR, (i, HEIGHT-30+height_var, 3, 30-height_var))
    return surf

def create_cached_rays():
    surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for _ in range(4):
        x = random.randint(0, WIDTH)
        width = random.randint(30, 90)
        ray = pygame.Surface((width, HEIGHT), pygame.SRCALPHA)
        for j in range(18):
            alpha = max(0, 12 - j//2)
            ray_color = (255,255,255, alpha)
            pygame.draw.line(ray, ray_color, (width//2, 0), (width//2, HEIGHT), 1)
        surf.blit(ray, (x, 0), special_flags=pygame.BLEND_PREMULTIPLIED)
    return surf

def create_glow_base(size=128):
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    center = size // 2
    max_r = center
    for r in range(max_r, 0, -1):
        alpha = int(180 * (r / max_r) ** 1.8)
        pygame.draw.circle(s, (255,255,255,alpha), (center, center), r)
    return s

background = create_gradient_background()
cached_rays = create_cached_rays()
glow_base = create_glow_base(128)

# Flow field
class FlowField:
    def __init__(self):
        self.angle = random.uniform(0, math.pi * 2)
        self.change_timer = 0
        self.current_lines = []
        self.max_lines = 60
    def update(self):
        self.change_timer += 1
        if self.change_timer > 70:
            self.angle = random.uniform(0, math.pi * 2)
            self.change_timer = 0
        if len(self.current_lines) < self.max_lines and random.random() < 0.04:
            x = random.randint(0, WIDTH)
            y = random.randint(0, HEIGHT)
            fx, fy = self.get_vector(x, y)
            if abs(fx) > 0.25 or abs(fy) > 0.25:
                c = int(140 + 100 * (y / HEIGHT))
                self.current_lines.append({'x':x,'y':y,'color':(c,c,255,140),'life':90,'path':[(x,y)]})
        for line in self.current_lines[:]:
            line['life'] -= 1
            if line['life'] <= 0:
                self.current_lines.remove(line); continue
            fx, fy = self.get_vector(line['x'], line['y'])
            line['x'] += fx * 2
            line['y'] += fy * 2
            line['path'].append((line['x'], line['y']))
            if line['x'] < -60 or line['x'] > WIDTH+60 or line['y'] < -60 or line['y'] > HEIGHT+60:
                if line in self.current_lines: self.current_lines.remove(line)
    def get_vector(self, x, y):
        fx, fy = math.cos(self.angle), math.sin(self.angle)
        v = 0.28
        fx += v * math.sin(x/110 + y/140)
        fy += v * math.cos(x/130 - y/120)
        toxicity_depth = 0.6
        depth_factor = max(0, (y/HEIGHT - toxicity_depth) / (1 - toxicity_depth))
        fy += depth_factor * 0.7
        return fx, fy
    def draw_currents(self, surface):
        ol = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for line in self.current_lines:
            if len(line['path']) > 1:
                plen = len(line['path'])
                start_i = max(0, plen-10)
                for i in range(start_i, plen-1):
                    alpha = int(line['color'][3] * ((i-start_i+1) / max(1, plen-start_i)))
                    color = (line['color'][0],line['color'][1],line['color'][2], alpha)
                    pygame.draw.line(ol, color, line['path'][i], line['path'][i+1], 1)
        surface.blit(ol, (0,0))

class Particle:
    def __init__(self, x, y, ptype):
        self.x = float(x); self.y = float(y)
        self.ptype = ptype
        if ptype == 0:   # bubbles
            self.size = random.uniform(1.2, 3.0); self.base_speed = random.uniform(0.35, 1.1)
        elif ptype == 1: # nanoparticles
            self.size = random.uniform(0.6, 1.8); self.base_speed = random.uniform(0.08, 0.5)
        else:            # debris
            self.size = random.uniform(2.0, 4.5); self.base_speed = random.uniform(0.08, 0.45)
        self.depth = self.y / HEIGHT
        self.wobble = random.uniform(0, 2*math.pi)
        self.wobble_speed = random.uniform(0.02, 0.06)
        self.age = 0; self.max_age = random.randint(600, 1400)
        self.toxicity = 0.0 if ptype!=1 else random.uniform(0.08, 0.28)
    def update(self, flow_field, global_speed):
        fx, fy = flow_field.get_vector(self.x, self.y)
        speed = self.base_speed * global_speed
        if self.ptype == 0:
            self.y -= speed * 0.8
            self.x += math.sin(self.wobble) * 0.28
        elif self.ptype == 1:
            self.y += fy * speed * 0.5
            self.x += fx * speed * 0.5 + math.sin(self.wobble) * 0.28
            if self.depth > 0.6:
                self.toxicity = min(1.0, self.toxicity + 0.004)
                self.x += random.uniform(-0.45,0.45) * self.toxicity
                self.y += random.uniform(-0.18,0.45) * self.toxicity
        else:
            self.y += speed * 0.28
            self.x += math.sin(self.wobble) * 0.18
        self.x += fx * speed * (1 - self.depth)
        self.y += fy * speed * (1 - self.depth)
        self.wobble += self.wobble_speed
        self.depth = max(0.0, min(1.0, self.y / HEIGHT))
        self.age += 1
        if self.x < -12: self.x = WIDTH + 12
        elif self.x > WIDTH + 12: self.x = -12
        if self.y < -48 or self.y > HEIGHT + 48 or self.age > self.max_age:
            if self.ptype == 0:
                self.y = random.randint(HEIGHT//2, HEIGHT)
            elif self.ptype == 1:
                self.y = random.randint(max(5, SURFACE_Y+2), int(HEIGHT * 0.25))
                self.toxicity = random.uniform(0.08, 0.28)
            else:
                self.y = random.randint(0, HEIGHT//2)
            self.x = random.randint(0, WIDTH)
            self.age = 0; self.depth = self.y / HEIGHT
    def draw(self, surface, wave_phase):
        prox_pixels = max(0.0, (self.y - SURFACE_Y))
        prox_factor = 1.0 - min(1.0, prox_pixels / (HEIGHT * 0.22))
        shimmer = (math.sin((self.x * 0.02) + wave_phase * 2.8) + 1) * 0.5
        if self.ptype == 0:
            base = BUBBLE_COLOR
            highlight = 36 + int(56 * (1 - self.depth))
            col = (min(255, base[0]+highlight), min(255, base[1]+highlight), min(255, base[2]+highlight))
        elif self.ptype == 1:
            if self.toxicity < 0.4:
                base = NANO_COLOR
            elif self.toxicity < 0.7:
                mix = (self.toxicity - 0.4) / 0.3
                base = (int(NANO_COLOR[0]*(1-mix)+TOXIC_YELLOW[0]*mix),
                        int(NANO_COLOR[1]*(1-mix)+TOXIC_YELLOW[1]*mix),
                        int(NANO_COLOR[2]*(1-mix)+TOXIC_YELLOW[2]*mix))
            else:
                mix = min(1.0, (self.toxicity - 0.7)/0.3)
                base = (int(NANO_COLOR[0]*(1-mix)+TOXIC_RED[0]*mix),
                        int(NANO_COLOR[1]*(1-mix)+TOXIC_RED[1]*mix),
                        int(NANO_COLOR[2]*(1-mix)+TOXIC_RED[2]*mix))
            col = base
        else:
            base = DEBRIS_COLOR
            darken = int(56 * self.depth)
            col = (max(0, base[0]-darken), max(0, base[1]-darken), max(0, base[2]-darken))
        brightness_mult = 1.0 + 0.6 * shimmer * prox_factor
        col = (max(0, min(255, int(col[0]*brightness_mult))),
               max(0, min(255, int(col[1]*brightness_mult))),
               max(0, min(255, int(col[2]*brightness_mult))))
        size_factor = 1.0 - self.depth * 0.5
        radius = max(1, int(self.size * size_factor))
        if self.ptype == 0:
            pygame.draw.circle(surface, col, (int(self.x), int(self.y)), radius)
            if prox_factor > 0.18:
                spec_r = max(1, radius//2)
                spec_alpha = int(100 * prox_factor)
                s = pygame.Surface((spec_r*2, spec_r*2), pygame.SRCALPHA)
                pygame.draw.circle(s, (255,255,255,spec_alpha), (spec_r, spec_r), spec_r)
                surface.blit(s, (int(self.x)-spec_r, int(self.y)-spec_r))
        elif self.ptype == 1:
            pygame.draw.circle(surface, col, (int(self.x), int(self.y)), radius)
            if self.toxicity > 0.35:
                glow_scale = max(1.4, 1.0 + self.toxicity * 1.8) * (1.0 + prox_factor*0.7)
                gsize = int(128 * glow_scale)
                glow = pygame.transform.smoothscale(glow_base, (gsize, gsize))
                glow_t = glow.copy()
                tint = pygame.Surface((gsize, gsize), pygame.SRCALPHA)
                tint.fill((*col, 0))
                glow_t.blit(tint, (0,0), special_flags=pygame.BLEND_RGBA_MULT)
                alpha = int(100 * self.toxicity * prox_factor) + 20
                glow_t.set_alpha(alpha)
                surface.blit(glow_t, (int(self.x) - gsize//2, int(self.y) - gsize//2), special_flags=pygame.BLEND_PREMULTIPLIED)
        else:
            pts = []
            for i in range(5):
                ang = 2*math.pi*i/5 + random.uniform(-0.18, 0.18)
                r = radius * random.uniform(0.78, 1.18)
                pts.append((self.x + r*math.cos(ang), self.y + r*math.sin(ang)))
            pygame.draw.polygon(surface, col, pts)

# Surface drawing
def draw_surface(surface, wave_phase):
    surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    points = []
    step = 8
    k = (2*math.pi) / WAVE_LENGTH
    for x in range(0, WIDTH + step, step):
        s = math.sin(k * x + wave_phase)
        chop = s * WAVE_AMPLITUDE * WAVE_CHOPPINESS
        x_disp = x + chop
        y = SURFACE_Y + s * WAVE_AMPLITUDE
        points.append((x_disp, y))
    points.append((WIDTH, 0)); points.append((0, 0))
    pygame.draw.polygon(surf, (*SURFACE_BLUE, 220), points)
    if SURFACE_REFLECTION_LINES:
        for i in range(5):
            offset = wave_phase * (0.6 + i*0.18) + i*1.2
            for x in range(0, WIDTH, 18):
                y = SURFACE_Y + math.sin(k * x + offset) * (WAVE_AMPLITUDE * (0.4 + i*0.08))
                a = int(40 * (1.0 - i*0.08))
                pygame.draw.line(surf, (255,255,255,a), (x,y), (x+6,y), 1)
    glare = pygame.Surface((WIDTH, int(WAVE_AMPLITUDE*3)), pygame.SRCALPHA)
    for y in range(glare.get_height()):
        alpha = max(0, 60 - int((y / glare.get_height()) * 60))
        pygame.draw.line(glare, (255,255,255,alpha), (0,y), (WIDTH,y))
    surf.blit(glare, (0, SURFACE_Y - glare.get_height()//2), special_flags=pygame.BLEND_PREMULTIPLIED)
    surface.blit(surf, (0,0))

# Toxicity layer
def draw_toxicity(surface):
    tox_zone = 0.6; max_tox = 0.9
    tox_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for y in range(int(HEIGHT * tox_zone), HEIGHT):
        depth = y / HEIGHT
        ti = min(1.0, (depth - tox_zone) / (max_tox - tox_zone))
        if ti < 0.33:
            color = TOXIC_GREEN; alpha = int(36 * ti * 3)
        elif ti < 0.66:
            color = TOXIC_YELLOW; alpha = int(56 * (ti - 0.33) * 3)
        else:
            color = TOXIC_RED; alpha = int(72 * (ti - 0.66) * 3)
        pygame.draw.rect(tox_surf, (*color, alpha), (0, y, WIDTH, 1))
    surface.blit(tox_surf, (0,0))

# Dynamic analysis bins: 1m bins up to TOTAL_DEPTH
def analyze_nanoparticles(particles):
    max_depth = max(1, int(round(TOTAL_DEPTH)))
    depth_ranges = [(i, i+1) for i in range(0, max_depth)]
    counts = [0]*len(depth_ranges)
    pixels_per_meter = HEIGHT / TOTAL_DEPTH
    for p in particles:
        if p.ptype == 1:
            depth_m = p.y / pixels_per_meter
            bin_i = int(depth_m)
            if 0 <= bin_i < len(counts):
                counts[bin_i] += 1
    labels_counts = [(f"{s}-{e}m", c) for (s,e), c in zip(depth_ranges, counts)]
    return labels_counts

font = pygame.font.SysFont('Arial', 16)
title_font = pygame.font.SysFont('Arial', 20, bold=True)

def draw_ui(surface, fps, particle_speed, particles):
    # Legend
    key_w, key_h = 280, 190
    key_surf = pygame.Surface((key_w, key_h), pygame.SRCALPHA)
    key_surf.fill((*PANEL_BG, 220))
    title = title_font.render("Nanoparticle Simulation", True, WHITE)
    key_surf.blit(title, (10,10))
    pygame.draw.circle(key_surf, BUBBLE_COLOR, (15,45), 5); key_surf.blit(font.render("Bubbles", True, WHITE), (30,40))
    pygame.draw.circle(key_surf, NANO_COLOR, (15,65), 3); key_surf.blit(font.render("Nanoparticles", True, WHITE), (30,60))
    pygame.draw.circle(key_surf, TOXIC_YELLOW, (15,80), 3); key_surf.blit(font.render("Toxic Nanoparticles", True, WHITE), (30,75))
    pygame.draw.circle(key_surf, TOXIC_RED, (15,95), 3); key_surf.blit(font.render("Highly Toxic", True, WHITE), (30,90))
    points = [(15,110),(13,115),(17,115)]; pygame.draw.polygon(key_surf, DEBRIS_COLOR, points); key_surf.blit(font.render("Organic Debris", True, WHITE), (30,108))
    pygame.draw.rect(key_surf, TOXIC_GREEN, (10,130,15,5)); pygame.draw.rect(key_surf, TOXIC_YELLOW, (10,135,15,5)); pygame.draw.rect(key_surf, TOXIC_RED, (10,140,15,5))
    key_surf.blit(font.render("Toxicity Gradient", True, WHITE), (30,132))
    pygame.draw.line(key_surf, (150,150,255), (10,155),(25,155),2); key_surf.blit(font.render("Water Currents", True, WHITE),(30,148))
    surface.blit(key_surf, (WIDTH - key_w - 10, 10))

    # Depth meter
    meter_w, meter_h = 130, HEIGHT - 60
    meter_surf = pygame.Surface((meter_w, meter_h), pygame.SRCALPHA); meter_surf.fill((*PANEL_BG,200))
    for y in range(meter_h):
        depth = y / meter_h
        r = int(DEEP_BLUE[0] + (SHALLOW_BLUE[0] - DEEP_BLUE[0]) * (1 - depth))
        g = int(DEEP_BLUE[1] + (SHALLOW_BLUE[1] - DEEP_BLUE[1]) * (1 - depth))
        b = int(DEEP_BLUE[2] + (SHALLOW_BLUE[2] - DEEP_BLUE[2]) * (1 - depth))
        pygame.draw.line(meter_surf, (r,g,b), (5,y), (35,y))
    toxicity_start = int(meter_h * 0.6); toxicity_mid = int(meter_h * 0.77); toxicity_high = int(meter_h * 0.9)
    pygame.draw.line(meter_surf, TOXIC_GREEN, (35,toxicity_start), (45,toxicity_start),2)
    pygame.draw.line(meter_surf, TOXIC_YELLOW, (35,toxicity_mid), (45,toxicity_mid),2)
    pygame.draw.line(meter_surf, TOXIC_RED, (35,toxicity_high), (45,toxicity_high),2)
    meter_surf.blit(font.render("0m", True, WHITE), (50,0))
    mid_y = meter_h//2; meter_surf.blit(font.render(f"{TOTAL_DEPTH/2:.0f}m", True, WHITE), (50, mid_y - 8))
    meter_surf.blit(font.render(f"{TOTAL_DEPTH:.0f}m", True, WHITE), (50, meter_h - 16))
    meter_surf.blit(font.render("Low", True, TOXIC_GREEN), (50, toxicity_start - 8))
    meter_surf.blit(font.render("Med", True, TOXIC_YELLOW), (50, toxicity_mid - 8))
    meter_surf.blit(font.render("High", True, TOXIC_RED), (50, toxicity_high - 8))
    surface.blit(meter_surf, (10,30))

    # Depth analysis
    analysis_w, analysis_h = 300, 170
    analysis_surf = pygame.Surface((analysis_w, analysis_h), pygame.SRCALPHA); analysis_surf.fill((*PANEL_BG,200))
    analysis_title = title_font.render("Nanoparticle Depth Analysis (1m bins)", True, WHITE); analysis_surf.blit(analysis_title, (10,8))
    depth_data = analyze_nanoparticles(particles)
    y0 = 35
    for i, (depth_range, count) in enumerate(depth_data[:6]):  # show up to 6 lines to keep compact
        y_pos = y0 + i * 20
        color = SHALLOW_BLUE if i == 0 else MID_BLUE if i == 1 else DEEP_BLUE
        pygame.draw.rect(analysis_surf, color, (10, y_pos, 15, 12))
        analysis_surf.blit(font.render(f"{depth_range}: {count} particles", True, WHITE), (30, y_pos))
    surface.blit(analysis_surf, (WIDTH - analysis_w - 10, 210))

    # Status line & inputs shown
    surface.blit(font.render(f"Speed: {particle_speed:.1f} | Particles: {PARTICLE_COUNT}", True, WHITE), (10,10))
    if lat is not None and lon is not None:
        surface.blit(font.render(f"Location: {lat:.2f}, {lon:.2f}", True, WHITE), (10, HEIGHT - 60))
    if measurement is not None:
        surface.blit(font.render(f"Microplastics: {measurement:.1f}", True, WHITE), (10, HEIGHT - 40))
    if TOTAL_DEPTH is not None:
        surface.blit(font.render(f"Sample depth: {TOTAL_DEPTH:.1f} m", True, WHITE), (10, HEIGHT - 20))
    if SHOW_FPS:
        surface.blit(font.render(f"FPS: {fps:.1f}", True, WHITE), (WIDTH - 100, 10))

# Create particles (bias nanoparticles near surface)
flow_field = FlowField()
particles = []
for _ in range(PARTICLE_COUNT):
    ptype = random.choices([0,1,2], weights=[0.2,0.6,0.2])[0]
    if ptype == 1:
        y = random.randint(max(5, SURFACE_Y+2), int(HEIGHT * 0.25))
    else:
        y = random.randint(0, HEIGHT)
    x = random.randint(0, WIDTH)
    particles.append(Particle(x, y, ptype))

# Main loop
running = True
wave_phase = 0.0
while running:
    dt = clock.get_time() / 1000.0
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                paused = not paused
            elif event.key == pygame.K_ESCAPE:
                running = False
            elif event.key == pygame.K_f:
                SHOW_FPS = not SHOW_FPS
            elif event.key == pygame.K_UP:
                PARTICLE_SPEED += 0.2
            elif event.key == pygame.K_DOWN:
                PARTICLE_SPEED = max(0.2, PARTICLE_SPEED - 0.2)
    if not paused:
        flow_field.update()
        screen.blit(background, (0,0))
        screen.blit(cached_rays, (0,0))
        draw_toxicity(screen)
        flow_field.draw_currents(screen)
        wave_phase += WAVE_SPEED

        for p in particles:
            p.update(flow_field, PARTICLE_SPEED)
            p.draw(screen, wave_phase)

        draw_surface(screen, wave_phase)

        fps_val = clock.get_fps()
        draw_ui(screen, fps_val, PARTICLE_SPEED, particles)
        pygame.display.flip()
    clock.tick(FPS_TARGET)

pygame.quit()
sys.exit()
