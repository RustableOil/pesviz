# PESviz (PARTn Event Search visualizer)
---

A 3D, Python & OpenGL-based program that uses a series of points and arrows to visually display the event search paths taken by a [pARTn](https://mammasmias.gitlab.io/artn-plugin/) event search. 

![alt text](https://github.com/RustableOil/pesviz/blob/main/docs/images/sample.png "sample render view")

# Installation
---
### Linux

Ensure you have a valid version of OpenGL installed with package `mesa-utils`

```
glxinfo | grep "OpenGL version"
```

Create a Python virtual environment, `source` into it, `git clone` the repository and `cd` into it

```
python -m venv /your/venv/dir/pesviz_venv
source /your/venv/dir/pesviz_venv/bi/activate
git clone https://github.com/RustableOil/pesviz.git
cd pesviz
```

Install the package contents to the virtual environment

```
pip install -e .
```

# Usage

Supported file systems are (currently):
* `pandas`' `.pickle`
* TODO: HDF5

The program expects these generic search parameters as input:
* `disp_code` : `int` - Search phase marker
* `pos` : `list[float]` - central atom positions per step
* `etot` : `float` - total system energy (eV)

Run the program

```
python -m pesviz -fp /path/to/supported_file
python -m pesviz --filepath /path/to/supported_file
```


