"""Keep track of rendered objects"""

import glm
import numpy as np
from pesviz.constants import *
from pesviz.renderer import Renderer

class Scene:
    """Holds a loaded search trajectory and its display/animation state, and draws it each frame."""

    # steps whose displacement from the last renderable point falls below this
    # are indistinguishable on screen and are excluded from rendering/picking
    MIN_STEP_DISTANCE = 1e-4

    # radius/height per unit distance from the camera, so points and push
    # vectors keep a consistent apparent size regardless of how far the
    # camera has orbited from each of them individually
    ICOSPHERE_RADIUS_FACTOR = 1.0 / 150
    STALK_RADIUS_FACTOR = 1.0 / 500
    CONE_RADIUS_FACTOR = 1.0 / 200
    CONE_HEIGHT_FACTOR = 1.0 / 50

    def __init__(self, dfenvironment, hovered_idx=None, target_idx=None, istep=None, isearch=-1):
        """Store the search dataframe and compute the offsets/ranges used to place and color points."""
        self.dfenvironment = dfenvironment
        self.hovered_idx = hovered_idx
        self.target_idx = target_idx
        self.nstep = len(dfenvironment)
        self.istep = len(dfenvironment) # initially open with all steps rendered
        self.isearch = isearch

        # cached as numpy arrays so _renderable_points can index them
        # directly instead of re-running a pandas column lookup every row
        self._pos_col = np.stack(self.dfenvironment['pos'].to_numpy())
        self._etot_col = self.dfenvironment['etot'].to_numpy()
        self._disp_code_col = self.dfenvironment['disp_code'].to_numpy()

        self.posx_offset = self._pos_col[0][0]
        self.posy_offset = self._pos_col[0][1]
        self.posz_offset = self._pos_col[0][2]
        self.etot_offset = self._etot_col[0]
        self.etot_min = self._etot_col.min() - self.etot_offset
        self.etot_max = self._etot_col.max() - self.etot_offset

        # raw spatial extent, used to normalize the real z-coordinate against
        # x/y in true-3D mode (etot's range is normalized separately below,
        # against the *projected* plane's extent, since that's what's
        # actually shown on the horizontal axes in that mode)
        z_range = self._pos_col[:, 2].max() - self._pos_col[:, 2].min()
        x_range = self._pos_col[:, 0].max() - self._pos_col[:, 0].min()
        y_range = self._pos_col[:, 1].max() - self._pos_col[:, 1].min()
        raw_spatial_range = max(x_range, y_range)
        self._z_scale_baseline = raw_spatial_range / z_range if z_range > 0 and raw_spatial_range > 0 else 1.0

        # best-fit plane (via PCA / total least squares) through the full 3D
        # trajectory, computed once so the projection doesn't shift around as
        # animation reveals more points. The smallest-variance eigenvector is
        # the plane's normal; the other two span the plane itself.
        centroid = self._pos_col.mean(axis=0)
        centered = self._pos_col - centroid
        cov = np.cov(centered, rowvar=False)
        print(cov)
        eigvals, eigvecs = np.linalg.eigh(cov) # ascending eigenvalue order
        plane_normal = eigvecs[:, 0]
        plane_basis_u = eigvecs[:, 2] # largest-variance in-plane direction
        plane_basis_v = eigvecs[:, 1] # second-largest in-plane direction

        plane_coords = centered @ np.stack([plane_basis_u, plane_basis_v], axis=1)
        plane_coords -= plane_coords[0] # search starts at the origin, like every other mode
        self._plane_x_col = plane_coords[:, 0]
        self._plane_z_col = plane_coords[:, 1]

        # perpendicular (not vertical) distance of each point from the fitted
        # plane; its standard deviation is a direct measure of how well a
        # single plane actually represents the search's 3D path
        perp_dist = centered @ plane_normal
        self.plane_fit_error = float(np.std(perp_dist))

        plane_x_range = self._plane_x_col.max() - self._plane_x_col.min()
        plane_z_range = self._plane_z_col.max() - self._plane_z_col.min()
        plane_spatial_range = max(plane_x_range, plane_z_range)
        etot_range = self.etot_max - self.etot_min
        self._energy_scale_baseline = plane_spatial_range / etot_range if etot_range > 0 and plane_spatial_range > 0 else 1.0

        self.heatmap_mode = False
        # False: horizontal axes are the best-fit-plane projection, y-axis is etot
        # True: axes are the search's real (x, z, y) positions, unprojected
        self.spatial_mode = False
        self.energy_scale = 1.0
        self.show_arrows = True
        self.show_points = True
        self.omit_short_steps = True
        self.rendered_point_count = 1 # updated by draw_scene; origin only until the first draw

    @property
    def _effective_vertical_scale(self):
        """energy_scale combined with whichever internal baseline (etot or real z) matches the active position mode."""
        baseline = self._z_scale_baseline if self.spatial_mode else self._energy_scale_baseline
        return self.energy_scale * baseline

    def _renderable_points(self, upto=None):
        """
        Yield (point_idx, row_idx, position, disp_code, etot_value) for the origin
        plus every step up to `upto` (row index, default istep). If omit_short_steps
        is set, steps whose displacement from the previous renderable point falls
        below MIN_STEP_DISTANCE are skipped; otherwise every step is yielded.
        point_idx matches the indices returned by picking, so it lines up with
        hovered_idx/target_idx. row_idx is the underlying dataframe row, used to
        drive animation. etot_value is the raw (offset-relative, unscaled)
        energy, independent of which quantity the position's y-axis represents.
        """
        if upto is None:
            upto = self.istep

        point_idx = 0
        prev_position = glm.vec3(0.0, 0.0, 0.0)
        yield point_idx, 0, prev_position, PHASE_VOID, 0.0

        for i in range(1, upto):
            etot_value = self._etot_col[i] - self.etot_offset

            if self.spatial_mode:
                position = glm.vec3(
                    self._pos_col[i][0] - self.posx_offset,
                    (self._pos_col[i][2] - self.posz_offset) * self._effective_vertical_scale,
                    self._pos_col[i][1] - self.posy_offset,
                )
            else:
                position = glm.vec3(
                    self._plane_x_col[i],
                    etot_value * self._effective_vertical_scale,
                    self._plane_z_col[i],
                )

            is_renderable = (not self.omit_short_steps) or glm.length(position - prev_position) > self.MIN_STEP_DISTANCE
            if not is_renderable:
                continue

            point_idx += 1
            disp_code = self._disp_code_col[i]
            yield point_idx, i, position, disp_code, etot_value

            prev_position = position

    @property
    def target_positions(self):
        """World-space positions of every icosphere currently rendered by draw_scene."""
        return [position for _, _, position, _, _ in self._renderable_points()]

    def istep_for_point_idx(self, point_idx):
        """Return the istep that makes the given target_positions/hovered_idx index the last point shown."""
        for p_idx, row_idx, _, _, _ in self._renderable_points():
            if p_idx == point_idx:
                return row_idx + 1

        return self.istep

    def next_renderable_istep(self):
        """
        Return the istep that reveals the next renderable point beyond the one
        currently displayed, skipping over steps too small to visibly change the
        scene. Wraps back to istep=1 once nstep is reached.
        """
        if self.istep >= self.nstep:
            return 1

        for _, row_idx, _, _, _ in self._renderable_points(upto=self.nstep):
            if row_idx >= self.istep:
                return row_idx + 1

        return self.nstep

    def previous_renderable_istep(self):
        """
        Return the istep that hides the most-recently revealed renderable point,
        mirroring next_renderable_istep. First collapses any trailing
        non-renderable steps without hiding a point, then wraps to nstep once
        istep=1 is reached.
        """
        shown_row_indices = [row_idx for _, row_idx, _, _, _ in self._renderable_points(upto=self.istep)]
        last_shown_row = shown_row_indices[-1]

        if self.istep > last_shown_row + 1:
            return last_shown_row + 1

        if len(shown_row_indices) == 1:
            return self.nstep

        return shown_row_indices[-2] + 1

    def draw_scene(self, renderer, V, P, view_pos):
        """Draw every currently renderable point (and, if enabled, the push vectors between them)."""
        prev_position = None
        prev_color = None
        rendered_count = 0

        for point_idx, _, position, disp_code, etot_value in self._renderable_points():
            rendered_count += 1
            point_distance = glm.length(position - view_pos)
            icosphere_radius = point_distance * self.ICOSPHERE_RADIUS_FACTOR

            if self.hovered_idx == point_idx:
                color = HOVER_COLOR
            elif self.heatmap_mode:
                etot_range = self.etot_max - self.etot_min
                t = (etot_value - self.etot_min) / etot_range if etot_range > 0 else 0.0
                color = heatmap_color(t)
            else:
                color = PHASE_COLORS[disp_code]

            if self.show_points:
                renderer.draw_icosphere(position=position,
                               radius=icosphere_radius,
                               color=color,
                               V=V,
                               P=P,
                               view_pos=view_pos)

            # push vectors
            if self.show_arrows and prev_position is not None:
                direction = position - prev_position
                # scale from whichever endpoint is nearer the camera, so a
                # close origin/tip never inherits an oversized radius from a
                # much farther-away endpoint
                arrow_distance = min(point_distance, glm.length(prev_position - view_pos))
                # color the push vector by the phase it departs FROM (the
                # previous point), not the phase it arrives at
                renderer.draw_arrow(
                            origin=prev_position,
                            direction=direction,
                            color=prev_color,
                            V=V,
                            P=P,
                            view_pos=view_pos,
                            stalk_radius=arrow_distance * self.STALK_RADIUS_FACTOR,
                            cone_radius=arrow_distance * self.CONE_RADIUS_FACTOR,
                            cone_height=arrow_distance * self.CONE_HEIGHT_FACTOR
                            )

            prev_position = position
            prev_color = color

        self.rendered_point_count = rendered_count

