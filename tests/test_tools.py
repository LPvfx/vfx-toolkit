"""End-to-end tests: build small fixtures, run every tool against them."""

from __future__ import annotations

import json
import shutil
import subprocess

import pytest

import OpenImageIO as oiio

from vfxtk import contact, exr2proxy, layers, ocio_convert, seqinfo, usdinfo, vidprep
from vfxtk.seq import compress_frames, parse_frames, resolve

W, H = 128, 72


def write_multilayer(path, value):
    names = ("R", "G", "B", "A", "diffuse.R", "diffuse.G", "diffuse.B", "depth.Z")
    spec = oiio.ImageSpec(W, H, len(names), "half")
    spec.channelnames = names
    spec.attribute("compression", "zip")
    buf = oiio.ImageBuf(spec)
    oiio.ImageBufAlgo.fill(buf, (value, value * 0.5, 0.1, 1.0, 0.2, 0.3, 0.4, 10.0))
    assert buf.write(str(path)), buf.geterror()


@pytest.fixture
def renders(tmp_path):
    d = tmp_path / "renders"
    d.mkdir()
    for f in range(1001, 1011):
        if f == 1005:
            continue  # deliberate gap
        write_multilayer(d / f"beauty.{f}.exr", (f - 1000) / 10)
    for f in range(1, 4):
        buf = oiio.ImageBuf(oiio.ImageSpec(W, H, 3, "uint8"))
        oiio.ImageBufAlgo.fill(buf, (0.5, 0.2, 0.8))
        buf.write(str(d / f"plate_{f:04d}.png"))
    (d / "beauty.1003.exr.bak").write_text("ignored")
    return d


def test_frame_helpers():
    assert compress_frames([1, 2, 3, 5, 7, 8]) == "1-3,5,7-8"
    assert parse_frames("1-3,5,10-20x5") == [1, 2, 3, 5, 10, 15, 20]


def test_resolve_variants(renders):
    names = {s.name for s in resolve(renders)}
    assert {"beauty.####.exr", "plate_####.png"} <= names
    seq = resolve(renders / "beauty.####.exr")[0]
    assert seq.missing == [1005] and len(seq) == 9
    assert resolve(renders / "beauty.%04d.exr")[0].frames == seq.frames
    assert resolve(renders / "beauty.1003.exr")[0].frames == seq.frames


def test_seqinfo_json(renders, capsys):
    seqinfo.main([str(renders), "--json", "--check"])
    data = json.loads(capsys.readouterr().out)
    beauty = next(r for r in data if r["name"] == "beauty.####.exr")
    assert beauty["missing"] == "1005"
    assert beauty["channels"] == 8
    assert beauty["corrupt_count"] == 0


def test_layers_list_and_extract(renders, tmp_path, capsys):
    layers.main([str(renders / "beauty.1001.exr")])
    listing = capsys.readouterr().out
    assert "diffuse" in listing and "depth" in listing
    out = tmp_path / "aov"
    layers.main([str(renders / "beauty.####.exr"), "-e", "diffuse", "-o", str(out)])
    files = sorted(out.glob("*.exr"))
    assert len(files) == 9
    spec = oiio.ImageInput.open(str(files[0])).spec()
    assert list(spec.channelnames) == ["R", "G", "B"]


def test_contact(renders, tmp_path):
    sheet = tmp_path / "sheet.jpg"
    contact.main([str(renders / "beauty.####.exr"), "-n", "4", "-o", str(sheet), "--width", "64"])
    assert oiio.ImageBuf(str(sheet)).spec().width > 64


def test_ocio_convert(renders, tmp_path):
    out = tmp_path / "png"
    ocio_convert.main([str(renders / "beauty.####.exr"), "--display", "sRGB - Display",
                       "--ext", "png", "-o", str(out)])
    assert len(list(out.glob("*.png"))) == 9


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg missing")
def test_exr2proxy_and_vidprep(renders, tmp_path, capsys):
    mov = tmp_path / "beauty.mp4"
    exr2proxy.main([str(renders / "beauty.####.exr"), "-o", str(mov), "--burnin"])
    probe = vidprep.probe(str(mov))
    v = probe["streams"][0]
    assert v["width"] == W and int(v["nb_frames"]) == 10  # gap held, not dropped

    hap = tmp_path / "beauty_hap.mov"
    vidprep.main([str(mov), "-p", "hap", "-o", str(hap)])
    assert vidprep.probe(str(hap))["streams"][0]["codec_name"] == "hap"

    vert = tmp_path / "vert.mp4"
    vidprep.main([str(mov), "-p", "h264", "--frame", "9x16", "-o", str(vert)])
    s = vidprep.probe(str(vert))["streams"][0]
    assert (s["width"], s["height"]) == (1080, 1920)

    gif = tmp_path / "a.gif"
    vidprep.main([str(mov), "-p", "gif", "--width", "64", "-o", str(gif)])
    assert gif.stat().st_size > 0


def test_usdinfo(tmp_path, capsys):
    from pxr import Usd, UsdGeom, UsdShade

    path = tmp_path / "asset.usda"
    stage = Usd.Stage.CreateNew(str(path))
    root = UsdGeom.Xform.Define(stage, "/asset")
    stage.SetDefaultPrim(root.GetPrim())
    cube = UsdGeom.Mesh.Define(stage, "/asset/geo")
    cube.CreatePointsAttr([(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)])
    cube.CreateFaceVertexCountsAttr([4])
    cube.CreateFaceVertexIndicesAttr([0, 1, 2, 3])
    UsdShade.Material.Define(stage, "/asset/mtl/m")
    root.GetPrim().GetReferences().AddReference("./missing_thing.usd")
    stage.GetRootLayer().Save()

    usdinfo.main([str(path), "--json"])
    s = json.loads(capsys.readouterr().out)
    assert s["meshes"] == 1 and s["faces"] == 1 and len(s["materials"]) == 1
    assert s["meshes_without_material"] == 1
    assert any("missing_thing" in u for u in s["unresolved"])


def test_console_scripts_installed():
    # only meaningful after `uv tool install`, so just ensure entry points import
    for mod in (seqinfo, layers, contact, exr2proxy, ocio_convert, usdinfo, vidprep):
        assert callable(mod.main)
    assert subprocess.run(["python", "-m", "vfxtk.cli"], capture_output=True).returncode == 0
