"""Beyond the Edge -- procedural Blender scene builder.

Run:  blender -b --python build_scene.py -- [--out scene.blend] [--res 1920x1080] [--samples 24]

Builds everything from code: mountain terrain with a cliffside road, guardrail,
pine forest, a river valley, a black GT3 RS-style coupe, a scripted crash with
breakaway barrier, sparks and debris, five camera setups (eight cameras,
cut by timeline markers), golden-hour Nishita sky, and a compositor haze and
anamorphic-streak pass. 15 s @ 24 fps = 360 frames.
"""
import bpy, bmesh, math, sys, random
import numpy as np
from mathutils import Vector, Matrix, Euler, Quaternion

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
def arg(name, default):
    return argv[argv.index(name) + 1] if name in argv else default

OUT = arg("--out", "/tmp/beyond_the_edge.blend")
RES = [int(v) for v in arg("--res", "1920x1080").split("x")]
SAMPLES = int(arg("--samples", "24"))
FPS = 24
NFR = 360
G = 9.81
rng = np.random.default_rng(7)
random.seed(7)

# ----------------------------------------------------------------- reset
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.fps = FPS
sc.frame_start, sc.frame_end = 1, NFR
bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'

def link(obj, coll=None):
    (coll or sc.collection).objects.link(obj)
    return obj

_QPREV = {}
def qcont(key, q):
    p = _QPREV.get(key)
    if p is not None and p.dot(q) < 0:
        q = -q
    _QPREV[key] = q.copy()
    return q

# ----------------------------------------------------------------- noise
def _hash(ix, iy, seed):
    h = (ix.astype(np.int64) * 374761393 + iy.astype(np.int64) * 668265263 + seed * 144269504) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    h = h ^ (h >> 16)
    return h.astype(np.float64) / 4294967296.0

def vnoise(x, y, seed=0):
    ix, iy = np.floor(x), np.floor(y)
    fx, fy = x - ix, y - iy
    ux, uy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a = _hash(ix, iy, seed); b = _hash(ix + 1, iy, seed)
    c = _hash(ix, iy + 1, seed); d = _hash(ix + 1, iy + 1, seed)
    return (a + (b - a) * ux + (c - a) * uy + (a - b - c + d) * ux * uy) * 2 - 1

def fbm(x, y, oct=5, seed=0, gain=0.5):
    s, amp, f, norm = 0.0, 1.0, 1.0, 0.0
    for o in range(oct):
        s = s + amp * vnoise(x * f + 17.3 * o, y * f - 9.1 * o, seed + o * 31)
        norm += amp; amp *= gain; f *= 2.03
    return s / norm

def ridged(x, y, oct=5, seed=0):
    s, amp, f, norm = 0.0, 1.0, 1.0, 0.0
    for o in range(oct):
        n = 1 - np.abs(vnoise(x * f + 5.1 * o, y * f + 3.7 * o, seed + 97 + o * 13))
        s = s + amp * n * n
        norm += amp; amp *= 0.5; f *= 2.1
    return s / norm

def smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)

# ----------------------------------------------------------------- road
XB, WB, KB = 262.0, 7.0, 1.6           # bend position / width / final slope

def road_y(x):
    x = np.asarray(x, dtype=float)
    win = 1 - smooth(-20, 130, x)
    wig = 24 * np.sin(x / 70) + 14 * np.sin(x / 37 + 1.0)
    sp = np.logaddexp(0, (x - XB) / WB) * WB * KB
    return win * wig + sp

def road_dy(x):
    e = 0.01
    return (road_y(x + e) - road_y(x - e)) / (2 * e)

def road_z(x):
    return 160 + 0.022 * (np.asarray(x, dtype=float) + 900)

# dense arclength-parameterised samples
_xs = np.linspace(-1100, 720, 400001)
_ys = road_y(_xs)
_seg = np.hypot(np.diff(_xs), np.diff(_ys))
_s = np.concatenate([[0], np.cumsum(_seg)])

def road_at_s(s):
    x = np.interp(s, _s, _xs)
    y = road_y(x); dy = road_dy(x)
    th = np.arctan2(dy, 1.0)
    return x, y, road_z(x), th

def s_at_x(x):
    return float(np.interp(x, _xs, _s))

def road_offset_point(s, v):
    x, y, z, th = road_at_s(s)
    return x - v * np.sin(th), y + v * np.cos(th), z

def signed_dist(px, py):
    """Exact signed distance (+ = mountain side / left) to the road centreline."""
    i = int(np.argmin((_xs - px) ** 2 + (_ys - py) ** 2))
    th = math.atan2(float(road_dy(_xs[i])), 1.0)
    nx, ny = -math.sin(th), math.cos(th)
    return (px - _xs[i]) * nx + (py - _ys[i]) * ny, i

# ----------------------------------------------------------------- terrain
def axis(segments):
    out = []
    for a, b, step in segments:
        out.append(np.arange(a, b, step))
    v = np.unique(np.concatenate(out + [np.array([segments[-1][1]])]))
    return v

def geo(a, b, n, first, toward_b=True):
    # geometric spacing from a toward b starting at 'first'
    L = abs(b - a); r = (L / first) ** (1.0 / n)
    t = np.cumsum(first * r ** np.arange(n)); t = t / t[-1] * L
    return a + np.sign(b - a) * t

XAX = np.unique(np.concatenate([geo(-1000, -6000, 45, 1.6)[::-1], axis([(-1000, 520, 1.6)]), geo(520, 6000, 45, 1.6)]))
YAX = np.unique(np.concatenate([geo(-470, -6000, 45, 4.0)[::-1], axis([(-470, -60, 4.0), (-60, 300, 1.6)]), geo(300, 6000, 40, 1.6)]))

def valley_floor(X, Y):
    yr = -330 + 60 * np.sin(X / 400) + 25 * np.sin(X / 150 + 2)
    h = 16 + 9 * fbm(X / 260, Y / 260, 4, 3)
    h -= 13 * np.exp(-((Y - yr) / 38) ** 2)
    far = np.clip(-Y - 560, 0, None)
    h += far * 0.42 * (1 + 0.5 * fbm(X / 700, Y / 700, 3, 5)) + 520 * ridged(X / 900, Y / 900, 5, 8) * smooth(-560, -1800, Y)
    # left/right flanks of the valley so the horizon is mountains everywhere
    side = np.clip(np.abs(X - 200) - 2000, 0, None)
    h += side * 0.16 + 750 * ridged(X / 650 + 3.3, Y / 650, 5, 17) * smooth(0, 900, side)
    return h

def terrain_height(X, Y):
    fx = road_y(X); fp = road_dy(X)
    d = (Y - fx) / np.sqrt(1 + fp * fp)
    zr = road_z(X)
    H = np.full_like(X, 0.0)
    # mountain side
    t = np.clip(d - 6.5, 0, None)
    rise = 7 * smooth(0, 3.5, t) + 0.5 * t + 0.0011 * t * t
    rise *= 1 + 0.35 * fbm(X / 320, Y / 320, 3, 11)
    rise += 260 * ridged(X / 520, Y / 520, 5, 2) * smooth(15, 320, t)
    rise += 3.5 * fbm(X / 18, Y / 18, 4, 4) * smooth(0, 6, t)
    Hm = zr + rise
    # valley side
    tv = np.clip(-d - 6.5, 0, None)
    hv = valley_floor(X, Y)
    csc = 7.5 * (1 + 0.8 * np.abs(fbm(X / 90, Y / 90, 3, 41))) + 10 * np.clip(fbm(X / 300, Y / 300, 2, 43), 0, None)
    drop = (zr - 0.25 - hv) * (1 - np.exp(-np.clip(tv - 1.6, 0, None) / csc))
    Hv = zr - 0.25 - drop
    face = np.exp(-((tv - 16) / 14) ** 2)
    Hv += (10 * fbm(X / 22, Y / 22, 4, 21) + 3 * fbm(X / 5, Y / 5, 2, 22)) * face
    Hv = np.maximum(Hv, hv)
    H = np.where(d > 6.5, Hm, np.where(d < -6.5, Hv, zr - 0.35))
    return H, d

def make_grid_mesh(name, xa, ya, zf):
    X, Y = np.meshgrid(xa, ya)
    Z, D = zf(X, Y)
    nx, ny = len(xa), len(ya)
    verts = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1)
    idx = np.arange(nx * ny).reshape(ny, nx)
    a = idx[:-1, :-1].ravel(); b = idx[:-1, 1:].ravel(); c = idx[1:, 1:].ravel(); dd = idx[1:, :-1].ravel()
    quads = np.stack([a, b, c, dd], 1)
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(verts)); me.vertices.foreach_set("co", verts.astype(np.float32).ravel())
    me.loops.add(quads.size); me.loops.foreach_set("vertex_index", quads.astype(np.int32).ravel())
    me.polygons.add(len(quads))
    me.polygons.foreach_set("loop_start", (np.arange(len(quads)) * 4).astype(np.int32))
    me.polygons.foreach_set("loop_total", np.full(len(quads), 4, np.int32))
    me.update(calc_edges=True); me.validate()
    me.shade_smooth() if hasattr(me, "shade_smooth") else None
    return me, X, Y, Z, D

print("building terrain", len(XAX), "x", len(YAX))
terr_me, TX, TY, TZ, TD = make_grid_mesh("terrain", XAX, YAX, terrain_height)
terrain = link(bpy.data.objects.new("Terrain", terr_me))

def height_at(x, y):
    h, d = terrain_height(np.array([x], float), np.array([y], float))
    return float(h[0])

# ----------------------------------------------------------------- materials
def mat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True
    return m, m.node_tree.nodes, m.node_tree.links, m.node_tree.nodes["Principled BSDF"]

def principled(name, col, rough=0.5, metal=0.0, coat=0.0, emit=None, estr=0.0):
    m, N, L, P = mat(name)
    P.inputs["Base Color"].default_value = (*col, 1)
    P.inputs["Roughness"].default_value = rough
    P.inputs["Metallic"].default_value = metal
    P.inputs["Coat Weight"].default_value = coat
    if emit:
        P.inputs["Emission Color"].default_value = (*emit, 1)
        P.inputs["Emission Strength"].default_value = estr
    return m

def node(N, t, **kw):
    n = N.new(t)
    for k, v in kw.items():
        setattr(n, k, v)
    return n

# terrain: rock vs vegetation by slope, dry grass by height, rocky bump
m_ter, N, L, P = mat("Terrain")
geo_n = node(N, "ShaderNodeNewGeometry")
sep = node(N, "ShaderNodeSeparateXYZ"); L.new(geo_n.outputs["Normal"], sep.inputs[0])
tc = node(N, "ShaderNodeTexCoord")
nz1 = node(N, "ShaderNodeTexNoise"); nz1.inputs["Scale"].default_value = 0.08; nz1.inputs["Detail"].default_value = 8
L.new(tc.outputs["Object"], nz1.inputs["Vector"])
nz2 = node(N, "ShaderNodeTexNoise"); nz2.inputs["Scale"].default_value = 1.3; nz2.inputs["Detail"].default_value = 10
L.new(tc.outputs["Object"], nz2.inputs["Vector"])
slope = node(N, "ShaderNodeMath", operation='ADD'); L.new(sep.outputs["Z"], slope.inputs[0])
mixn = node(N, "ShaderNodeMath", operation='MULTIPLY'); L.new(nz1.outputs["Fac"], mixn.inputs[0]); mixn.inputs[1].default_value = 0.25
L.new(mixn.outputs[0], slope.inputs[1])
ramp_s = node(N, "ShaderNodeValToRGB"); L.new(slope.outputs[0], ramp_s.inputs[0])
ramp_s.color_ramp.elements[0].position = 0.80; ramp_s.color_ramp.elements[0].color = (0, 0, 0, 1)
ramp_s.color_ramp.elements[1].position = 0.95; ramp_s.color_ramp.elements[1].color = (1, 1, 1, 1)
wave = node(N, "ShaderNodeTexWave", bands_direction='Z'); wave.inputs["Scale"].default_value = 0.035
wave.inputs["Distortion"].default_value = 6.0; wave.inputs["Detail"].default_value = 6; wave.inputs["Detail Scale"].default_value = 2.5
L.new(tc.outputs["Object"], wave.inputs["Vector"])
wmul = node(N, "ShaderNodeMath", operation='MULTIPLY'); L.new(wave.outputs["Fac"], wmul.inputs[0]); wmul.inputs[1].default_value = 0.28
strata = node(N, "ShaderNodeMath", operation='MULTIPLY_ADD'); L.new(nz2.outputs["Fac"], strata.inputs[0]); strata.inputs[1].default_value = 0.72; L.new(wmul.outputs[0], strata.inputs[2])
rock = node(N, "ShaderNodeValToRGB"); L.new(strata.outputs[0], rock.inputs[0])
rock.color_ramp.elements[0].color = (0.06, 0.05, 0.042, 1); rock.color_ramp.elements[1].color = (0.30, 0.24, 0.19, 1)
veg = node(N, "ShaderNodeValToRGB"); L.new(nz1.outputs["Fac"], veg.inputs[0])
veg.color_ramp.elements[0].color = (0.030, 0.045, 0.016, 1); veg.color_ramp.elements[1].color = (0.13, 0.12, 0.045, 1)
mixc = node(N, "ShaderNodeMix", data_type='RGBA'); L.new(ramp_s.outputs["Color"], mixc.inputs["Factor"])
L.new(rock.outputs["Color"], mixc.inputs[6]); L.new(veg.outputs["Color"], mixc.inputs[7])
L.new(mixc.outputs[2], P.inputs["Base Color"])
P.inputs["Roughness"].default_value = 0.9
bump = node(N, "ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.8; bump.inputs["Distance"].default_value = 1.2
L.new(strata.outputs[0], bump.inputs["Height"]); L.new(bump.outputs["Normal"], P.inputs["Normal"])
terrain.data.materials.append(m_ter)

# asphalt with painted lines (UV: u = metres along, v = metres across)
m_road, N, L, P = mat("Road")
uvn = node(N, "ShaderNodeUVMap")
sepr = node(N, "ShaderNodeSeparateXYZ"); L.new(uvn.outputs["UV"], sepr.inputs[0])
absv = node(N, "ShaderNodeMath", operation='ABSOLUTE'); L.new(sepr.outputs["Y"], absv.inputs[0])
def band(lo, hi, src):
    g1 = node(N, "ShaderNodeMath", operation='GREATER_THAN'); L.new(src, g1.inputs[0]); g1.inputs[1].default_value = lo
    l1 = node(N, "ShaderNodeMath", operation='LESS_THAN'); L.new(src, l1.inputs[0]); l1.inputs[1].default_value = hi
    m1 = node(N, "ShaderNodeMath", operation='MULTIPLY'); L.new(g1.outputs[0], m1.inputs[0]); L.new(l1.outputs[0], m1.inputs[1])
    return m1.outputs[0]
edge = band(3.72, 3.88, absv.outputs[0])
cen = band(-1, 0.075, absv.outputs[0])
fr = node(N, "ShaderNodeMath", operation='FRACT')
dv = node(N, "ShaderNodeMath", operation='DIVIDE'); L.new(sepr.outputs["X"], dv.inputs[0]); dv.inputs[1].default_value = 9.0
L.new(dv.outputs[0], fr.inputs[0])
dash = node(N, "ShaderNodeMath", operation='LESS_THAN'); L.new(fr.outputs[0], dash.inputs[0]); dash.inputs[1].default_value = 0.42
cd = node(N, "ShaderNodeMath", operation='MULTIPLY'); L.new(cen, cd.inputs[0]); L.new(dash.outputs[0], cd.inputs[1])
lines = node(N, "ShaderNodeMath", operation='MAXIMUM'); L.new(edge, lines.inputs[0]); L.new(cd.outputs[0], lines.inputs[1])
verge = node(N, "ShaderNodeMath", operation='GREATER_THAN'); L.new(absv.outputs[0], verge.inputs[0]); verge.inputs[1].default_value = 4.25
ntx = node(N, "ShaderNodeTexNoise"); ntx.inputs["Scale"].default_value = 3.0; ntx.inputs["Detail"].default_value = 12
L.new(uvn.outputs["UV"], ntx.inputs["Vector"])
asp = node(N, "ShaderNodeValToRGB"); L.new(ntx.outputs["Fac"], asp.inputs[0])
asp.color_ramp.elements[0].color = (0.018, 0.018, 0.019, 1); asp.color_ramp.elements[1].color = (0.06, 0.058, 0.056, 1)
c1 = node(N, "ShaderNodeMix", data_type='RGBA'); L.new(lines.outputs[0], c1.inputs["Factor"])
L.new(asp.outputs["Color"], c1.inputs[6]); c1.inputs[7].default_value = (0.62, 0.6, 0.55, 1)
c2 = node(N, "ShaderNodeMix", data_type='RGBA'); L.new(verge.outputs[0], c2.inputs["Factor"])
L.new(c1.outputs[2], c2.inputs[6]); c2.inputs[7].default_value = (0.11, 0.095, 0.08, 1)
L.new(c2.outputs[2], P.inputs["Base Color"])
rr = node(N, "ShaderNodeMapRange"); L.new(ntx.outputs["Fac"], rr.inputs[0]); rr.inputs[3].default_value = 0.55; rr.inputs[4].default_value = 0.85
L.new(rr.outputs[0], P.inputs["Roughness"])
bmp = node(N, "ShaderNodeBump"); bmp.inputs["Strength"].default_value = 0.25; bmp.inputs["Distance"].default_value = 0.01
L.new(ntx.outputs["Fac"], bmp.inputs["Height"]); L.new(bmp.outputs["Normal"], P.inputs["Normal"])

m_paint = principled("CarPaint", (0.006, 0.006, 0.007), 0.32, 0.55, coat=1.0)
m_paint.node_tree.nodes["Principled BSDF"].inputs["Coat Roughness"].default_value = 0.02
m_glass = principled("Glass", (0.004, 0.005, 0.006), 0.03, 0.0, coat=0.0)
m_glass.node_tree.nodes["Principled BSDF"].inputs["Specular IOR Level"].default_value = 0.9
m_rubber = principled("Rubber", (0.012, 0.012, 0.012), 0.7)
m_rim = principled("Rim", (0.42, 0.42, 0.44), 0.3, 1.0)
m_disc = principled("Disc", (0.35, 0.33, 0.31), 0.4, 1.0)
m_caliper = principled("Caliper", (0.55, 0.012, 0.01), 0.3, 0.0, coat=0.6)
m_carbon = principled("Carbon", (0.012, 0.012, 0.013), 0.25, 0.2, coat=0.8)
m_titan = principled("Titanium", (0.62, 0.48, 0.36), 0.25, 1.0)
m_head = principled("Headlight", (0.8, 0.85, 0.9), 0.05, 0.0, emit=(0.85, 0.9, 1.0), estr=0.0)
m_lens = principled("Lens", (0.9, 0.95, 1.0), 0.02); m_lens.node_tree.nodes["Principled BSDF"].inputs["Transmission Weight"].default_value = 1.0
m_tail = principled("Taillight", (0.4, 0.0, 0.0), 0.1, 0.0, emit=(1.0, 0.02, 0.01), estr=6.0)
m_rail = principled("Guardrail", (0.55, 0.56, 0.57), 0.38, 1.0)
m_post = principled("Post", (0.42, 0.42, 0.43), 0.5, 1.0)
m_spark = principled("Spark", (1, 0.5, 0.1), 0.5, 0.0, emit=(1.0, 0.45, 0.08), estr=60.0)
m_debris = principled("Debris", (0.07, 0.065, 0.06), 0.85)
m_water = principled("Water", (0.01, 0.02, 0.025), 0.04, 0.0)
m_bark = principled("Bark", (0.05, 0.035, 0.022), 0.9)
m_pine = principled("Pine", (0.018, 0.034, 0.016), 0.8)

# ----------------------------------------------------------------- road mesh
def build_road(s0, s1, step=1.0):
    offs = [(-5.75, -1.2), (-5.6, 0.0), (-4.3, 0.0), (-3.9, 0), (-3.7, 0), (-1.5, 0), (0, 0.0),
            (1.5, 0), (3.7, 0), (3.9, 0), (4.3, 0), (5.6, 0.0), (5.75, -1.2)]
    ss = np.arange(s0, s1, step)
    bm = bmesh.new(); uv = bm.loops.layers.uv.new("UVMap")
    rows = []
    for s in ss:
        row = []
        for v, dz in offs:
            x, y, z = road_offset_point(s, v)
            row.append(bm.verts.new((float(x), float(y), float(z + 0.02 + dz))))
        rows.append(row)
    for i in range(len(rows) - 1):
        for j in range(len(offs) - 1):
            f = bm.faces.new((rows[i][j], rows[i][j + 1], rows[i + 1][j + 1], rows[i + 1][j]))
            for lp, (ii, jj) in zip(f.loops, [(i, j), (i, j + 1), (i + 1, j + 1), (i + 1, j)]):
                lp[uv].uv = (float(ss[ii]), float(offs[jj][0]))
    me = bpy.data.meshes.new("road"); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    o = link(bpy.data.objects.new("Road", me)); o.data.materials.append(m_road)
    return o

S_ROAD0, S_ROAD1 = s_at_x(-950), s_at_x(505)
road = build_road(S_ROAD0, S_ROAD1)

# ----------------------------------------------------------------- car model
def loft(name, stations, nring=40, cap=True):
    """stations: list of (x, half_w, z_bot, z_top, side_bulge, n_exp)."""
    bm = bmesh.new(); rings = []
    for (x, w, zb, zt, bul, ne) in stations:
        ring = []
        zc, hz = (zt + zb) / 2, (zt - zb) / 2
        for k in range(nring):
            a = 2 * math.pi * k / nring
            c, s = math.cos(a), math.sin(a)
            y = w * math.copysign(abs(c) ** (2 / ne), c)
            z = zc + hz * math.copysign(abs(s) ** (2 / ne), s)
            if s > 0:
                z += bul * (abs(y) / max(w, 1e-3)) ** 4
            ring.append(bm.verts.new((x, y, z)))
        rings.append(ring)
    for i in range(len(rings) - 1):
        for k in range(nring):
            bm.faces.new((rings[i][k], rings[i][(k + 1) % nring], rings[i + 1][(k + 1) % nring], rings[i + 1][k]))
    if cap:
        bm.faces.new(rings[0][::-1]); bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    return me

def interp_profile(x, pts):
    xs = [p[0] for p in pts]; vs = [p[1] for p in pts]
    return float(np.interp(x, xs, vs))

# profiles along car (x = forward). Values tuned for a 911-ish silhouette.
TOP = [(-2.30, 0.80), (-2.22, 0.90), (-1.95, 0.93), (-1.6, 0.93), (-1.2, 0.95), (0.6, 0.86), (1.0, 0.80), (1.6, 0.74), (2.05, 0.66), (2.25, 0.52), (2.31, 0.40)]
BOT = [(-2.30, 0.36), (-2.15, 0.22), (-1.9, 0.15), (1.9, 0.14), (2.2, 0.20), (2.31, 0.28)]
WID = [(-2.30, 0.82), (-2.15, 0.93), (-1.55, 0.985), (-1.0, 0.975), (-0.5, 0.92), (0.4, 0.91), (0.9, 0.935), (1.35, 0.955), (1.8, 0.93), (2.15, 0.82), (2.31, 0.60)]
BUL = [(-2.3, 0.0), (-1.8, 0.03), (-1.2, 0.05), (-0.6, 0.0), (0.7, 0.0), (1.1, 0.07), (1.7, 0.09), (2.1, 0.05), (2.31, 0.0)]

def build_body():
    xs = np.linspace(-2.30, 2.31, 90)
    st = [(float(x), interp_profile(x, WID), interp_profile(x, BOT), interp_profile(x, TOP), interp_profile(x, BUL), 3.2) for x in xs]
    me = loft("body", st, nring=56)
    return me

# greenhouse: windshield base x=0.78 -> roof -> fastback down to deck
GH_TOP = [(-2.02, 0.93), (-1.6, 1.03), (-1.0, 1.19), (-0.4, 1.285), (0.0, 1.29), (0.25, 1.25), (0.5, 1.10), (0.80, 0.86)]
GH_W = [(-2.02, 0.42), (-1.6, 0.56), (-0.9, 0.64), (0.0, 0.66), (0.5, 0.71), (0.80, 0.74)]

def build_greenhouse():
    xs = np.linspace(-2.0, 0.79, 60)
    st = []
    for x in xs:
        zt = interp_profile(x, GH_TOP); w = interp_profile(x, GH_W)
        zb = interp_profile(x, TOP) - 0.12
        st.append((float(x), w, zb, max(zt, zb + 0.05), 0.0, 3.0))
    return loft("greenhouse", st, nring=48)

def assign_greenhouse_materials(o):
    o.data.materials.append(m_paint); o.data.materials.append(m_glass)
    for p in o.data.polygons:
        c = p.center; n = p.normal
        is_roof = abs(c.y) < 0.46 and n.z > 0.55 and c.x < 0.28
        fastback = c.x < -1.35
        p.material_index = 0 if (is_roof or fastback) else 1
        # low band near deck stays paint
        if c.z < interp_profile(c.x, TOP) + 0.03:
            p.material_index = 0

def boolean_apply(obj, cutter, op='DIFFERENCE'):
    mod = obj.modifiers.new("b", 'BOOLEAN'); mod.operation = op; mod.object = cutter; mod.solver = 'EXACT'
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(obj.evaluated_get(dg))
    obj.modifiers.clear(); old = obj.data; obj.data = me
    bpy.data.meshes.remove(old)

def cyl_mesh(name, r, depth, verts=48, caps=True):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=caps, segments=verts, radius1=r, radius2=r, depth=depth)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); return me

def box(name, sx, sy, sz, loc=(0, 0, 0), m=None, parent=None, rot=(0, 0, 0)):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=bm.verts)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = link(bpy.data.objects.new(name, me)); o.location = loc; o.rotation_euler = rot
    if m: o.data.materials.append(m)
    if parent: o.parent = parent
    return o

def tire_mesh(name, r, width, sidewall=0.11, segs=64):
    # lathe a rounded profile around the Y axis
    prof = []
    rin = r - sidewall; hw = width / 2
    for k in range(13):
        a = -math.pi / 2 + math.pi * k / 12
        prof.append((r - 0.035 + 0.035 * math.cos(a), hw * 0.9 * math.sin(a) + 0.0))
    prof = [(rin, -hw * 0.92)] + [(rr, yy) for rr, yy in prof] + [(rin, hw * 0.92)]
    bm = bmesh.new(); rings = []
    for i in range(segs):
        a = 2 * math.pi * i / segs
        rings.append([bm.verts.new((rr * math.cos(a), yy, rr * math.sin(a))) for rr, yy in prof])
    for i in range(segs):
        for j in range(len(prof) - 1):
            bm.faces.new((rings[i][j], rings[i][j + 1], rings[(i + 1) % segs][j + 1], rings[(i + 1) % segs][j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    return me

def build_wheel(name, r, width, side, car):
    piv = link(bpy.data.objects.new(name, None)); piv.parent = car
    t = link(bpy.data.objects.new(name + "_tire", tire_mesh(name + "_tire", r, width))); t.parent = piv
    t.data.materials.append(m_rubber)
    face_y = side * (width / 2 - 0.02)
    rim_r = r - 0.105
    barrel = link(bpy.data.objects.new(name + "_barrel", cyl_mesh(name + "_barrel", rim_r, width * 0.9, caps=False)))
    inner = link(bpy.data.objects.new(name + "_inner", cyl_mesh(name + "_inner", rim_r * 0.98, 0.01)))
    inner.rotation_euler = (math.pi / 2, 0, 0); inner.location = (0, -side * 0.06, 0); inner.parent = piv
    inner.data.materials.append(principled("RimInner", (0.01, 0.01, 0.01), 0.6))
    barrel.rotation_euler = (math.pi / 2, 0, 0); barrel.parent = piv; barrel.data.materials.append(m_rim)
    # spokes (10) + centre lock
    for k in range(10):
        a = 2 * math.pi * k / 10
        sp = box(f"{name}_spoke{k}", 0.075, 0.07, rim_r * 0.95, m=m_rim, parent=piv)
        sp.location = (math.sin(a) * rim_r * 0.5, face_y + side * 0.005, math.cos(a) * rim_r * 0.5)
        sp.rotation_euler = (0, a, 0)
    hub = link(bpy.data.objects.new(name + "_hub", cyl_mesh(name + "_hub", 0.065, 0.06, 6)))
    hub.rotation_euler = (math.pi / 2, 0, 0); hub.location = (0, face_y + side * 0.03, 0); hub.parent = piv
    hub.data.materials.append(m_titan)
    disc = link(bpy.data.objects.new(name + "_disc", cyl_mesh(name + "_disc", rim_r * 0.88, 0.03)))
    disc.rotation_euler = (math.pi / 2, 0, 0); disc.location = (0, face_y - side * 0.08, 0); disc.parent = piv
    disc.data.materials.append(m_disc)
    return piv

def build_car():
    car = link(bpy.data.objects.new("Car", None))
    body = link(bpy.data.objects.new("Body", build_body())); body.parent = car
    body.data.materials.append(m_paint)
    # wheel arches
    for (wx, rr) in [(1.24, 0.345), (-1.21, 0.355)]:
        cut = link(bpy.data.objects.new("cut", cyl_mesh("cut", rr + 0.05, 2.4, 48)))
        cut.rotation_euler = (math.pi / 2, 0, 0); cut.location = (wx, 0, rr + 0.03)
        bpy.context.view_layer.update()
        boolean_apply(body, cut)
        bpy.data.objects.remove(cut)
    for p in body.data.polygons: p.use_smooth = True
    gh = link(bpy.data.objects.new("Greenhouse", build_greenhouse())); gh.parent = car
    for p in gh.data.polygons: p.use_smooth = True
    assign_greenhouse_materials(gh)
    # wheels
    wheels = []
    for (wx, rr, wd, tag) in [(1.24, 0.345, 0.26, "F"), (-1.21, 0.355, 0.33, "R")]:
        for side, sname in [(1, "L"), (-1, "R")]:
            yc = side * (0.80 if tag == "F" else 0.79)
            w = build_wheel(f"Wheel{tag}{sname}", rr, wd, side, car)
            w.location = (wx, yc, rr)
            wheels.append(w)
            cal = box(f"Caliper{tag}{sname}", 0.12, 0.07, 0.16, m=m_caliper, parent=car)
            cal.location = (wx - 0.17, yc - side * 0.02, rr + 0.14); cal.rotation_euler = (0, -0.7, 0)
    # rear wing: two swan-neck uprights + main plane + endplates
    wing = box("WingPlane", 0.36, 1.72, 0.035, (-2.02, 0, 1.36), m_carbon, car, rot=(0, math.radians(-7), 0))
    box("WingFlap", 0.16, 1.72, 0.025, (-2.19, 0, 1.41), m_carbon, car, rot=(0, math.radians(-25), 0))
    for side in (1, -1):
        box(f"Endplate{side}", 0.5, 0.02, 0.24, (-2.08, side * 0.87, 1.33), m_carbon, car)
        box(f"Upright{side}", 0.07, 0.03, 0.42, (-1.98, side * 0.28, 1.15), m_carbon, car, rot=(0, math.radians(-14), 0))
    # front splitter, side skirts, diffuser
    box("Splitter", 0.30, 1.62, 0.03, (2.20, 0, 0.15), m_carbon, car)
    for side in (1, -1):
        box(f"Skirt{side}", 1.85, 0.05, 0.08, (0.02, side * 0.93, 0.19), m_carbon, car)
        box(f"Mirror{side}", 0.18, 0.14, 0.08, (0.56, side * 0.98, 0.98), m_paint, car)
        box(f"MirrorArm{side}", 0.08, 0.16, 0.025, (0.6, side * 0.88, 0.94), m_carbon, car)
    box("Diffuser", 0.35, 1.45, 0.06, (-2.18, 0, 0.27), m_carbon, car, rot=(0, math.radians(18), 0))
    # front hood vents (GT3 RS style dark slots)
    for side in (1, -1):
        box(f"HoodVent{side}", 0.42, 0.25, 0.02, (1.38, side * 0.33, 0.815), m_carbon, car, rot=(0, math.radians(-5), 0))
    # headlights: tilted ellipsoids sunk into the fenders
    heads = []
    for side in (1, -1):
        bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=1.0)
        bmesh.ops.scale(bm, vec=(0.17, 0.115, 0.08), verts=bm.verts)
        me = bpy.data.meshes.new("head"); bm.to_mesh(me); bm.free()
        for p in me.polygons: p.use_smooth = True
        h = link(bpy.data.objects.new(f"Headlight{side}", me)); h.parent = car
        h.location = (1.93, side * 0.64, 0.66); h.rotation_euler = (0, math.radians(18), side * math.radians(-12))
        h.data.materials.append(m_lens); heads.append(h)
        hi = link(bpy.data.objects.new(f"HeadInner{side}", me.copy())); hi.parent = h; hi.scale = (0.6, 0.7, 0.6)
        hi.data.materials.clear(); hi.data.materials.append(m_head)
    # tail-light bar + exhaust
    box("TailBar", 0.04, 1.62, 0.035, (-2.255, 0, 0.86), m_tail, car)
    for side in (1, -1):
        ex = link(bpy.data.objects.new(f"Exhaust{side}", cyl_mesh("ex", 0.048, 0.2, 24, caps=False))); ex.parent = car
        ex.modifiers.new("sol", 'SOLIDIFY').thickness = 0.006
        ex.rotation_euler = (0, math.pi / 2, 0); ex.location = (-2.25, side * 0.075, 0.36); ex.data.materials.append(m_titan)
        inner = link(bpy.data.objects.new(f"ExhaustIn{side}", cyl_mesh("exi", 0.04, 0.16, 24))); inner.parent = car
        inner.rotation_euler = (0, math.pi / 2, 0); inner.location = (-2.18, side * 0.075, 0.36)
        inner.data.materials.append(principled("Soot", (0.005, 0.004, 0.004), 0.9))
    # head-light beams (spot lamps)
    for side in (1, -1):
        ld = bpy.data.lights.new(f"Beam{side}", 'SPOT'); ld.energy = 0.0; ld.spot_size = math.radians(40)
        ld.color = (0.85, 0.9, 1.0); ld.shadow_soft_size = 0.05
        lo = link(bpy.data.objects.new(f"Beam{side}", ld)); lo.parent = car
        lo.location = (2.1, side * 0.64, 0.66); lo.rotation_euler = (0, math.radians(-95), 0)
    return car, wheels, heads

car, wheels, heads = build_car()

# ----------------------------------------------------------------- crash physics
# timeline mapping: frame -> physical seconds (speed ramps)
SHOT = {1: (1, 72), 2: (73, 144), 3: (145, 216), 4: (217, 288), 5: (289, 360)}
def speed_factor(f):
    if f <= 214: return 1.0
    if f <= 222: return 1.0 - 0.72 * (f - 214) / 8      # ramp into slow motion
    if f <= 288: return 0.28
    return 0.28 + (1.25 - 0.28) * min(1, (f - 288) / 50.0)
TF = np.zeros(NFR + 2)
for f in range(2, NFR + 2):
    TF[f] = TF[f - 1] + speed_factor(f) / FPS
T_OF_FRAME = lambda f: float(TF[int(f)])

S_CRASH = s_at_x(238.0)
T_CRASH = T_OF_FRAME(216)           # car hits the bend entry right at the cut to shot 4
def speed(T):
    return 30.0 if T < 6 else 30.0 + 4.6 * (T - 6)
# integrate road phase backwards from crash
DT = 1 / 2400.
def road_s(T):
    # s(T) = S_CRASH - integral_T^Tc v
    if T >= T_CRASH: return S_CRASH
    a = 4.6
    def V(t): return 30 * t if t < 6 else 30 * 6 + 30 * (t - 6) + 0.5 * a * (t - 6) ** 2
    return S_CRASH - (V(T_CRASH) - V(T))

xc, yc, zc, thc = road_at_s(S_CRASH)
v0 = speed(T_CRASH)

# simulate post-crash
sim = []           # (T, x, y, z, yaw, pitch, roll, wheel_spin_speed)
state = dict(x=float(xc), y=float(yc - 2.0 * math.cos(thc)), z=float(zc), vx=0., vy=0., vz=0.,
             yaw=float(thc), pitch=0., roll=0., wpitch=0., wroll=0., phase="slide")
state["x"] += 2.0 * math.sin(thc)  # right lane (d = -2)
heading = thc - math.radians(5.5)
state["vx"], state["vy"] = v0 * math.cos(heading), v0 * math.sin(heading)
T = T_CRASH; T_HIT = None; T_EDGE = None; HIT_POS = None
while T < T_CRASH + 7.0:
    sp = math.hypot(state["vx"], state["vy"])
    d, _ = signed_dist(state["x"], state["y"])
    zr = float(road_z(state["x"]))
    if state["phase"] == "slide":
        dec = 9.0
        state["yaw"] = thc + math.radians(38) * float(smooth(0, 0.42, np.array(T - T_CRASH)))
        state["roll"] = math.radians(-3.5) * float(smooth(0, 0.3, np.array(T - T_CRASH)))
        state["z"] = zr
        if d <= -4.35:
            state["phase"] = "barrier"; T_HIT = T; HIT_POS = (state["x"], state["y"], zr)
    elif state["phase"] == "barrier":
        dec = 16.0 if T - T_HIT < 0.12 else 6.0
        state["yaw"] += math.radians(55) * DT
        state["roll"] -= math.radians(28) * DT
        state["z"] = zr + 0.18 * float(smooth(0, 0.1, np.array(T - T_HIT)))
        if d <= -7.9:
            state["phase"] = "air"; T_EDGE = T; state["vz"] = 1.6
            state["wpitch"] = math.radians(25); state["wroll"] = math.radians(-35)
    else:
        dec = 0.6
        state["vz"] -= G * DT
        state["z"] += state["vz"] * DT
        state["wpitch"] = min(state["wpitch"] + math.radians(45) * DT, math.radians(95))
        state["pitch"] += state["wpitch"] * DT
        state["roll"] += state["wroll"] * DT
        state["yaw"] += math.radians(12) * DT
        ground = height_at(state["x"], state["y"])
        if state["vz"] < 0 and T - T_EDGE > 0.4 and state["z"] < ground + 0.4:
            state["z"] = ground + 0.4; state["vz"] = 0; state["vx"] *= 0.2; state["vy"] *= 0.2; state["wpitch"] = 0; state["wroll"] = 0
    if sp > 0.1 and state["phase"] != "air":
        k = max(0.0, 1 - dec * DT / sp)
        state["vx"] *= k; state["vy"] *= k
    elif state["phase"] == "air":
        k = 1 - dec * DT / max(sp, 1)
        state["vx"] *= k; state["vy"] *= k
    state["x"] += state["vx"] * DT; state["y"] += state["vy"] * DT
    if int(round((T - T_CRASH) / DT)) % 10 == 0:
        sim.append((T, state["x"], state["y"], state["z"], state["yaw"], state["pitch"], state["roll"], sp))
    T += DT
SIM = np.array(sim)
print(f"crash T={T_CRASH:.3f} hit={T_HIT} edge={T_EDGE} speed={v0:.1f}")

def car_state(T):
    if T < T_CRASH:
        s = road_s(T)
        x, y, z, th = road_at_s(s)
        x -= -2.0 * math.sin(th) * -1; y += -2.0 * math.cos(th)
        # proper right-lane offset: v = -2
        x, y, z = road_offset_point(s, -2.0)
        grade = math.atan(0.022 * math.cos(th))
        return dict(pos=(float(x), float(y), float(z)), yaw=float(th), pitch=-grade, roll=0.0, speed=speed(T), s=s)
    i = min(int(np.searchsorted(SIM[:, 0], T)), len(SIM) - 1)
    r = SIM[i]
    return dict(pos=(r[1], r[2], r[3]), yaw=r[4], pitch=r[5], roll=r[6], speed=r[7], s=None)

def car_matrix(st):
    rot = Euler((st["roll"], st["pitch"], st["yaw"]), 'ZYX')
    # apply yaw, then pitch about local Y (nose down positive), then roll about local X
    m = Matrix.Rotation(st["yaw"], 4, 'Z') @ Matrix.Rotation(st["pitch"], 4, 'Y') @ Matrix.Rotation(st["roll"], 4, 'X')
    return Matrix.Translation(Vector(st["pos"])) @ m

# keyframe car + wheels + headlights
CAR = {}
wheel_angle = 0.0
car.rotation_mode = 'QUATERNION'
for f in range(1, NFR + 1):
    T = T_OF_FRAME(f)
    st = car_state(T); CAR[f] = st
    M = car_matrix(st)
    car.location = M.to_translation(); car.rotation_quaternion = qcont('car', M.to_quaternion())
    car.keyframe_insert("location", frame=f); car.keyframe_insert("rotation_quaternion", frame=f)
    if f > 1:
        dT = T - T_OF_FRAME(f - 1)
        wheel_angle += st["speed"] * dT / 0.35
    for w in wheels:
        w.rotation_euler = (0, wheel_angle, 0)
        w.keyframe_insert("rotation_euler", frame=f)

# headlights snap on during the macro montage (frame 127) and stay on
P_head = m_head.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
for f, v in [(1, 0.0), (126, 0.0), (127, 40.0), (360, 40.0)]:
    P_head.default_value = v; P_head.keyframe_insert("default_value", frame=f)
for side in (1, -1):
    b = bpy.data.lights[f"Beam{side}"]
    for f, v in [(1, 0.0), (126, 0.0), (127, 250.0), (360, 250.0)]:
        b.energy = v; b.keyframe_insert("energy", frame=f)

# ----------------------------------------------------------------- guardrail with breakaway section
S_HIT = s_at_x(HIT_POS[0]) if HIT_POS else S_CRASH + 10
BREAK0, BREAK1 = S_HIT - 5.0, S_HIT + 9.0
def rail_strip(name, s0, s1, v=-5.45, step=0.5):
    bm = bmesh.new(); rows = []
    for s in np.arange(s0, s1 + 1e-6, step):
        x, y, z = road_offset_point(s, v)
        x2, y2, _ = road_offset_point(s, v - 0.04)
        prof = [(0.48, 0), (0.56, 0.06), (0.64, 0.0), (0.72, 0.06), (0.80, 0)]
        row = []
        for zz, out in prof:
            px, py, _ = road_offset_point(s, v - out * 0.6)
            row.append(bm.verts.new((float(px), float(py), float(z + zz))))
        rows.append(row)
    for i in range(len(rows) - 1):
        for j in range(4):
            bm.faces.new((rows[i][j], rows[i][j + 1], rows[i + 1][j + 1], rows[i + 1][j]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = link(bpy.data.objects.new(name, me)); o.data.materials.append(m_rail)
    sol = o.modifiers.new("sol", 'SOLIDIFY'); sol.thickness = 0.006
    return o

def posts(name, s0, s1, v=-5.5, spacing=2.0):
    bm = bmesh.new()
    for s in np.arange(s0, s1, spacing):
        x, y, z = road_offset_point(s, v - 0.12)
        r = bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.scale(bm, vec=(0.1, 0.1, 0.95), verts=r["verts"])
        bmesh.ops.translate(bm, vec=(float(x), float(y), float(z + 0.40)), verts=r["verts"])
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = link(bpy.data.objects.new(name, me)); o.data.materials.append(m_post)
    return o

rail_strip("Rail_A", S_ROAD0 + 2, BREAK0); rail_strip("Rail_B", BREAK1, S_ROAD1 - 2)
posts("Posts_A", S_ROAD0 + 2, BREAK0 - 0.5); posts("Posts_B", BREAK1 + 0.5, S_ROAD1 - 2)

# breakaway rail segments + posts, animated from impact
F_HIT = next(f for f in range(1, NFR + 1) if T_OF_FRAME(f) >= T_HIT)
pieces = []
for k, (a, b) in enumerate([(BREAK0, BREAK0 + 3.5), (BREAK0 + 3.5, BREAK0 + 7.0), (BREAK0 + 7.0, BREAK0 + 10.5), (BREAK0 + 10.5, BREAK1)]):
    seg = rail_strip(f"RailBreak{k}", a, b)
    # re-centre origin for nice rotation
    cx, cy, cz = road_offset_point((a + b) / 2, -5.5)
    seg.data.transform(Matrix.Translation((-cx, -cy, -cz - 0.64))); seg.location = (cx, cy, cz + 0.64)
    pieces.append(seg)
for k, s in enumerate(np.arange(BREAK0, BREAK1, 2.0)):
    x, y, z = road_offset_point(s, -5.62)
    p = box(f"PostBreak{k}", 0.1, 0.1, 0.95, (float(x), float(y), float(z + 0.40)), m_post)
    pieces.append(p)

def animate_debris(obj, t0, v, w, g=G, scale_end=None):
    bpy.context.view_layer.update()
    base = obj.matrix_world.copy(); p0 = base.to_translation(); r0 = base.to_quaternion()
    obj.rotation_mode = 'QUATERNION'
    for f in range(1, NFR + 1):
        T = T_OF_FRAME(f); dt = max(0.0, T - t0)
        p = p0 + Vector(v) * dt + Vector((0, 0, -0.5 * g * dt * dt))
        ang = Vector(w) * dt
        q = Quaternion(ang.normalized(), ang.length) @ r0 if ang.length > 1e-6 else r0
        obj.location = p; obj.rotation_quaternion = qcont(obj.name, q)
        obj.keyframe_insert("location", frame=f); obj.keyframe_insert("rotation_quaternion", frame=f)

_ih = int(np.searchsorted(SIM[:, 0], T_HIT))
_dv = SIM[min(_ih + 5, len(SIM) - 1), 1:3] - SIM[max(_ih - 5, 0), 1:3]
cvx, cvy = (_dv / np.linalg.norm(_dv)).tolist()
for k, pc in enumerate(pieces):
    dist = abs(s_at_x(pc.location.x) - S_HIT)
    t0 = T_HIT + 0.012 * dist
    sp = 26 * math.exp(-dist / 7) + 4
    v = (cvx * sp + rng.normal(0, 3), cvy * sp + rng.normal(0, 3), 3 + rng.uniform(0, 5))
    w = tuple(rng.normal(0, 6, 3))
    animate_debris(pc, t0, v, w)

# sparks + gravel debris (keyframed meshes, deterministic)
def spark_mesh():
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=6, v_segments=4, radius=1.0)
    bmesh.ops.scale(bm, vec=(0.09, 0.012, 0.012), verts=bm.verts)
    me = bpy.data.meshes.new("spark"); bm.to_mesh(me); bm.free(); me.materials.append(m_spark); return me
SPK = spark_mesh()
hx, hy, hz = HIT_POS
for k in range(170):
    t0 = T_HIT + rng.uniform(0, 0.22)
    life = rng.uniform(0.25, 0.7)
    dirv = np.array([cvx, cvy, 0]) * rng.uniform(4, 18) + rng.normal(0, 7, 3); dirv[2] = abs(dirv[2]) * 0.8 + 2
    o = link(bpy.data.objects.new(f"Spark{k}", SPK))
    o0 = np.array([hx, hy, hz + 0.5]) + rng.normal(0, 0.35, 3)
    for f in range(max(1, F_HIT - 2), min(NFR, F_HIT + 120)):
        T = T_OF_FRAME(f); dt = T - t0
        alive = 0 <= dt <= life
        p = o0 + dirv * max(dt, 0) + np.array([0, 0, -0.5 * G * max(dt, 0) ** 2])
        vel = dirv + np.array([0, 0, -G * max(dt, 0)])
        o.location = p.tolist()
        o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = qcont(o.name, Vector(vel.tolist()).to_track_quat('X', 'Z'))
        s = 1.0 if alive else 0.0
        o.scale = (s, s, s)
        o.keyframe_insert("location", frame=f); o.keyframe_insert("rotation_quaternion", frame=f); o.keyframe_insert("scale", frame=f)
    o.scale = (0, 0, 0); o.keyframe_insert("scale", frame=max(1, F_HIT - 3))

bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.0)
DEB = bpy.data.meshes.new("deb"); bm.to_mesh(DEB); bm.free(); DEB.materials.append(m_debris)
for k in range(70):
    o = link(bpy.data.objects.new(f"Gravel{k}", DEB)); sz = rng.uniform(0.03, 0.12); o.scale = (sz, sz * 0.8, sz * 0.7)
    o.location = (hx + rng.normal(0, 1), hy + rng.normal(0, 1), hz + 0.1)
    bpy.context.view_layer.update()
    t0 = T_HIT + rng.uniform(0, 0.25)
    v = (cvx * rng.uniform(6, 20) + rng.normal(0, 4), cvy * rng.uniform(6, 20) + rng.normal(0, 4), rng.uniform(2, 9))
    animate_debris(o, t0, v, tuple(rng.normal(0, 10, 3)))

# ----------------------------------------------------------------- water + forest
water_me = bpy.data.meshes.new("water")
water_me.from_pydata([(-6000, -2500, 0), (6000, -2500, 0), (6000, -60, 0), (-6000, -60, 0)], [], [(0, 1, 2, 3)])
water = link(bpy.data.objects.new("River", water_me)); water.location.z = 9.0; water.data.materials.append(m_water)

def tree_mesh():
    bm = bmesh.new()
    r = bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=0.035, radius2=0.025, depth=0.25)
    bmesh.ops.translate(bm, vec=(0, 0, 0.125), verts=r["verts"])
    for i, (z, rad, h) in enumerate([(0.18, 0.30, 0.42), (0.40, 0.24, 0.38), (0.60, 0.17, 0.32), (0.78, 0.10, 0.25)]):
        r = bmesh.ops.create_cone(bm, cap_ends=True, segments=7, radius1=rad, radius2=0.0, depth=h)
        bmesh.ops.translate(bm, vec=(0, 0, z + h / 2), verts=r["verts"])
    me = bpy.data.meshes.new("pine"); bm.to_mesh(me); bm.free()
    me.materials.append(m_bark); me.materials.append(m_pine)
    for p in me.polygons:
        p.material_index = 0 if p.center.z < 0.17 and abs(p.center.x) < 0.04 else 1
    return me

pine = link(bpy.data.objects.new("PineProto", tree_mesh()))
pine.location = (0, 0, 0)
N_T = 60000
TXs = rng.uniform(-1600, 1700, N_T); TYs = rng.uniform(-1500, 1200, N_T)
TH, TDd = terrain_height(TXs, TYs)
e = 1.5
hx1, _ = terrain_height(TXs + e, TYs); hy1, _ = terrain_height(TXs, TYs + e)
slope_v = np.hypot(hx1 - TH, hy1 - TH) / e
zr_t = road_z(TXs)
keep = ((TDd > 11) & (slope_v < 0.85) & (TH < zr_t + 330)) | ((TDd < -60) & (TH < 70) & (TH > 9.5) & (slope_v < 0.6))
keep &= rng.uniform(0, 1, N_T) < np.where(TDd > 0, 0.85 - 0.5 * smooth(0.3, 0.85, slope_v), 0.95)
TXs, TYs, TH = TXs[keep], TYs[keep], TH[keep]
print("trees", len(TXs))
bm = bmesh.new()
for x, y, h in zip(TXs, TYs, TH):
    sz = rng.uniform(9, 22) * 0.06
    a = rng.uniform(0, 2 * math.pi)
    vs = [bm.verts.new((x + sz * math.cos(a + k * 2.094), y + sz * math.sin(a + k * 2.094), h - 0.3)) for k in range(3)]
    bm.faces.new(vs)
tme = bpy.data.meshes.new("forest_pts"); bm.to_mesh(tme); bm.free()
forest = link(bpy.data.objects.new("Forest", tme))
forest.instance_type = 'FACES'; forest.use_instance_faces_scale = True; forest.instance_faces_scale = 1 / 0.06 / 1.732 * 1.0
pine.parent = forest
forest.visible_camera = True

# ----------------------------------------------------------------- world: golden hour sky
SUN_AZ = math.radians(-64.0); SUN_EL = math.radians(4.6)
w = bpy.data.worlds.new("Sky"); sc.world = w; w.use_nodes = True
WN = w.node_tree.nodes; WL = w.node_tree.links
sky = WN.new("ShaderNodeTexSky"); sky.sky_type = 'NISHITA'
sky.sun_elevation = SUN_EL; sky.sun_rotation = math.radians(90) - SUN_AZ
sky.altitude = 400; sky.air_density = 1.6; sky.dust_density = 4.0; sky.ozone_density = 1.2
sky.sun_disc = True; sky.sun_size = math.radians(1.2); sky.sun_intensity = 1.0
WL.new(sky.outputs[0], WN["Background"].inputs[0]); WN["Background"].inputs[1].default_value = 0.35
w.mist_settings.start = 80; w.mist_settings.depth = 6000; w.mist_settings.falloff = 'LINEAR'

# ----------------------------------------------------------------- cameras
def make_cam(name, lens=35, fstop=None, focus=None):
    cd = bpy.data.cameras.new(name); cd.lens = lens; cd.sensor_width = 36; cd.clip_start = 0.05; cd.clip_end = 20000
    if fstop:
        cd.dof.use_dof = True; cd.dof.aperture_fstop = fstop
        if focus is not None: cd.dof.focus_distance = focus
    return link(bpy.data.objects.new(name, cd))

def look(cam, pos, target, roll=0.0, f=None):
    pos = Vector(pos); target = Vector(target)
    q = (target - pos).to_track_quat('-Z', 'Y')
    if roll: q = q @ Quaternion((0, 0, 1), roll)
    cam.location = pos; cam.rotation_mode = 'QUATERNION'; cam.rotation_quaternion = qcont(cam.name, q)
    if f is not None:
        cam.keyframe_insert("location", frame=f); cam.keyframe_insert("rotation_quaternion", frame=f)
        if cam.data.dof.use_dof:
            cam.data.dof.focus_distance = (target - pos).length
            cam.data.dof.keyframe_insert("focus_distance", frame=f)

def cpos(f):
    return Vector(CAR[f]["pos"])

def car_local(f, off):
    return car_matrix(CAR[f]) @ Vector(off)

markers = []
def shot_cam(cam, f0):
    m = sc.timeline_markers.new(cam.name, frame=f0); m.camera = cam

# Shot 1: wide drone over the cliff side, gliding along with the car
c1 = make_cam("Cam1_Drone", 26)
for f in range(1, 73):
    u = (f - 1) / 71
    st = CAR[f]; p = cpos(f); th = st["yaw"]
    fwd = Vector((math.cos(th), math.sin(th), 0)); right = Vector((math.sin(th), -math.cos(th), 0))
    pos = p - fwd * (34 - 10 * u) + right * (26 - 4 * u) + Vector((0, 0, 20 - 6 * u))
    tgt = p + fwd * 14 + Vector((0, 0, -2))
    look(c1, pos, tgt, roll=math.radians(-2.5 + 2 * u), f=f)
shot_cam(c1, 1)

# Shot 2: macro montage, four 18-frame cuts, cameras rigidly attached to the car
macro = [
    ("Cam2a_Wheel", 45, 2.8, (2.15, -1.75, 0.42), (1.24, -0.85, 0.34)),
    ("Cam2b_Exhaust", 55, 2.2, (-3.0, -0.55, 0.42), (-2.25, 0.0, 0.38)),
    ("Cam2c_Headlight", 45, 2.0, (2.9, -1.15, 0.72), (1.93, -0.64, 0.66)),
    ("Cam2d_Wing", 28, 4.0, (-4.4, -2.6, 0.55), (-1.4, 0.0, 0.85)),
]
for k, (nm, lens, fs, off, tgt) in enumerate(macro):
    cm = make_cam(nm, lens, fstop=fs)
    f0 = 73 + 18 * k
    for f in range(f0, f0 + 18):
        u = (f - f0) / 17
        drift = Vector((0.0, 0.0, 0.0))
        if k == 0: drift = Vector((0.25 * u, 0, 0.02 * u))
        if k == 1: drift = Vector((0, 0.25 * u, 0.06 * u))
        if k == 2: drift = Vector((-0.2 * u, 0.1 * u, 0))
        if k == 3: drift = Vector((-0.4 * u, 0.2 * u, -0.1 * u))
        look(cm, car_local(f, Vector(off) + drift), car_local(f, tgt), f=f)
    shot_cam(cm, f0)

# Shot 3: low-angle tracking, car overtakes the camera and races at the bend
c3 = make_cam("Cam3_Low", 22)
for f in range(145, 217):
    u = (f - 145) / 71
    st = CAR[f]; s = st["s"] if st["s"] is not None else S_CRASH
    ds = 8.0 - 19.0 * (u ** 1.2)
    cx_, cy_, cz_ = road_offset_point(s + ds, 1.4 + 1.6 * u)
    pos = Vector((cx_, cy_, cz_ + 0.42 + 0.25 * u))
    tgt = cpos(f) + Vector((0, 0, 0.75))
    look(c3, pos, tgt, roll=math.radians(4 * (1 - u)), f=f)
shot_cam(c3, 145)

# Shot 4: slow-motion crash, drone hovering off the cliff edge looking back at the barrier
c4 = make_cam("Cam4_Crash", 24)
hit = Vector(HIT_POS)
out = Vector((cvx, cvy, 0)).normalized()
side = Vector((-out.y, out.x, 0))
right = -side
c4base = hit + out * 11 + right * 21 + Vector((0, 0, -1.2))
print('CAM4 base', tuple(c4base), 'ground below', height_at(c4base.x, c4base.y))
for f in range(217, 289):
    u = (f - 217) / 71
    pos = c4base + out * (6 * u) + right * (1.5 * u) + Vector((0, 0, -1.0 * u))
    tgt = cpos(f).lerp(hit + Vector((0, 0, 0.5)), 0.3) + Vector((0, 0, 0.3))
    look(c4, pos, tgt, roll=math.radians(-3), f=f)
shot_cam(c4, 217)

# Shot 5: aerial -- follow the fall, then rise and pull back to a wide down the golden valley
c5 = make_cam("Cam5_Aerial", 40)
edge = Vector(CAR[F_HIT]["pos"]) + out * 6
p_start = edge + out * 58 + right * 30 + Vector((0, 0, -3))
p_end = hit + Vector((-60, -175, 62))
end_dir = Vector((math.cos(math.radians(22)), math.sin(math.radians(22)), -0.2)).normalized()
for f in range(289, 361):
    u = (f - 289) / 71
    e5 = float(smooth(0.0, 1.0, np.array(u)))
    pos = p_start.lerp(p_end, e5)
    pos.z = max(pos.z, height_at(pos.x, pos.y) + 4)
    d_car = (cpos(f) - pos).normalized()
    d = d_car.lerp(end_dir, float(smooth(0.2, 1.0, np.array(u)))).normalized()
    look(c5, pos, pos + d * 50, f=f)
    c5.data.lens = 40 - 21 * float(smooth(0.05, 0.95, np.array(u))); c5.data.keyframe_insert("lens", frame=f)
shot_cam(c5, 289)
sc.camera = c1

# fast shutter for the wheel macro so spokes read; normal 180-degree shutter elsewhere
for f, v in [(1, 0.5), (72, 0.5), (73, 0.12), (90, 0.12), (91, 0.5), (360, 0.5)]:
    sc.render.motion_blur_shutter = v
    sc.keyframe_insert(data_path="render.motion_blur_shutter", frame=f)

# macro fill light (bounce card) that only exists during the montage
fl = bpy.data.lights.new("MacroFill", 'AREA'); fl.size = 1.6; fl.color = (1.0, 0.8, 0.6)
flo = link(bpy.data.objects.new("MacroFill", fl)); flo.parent = car; flo.rotation_mode = 'QUATERNION'
fills = [((2.6, -2.6, 1.1), (1.24, -0.85, 0.35), 160), ((-3.4, -1.6, 1.0), (-2.25, 0.0, 0.4), 140),
         ((3.4, -2.2, 1.5), (1.93, -0.64, 0.66), 90), ((-3.6, -3.4, 2.2), (-1.5, 0, 0.8), 120)]
for k, (lp, lt, en) in enumerate(fills):
    for f in (73 + 18 * k, 90 + 18 * k):
        flo.location = lp; flo.rotation_quaternion = (Vector(lt) - Vector(lp)).to_track_quat('-Z', 'Y')
        flo.keyframe_insert("location", frame=f); flo.keyframe_insert("rotation_quaternion", frame=f)
for f, v in [(1, 0), (72, 0), (73, 1), (144, 1), (145, 0)]:
    fl.energy = v * 45; fl.keyframe_insert("energy", frame=f)

# ----------------------------------------------------------------- render settings + compositor
r = sc.render
r.engine = 'CYCLES'; sc.cycles.device = 'CPU'
sc.cycles.samples = SAMPLES; sc.cycles.use_adaptive_sampling = True; sc.cycles.adaptive_threshold = 0.03
sc.cycles.use_denoising = True; sc.cycles.denoiser = 'OPENIMAGEDENOISE'
sc.cycles.max_bounces = 4; sc.cycles.diffuse_bounces = 2; sc.cycles.glossy_bounces = 2
sc.cycles.transmission_bounces = 2; sc.cycles.transparent_max_bounces = 4; sc.cycles.caustics_reflective = False; sc.cycles.caustics_refractive = False
sc.cycles.sample_clamp_indirect = 6.0
r.use_persistent_data = True
r.resolution_x, r.resolution_y = RES; r.resolution_percentage = 100
r.use_motion_blur = True; r.motion_blur_shutter = 0.5
r.film_transparent = True
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
sc.view_settings.exposure = 1.25
r.image_settings.file_format = 'PNG'; r.image_settings.color_depth = '8'
vl = sc.view_layers[0]; vl.use_pass_mist = True; vl.use_pass_environment = True

sc.use_nodes = True
CT = sc.node_tree; CN = CT.nodes; CL = CT.links
for n in list(CN): CN.remove(n)
rl = CN.new("CompositorNodeRLayers")
haze = CN.new("CompositorNodeMixRGB"); haze.blend_type = 'MIX'; haze.inputs[2].default_value = (0.95, 0.68, 0.42, 1)
mf = CN.new("CompositorNodeMath"); mf.operation = 'MULTIPLY'; mf.inputs[1].default_value = 0.62
CL.new(rl.outputs["Mist"], mf.inputs[0])
mfa = CN.new("CompositorNodeMath"); mfa.operation = 'MULTIPLY'
CL.new(mf.outputs[0], mfa.inputs[0]); CL.new(rl.outputs["Alpha"], mfa.inputs[1])
hazecol = CN.new("CompositorNodeMixRGB"); hazecol.blend_type = 'MULTIPLY'; hazecol.inputs[0].default_value = 1.0
hazecol.inputs[1].default_value = (0.98, 0.72, 0.46, 1)
CL.new(rl.outputs["Alpha"], hazecol.inputs[2])
haze_strength = CN.new("CompositorNodeMixRGB"); haze_strength.blend_type = 'MULTIPLY'; haze_strength.inputs[0].default_value = 1
haze_strength.inputs[2].default_value = (0.75, 0.75, 0.75, 1)
CL.new(hazecol.outputs[0], haze_strength.inputs[1])
CL.new(mfa.outputs[0], haze.inputs[0]); CL.new(rl.outputs["Image"], haze.inputs[1]); CL.new(haze_strength.outputs[0], haze.inputs[2])
setalpha = CN.new("CompositorNodeSetAlpha"); setalpha.mode = 'REPLACE_ALPHA'
CL.new(haze.outputs[0], setalpha.inputs[0]); CL.new(rl.outputs["Alpha"], setalpha.inputs[1])
over = CN.new("CompositorNodeAlphaOver"); over.use_premultiply = False
CL.new(rl.outputs["Env"], over.inputs[1]); CL.new(setalpha.outputs[0], over.inputs[2])
glare = CN.new("CompositorNodeGlare"); glare.glare_type = 'STREAKS'; glare.streaks = 2; glare.angle_offset = 0.0
glare.threshold = 6.0; glare.mix = -0.75; glare.quality = 'MEDIUM'; glare.fade = 0.93
CL.new(over.outputs[0], glare.inputs[0])
fog = CN.new("CompositorNodeGlare"); fog.glare_type = 'FOG_GLOW'; fog.threshold = 3.0; fog.mix = -0.8; fog.size = 8; fog.quality = 'MEDIUM'
CL.new(glare.outputs[0], fog.inputs[0])
lens = CN.new("CompositorNodeLensdist"); lens.inputs[1].default_value = -0.012; lens.inputs[2].default_value = 0.006
CL.new(fog.outputs[0], lens.inputs[0])
comp = CN.new("CompositorNodeComposite"); comp.use_alpha = False
CL.new(lens.outputs[0], comp.inputs[0])

bpy.ops.wm.save_as_mainfile(filepath=OUT, compress=True)
print("SAVED", OUT, "F_HIT", F_HIT, "T_HIT", T_HIT, "T_EDGE", T_EDGE)
