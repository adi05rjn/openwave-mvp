from openwave.plotting import save_mode_plot
from openwave.waveguide import RectangularWaveguide


guide = RectangularWaveguide(width=22.86e-3, height=10.16e-3, nx=101, ny=51)
modes = guide.solve_te_modes(count=4)

for mode in modes:
    print(f"Mode {mode.index}: {mode.cutoff_frequency_hz / 1e9:.6f} GHz")

save_mode_plot(guide.grid, modes[0], "artifacts/wr90_mode1.png")
