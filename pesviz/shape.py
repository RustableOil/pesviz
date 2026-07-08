"""Procedurally generate meshes (icosphere, cone, cylinder) for the primitive shapes drawn by Renderer"""

import numpy as np


def generate_icosphere(subdivisions=1):
    """
    Generate a unit icosphere centered at (0, 0, 0).

    Parameters
    ----------
    subdivisions : int
        Number of subdivision steps.
        0 = raw icosahedron (20 faces)
        1 = 80 faces
        2 = 320 faces

    Returns
    -------
    vertices : (V, 3) float32 — positions on the unit sphere
    normals  : (V, 3) float32 — identical to vertices for a unit sphere
    indices  : (F, 3) uint32  — triangle face indices
    """
    phi = (1.0 + np.sqrt(5.0)) / 2.0

    raw_verts = [
        (-1,  phi,  0), ( 1,  phi,  0), (-1, -phi,  0), ( 1, -phi,  0),
        ( 0, -1,  phi), ( 0,  1,  phi), ( 0, -1, -phi), ( 0,  1, -phi),
        ( phi,  0, -1), ( phi,  0,  1), (-phi,  0, -1), (-phi,  0,  1),
    ]

    vertices = [np.array(v, dtype=np.float64) for v in raw_verts]
    vertices = [v / np.linalg.norm(v) for v in vertices]

    faces = [
        [0, 11, 5], [0, 5, 1],  [0, 1, 7],  [0, 7, 10], [0, 10, 11],
        [1, 5, 9],  [5, 11, 4], [11, 10, 2],[10, 7, 6],  [7, 1, 8],
        [3, 9, 4],  [3, 4, 2],  [3, 2, 6],  [3, 6, 8],   [3, 8, 9],
        [4, 9, 5],  [2, 4, 11], [6, 2, 10], [8, 6, 7],   [9, 8, 1],
    ]

    midpoint_cache = {}

    def get_midpoint(i, j):
        """Return the index of the (cached) normalized midpoint vertex between vertices i and j."""
        key = (min(i, j), max(i, j))
        if key in midpoint_cache:
            return midpoint_cache[key]
        mid = (vertices[i] + vertices[j]) / 2.0
        mid = mid / np.linalg.norm(mid)
        idx = len(vertices)
        vertices.append(mid)
        midpoint_cache[key] = idx
        return idx

    for _ in range(subdivisions):
        new_faces = []
        for a, b, c in faces:
            ab = get_midpoint(a, b)
            bc = get_midpoint(b, c)
            ca = get_midpoint(c, a)
            new_faces.extend([
                [a, ab, ca],
                [b, bc, ab],
                [c, ca, bc],
                [ab, bc, ca],
            ])
        faces = new_faces

    verts_np = np.array(vertices, dtype=np.float32)

    # normals are identical to positions on a unit sphere
    return verts_np, np.array(faces, dtype=np.uint32), verts_np.copy()


def generate_cone(n=16, radius=1.0, height=1.0):
    """
    Generate a cone with base center at (0, 0, 0) and tip at (0, height, 0).

    Vertex layout
    -------------
    0      .. n-1   lateral ring  (slanted outward normals)
    n               apex
    n+1    .. 2n    cap ring      (same positions, downward normals)
    2n+1            cap center

    Parameters
    ----------
    n      : int   Number of circumference segments.
    radius : float Base radius in canonical space.
    height : float Cone height in canonical space.

    Returns
    -------
    vertices : (2n+2, 3) float32
    indices  : (2n,   3) uint32
    normals  : (2n+2, 3) float32
    """
    angles = np.linspace(0.0, 2.0 * np.pi, n, endpoint=False)
    cos_a  = np.cos(angles)
    sin_a  = np.sin(angles)

    # slope angle determines the outward tilt of lateral normals
    slope  = np.arctan2(radius, height)
    cos_sl = np.cos(slope)
    sin_sl = np.sin(slope)

    # --- vertices ---

    # lateral ring: base circle at y=0
    lat_pos  = np.stack([radius * cos_a,
                         np.zeros(n),
                         radius * sin_a], axis=1)

    # apex at top
    apex_pos = np.array([[0.0, height, 0.0]])

    # cap ring: identical positions to lateral ring, different normals
    cap_pos    = lat_pos.copy()
    center_pos = np.array([[0.0, 0.0, 0.0]])

    # --- normals ---

    lat_norm = np.stack([cos_sl * cos_a,
                         np.full(n, sin_sl),
                         cos_sl * sin_a], axis=1)

    apex_norm   = np.array([[0.0,  1.0, 0.0]])
    cap_norm    = np.tile([0.0, -1.0, 0.0], (n, 1))
    center_norm = np.array([[0.0, -1.0, 0.0]])

    vertices = np.concatenate([lat_pos, apex_pos,
                                cap_pos, center_pos]).astype(np.float32)
    normals  = np.concatenate([lat_norm, apex_norm,
                                cap_norm, center_norm]).astype(np.float32)

    # --- faces ---

    apex_idx   = n
    cap_start  = n + 1
    center_idx = 2 * n + 1

    faces = []
    for i in range(n):
        nxt = (i + 1) % n
        # lateral triangle: CCW from outside
        faces.append([apex_idx,   nxt,             i            ])
        # cap triangle: CCW from below (-y outward)
        faces.append([center_idx, cap_start + i,   cap_start + nxt])

    return vertices, np.array(faces, dtype=np.uint32), normals


def generate_cylinder(n=32, radius=1.0, height=1.0):
    """
    Generate a cylinder with base center at (0, 0, 0) and top at (0, height, 0).

    Vertex layout
    -------------
    0      .. n-1   bottom lateral ring  (outward normals)
    n      .. 2n-1  top lateral ring     (outward normals)
    2n     .. 3n-1  bottom cap ring      (downward normals)
    3n              bottom cap center
    3n+1   .. 4n    top cap ring         (upward normals)
    4n+1            top cap center

    Parameters
    ----------
    n      : int   Number of circumference segments.
    radius : float Cylinder radius in canonical space.
    height : float Cylinder height in canonical space.

    Returns
    -------
    vertices : (4n+2, 3) float32
    indices  : (4n,   3) uint32
    normals  : (4n+2, 3) float32
    """
    angles = np.linspace(0.0, 2.0 * np.pi, n, endpoint=False)
    cos_a  = np.cos(angles)
    sin_a  = np.sin(angles)
    x      = radius * cos_a
    z      = radius * sin_a

    # --- vertices ---

    bot_lat = np.stack([x, np.zeros(n),        z], axis=1)
    top_lat = np.stack([x, np.full(n, height), z], axis=1)

    bot_cap    = bot_lat.copy()
    bot_center = np.array([[0.0, 0.0,    0.0]])
    top_cap    = top_lat.copy()
    top_center = np.array([[0.0, height, 0.0]])

    # --- normals ---

    lat_norm     = np.stack([cos_a, np.zeros(n), sin_a], axis=1)
    bot_cap_norm = np.tile([ 0.0, -1.0, 0.0], (n, 1))
    bot_ctr_norm = np.array([[0.0, -1.0, 0.0]])
    top_cap_norm = np.tile([ 0.0,  1.0, 0.0], (n, 1))
    top_ctr_norm = np.array([[0.0,  1.0, 0.0]])

    vertices = np.concatenate([
        bot_lat, top_lat,
        bot_cap, bot_center,
        top_cap, top_center,
    ]).astype(np.float32)

    normals = np.concatenate([
        lat_norm, lat_norm,
        bot_cap_norm, bot_ctr_norm,
        top_cap_norm, top_ctr_norm,
    ]).astype(np.float32)

    # --- faces ---

    bot_start     = 0
    top_start     = n
    bot_cap_start = 2 * n
    bot_ctr_idx   = 3 * n
    top_cap_start = 3 * n + 1
    top_ctr_idx   = 4 * n + 1

    faces = []
    for i in range(n):
        nxt = (i + 1) % n

        b0 = bot_start + i;     b1 = bot_start + nxt
        t0 = top_start + i;     t1 = top_start + nxt

        # lateral quad as two CCW triangles viewed from outside
        faces.append([b0, t0, b1])
        faces.append([b1, t0, t1])

        # bottom cap: CCW from below (-y outward)
        faces.append([bot_ctr_idx, bot_cap_start + i,   bot_cap_start + nxt])

        # top cap: CCW from above (+y outward)
        faces.append([top_ctr_idx, top_cap_start + nxt, top_cap_start + i  ])

    return vertices, np.array(faces, dtype=np.uint32), normals
