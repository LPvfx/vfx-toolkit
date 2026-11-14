# Radar: six months in review (mid-May to mid-Nov 2026)

A look back over the period, not a weekly edition. It pulls together what the
[baseline](2026-11-01.md) and weekly editions logged, plus a few things they
missed. It's organised around the shifts that change how you'd work, rather
than around model drops.

**Confidence.** Items marked **(title only)** were confirmed by search listings
(the page title and URL) but not read in full. Their dates and links are real,
but check licences and details before you rely on them. Everything else was
verified in the earlier editions.

## The five shifts

1. **Splats became a native data type, not a plugin.**
   - The standards came first: the Khronos `KHR_gaussian_splatting` RC (Feb) and OpenUSD 26.03 splat prims (Mar).
   - Then every DCC you use shipped native splats within about four months:
     - **Houdini 22** (GA July): training in TOPs, rasterising in Copernicus, deformers, Karma back to 3DGS.
     - **Nuke 17.1** (20 Aug): dynamic splats and basic relighting.
     - **Nuke 18.0** open beta (late Oct): splat isolation. **(title only)**
     - **Blender 5.3** (10 Nov).
     - **UE 5.9 Preview** (Nov): experimental.
   - Paid capture services opened up alongside: World Labs Atlas, SpAItial Echo-3, Hesai Kosmo.
   - **What changed:** the question is no longer "can I get splats into X" but "does the USD round-trip keep orientation, SH and scale intact".
2. **COLMAP stopped being the default.** Feed-forward reconstruction now solves cameras and dense points directly from footage.
   - **VGGT-Ω** (CVPR'26, best-paper finalist).
   - **Depth Anything 3**, with Apache-licensed Small and Base models.
   - **Holo4D** (4D reconstruction used as control for video diffusion).
   - **What changed:** layout, matchmove previs and splat capture from witness-cam or phone footage need no SfM step, and DA3 and VGGT-Ω inference is plausible on the Mac.
3. **Open video consolidated around LTX, and licences became the real filter.**
   - **LTX-2.5** (Aug) plus IC-LoRAs is the VFX-shaped open model: depth, pose and track control, the Clean Plate and SDR→HDR LoRAs, and an MLX port.
   - **Wan** stopped at 2.2 for open weights.
   - **MiniMax H3** (weights in Aug) is the most capable open video model, but its licence **excludes the UK**. The same goes for everything built on it (Viggle Remake, P-H3-Image, FastH3, the H3 MLX ports).
   - **Tencent** models (HunyuanVideo 1.5, HY-World) are similarly restricted.
   - **What changed:** for UK studio work, the usable open stack is effectively LTX, Wan 2.2 and Apache/MIT research code.
4. **Agents moved inside the DCCs.** The big apps now ship official MCP servers or agent hooks:
   - Blender Lab MCP v1.0 (Apr).
   - SideFX's Apex Script MCP (previewed at the H22 launch, not released).
   - Maxon C4D 2026.4 MCP server (Sept). **(title only)**
   - Resolve Studio 21.1 native MCP (Sept).
   - Derivative TDMCP (public beta).
   - Comfy MCP.
   - UE 5.9's MCP client, server and agent stack (Nov).
   - Maya 2027.2 also lets you train your own MotionMaker models (July). **(title only)**
   - **What changed:** "have Claude build the network and render it back to check" is now a supported workflow in TouchDesigner, Blender, Resolve and Unreal, not a hack. Houdini is still community-led: fxhoudinimcp is the best fit for the Mac.
5. **The Mac became a real inference box for this work.**
   - **WWDC26 (June):** Apple announced *Core AI* as the successor to Core ML, with MLX treated as first class. **(title only)**
   - **MLX ports** now cover:
     - video (ltx-2-mlx, mlx-video-rs);
     - image-to-3D (pixal3d-mlx);
     - splat training (gsplat-mlx);
     - segmentation (`mlx-community/sam3.1-bf16`, `mlx_sam3`) **(title only)**.
   - **What changed:** the 64GB M5 Pro handles depth, segmentation, splats and image-to-3D locally. Video generation and anything 14B-plus is still a rented-GPU job.

## Roto, matting and plate tools

Steady progress, mostly incremental:
- **Segmentation:** SAM 3 and 3.1, with text-prompted video tracking.
- **Matting:** MatAnyone 2 (CVPR'26), the best open hair mattes (NC). SAM2Matting (ECCV'26, FudanCVL) generalises SAM 2 to image and video matting. https://github.com/FudanCVL/SAM2Matting **(title only; check its licence)**
- **Roto GUIs:** Sammie-Roto 2 and Better-Brush wrap SAM 2 propagation and matting in local editors. https://github.com/Zarxrax/Sammie-Roto-2 · https://github.com/VFXNO/Better-Brush **(title only)**
- **Removal:** Netflix VOID (Apache), EffectErase (NC) and the LTX Clean Plate LoRA.
- **Upscaling:** SeedVR2, then RelayVSR (Apache 2.0, Nov).
- **Depth and intrinsics:** Marigold V2 (Apache: depth, normals, albedo), V-RGBX (NC intrinsics), PVDepth (360 video depth).

## Worth knowing, not yet worth trying

- **EasyVFX (SIGGRAPH'26).** Effect generation with frequency-based decoupling, aimed at lower compute. https://github.com/mayuelala/EasyVFX **(title only)**
- **Relightable splats for virtual production with image-based illumination** (arXiv, May). https://arxiv.org/html/2605.09024v1 **(title only)**
- **Spaghetti Splatting.** Strand-based splats for hair, with code due 23 Nov. https://arxiv.org/abs/2611.12716
- **Cosmos 3 Nano Sim-Transfer.** Turns depth or segmentation into video. OpenMDW licence, but it needs NVIDIA data-centre class hardware.

## Three mini projects

1. **The splat interchange test (Mac, free tools).**
   - Phone or witness-cam footage → VGGT-Ω or DA3 cameras (no COLMAP) → gsplat-mlx → write an OpenUSD 26.03 splat prim.
   - Open that one file in Houdini 22, Blender 5.3 and Nuke 17.1 (non-commercial), plus UE 5.9 if you're brave.
   - Check orientation, SH degree, scale and colour space in each, then write up what survives.
   - This is the pipeline question every studio will ask in 2027, and nobody has a clear answer yet.
2. **Agent-built projection rig (Mac).**
   - Have Claude use Derivative's TDMCP to build a TouchDesigner network.
   - Live camera → SAM 3.1 (MLX) person masks → mask-driven projection onto a performer, with DA3-Small depth for parallax.
   - Let it render TOPs back to check its own work.
   - Tests two of the six-month shifts at once: in-app agents and local segmentation at interactive rates.
3. **Generative vs reconstructive reshoot (rent a GPU).**
   - Take one real plate with a camera move.
   - **Path A:** a new camera path with ReCamMaster or Holo4D.
   - **Path B:** VGGT-Ω → splat → re-render the new path in Houdini 22 or Blender 5.3.
   - Compare parallax accuracy, temporal stability and how fixable each is in comp.
   - This tells you where generative reshoots beat the 3D route today, and where they still hallucinate.

## What to watch next

- SIGGRAPH Asia (1–4 Dec, Kuala Lumpur).
- Nuke 18.0 final.
- UE 5.9 final (planned for next year).
- A real SideFX MCP release in Labs.
- Whether Lightricks ships an LTX-3.
- Whether a UK-usable open model catches up with MiniMax H3.
