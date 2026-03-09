from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from Simulation import LBMKarmanSimulation


def run_case(case, ny=180, nx=600, steps=2500):
    sim = LBMKarmanSimulation(
        ny=ny,
        nx=nx,
        tau=case["tau"],
        u_in=case["u_in"],
        steps_per_frame=1,
        obstacle_mode="circle",
        periodic_y=True,
    )

    for _ in range(steps):
        sim.step()

    sim.compute_macroscopic()
    sim.compute_vorticity()
    return sim.vorticity.copy(), sim.reynolds_number()


def main():
    cases = [
        {"name": "Case A", "label": "Laminar", "tau": 0.90, "u_in": 0.04},
        {"name": "Case B", "label": "Symmetric vortices", "tau": 0.72, "u_in": 0.06},
        {"name": "Case C", "label": "Karman street", "tau": 0.58, "u_in": 0.08},
        {"name": "Case D", "label": "Unstable wake", "tau": 0.53, "u_in": 0.10},
    ]

    results = []
    for case in cases:
        vort, re = run_case(case)
        results.append((case, vort, re))
        print(f"{case['name']}: {case['label']} | Re~{re:.1f}")

    fig, axes = plt.subplots(2, 2, figsize=(14, 8), facecolor="#1f1f1f")
    axes = axes.ravel()

    for ax, (case, vort, re) in zip(axes, results):
        vmax = np.percentile(np.abs(vort), 99)
        vmax = max(vmax, 0.05)
        ax.imshow(vort, cmap="seismic", vmin=-vmax, vmax=vmax, interpolation="nearest")
        ax.set_title(
            f"{case['name']} | {case['label']}\n" f"tau={case['tau']:.2f}, u_in={case['u_in']:.3f}, Re~{re:.1f}",
            color="white",
            fontsize=10,
        )
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_facecolor("#111111")

    fig.suptitle("LBM D2Q9: Reynolds Number vs Wake Pattern", color="white", fontsize=14)
    fig.tight_layout()

    out_dir = Path(__file__).resolve().parent
    out_path = out_dir / "reynolds_comparison.png"
    fig.savefig(out_path, dpi=220, facecolor=fig.get_facecolor())
    print(f"Saved: {out_path}")
    backend = plt.get_backend().lower()
    if "agg" in backend:
        plt.close(fig)
    else:
        plt.show()


if __name__ == "__main__":
    main()
