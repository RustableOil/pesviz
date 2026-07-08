"""Handle the GLFW window context"""

import glfw
import glm
from OpenGL.GL import *
import imgui
from imgui.integrations.glfw import GlfwRenderer
from pesviz.renderer import Renderer
from pesviz.shader import create_shader_program
from pesviz.camera import Camera
from pesviz.loader import import_partn_search
from pesviz.scene import Scene
from pesviz.constants import *


def main(args=None):
    """Initialize window and enter main interaction loop"""


    if not glfw.init():
        raise RuntimeError("Failed to initialize GLFW.")

    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, True)  # required on macOS
    glfw.window_hint(glfw.SAMPLES, 4)

    window_width = 1280
    window_height = 720
    aspect_ratio = window_width / window_height

    window = glfw.create_window(window_width, window_height, "PESviz", None, None)
    if not window:
        glfw.terminate()
        raise RuntimeError("Failed to create glfw window")

    glfw.make_context_current(window)
    glfw.swap_interval(1)

    init_camera_pos = [0, 0.5, 1]
    init_camera_target = [0, 0, 0]
    camera = Camera(position=init_camera_pos, target=init_camera_target)

    shader = create_shader_program()
    renderer = Renderer(shader)

    glEnable(GL_DEPTH_TEST)
    glClearColor(0.1, 0.1, 0.1, 1.0)

    glfw.show_window(window)

    filepath = args.filepath if args else None
    selected_environment = import_partn_search(filepath) if filepath else None

    scene = Scene(selected_environment)

    imgui.create_context()
    imgui_renderer = GlfwRenderer(window, attach_callbacks=False)

    # callback function state variables
    prev_x, prev_y = None, None
    left_mouse_button_held = False 
    right_mouse_button_held = False 
    ctrl_held = False
    shift_held = False
    alt_held = False
    camera_distance = glm.length([t - p for t, p in zip(init_camera_target, init_camera_pos)])
    animation = False
    ff_animation = False
    debug_arrow_origin = None
    debug_arrow_direction = None
    left_click_pending = False
    follow_camera = False

    def follow_target_point():
        """If camera-follow is on, re-aim the camera at the latest point without moving it."""
        if follow_camera:
            camera.reset(camera.position, scene.target_positions[-1])

    def on_key(window, key, scancode, action, mods):
        """Handle key presses/releases: quit, modifier state, and the animation/color/scale toggles."""
        nonlocal ctrl_held, animation, ff_animation, follow_camera, alt_held
        if key == glfw.KEY_ESCAPE and action == glfw.PRESS:
            glfw.set_window_should_close(window, True)
        if key == glfw.KEY_LEFT_CONTROL or key == glfw.KEY_RIGHT_CONTROL:
            ctrl_held = (action != glfw.RELEASE)
        if key == glfw.KEY_LEFT_SHIFT or key == glfw.KEY_RIGHT_SHIFT:
            shift_held = (action != glfw.RELEASE)
        if key == glfw.KEY_LEFT_ALT or key == glfw.KEY_RIGHT_ALT:
            alt_held = (action != glfw.RELEASE)
        if key == glfw.KEY_A and action == glfw.PRESS:
            animation = not animation
        if key == glfw.KEY_S:
            ff_animation = (action != glfw.RELEASE)
        if key == glfw.KEY_M and action == glfw.PRESS:
            scene.heatmap_mode = not scene.heatmap_mode
        if key == glfw.KEY_T and action == glfw.PRESS:
            scene.spatial_mode = not scene.spatial_mode
        if key == glfw.KEY_V and action == glfw.PRESS:
            scene.show_arrows = not scene.show_arrows
        if key == glfw.KEY_P and action == glfw.PRESS:
            scene.show_points = not scene.show_points
        if key == glfw.KEY_R and action == glfw.PRESS:
            scene.omit_short_steps = not scene.omit_short_steps
        if key == glfw.KEY_EQUAL and action == glfw.PRESS:
            scene.energy_scale *= 1.25
        if key == glfw.KEY_MINUS and action == glfw.PRESS:
            scene.energy_scale = max(0.01, scene.energy_scale / 1.25)
        if key == glfw.KEY_Z and not animation and (action == glfw.PRESS or action == glfw.REPEAT):
            scene.istep = scene.previous_renderable_istep()
            follow_target_point()
        if key == glfw.KEY_X and not animation and (action == glfw.PRESS or action == glfw.REPEAT):
            scene.istep = scene.next_renderable_istep()
            follow_target_point()
        if key == glfw.KEY_C and action == glfw.PRESS and not animation:
            scene.istep = scene.nstep
            follow_target_point()
        if key == glfw.KEY_B and action == glfw.PRESS:
            camera.reset(init_camera_pos, init_camera_target)
        if key == glfw.KEY_F and action == glfw.PRESS:
            follow_camera = not follow_camera
            
    def on_mouse_button(window, button, action, mods):
        """Track left/right mouse button held-state and flag a pending left-click for picking."""
        nonlocal left_mouse_button_held, right_mouse_button_held, left_click_pending
        if button == glfw.MOUSE_BUTTON_LEFT:
            left_mouse_button_held = (action == glfw.PRESS)
            if action == glfw.PRESS:
                left_click_pending = True
        elif button == glfw.MOUSE_BUTTON_RIGHT:
            right_mouse_button_held = (action == glfw.PRESS)

    def on_cursor_move(window, x, y):
        """Orbit the camera from mouse-drag deltas while the left button is held (ctrl = vertical)."""
        nonlocal ctrl_held

        imgui_renderer.process_inputs()
        if not imgui.get_io().want_capture_mouse:

            nonlocal prev_x, prev_y
            if prev_x is None:
                prev_x = x
                prev_y = y
                return

            dx = x - prev_x
            dy = y - prev_y
            prev_x = x
            prev_y = y

            if left_mouse_button_held:
                if ctrl_held:
                    camera.handle_vertical_orbit(dy)
                else:
                    camera.handle_horizontal_orbit(dx)


    def on_scroll(window, x_offset, y_offset):
        """Zoom the camera in/out on scroll."""
        nonlocal camera_distance
        camera_distance = camera.handle_mouse_scroll(x_offset, y_offset)

    def on_window_resize(window, width, height):
        """Track the window's logical size, used by imgui and cursor-position math."""
        nonlocal window_width, window_height
        window_width = width
        window_height = height

    def on_framebuffer_resize(window, width, height):
        """Resize the GL viewport to the new framebuffer pixel size."""
        glViewport(0, 0, width, height)

    glfw.set_key_callback(window, on_key)
    glfw.set_mouse_button_callback(window, on_mouse_button)
    glfw.set_cursor_pos_callback(window, on_cursor_move)
    glfw.set_scroll_callback(window, on_scroll)
    glfw.set_window_size_callback(window, on_window_resize)
    glfw.set_framebuffer_size_callback(window, on_framebuffer_resize)

    prev_tick_time = glfw.get_time()
    prev_animation_time = glfw.get_time()

    # MAIN GLFW LOOP
    while not glfw.window_should_close(window):

        curr_time = glfw.get_time()
        delta_tick_time = curr_time - prev_tick_time
        prev_tick_time = curr_time
        fps = 1.0 / delta_tick_time 

        glfw.poll_events()

        imgui_renderer.process_inputs()

        imgui.new_frame()
        draw_info_window(scene, fps, window_height, follow_camera)
        imgui.render()

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        V = camera.get_view_matrix()
        P = camera.get_projection_matrix(aspect_ratio)

        # consume this frame's click exactly once, so holding the button
        # down doesn't keep re-selecting whatever is currently hovered
        click_this_frame = left_click_pending
        left_click_pending = False

        # target picking: right-hold to select a camera target, alt-hold to jump istep to a point
        if right_mouse_button_held or alt_held:

            cursor_x, cursor_y = glfw.get_cursor_pos(window)

            ray_origin, ray_dir = cast_picking_ray(cursor_x, cursor_y, window_width, window_height, V, P)

            # debug_arrow_origin = ray_origin
            # debug_arrow_direction = ray_dir

            target_positions = scene.target_positions
            hovered_idx = pick_target_point(ray_origin, ray_dir, target_positions, camera.position,
                                             radius_factor=Scene.ICOSPHERE_RADIUS_FACTOR)

            scene.hovered_idx = hovered_idx

            if click_this_frame and hovered_idx is not None:
                if right_mouse_button_held:
                    scene.target_idx = hovered_idx
                    camera.target = target_positions[hovered_idx]
                elif alt_held:
                    scene.istep = scene.istep_for_point_idx(hovered_idx)
                    follow_target_point()

        # if debug_arrow_origin is not None:
        #     renderer.draw_arrow(
        #         origin=debug_arrow_origin,
        #         direction=debug_arrow_direction,
        #         color=PHASE_COLORS[PHASE_VOID],
        #         V=V,
        #         P=P,
        #         view_pos=camera.position,
        #         stalk_radius=camera_distance / 500,
        #         cone_radius=camera_distance / 200,
        #         cone_height=camera_distance / 50,
        #     )

        # animation
        delta_animation_time = curr_time - prev_animation_time
        
        tick_thr = FF_ANIMATION_TICK_THR if ff_animation else ANIMATION_TICK_THR
        if scene.istep >= scene.nstep:
            tick_thr = END_PAUSE_DURATION

        if animation and delta_animation_time > tick_thr:
            scene.istep = scene.next_renderable_istep()
            follow_target_point()
            prev_animation_time = curr_time

        # draw the scene
        scene.draw_scene(renderer, V, P, camera.position)
        renderer.render(V, P, camera.position)

        imgui_renderer.render(imgui.get_draw_data())

        glfw.swap_buffers(window)

    imgui_renderer.shutdown()
    glfw.terminate()
    

def draw_legend(scene):
    """Draw the phase-color legend, or the heatmap gradient with its etot range, depending on mode."""

    if scene.heatmap_mode:
        imgui.text("Heatmap Legend (relative etot)")
        imgui.separator()

        bar_width, bar_height = 200, 20
        pos_x, pos_y = imgui.get_cursor_screen_pos()
        draw_list = imgui.get_window_draw_list()
        low_color = imgui.get_color_u32_rgba(*HEATMAP_LOW_COLOR)
        high_color = imgui.get_color_u32_rgba(*HEATMAP_HIGH_COLOR)
        draw_list.add_rect_filled_multicolor(
            pos_x, pos_y, pos_x + bar_width, pos_y + bar_height,
            low_color, high_color, high_color, low_color,
        )
        imgui.dummy(bar_width, bar_height)

        imgui.text(f"Min etot: {scene.etot_min:.3f} eV")
        imgui.text(f"Max etot: {scene.etot_max:.3f} eV")
        return

    imgui.text("Search Phase Legend")
    imgui.separator()

    for phase_idx, label in PHASE_LABELS.items():
        r, g, b, a = PHASE_COLORS[phase_idx]

        imgui.color_button(
                f"##{phase_idx}",
                r, g, b, a,
                flags=imgui.COLOR_EDIT_NO_TOOLTIP,
                width=16,
                height=16
            )
        imgui.same_line()
        imgui.text(label)


def draw_info_window(scene, fps, window_height, follow_camera):
    """Draw the ##Info side panel: render state, mouse/keyboard controls, and the color legend."""
    imgui.set_next_window_position(0, 0)
    imgui.set_next_window_size(300, window_height)
    imgui.begin("##Info",
                    flags=imgui.WINDOW_NO_RESIZE |
                    imgui.WINDOW_NO_MOVE |
                    imgui.WINDOW_NO_COLLAPSE
                )

    imgui.text(f"FPS: {fps:.1f}")

    imgui.separator()

    imgui.text("Render Info")
    imgui.separator()
    imgui.text(f"Step: {scene.istep} / {scene.nstep}")

    imgui.indent()
    omit_label = "on" if scene.omit_short_steps else "off"
    omitted_steps = scene.istep - scene.rendered_point_count
    imgui.text_disabled(f"{omitted_steps} step(s) omitted ({omit_label})")

    imgui.same_line()
    imgui.text_disabled("(i)")
    if imgui.is_item_hovered():
        imgui.begin_tooltip()
        imgui.push_text_wrap_pos(200)
        imgui.text_unformatted("short-displacement steps can be omitted for improving performance (R to toggle)")
        imgui.pop_text_wrap_pos()
        imgui.end_tooltip()

    imgui.unindent()

    view_mode_label = "True 3D (z)" if scene.spatial_mode else "Proj. energy landscape"
    imgui.text(f"View mode: {view_mode_label}")
    imgui.same_line()
    imgui.text_disabled("(i)")
    if imgui.is_item_hovered():
        imgui.begin_tooltip()
        imgui.push_text_wrap_pos(220)
        imgui.text_unformatted(
                "projected energy landscape mode determines a plane of best-fit via PCA "
                "(smallest variance eigenvector), as well as a standard deviation to compress "
                "3D position data down to 2D. note that this process may create inaccuracies "
                "in the projected data if the deviation is too large"
        )
        imgui.pop_text_wrap_pos()
        imgui.end_tooltip()

    imgui.indent()
    imgui.text_disabled(f"Plane fit error: {scene.plane_fit_error:.4f}")
    imgui.unindent()

    color_mode_label = "Heatmap (etot)" if scene.heatmap_mode else "Phase"
    imgui.text(f"Color mode: {color_mode_label}")
    scale_label = "Z scale" if scene.spatial_mode else "Energy scale"
    imgui.text(f"{scale_label}: {scene.energy_scale:.2f}x")
    arrows_label = "On" if scene.show_arrows else "Off"
    imgui.text(f"Push vectors: {arrows_label}")
    points_label = "On" if scene.show_points else "Off"
    imgui.text(f"Points: {points_label}")
    follow_label = "On" if follow_camera else "Off"
    imgui.text(f"Camera follow: {follow_label}")
    imgui.separator()

    imgui.text("Mouse Control")
    imgui.separator()
    imgui.text("Left-Drag - horizontal orbit")
    imgui.text("Ctrl-Left-Drag - vertical orbit")
    imgui.text("Right-Hold - hover over target point")
    imgui.text("  > Left-Click to select target point")
    imgui.text("Alt-Hold - hover over target point")
    imgui.text("  > Left-Click to jump istep to point")
    imgui.separator()

    imgui.text("Hotkeys")
    imgui.separator()
    imgui.text("Esc - quit")
    imgui.text("A - toggle animation")
    imgui.text("S (hold) - fast-forward")
    imgui.text("Z / X - prev / next point (anim off)")
    imgui.text("C - jump to full trajectory (anim off)")
    imgui.text("M - toggle color mode")
    imgui.text("T - toggle view mode")
    imgui.text("V - toggle push vectors")
    imgui.text("P - toggle points")
    imgui.text("R - toggle short-step omission")
    imgui.text("+/- - vertical scale")
    imgui.text("B - reset camera")
    imgui.text("F - toggle camera follow")
    imgui.separator()

    draw_legend(scene)
    imgui.separator()

    imgui.end()


def cast_picking_ray(cursor_x, cursor_y, window_width, window_height, V, P):
    """Unproject the cursor position into a world-space ray (origin, normalized direction)."""

    x_NDC = (2.0 * cursor_x / window_width) - 1.0
    y_NDC = (2.0 * cursor_y / window_height) - 1.0
    y_NDC = -y_NDC # viewport is top-down, NDC is bottom up

    near_clip = glm.vec4(x_NDC, y_NDC, -1.0, 1.0)
    far_clip = glm.vec4(x_NDC, y_NDC, 1.0, 1.0)

    inv_P = glm.inverse(P)
    near_view = inv_P * near_clip
    far_view = inv_P * far_clip

    near_view /= near_view.w
    far_view /= far_view.w

    inv_V = glm.inverse(V)
    near_world = glm.vec3(inv_V * glm.vec4(glm.vec3(near_view), 1.0))
    far_world = glm.vec3(inv_V * glm.vec4(glm.vec3(far_view), 1.0))

    ray_origin = near_world
    ray_dir = glm.normalize(far_world - near_world)

    return ray_origin, ray_dir


def pick_target_point(ray_origin, ray_dir, target_positions, view_pos, radius_factor):
    """Return the index of the closest target_positions point within pick range of the ray, or None."""

    candidates = []

    for i, point in enumerate(target_positions):
        v = glm.vec3(point - ray_origin)
        t = glm.dot(v, ray_dir)

        if t < 0.0:
            continue

        closest = ray_origin + ray_dir * t
        perp_dist = glm.length(point - closest)

        pick_radius = glm.length(point - view_pos) * radius_factor

        if perp_dist <= pick_radius:
            candidates.append((t, i))

    if not candidates:
        return None

    closest_candidate = min(candidates, key=lambda c: c[0])
    return closest_candidate[1]


if __name__ == "__main__":
    main()
