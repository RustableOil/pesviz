"""Define vertex and fragment shaders, compile and combine"""

from OpenGL.GL import *

VERTEX_SHADER = """
#version 330 core

layout (location = 0) in vec3 a_pos;
layout (location = 1) in vec3 a_norm;
layout (location = 2) in mat4 a_M;
layout (location = 6) in mat3 a_N;
layout (location = 9) in vec4 a_color;

uniform mat4 u_V;
uniform mat4 u_P;

out vec3 v_normal;
out vec3 v_frag_pos;
out vec4 v_color;

void main() {

    vec4 pos_WCS = a_M * vec4(a_pos, 1.0);
    v_frag_pos = vec3(pos_WCS);
    v_normal = normalize(a_N * a_norm);
    v_color = a_color;
    gl_Position = u_P * u_V * pos_WCS;

}
"""

FRAGMENT_SHADER = """
#version 330 core

in vec3 v_normal;
in vec3 v_frag_pos;
in vec4 v_color;

uniform vec3 u_light_dir;
uniform vec3 u_view_pos;

out vec4 frag_color;

void main() {
    vec3 normal = normalize(v_normal);
    vec3 view_dir = normalize(u_view_pos - v_frag_pos);

    float ambient = 0.2;

    // lambertian diffusion
    float diffuse = max(dot(normalize(v_normal), normalize(u_light_dir)), 0.0);

    float lighting = ambient + (1.0 - ambient) * diffuse;

    // shape border
    float rim_dot = 1.0 - max(dot(view_dir, normal), 0.0);
    float rim_power = 1.5;
    float rim = pow(rim_dot, rim_power);
    float rim_strength = 0.6;

    vec3 rim_color = vec3(1.0, 1.0, 1.0);

    vec3 color_lighting = v_color.rgb * lighting;
    vec3 color_lighting_rim = color_lighting + rim_color * rim * rim_strength;

    frag_color = vec4(color_lighting_rim, v_color.a);

}
"""


def _compile_shaders(src, shader_type):
    """Compile a single GLSL shader stage from source, raising on a compile error."""

    handle = glCreateShader(shader_type)
    glShaderSource(handle, src)
    glCompileShader(handle)

    log = glGetShaderInfoLog(handle)
    status = glGetShaderiv(handle, GL_COMPILE_STATUS)
    stage = "vertex" if shader_type == GL_VERTEX_SHADER else "fragment"

    if log:
        print(f"{stage} shader log:\n{log}")

    if not status:
        glDeleteShader(handle)
        raise RuntimeError(f"{stage} shader compile error")

    return handle


def create_shader_program(vert_src=VERTEX_SHADER, frag_src=FRAGMENT_SHADER):
    """Compile and link the vertex/fragment shaders into a GL program, raising on a link error."""

    vert = _compile_shaders(vert_src, GL_VERTEX_SHADER)
    frag = _compile_shaders(frag_src, GL_FRAGMENT_SHADER)

    program = glCreateProgram()
    glAttachShader(program, vert)
    glAttachShader(program, frag)
    glLinkProgram(program)

    glDetachShader(program, vert)
    glDetachShader(program, frag)
    glDeleteShader(vert)
    glDeleteShader(frag)

    log = glGetProgramInfoLog(program)
    status = glGetProgramiv(program, GL_LINK_STATUS)

    if log:
        print(f"shader link log:\n{log}")

    if not status:
        glDeleteProgram(program)
        raise RuntimeError(f"shader link error")

    return program


def delete_shader_program(program):
    """Delete a previously linked GL shader program."""
    glDeleteProgram(program)
    


