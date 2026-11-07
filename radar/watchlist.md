# Watchlist: things worth actually trying

This is a curated, living list. The weekly radar adds to it, and finished or stale items get struck through.
Columns:
- **where:** `mac` runs locally, `gpu` needs a rented card (comfy-cloud).
- **licence:** ok, NC (non-commercial), Tencent (excludes the UK), or H3 (MiniMax H3 licence: excludes the UK, EU, US and Korea, so skip MiniMax H3, Viggle Remake and P-H3-Image).

## Try first (runs on the Mac)

| what | why | where | licence | link |
|---|---|---|---|---|
| Apple SHARP | photo → metric splat in under 1s; feed TouchDesigner / Houdini | mac | check | https://github.com/apple/ml-sharp |
| ltx-2-mlx (LTX-2.5) | local text/image→video with depth/pose control | mac (slow) | LTX community | https://github.com/dgrauet/ltx-2-mlx |
| Depth Anything 3 Small/Base | depth, poses and splats from footage | mac | Apache 2.0 | https://github.com/ByteDance-Seed/depth-anything-3 |
| VGGT-Ω | cameras and points from video without COLMAP | mac (inference) | check | https://github.com/facebookresearch/vggt-omega |
| gsplat-mlx | train splats locally | mac | check | https://github.com/RobotFlow-Labs/gsplat-mlx |
| Pixal3D-mac / pixal3d-mlx | image → PBR asset; the MLX port needs no PyTorch (1024 res needs all 64GB) | mac | MIT + DINOv3 | https://github.com/pawel-mazurkiewicz/Pixal3D-mac · https://github.com/lyonsno/pixal3d-mlx |
| Blender 5.3 splats | native splats in Cycles/EEVEE; SplatPatch turns CG meshes into splats | mac | GPL | https://code.blender.org/2026/10/splatting-the-gaussians-into-blender/ |
| Derivative TDMCP | official TouchDesigner MCP: Claude builds and inspects networks | mac (likely) | Shared Use | https://github.com/TouchDesigner/TDMCP |
| MatAnyone 2 (Core ML) | hair-quality mattes | mac | NC | https://github.com/pq-yang/MatAnyone2 |

## Rent a GPU for

| what | why | licence | link |
|---|---|---|---|
| LTX-2.5 + IC-LoRAs in ComfyUI | full-speed video gen and the 2.3 Clean Plate LoRA | LTX community | `comfy-cloud up --models ltx25` |
| Netflix VOID | remove objects with their shadows, reflections and physics | Apache 2.0 | https://github.com/netflix/void-model |
| SAM 3.1 | text-prompted roto seeds across video | SAM (gated) | https://github.com/facebookresearch/sam3 |
| Marigold V2 | depth, normals and albedo at 2K | Apache 2.0 | https://github.com/huawei-bayerlab/marigold-v2 |
| ReCamMaster | new camera moves on existing footage | check | https://jianhongbai.github.io/ReCamMaster/ |
| Holo4D | 4D recon (VGGT-Ω) as geometric control for Wan, for reshoots and plate extension; the 14B peaks around 49GB, so rent an 80GB card | Apache code; check weights | https://github.com/NIRVANALAN/Holo4D |

## Weekend projects

1. **Phone video → Houdini 22 without COLMAP.**
   - Get cameras and dense points from VGGT-Ω or DA3.
   - Train the splat in H22 TOPs, or locally with gsplat-mlx.
   - Write it out as an OpenUSD 26.03 splat prim and comp it with CG in Copernicus.
   - Tests whether feed-forward solves are good enough for layout or matchmove.
2. **Projection-mapped splats in TouchDesigner.**
   - Turn stills into splats with SHARP and load them with GSOPs-TD or gsScene.
   - Have Claude build the network through Derivative's official TDMCP.
   - Drive parallax from tracked viewer or projector positions.
   - Add live DA3-Small depth as a reactive layer.
3. **Agentic Houdini → ComfyUI look-dev.**
   - Claude drives the Houdini MCP (Solaris profile) and the Comfy MCP.
   - Houdini renders depth and pose AOVs, which feed LTX-2.5 IC-LoRAs.
   - The results come back as plates.
4. **Clean-plate and roto shootout.**
   - Seed masks with SAM 3.1 and take alpha from MatAnyone 2.
   - Compare LTX Clean Plate, EffectErase and VOID on real plates with shadows and reflections.
   - Upscale with SeedVR2.
5. **Intrinsic relight.**
   - Decompose a plate into albedo and normals with V-RGBX or Marigold V2.
   - Relight it in TouchDesigner or Copernicus.
   - Alternatively, build a small Houdini/PDG synthetic dataset and compare it with Infinigen2.
