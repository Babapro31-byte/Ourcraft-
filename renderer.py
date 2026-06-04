from __future__ import annotations

import math
import os
import time
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import moderngl
import numpy as np




def perspective(fov_y: float, aspect: float, near: float, far: float) -> np.ndarray:
    f = 1.0 / math.tan(fov_y * 0.5)
    m = np.zeros((4, 4), dtype="f4")
    m[0, 0] = f / aspect
    m[1, 1] = f
    m[2, 2] = (far + near) / (near - far)
    m[2, 3] = (2.0 * far * near) / (near - far)
    m[3, 2] = -1.0
    m[3, 3] = 0.0
    return m


def look_at(eye: np.ndarray, target: np.ndarray, up: np.ndarray) -> np.ndarray:
    f = target - eye
    fn = np.linalg.norm(f)
    if fn == 0.0:
        f = np.array([0.0, 0.0, -1.0], dtype="f4")
    else:
        f = f / fn
    r = np.cross(f, up)
    rn = np.linalg.norm(r)
    if rn == 0.0:
        r = np.array([1.0, 0.0, 0.0], dtype="f4")
    else:
        r = r / rn
    u = np.cross(r, f)

    m = np.eye(4, dtype="f4")
    m[0, 0:3] = r
    m[1, 0:3] = u
    m[2, 0:3] = -f
    m[0, 3] = -float(np.dot(r, eye))
    m[1, 3] = -float(np.dot(u, eye))
    m[2, 3] = float(np.dot(f, eye))
    return m


def aabb_visible(mvp: np.ndarray, mn: Tuple[float, float, float], mx: Tuple[float, float, float]) -> bool:
    corners = np.array(
        [
            [mn[0], mn[1], mn[2], 1.0],
            [mx[0], mn[1], mn[2], 1.0],
            [mn[0], mx[1], mn[2], 1.0],
            [mx[0], mx[1], mn[2], 1.0],
            [mn[0], mn[1], mx[2], 1.0],
            [mx[0], mn[1], mx[2], 1.0],
            [mn[0], mx[1], mx[2], 1.0],
            [mx[0], mx[1], mx[2], 1.0],
        ],
        dtype="f4",
    )
    clip = corners @ mvp.T
    x = clip[:, 0]
    y = clip[:, 1]
    z = clip[:, 2]
    w = clip[:, 3]

    if np.all(x < -w):
        return False
    if np.all(x > w):
        return False
    if np.all(y < -w):
        return False
    if np.all(y > w):
        return False
    if np.all(z < -w):
        return False
    if np.all(z > w):
        return False
    return True


@dataclass(slots=True)
class ChunkGL:
    vbo_opaque: Optional[moderngl.Buffer]
    vao_opaque: Optional[moderngl.VertexArray]
    count_opaque: int
    vbo_cutout: Optional[moderngl.Buffer]
    vao_cutout: Optional[moderngl.VertexArray]
    count_cutout: int
    vbo_trans: Optional[moderngl.Buffer]
    vao_trans: Optional[moderngl.VertexArray]
    count_trans: int
    # Shadow-only VAOs (pos attribute only) reusing the existing VBOs
    shadow_vao_opaque: Optional[moderngl.VertexArray] = None
    shadow_vao_cutout: Optional[moderngl.VertexArray] = None

    def release(self) -> None:
        for obj in (self.vao_opaque, self.vbo_opaque, self.vao_cutout, self.vbo_cutout,
                    self.vao_trans, self.vbo_trans,
                    self.shadow_vao_opaque, self.shadow_vao_cutout):
            if obj is not None:
                obj.release()


class Renderer:
    def __init__(self, ctx: moderngl.Context, base_dir: str, atlas_data, uv_by_block_face, fov: float = 75.0):
        self.ctx = ctx
        self.base_dir = base_dir
        self.uv_by_block_face = uv_by_block_face
        self.fov = fov

        self.atlas = ctx.texture((atlas_data.size, atlas_data.size), 4, atlas_data.rgba_bytes)
        self.atlas.filter = (moderngl.NEAREST_MIPMAP_NEAREST, moderngl.NEAREST)
        self.atlas.repeat_x = True
        self.atlas.repeat_y = True
        self.atlas.build_mipmaps(base=0, max_level=4)
        # Keep per-name UV regions for billboard sprites (mobs, etc.).
        self.atlas_uv_by_name = dict(getattr(atlas_data, "uv_by_name", {}))

        self.program_block = self._load_program("block.vert", "block.frag")
        self.program_ui = self._load_program("ui.vert", "ui.frag")
        self.program_overlay = self._load_program("overlay.vert", "overlay.frag")

        self.program_block["u_atlas"].value = 0
        self.program_ui["u_ui"].value = 0
        self._elapsed = 0.0

        self.ctx.enable(moderngl.DEPTH_TEST)

        self.chunk_gl: Dict[Tuple[int, int], ChunkGL] = {}

        # Thread pool for mesh building. More workers drain the chunk-mesh queue faster on
        # load spikes (teleport / render-distance change), cutting main-thread upload stalls.
        self.executor = ThreadPoolExecutor(max_workers=4)
        self._pending_mesh: Dict[Tuple[int, int], Future] = {}
        self._ready_mesh: Dict[Tuple[int, int], object] = {}

        quad = np.array(
            [
                -1.0,
                -1.0,
                0.0,
                0.0,
                1.0,
                -1.0,
                1.0,
                0.0,
                1.0,
                1.0,
                1.0,
                1.0,
                -1.0,
                -1.0,
                0.0,
                0.0,
                1.0,
                1.0,
                1.0,
                1.0,
                -1.0,
                1.0,
                0.0,
                1.0,
            ],
            dtype="f4",
        )
        self.ui_vbo = ctx.buffer(quad.tobytes())
        self.ui_vao = ctx.vertex_array(self.program_ui, [(self.ui_vbo, "2f 2f", "in_pos", "in_uv")])

        self.ui_tex = None
        self.screen_size = (1, 1)

        self.overlay_vbo = None
        self.overlay_vao = None

        # Entity billboard renderer
        self._entity_vbo = None
        self._entity_vao = None
        self._entity_max_bytes = 0
        try:
            self.program_entity = self._load_program("entity.vert", "entity.frag")
            try:
                self.program_entity["u_atlas"].value = 0
            except KeyError:
                pass
        except Exception:
            self.program_entity = None

        # Item cube renderer (3D textured mini-cubes for ItemEntity)
        self._item_vbo = None
        self._item_vao = None
        self._item_max_bytes = 0
        try:
            self.program_item = self._load_program("item_cube.vert", "item_cube.frag")
            self.program_item["u_atlas"].value = 0
        except Exception:
            self.program_item = None

        # Sky dome (fullscreen NDC quad)
        try:
            self.program_sky = self._load_program("sky.vert", "sky.frag")
            sky_quad = np.array(
                [-1.0, -1.0,  1.0, -1.0,  1.0,  1.0,
                 -1.0, -1.0,  1.0,  1.0, -1.0,  1.0], dtype="f4",
            )
            self.sky_vbo = ctx.buffer(sky_quad.tobytes())
            self.sky_vao = ctx.vertex_array(
                self.program_sky, [(self.sky_vbo, "2f", "in_pos")]
            )
        except Exception:
            self.program_sky = None
            self.sky_vbo = None
            self.sky_vao = None

        # Shadow mapping (depth-only FBO + program)
        self.shadow_size = 2048
        self.shadow_enabled = True
        try:
            self.program_shadow = self._load_program("shadow.vert", "shadow.frag")
            self.shadow_depth = ctx.depth_texture((self.shadow_size, self.shadow_size))
            self.shadow_depth.filter = (moderngl.LINEAR, moderngl.LINEAR)
            self.shadow_depth.compare_func = "<="
            self.shadow_depth.repeat_x = False
            self.shadow_depth.repeat_y = False
            self.shadow_fbo = ctx.framebuffer(depth_attachment=self.shadow_depth)
            try:
                self.program_block["u_shadow_map"].value = 1
                self.program_block["u_shadow_enabled"].value = 1
            except KeyError:
                pass
        except Exception as e:
            print(f"Shadow init failed: {e}")
            self.program_shadow = None
            self.shadow_depth = None
            self.shadow_fbo = None
            self.shadow_enabled = False
            try:
                self.program_block["u_shadow_enabled"].value = 0
            except KeyError:
                pass

        # Particles (block break debris)
        self._particle_vbo = None
        self._particle_vao = None
        self._particle_max_bytes = 0
        try:
            self.program_particle = self._load_program("particle.vert", "particle.frag")
            self.program_particle["u_atlas"].value = 0
        except Exception as e:
            print(f"Particle init failed: {e}")
            self.program_particle = None

        # Stars: static unit-direction set distributed on upper hemisphere
        try:
            self.program_stars = self._load_program("stars.vert", "stars.frag")
            star_count = 800
            rng = np.random.default_rng(seed=2026)
            stars = []
            attempts = 0
            while len(stars) < star_count and attempts < star_count * 6:
                attempts += 1
                v = rng.normal(size=3).astype("f4")
                n = float(np.linalg.norm(v))
                if n < 1e-6:
                    continue
                v = v / n
                if v[1] < 0.05:
                    continue
                bright = float(rng.uniform(0.45, 1.0))
                stars.extend([float(v[0]), float(v[1]), float(v[2]), bright])
            star_data = np.array(stars, dtype="f4")
            self.stars_vbo = ctx.buffer(star_data.tobytes())
            self.stars_vao = ctx.vertex_array(
                self.program_stars,
                [(self.stars_vbo, "3f 1f", "in_dir", "in_bright")],
            )
            self.stars_count = len(stars) // 4
            ctx.enable(moderngl.PROGRAM_POINT_SIZE)
        except Exception as e:
            print(f"Stars init failed: {e}")
            self.program_stars = None
            self.stars_vbo = None
            self.stars_vao = None
            self.stars_count = 0

        # Celestial: sun + moon billboards
        try:
            self.program_celestial = self._load_program("celestial.vert", "celestial.frag")
            self.sun_tex = self._make_sun_texture(64)
            self.moon_tex = self._make_moon_texture(64)
            for t in (self.sun_tex, self.moon_tex):
                t.filter = (moderngl.LINEAR, moderngl.LINEAR)
            self.program_celestial["u_tex"].value = 0
            self.celestial_vbo = ctx.buffer(reserve=6 * 5 * 4)
            self.celestial_vao = ctx.vertex_array(
                self.program_celestial,
                [(self.celestial_vbo, "3f 2f", "in_pos", "in_uv")],
            )
        except Exception as e:
            print(f"Celestial init failed: {e}")
            self.program_celestial = None
            self.sun_tex = None
            self.moon_tex = None
            self.celestial_vbo = None
            self.celestial_vao = None

        # Clouds: two layers — low fluffy + high wispy. Per-session randomized.
        self.cloud_y = 192.0          # low layer
        self.cloud_y_high = 232.0     # high layer (above)
        self.cloud_size = 1024.0
        try:
            self.program_cloud = self._load_program("cloud.vert", "cloud.frag")
            # Low layer: denser puffs (128px detail)
            self.cloud_tex = self._make_cloud_texture(128, seed=None, threshold=0.48)
            self.cloud_tex.repeat_x = True
            self.cloud_tex.repeat_y = True
            self.cloud_tex.filter = (moderngl.NEAREST, moderngl.NEAREST)
            # High layer: sparser wisps (different seed, higher threshold)
            self.cloud_tex_high = self._make_cloud_texture(128, seed=None, threshold=0.58)
            self.cloud_tex_high.repeat_x = True
            self.cloud_tex_high.repeat_y = True
            self.cloud_tex_high.filter = (moderngl.NEAREST, moderngl.NEAREST)
            self.program_cloud["u_cloud_tex"].value = 0
            # Two triangles forming horizontal quad in local space; world position
            # will be set per-frame by translating positions in CPU buffer.
            self.cloud_vbo = ctx.buffer(reserve=6 * 3 * 4)
            self.cloud_vao = ctx.vertex_array(
                self.program_cloud, [(self.cloud_vbo, "3f", "in_pos")]
            )
        except Exception as e:
            print(f"Cloud init failed: {e}")
            self.program_cloud = None
            self.cloud_tex = None
            self.cloud_tex_high = None
            self.cloud_vbo = None
            self.cloud_vao = None

        # Bloom post-processing: scene FBO → extract → H-blur → V-blur → combine
        self._init_bloom(ctx)

    def _init_bloom(self, ctx):
        w, h = self.screen_size
        bw, bh = max(1, w // 2), max(1, h // 2)  # half-res bloom buffer
        try:
            self._bloom_scene_tex = ctx.texture((w, h), 4)
            self._bloom_scene_tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
            self._bloom_scene_fbo = ctx.framebuffer(
                color_attachments=[self._bloom_scene_tex],
                depth_attachment=ctx.depth_renderbuffer((w, h)),
            )

            self._bloom_extract_tex = ctx.texture((bw, bh), 4)
            self._bloom_extract_tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
            self._bloom_extract_fbo = ctx.framebuffer(color_attachments=[self._bloom_extract_tex])

            self._bloom_blur_tex = [ctx.texture((bw, bh), 4) for _ in range(2)]
            for t in self._bloom_blur_tex:
                t.filter = (moderngl.LINEAR, moderngl.LINEAR)
                t.repeat_x = False
                t.repeat_y = False
            self._bloom_blur_fbo = [
                ctx.framebuffer(color_attachments=[self._bloom_blur_tex[i]]) for i in range(2)
            ]

            self._prog_bloom_extract = self._load_program("bloom.vert", "bloom_extract.frag")
            self._prog_bloom_blur = self._load_program("bloom.vert", "bloom_blur.frag")
            self._prog_bloom_combine = self._load_program("bloom.vert", "bloom_combine.frag")
            self._prog_bloom_extract["u_scene"].value = 0
            self._prog_bloom_extract["u_threshold"].value = 0.85
            self._prog_bloom_blur["u_tex"].value = 0
            self._prog_bloom_combine["u_scene"].value = 0
            self._prog_bloom_combine["u_bloom"].value = 1
            self._prog_bloom_combine["u_bloom_strength"].value = 0.45

            # Full-screen NDC quad for bloom passes
            quad = np.array([-1, -1, 1, -1, 1, 1, -1, -1, 1, 1, -1, 1], dtype="f4")
            self._bloom_quad_vbo = ctx.buffer(quad.tobytes())
            self._bloom_quad_vao_extract = ctx.vertex_array(
                self._prog_bloom_extract, [(self._bloom_quad_vbo, "2f", "in_pos")]
            )
            self._bloom_quad_vao_blur = ctx.vertex_array(
                self._prog_bloom_blur, [(self._bloom_quad_vbo, "2f", "in_pos")]
            )
            self._bloom_quad_vao_combine = ctx.vertex_array(
                self._prog_bloom_combine, [(self._bloom_quad_vbo, "2f", "in_pos")]
            )
            self._bloom_enabled = False  # Bloom disabled — FBO combine clobbers depth state on some drivers
            self._bloom_size = (bw, bh)
        except Exception as e:
            print(f"Bloom init failed: {e}")
            self._bloom_enabled = False
            self._bloom_scene_fbo = None

    def _shader_path(self, name: str) -> str:
        return os.path.join(self.base_dir, "shaders", name)

    def _make_sun_texture(self, size: int = 64) -> moderngl.Texture:
        """Bright yellow disk with soft glow halo."""
        rgba = np.zeros((size, size, 4), dtype=np.uint8)
        cx = cy = size / 2.0
        for y in range(size):
            for x in range(size):
                dx = (x - cx) / cx
                dy = (y - cy) / cy
                d = math.sqrt(dx * dx + dy * dy)
                if d > 1.0:
                    continue
                # Core disk (0..0.55 radius solid), halo falloff beyond
                if d < 0.55:
                    alpha = 255
                    r, g, b = 255, 240, 180
                else:
                    t = (d - 0.55) / 0.45
                    falloff = max(0.0, 1.0 - t)
                    alpha = int(falloff * falloff * 200)
                    r, g, b = 255, 220, 140
                rgba[y, x] = (r, g, b, alpha)
        return self.ctx.texture((size, size), 4, rgba.tobytes())

    def _make_moon_texture(self, size: int = 64) -> moderngl.Texture:
        """Pale gray disk with darker craters."""
        rng = np.random.default_rng(seed=42)
        rgba = np.zeros((size, size, 4), dtype=np.uint8)
        cx = cy = size / 2.0
        craters = [(rng.uniform(-0.5, 0.5), rng.uniform(-0.5, 0.5), rng.uniform(0.08, 0.18)) for _ in range(5)]
        for y in range(size):
            for x in range(size):
                dx = (x - cx) / cx
                dy = (y - cy) / cy
                d = math.sqrt(dx * dx + dy * dy)
                if d > 0.92:
                    if d > 1.0:
                        continue
                    t = (d - 0.92) / 0.08
                    alpha = int((1.0 - t) * 255)
                else:
                    alpha = 255
                base = 235
                # Apply crater darkening
                for (cxn, cyn, cr) in craters:
                    cd = math.sqrt((dx - cxn) ** 2 + (dy - cyn) ** 2)
                    if cd < cr:
                        base -= int((1.0 - cd / cr) * 60)
                base = max(120, min(255, base))
                rgba[y, x] = (base, base, base + 5 if base + 5 < 255 else 255, alpha)
        return self.ctx.texture((size, size), 4, rgba.tobytes())

    def _make_cloud_texture(self, size: int = 128, seed: int = None,
                            threshold: float = 0.50) -> moderngl.Texture:
        """Procedural cloud pattern via 4-octave FBM with random per-session seed.
        Smoother organic shapes than binary 2-octave version."""
        if seed is None:
            seed = np.random.randint(0, 2**31 - 1)
        rng = np.random.default_rng(seed=seed)
        nx = ny = size

        # 4 octaves of value noise: each octave is a low-res random grid
        # upscaled by nearest-neighbor, then averaged with decreasing weight.
        accum = np.zeros((nx, ny), dtype=np.float32)
        weight_sum = 0.0
        for octave in range(4):
            cell = max(2, size // (8 // (2 ** octave) or 1))  # 8, 4, 2, 1 cell sizes
            grid_size = max(2, nx // cell)
            grid = rng.random((grid_size, grid_size)).astype(np.float32)
            upscaled = np.kron(grid, np.ones((cell, cell), dtype=np.float32))[:nx, :ny]
            weight = 0.5 ** octave
            accum += upscaled * weight
            weight_sum += weight
        noise = accum / weight_sum

        # Sigmoid-like soft threshold for smoother edges
        density = 1.0 / (1.0 + np.exp(-12.0 * (noise - threshold)))
        mask = (density > 0.5).astype(np.uint8)

        # Build RGBA: white where mask, transparent otherwise
        rgba = np.zeros((nx, ny, 4), dtype=np.uint8)
        rgba[..., 0] = 252
        rgba[..., 1] = 252
        rgba[..., 2] = 255
        rgba[..., 3] = mask * 255
        tex = self.ctx.texture((nx, ny), 4, rgba.tobytes())
        return tex

    def _load_program(self, vert_name: str, frag_name: str) -> moderngl.Program:
        with open(self._shader_path(vert_name), "r", encoding="utf-8") as f:
            vs = f.read()
        with open(self._shader_path(frag_name), "r", encoding="utf-8") as f:
            fs = f.read()
        return self.ctx.program(vertex_shader=vs, fragment_shader=fs)

    def _is_player_underwater(self, world, camera) -> bool:
        import math
        from .chunk import BLOCK_WATER
        try:
            pos = camera["pos"]
            px = int(math.floor(pos[0]))
            py = int(math.floor(pos[1]))
            pz = int(math.floor(pos[2]))
            return world.get_block(px, py, pz) == BLOCK_WATER
        except Exception:
            return False

    def resize(self, w: int, h: int) -> None:
        w = max(1, int(w))
        h = max(1, int(h))
        self.screen_size = (w, h)
        self.ctx.viewport = (0, 0, w, h)
        if self.ui_tex is not None:
            self.ui_tex.release()
        self.ui_tex = self.ctx.texture((w, h), 4)
        self.ui_tex.filter = (moderngl.NEAREST, moderngl.NEAREST)

    def _ensure_chunk_gl(self, key, chunk, world):
        gl = self.chunk_gl.get(key)
        if gl is None:
            gl = ChunkGL(None, None, 0, None, None, 0, None, None, 0)
            self.chunk_gl[key] = gl

        # If chunk is dirty and no pending mesh, submit build job to thread pool
        if chunk.dirty and key not in self._pending_mesh:
            future = self.executor.submit(chunk.build_mesh, world, self.uv_by_block_face)
            self._pending_mesh[key] = future
            chunk.dirty = False

    def _upload_mesh_to_gpu(self, key, gl, mesh):
        """Upload a completed mesh to GPU (must be called on main thread)."""
        for obj in (gl.vao_opaque, gl.vbo_opaque, gl.vao_cutout, gl.vbo_cutout, gl.vao_trans, gl.vbo_trans,
                    gl.shadow_vao_opaque, gl.shadow_vao_cutout):
            if obj is not None:
                obj.release()

        gl.vbo_opaque = None
        gl.vao_opaque = None
        gl.count_opaque = 0
        gl.vbo_cutout = None
        gl.vao_cutout = None
        gl.count_cutout = 0
        gl.vbo_trans = None
        gl.vao_trans = None
        gl.count_trans = 0
        gl.shadow_vao_opaque = None
        gl.shadow_vao_cutout = None

        # Shadow VAO uses only the position attribute. Stride = 14 floats = 56 bytes;
        # position is the first 3 floats (12 bytes), then we skip the remaining 11
        # floats (44 bytes) via "3f 44x".
        if mesh.opaque.size:
            gl.vbo_opaque = self.ctx.buffer(mesh.opaque.tobytes())
            gl.count_opaque = int(mesh.opaque.size // 14)
            gl.vao_opaque = self.ctx.vertex_array(
                self.program_block,
                [(gl.vbo_opaque, "3f 3f 2f 1f 1f 3f 1f",
                  "in_pos", "in_normal", "in_uv", "in_ao", "in_light", "in_tint", "in_anim")],
            )
            if self.program_shadow is not None:
                try:
                    gl.shadow_vao_opaque = self.ctx.vertex_array(
                        self.program_shadow,
                        [(gl.vbo_opaque, "3f 44x", "in_pos")],
                    )
                except Exception:
                    gl.shadow_vao_opaque = None
        if mesh.cutout.size:
            gl.vbo_cutout = self.ctx.buffer(mesh.cutout.tobytes())
            gl.count_cutout = int(mesh.cutout.size // 14)
            gl.vao_cutout = self.ctx.vertex_array(
                self.program_block,
                [(gl.vbo_cutout, "3f 3f 2f 1f 1f 3f 1f",
                  "in_pos", "in_normal", "in_uv", "in_ao", "in_light", "in_tint", "in_anim")],
            )
            if self.program_shadow is not None:
                try:
                    gl.shadow_vao_cutout = self.ctx.vertex_array(
                        self.program_shadow,
                        [(gl.vbo_cutout, "3f 44x", "in_pos")],
                    )
                except Exception:
                    gl.shadow_vao_cutout = None
        if mesh.translucent.size:
            gl.vbo_trans = self.ctx.buffer(mesh.translucent.tobytes())
            gl.count_trans = int(mesh.translucent.size // 14)
            gl.vao_trans = self.ctx.vertex_array(
                self.program_block,
                [(gl.vbo_trans, "3f 3f 2f 1f 1f 3f 1f",
                  "in_pos", "in_normal", "in_uv", "in_ao", "in_light", "in_tint", "in_anim")],
            )

    def _drop_missing_chunks(self, world) -> None:
        alive = set(world.chunks.keys())
        dead = [k for k in self.chunk_gl.keys() if k not in alive]
        for k in dead:
            self.chunk_gl[k].release()
            del self.chunk_gl[k]

    def _ensure_overlay(self, pos: Tuple[int, int, int]):
        x, y, z = pos
        verts = np.array(
            [
                x,
                y,
                z,
                x + 1,
                y,
                z,
                x + 1,
                y + 1,
                z,
                x,
                y,
                z,
                x + 1,
                y + 1,
                z,
                x,
                y + 1,
                z,
                x,
                y,
                z + 1,
                x + 1,
                y,
                z + 1,
                x + 1,
                y + 1,
                z + 1,
                x,
                y,
                z + 1,
                x + 1,
                y + 1,
                z + 1,
                x,
                y + 1,
                z + 1,
                x,
                y,
                z,
                x,
                y,
                z + 1,
                x,
                y + 1,
                z + 1,
                x,
                y,
                z,
                x,
                y + 1,
                z + 1,
                x,
                y + 1,
                z,
                x + 1,
                y,
                z,
                x + 1,
                y,
                z + 1,
                x + 1,
                y + 1,
                z + 1,
                x + 1,
                y,
                z,
                x + 1,
                y + 1,
                z + 1,
                x + 1,
                y + 1,
                z,
                x,
                y + 1,
                z,
                x + 1,
                y + 1,
                z,
                x + 1,
                y + 1,
                z + 1,
                x,
                y + 1,
                z,
                x + 1,
                y + 1,
                z + 1,
                x,
                y + 1,
                z + 1,
                x,
                y,
                z,
                x + 1,
                y,
                z,
                x + 1,
                y,
                z + 1,
                x,
                y,
                z,
                x + 1,
                y,
                z + 1,
                x,
                y,
                z + 1,
            ],
            dtype="f4",
        )
        if self.overlay_vbo is None:
            self.overlay_vbo = self.ctx.buffer(verts.tobytes())
            self.overlay_vao = self.ctx.vertex_array(self.program_overlay, [(self.overlay_vbo, "3f", "in_pos")])
        else:
            self.overlay_vbo.orphan(verts.nbytes)
            self.overlay_vbo.write(verts.tobytes())

    def upload_ui(self, rgba_bytes: bytes) -> None:
        if self.ui_tex is None:
            return
        self.ui_tex.write(rgba_bytes)

    def _sky_from_time(self, tod: float):
        """Return (sun_dir, sky_color, sky_horizon, sky_zenith, night_factor) for time-of-day [0,1].

        Wide 10% transition windows + smoothstep interpolation for cinematic sunsets.
        Sunrise and sunset have distinct color palettes.
        """
        angle = tod * 2.0 * math.pi
        sun_dir = (math.cos(angle), math.sin(angle), 0.35)

        # Horizon and zenith palettes per time of day
        night_h  = (0.02, 0.02, 0.08)
        night_z  = (0.01, 0.01, 0.04)
        # Sunrise: warm yellow-pink with violet zenith
        dawn_h   = (0.98, 0.62, 0.32)
        dawn_z   = (0.55, 0.35, 0.55)
        # Sunset: redder, more saturated, deeper indigo zenith
        dusk_h   = (1.00, 0.40, 0.20)
        dusk_z   = (0.45, 0.20, 0.45)
        day_h    = (0.70, 0.85, 0.95)
        day_z    = (0.30, 0.55, 0.95)

        def lerp3(a, b, t):
            return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))

        def smoothstep(t):
            t = max(0.0, min(1.0, t))
            return t * t * (3.0 - 2.0 * t)

        # Transition windows (each 5% of day, total 10% sunrise + 10% sunset):
        #   night → dawn:  0.20–0.25 (5%)
        #   dawn  → day:   0.25–0.30 (5%)
        #   day   → dusk:  0.68–0.73 (5%)
        #   dusk  → night: 0.73–0.78 (5%)
        # At 1800s/day, 5% = 90s — gentle ~1.5 min twilight phases.
        if tod < 0.20:
            hor, zen = night_h, night_z;        night_f = 1.0
        elif tod < 0.25:
            t = smoothstep((tod - 0.20) / 0.05)
            hor = lerp3(night_h, dawn_h, t)
            zen = lerp3(night_z, dawn_z, t)
            night_f = 1.0 - t
        elif tod < 0.30:
            t = smoothstep((tod - 0.25) / 0.05)
            hor = lerp3(dawn_h, day_h, t)
            zen = lerp3(dawn_z, day_z, t)
            night_f = 0.0
        elif tod < 0.68:
            hor, zen = day_h, day_z;            night_f = 0.0
        elif tod < 0.73:
            t = smoothstep((tod - 0.68) / 0.05)
            hor = lerp3(day_h, dusk_h, t)
            zen = lerp3(day_z, dusk_z, t)
            night_f = 0.0
        elif tod < 0.78:
            t = smoothstep((tod - 0.73) / 0.05)
            hor = lerp3(dusk_h, night_h, t)
            zen = lerp3(dusk_z, night_z, t)
            night_f = t
        else:
            hor, zen = night_h, night_z;        night_f = 1.0

        # Legacy sky_color: blend horizon+zenith for fog (used by block.frag)
        sky_color = tuple((hor[i] * 0.6 + zen[i] * 0.4) for i in range(3))

        return sun_dir, sky_color, hor, zen, float(max(0.0, min(1.0, night_f)))

    def render_title(self, ui_rgba: bytes) -> None:
        """Render only the UI overlay on a dark background (for title screen)."""
        self.ctx.clear(0.05, 0.05, 0.12, 1.0, depth=1.0)
        if self.ui_tex is None:
            return
        self.upload_ui(ui_rgba)
        self.ctx.disable(moderngl.DEPTH_TEST)
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)
        self.ui_tex.use(0)
        self.ui_vao.render(mode=moderngl.TRIANGLES)
        self.ctx.disable(moderngl.BLEND)
        self.ctx.enable(moderngl.DEPTH_TEST)

    def render_entities(self, entities: list, camera: dict, mvp: np.ndarray,
                        sun_dir=None, night_factor: float = 0.0, world=None) -> None:
        """Render entities: ItemEntity as textured rotating mini-cubes, mobs as 3D box models."""
        alive = [e for e in entities if getattr(e, 'alive', False)]
        if not alive:
            return
        items = [e for e in alive if hasattr(e, 'stack') and hasattr(e, 'age')]
        mobs = [e for e in alive if e not in items]
        _sun = sun_dir if sun_dir is not None else (0.55, 1.0, 0.35)
        if mobs:
            self._render_mob_parts(mobs, mvp, _sun, night_factor, world)
        if items:
            self._render_item_cubes(items, camera, mvp, _sun, night_factor, world)

    def _sample_entity_light(self, world, x: float, y: float, z: float,
                             night_factor: float) -> float:
        """Brightness [0.20, 1.0] from world sky+block light at an entity position.

        Mirrors the block mesh: sky light is attenuated by time-of-day so mobs
        darken at night, while torch/block light keeps them lit in caves.
        """
        if world is None:
            return 1.0
        ix = int(math.floor(x)); iy = int(math.floor(y)); iz = int(math.floor(z))
        try:
            blk = world.get_block_light(ix, iy, iz) / 15.0
            sky = world.get_sky_light(ix, iy, iz) / 15.0
        except Exception:
            return 1.0
        day_brightness = 1.0 - 0.85 * float(night_factor)
        eff = max(blk, sky * day_brightness)
        return 0.20 + 0.80 * eff

    def _render_mob_billboards(self, alive: list, camera: dict, mvp: np.ndarray) -> None:
        """Render entity billboards as textured camera-facing quads (mob sprites)."""
        if self.program_entity is None:
            return
        if not alive:
            return

        from .entity import MOB_TEXTURE_NAMES

        fwd = np.array(camera["forward"], dtype="f4")
        world_up = np.array([0.0, 1.0, 0.0], dtype="f4")
        right = np.cross(fwd, world_up)
        rn = float(np.linalg.norm(right))
        if rn < 1e-6:
            return
        right = right / rn

        verts = []
        for ent in alive:
            ex = float(ent.pos[0])
            ey = float(ent.pos[1]) + float(ent.height) * 0.5
            ez = float(ent.pos[2])
            w2 = float(ent.width) * 0.5
            h2 = float(ent.height) * 0.5

            color = getattr(ent, 'color', (1.0, 0.5, 0.0, 1.0))
            if getattr(ent, '_hit_flash_timer', 0.0) > 0.0:
                color = (1.0, 1.0, 1.0, 1.0)
            r, g, b, a = color

            # Resolve sprite atlas region for this mob type.
            mob_type = getattr(ent, 'mob_type', None)
            tex_name = MOB_TEXTURE_NAMES.get(mob_type, "") if mob_type else ""
            uv = self.atlas_uv_by_name.get(tex_name)
            if uv is None:
                # No sprite: collapse UVs so shader falls back to v_color.
                u0 = v0u = u1 = v1u = 0.0
            else:
                u0, v0u, u1, v1u = uv

            p = np.array([ex, ey, ez], dtype="f4")
            v0 = p - right * w2 - world_up * h2  # bottom-left
            v1 = p + right * w2 - world_up * h2  # bottom-right
            v2 = p + right * w2 + world_up * h2  # top-right
            v3 = p - right * w2 + world_up * h2  # top-left

            # Sprite is "right-side up" — top of sprite at top of quad.
            # Atlas v grows downward in texture space (top row = small v) — flip
            # so v1u (larger v in atlas) is at the bottom of the quad.
            uv_bl = (u0, v1u)
            uv_br = (u1, v1u)
            uv_tr = (u1, v0u)
            uv_tl = (u0, v0u)

            quad_uvs = (uv_bl, uv_br, uv_tr, uv_bl, uv_tr, uv_tl)
            quad_verts = (v0, v1, v2, v0, v2, v3)

            for v, (uu, vv) in zip(quad_verts, quad_uvs):
                verts.extend([float(v[0]), float(v[1]), float(v[2]),
                              r, g, b, a, uu, vv])

        if not verts:
            return

        data = np.array(verts, dtype="f4")
        n_bytes = data.nbytes

        if self._entity_vbo is None or n_bytes > self._entity_max_bytes:
            if self._entity_vbo is not None:
                self._entity_vao.release()
                self._entity_vbo.release()
            self._entity_vbo = self.ctx.buffer(data.tobytes())
            self._entity_vao = self.ctx.vertex_array(
                self.program_entity,
                [(self._entity_vbo, "3f 4f 2f", "in_pos", "in_color", "in_uv")],
            )
            self._entity_max_bytes = n_bytes
        else:
            self._entity_vbo.orphan(n_bytes)
            self._entity_vbo.write(data.tobytes())

        self.atlas.use(0)
        self.program_entity["u_mvp"].write(mvp.T.tobytes())
        self.ctx.disable(moderngl.CULL_FACE)
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)
        self._entity_vao.render(moderngl.TRIANGLES, vertices=len(verts) // 9)
        self.ctx.disable(moderngl.BLEND)
        self.ctx.enable(moderngl.CULL_FACE)

    def _render_mob_parts(self, alive: list, mvp: np.ndarray,
                          sun_dir=(0.55, 1.0, 0.35), night_factor: float = 0.0,
                          world=None) -> None:
        """Render mobs as Minecraft-style articulated 3D box models with walking animation."""
        if self.program_item is None or not alive:
            return

        from .entity import MOB_BOX_MODELS, Mob

        sim_time = self._elapsed
        face_local = [
            [(-1, -1,  1), (-1, -1, -1), (-1,  1, -1), (-1,  1,  1)],  # -X
            [( 1, -1, -1), ( 1, -1,  1), ( 1,  1,  1), ( 1,  1, -1)],  # +X
            [(-1, -1, -1), ( 1, -1, -1), ( 1, -1,  1), (-1, -1,  1)],  # -Y
            [(-1,  1,  1), ( 1,  1,  1), ( 1,  1, -1), (-1,  1, -1)],  # +Y
            [( 1, -1, -1), (-1, -1, -1), (-1,  1, -1), ( 1,  1, -1)],  # -Z
            [(-1, -1,  1), ( 1, -1,  1), ( 1,  1,  1), (-1,  1,  1)],  # +Z
        ]
        face_normals = [(-1,0,0),(1,0,0),(0,-1,0),(0,1,0),(0,0,-1),(0,0,1)]
        tri_idx = (0, 1, 2, 0, 2, 3)
        uv_corners = [(0, 1), (1, 1), (1, 0), (0, 0)]

        verts = []
        for ent in alive:
            if not isinstance(ent, Mob) or not ent.alive:
                continue
            mob_type = getattr(ent, 'mob_type', None)
            if mob_type is None:
                continue
            parts = MOB_BOX_MODELS.get(mob_type)
            if not parts:
                continue

            _rp = getattr(ent, 'render_pos', ent.pos)
            ex, ey, ez = float(_rp[0]), float(_rp[1]), float(_rp[2])
            # Frustum cull: skip building geometry for mobs outside the view cone
            # (the per-mob vertex build is the entity-render bottleneck).
            _cw = float(getattr(ent, 'width', 0.6)) * 0.6 + 0.5
            _ch = float(getattr(ent, 'height', 1.8)) + 0.3
            if not aabb_visible(mvp, (ex - _cw, ey - 0.2, ez - _cw), (ex + _cw, ey + _ch, ez + _cw)):
                continue
            # Sample world light once per mob at chest height.
            _mh = float(getattr(ent, 'height', 1.8))
            mob_light = self._sample_entity_light(world, ex, ey + _mh * 0.5, ez, night_factor)
            vx, vz = float(ent.vel[0]), float(ent.vel[2])
            speed = math.sqrt(vx*vx + vz*vz)
            yaw = math.atan2(vx, vz) if speed > 0.05 else 0.0
            walk_freq = 5.0 * min(speed / 2.5, 1.5)
            walk_phase = sim_time * walk_freq

            # hit flash: red tint on damage
            hit_flash = getattr(ent, '_hit_flash_timer', 0.0)
            flash = min(1.0, hit_flash * 5.0)  # 0-1 blend toward red

            cy, sy = math.cos(yaw), math.sin(yaw)

            _FACE_ROLE = ('left', 'right', 'bottom', 'top', 'back', 'front')
            _SIDE_FACES = frozenset({0, 1, 4})  # left, right, back use face_side fallback

            for part in parts:
                tex_name = part.get('tex', '')
                base_uv = self.atlas_uv_by_name.get(tex_name)
                if base_uv is None:
                    continue

                ox, oy, oz = part['offset']
                sw, sh, sd = [x * 0.5 for x in part['size']]

                # Leg/arm swing animation
                anim_angle = 0.0
                if part.get('animated') and speed > 0.05:
                    phase_off = part.get('phase', 0.0) * math.pi * 2
                    anim_angle = math.sin(walk_phase + phase_off) * 0.45

                # Rotate part offset by mob yaw
                rox = cy * ox + sy * oz
                roz = -sy * ox + cy * oz

                # Part world center
                pcx = ex + rox
                pcy = ey + oy
                pcz = ez + roz

                for fi, corners in enumerate(face_local):
                    fnx, fny, fnz = face_normals[fi]
                    # Rotate normal by yaw
                    rfnx = cy * fnx + sy * fnz
                    rfnz = -sy * fnx + cy * fnz

                    # Per-face UV: face_<role> → face_side (sides) → base tex
                    _role = _FACE_ROLE[fi]
                    _fk = part.get(f'face_{_role}')
                    if _fk is None and fi in _SIDE_FACES:
                        _fk = part.get('face_side')
                    _uv = (self.atlas_uv_by_name.get(_fk) if _fk else None) or base_uv
                    u0, v0_uv, u1, v1_uv = _uv
                    face_uv = [(u0, v1_uv), (u1, v1_uv), (u1, v0_uv), (u0, v0_uv)]

                    pts = []
                    for (lx, ly, lz) in corners:
                        # Scale to part half-extents
                        sx_c = lx * sw
                        sy_c = ly * sh
                        sz_c = lz * sd

                        # Apply animation (rotate around part center X axis for legs)
                        if anim_angle != 0.0:
                            ca, sa = math.cos(anim_angle), math.sin(anim_angle)
                            ny_c = ca * sy_c - sa * sz_c
                            nz_c = sa * sy_c + ca * sz_c
                            sy_c, sz_c = ny_c, nz_c

                        # Rotate by mob yaw
                        rx = cy * sx_c + sy * sz_c
                        rz = -sy * sx_c + cy * sz_c

                        pts.append((pcx + rx, pcy + sy_c, pcz + rz))

                    for i in tri_idx:
                        px_, py_, pz_ = pts[i]
                        uu, vv = face_uv[i]
                        verts.extend([px_, py_, pz_, uu, vv, rfnx, fny, rfnz, mob_light])

        if not verts:
            return

        data = np.array(verts, dtype="f4")
        n_bytes = data.nbytes
        if not hasattr(self, '_mob_vbo') or self._mob_vbo is None or n_bytes > getattr(self, '_mob_max_bytes', 0):
            if getattr(self, '_mob_vbo', None) is not None:
                self._mob_vao.release()
                self._mob_vbo.release()
            self._mob_vbo = self.ctx.buffer(data.tobytes())
            self._mob_vao = self.ctx.vertex_array(
                self.program_item,
                [(self._mob_vbo, "3f 2f 3f 1f", "in_pos", "in_uv", "in_normal", "in_light")],
            )
            self._mob_max_bytes = n_bytes
        else:
            self._mob_vbo.orphan(n_bytes)
            self._mob_vbo.write(data.tobytes())

        self.program_item["u_mvp"].write(mvp.T.tobytes())
        try:
            self.program_item["u_sun_dir"].value = tuple(float(x) for x in sun_dir)
            self.program_item["u_night_factor"].value = float(night_factor)
        except KeyError:
            pass
        self.atlas.use(0)
        self.ctx.enable(moderngl.DEPTH_TEST)
        self.ctx.disable(moderngl.BLEND)
        self.ctx.enable(moderngl.CULL_FACE)
        self._mob_vao.render(moderngl.TRIANGLES, vertices=len(verts) // 9)

    def _item_atlas_uv(self, item_id: int):
        """Return 6-face UV boxes for an item id, or None if not renderable."""
        from .chunk import BLOCK_BLOCKS_COUNT
        if 0 <= item_id < BLOCK_BLOCKS_COUNT:
            faces = []
            for face in range(6):
                uv = self.uv_by_block_face.get((item_id, face))
                if uv is None:
                    uv = self.uv_by_block_face.get((item_id, 4))  # fallback to top face
                if uv is None:
                    return None
                faces.append(uv)
            return faces
        # Item id (non-block): look up sprite via ItemDef.texture_name
        from .items import is_item_id, ITEMS
        if is_item_id(item_id):
            defn = ITEMS.get(item_id)
            if defn and defn.texture_name:
                uv = self.atlas_uv_by_name.get(defn.texture_name)
                if uv is not None:
                    return [uv] * 6
        return None

    def _render_item_cubes(self, items: list, camera: dict, mvp: np.ndarray,
                           sun_dir=(0.55, 1.0, 0.35), night_factor: float = 0.0,
                           world=None) -> None:
        """Render ItemEntity instances as 3D rotating textured mini-cubes."""
        if self.program_item is None or not items:
            return

        t = self._elapsed
        yaw = (t * 1.5) % (2.0 * math.pi)
        bob = math.sin(t * 2.0) * 0.06
        c = math.cos(yaw)
        s = math.sin(yaw)
        size = 0.25  # half-extent

        face_corners = [
            # -X face
            [(-size, -size,  size), (-size, -size, -size), (-size,  size, -size), (-size,  size,  size)],
            # +X face
            [( size, -size, -size), ( size, -size,  size), ( size,  size,  size), ( size,  size, -size)],
            # -Y face (bottom)
            [(-size, -size, -size), ( size, -size, -size), ( size, -size,  size), (-size, -size,  size)],
            # +Y face (top)
            [(-size,  size,  size), ( size,  size,  size), ( size,  size, -size), (-size,  size, -size)],
            # -Z face
            [( size, -size, -size), (-size, -size, -size), (-size,  size, -size), ( size,  size, -size)],
            # +Z face
            [(-size, -size,  size), ( size, -size,  size), ( size,  size,  size), (-size,  size,  size)],
        ]
        # Face normals in local space (before yaw rotation)
        face_normals_local = [
            (-1.0, 0.0, 0.0),
            ( 1.0, 0.0, 0.0),
            ( 0.0,-1.0, 0.0),
            ( 0.0, 1.0, 0.0),
            ( 0.0, 0.0,-1.0),
            ( 0.0, 0.0, 1.0),
        ]
        tri_indices = (0, 1, 2, 0, 2, 3)

        verts = []
        for ent in items:
            stack = getattr(ent, 'stack', None)
            if stack is None:
                continue
            item_id = int(getattr(stack, 'block_id', 0))
            face_uvs = self._item_atlas_uv(item_id)
            if face_uvs is None:
                continue

            _rp = getattr(ent, 'render_pos', ent.pos)
            ex = float(_rp[0])
            ey = float(_rp[1]) + 0.25 + bob
            ez = float(_rp[2])
            # Frustum cull dropped items outside the view.
            if not aabb_visible(mvp, (ex - 0.4, ey - 0.4, ez - 0.4), (ex + 0.4, ey + 0.4, ez + 0.4)):
                continue
            item_light = self._sample_entity_light(world, ex, ey, ez, night_factor)

            for face_idx, corners in enumerate(face_corners):
                u0, v0, u1, v1 = face_uvs[face_idx]
                uv_corners = [(u0, v1), (u1, v1), (u1, v0), (u0, v0)]
                # Rotate normal by yaw
                nx, ny, nz = face_normals_local[face_idx]
                rnx = c * nx + s * nz
                rnz = -s * nx + c * nz
                rotated = []
                for (lx, ly, lz) in corners:
                    rx = c * lx + s * lz
                    rz = -s * lx + c * lz
                    rotated.append((ex + rx, ey + ly, ez + rz))
                for i in tri_indices:
                    px, py, pz = rotated[i]
                    u, v = uv_corners[i]
                    verts.extend([px, py, pz, u, v, rnx, ny, rnz, item_light])

        if not verts:
            return

        data = np.array(verts, dtype="f4")
        n_bytes = data.nbytes
        if self._item_vbo is None or n_bytes > self._item_max_bytes:
            if self._item_vbo is not None:
                self._item_vao.release()
                self._item_vbo.release()
            self._item_vbo = self.ctx.buffer(data.tobytes())
            self._item_vao = self.ctx.vertex_array(
                self.program_item,
                [(self._item_vbo, "3f 2f 3f 1f", "in_pos", "in_uv", "in_normal", "in_light")],
            )
            self._item_max_bytes = n_bytes
        else:
            self._item_vbo.orphan(n_bytes)
            self._item_vbo.write(data.tobytes())

        self.program_item["u_mvp"].write(mvp.T.tobytes())
        try:
            self.program_item["u_sun_dir"].value = tuple(float(x) for x in sun_dir)
            self.program_item["u_night_factor"].value = float(night_factor)
        except KeyError:
            pass
        self.atlas.use(0)
        self.ctx.enable(moderngl.DEPTH_TEST)
        self.ctx.disable(moderngl.BLEND)
        self.ctx.disable(moderngl.CULL_FACE)
        self._item_vao.render(moderngl.TRIANGLES, vertices=len(verts) // 8)
        self.ctx.enable(moderngl.CULL_FACE)

    def render_particles(self, particles, camera: dict, mvp: np.ndarray, night_factor: float = 0.0) -> None:
        """Render block-break particles as camera-facing billboards."""
        if self.program_particle is None or particles is None:
            return
        verts = particles.build_vertex_data()
        if verts is None or verts.size == 0:
            return

        fwd = np.array(camera["forward"], dtype="f4")
        world_up = np.array([0.0, 1.0, 0.0], dtype="f4")
        right = np.cross(fwd, world_up)
        rn = float(np.linalg.norm(right))
        if rn < 1e-6:
            right = np.array([1.0, 0.0, 0.0], dtype="f4")
        else:
            right = right / rn
        up = np.cross(right, fwd)
        un = float(np.linalg.norm(up))
        if un < 1e-6:
            up = world_up
        else:
            up = up / un

        data = verts.astype("f4")
        n_bytes = data.nbytes
        if self._particle_vbo is None or n_bytes > self._particle_max_bytes:
            if self._particle_vbo is not None:
                self._particle_vao.release()
                self._particle_vbo.release()
            self._particle_vbo = self.ctx.buffer(data.tobytes())
            self._particle_vao = self.ctx.vertex_array(
                self.program_particle,
                [(self._particle_vbo, "3f 2f 2f 1f 1f",
                  "in_center", "in_offset", "in_uv", "in_size", "in_life")],
            )
            self._particle_max_bytes = n_bytes
        else:
            self._particle_vbo.orphan(n_bytes)
            self._particle_vbo.write(data.tobytes())

        self.program_particle["u_mvp"].write(mvp.T.tobytes())
        self.program_particle["u_cam_right"].value = (float(right[0]), float(right[1]), float(right[2]))
        self.program_particle["u_cam_up"].value = (float(up[0]), float(up[1]), float(up[2]))
        try:
            self.program_particle["u_night_factor"].value = float(night_factor)
        except KeyError:
            pass

        self.atlas.use(0)
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)
        self.ctx.disable(moderngl.CULL_FACE)
        self.ctx.depth_mask = False
        self._particle_vao.render(mode=moderngl.TRIANGLES, vertices=len(data))
        self.ctx.depth_mask = True
        self.ctx.enable(moderngl.CULL_FACE)
        self.ctx.disable(moderngl.BLEND)

    def _render_celestial(self, eye: np.ndarray, sun_dir, mvp: np.ndarray, camera: dict) -> None:
        """Render sun + moon billboards positioned along sun direction at large radius."""
        radius = 400.0
        size = 30.0

        fwd = np.array(camera["forward"], dtype="f4")
        world_up = np.array([0.0, 1.0, 0.0], dtype="f4")

        for is_sun in (True, False):
            direction = np.array(sun_dir, dtype="f4") if is_sun else -np.array(sun_dir, dtype="f4")
            dn = float(np.linalg.norm(direction))
            if dn < 1e-6:
                continue
            direction = direction / dn

            # Fade based on whether body is above horizon (y component of direction)
            if is_sun:
                alpha = max(0.0, min(1.0, direction[1] * 1.5 + 0.4))
            else:
                alpha = max(0.0, min(1.0, direction[1] * 1.5 + 0.4))
            if alpha <= 0.01:
                continue

            center = np.array(eye, dtype="f4") + direction * radius

            # Build camera-facing billboard quad axes
            view_dir = direction  # Looking from cam toward body, axes should be perpendicular to this
            right = np.cross(view_dir, world_up)
            rn = float(np.linalg.norm(right))
            if rn < 1e-6:
                right = np.array([1.0, 0.0, 0.0], dtype="f4")
            else:
                right = right / rn
            up = np.cross(right, view_dir)
            un = float(np.linalg.norm(up))
            if un < 1e-6:
                up = world_up
            else:
                up = up / un

            half = size * 0.5
            p0 = center - right * half - up * half
            p1 = center + right * half - up * half
            p2 = center + right * half + up * half
            p3 = center - right * half + up * half

            verts = np.array([
                p0[0], p0[1], p0[2], 0.0, 1.0,
                p1[0], p1[1], p1[2], 1.0, 1.0,
                p2[0], p2[1], p2[2], 1.0, 0.0,
                p0[0], p0[1], p0[2], 0.0, 1.0,
                p2[0], p2[1], p2[2], 1.0, 0.0,
                p3[0], p3[1], p3[2], 0.0, 0.0,
            ], dtype="f4")

            self.celestial_vbo.orphan(verts.nbytes)
            self.celestial_vbo.write(verts.tobytes())

            tex = self.sun_tex if is_sun else self.moon_tex
            tint = (1.0, 1.0, 1.0)

            self.program_celestial["u_mvp"].write(mvp.T.tobytes())
            self.program_celestial["u_alpha"].value = float(alpha)
            self.program_celestial["u_tint"].value = tint
            tex.use(0)

            self.ctx.enable(moderngl.BLEND)
            self.ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)
            self.ctx.disable(moderngl.CULL_FACE)
            self.ctx.depth_mask = False
            self.celestial_vao.render(mode=moderngl.TRIANGLES)
            self.ctx.depth_mask = True
            self.ctx.enable(moderngl.CULL_FACE)
            self.ctx.disable(moderngl.BLEND)

    def render(self, world, camera, render_distance_chunks: int, ui_rgba: bytes, selected, break_progress: float):
        self.ctx.screen.use()  # always start from the default framebuffer
        # Advance shader animation clock (water/lava UV scroll)
        now = time.perf_counter()
        last = getattr(self, "_last_time", now)
        self._elapsed += (now - last)
        self._last_time = now
        # Check for completed mesh builds and upload them to GPU
        completed_keys = []
        for key, future in list(self._pending_mesh.items()):
            if future.done():
                try:
                    mesh = future.result()
                    gl = self.chunk_gl[key]
                    self._upload_mesh_to_gpu(key, gl, mesh)
                    completed_keys.append(key)
                except Exception as e:
                    # Mesh building failed; log and remove from pending
                    print(f"Error building mesh for chunk {key}: {e}")
                    completed_keys.append(key)

        for key in completed_keys:
            del self._pending_mesh[key]

        self._drop_missing_chunks(world)
        self.atlas.use(0)

        w, h = self.screen_size

        # Redirect scene rendering into offscreen FBO for bloom post-processing
        if self._bloom_enabled and self._bloom_scene_fbo is not None:
            self._bloom_scene_fbo.use()
            self.ctx.viewport = (0, 0, w, h)
        aspect = w / h if h else 1.0
        proj = perspective(math.radians(self.fov), aspect, 0.1, 1200.0)
        eye = np.array(camera["pos"], dtype="f4")
        target = eye + np.array(camera["forward"], dtype="f4")
        view = look_at(eye, target, np.array([0.0, 1.0, 0.0], dtype="f4"))
        mvp = proj @ view
        self.program_block["u_mvp"].write(mvp.T.tobytes())
        self.program_block["u_cam_pos"].value = (float(eye[0]), float(eye[1]), float(eye[2]))

        # Fog mesafesini render distance'a bağla (chunk pop-in'ini maskeler).
        _rd_blocks = float(max(2, render_distance_chunks)) * 16.0
        _fog_end = _rd_blocks * 0.95
        _fog_start = _rd_blocks * 0.60
        try:
            self.program_block["u_fog_start"].value = _fog_start
            self.program_block["u_fog_end"].value = _fog_end
        except KeyError:
            pass

        # Day-night cycle
        tod = getattr(world, 'time_of_day', 0.5)
        sun_dir, sky_color, sky_horizon, sky_zenith, night_factor = self._sky_from_time(tod)
        self.program_block["u_sun_dir"].value = sun_dir
        self.program_block["u_sky_color"].value = sky_color
        try:
            self.program_block["u_sky_horizon"].value = sky_horizon
        except KeyError:
            pass
        try:
            self.program_block["u_sky_zenith"].value = sky_zenith
        except KeyError:
            pass
        try:
            self.program_block["u_night_factor"].value = night_factor
        except KeyError:
            pass
        # Animated water/lava UV scroll
        try:
            self.program_block["u_time"].value = float(self._elapsed)
        except KeyError:
            pass

        # Clear (color cleared by sky pass; keep fallback if sky shader missing)
        if self.program_sky is not None and self.sky_vao is not None:
            self.ctx.clear(depth=1.0)
        else:
            self.ctx.clear(*sky_color, 1.0, depth=1.0)

        # Sky dome pass (before everything, depth disabled)
        if self.program_sky is not None and self.sky_vao is not None:
            try:
                view_inv = np.linalg.inv(view).astype("f4")
                proj_inv = np.linalg.inv(proj).astype("f4")
                self.program_sky["u_view_inv"].write(view_inv.T.tobytes())
                self.program_sky["u_proj_inv"].write(proj_inv.T.tobytes())
                self.program_sky["u_sun_dir"].value = sun_dir
                self.program_sky["u_sky_horizon"].value = sky_horizon
                self.program_sky["u_sky_zenith"].value = sky_zenith
                self.program_sky["u_night_factor"].value = night_factor
                self.ctx.disable(moderngl.DEPTH_TEST)
                self.ctx.disable(moderngl.CULL_FACE)
                self.ctx.disable(moderngl.BLEND)
                self.ctx.depth_mask = False
                self.sky_vao.render(mode=moderngl.TRIANGLES)
                self.ctx.depth_mask = True
                self.ctx.enable(moderngl.DEPTH_TEST)
            except Exception as e:
                print(f"Sky render error: {e}")

        # Stars (only visible when night_factor > 0)
        if self.program_stars is not None and self.stars_vao is not None and night_factor > 0.05:
            try:
                self.program_stars["u_mvp"].write(mvp.T.tobytes())
                self.program_stars["u_cam_pos"].value = (float(eye[0]), float(eye[1]), float(eye[2]))
                self.program_stars["u_radius"].value = 500.0
                self.program_stars["u_night_factor"].value = float(night_factor)
                self.ctx.enable(moderngl.BLEND)
                self.ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE)  # additive
                self.ctx.disable(moderngl.DEPTH_TEST)
                self.ctx.depth_mask = False
                self.stars_vao.render(mode=moderngl.POINTS, vertices=self.stars_count)
                self.ctx.depth_mask = True
                self.ctx.enable(moderngl.DEPTH_TEST)
                self.ctx.disable(moderngl.BLEND)
            except Exception as e:
                print(f"Stars render error: {e}")

        # Sun + Moon billboards
        if self.program_celestial is not None and self.celestial_vao is not None:
            self._render_celestial(eye, sun_dir, mvp, camera)
            self.atlas.use(0)

        r = int(max(4, min(12, render_distance_chunks)))
        cam_cx = int(math.floor(eye[0] / 16.0))
        cam_cz = int(math.floor(eye[2] / 16.0))

        self.ctx.enable(moderngl.DEPTH_TEST)
        self.ctx.enable(moderngl.CULL_FACE)
        self.ctx.disable(moderngl.BLEND)
        self.program_block["u_cutout"].value = 0

        # Single pass over chunks to collect visible ones and build meshes
        opaque_draw: List[moderngl.VertexArray] = []
        cutout_draw: List[moderngl.VertexArray] = []
        trans_draw: List[Tuple[float, moderngl.VertexArray]] = []
        shadow_opaque_draw: List[moderngl.VertexArray] = []
        shadow_cutout_draw: List[moderngl.VertexArray] = []

        for key, chunk in world.chunks.items():
            cx, cz = key
            if (cx - cam_cx) * (cx - cam_cx) + (cz - cam_cz) * (cz - cam_cz) > (r + 0.5) * (r + 0.5):
                continue
            mn = (cx * 16.0, 0.0, cz * 16.0)
            mx = (cx * 16.0 + 16.0, 256.0, cz * 16.0 + 16.0)
            if not aabb_visible(mvp, mn, mx):
                continue

            self._ensure_chunk_gl(key, chunk, world)
            gl = self.chunk_gl[key]

            if gl.vao_opaque is not None and gl.count_opaque:
                opaque_draw.append(gl.vao_opaque)
                if gl.shadow_vao_opaque is not None:
                    shadow_opaque_draw.append(gl.shadow_vao_opaque)
            if gl.vao_cutout is not None and gl.count_cutout:
                cutout_draw.append(gl.vao_cutout)
                if gl.shadow_vao_cutout is not None:
                    shadow_cutout_draw.append(gl.shadow_vao_cutout)
            if gl.vao_trans is not None and gl.count_trans:
                cxw = cx * 16.0 + 8.0
                czw = cz * 16.0 + 8.0
                dx = cxw - float(eye[0])
                dz = czw - float(eye[2])
                trans_draw.append((dx * dx + dz * dz, gl.vao_trans))

        # ---- Shadow Pass ----
        shadow_mvp_ortho = None
        if (self.program_shadow is not None and self.shadow_fbo is not None
                and night_factor < 0.95 and (shadow_opaque_draw or shadow_cutout_draw)):
            try:
                fwd = np.array(camera["forward"], dtype="f4")
                center = eye + fwd * 32.0
                sd = np.array(sun_dir, dtype="f4")
                sn = float(np.linalg.norm(sd))
                if sn > 1e-6:
                    sd = sd / sn
                sun_eye = center - sd * 180.0

                shadow_view = look_at(sun_eye, center, np.array([0.0, 1.0, 0.0], dtype="f4"))
                # Orthographic projection covering 128 m around the camera
                left, right_o, bottom, top, near_o, far_o = -96.0, 96.0, -96.0, 96.0, 1.0, 360.0
                shadow_proj = np.zeros((4, 4), dtype="f4")
                shadow_proj[0, 0] = 2.0 / (right_o - left)
                shadow_proj[1, 1] = 2.0 / (top - bottom)
                shadow_proj[2, 2] = -2.0 / (far_o - near_o)
                shadow_proj[0, 3] = -(right_o + left) / (right_o - left)
                shadow_proj[1, 3] = -(top + bottom) / (top - bottom)
                shadow_proj[2, 3] = -(far_o + near_o) / (far_o - near_o)
                shadow_proj[3, 3] = 1.0
                shadow_mvp_ortho = shadow_proj @ shadow_view

                self.shadow_fbo.use()
                self.ctx.viewport = (0, 0, self.shadow_size, self.shadow_size)
                self.ctx.clear(depth=1.0)
                self.ctx.front_face = "ccw"
                # Front-face culling reduces peter-panning
                try:
                    self.ctx.cull_face = "front"
                except Exception:
                    pass
                self.program_shadow["u_mvp"].write(shadow_mvp_ortho.T.tobytes())
                for vao in shadow_opaque_draw:
                    vao.render(mode=moderngl.TRIANGLES)
                for vao in shadow_cutout_draw:
                    vao.render(mode=moderngl.TRIANGLES)
                try:
                    self.ctx.cull_face = "back"
                except Exception:
                    pass
                # Restore rendering target + viewport (bloom scene FBO if enabled)
                if self._bloom_enabled and self._bloom_scene_fbo is not None:
                    self._bloom_scene_fbo.use()
                else:
                    self.ctx.screen.use()
                self.ctx.viewport = (0, 0, self.screen_size[0], self.screen_size[1])
            except Exception as e:
                print(f"Shadow pass error: {e}")
                shadow_mvp_ortho = None

        # Bind shadow uniforms for block shader
        try:
            if shadow_mvp_ortho is not None:
                self.program_block["u_shadow_mvp"].write(shadow_mvp_ortho.T.tobytes())
                self.program_block["u_shadow_enabled"].value = 1
                self.shadow_depth.use(location=1)
            else:
                self.program_block["u_shadow_enabled"].value = 0
                # Identity for u_shadow_mvp to avoid undefined behavior
                self.program_block["u_shadow_mvp"].write(np.eye(4, dtype="f4").T.tobytes())
        except KeyError:
            pass

        for vao in opaque_draw:
            vao.render(mode=moderngl.TRIANGLES)

        self.program_block["u_cutout"].value = 1
        for vao in cutout_draw:
            vao.render(mode=moderngl.TRIANGLES)

        # Clouds: render two layers before translucent (water alpha-blends over them at distance)
        if self.program_cloud is not None and self.cloud_vao is not None:
            try:
                grid = 16.0
                cx = math.floor(float(eye[0]) / grid) * grid
                cz = math.floor(float(eye[2]) / grid) * grid
                half = self.cloud_size * 0.5

                self.ctx.enable(moderngl.BLEND)
                self.ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)
                self.ctx.disable(moderngl.CULL_FACE)
                self.program_cloud["u_mvp"].write(mvp.T.tobytes())
                self.program_cloud["u_time"].value = float(self._elapsed)
                self.program_cloud["u_night_factor"].value = night_factor
                self.program_cloud["u_cam_pos"].value = (float(eye[0]), float(eye[1]), float(eye[2]))

                # Layer 1 — low fluffy clouds (denser, slower-scrolling, denser tex)
                y_low = self.cloud_y
                verts_low = np.array([
                    cx - half, y_low, cz - half,
                    cx + half, y_low, cz - half,
                    cx + half, y_low, cz + half,
                    cx - half, y_low, cz - half,
                    cx + half, y_low, cz + half,
                    cx - half, y_low, cz + half,
                ], dtype="f4")
                self.cloud_vbo.orphan(verts_low.nbytes)
                self.cloud_vbo.write(verts_low.tobytes())
                self.program_cloud["u_uv_scale"].value = 1.0 / 96.0
                self.program_cloud["u_cloud_y"].value = y_low
                try:
                    self.program_cloud["u_scroll_speed"].value = (0.0008, 0.0)
                except KeyError:
                    pass
                self.cloud_tex.use(0)
                self.cloud_vao.render(mode=moderngl.TRIANGLES)

                # Layer 2 — high wispy clouds (different texture, slower drift, larger scale)
                if getattr(self, 'cloud_tex_high', None) is not None:
                    y_high = self.cloud_y_high
                    verts_high = np.array([
                        cx - half, y_high, cz - half,
                        cx + half, y_high, cz - half,
                        cx + half, y_high, cz + half,
                        cx - half, y_high, cz - half,
                        cx + half, y_high, cz + half,
                        cx - half, y_high, cz + half,
                    ], dtype="f4")
                    self.cloud_vbo.orphan(verts_high.nbytes)
                    self.cloud_vbo.write(verts_high.tobytes())
                    self.program_cloud["u_uv_scale"].value = 1.0 / 160.0
                    self.program_cloud["u_cloud_y"].value = y_high
                    try:
                        # Slower drift + small lateral component for variety
                        self.program_cloud["u_scroll_speed"].value = (0.00030, 0.00012)
                    except KeyError:
                        pass
                    self.cloud_tex_high.use(0)
                    self.cloud_vao.render(mode=moderngl.TRIANGLES)

                self.ctx.enable(moderngl.CULL_FACE)
                self.ctx.disable(moderngl.BLEND)
                # Restore atlas binding for translucent chunks below
                self.atlas.use(0)
            except Exception as e:
                print(f"Cloud render error: {e}")

        if trans_draw:
            self.ctx.enable(moderngl.BLEND)
            self.ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)
            self.ctx.depth_mask = False
            self.program_block["u_cutout"].value = 0
            trans_draw.sort(key=lambda t: t[0], reverse=True)
            for _, vao in trans_draw:
                vao.render(mode=moderngl.TRIANGLES)
            self.ctx.depth_mask = True
            self.ctx.disable(moderngl.BLEND)

        # Particles (block break debris) — render before entities/items
        particles = getattr(world, 'particles', None)
        if particles is not None:
            try:
                self.render_particles(particles, camera, mvp, night_factor)
            except Exception as e:
                print(f"Particles render error: {e}")

        entities = getattr(world, 'entities', [])
        if entities:
            self.render_entities(entities, camera, mvp, sun_dir, night_factor, world)

        if selected and getattr(selected, "hit", False):
            self.program_overlay["u_mvp"].write(mvp.T.tobytes())
            self.program_overlay["u_color"].value = (1.0, 1.0, 1.0, 0.65)
            self.program_overlay["u_progress"].value = float(max(0.0, min(1.0, break_progress)))
            self._ensure_overlay(selected.block_pos)
            self.ctx.enable(moderngl.BLEND)
            self.ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)
            self.ctx.wireframe = True
            self.overlay_vao.render(mode=moderngl.TRIANGLES)
            self.ctx.wireframe = False
            self.ctx.disable(moderngl.BLEND)

        # Bloom post-processing passes (after 3D scene, before UI)
        if self._bloom_enabled and self._bloom_scene_fbo is not None:
            try:
                bw, bh = self._bloom_size
                self.ctx.disable(moderngl.DEPTH_TEST)
                self.ctx.disable(moderngl.BLEND)

                # Extract bright pixels into half-res buffer
                self._bloom_extract_fbo.use()
                self.ctx.viewport = (0, 0, bw, bh)
                self.ctx.clear(0.0, 0.0, 0.0, 1.0)
                self._bloom_scene_tex.use(0)
                self._bloom_quad_vao_extract.render(moderngl.TRIANGLES)

                # Horizontal Gaussian blur
                self._bloom_blur_fbo[0].use()
                self.ctx.clear(0.0, 0.0, 0.0, 1.0)
                self._bloom_extract_tex.use(0)
                self._prog_bloom_blur["u_direction"].value = (1.0, 0.0)
                self._prog_bloom_blur["u_texel_size"].value = (1.0 / bw, 1.0 / bh)
                self._bloom_quad_vao_blur.render(moderngl.TRIANGLES)

                # Vertical Gaussian blur
                self._bloom_blur_fbo[1].use()
                self.ctx.clear(0.0, 0.0, 0.0, 1.0)
                self._bloom_blur_tex[0].use(0)
                self._prog_bloom_blur["u_direction"].value = (0.0, 1.0)
                self._prog_bloom_blur["u_texel_size"].value = (1.0 / bw, 1.0 / bh)
                self._bloom_quad_vao_blur.render(moderngl.TRIANGLES)

                # Combine scene + blurred bloom onto default framebuffer
                self.ctx.screen.use()
                self.ctx.viewport = (0, 0, w, h)
                self.ctx.clear(0.0, 0.0, 0.0, 1.0)
                self._bloom_scene_tex.use(0)
                self._bloom_blur_tex[1].use(1)
                self._bloom_quad_vao_combine.render(moderngl.TRIANGLES)

                self.ctx.enable(moderngl.DEPTH_TEST)
            except Exception as e:
                # Self-heal: if the bloom pipeline misbehaves on this GPU, disable
                # it permanently so subsequent frames render directly to the
                # screen instead of staying stuck on a black offscreen buffer.
                print(f"Bloom pass error (disabling bloom): {e}")
                self._bloom_enabled = False
                self.ctx.screen.use()
                self.ctx.viewport = (0, 0, w, h)
                self.ctx.enable(moderngl.DEPTH_TEST)

        # Underwater blue overlay effect
        if self._is_player_underwater(world, camera):
            self.ctx.screen.use()
            self.ctx.viewport = (0, 0, w, h)
            self.ctx.disable(moderngl.DEPTH_TEST)
            self.ctx.enable(moderngl.BLEND)
            self.ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)
            try:
                # Render full-screen blue tint quad
                # Simple full-screen quad vertices (NDC space: -1 to 1)
                quad_verts = np.array([
                    -1.0, -1.0, 0.0,
                    1.0, -1.0, 0.0,
                    1.0, 1.0, 0.0,
                    -1.0, 1.0, 0.0,
                ], dtype='f4')
                quad_indices = np.array([0, 1, 2, 0, 2, 3], dtype='u4')

                if not hasattr(self, '_underwater_prog'):
                    vert_src = """
#version 330
in vec3 in_pos;
void main() { gl_Position = vec4(in_pos, 1.0); }
"""
                    frag_src = """
#version 330
out vec4 out_color;
void main() { out_color = vec4(0.0, 0.25, 0.75, 0.35); }
"""
                    self._underwater_prog = self.ctx.program(vertex_shader=vert_src, fragment_shader=frag_src)

                if not hasattr(self, '_underwater_vao'):
                    vbo = self.ctx.buffer(quad_verts)
                    ibo = self.ctx.buffer(quad_indices)
                    self._underwater_vao = self.ctx.vertex_array(
                        self._underwater_prog, [(vbo, '3f', 'in_pos')], ibo
                    )

                self._underwater_vao.render(mode=moderngl.TRIANGLES)
            except Exception as e:
                print(f"Underwater effect error: {e}")
            self.ctx.disable(moderngl.BLEND)
            self.ctx.enable(moderngl.DEPTH_TEST)

        if self.ui_tex is not None:
            self.upload_ui(ui_rgba)
            self.ctx.disable(moderngl.DEPTH_TEST)
            self.ctx.enable(moderngl.BLEND)
            self.ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)
            self.ui_tex.use(0)
            self.ui_vao.render(mode=moderngl.TRIANGLES)
            self.ctx.disable(moderngl.BLEND)
            self.ctx.enable(moderngl.DEPTH_TEST)
