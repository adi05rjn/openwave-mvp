# OpenWave

**Learn RF waveguide modes by changing dimensions and watching the field patterns.**

OpenWave is an early open-source teaching tool for rectangular waveguides. It shows the first four transverse-electric (TE) modes, their cutoff frequencies, and the corresponding **relative longitudinal magnetic-field** (`H_z`) patterns.

No scripting or solver configuration is needed to use the desktop interface.

## Try it on Linux

You need Python 3.10+ and a graphical desktop. Tkinter is required for the desktop interface. On Ubuntu/Debian, install the prerequisites first:

```bash
sudo apt update
sudo apt install -y git python3-venv python3-tk
```

On other Linux distributions (including Arch-based systems), install Python, Tk, and Python virtual-environment support using your package manager.

```bash
git clone https://github.com/adi05rjn/openwave-mvp.git
cd openwave-mvp
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
openwave-gui
```

## Your first experiment (about two minutes)

1. **OpenWave starts with an example already displayed.** The initial waveguide is 22.86 mm wide and 10.16 mm tall.
2. Look at the colored pattern: red and blue represent opposite signs of the magnetic field `H_z`, **not heat or power**.
3. Change **Width (mm)** from `22.86` to `30` and press **Update**.
4. Notice how the field pattern and the **cutoff frequency** change.
5. Choose another pattern using **Show pattern**. You can save the image or close the window with **Exit** (or Esc).

**What is cutoff frequency?** Each waveguide mode has a minimum frequency needed to travel through the guide. Below its cutoff, the mode does not propagate along the guide.

**What is a mode?** A particular electromagnetic field pattern that can exist inside the waveguide.

## Optional command line

The command-line interface is useful for further experiments but is **not needed** for the GUI.

```bash
openwave --width-mm 22.86 --height-mm 10.16 --modes 4 --plot artifacts/mode1.png
```

It prints cutoff frequencies in GHz and saves a PNG of the first mode.

## For developers

```bash
python -m pip install -e '.[dev]'
python -m pytest -q
```

The solver uses a cell-centred 2-D grid and a scalar finite-difference TE eigenproblem. The repository includes analytical cutoff and mesh-convergence tests. See [architecture notes](docs/ARCHITECTURE.md).

## Current limits

OpenWave only handles ideal, perfectly conducting, rectangular waveguides and scalar TE modes. It does **not** yet support TM modes, driven simulations, S-parameters, conductor losses, arbitrary CAD geometries, or full 3-D electromagnetic fields.

It is an educational prototype, not a substitute for a full-wave RF design tool.

## License

Apache-2.0 (see [LICENSE](LICENSE)).
