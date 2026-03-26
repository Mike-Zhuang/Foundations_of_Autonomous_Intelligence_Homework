import argparse
from pathlib import Path

import matplotlib.animation as animation
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.path import Path as MplPath

try:
	import cv2  # Optional dependency for obstacle image import.
except ImportError:
	cv2 = None


# D2Q9 lattice directions: 0 rest, 1 E, 2 N, 3 W, 4 S, 5 NE, 6 NW, 7 SW, 8 SE.
CX = np.array([0, 1, 0, -1, 0, 1, -1, -1, 1], dtype=np.int32)
CY = np.array([0, 0, 1, 0, -1, 1, 1, -1, -1], dtype=np.int32)
W = np.array([4 / 9] + [1 / 9] * 4 + [1 / 36] * 4, dtype=np.float64)
OPP = np.array([0, 3, 4, 1, 2, 7, 8, 5, 6], dtype=np.int32)


class LBMKarmanSimulation:
	def __init__(
		self,
		ny=200,
		nx=800,#宽 800 列、高 200 行
		tau=0.56,
		u_in=0.08,
		steps_per_frame=6,
		obstacle_mode="circle",
		obstacle_image=None,
		periodic_y=True,
	):
		self.ny = ny
		self.nx = nx
		self.tau = tau
		self.u_in = u_in
		self.steps_per_frame = steps_per_frame
		self.periodic_y = periodic_y

		self.paused = False
		self.brush_radius = 6
		self.draw_mode = True
		self.is_dragging = False
		self.frame_count = 0
		self.fig = None
		self.ax1 = None
		self.ax2 = None
		self.ax3 = None
		self.im_speed = None
		self.im_vorticity = None
		self.im_obstacle1 = None
		self.im_obstacle2 = None
		self.im_core1 = None
		self.im_core2 = None
		self.info_ax = None
		self.status_text = None
		self.ani = None
		self.display_mode = "vorticity"
		self.vorticity_dynamic_scale = True
		self.show_vortex_cores = True
		self.enable_initial_perturbation = True
		self.perturbation_strength = 0.015
		self.maze_flow_score = np.zeros((ny, nx), dtype=np.float64)
		self.maze_score_alpha = 0.995
		self.maze_path_mask = np.zeros((ny, nx), dtype=bool)
		self.maze_path_revealed = np.zeros((ny, nx), dtype=bool)
		self.maze_path_overlay = None  # RGBA overlay for path highlight
		self.im_path1 = None
		self.im_path2 = None
		self.q_criterion = np.zeros((ny, nx), dtype=np.float64)

		self.fx_mem = 0.0
		self.fy_mem = 0.0
		self.fx_pressure = 0.0
		self.fy_pressure = 0.0
		self.gamma = 0.0
		self.lift_gamma = 0.0
		self.cd_mem = 0.0
		self.cl_mem = 0.0
		self.cd_pressure = 0.0
		self.cl_pressure = 0.0
		self.cl_gamma = 0.0
		self.fx_mem_accum = 0.0
		self.fy_mem_accum = 0.0
		self.mem_samples = 0

		self.history_max_points = 900
		self.time_history = []
		self.cl_mem_history = []
		self.cl_pressure_history = []
		self.cl_gamma_history = []
		self.line_cl_mem = None
		self.line_cl_pressure = None
		self.line_cl_gamma = None

		self.cx_3d = CX[:, None, None]
		self.cy_3d = CY[:, None, None]

		self.presets = {
			"1": {"tau": 0.9, "u_in": 0.04, "label": "Preset 1: Low Re (laminar)"},
			"2": {"tau": 0.72, "u_in": 0.06, "label": "Preset 2: Medium Re"},
			"3": {"tau": 0.58, "u_in": 0.08, "label": "Preset 3: Karman street"},
			"4": {"tau": 0.53, "u_in": 0.1, "label": "Preset 4: High Re (unstable)"},
		}
		self.last_action = "Initialized"

		self.obstacle = np.zeros((ny, nx), dtype=bool)
		if obstacle_mode == "image" and obstacle_image:
			loaded = self.load_obstacle_from_image(obstacle_image)
			if loaded:
				self.last_action = f"Obstacle loaded: {Path(obstacle_image).name}"
				# Auto-solve maze when loaded via command line.
				is_maze = self.solve_maze_bfs()
				if is_maze:
					self.display_mode = "maze"
					self.last_action += " | Path found!"
			else:
				self.set_circle_obstacle()
				self.last_action = "Image load failed, fallback to circle obstacle"
		else:
			self.set_circle_obstacle()

		# Maze images start from rest so fluid propagates visibly.
		self.reset_flow(quiescent=(obstacle_mode == "image"))

	def set_circle_obstacle(self):
		self.obstacle.fill(False)
		cy = self.ny // 2
		cx = self.nx // 5
		radius = max(8, self.ny // 10)
		y, x = np.ogrid[: self.ny, : self.nx]
		self.obstacle = (x - cx) ** 2 + (y - cy) ** 2 <= radius**2

	def set_square_obstacle(self):
		"""Square bluff body centred at the canonical position."""
		self.obstacle.fill(False)
		cy = self.ny // 2
		cx = self.nx // 5
		half = max(8, self.ny // 10)
		y0, y1 = cy - half, cy + half
		x0, x1 = cx - half, cx + half
		self.obstacle[max(y0, 0):min(y1 + 1, self.ny),
					  max(x0, 0):min(x1 + 1, self.nx)] = True

	def set_ellipse_obstacle(self):
		"""Ellipse with major axis perpendicular to the flow (aspect ratio ~2:1)."""
		self.obstacle.fill(False)
		cy = self.ny // 2
		cx = self.nx // 5
		a = max(5, self.ny // 16)   # semi-axis along flow (shorter)
		b = max(8, self.ny // 10)   # semi-axis perpendicular to flow (longer)
		y, x = np.ogrid[:self.ny, :self.nx]
		self.obstacle = ((x - cx) / max(a, 1)) ** 2 + ((y - cy) / max(b, 1)) ** 2 <= 1.0

	def set_triangle_obstacle(self):
		"""Equilateral triangle with apex pointing upstream (half-plane intersection)."""
		self.obstacle.fill(False)
		cy = self.ny // 2
		cx = self.nx // 5
		half = max(8, self.ny // 10)
		y, x = np.ogrid[:self.ny, :self.nx]
		t = np.clip(x - (cx - half), 0, None) / max(2.0 * half, 1)
		self.obstacle = (x >= cx - half) & (x <= cx + half) & (np.abs(y - cy) <= half * t)

	def set_plate_obstacle(self):
		"""Thin flat plate perpendicular to the flow."""
		self.obstacle.fill(False)
		cy = self.ny // 2
		cx = self.nx // 5
		half_h = max(8, self.ny // 10)
		half_w = max(1, half_h // 8)
		y0 = max(0, cy - half_h)
		y1 = min(self.ny, cy + half_h + 1)
		x0 = max(0, cx - half_w)
		x1 = min(self.nx, cx + half_w + 1)
		self.obstacle[y0:y1, x0:x1] = True

	def set_diamond_obstacle(self):
		"""Diamond / rhombus (L1-norm ball)."""
		self.obstacle.fill(False)
		cy = self.ny // 2
		cx = self.nx // 5
		half = max(8, self.ny // 10)
		y, x = np.ogrid[:self.ny, :self.nx]
		self.obstacle = (np.abs(x - cx) + np.abs(y - cy)) <= half

	def set_naca0012_obstacle(self, aoa_deg=8.0):
		"""Create a NACA 0012 airfoil obstacle with optional angle of attack."""
		self.obstacle.fill(False)

		thickness = 0.12
		chord_px = max(50, self.nx // 4)
		x_start = self.nx // 5
		y_mid = self.ny // 2
		n_pts = max(250, chord_px * 2)

		x = np.linspace(0.0, 1.0, n_pts)
		yt = 5.0 * thickness * (
			0.2969 * np.sqrt(np.maximum(x, 1e-12))
			- 0.1260 * x
			- 0.3516 * x**2
			+ 0.2843 * x**3
			- 0.1015 * x**4
		)

		x_upper = x
		y_upper = yt
		x_lower = x[::-1]
		y_lower = -yt[::-1]

		x_poly = np.concatenate([x_upper, x_lower]) * chord_px + x_start
		y_poly = np.concatenate([y_upper, y_lower]) * chord_px + y_mid

		# Rotate around quarter chord to introduce lift-generating asymmetry.
		pivot_x = x_start + 0.25 * chord_px
		pivot_y = y_mid
		theta = np.deg2rad(aoa_deg)
		x_rel = x_poly - pivot_x
		y_rel = y_poly - pivot_y
		x_rot = x_rel * np.cos(theta) - y_rel * np.sin(theta) + pivot_x
		y_rot = x_rel * np.sin(theta) + y_rel * np.cos(theta) + pivot_y
		polygon = np.column_stack([x_rot, y_rot])

		xx, yy = np.meshgrid(np.arange(self.nx), np.arange(self.ny))
		points = np.column_stack([xx.ravel() + 0.5, yy.ravel() + 0.5])
		mask = MplPath(polygon, closed=True).contains_points(points).reshape(self.ny, self.nx)

		self.obstacle[mask] = True
		# Keep inlet region open to avoid fully blocked domain.
		self.obstacle[:, :3] = False
		return np.any(self.obstacle)

	def load_obstacle_from_image(self, image_path):
		if cv2 is None:
			return False
		img = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
		if img is None:
			return False

		# Keep original aspect ratio: fit image into domain and pad the rest.
		h, w = img.shape[:2]
		if h == 0 or w == 0:
			return False
		scale = min(self.nx / float(w), self.ny / float(h))
		new_w = max(1, int(round(w * scale)))
		new_h = max(1, int(round(h * scale)))

		resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_NEAREST)
		canvas = np.full((self.ny, self.nx), 255, dtype=np.uint8)
		y0 = (self.ny - new_h) // 2
		x0 = (self.nx - new_w) // 2
		canvas[y0 : y0 + new_h, x0 : x0 + new_w] = resized

		_, binary = cv2.threshold(canvas, 127, 255, cv2.THRESH_BINARY)
		self.obstacle = binary < 127
		# Keep inlet region open to avoid fully blocked domain.
		self.obstacle[:, :3] = False
		return np.any(self.obstacle)

	def equilibria(self, rho, ux, uy):
		cu = 3.0 * (self.cx_3d * ux[None, :, :] + self.cy_3d * uy[None, :, :])
		u2 = ux**2 + uy**2
		return W[:, None, None] * rho[None, :, :] * (1.0 + cu + 0.5 * cu**2 - 1.5 * u2[None, :, :])

	def reset_flow(self, quiescent=False):
		rho0 = np.ones((self.ny, self.nx), dtype=np.float64)
		if quiescent:
			# Start from rest everywhere — fluid must propagate in from the inlet.
			ux0 = np.zeros((self.ny, self.nx), dtype=np.float64)
		else:
			ux0 = np.full((self.ny, self.nx), self.u_in, dtype=np.float64)
		uy0 = np.zeros((self.ny, self.nx), dtype=np.float64)
		if (not quiescent) and self.enable_initial_perturbation:
			self.apply_initial_perturbation(ux0, uy0)

		ux0[self.obstacle] = 0.0
		uy0[self.obstacle] = 0.0

		self.F = self.equilibria(rho0, ux0, uy0)
		self.rho = rho0
		self.ux = ux0
		self.uy = uy0
		self.vorticity = np.zeros_like(rho0)
		self.maze_flow_score.fill(0.0)
		self.maze_path_revealed.fill(False)
		self.frame_count = 0
		self.fx_mem = 0.0
		self.fy_mem = 0.0
		self.fx_pressure = 0.0
		self.fy_pressure = 0.0
		self.gamma = 0.0
		self.lift_gamma = 0.0
		self.cd_mem = 0.0
		self.cl_mem = 0.0
		self.cd_pressure = 0.0
		self.cl_pressure = 0.0
		self.cl_gamma = 0.0
		self.fx_mem_accum = 0.0
		self.fy_mem_accum = 0.0
		self.mem_samples = 0
		self.time_history.clear()
		self.cl_mem_history.clear()
		self.cl_pressure_history.clear()
		self.cl_gamma_history.clear()

	def apply_initial_perturbation(self, ux, uy):
		"""Inject a tiny antisymmetric disturbance to trigger vortex shedding earlier."""
		ys, xs = np.where(self.obstacle)
		if ys.size == 0:
			return

		y_mid = 0.5 * (ys.min() + ys.max())
		x_trailing = int(xs.max()) + 2
		char_h = max(8, int(ys.max() - ys.min() + 1))
		sigma_x = max(6.0, 0.8 * char_h)
		sigma_y = max(6.0, 0.5 * char_h)

		x_grid = np.arange(self.nx, dtype=np.float64)[None, :]
		y_grid = np.arange(self.ny, dtype=np.float64)[:, None]

		envelope = np.exp(
			-((x_grid - x_trailing) ** 2) / (2.0 * sigma_x**2)
			-((y_grid - y_mid) ** 2) / (2.0 * sigma_y**2)
		)
		antisym = np.tanh((y_grid - y_mid) / max(1.0, 0.15 * char_h))
		uy += self.perturbation_strength * self.u_in * envelope * antisym
		uy[self.obstacle] = 0.0

	def obstacle_characteristic_length(self):
		ys, _xs = np.where(self.obstacle)
		if ys.size == 0:
			return float(max(10, self.ny // 10))
		return float(max(4, ys.max() - ys.min() + 1))

	def _reference_density(self):
		if self.rho is None:
			return 1.0
		return float(max(1e-8, np.mean(self.rho[:, 0])))

	def _force_to_coeff(self, fx, fy):
		rho_ref = self._reference_density()
		d = self.obstacle_characteristic_length()
		dyn = 0.5 * rho_ref * self.u_in**2 * max(d, 1.0)
		if dyn <= 1e-12:
			return 0.0, 0.0
		cd = fx / dyn
		cl = fy / dyn
		return float(cd), float(cl)

	def estimate_momentum_exchange_force(self):
		"""Approximate force from fluid links that point into obstacle cells."""
		if not np.any(self.obstacle):
			return 0.0, 0.0

		fx = 0.0
		fy = 0.0
		fluid = ~self.obstacle
		for i in range(1, 9):
			neighbor_is_obstacle = np.roll(self.obstacle, shift=(-CY[i], -CX[i]), axis=(0, 1))
			mask = fluid & neighbor_is_obstacle
			mask[:, 0] = False
			mask[:, -1] = False
			if not self.periodic_y:
				mask[0, :] = False
				mask[-1, :] = False
			if np.any(mask):
				fi = self.F[i, mask]
				fx += 2.0 * CX[i] * np.sum(fi)
				fy += 2.0 * CY[i] * np.sum(fi)
		return float(fx), float(fy)

	def estimate_pressure_force(self):
		"""Approximate pressure-integral force using local boundary normals."""
		if not np.any(self.obstacle):
			return 0.0, 0.0

		obs_f = self.obstacle.astype(np.float64)
		gx = np.gradient(obs_f, axis=1)
		gy = np.gradient(obs_f, axis=0)
		grad_mag = np.sqrt(gx**2 + gy**2)
		boundary = self.obstacle & (grad_mag > 1e-10)
		if not np.any(boundary):
			return 0.0, 0.0

		nx = -gx / (grad_mag + 1e-12)
		ny = -gy / (grad_mag + 1e-12)
		pressure = self.rho / 3.0
		weight = grad_mag

		fx = -np.sum(pressure[boundary] * nx[boundary] * weight[boundary])
		fy = -np.sum(pressure[boundary] * ny[boundary] * weight[boundary])
		return float(fx), float(fy)

	def estimate_circulation_lift(self, margin=8):
		"""Estimate lift by Kutta-Joukowski from circulation around obstacle."""
		ys, xs = np.where(self.obstacle)
		if ys.size == 0:
			return 0.0, 0.0

		x0 = max(1, int(xs.min()) - margin)
		x1 = min(self.nx - 2, int(xs.max()) + margin)
		y0 = max(1, int(ys.min()) - margin)
		y1 = min(self.ny - 2, int(ys.max()) + margin)
		if x1 <= x0 or y1 <= y0:
			return 0.0, 0.0

		top = np.sum(self.ux[y0, x0:x1])
		right = np.sum(self.uy[y0:y1, x1])
		bottom = -np.sum(self.ux[y1, x0:x1])
		left = -np.sum(self.uy[y0:y1, x0])
		gamma = float(top + right + bottom + left)
		lift = self._reference_density() * self.u_in * gamma
		return gamma, float(lift)

	def set_right_panel_mode(self, mode):
		self.display_mode = mode
		if self.im_vorticity is None or self.ax2 is None:
			return
		if mode == "maze":
			self.im_vorticity.set_cmap("gray")
			self.im_vorticity.set_clim(0.0, 1.0)
			if np.any(self.maze_path_mask):
				self.ax2.set_title("Maze Solution (BFS Shortest Path)", color="#00ff33")
			else:
				self.ax2.set_title("Maze (solving...)", color="yellow")
		else:
			self.im_vorticity.set_cmap("seismic")
			self.im_vorticity.set_clim(-0.15, 0.15)
			self.ax2.set_title("Vorticity (Karman Vortex Street)", color="white")

	def solve_maze_bfs(self):
		"""BFS shortest path through the maze from left openings to right openings.

		Only considers entrance/exit cells *within* the obstacle's vertical extent,
		so the path cannot cheat by going around the maze through open padding."""
		from collections import deque

		self.maze_path_mask.fill(False)
		ny, nx = self.ny, self.nx
		free = ~self.obstacle  # True = passable

		# --- Determine the maze bounding box so we restrict entry/exit to it ---
		obs_ys, obs_xs = np.where(self.obstacle)
		if obs_ys.size == 0:
			return False
		y_min, y_max = int(obs_ys.min()), int(obs_ys.max())
		x_min, x_max = int(obs_xs.min()), int(obs_xs.max())

		# parent map: -1 = unvisited
		parent = np.full((ny, nx, 2), -1, dtype=np.int32)
		queue = deque()

		# Seed: free cells on the LEFT side, only within the obstacle vertical span.
		for y in range(y_min, y_max + 1):
			for xs in range(max(0, x_min - 3), x_min + 2):
				if 0 <= xs < nx and free[y, xs] and parent[y, xs, 0] == -1:
					parent[y, xs] = [y, xs]  # self-parent = start marker
					queue.append((y, xs))

		# 4-connected neighbours
		dirs = [(-1, 0), (1, 0), (0, -1), (0, 1)]
		target = None

		while queue:
			cy, cx = queue.popleft()
			# Reached right side of maze?
			if cx >= x_max - 1:
				target = (cy, cx)
				break
			for dy, dx in dirs:
				ny2, nx2 = cy + dy, cx + dx
				if 0 <= ny2 < ny and 0 <= nx2 < nx and free[ny2, nx2] and parent[ny2, nx2, 0] == -1:
					parent[ny2, nx2] = [cy, cx]
					queue.append((ny2, nx2))

		if target is None:
			return False

		# Trace back from target to start.
		y, x = target
		while not (parent[y, x, 0] == y and parent[y, x, 1] == x):
			self.maze_path_mask[y, x] = True
			py, px = parent[y, x]
			y, x = int(py), int(px)
		self.maze_path_mask[y, x] = True

		# Thicken path by 1 pixel for visibility (avoid np.roll wraparound).
		thick = self.maze_path_mask.copy()
		for dy in (-1, 0, 1):
			for dx in (-1, 0, 1):
				if dy == 0 and dx == 0:
					continue
				shifted = np.zeros_like(self.maze_path_mask)
				sy = slice(max(0, dy), min(ny, ny + dy))
				dy_dst = slice(max(0, -dy), min(ny, ny - dy))
				sx = slice(max(0, dx), min(nx, nx + dx))
				dx_dst = slice(max(0, -dx), min(nx, nx - dx))
				shifted[dy_dst, dx_dst] = self.maze_path_mask[sy, sx]
				thick |= shifted
		thick &= free
		self.maze_path_mask = thick
		thick &= free
		self.maze_path_mask = thick

		# Don't show path yet — it will be revealed progressively by the fluid.
		self.maze_path_revealed.fill(False)
		self._build_path_overlay(reveal_mask=self.maze_path_revealed)
		return True

	def _build_path_overlay(self, reveal_mask=None):
		"""Build an RGBA overlay image highlighting the solved path.
		If reveal_mask is given, only show path cells that are also revealed."""
		overlay = np.zeros((self.ny, self.nx, 4), dtype=np.float32)
		if reveal_mask is not None:
			show = self.maze_path_mask & reveal_mask
		else:
			show = self.maze_path_mask
		overlay[show] = [0.0, 1.0, 0.2, 0.7]
		self.maze_path_overlay = overlay
		if self.im_path1 is not None:
			self.im_path1.set_array(overlay)
		if self.im_path2 is not None:
			self.im_path2.set_array(overlay)

	def update_maze_flow_score(self):
		speed = np.sqrt(self.ux**2 + self.uy**2)
		speed[self.obstacle] = 0.0
		self.maze_flow_score = self.maze_score_alpha * self.maze_flow_score + (1.0 - self.maze_score_alpha) * speed

	def apply_inlet(self):
		ux = np.full(self.ny, self.u_in)
		uy = np.zeros(self.ny)

		# Zou-He velocity boundary on left side.
		rho = (
			self.F[0, :, 0]
			+ self.F[2, :, 0]
			+ self.F[4, :, 0]
			+ 2.0 * (self.F[3, :, 0] + self.F[6, :, 0] + self.F[7, :, 0])
		) / (1.0 - ux)

		self.F[1, :, 0] = self.F[3, :, 0] + (2.0 / 3.0) * rho * ux
		self.F[5, :, 0] = (
			self.F[7, :, 0]
			+ 0.5 * (self.F[4, :, 0] - self.F[2, :, 0])
			+ (1.0 / 6.0) * rho * ux
		)
		self.F[8, :, 0] = (
			self.F[6, :, 0]
			+ 0.5 * (self.F[2, :, 0] - self.F[4, :, 0])
			+ (1.0 / 6.0) * rho * ux
		)

		blocked = self.obstacle[:, 0]
		if np.any(blocked):
			self.F[:, blocked, 0] = 0.0
			self.F[0, blocked, 0] = 1.0

	def apply_outlet(self):
		# Simple zero-gradient outlet.
		self.F[:, :, -1] = self.F[:, :, -2]

	def apply_non_periodic_y(self):
		# Bounce at top and bottom for non-periodic setting.
		top = 0
		bottom = self.ny - 1

		self.F[2, top, :] = self.F[4, top, :]
		self.F[5, top, :] = self.F[7, top, :]
		self.F[6, top, :] = self.F[8, top, :]

		self.F[4, bottom, :] = self.F[2, bottom, :]
		self.F[7, bottom, :] = self.F[5, bottom, :]
		self.F[8, bottom, :] = self.F[6, bottom, :]

	def compute_macroscopic(self):
		self.rho = np.sum(self.F, axis=0)
		self.rho = np.maximum(self.rho, 1e-12)
		self.ux = np.sum(self.F * self.cx_3d, axis=0) / self.rho
		self.uy = np.sum(self.F * self.cy_3d, axis=0) / self.rho
		self.ux[self.obstacle] = 0.0
		self.uy[self.obstacle] = 0.0

	def compute_vorticity(self):
		duy_dx = np.gradient(self.uy, axis=1)
		dux_dy = np.gradient(self.ux, axis=0)
		self.vorticity = duy_dx - dux_dy

	def compute_q_criterion(self):
		dux_dx = np.gradient(self.ux, axis=1)
		dux_dy = np.gradient(self.ux, axis=0)
		duy_dx = np.gradient(self.uy, axis=1)
		duy_dy = np.gradient(self.uy, axis=0)

		oxy = 0.5 * (duy_dx - dux_dy)
		sxx = dux_dx
		syy = duy_dy
		sxy = 0.5 * (dux_dy + duy_dx)

		s_norm_sq = sxx**2 + syy**2 + 2.0 * sxy**2
		self.q_criterion = oxy**2 - 0.5 * s_norm_sq
		self.q_criterion[self.obstacle] = -np.inf

	def step(self):
		self.compute_macroscopic()

		feq = self.equilibria(self.rho, self.ux, self.uy)
		self.F += -(self.F - feq) / self.tau

		fx_mem, fy_mem = self.estimate_momentum_exchange_force()
		self.fx_mem_accum += fx_mem
		self.fy_mem_accum += fy_mem
		self.mem_samples += 1

		# Bounce-back on obstacle (local CA wall rule).
		for i in range(9):
			self.F[i, self.obstacle] = self.F[OPP[i], self.obstacle]

		# Streaming: move each particle population to neighboring cell.
		for i in range(9):
			self.F[i] = np.roll(self.F[i], shift=(CY[i], CX[i]), axis=(0, 1))

		if not self.periodic_y:
			self.apply_non_periodic_y()
		self.apply_inlet()
		self.apply_outlet()

		self.F = np.maximum(self.F, 0.0)

	def add_obstacle_disk(self, x, y, radius, value=True):
		yy, xx = np.ogrid[: self.ny, : self.nx]
		disk = (xx - x) ** 2 + (yy - y) ** 2 <= radius**2
		if value:
			self.obstacle[disk] = True
		else:
			self.obstacle[disk] = False
		self.obstacle[:, :3] = False
		self.last_action = f"Obstacle {'added' if value else 'removed'} at ({x}, {y})"

	def on_mouse_press(self, event):
		if event.inaxes not in (self.ax1, self.ax2):
			return
		if event.xdata is None or event.ydata is None:
			return
		self.is_dragging = True
		x = int(event.xdata)
		y = int(event.ydata)
		self.add_obstacle_disk(x, y, self.brush_radius, value=self.draw_mode)

	def on_mouse_release(self, _event):
		self.is_dragging = False

	def on_mouse_move(self, event):
		if not self.is_dragging:
			return
		if event.inaxes not in (self.ax1, self.ax2):
			return
		if event.xdata is None or event.ydata is None:
			return
		x = int(event.xdata)
		y = int(event.ydata)
		self.add_obstacle_disk(x, y, self.brush_radius, value=self.draw_mode)

	def _clear_maze_path(self):
		"""Clear maze path data and overlay."""
		self.maze_path_mask.fill(False)
		self.maze_path_revealed.fill(False)
		self._build_path_overlay(reveal_mask=self.maze_path_revealed)

	def set_preset(self, key):
		if key not in self.presets:
			return
		p = self.presets[key]
		self.tau = p["tau"]
		self.u_in = p["u_in"]
		self._clear_maze_path()
		self.set_right_panel_mode("vorticity")
		self.reset_flow()
		self.last_action = p["label"]

	def on_key_press(self, event):
		if event.key is None:
			return
		key = event.key.lower()

		if key == " ":
			self.paused = not self.paused
			self.last_action = "Paused" if self.paused else "Running"
		elif key == "r":
			self._clear_maze_path()
			self.reset_flow()
			self.last_action = "Flow reset"
		elif key == "c":
			self.obstacle.fill(False)
			self._clear_maze_path()
			self.set_right_panel_mode("vorticity")
			self.reset_flow()
			self.last_action = "Obstacle cleared"
		elif key == "d":
			self.draw_mode = True
			self.last_action = "Draw mode: add obstacle"
		elif key == "e":
			self.draw_mode = False
			self.last_action = "Erase mode: remove obstacle"
		elif key in {"+", "="}:
			self.brush_radius = min(40, self.brush_radius + 1)
			self.last_action = f"Brush radius: {self.brush_radius}"
		elif key == "-":
			self.brush_radius = max(1, self.brush_radius - 1)
			self.last_action = f"Brush radius: {self.brush_radius}"
		elif key == "up":
			self.tau = min(1.8, self.tau + 0.01)
			self.last_action = f"tau={self.tau:.3f}"
		elif key == "down":
			self.tau = max(0.51, self.tau - 0.01)
			self.last_action = f"tau={self.tau:.3f}"
		elif key == "right":
			self.u_in = min(0.2, self.u_in + 0.005)
			self.last_action = f"u_in={self.u_in:.3f}"
		elif key == "left":
			self.u_in = max(0.01, self.u_in - 0.005)
			self.last_action = f"u_in={self.u_in:.3f}"
		elif key == "s":
			if self.fig is not None:
				out_path = Path.cwd() / f"snapshot_{self.frame_count:06d}.png"
				self.fig.savefig(out_path, dpi=180)
				self.last_action = f"Snapshot saved: {out_path.name}"
		elif key == "i":
			default_img = Path.cwd() / "obstacle.png"
			if self.load_obstacle_from_image(default_img):
				self.tau = max(self.tau, 0.62)
				self.u_in = min(max(self.u_in, 0.07), 0.12)
				# Start from rest so fluid visibly propagates through the maze.
				self.reset_flow(quiescent=True)
				# Auto-solve the maze and display path.
				found = self.solve_maze_bfs()
				self.set_right_panel_mode("maze")
				if found:
					self.last_action = f"Maze loaded & solved! Path shown in green"
				else:
					self.last_action = f"Maze loaded but no path found (left→right)"
			else:
				self.last_action = "Load failed: put obstacle.png in current folder"
		elif key == "m":
			if self.display_mode == "maze":
				self.set_right_panel_mode("vorticity")
				self.last_action = "Display mode: vorticity"
			else:
				self.set_right_panel_mode("maze")
				self.last_action = "Display mode: maze throughflow"
		elif key == "n":
			# Tuned defaults for visible lift-like contrast near the airfoil.
			self.tau = 0.58
			self.u_in = max(self.u_in, 0.09)
			if self.set_naca0012_obstacle(aoa_deg=8.0):
				self._clear_maze_path()
				self.reset_flow()
				self.set_right_panel_mode("vorticity")
				self.last_action = "Obstacle loaded: NACA 0012 (AoA=8deg, lift demo)"
			else:
				self.last_action = "NACA load failed"
		elif key == "k":
			self.tau = 0.58
			self.u_in = 0.09
			self.set_circle_obstacle()
			self._clear_maze_path()
			self.set_right_panel_mode("vorticity")
			self.reset_flow(quiescent=False)
			for _ in range(220):
				self.step()
			self.compute_macroscopic()
			self.compute_vorticity()
			self.last_action = "Karman demo preset (circle + warmup + perturbation)"
		elif key == "p":
			self.enable_initial_perturbation = not self.enable_initial_perturbation
			state = "on" if self.enable_initial_perturbation else "off"
			self.last_action = f"Initial perturbation: {state}"
		elif key == "v":
			self.show_vortex_cores = not self.show_vortex_cores
			state = "on" if self.show_vortex_cores else "off"
			self.last_action = f"Vortex-core overlay: {state}"
		elif key == "a":
			self.vorticity_dynamic_scale = not self.vorticity_dynamic_scale
			state = "dynamic" if self.vorticity_dynamic_scale else "fixed"
			self.last_action = f"Vorticity color scale: {state}"
		elif key == "5":
			self.set_square_obstacle()
			self._clear_maze_path()
			self.set_right_panel_mode("vorticity")
			self.reset_flow()
			self.last_action = "Obstacle: Square bluff body"
		elif key == "6":
			self.set_ellipse_obstacle()
			self._clear_maze_path()
			self.set_right_panel_mode("vorticity")
			self.reset_flow()
			self.last_action = "Obstacle: Ellipse (major axis perpendicular to flow)"
		elif key == "7":
			self.set_triangle_obstacle()
			self._clear_maze_path()
			self.set_right_panel_mode("vorticity")
			self.reset_flow()
			self.last_action = "Obstacle: Triangle (apex upstream)"
		elif key == "8":
			self.set_plate_obstacle()
			self._clear_maze_path()
			self.set_right_panel_mode("vorticity")
			self.reset_flow()
			self.last_action = "Obstacle: Flat plate (perpendicular to flow)"
		elif key == "9":
			self.set_diamond_obstacle()
			self._clear_maze_path()
			self.set_right_panel_mode("vorticity")
			self.reset_flow()
			self.last_action = "Obstacle: Diamond (rotated square)"
		elif key in self.presets:
			self.set_preset(key)

	def reynolds_number(self):
		# Characteristic length based on obstacle vertical size.
		d = self.obstacle_characteristic_length()
		nu = (self.tau - 0.5) / 3.0
		return self.u_in * d / max(nu, 1e-8)

	def update(self, _frame):
		if not self.paused:
			for _ in range(self.steps_per_frame):
				self.step()
			self.frame_count += self.steps_per_frame

		self.compute_macroscopic()
		self.compute_vorticity()
		self.compute_q_criterion()

		if self.mem_samples > 0:
			self.fx_mem = self.fx_mem_accum / self.mem_samples
			self.fy_mem = self.fy_mem_accum / self.mem_samples
			self.fx_mem_accum = 0.0
			self.fy_mem_accum = 0.0
			self.mem_samples = 0

		self.fx_pressure, self.fy_pressure = self.estimate_pressure_force()
		self.gamma, self.lift_gamma = self.estimate_circulation_lift()
		self.cd_mem, self.cl_mem = self._force_to_coeff(self.fx_mem, self.fy_mem)
		self.cd_pressure, self.cl_pressure = self._force_to_coeff(self.fx_pressure, self.fy_pressure)
		_ignored_cd, self.cl_gamma = self._force_to_coeff(0.0, self.lift_gamma)

		self.time_history.append(self.frame_count)
		self.cl_mem_history.append(self.cl_mem)
		self.cl_pressure_history.append(self.cl_pressure)
		self.cl_gamma_history.append(self.cl_gamma)
		if len(self.time_history) > self.history_max_points:
			self.time_history.pop(0)
			self.cl_mem_history.pop(0)
			self.cl_pressure_history.pop(0)
			self.cl_gamma_history.pop(0)

		if self.line_cl_mem is not None:
			xs = np.arange(len(self.time_history), dtype=np.float64)
			self.line_cl_mem.set_data(xs, np.asarray(self.cl_mem_history))
			self.line_cl_pressure.set_data(xs, np.asarray(self.cl_pressure_history))
			self.line_cl_gamma.set_data(xs, np.asarray(self.cl_gamma_history))

		speed = np.sqrt(self.ux**2 + self.uy**2)
		non_obstacle_speed = speed[~self.obstacle]
		dyn_vmax = max(self.u_in * 1.4, 0.1)
		if non_obstacle_speed.size > 0:
			dyn_vmax = np.percentile(non_obstacle_speed, 99.5)
			dyn_vmax = max(dyn_vmax, self.u_in * 1.4, 0.1)

		self.im_speed.set_array(speed)
		self.im_speed.set_clim(0.0, dyn_vmax)
		self.ax1.set_title("Velocity Magnitude", color="white")

		if self.display_mode == "maze":
			# Right panel: show obstacle layout in gray, path overlay drawn separately.
			maze_bg = np.ones((self.ny, self.nx), dtype=np.float64)
			maze_bg[self.obstacle] = 0.0
			self.im_vorticity.set_array(maze_bg)
			self.im_vorticity.set_clim(0.0, 1.0)
		else:
			self.im_vorticity.set_array(self.vorticity)
			if self.vorticity_dynamic_scale:
				vort_vals = np.abs(self.vorticity[~self.obstacle])
				if vort_vals.size > 0:
					vlim = max(0.03, float(np.percentile(vort_vals, 99.0)))
					self.im_vorticity.set_clim(-vlim, vlim)

		overlay = np.zeros((self.ny, self.nx, 4), dtype=np.float32)
		overlay[self.obstacle] = [1.0, 1.0, 1.0, 0.95]
		self.im_obstacle1.set_array(overlay)
		self.im_obstacle2.set_array(overlay)

		core_overlay = np.zeros((self.ny, self.nx, 4), dtype=np.float32)
		if self.show_vortex_cores and self.display_mode != "maze":
			q_vals = self.q_criterion[~self.obstacle]
			if q_vals.size > 0:
				q_thr = np.percentile(q_vals, 99.3)
				core_mask = (self.q_criterion > q_thr) & (~self.obstacle)
				core_overlay[core_mask] = [1.0, 1.0, 1.0, 0.45]
		self.im_core1.set_array(core_overlay)
		self.im_core2.set_array(core_overlay)

		# Progressive path reveal: light up path cells reached by the fluid.
		if self.display_mode == "maze" and np.any(self.maze_path_mask):
			speed_threshold = self.u_in * 0.05
			newly_reached = self.maze_path_mask & (speed > speed_threshold) & ~self.maze_path_revealed
			if np.any(newly_reached):
				self.maze_path_revealed |= newly_reached
				self._build_path_overlay(reveal_mask=self.maze_path_revealed)

		re = self.reynolds_number()
		self.status_text.set_text(
			(
				f"step={self.frame_count}  tau={self.tau:.3f}  u_in={self.u_in:.3f}  "
				f"Re~{re:.1f}  brush={self.brush_radius}  mode={'draw' if self.draw_mode else 'erase'}\n"
				f"MEM: Fy={self.fy_mem:+.4e}, Cl={self.cl_mem:+.3f} | "
				f"Pressure: Fy={self.fy_pressure:+.4e}, Cl={self.cl_pressure:+.3f} | "
				f"Gamma={self.gamma:+.4e}, Cl(gamma)={self.cl_gamma:+.3f}\n"
				f"keys: space pause | r reset | c clear | d/e draw/erase | +/- brush | arrows tune | s snapshot\n"
				f"1-4 presets | 5 sq | 6 ellip | 7 tri | 8 plate | 9 dia | k Karman | n NACA | i image | m maze | p perturb | v cores | a scale\n"
				f"last: {self.last_action}"
			)
		)

		artists = [
			self.im_speed,
			self.im_vorticity,
			self.im_obstacle1,
			self.im_obstacle2,
			self.im_core1,
			self.im_core2,
			self.status_text,
		]
		if self.im_path1 is not None:
			artists.append(self.im_path1)
		if self.im_path2 is not None:
			artists.append(self.im_path2)
		if self.line_cl_mem is not None:
			artists.append(self.line_cl_mem)
			artists.append(self.line_cl_pressure)
			artists.append(self.line_cl_gamma)
		return artists

	def build_figure(self):
		self.fig = plt.figure(figsize=(20, 7), facecolor="#2b2b2b")
		from matplotlib.gridspec import GridSpec
		# 适当增大列间距，避免中间图色标标签与右侧升力系数坐标轴标题拥挤重叠。
		gs = GridSpec(1, 3, figure=self.fig, width_ratios=[4, 4, 2.5],
					  left=0.02, right=0.98, top=0.93, bottom=0.15,
					  wspace=0.28)
		self.ax1 = self.fig.add_subplot(gs[0])
		self.ax2 = self.fig.add_subplot(gs[1])
		self.ax3 = self.fig.add_subplot(gs[2])
		for ax in (self.ax1, self.ax2):
			ax.set_facecolor("#111111")
			ax.set_xticks([])
			ax.set_yticks([])

		speed = np.sqrt(self.ux**2 + self.uy**2)
		self.compute_vorticity()

		self.im_speed = self.ax1.imshow(speed, cmap="inferno", interpolation="nearest", vmin=0, vmax=max(0.15, self.u_in * 2.0))
		self.ax1.set_title("Velocity Magnitude", color="white")
		self.cbar_speed = self.fig.colorbar(self.im_speed, ax=self.ax1, fraction=0.035, pad=0.02)
		self.cbar_speed.set_label("Speed [lu/ts]", color="white", fontsize=8)
		self.cbar_speed.ax.tick_params(colors="white", labelsize=6)

		self.im_vorticity = self.ax2.imshow(self.vorticity, cmap="seismic", interpolation="nearest", vmin=-0.15, vmax=0.15)
		self.cbar_vorticity = self.fig.colorbar(self.im_vorticity, ax=self.ax2, fraction=0.035, pad=0.02)
		self.cbar_vorticity.set_label("Vorticity \u03c9 [1/ts]", color="white", fontsize=8)
		self.cbar_vorticity.ax.tick_params(colors="white", labelsize=6)
		self.set_right_panel_mode(self.display_mode)

		obstacle_overlay = np.zeros((self.ny, self.nx, 4), dtype=np.float32)
		obstacle_overlay[self.obstacle] = [1.0, 1.0, 1.0, 0.95]
		self.im_obstacle1 = self.ax1.imshow(obstacle_overlay, interpolation="nearest")
		self.im_obstacle2 = self.ax2.imshow(obstacle_overlay, interpolation="nearest")

		core_overlay = np.zeros((self.ny, self.nx, 4), dtype=np.float32)
		self.im_core1 = self.ax1.imshow(core_overlay, interpolation="nearest")
		self.im_core2 = self.ax2.imshow(core_overlay, interpolation="nearest")

		# Path overlay layers (initially transparent).
		empty_path = np.zeros((self.ny, self.nx, 4), dtype=np.float32)
		self.im_path1 = self.ax1.imshow(empty_path, interpolation="nearest")
		self.im_path2 = self.ax2.imshow(empty_path, interpolation="nearest")
		if self.maze_path_overlay is not None:
			self.im_path1.set_array(self.maze_path_overlay)
			self.im_path2.set_array(self.maze_path_overlay)

		self.ax3.set_facecolor("#0e0e0e")
		self.ax3.set_title("Lift Coefficient History", color="white")
		self.ax3.set_xlabel("History index (latest at right)", color="white", fontsize=9)
		self.ax3.set_ylabel("Cl [-]", color="white", fontsize=9)
		self.ax3.tick_params(colors="white", labelsize=8)
		self.ax3.grid(color="#333333", linestyle="--", linewidth=0.6, alpha=0.8)
		self.ax3.axhline(0.0, color="#666666", linewidth=1.0)
		self.line_cl_mem, = self.ax3.plot([], [], color="#00ffaa", linewidth=1.3, label="Cl (MEM)")
		self.line_cl_pressure, = self.ax3.plot([], [], color="#ffd166", linewidth=1.1, label="Cl (Pressure)")
		self.line_cl_gamma, = self.ax3.plot([], [], color="#66c2ff", linewidth=1.1, label="Cl (Gamma)")
		legend = self.ax3.legend(loc="upper right", fontsize=8, frameon=True)
		legend.get_frame().set_facecolor("#1a1a1a")
		legend.get_frame().set_edgecolor("#666666")
		for txt in legend.get_texts():
			txt.set_color("white")
		self.ax3.set_xlim(0, max(20, self.history_max_points))
		self.ax3.set_ylim(-2.0, 2.0)

		# Dedicated info bar under images so text never blocks the simulation view.
		self.info_ax = self.fig.add_axes([0.01, 0.005, 0.98, 0.12])
		self.info_ax.set_facecolor("#0d0d0d")
		self.info_ax.set_xticks([])
		self.info_ax.set_yticks([])
		for spine in self.info_ax.spines.values():
			spine.set_visible(False)

		self.status_text = self.info_ax.text(
			0.01,
			0.5,
			"",
			transform=self.info_ax.transAxes,
			color="cyan",
			fontsize=7.5,
			va="center",
			ha="left",
			family="monospace",
		)

		self.fig.canvas.mpl_connect("button_press_event", self.on_mouse_press)
		self.fig.canvas.mpl_connect("button_release_event", self.on_mouse_release)
		self.fig.canvas.mpl_connect("motion_notify_event", self.on_mouse_move)
		self.fig.canvas.mpl_connect("key_press_event", self.on_key_press)

	def run(self, total_frames=5000, interval=30):
		self.build_figure()
		self.ani = animation.FuncAnimation(
			self.fig,
			self.update,
			frames=total_frames,
			interval=interval,
			blit=True,
		)
		plt.show()

	def export(self, output_path, frames=600, interval=30, fps=30):
		self.build_figure()
		self.ani = animation.FuncAnimation(
			self.fig,
			self.update,
			frames=frames,
			interval=interval,
			blit=True,
		)

		output_path = Path(output_path)
		output_path.parent.mkdir(parents=True, exist_ok=True)

		suffix = output_path.suffix.lower()
		if suffix == ".gif":
			writer = animation.PillowWriter(fps=fps)
		elif suffix == ".mp4":
			writer = animation.FFMpegWriter(fps=fps, bitrate=2200)
		else:
			raise ValueError("Output format must be .gif or .mp4")

		self.ani.save(output_path, writer=writer)
		plt.close(self.fig)


def parse_args():
	parser = argparse.ArgumentParser(
		description="LBM D2Q9 Cellular Automaton: Karman Vortex Street Simulation"
	)
	parser.add_argument("--ny", type=int, default=200, help="Grid height")
	parser.add_argument("--nx", type=int, default=800, help="Grid width")
	parser.add_argument("--tau", type=float, default=0.56, help="Relaxation time")
	parser.add_argument("--u-in", type=float, default=0.08, dest="u_in", help="Inlet velocity")
	parser.add_argument("--steps-per-frame", type=int, default=6, help="LBM iterations per animation frame")
	parser.add_argument(
		"--obstacle-mode",
		choices=["circle", "image"],
		default="circle",
		help="Obstacle mode",
	)
	parser.add_argument("--obstacle-image", type=str, default=None, help="Path to obstacle image (black=obstacle)")
	parser.add_argument("--non-periodic-y", action="store_true", help="Use bounce walls at top/bottom")
	parser.add_argument("--frames", type=int, default=5000, help="Total frames for interactive run")
	parser.add_argument("--interval", type=int, default=30, help="Animation interval in ms")
	parser.add_argument("--export", type=str, default=None, help="Export animation path (.gif or .mp4)")
	parser.add_argument("--export-frames", type=int, default=600, help="Frame count for export")
	parser.add_argument("--fps", type=int, default=30, help="FPS for export")
	return parser.parse_args()


def main():
	args = parse_args()

	sim = LBMKarmanSimulation(
		ny=args.ny,
		nx=args.nx,
		tau=args.tau,
		u_in=args.u_in,
		steps_per_frame=args.steps_per_frame,
		obstacle_mode=args.obstacle_mode,
		obstacle_image=args.obstacle_image,
		periodic_y=not args.non_periodic_y,
	)

	if args.export:
		sim.export(args.export, frames=args.export_frames, interval=args.interval, fps=args.fps)
		print(f"Saved animation to: {args.export}")
	else:
		sim.run(total_frames=args.frames, interval=args.interval)


if __name__ == "__main__":
	main()
