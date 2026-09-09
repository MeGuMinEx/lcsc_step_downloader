"""Build the browser's basic body/lead preview as planar STEP solids.

The SMT preview extrudes layer 99 (body) and layer 100 (leads), using
fixed heights of 5..35 mil and 0..15 mil respectively. These are display
defaults, not dimensions measured from the actual component.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import math
import re

CANVAS_MM = 0.254
MIL_MM = 0.0254


class UnsupportedOutline(ValueError):
    pass


@dataclass(frozen=True)
class Region:
    points: tuple
    bottom: float
    top: float
    colour: tuple
    name: str


def _polygon(points):
    clean = []
    for point in points:
        if not all(math.isfinite(v) for v in point):
            raise UnsupportedOutline("轮廓坐标无效")
        if not clean or math.dist(point, clean[-1]) > 1e-8:
            clean.append(point)
    if clean and math.dist(clean[0], clean[-1]) < 1e-8:
        clean.pop()
    if not 3 <= len(clean) <= 2048:
        raise UnsupportedOutline("轮廓点数不受支持")
    area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(clean, clean[1:] + clean[:1]))
    if abs(area) < 1e-9:
        raise UnsupportedOutline("轮廓面积为零")
    if area < 0:
        clean.reverse()

    def cross(a, b, c):
        return (b[0]-a[0]) * (c[1]-a[1]) - (b[1]-a[1]) * (c[0]-a[0])

    for i in range(len(clean)):
        a, b = clean[i], clean[(i+1) % len(clean)]
        for j in range(i+2, len(clean)):
            if i == 0 and j == len(clean)-1:
                continue
            c, d = clean[j], clean[(j+1) % len(clean)]
            if (max(min(a[0], b[0]), min(c[0], d[0])) <= min(max(a[0], b[0]), max(c[0], d[0])) + 1e-9
                and max(min(a[1], b[1]), min(c[1], d[1])) <= min(max(a[1], b[1]), max(c[1], d[1])) + 1e-9
                and cross(a, b, c) * cross(a, b, d) <= 0
                and cross(c, d, a) * cross(c, d, b) <= 0):
                raise UnsupportedOutline("暂不支持自相交轮廓")
    return tuple(clean)


def _path_points(path):
    """Read a single closed, straight-sided SVG outline without dropping commands."""
    token_re = r"[A-Za-z]|[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?"
    tokens = re.findall(token_re, path)
    if re.sub(token_re + r"|[\s,]", "", path):
        raise UnsupportedOutline("无法识别轮廓路径")
    points, current, command, index, closed = [], (0.0, 0.0), None, 0, False
    while index < len(tokens):
        if tokens[index].isalpha():
            command = tokens[index]
            index += 1
        if command is None or command.upper() not in ("M", "L", "H", "V", "Z"):
            raise UnsupportedOutline("暂不支持该曲线轮廓")
        if closed:
            raise UnsupportedOutline("暂不支持带孔或复合轮廓")
        upper = command.upper()
        if upper == "Z":
            closed = True
            command = None
            continue
        count = 1 if upper in ("H", "V") else 2
        try:
            values = [float(v) for v in tokens[index:index + count]]
        except ValueError as exc:
            raise UnsupportedOutline("轮廓参数不完整") from exc
        if len(values) != count:
            raise UnsupportedOutline("轮廓参数不完整")
        index += count
        if upper == "M" and points:
            raise UnsupportedOutline("暂不支持带孔或复合轮廓")
        x, y = current
        relative = command.islower()
        if upper in ("M", "L"):
            x, y = (x + values[0], y + values[1]) if relative else values
        elif upper == "H":
            x = x + values[0] if relative else values[0]
        else:
            y = y + values[0] if relative else values[0]
        current = (x, y)
        points.append(current)
        if upper == "M":
            command = "l" if relative else "L"
    if not closed:
        raise UnsupportedOutline("轮廓未闭合")
    return points


def preview_regions(package):
    if not isinstance(package, dict) or not package.get("dataStr"):
        return ()
    data = package["dataStr"]
    if isinstance(data, str):
        data = json.loads(data)
    canvas = data.get("canvas", "").split("~")
    head = data.get("head") or {}
    ox = float(canvas[16]) if len(canvas) > 17 else float(head.get("x", 0))
    oy = float(canvas[17]) if len(canvas) > 17 else float(head.get("y", 0))
    regions = []

    def add(points, layer):
        points = _polygon([((x - ox) * CANVAS_MM, -(y - oy) * CANVAS_MM) for x, y in points])
        if layer == 99:
            regions.append(Region(points, 5 * MIL_MM, 35 * MIL_MM, (64/255,) * 3, "Body"))
        else:
            regions.append(Region(points, 0, 15 * MIL_MM, (196/255,) * 3, "Lead"))

    for shape in data.get("shape", []):
        fields = shape.split("~")
        if fields[0] == "SOLIDREGION" and len(fields) > 4 and fields[1] in ("99", "100"):
            if fields[4] != "solid":
                raise UnsupportedOutline("暂不支持带孔轮廓")
            add(_path_points(fields[3]), int(fields[1]))
        elif fields[0] == "CIRCLE" and len(fields) > 5 and fields[5] == "100":
            x, y, radius, stroke = map(float, fields[1:5])
            radius += stroke / 2
            if radius <= 0:
                raise UnsupportedOutline("圆形轮廓半径无效")
            add([(x + radius * math.cos(i * math.tau / 48),
                  y + radius * math.sin(i * math.tau / 48)) for i in range(48)], 100)
        elif fields[0] == "TRACK" and len(fields) > 4 and fields[2] in ("99", "100"):
            width = float(fields[1])
            coords = list(map(float, fields[4].split()))
            if width <= 0 or len(coords) % 2:
                raise UnsupportedOutline("线段轮廓无效")
            for i in range(0, len(coords) - 2, 2):
                x1, y1, x2, y2 = coords[i:i + 4]
                angle = math.atan2(y2-y1, x2-x1)
                points = [(x2 + width/2 * math.cos(angle-math.pi/2+j*math.pi/12),
                           y2 + width/2 * math.sin(angle-math.pi/2+j*math.pi/12)) for j in range(13)]
                points += [(x1 + width/2 * math.cos(angle+math.pi/2+j*math.pi/12),
                            y1 + width/2 * math.sin(angle+math.pi/2+j*math.pi/12)) for j in range(13)]
                add(points, int(fields[2]))
    if not any(r.name == "Body" for r in regions) or not any(r.name == "Lead" for r in regions):
        return ()
    if len(regions) > 256:
        raise UnsupportedOutline("简化轮廓数量过多")
    return tuple(regions)


def _number(value):
    if not math.isfinite(value):
        raise ValueError("Non-finite STEP coordinate")
    value = 0 if abs(value) < 1e-10 else value
    text = f"{value:.9f}".rstrip("0")
    return text if "." in text else text + "."


def build_step(lcsc_id, regions):
    """Write AP214 faceted solids using only Python's standard library."""
    if not re.fullmatch(r"C[0-9]+", lcsc_id) or not regions:
        raise ValueError("A valid part number and nonempty regions are required")
    lines = []

    def entity(value):
        ref = f"#{len(lines) + 1}"
        lines.append(f"{ref}={value};")
        return ref

    def xyz(kind, point):
        return entity(f"{kind}('',({','.join(_number(v) for v in point)}))")

    def placement(origin, normal=(0, 0, 1), xdir=(1, 0, 0)):
        return entity(f"AXIS2_PLACEMENT_3D('',{xyz('CARTESIAN_POINT', origin)},"
                      f"{xyz('DIRECTION', normal)},{xyz('DIRECTION', xdir)})")

    app = entity("APPLICATION_CONTEXT('core data for automotive mechanical design processes')")
    entity(f"APPLICATION_PROTOCOL_DEFINITION('international standard','automotive_design',2000,{app})")
    pctx = entity(f"PRODUCT_CONTEXT('',{app},'mechanical')")
    product = entity(f"PRODUCT('{lcsc_id}_simplified','{lcsc_id}_simplified','Generic preview heights',({pctx}))")
    formation = entity(f"PRODUCT_DEFINITION_FORMATION('','',{product})")
    dctx = entity(f"PRODUCT_DEFINITION_CONTEXT('part definition',{app},'design')")
    definition = entity(f"PRODUCT_DEFINITION('design','',{formation},{dctx})")
    product_shape = entity(f"PRODUCT_DEFINITION_SHAPE('','',{definition})")
    mm = entity("(LENGTH_UNIT() NAMED_UNIT(*) SI_UNIT(.MILLI.,.METRE.))")
    rad = entity("(NAMED_UNIT(*) PLANE_ANGLE_UNIT() SI_UNIT($,.RADIAN.))")
    sr = entity("(NAMED_UNIT(*) SI_UNIT($,.STERADIAN.) SOLID_ANGLE_UNIT())")
    uncertainty = entity(f"UNCERTAINTY_MEASURE_WITH_UNIT(LENGTH_MEASURE(1.E-7),{mm},'distance_accuracy_value','')")
    context = entity(f"(GEOMETRIC_REPRESENTATION_CONTEXT(3) GLOBAL_UNCERTAINTY_ASSIGNED_CONTEXT(({uncertainty})) "
                     f"GLOBAL_UNIT_ASSIGNED_CONTEXT(({mm},{rad},{sr})) REPRESENTATION_CONTEXT('','3D'))")
    axis = placement((0, 0, 0))
    solids, styled = [], []
    for region in regions:
        n = len(region.points)
        vertices = [(x, y, z) for z in (region.bottom, region.top) for x, y in region.points]
        refs = [xyz("CARTESIAN_POINT", vertex) for vertex in vertices]
        loops = [list(reversed(range(n))), list(range(n, 2*n))]
        loops += [[i, (i+1) % n, (i+1) % n + n, i+n] for i in range(n)]
        faces = []
        for loop in loops:
            points = [vertices[i] for i in loop]
            normal = [0., 0., 0.]
            for a, b in zip(points, points[1:] + points[:1]):
                normal[0] += (a[1]-b[1]) * (a[2]+b[2])
                normal[1] += (a[2]-b[2]) * (a[0]+b[0])
                normal[2] += (a[0]-b[0]) * (a[1]+b[1])
            magnitude = math.sqrt(sum(v*v for v in normal))
            normal = tuple(v / magnitude for v in normal)
            edge = tuple(b-a for a, b in zip(points[0], points[1]))
            length = math.sqrt(sum(v*v for v in edge))
            plane = entity(f"PLANE('',{placement(points[0], normal, tuple(v/length for v in edge))})")
            polyloop = entity(f"POLY_LOOP('',({','.join(refs[i] for i in loop)}))")
            bound = entity(f"FACE_OUTER_BOUND('',{polyloop},.T.)")
            faces.append(entity(f"FACE_SURFACE('',({bound}),{plane},.T.)"))
        shell = entity(f"CLOSED_SHELL('',({','.join(faces)}))")
        solid = entity(f"FACETED_BREP('{region.name}',{shell})")
        solids.append(solid)
        colour = entity(f"COLOUR_RGB('',{','.join(_number(v) for v in region.colour)})")
        fill_colour = entity(f"FILL_AREA_STYLE_COLOUR('',{colour})")
        fill = entity(f"FILL_AREA_STYLE('',({fill_colour}))")
        surface_fill = entity(f"SURFACE_STYLE_FILL_AREA({fill})")
        side = entity(f"SURFACE_SIDE_STYLE('',({surface_fill}))")
        usage = entity(f"SURFACE_STYLE_USAGE(.BOTH.,{side})")
        style = entity(f"PRESENTATION_STYLE_ASSIGNMENT(({usage}))")
        styled.append(entity(f"STYLED_ITEM('',({style}),{solid})"))
    representation = entity(f"FACETED_BREP_SHAPE_REPRESENTATION('',({','.join([axis] + solids)}),{context})")
    entity(f"SHAPE_DEFINITION_REPRESENTATION({product_shape},{representation})")
    entity(f"MECHANICAL_DESIGN_GEOMETRIC_PRESENTATION_REPRESENTATION('',({','.join(styled)}),{context})")
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    header = ("ISO-10303-21;\nHEADER;\n"
              "FILE_DESCRIPTION(('Simplified footprint preview; heights are generic'),'2;1');\n"
              f"FILE_NAME('{lcsc_id}_simplified.step','{timestamp}',(''),(''),"
              "'JLC STEP Downloader','JLC STEP Downloader','');\n"
              "FILE_SCHEMA(('AUTOMOTIVE_DESIGN'));\nENDSEC;\nDATA;\n")
    return (header + "\n".join(lines) + "\nENDSEC;\nEND-ISO-10303-21;\n").encode("ascii")
