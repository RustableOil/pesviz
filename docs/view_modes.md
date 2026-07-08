PESviz has the option of cycling through different methods of displaying position data in the 3D scene. The necessity of this feature comes about due to a limitation in how 4D data (x, y, z, etot) is able to be plotted in a 3D space. There are currently two different methods of representing this data.

## True-3D

This rendering method maintains the (x, y, z) position data, and generates a heatmap-style gradient to color the individual search steps based on their relative total energy, `etot`. Although this layout maintains the most accuracy to the original searching sequence, it looses the visual effect of being able to see the movement on top of the PES, and convergence to minimums.

## Projected energy landscape

In this mode, the vertical axis of the rendered scene is reserved for the system's total energy `etot`, while the 3D position data is compressed down to 2D. This is done using [principle component analysis (PCA)](https://en.wikipedia.org/wiki/Principal_component_analysis). Note: both of the following code snippets are located in the `scene.py` module.

```python
centroid = self._pos_col.mean(axis=0)
centered = self._pos_col - centroid
cov = np.cov(centered, rowvar=False)
eigvals, eigvecs = np.linalg.eigh(cov) # ascending eigenvalue order
plane_normal = eigvecs[:, 0]
plane_basis_u = eigvecs[:, 2] # largest-variance in-plane direction
plane_basis_v = eigvecs[:, 1] # second-largest in-plane direction
```

First, the centroid of all the data is defined, which is the mean position across the three coordinate axes (the list of positions has shape (N, 3). To center points around (0, 0, 0), the centroid is subtracted from all position data. Next, the 3x3 covariance matrix is generated, where the option `rowvar=False` means that the matrix is transposed, such that columns contain variables, while rows contain observations. The eigenvalues and eigenvectors of the convariance matrix are obtained in ascending order, guaranteeing that the first eigenvector is the princple plane's normal vector, then the second largest principle axis v, and finally the largest principle axis u. These new basis vectors (u,v) define the plane that is closest to where the event search takes place. 

All points are now projected onto this principle plane, to be used as the two horizontal axes for plotting later. Note: the second horizontal axis projected onto the plane is labeled as z. This is done in reference to rendering the scene, and how OpenGL treats the depth of the scene to be the z-axis, and alternatively the scene's height to be the y-axis.

```
plane_coords = centered @ np.stack([plane_basis_u, plane_basis_v], axis=1)
plane_coords -= plane_coords[0] # search starts at the origin, like every other mode
self._plane_x_col = plane_coords[:, 0]
self._plane_z_col = plane_coords[:, 1]
```

Additionally, a standard deviation is obtained to show how well the principle plane fits onto the 3D position data.

```python
perp_dist = centered @ plane_normal
self.plane_fit_error = float(np.std(perp_dist))
```

The perpendicular (not vertical) distance from the plane to each centered 3D position is obtained. Finally, 
