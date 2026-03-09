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
		nx=800,
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
		self.im_speed = None
		self.im_vorticity = None
		self.im_obstacle1 = None
		self.im_obstacle2 = None
		self.info_ax = None
		self.status_text = None
		self.ani = None

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
			else:
				self.set_circle_obstacle()
				self.last_action = "Image load failed, fallback to circle obstacle"
		else:
			self.set_circle_obstacle()

		self.reset_flow()

	def set_circle_obstacle(self):
		self.obstacle.fill(False)
		cy = self.ny // 2
		cx = self.nx // 5
		radius = max(8, self.ny // 10)
		y, x = np.ogrid[: self.ny, : self.nx]
		self.obstacle = (x - cx) ** 2 + (y - cy) ** 2 <= radius**2

	def set_naca0012_obstacle(self):
		"""Create a centered NACA 0012 airfoil obstacle in pixel space."""
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
		polygon = np.column_stack([x_poly, y_poly])

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

	def reset_flow(self):
		rho0 = np.ones((self.ny, self.nx), dtype=np.float64)
		ux0 = np.full((self.ny, self.nx), self.u_in, dtype=np.float64)
		uy0 = np.zeros((self.ny, self.nx), dtype=np.float64)

		ux0[self.obstacle] = 0.0
		uy0[self.obstacle] = 0.0

		self.F = self.equilibria(rho0, ux0, uy0)
		self.rho = rho0
		self.ux = ux0
		self.uy = uy0
		self.vorticity = np.zeros_like(rho0)
		self.frame_count = 0

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

	def step(self):
		self.compute_macroscopic()

		feq = self.equilibria(self.rho, self.ux, self.uy)
		self.F += -(self.F - feq) / self.tau

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

	def set_preset(self, key):
		if key not in self.presets:
			return
		p = self.presets[key]
		self.tau = p["tau"]
		self.u_in = p["u_in"]
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
			self.reset_flow()
			self.last_action = "Flow reset"
		elif key == "c":
			self.obstacle.fill(False)
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
				self.reset_flow()
				self.last_action = f"Obstacle loaded: {default_img.name}"
			else:
				self.last_action = "Load failed: put obstacle.png in current folder"
		elif key == "n":
			if self.set_naca0012_obstacle():
				self.reset_flow()
				self.last_action = "Obstacle loaded: NACA 0012 airfoil"
			else:
				self.last_action = "NACA load failed"
		elif key in self.presets:
			self.set_preset(key)

	def reynolds_number(self):
		# Characteristic length based on obstacle vertical size.
		ys, xs = np.where(self.obstacle)
		if ys.size == 0:
			d = max(10, self.ny // 10)
		else:
			d = max(4, ys.max() - ys.min() + 1)
		nu = (self.tau - 0.5) / 3.0
		return self.u_in * d / max(nu, 1e-8)

	def update(self, _frame):
		if not self.paused:
			for _ in range(self.steps_per_frame):
				self.step()
			self.frame_count += self.steps_per_frame

		self.compute_macroscopic()
		self.compute_vorticity()

		speed = np.sqrt(self.ux**2 + self.uy**2)
		self.im_speed.set_array(speed)
		self.im_vorticity.set_array(self.vorticity)

		overlay = np.zeros((self.ny, self.nx, 4), dtype=np.float32)
		overlay[self.obstacle] = [1.0, 1.0, 1.0, 0.95]
		self.im_obstacle1.set_array(overlay)
		self.im_obstacle2.set_array(overlay)

		re = self.reynolds_number()
		self.status_text.set_text(
			(
				f"step={self.frame_count}  tau={self.tau:.3f}  u_in={self.u_in:.3f}  "
				f"Re~{re:.1f}  brush={self.brush_radius}  mode={'draw' if self.draw_mode else 'erase'}\n"
				f"keys: space pause | r reset | c clear | d/e draw/erase | +/- brush | "
				f"arrows tune | 1-4 presets | s snapshot | i load image | n NACA0012\n"
				f"last: {self.last_action}"
			)
		)

		return [
			self.im_speed,
			self.im_vorticity,
			self.im_obstacle1,
			self.im_obstacle2,
			self.status_text,
		]

	def build_figure(self):
		self.fig, (self.ax1, self.ax2) = plt.subplots(1, 2, figsize=(15, 6), facecolor="#2b2b2b")
		for ax in (self.ax1, self.ax2):
			ax.set_facecolor("#111111")
			ax.set_xticks([])
			ax.set_yticks([])

		speed = np.sqrt(self.ux**2 + self.uy**2)
		self.compute_vorticity()

		self.im_speed = self.ax1.imshow(speed, cmap="inferno", interpolation="nearest", vmin=0, vmax=max(0.15, self.u_in * 2.0))
		self.ax1.set_title("Velocity Magnitude", color="white")

		self.im_vorticity = self.ax2.imshow(self.vorticity, cmap="seismic", interpolation="nearest", vmin=-0.15, vmax=0.15)
		self.ax2.set_title("Vorticity (Karman Vortex Street)", color="white")

		obstacle_overlay = np.zeros((self.ny, self.nx, 4), dtype=np.float32)
		obstacle_overlay[self.obstacle] = [1.0, 1.0, 1.0, 0.95]
		self.im_obstacle1 = self.ax1.imshow(obstacle_overlay, interpolation="nearest")
		self.im_obstacle2 = self.ax2.imshow(obstacle_overlay, interpolation="nearest")

		# Dedicated info bar under images so text never blocks the simulation view.
		self.info_ax = self.fig.add_axes([0.02, 0.02, 0.96, 0.12])
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
			fontsize=9,
			va="center",
			ha="left",
			family="monospace",
		)

		self.fig.subplots_adjust(left=0.02, right=0.98, top=0.9, bottom=0.17, wspace=0.08)
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
