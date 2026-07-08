"""View and projection matrix generation"""

import glm
import math

class Camera:
    """Spherical-coordinate orbit camera: orbits, zooms, and reconstructs its own view/projection matrices."""

    def __init__(self, position, target, up=(0.0, 1.0, 0.0), fov=45, orbit_sensitivity=0.005):
        """Derive the initial orbit radius/yaw/pitch from a Cartesian position and target."""
        self.up = glm.vec3(*up)
        self.fov = fov
        self.orbit_sensitivity = orbit_sensitivity
        self.reset(position, target)

    def reset(self, position, target):
        """Re-derive the orbit radius/yaw/pitch from a Cartesian position and target."""
        self.target = glm.vec3(*target)

        offset = glm.vec3(*position) - self.target
        self.radius = glm.length(offset)

        self.theta = math.atan2(offset.x, offset.z)   # yaw   (horizontal angle)
        self.phi = math.asin(offset.y / self.radius) # pitch (vertical angle)

    @property
    def position(self):
        """Reconstruct Cartesian position from spherical coordinates."""
        cos_phi = math.cos(self.phi)
        return self.target + glm.vec3(
            self.radius * cos_phi * math.sin(self.theta),
            self.radius * math.sin(self.phi),
            self.radius * cos_phi * math.cos(self.theta),
        )

    def get_view_matrix(self):
        """Build the view matrix looking from the current position at the target."""
        return glm.lookAt(self.position, self.target, self.up)

    def get_projection_matrix(self, aspect_ratio):
        """Build the perspective projection matrix, with near/far scaled to the current
        orbit radius so the far/near ratio - and depth-buffer precision - stays roughly
        constant at any zoom level, instead of collapsing when zoomed in close."""
        near = max(1e-5, self.radius * 0.01)
        far = max(10.0, self.radius * 100.0)
        return glm.perspective(glm.radians(self.fov), aspect_ratio, near, far)

    def handle_horizontal_orbit(self, dx):
        """Orbit horizontally (yaw) by a mouse-drag delta."""
        self.theta -= dx * self.orbit_sensitivity

    def handle_vertical_orbit(self, dy):
        """Orbit vertically (pitch) by a mouse-drag delta, clamped just short of the poles."""
        self.phi = max(
            -math.pi / 2.0 + 0.01,
            min(math.pi / 2.0 - 0.01, self.phi + dy * self.orbit_sensitivity)
        )

    def handle_mouse_scroll(self, x_offset, y_offset, zoom_speed=0.1):
        """Zoom in/out proportionally to the current radius, so zooming slows near the target."""
        zoom_factor = max(0.1, 1.0 - y_offset * zoom_speed)
        self.radius = max(0.0001, self.radius * zoom_factor)
        return self.radius
