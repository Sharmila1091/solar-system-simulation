import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import math
import random
import sys

WIDTH, HEIGHT = 1280, 720

PLANET_DATA = [
    {"name": "Mercury", "color": (0.72, 0.72, 0.72), "size": 0.38,
     "orbit": 8.5,  "speed": 4.74, "angle": random.uniform(0, 360)},
    {"name": "Venus",   "color": (0.93, 0.80, 0.38), "size": 0.95,
     "orbit": 13.0, "speed": 3.50, "angle": random.uniform(0, 360)},
    {"name": "Earth",   "color": (0.22, 0.55, 0.95), "size": 1.00,
     "orbit": 18.0, "speed": 3.00, "angle": random.uniform(0, 360)},
    {"name": "Mars",    "color": (0.82, 0.32, 0.12), "size": 0.55,
     "orbit": 24.0, "speed": 2.40, "angle": random.uniform(0, 360)},
    {"name": "Jupiter", "color": (0.83, 0.65, 0.43), "size": 2.60,
     "orbit": 35.0, "speed": 1.30, "angle": random.uniform(0, 360)},
    {"name": "Saturn",  "color": (0.92, 0.87, 0.58), "size": 2.10,
     "orbit": 46.0, "speed": 0.97, "angle": random.uniform(0, 360),
     "rings": True},
    {"name": "Uranus",  "color": (0.55, 0.92, 0.95), "size": 1.65,
     "orbit": 57.0, "speed": 0.68, "angle": random.uniform(0, 360)},
    {"name": "Neptune", "color": (0.22, 0.32, 0.95), "size": 1.55,
     "orbit": 67.0, "speed": 0.54, "angle": random.uniform(0, 360)},
]

STARS = [
    (random.uniform(-220, 220),
     random.uniform(-110, 110),
     random.uniform(-220, -5),
     random.uniform(0.45, 1.0))
    for _ in range(3500)
]

# ── Moon state ────────────────────────────────────────────────────────────────
moon = {"angle": random.uniform(0, 360), "speed": 13.0, "orbit": 2.2, "size": 0.27}

# ── Comets ────────────────────────────────────────────────────────────────────
class Comet:
    def __init__(self):
        self.reset(initial=True)

    def reset(self, initial=False):
        side = random.choice(['left','right','top','bottom'])
        r = random.uniform(55, 80)
        if side == 'left':
            self.x, self.z = -r, random.uniform(-r*0.4, r*0.4)
        elif side == 'right':
            self.x, self.z =  r, random.uniform(-r*0.4, r*0.4)
        elif side == 'top':
            self.x, self.z = random.uniform(-r*0.4, r*0.4), -r
        else:
            self.x, self.z = random.uniform(-r*0.4, r*0.4),  r

        if initial:
            self.x = random.uniform(-70, 70)
            self.z = random.uniform(-70, 70)

        tx = random.uniform(-10, 10)
        tz = random.uniform(-10, 10)
        dx, dz = tx - self.x, tz - self.z
        mag = math.sqrt(dx*dx + dz*dz) or 1
        spd = random.uniform(0.18, 0.40)
        self.vx = dx/mag * spd
        self.vz = dz/mag * spd
        self.vy = random.uniform(-0.04, 0.04)
        self.y  = random.uniform(-3, 3)

        self.tail_len = random.randint(28, 55)
        self.size     = random.uniform(0.18, 0.38)
        self.tail_col = (
            random.uniform(0.7, 1.0),
            random.uniform(0.8, 1.0),
            random.uniform(0.9, 1.0),
        )
        self.trail = []
        self.alive = True

    def update(self, dt, speed_mult):
        s = speed_mult * 60 * dt
        self.x += self.vx * s
        self.y += self.vy * s
        self.z += self.vz * s
        self.trail.append((self.x, self.y, self.z))
        if len(self.trail) > self.tail_len:
            self.trail.pop(0)
        if abs(self.x) > 100 or abs(self.z) > 100:
            self.reset()

    def draw(self):
        if len(self.trail) < 2:
            return
        glDisable(GL_LIGHTING)
        glDisable(GL_FOG)

        glBegin(GL_LINE_STRIP)
        for i, (tx, ty, tz) in enumerate(self.trail):
            alpha = (i / len(self.trail)) * 0.85
            glColor4f(*self.tail_col, alpha)
            glVertex3f(tx, ty, tz)
        glEnd()

        glBlendFunc(GL_SRC_ALPHA, GL_ONE)
        glDisable(GL_DEPTH_TEST)
        for gi in range(4):
            gs = self.size * (1.0 + gi * 0.7)
            al = 0.35 - gi * 0.07
            glColor4f(*self.tail_col, al)
            q = gluNewQuadric()
            glPushMatrix()
            glTranslatef(self.x, self.y, self.z)
            gluSphere(q, gs, 8, 8)
            gluDeleteQuadric(q)
            glPopMatrix()
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_DEPTH_TEST)

        glColor3f(0.95, 0.97, 1.0)
        q = gluNewQuadric()
        glPushMatrix()
        glTranslatef(self.x, self.y, self.z)
        gluSphere(q, self.size * 0.6, 10, 10)
        gluDeleteQuadric(q)
        glPopMatrix()

        glEnable(GL_FOG)
        glEnable(GL_LIGHTING)

# spawn 3 comets
COMETS = [Comet() for _ in range(3)]

cam = {"z": -72, "x": 0.0, "y": 0.0, "rot_x": 22.0, "rot_y": 0.0}
app = {"paused": False, "speed": 1.0, "time": 0.0,
       "fog": True, "info_name": None, "info_timer": 0,
       "info_sx": 0, "info_sy": 0}


def draw_sphere(r, slices=24, stacks=24):
    q = gluNewQuadric()
    gluSphere(q, r, slices, stacks)
    gluDeleteQuadric(q)

def draw_orbit_ring(radius):
    glDisable(GL_LIGHTING)
    glColor4f(1.0, 1.0, 1.0, 0.13)
    glBegin(GL_LINE_LOOP)
    for i in range(360):
        a = math.radians(i)
        glVertex3f(math.cos(a) * radius, 0.0, math.sin(a) * radius)
    glEnd()
    glEnable(GL_LIGHTING)

def draw_stars():
    glDisable(GL_LIGHTING)
    glDisable(GL_FOG)
    glPointSize(1.6)
    glBegin(GL_POINTS)
    for x, y, z, b in STARS:
        glColor3f(b, b, min(1.0, b + 0.15))
        glVertex3f(x, y, z)
    glEnd()
    glEnable(GL_FOG)
    glEnable(GL_LIGHTING)

def draw_sun(t):
    glDisable(GL_LIGHTING)
    glDisable(GL_DEPTH_TEST)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE)
    for i in range(7):
        alpha = 0.055 - i * 0.006
        size  = 3.3  + i * 1.1
        glColor4f(1.0, 0.55 + i * 0.03, 0.0, alpha)
        draw_sphere(size, 16, 16)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glEnable(GL_DEPTH_TEST)
    glPushMatrix()
    glRotatef(t * 15, 0, 1, 0)
    glColor3f(1.0, 0.96, 0.15)
    draw_sphere(3.0, 32, 32)
    glPopMatrix()
    glEnable(GL_LIGHTING)

def draw_saturn_rings(size):
    glDisable(GL_LIGHTING)
    glColor4f(0.87, 0.77, 0.52, 0.38)
    glBegin(GL_TRIANGLE_STRIP)
    inner = size * 1.45
    outer = size * 2.65
    for i in range(361):
        a = math.radians(i)
        c, s = math.cos(a), math.sin(a)
        glVertex3f(c * inner, 0.0, s * inner)
        glVertex3f(c * outer, 0.0, s * outer)
    glEnd()
    glEnable(GL_LIGHTING)

def draw_planet(planet, t):
    a  = math.radians(planet["angle"])
    px = math.cos(a) * planet["orbit"]
    pz = math.sin(a) * planet["orbit"]
    c  = planet["color"]
    glPushMatrix()
    glTranslatef(px, 0.0, pz)
    glRotatef(t * planet["speed"] * 40, 0, 1, 0)
    glColor3f(*c)
    glMaterialfv(GL_FRONT, GL_SPECULAR,  [0.5, 0.5, 0.5, 1.0])
    glMaterialfv(GL_FRONT, GL_EMISSION,  [0.0, 0.0, 0.0, 1.0])
    glMaterialf (GL_FRONT, GL_SHININESS, 48.0)
    draw_sphere(planet["size"], 28, 28)
    if planet.get("rings"):
        glRotatef(27, 1, 0, 0)
        draw_saturn_rings(planet["size"])
    glPopMatrix()

# ── Moon drawing ──────────────────────────────────────────────────────────────
def draw_moon(earth, t):
    ea = math.radians(earth["angle"])
    ex = math.cos(ea) * earth["orbit"]
    ez = math.sin(ea) * earth["orbit"]

    ma = math.radians(moon["angle"])
    mx_ = ex + math.cos(ma) * moon["orbit"]
    mz_ = ez + math.sin(ma) * moon["orbit"]

    glDisable(GL_LIGHTING)
    glColor4f(1.0, 1.0, 1.0, 0.07)
    glBegin(GL_LINE_LOOP)
    for i in range(60):
        a = math.radians(i * 6)
        glVertex3f(ex + math.cos(a)*moon["orbit"], 0.0,
                   ez + math.sin(a)*moon["orbit"])
    glEnd()
    glEnable(GL_LIGHTING)

    glPushMatrix()
    glTranslatef(mx_, 0.0, mz_)
    glColor3f(0.80, 0.80, 0.78)
    glMaterialfv(GL_FRONT, GL_SPECULAR,  [0.2, 0.2, 0.2, 1.0])
    glMaterialfv(GL_FRONT, GL_EMISSION,  [0.0, 0.0, 0.0, 1.0])
    glMaterialf (GL_FRONT, GL_SHININESS, 10.0)
    draw_sphere(moon["size"], 14, 14)
    glPopMatrix()


# ── HUD ───────────────────────────────────────────────────────────────────────
def _make_text_surface(font, text, color):
    surf = font.render(text, True, color)
    surf = pygame.transform.flip(surf, False, True)
    return surf

def _surf_to_texture(surf):
    w, h = surf.get_size()
    data = pygame.image.tostring(surf, "RGBA", True)
    tid  = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tid)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0,
                 GL_RGBA, GL_UNSIGNED_BYTE, data)
    return tid, w, h

def _blit_texture(tid, x, y, w, h):
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, tid)
    glColor4f(1, 1, 1, 1)
    glBegin(GL_QUADS)
    glTexCoord2f(0, 0); glVertex2f(x,     y)
    glTexCoord2f(1, 0); glVertex2f(x + w, y)
    glTexCoord2f(1, 1); glVertex2f(x + w, y + h)
    glTexCoord2f(0, 1); glVertex2f(x,     y + h)
    glEnd()
    glDisable(GL_TEXTURE_2D)

def draw_hud(fonts):
    font_sm, font_lg = fonts
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    glOrtho(0, WIDTH, HEIGHT, 0, -1, 1)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glDisable(GL_DEPTH_TEST)
    glDisable(GL_LIGHTING)
    glDisable(GL_FOG)

    # title
    title_surf = _make_text_surface(font_lg, "Solar System Simulation", (255, 215, 50))
    tid, tw, th = _surf_to_texture(title_surf)
    _blit_texture(tid, 12, 12, tw, th)
    glDeleteTextures([tid])

    # planet name above clicked planet
    if app["info_name"] and app["info_timer"] > 0:
        alpha_ratio = min(1.0, app["info_timer"] / 30)
        gv = int(255 * alpha_ratio)
        name_surf = _make_text_surface(font_lg, app["info_name"], (255, gv, 60))
        tid, tw, th = _surf_to_texture(name_surf)
        nx = max(4, min(WIDTH  - tw - 4, int(app["info_sx"] - tw // 2)))
        ny = max(4, min(HEIGHT - th - 4, int(app["info_sy"] - th - 10)))
        _blit_texture(tid, nx, ny, tw, th)
        glDeleteTextures([tid])

    # speed indicator
    if app["paused"]:
        spd_text  = "II  PAUSED"
        spd_color = (255, 80, 80)
    else:
        spd_text  = f"SPD  {app['speed']:.1f}x"
        t_spd = (app["speed"] - 0.1) / (12.0 - 0.1)
        sr = int(80  + 175 * min(1.0, t_spd * 2))
        sg = int(220 - 140 * min(1.0, t_spd * 2))
        spd_color = (sr, sg, 60)

    spd_surf = _make_text_surface(font_lg, spd_text, spd_color)
    tid, tw, th = _surf_to_texture(spd_surf)
    _blit_texture(tid, 12, HEIGHT - th - 12, tw, th)
    glDeleteTextures([tid])

    bar_w  = 160; bar_h = 5; bar_x = 12
    bar_y  = HEIGHT - th - 20
    filled = int(bar_w * min(1.0, (app["speed"] - 0.1) / (12.0 - 0.1)))
    glDisable(GL_TEXTURE_2D)
    glColor4f(1.0, 1.0, 1.0, 0.15)
    glBegin(GL_QUADS)
    glVertex2f(bar_x,         bar_y); glVertex2f(bar_x+bar_w, bar_y)
    glVertex2f(bar_x+bar_w,   bar_y+bar_h); glVertex2f(bar_x, bar_y+bar_h)
    glEnd()
    t_fill = filled / max(1, bar_w)
    glColor4f(min(1.0,t_fill*2), max(0.0,1.0-t_fill), 0.2, 0.85)
    glBegin(GL_QUADS)
    glVertex2f(bar_x,        bar_y); glVertex2f(bar_x+filled, bar_y)
    glVertex2f(bar_x+filled, bar_y+bar_h); glVertex2f(bar_x,  bar_y+bar_h)
    glEnd()

    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)
    if app["fog"]: glEnable(GL_FOG)
    glMatrixMode(GL_PROJECTION); glPopMatrix()
    glMatrixMode(GL_MODELVIEW);  glPopMatrix()


def check_click(mx, my):
    vp  = glGetIntegerv(GL_VIEWPORT)
    mv  = glGetDoublev(GL_MODELVIEW_MATRIX)
    prj = glGetDoublev(GL_PROJECTION_MATRIX)
    try:
        wx, wy, _ = gluProject(0, 0, 0, mv, prj, vp)
        sy = HEIGHT - wy
        if math.hypot(mx - wx, my - sy) < 36:
            return "Sun", int(wx), int(sy)
    except Exception:
        pass
    for planet in PLANET_DATA:
        a  = math.radians(planet["angle"])
        px = math.cos(a) * planet["orbit"]
        pz = math.sin(a) * planet["orbit"]
        try:
            wx, wy, _ = gluProject(px, 0, pz, mv, prj, vp)
            sy = HEIGHT - wy
            if math.hypot(mx - wx, my - sy) < max(14, planet["size"] * 18):
                return planet["name"], int(wx), int(sy)
        except Exception:
            pass

    # Moon click detection
    try:
        earth   = next(p for p in PLANET_DATA if p["name"] == "Earth")
        ea      = math.radians(earth["angle"])
        ex      = math.cos(ea) * earth["orbit"]
        ez      = math.sin(ea) * earth["orbit"]
        ma      = math.radians(moon["angle"])
        mx_     = ex + math.cos(ma) * moon["orbit"]
        mz_     = ez + math.sin(ma) * moon["orbit"]
        wx, wy, _ = gluProject(mx_, 0, mz_, mv, prj, vp)
        sy = HEIGHT - wy
        if math.hypot(mx - wx, my - sy) < 16:
            return "Moon", int(wx), int(sy)
    except Exception:
        pass

    return None, 0, 0


def init_gl():
    glViewport(0, 0, WIDTH, HEIGHT)
    glMatrixMode(GL_PROJECTION); glLoadIdentity()
    gluPerspective(45.0, WIDTH / HEIGHT, 0.1, 500.0)
    glMatrixMode(GL_MODELVIEW)
    glEnable(GL_DEPTH_TEST); glDepthFunc(GL_LEQUAL)
    glShadeModel(GL_SMOOTH)
    glEnable(GL_LIGHTING); glEnable(GL_LIGHT0)
    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
    glLightModelfv(GL_LIGHT_MODEL_AMBIENT, [0.05, 0.05, 0.08, 1.0])
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glEnable(GL_FOG)
    glFogi(GL_FOG_MODE, GL_LINEAR)
    glFogfv(GL_FOG_COLOR, [0.0, 0.0, 0.025, 1.0])
    glFogf(GL_FOG_START, 65.0); glFogf(GL_FOG_END, 190.0)
    glHint(GL_FOG_HINT, GL_NICEST)
    glEnable(GL_POINT_SMOOTH)
    glHint(GL_POINT_SMOOTH_HINT, GL_NICEST)
    glLineWidth(1.4)


def main():
    pygame.init()
    pygame.display.set_mode((WIDTH, HEIGHT), DOUBLEBUF | OPENGL)
    pygame.display.set_caption("Solar System Simulation")
    pygame.font.init()
    init_gl()

    font_sm = pygame.font.SysFont("Consolas", 15)
    font_lg = pygame.font.SysFont("Consolas", 23, bold=True)
    fonts   = (font_sm, font_lg)
    clock   = pygame.time.Clock()
    earth   = next(p for p in PLANET_DATA if p["name"] == "Earth")

    while True:
        dt = clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit(); sys.exit()
            if event.type == KEYDOWN:
                if   event.key == K_ESCAPE:  pygame.quit(); sys.exit()
                elif event.key == K_SPACE:   app["paused"] = not app["paused"]
                elif event.key in (K_EQUALS, K_PLUS, K_KP_PLUS):
                    app["speed"] = min(app["speed"] * 1.5, 12.0)
                elif event.key in (K_MINUS, K_KP_MINUS):
                    app["speed"] = max(app["speed"] / 1.5, 0.1)
                elif event.key == K_f:
                    app["fog"] = not app["fog"]
                    if app["fog"]: glEnable(GL_FOG)
                    else:          glDisable(GL_FOG)
            if event.type == MOUSEBUTTONDOWN and event.button == 1:
                name, sx, sy = check_click(*event.pos)
                if name:
                    app["info_name"]  = name
                    app["info_timer"] = 100
                    app["info_sx"]    = sx
                    app["info_sy"]    = sy

        keys = pygame.key.get_pressed()
        if keys[K_LEFT]:  cam["rot_y"] -= 1.6
        if keys[K_RIGHT]: cam["rot_y"] += 1.6
        if keys[K_UP]:    cam["rot_x"] = max(-88, cam["rot_x"] - 1.6)
        if keys[K_DOWN]:  cam["rot_x"] = min( 88, cam["rot_x"] + 1.6)
        if keys[K_w]:     cam["z"]     = min(-8,   cam["z"] + 0.55)
        if keys[K_s]:     cam["z"]     = max(-200, cam["z"] - 0.55)
        if keys[K_a]:     cam["x"]    += 0.35
        if keys[K_d]:     cam["x"]    -= 0.35

        if not app["paused"]:
            app["time"] += dt * app["speed"]
            for p in PLANET_DATA:
                p["angle"] = (p["angle"] + p["speed"] * dt * app["speed"] * 8) % 360
            moon["angle"] = (moon["angle"] + moon["speed"] * dt * app["speed"] * 8) % 360
            for c in COMETS:
                c.update(dt, app["speed"])

        if app["info_timer"] > 0:
            app["info_timer"] -= 1

        glClearColor(0.0, 0.0, 0.018, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()

        glTranslatef(cam["x"], cam["y"], cam["z"])
        glRotatef(cam["rot_x"], 1, 0, 0)
        glRotatef(cam["rot_y"], 0, 1, 0)

        glLightfv(GL_LIGHT0, GL_POSITION,             [0.0, 1.0, 0.0, 1.0])
        glLightfv(GL_LIGHT0, GL_DIFFUSE,              [1.0, 1.0, 0.95, 1.0])
        glLightfv(GL_LIGHT0, GL_SPECULAR,             [0.9, 0.85, 0.65, 1.0])
        glLightfv(GL_LIGHT0, GL_AMBIENT,              [0.07, 0.07, 0.10, 1.0])
        glLightf (GL_LIGHT0, GL_CONSTANT_ATTENUATION,  0.35)
        glLightf (GL_LIGHT0, GL_LINEAR_ATTENUATION,    0.007)
        glLightf (GL_LIGHT0, GL_QUADRATIC_ATTENUATION, 0.00015)

        draw_stars()
        for planet in PLANET_DATA:
            draw_orbit_ring(planet["orbit"])
        draw_sun(app["time"])
        for planet in PLANET_DATA:
            draw_planet(planet, app["time"])

        draw_moon(earth, app["time"])

        for c in COMETS:
            c.draw()

        draw_hud(fonts)
        pygame.display.flip()

if __name__ == "__main__":
    main()
