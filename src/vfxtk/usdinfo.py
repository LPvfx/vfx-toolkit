"""usdinfo - quick health check of a USD file.

    usdinfo asset.usd                 summary: prims, meshes, materials, layers
    usdinfo shot.usda --deps          every file it pulls in, flags missing ones
    usdinfo asset.usd --tree 3        prim hierarchy to depth 3
    usdinfo asset.usd --json
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from rich.table import Table
from rich.tree import Tree

from .common import die, out


def _pxr():
    try:
        from pxr import Sdf, Usd, UsdGeom, UsdShade, UsdUtils  # noqa: F401
    except ImportError:
        die("usd-core missing - run ./bootstrap.sh")
    from pxr import Usd, UsdGeom, UsdShade, UsdUtils
    return Usd, UsdGeom, UsdShade, UsdUtils


def summarize(path: str) -> dict:
    Usd, UsdGeom, UsdShade, UsdUtils = _pxr()
    stage = Usd.Stage.Open(path)
    if not stage:
        die(f"could not open {path}")

    types: Counter = Counter()
    points = faces = 0
    materials, bound = [], 0
    variants: dict[str, list[str]] = {}
    instances = 0
    for prim in stage.TraverseAll():
        types[prim.GetTypeName() or "(untyped)"] += 1
        if prim.IsInstance():
            instances += 1
        if prim.IsA(UsdGeom.Mesh):
            mesh = UsdGeom.Mesh(prim)
            pts = mesh.GetPointsAttr().Get()
            fvc = mesh.GetFaceVertexCountsAttr().Get()
            points += len(pts) if pts else 0
            faces += len(fvc) if fvc else 0
            if UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial()[0]:
                bound += 1
        if prim.IsA(UsdShade.Material):
            materials.append(str(prim.GetPath()))
        vsets = prim.GetVariantSets()
        for name in vsets.GetNames():
            variants[f"{prim.GetPath()}:{name}"] = vsets.GetVariantSet(name).GetVariantNames()

    layers, assets, unresolved = UsdUtils.ComputeAllDependencies(Sdf_path(path))
    meshes = types.get("Mesh", 0)
    return {
        "file": path,
        "default_prim": str(stage.GetDefaultPrim().GetPath()) if stage.GetDefaultPrim() else None,
        "up_axis": UsdGeom.GetStageUpAxis(stage),
        "meters_per_unit": UsdGeom.GetStageMetersPerUnit(stage),
        "time": [stage.GetStartTimeCode(), stage.GetEndTimeCode()] if stage.HasAuthoredTimeCodeRange() else None,
        "fps": stage.GetFramesPerSecond(),
        "prims": sum(types.values()),
        "types": dict(types.most_common()),
        "meshes": meshes,
        "points": points,
        "faces": faces,
        "instances": instances,
        "materials": materials,
        "meshes_without_material": meshes - bound,
        "variant_sets": variants,
        "layers": [lyr.realPath or lyr.identifier for lyr in layers],
        "assets": [str(a) for a in assets],
        "unresolved": [str(u) for u in unresolved],
    }


def Sdf_path(path: str):
    from pxr import Sdf
    return Sdf.AssetPath(path)


def print_tree(path: str, depth: int):
    Usd, *_ = _pxr()
    stage = Usd.Stage.Open(path)
    root = Tree(f"[bold]{Path(path).name}[/]")

    def walk(prim, node, d):
        if d > depth:
            return
        for child in prim.GetChildren():
            label = f"{child.GetName()} [dim]{child.GetTypeName()}[/]"
            if child.IsInstance():
                label += " [cyan](instance)[/]"
            walk(child, node.add(label), d + 1)

    walk(stage.GetPseudoRoot(), root, 1)
    out.print(root)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="usdinfo", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--deps", action="store_true", help="list layers and assets")
    ap.add_argument("--tree", type=int, metavar="DEPTH", help="print prim hierarchy")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if not Path(args.file).exists():
        die(f"not found: {args.file}")
    if args.tree:
        print_tree(args.file, args.tree)
        return

    s = summarize(args.file)
    if args.json:
        out.print_json(json.dumps(s))
        return

    t = Table(show_header=False, box=None)
    t.add_column(style="bold")
    t.add_column()
    t.add_row("file", s["file"])
    t.add_row("default prim", str(s["default_prim"]))
    t.add_row("up / units", f"{s['up_axis']}  {s['meters_per_unit']} m/unit")
    if s["time"]:
        t.add_row("time", f"{s['time'][0]:g}-{s['time'][1]:g} @ {s['fps']:g} fps")
    t.add_row("prims", f"{s['prims']:,}")
    t.add_row("meshes", f"{s['meshes']:,}  ({s['points']:,} points, {s['faces']:,} faces)")
    t.add_row("instances", f"{s['instances']:,}")
    mats = f"{len(s['materials'])}"
    if s["meshes_without_material"]:
        mats += f"  [yellow]{s['meshes_without_material']} mesh(es) unbound[/]"
    t.add_row("materials", mats)
    t.add_row("variant sets", ", ".join(s["variant_sets"]) or "-")
    t.add_row("layers", str(len(s["layers"])))
    t.add_row("assets", str(len(s["assets"])))
    missing = s["unresolved"]
    t.add_row("unresolved", f"[red]{len(missing)}[/]" if missing else "[green]0[/]")
    t.add_row("types", ", ".join(f"{k} {v}" for k, v in list(s["types"].items())[:8]))
    out.print(t)

    if args.deps or missing:
        if args.deps:
            out.print("\n[bold]layers[/]")
            for x in s["layers"]:
                out.print(f"  {x}")
            out.print("\n[bold]assets[/]")
            for x in s["assets"]:
                out.print(f"  {x}")
        if missing:
            out.print("\n[bold red]unresolved[/]")
            for x in missing:
                out.print(f"  {x}")


if __name__ == "__main__":
    main()
