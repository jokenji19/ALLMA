"""Build ALLMA's CC0 eight-year-old particle bust, entirely offline.

The original MakeHuman skin blends the CC0 one-year and ten-year macro targets
at 2/9 and 7/9, then receives one Catmull--Clark step. Only the derived bust is
shipped, never MakeHuman code. Proportions and resting eyelids are artistic;
this is not an anatomical age estimator or an inference about the user.
"""
import argparse
import base64
from collections import defaultdict
import hashlib
import heapq
import json
import math
from pathlib import Path
import random
import struct


POINT_COUNT = 100_000
PACKED_VERTEX_BYTES = 11


def average(values):
    return [sum(p[k] for p in values) / len(values) for k in range(3)]


def smoothstep(low, high, value):
    t = max(0.0, min(1.0, (value - low) / (high - low)))
    return t * t * (3.0 - 2.0 * t)


def subdivide_skin(vertices, faces):
    """One genuine Catmull--Clark step; keep the open bust boundary smooth."""
    used = sorted({i for face in faces for i in face})
    mapping = {old: new for new, old in enumerate(used)}
    vertices = [vertices[i] for i in used]
    faces = [[mapping[i] for i in face] for face in faces]
    centers = [average([vertices[i] for i in face]) for face in faces]
    edge_faces = defaultdict(list)
    vertex_faces = defaultdict(list)
    vertex_edges = defaultdict(set)
    for fi, face in enumerate(faces):
        for i in face:
            vertex_faces[i].append(fi)
        for a, b in zip(face, face[1:] + face[:1]):
            edge = tuple(sorted((a, b)))
            edge_faces[edge].append(fi)
            vertex_edges[a].add(edge)
            vertex_edges[b].add(edge)
    output = []
    for i, p in enumerate(vertices):
        boundary = [b if a == i else a for a, b in vertex_edges[i]
                    if len(edge_faces[(a, b)]) == 1]
        if len(boundary) == 2:
            output.append([(6 * p[k] + vertices[boundary[0]][k]
                            + vertices[boundary[1]][k]) / 8 for k in range(3)])
        elif boundary:
            # Preserve pathological source boundaries rather than moving them
            # according to an interior formula with an invalid neighbourhood.
            output.append(p[:])
        else:
            n = len(vertex_faces[i])
            f = average([centers[j] for j in vertex_faces[i]])
            r = average([average([vertices[a], vertices[b]])
                         for a, b in vertex_edges[i]])
            output.append([(f[k] + 2 * r[k] + (n - 3) * p[k]) / n
                           for k in range(3)])
    edge_ids = {}
    for edge, adjacent in edge_faces.items():
        edge_ids[edge] = len(output)
        values = [vertices[i] for i in edge]
        if len(adjacent) == 2:
            values += [centers[i] for i in adjacent]
        output.append(average(values))
    face_ids = []
    for center in centers:
        face_ids.append(len(output))
        output.append(center)
    quads = []
    for fi, face in enumerate(faces):
        for j, i in enumerate(face):
            previous = face[(j - 1) % len(face)]
            following = face[(j + 1) % len(face)]
            quads.append((i, edge_ids[tuple(sorted((i, following)))],
                          face_ids[fi], edge_ids[tuple(sorted((previous, i)))]))
    return output, quads


def solve(matrix, vector):
    """Small deterministic linear solve, without an offline package dependency."""
    rows = [list(row) + [value] for row, value in zip(matrix, vector)]
    for k in range(len(rows)):
        pivot = max(range(k, len(rows)), key=lambda j: abs(rows[j][k]))
        rows[k], rows[pivot] = rows[pivot], rows[k]
        if abs(rows[k][k]) < 1e-12:
            raise ValueError('Cannot fit the surrounding eyelid surface')
        divisor = rows[k][k]
        rows[k] = [value / divisor for value in rows[k]]
        for i in range(len(rows)):
            if i != k:
                factor = rows[i][k]
                rows[i] = [a - factor * b for a, b in zip(rows[i], rows[k])]
    return [row[-1] for row in rows]


def rest_eyelids(vertices, quads):
    """Close resting lids with real-area patches joined to the actual skin rim.

    Eye helpers are absent. The original exterior rim is reused, so there is
    neither an overlaid disk edge nor collapsed rings forming a bright slit.
    """
    kept = []
    for face in quads:
        x, y, z = average([vertices[i] for i in face])
        in_eye = any(math.hypot((x - side * 0.223) / 0.150, (y - 0.119) / 0.120) < 1.05
                     for side in (-1, 1))
        if not (in_eye and z > 0.49):
            kept.append(face)
    counts = defaultdict(int)
    neighbors = defaultdict(set)
    for face in kept:
        for a, b in zip(face, face[1:] + face[:1]):
            counts[tuple(sorted((a, b)))] += 1
    for (a, b), count in counts.items():
        if count == 1:
            neighbors[a].add(b)
            neighbors[b].add(a)
    seen, loops = set(), []
    for i in neighbors:
        if i in seen:
            continue
        loop, stack = [], [i]
        while stack:
            j = stack.pop()
            if j not in seen:
                seen.add(j)
                loop.append(j)
                stack.extend(neighbors[j])
        loops.append(loop)

    patches = []
    for side in (-1, 1):
        center_x, center_y = side * 0.223, 0.119
        candidates = [loop for loop in loops if len(loop) > 12
                      and 0.02 < average([vertices[i] for i in loop])[1] < 0.22
                      and average([vertices[i] for i in loop])[0] * side > 0]
        if not candidates:
            raise ValueError('The exterior eyelid rim was not found')
        # The second ring belongs to the recessed old socket. Only the rim
        # with the greatest frontal depth is the exterior skin boundary.
        rim = max(candidates, key=lambda loop: average([vertices[i] for i in loop])[2])
        if any(len(neighbors[i]) != 2 for i in rim):
            raise ValueError('The exterior eyelid rim is not a simple loop')
        rim = sorted(rim, key=lambda i: math.atan2(vertices[i][1] - center_y,
                                                 vertices[i][0] - center_x))
        rx, ry = 0.150, 0.120
        uvz = [((vertices[i][0] - center_x) / rx,
                (vertices[i][1] - center_y) / ry, vertices[i][2]) for i in rim]
        data = [(1, u, v, u * u, u * v, v * v) for u, v, _ in uvz]
        matrix = [[sum(row[i] * row[j] for row in data) for j in range(6)] for i in range(6)]
        values = [sum(row[i] * item[2] for row, item in zip(data, uvz)) for i in range(6)]
        coefficients = solve(matrix, values)

        def height(x, y, radius, boundary_z):
            u, v = (x - center_x) / rx, (y - center_y) / ry
            skin = sum(a * b for a, b in zip(coefficients, (1, u, v, u * u, u * v, v * v)))
            crease_y = 0.108 + 0.025 * min(1, u * u)
            crease = math.exp(-((y - crease_y) / 0.019) ** 2) * math.exp(-(u / 0.85) ** 6)
            fullness = 0.014 * math.exp(-((v - 0.18) / 0.65) ** 2 - (u / 0.85) ** 4)
            interior = skin + fullness - 0.010 * crease
            blend = smoothstep(0.55, 1.0, radius)
            return interior * (1 - blend) + boundary_z * blend

        center = len(vertices)
        vertices.append([center_x, center_y, height(center_x, center_y, 0, coefficients[0])])
        rings, ring_ids = 20, []
        for ring in range(1, rings):
            radius = ring / rings
            ids = []
            for i in rim:
                bx, by, bz = vertices[i]
                x = center_x + (bx - center_x) * radius
                y = center_y + (by - center_y) * radius
                ids.append(len(vertices))
                vertices.append([x, y, height(x, y, radius, bz)])
            ring_ids.append(ids)
        ring_ids.append(rim)
        segments = len(rim)
        for j in range(segments):
            patches.append((center, ring_ids[0][j], ring_ids[0][(j + 1) % segments]))
        for inner, outer in zip(ring_ids, ring_ids[1:]):
            for j in range(segments):
                k = (j + 1) % segments
                patches.append((inner[j], outer[j], outer[k], inner[k]))
    return kept + patches


def normalise(value):
    length = math.sqrt(sum(v * v for v in value)) or 1.0
    return [v / length for v in value]


def pack_vertex(p, n, fade=1.0):
    xyz = [round(v * 4096) for v in p]
    if any(abs(v) > 32767 for v in xyz):
        raise ValueError('Bust coordinate is outside the packed range')
    return struct.pack('<hhhbbbbB', *xyz,
                       *(round(v * 127) for v in normalise(n)),
                       0, round(max(0.0, min(1.0, fade)) * 255))


def build(source, destination, targets, child_targets):
    vertices, faces, group = [], [], ''
    for line in source.read_text().splitlines():
        if line.startswith('v '):
            vertices.append(list(map(float, line.split()[1:4])))
        elif line.startswith('g '):
            group = line[2:]
        elif line.startswith('f ') and group == 'body':
            ids = [int(p.split('/')[0]) - 1 for p in line.split()[1:]]
            if (min(vertices[i][1] for i in ids) >= 4.9
                    and max(abs(vertices[i][0]) for i in ids) <= 2.3):
                faces.append(ids)
    baby_files = sorted(targets.glob('*-baby.target'))
    child_files = sorted(child_targets.glob('*-child.target'))
    if len(baby_files) != 6 or len(child_files) != 6:
        raise ValueError('The six official baby and six child targets are required')
    files = baby_files + child_files
    # Upstream age anchors: baby = 1 year, child = 10 years. An eight-year
    # appearance is 7/9 of the way between them, not an adult/baby blend.
    for target in files:
        weight = (2 / 9 if target in baby_files else 7 / 9) / 6
        for line in target.read_text().splitlines():
            if not line or line.startswith('#'):
                continue
            idx, *delta = line.split()
            for k, d in enumerate(delta):
                vertices[int(idx)][k] += float(d) * weight
    # Reframe the blended bust around the same eye line as the renderer.
    # Unlike the former six-month portrait, do not shorten the lower face.
    for p in vertices:
        p[0] *= 0.967
        p[1] = (p[1] - 2.2498) * 0.967
        p[2] = (p[2] - 0.375) * 0.967
    # Crop in the final age coordinate system as well. The old source-space
    # cut otherwise carries invisible lower torso geometry into the bust.
    faces = [face for face in faces if min(vertices[i][1] for i in face) >= -1.18
             and max(abs(vertices[i][0]) for i in face) <= 1.20]
    vertices, quads = subdivide_skin(vertices, faces)
    quads = rest_eyelids(vertices, quads)
    for p in vertices:
        # Keep the source cranium round without an excessively tall silhouette.
        if p[1] > 0.25:
            p[1] = 0.25 + (p[1] - 0.25) * 0.81
        cheeks = math.exp(-((p[1] + 0.16) / 0.25) ** 2) * smoothstep(0.18, 0.48, p[2])
        p[0] *= 1 + 0.008 * cheeks
    normals = [[0.0, 0.0, 0.0] for _ in vertices]
    triangles, areas = [], []
    for face in quads:
        for j in range(1, len(face) - 1):
            ids = (face[0], face[j], face[j + 1])
            a, b, c = [vertices[i] for i in ids]
            u = [b[k] - a[k] for k in range(3)]
            v = [c[k] - a[k] for k in range(3)]
            n = [u[1] * v[2] - u[2] * v[1],
                 u[2] * v[0] - u[0] * v[2],
                 u[0] * v[1] - u[1] * v[0]]
            area = math.sqrt(sum(k * k for k in n)) * 0.5
            if area <= 1e-14:
                continue
            for i in ids:
                for k in range(3):
                    normals[i][k] += n[k]
            x, y, z = average([a, b, c])
            # Dense face and fine lips/eyelids, with continuous particles on
            # the skull, ears, nape and shoulders in the full 360-degree view.
            face_weight = smoothstep(0.24, 0.58, z) * smoothstep(-0.5, -0.28, y)
            weight = (0.95 if y > -0.48 else 0.43) + face_weight * 1.65
            triangles.append(ids)
            areas.append(area * weight)
    normals = [normalise(n) for n in normals]
    if len(vertices) >= 65536:
        raise ValueError('Depth mesh must fit WebGL1 Uint16 indices')

    # Feather the actual open cut instead of a view-dependent flat mask.
    edge_counts, neighbors = defaultdict(int), defaultdict(dict)
    for tri in triangles:
        for a, b in zip(tri, (tri[1], tri[2], tri[0])):
            edge = tuple(sorted((a, b)))
            edge_counts[edge] += 1
            distance = math.dist(vertices[a], vertices[b])
            neighbors[a][b] = distance
            neighbors[b][a] = distance
    boundary = {i for edge, count in edge_counts.items() if count == 1
                for i in edge if vertices[i][1] < -0.48}
    distances = {i: 0.0 for i in boundary}
    queue = [(0.0, i) for i in boundary]
    heapq.heapify(queue)
    while queue:
        distance, i = heapq.heappop(queue)
        if distance != distances[i]:
            continue
        for j, step in neighbors[i].items():
            d = distance + step
            if d < 0.24 and d < distances.get(j, float('inf')):
                distances[j] = d
                heapq.heappush(queue, (d, j))
    fades = [min(1.0, distances.get(i, 0.24) / 0.22) for i in range(len(vertices))]

    # Systematic area stratification preserves density even across groups of
    # tiny triangles. Rounding every triangle separately would leave the
    # finely tessellated center of an eyelid completely empty. A 2D
    # low-discrepancy sequence then distributes each triangle's particles.
    rng = random.Random(731961)
    total = sum(areas)
    offset = rng.random()
    allocations = []
    running, previous = 0.0, 0
    for area in areas:
        running += POINT_COUNT * area / total
        current = min(POINT_COUNT, math.floor(running + offset))
        allocations.append(current - previous)
        previous = current
    allocations[-1] += POINT_COUNT - sum(allocations)
    points, records, occupied = [], [], set()
    golden1, golden2 = 0.7548776662466927, 0.5698402909980532
    for ids, allocation in zip(triangles, allocations):
        offset_u, offset_v = rng.random(), rng.random()
        for j in range(allocation):
            attempt = 0
            while True:
                t = j + attempt * max(1, allocation) + 1
                u = math.sqrt((offset_u + golden1 * t) % 1)
                v = (offset_v + golden2 * t) % 1
                weights = (1 - u, u * (1 - v), u * v)
                p = [sum(vertices[i][k] * w for i, w in zip(ids, weights)) for k in range(3)]
                key = tuple(round(value * 4096) for value in p)
                if key not in occupied:
                    occupied.add(key)
                    break
                attempt += 1
                if attempt > 200:
                    raise ValueError('Particle quantisation exhausted a triangle')
            n = [sum(normals[i][k] * w for i, w in zip(ids, weights)) for k in range(3)]
            fade = sum(fades[i] * w for i, w in zip(ids, weights))
            points.append(p)
            records.append(pack_vertex(p, n, fade))
    order = list(range(len(points)))
    rng.shuffle(order)  # Prefixes and adaptive strides remain spatially balanced.
    points = [points[i] for i in order]
    packed = b''.join(records[i] for i in order)
    if len(points) != POINT_COUNT or len(packed) != POINT_COUNT * PACKED_VERTEX_BYTES:
        raise ValueError('Unexpected particle count')

    # Sparse optional links use only a balanced Uint16-compatible subset.
    # The particle draw itself is drawArrays and can contain >65535 vertices.
    buckets, edges = {}, []
    step = 0.055
    for i, p in enumerate(points[:65535]):
        cell = tuple(math.floor(v / step) for v in p)
        if i % 16 == 0 and len(edges) < 4800:
            near = []
            for x in (-1, 0, 1):
                for y in (-1, 0, 1):
                    for z in (-1, 0, 1):
                        for j in buckets.get((cell[0] + x, cell[1] + y, cell[2] + z), ()):
                            d = sum((p[k] - points[j][k]) ** 2 for k in range(3))
                            if 0.00015 < d < 0.0012:
                                near.append((d, j))
            if near:
                edges.extend((min(near)[1], i))
        buckets.setdefault(cell, []).append(i)
    indices = [i for tri in triangles for i in tri]
    encode = lambda data: base64.b64encode(data).decode()
    asset = {
        'version': 3, 'count': POINT_COUNT, 'life_stage': 'child',
        'visual_age_months': 96, 'source_kind': 'subdivided_skin_particles',
        'age_target_blend': {'baby': 2 / 9, 'child': 7 / 9},
        'subdivision_steps': 1, 'resting_eyes': 'closed', 'eye_helpers': False,
        'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'target_sha256': {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in files},
        'points': encode(packed),
        'edges': encode(struct.pack('<' + 'H' * len(edges), *edges)),
        'surface': encode(b''.join(pack_vertex(p, n, fade)
                                 for p, n, fade in zip(vertices, normals, fades))),
        'triangles': encode(struct.pack('<' + 'H' * len(indices), *indices)),
    }
    destination.write_text(
        '/* CC0 child skin particles; no eye spheres. See AVATAR_ASSET_LICENSE.txt. */\n'
        + 'window.AllmaPortraitMesh=' + json.dumps(asset, separators=(',', ':')) + ';\n')
    print(f'{POINT_COUNT} particles, {len(vertices)} smoothed depth vertices, '
          f'{len(triangles)} triangles, {len(edges) // 2} links; '
          f'{destination.stat().st_size} bytes')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--targets', type=Path, required=True)
    parser.add_argument('--child-targets', type=Path, required=True)
    args = parser.parse_args()
    build(args.source, args.destination, args.targets, args.child_targets)
