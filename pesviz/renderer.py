"""Populate MVP and normal matrices; align cone and cylinder meshes for arrow"""

import ctypes

from OpenGL.GL import *
import glm
import numpy as np
from pesviz.shape import generate_icosphere, generate_cylinder, generate_cone

# per-instance record uploaded to each mesh's instance VBO: a model matrix
# (16 floats), a normal matrix (9 floats), and a color (4 floats)
INSTANCE_FLOATS = 16 + 9 + 4
INSTANCE_STRIDE = INSTANCE_FLOATS * 4  # bytes

class Renderer:
    """Owns the shared shader and primitive-mesh VAOs, and instance-renders icospheres/arrows with them."""

    def __init__(self, shader):
        """Upload the icosphere/cylinder/cone meshes to VAOs (with per-instance buffers) for later draw calls."""

        self.shader = shader
        self.light_dir = glm.normalize(glm.vec3(1.0, 2.0, 1.0))

        vertices, indices, normals = generate_icosphere(subdivisions=1)
        self.icosphere_VAO, self.icosphere_n, self.icosphere_instance_VBO = self._create_mesh_vao(vertices, indices, normals)

        vertices, indices, normals = generate_cylinder()
        self.cylinder_VAO, self.cylinder_n, self.cylinder_instance_VBO = self._create_mesh_vao(vertices, indices, normals)

        vertices, indices, normals = generate_cone()
        self.cone_VAO, self.cone_n, self.cone_instance_VBO = self._create_mesh_vao(vertices, indices, normals)

        self._icosphere_instances = []
        self._cylinder_instances = []
        self._cone_instances = []

    def _create_mesh_vao(self, vertices, indices, normals):
        """Upload a mesh's position/normal/index buffers, attach a per-instance buffer, and return (VAO, index count, instance VBO)."""
        VAO = glGenVertexArrays(1)
        glBindVertexArray(VAO)

        pos_VBO = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, pos_VBO)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, None)

        norm_VBO = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, norm_VBO)
        glBufferData(GL_ARRAY_BUFFER, normals.nbytes, normals, GL_STATIC_DRAW)
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 0, None)

        EBO = glGenBuffers(1)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, EBO)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)

        # per-instance model matrix (locations 2-5, one column each), normal
        # matrix (6-8), and color (9); divisor=1 advances them once per
        # instance instead of once per vertex
        instance_VBO = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, instance_VBO)

        for col in range(4):
            loc = 2 + col
            glEnableVertexAttribArray(loc)
            glVertexAttribPointer(loc, 4, GL_FLOAT, GL_FALSE, INSTANCE_STRIDE, ctypes.c_void_p(col * 16))
            glVertexAttribDivisor(loc, 1)

        for col in range(3):
            loc = 6 + col
            glEnableVertexAttribArray(loc)
            glVertexAttribPointer(loc, 3, GL_FLOAT, GL_FALSE, INSTANCE_STRIDE, ctypes.c_void_p(64 + col * 12))
            glVertexAttribDivisor(loc, 1)

        glEnableVertexAttribArray(9)
        glVertexAttribPointer(9, 4, GL_FLOAT, GL_FALSE, INSTANCE_STRIDE, ctypes.c_void_p(100))
        glVertexAttribDivisor(9, 1)

        glBindVertexArray(0)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)

        return VAO, indices.size, instance_VBO

    def _flatten_mat(self, M):
        """Flatten a pyglm matrix's to_list() (a list of columns) into flat column-major floats."""
        return [v for col in M.to_list() for v in col]

    def _queue_instance(self, bucket, M, N, color):
        """Append one instance's model matrix, normal matrix, and color to a mesh's queue."""
        bucket.extend(self._flatten_mat(M))
        bucket.extend(self._flatten_mat(N))
        bucket.extend(color)

    def delete_mesh_vao(self, VAO):
        """Delete a single mesh VAO."""
        glDeleteVertexArrays(1, [VAO])

    def draw_icosphere(self, position, radius, color, V, P, view_pos):
        """Queue an icosphere instance of the given radius and color at a world-space position."""
        M = glm.translate(glm.mat4(1.0), position)
        M = glm.scale(M, glm.vec3(radius))
        N = glm.mat3(glm.transpose(glm.inverse(M)))
        self._queue_instance(self._icosphere_instances, M, N, color)

    def draw_arrow(self, origin, direction, color, V, P, view_pos, stalk_radius, cone_radius, cone_height):
        """Queue a cylinder-stalk + cone-tip arrow instance from origin along direction, tip at origin+direction."""

        length = glm.length(direction)
        if length < 1e-8:
            return

        unit  = direction / length
        dir_v = glm.vec3(*unit)
        y_axis = glm.vec3(0.0, 1.0, 0.0)

        dot = glm.dot(y_axis, dir_v)

        if dot > 1.0 - 1e-6:
            R = glm.mat4(1.0)
        elif dot < -1.0 + 1e-6:
            R = glm.rotate(glm.mat4(1.0), glm.pi(), glm.vec3(1.0, 0.0, 0.0))
        else:
            rotation_axis = glm.normalize(glm.cross(y_axis, dir_v))
            theta = glm.acos(dot)
            R = glm.rotate(glm.mat4(1.0), theta, rotation_axis)

        # allow stalk_length to go negative when the arrow is shorter than
        # the cone, so the cone extends back through the origin point but
        # its tip still lands exactly on the destination
        stalk_length = length - cone_height
        origin_v = glm.vec3(*origin)

        # cone
        tip_base = origin_v + dir_v * stalk_length
        M = glm.translate(glm.mat4(1.0), tip_base)
        M = M * R
        M = glm.scale(M, glm.vec3(cone_radius, cone_height, cone_radius))
        N = glm.mat3(glm.transpose(glm.inverse(M)))
        self._queue_instance(self._cone_instances, M, N, color)

        # stalk
        if stalk_length > 1e-8:
            M = glm.translate(glm.mat4(1.0), origin_v)
            M = M * R
            M = glm.scale(M, glm.vec3(stalk_radius, stalk_length, stalk_radius))
            N = glm.mat3(glm.transpose(glm.inverse(M)))
            self._queue_instance(self._cylinder_instances, M, N, color)

    def render(self, V, P, view_pos):
        """Upload this frame's queued instances and issue one instanced draw call per mesh type."""
        glUseProgram(self.shader)
        glUniformMatrix4fv(glGetUniformLocation(self.shader, "u_V"), 1, GL_FALSE, V.to_list())
        glUniformMatrix4fv(glGetUniformLocation(self.shader, "u_P"), 1, GL_FALSE, P.to_list())
        glUniform3f(glGetUniformLocation(self.shader, "u_light_dir"), *self.light_dir)
        glUniform3f(glGetUniformLocation(self.shader, "u_view_pos"), *view_pos)

        self._flush(self.icosphere_VAO, self.icosphere_instance_VBO, self.icosphere_n, self._icosphere_instances)
        self._flush(self.cylinder_VAO, self.cylinder_instance_VBO, self.cylinder_n, self._cylinder_instances)
        self._flush(self.cone_VAO, self.cone_instance_VBO, self.cone_n, self._cone_instances)

        self._icosphere_instances = []
        self._cylinder_instances = []
        self._cone_instances = []

    def _flush(self, VAO, instance_VBO, n_indices, instances):
        """Upload one mesh's queued instance data and draw every queued instance in a single call."""
        if not instances:
            return

        data = np.array(instances, dtype=np.float32)
        instance_count = data.size // INSTANCE_FLOATS

        glBindBuffer(GL_ARRAY_BUFFER, instance_VBO)
        glBufferData(GL_ARRAY_BUFFER, data.nbytes, data, GL_DYNAMIC_DRAW)

        glBindVertexArray(VAO)
        glDrawElementsInstanced(GL_TRIANGLES, n_indices, GL_UNSIGNED_INT, None, instance_count)
        glBindVertexArray(0)

    def destroy(self):
        """Delete all owned mesh VAOs and instance buffers."""
        self.delete_mesh_vao(self.icosphere_VAO)
        self.delete_mesh_vao(self.cylinder_VAO)
        self.delete_mesh_vao(self.cone_VAO)
        glDeleteBuffers(3, [self.icosphere_instance_VBO, self.cylinder_instance_VBO, self.cone_instance_VBO])
