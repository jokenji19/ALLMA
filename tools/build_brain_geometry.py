"""Bake an offline, reduced cortical wireframe from Nilearn's fsaverage5 data.

Build-time only (numpy/scipy); no scientific package is shipped to Android.
Usage: python3 tools/build_brain_geometry.py --source-dir <downloaded GIFTI files>
Source files are prefixed ``nilearn-``; provenance is in assets/web/licenses/.
"""
from pathlib import Path
import argparse
import base64
import gzip
import hashlib
import json
import xml.etree.ElementTree as ET
import zlib

import numpy as np
from scipy.spatial import cKDTree


def gifti(path):
    result = []
    for array in ET.fromstring(gzip.decompress(path.read_bytes())).findall('DataArray'):
        shape = [int(array.attrib[f'Dim{i}']) for i in range(int(array.attrib['Dimensionality']))]
        dtype = '<f4' if array.attrib['DataType'] == 'NIFTI_TYPE_FLOAT32' else '<i4'
        result.append(np.frombuffer(zlib.decompress(base64.b64decode(array.findtext('Data'))), dtype=dtype).reshape(shape))
    return result


def build(source, target):
    points, edges, regions, ridge = [], [], [], []
    curve_points, curve_lengths = [], []
    for side in ['left', 'right']:
        coords, _ = gifti(source / f'nilearn-pial_{side}.gii.gz')
        sphere, triangles = gifti(source / f'nilearn-sphere_{side}.gii.gz')
        sulc, = gifti(source / f'nilearn-sulc_{side}.gii.gz')
        # The nested icosphere uses the same first 2562 vertices at resolution 4.
        # Collapse on the sphere, never in folded Euclidean space: nearby banks
        # of a sulcus must not be welded together.
        count = 2562
        _, nearest = cKDTree(sphere[:count]).query(sphere)
        faces = nearest[triangles]
        faces = faces[(faces[:, 0] != faces[:, 1]) & (faces[:, 1] != faces[:, 2]) & (faces[:, 0] != faces[:, 2])]
        unique = set()
        for face in faces:
            for a, b in [(face[0], face[1]), (face[1], face[2]), (face[2], face[0])]:
                unique.add(tuple(sorted((int(a), int(b)))))
        offset = len(points)
        # Freesurfer RAS -> scene (right, up, anterior), uniform scale.
        transformed = np.column_stack((coords[:count, 0], coords[:count, 2] - 12, coords[:count, 1] + 18)) / 95
        points.extend(transformed.tolist())
        regions.extend([side] * count)
        ridge.extend(np.clip(.52 - sulc[:count] * .28, .12, .96).tolist())
        edges.extend([[a + offset, b + offset] for a, b in sorted(unique)])

        # Smooth contours of sulcal depth follow the cortical folds rather than
        # arbitrary arcs around an ellipsoid. Build from the full source mesh,
        # then simplify paths by distance before packing them for the phone.
        full = np.column_stack((coords[:, 0], coords[:, 2] - 12, coords[:, 1] + 18)) / 95
        _, full_faces = gifti(source / f'nilearn-pial_{side}.gii.gz')
        for level in [-.65, -.30, .05, .40, .75]:
            nodes, segments, positions = {}, [], []
            def intersection(a, b):
                key = tuple(sorted((int(a), int(b))))
                if key not in nodes:
                    t = (level - float(sulc[a])) / float(sulc[b] - sulc[a])
                    nodes[key] = len(positions)
                    positions.append(full[a] * (1 - t) + full[b] * t)
                return nodes[key]
            for face in full_faces:
                crossings = []
                for a, b in [(face[0], face[1]), (face[1], face[2]), (face[2], face[0])]:
                    if (sulc[a] < level) != (sulc[b] < level):
                        crossings.append(intersection(a, b))
                if len(crossings) == 2:
                    segments.append(crossings)
            adjacent = [[] for _ in positions]
            for a, b in segments:
                adjacent[a].append(b); adjacent[b].append(a)
            used = set()
            for a, b in segments:
                if tuple(sorted((a, b))) in used:
                    continue
                path, previous, current = [a], a, b
                while True:
                    used.add(tuple(sorted((previous, current))))
                    path.append(current)
                    nxt = [n for n in adjacent[current] if tuple(sorted((current, n))) not in used]
                    if not nxt:
                        break
                    previous, current = current, nxt[0]
                if len(path) < 12:
                    continue
                reduced = [positions[path[0]]]
                for i in path[1:-1]:
                    if np.linalg.norm(positions[i] - reduced[-1]) > .018:
                        reduced.append(positions[i])
                reduced.append(positions[path[-1]])
                if len(reduced) >= 6:
                    curve_points.extend(reduced); curve_lengths.append(len(reduced))

    # Small authored wire structures complete the silhouette. These are visual
    # approximations, not parts supplied by the fsaverage cortical dataset.
    def add(point, region, strength=.6):
        points.append(point); regions.append(region); ridge.append(strength)
        return len(points) - 1

    for side in [-1, 1]:
        rings = []
        for j in range(15):
            lat = -.5 * np.pi + (j + .5) / 15 * np.pi
            ring = []
            for i in range(42):
                a = i / 42 * 2 * np.pi
                folds = 1 + .035 * np.sin(j * 2.8 + a * 3)
                ring.append(add([side * .22 + .32 * np.cos(lat) * np.cos(a) * folds,
                                 -.60 + .28 * np.sin(lat),
                                 -.52 + .40 * np.cos(lat) * np.sin(a) * folds], 'cerebellum'))
            edges.extend([[ring[i], ring[(i + 1) % 42]] for i in range(42)])
            curve_points.extend([points[index] for index in ring] + [points[ring[0]]])
            curve_lengths.append(43)
            if rings:
                edges.extend([[rings[-1][i], ring[i]] for i in range(0, 42, 3)])
            rings.append(ring)
    rings = []
    for j in range(16):
        t = j / 15
        radius = .10 * (1 - .53 * t) + .065 * np.exp(-((t - .2) / .22) ** 2)
        ring = [add([radius * np.cos(i / 16 * 2 * np.pi), -.48 - .57 * t,
                     -.21 + .12 * t + radius * .8 * np.sin(i / 16 * 2 * np.pi)], 'stem') for i in range(16)]
        edges.extend([[ring[i], ring[(i + 1) % 16]] for i in range(16)])
        if rings:
            edges.extend([[rings[-1][i], ring[i]] for i in range(0, 16, 2)])
        rings.append(ring)

    coords = np.asarray(points, dtype=float)
    links = np.asarray(edges, dtype='<u2')
    assert len(points) < 65536 and np.isfinite(coords).all()
    packed = {
        'positions': base64.b64encode(np.rint(coords * 12000).astype('<i2').tobytes()).decode(),
        'edges': base64.b64encode(links.tobytes()).decode(),
        'ridge': base64.b64encode(np.rint(np.asarray(ridge) * 255).astype('u1').tobytes()).decode(),
        'regions': [regions.count(key) for key in ['left', 'right', 'cerebellum', 'stem']],
        'count': len(points), 'edgeCount': len(edges), 'scale': 12000,
        'filaments': base64.b64encode(np.rint(np.asarray(curve_points) * 12000).astype('<i2').tobytes()).decode(),
        'curveLengths': curve_lengths,
    }
    # All left/right vertices precede the two authored structures.
    payload = '/* Reduced fsaverage5 cortex: Nilearn, BSD-3-Clause. See licenses/brain-geometry.txt. */\nwindow.AllmaBrainGeometry=' + json.dumps(packed, separators=(',', ':')) + ';\n'
    target.write_text(payload)
    provenance = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(source.glob('nilearn-*.gii.gz')) if p.stat().st_size > 1000}
    print(json.dumps({'points': len(points), 'edges': len(edges), 'filament_points': len(curve_points), 'filaments': len(curve_lengths), 'bytes': target.stat().st_size, 'source_sha256': provenance}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[1] / 'assets/web/brain_geometry.js')
    args = parser.parse_args()
    build(args.source_dir, args.output)
