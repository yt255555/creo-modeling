"""
机械制图微课：第一角投影法 — 三视图形成与展开
使用 Manim Community Edition，继承 ThreeDScene。
"""

from manim import *
import numpy as np

# ---------- 可调参数（课堂微调入口）----------
CHINESE_FONT = "SimHei"  # Windows 建议改为 "Microsoft YaHei"
PLANE_SIZE = 5.5           # 投影面显示边长
PLANE_OPACITY = 0.22       # 投影面半透明程度
OBJECT_COLOR = "#6B8CAE"   # 组合体配色
OUTLINE_COLOR = YELLOW     # 视图画线颜色
PROJ_LINE_COLOR = GRAY_B   # 投射线颜色
HIGHLIGHT_COLOR = RED      # “长对正 / 高平齐 / 宽相等” 高亮
WAIT_AFTER_BEAT = 1.5      # 每个镜头关键步骤后的讲解停顿（秒）
ROT_UNFOLD = 1.8           # 展开旋转动画时长（秒）

# 阶梯缺口组合体尺寸（单位：Manim 长度，约占第一角空间 3×2×2）
BASE_DIM = np.array([2.8, 2.0, 1.0])   # 底板长方体
STEP_DIM = np.array([1.4, 2.0, 1.0])   # 左侧台阶（形成阶梯缺口）


def make_prism(dimensions, color=OBJECT_COLOR, opacity=0.85):
    """用 Prism 拼合组合体，不依赖外部模型。"""
    p = Prism(dimensions=list(dimensions))
    p.set_fill(color, opacity=opacity)
    p.set_stroke(WHITE, width=0.6, opacity=0.5)
    return p


def outline_on_v(points_xz):
    """V 面（y=0）上的主视轮廓，输入 (x,z) 顶点序列。"""
    verts = [np.array([x, 0.02, z]) for x, z in points_xz]
    closed = verts + [verts[0]]
    return VMobject().set_points_as_corners(closed).set_stroke(OUTLINE_COLOR, width=3)


def outline_on_h(points_xy):
    """H 面（z=0）上的俯视轮廓。"""
    verts = [np.array([x, y, 0.02]) for x, y in points_xy]
    closed = verts + [verts[0]]
    return VMobject().set_points_as_corners(closed).set_stroke(OUTLINE_COLOR, width=3)


def outline_on_w(points_yz):
    """W 面（x=0）上的左视轮廓。"""
    verts = [np.array([0.02, y, z]) for y, z in points_yz]
    closed = verts + [verts[0]]
    return VMobject().set_points_as_corners(closed).set_stroke(OUTLINE_COLOR, width=3)


def dashed_projector(start, end, num_dashes=10):
    """三维投射线（虚线效果）。"""
    line = DashedLine(
        start, end,
        dash_length=0.08,
        dashed_ratio=0.55,
        color=PROJ_LINE_COLOR,
        stroke_width=1.2,
    )
    return line


class ProjectionDemo(ThreeDScene):
    def construct(self):
        self.set_camera_orientation(phi=68 * DEGREES, theta=-38 * DEGREES, zoom=0.95)

        # ==================== 镜头1：建系 ====================
        axes = ThreeDAxes(
            x_range=[0, PLANE_SIZE, 1],
            y_range=[0, PLANE_SIZE, 1],
            z_range=[0, PLANE_SIZE, 1],
            x_length=PLANE_SIZE,
            y_length=PLANE_SIZE,
            z_length=PLANE_SIZE,
        )
        O = Dot3D(point=ORIGIN, radius=0.06, color=WHITE)
        x_lab = Text("X", font=CHINESE_FONT, font_size=28).set_color(RED)
        y_lab = Text("Y", font=CHINESE_FONT, font_size=28).set_color(GREEN)
        z_lab = Text("Z", font=CHINESE_FONT, font_size=28).set_color(BLUE)
        o_lab = Text("O", font=CHINESE_FONT, font_size=26)

        for lab, pos in [(x_lab, axes.c2p(PLANE_SIZE * 0.92, 0, 0)),
                         (y_lab, axes.c2p(0, PLANE_SIZE * 0.92, 0)),
                         (z_lab, axes.c2p(0, 0, PLANE_SIZE * 0.92)),
                         (o_lab, axes.c2p(-0.25, -0.25, 0))]:
            lab.move_to(pos)
            self.add_fixed_orientation_mobjects(lab)

        # H：z=0 水平面；V：y=0 正立面；W：x=0 侧立面
        plane_h = Rectangle(
            width=PLANE_SIZE, height=PLANE_SIZE,
            fill_color=TEAL, fill_opacity=PLANE_OPACITY, stroke_width=0.8,
        ).move_to(np.array([PLANE_SIZE / 2, PLANE_SIZE / 2, 0]))
        plane_v = Rectangle(
            width=PLANE_SIZE, height=PLANE_SIZE,
            fill_color=BLUE, fill_opacity=PLANE_OPACITY, stroke_width=0.8,
        ).rotate(90 * DEGREES, axis=RIGHT).move_to(np.array([PLANE_SIZE / 2, 0, PLANE_SIZE / 2]))
        plane_w = Rectangle(
            width=PLANE_SIZE, height=PLANE_SIZE,
            fill_color=MAROON, fill_opacity=PLANE_OPACITY, stroke_width=0.8,
        ).rotate(90 * DEGREES, axis=UP).move_to(np.array([0, PLANE_SIZE / 2, PLANE_SIZE / 2]))

        v_name = Text("V（正立）", font=CHINESE_FONT, font_size=24, color=BLUE_C)
        h_name = Text("H（水平）", font=CHINESE_FONT, font_size=24, color=TEAL_C)
        w_name = Text("W（侧立）", font=CHINESE_FONT, font_size=24, color=MAROON_B)
        v_name.move_to(np.array([PLANE_SIZE * 0.5, 0.15, PLANE_SIZE * 0.85]))
        h_name.move_to(np.array([PLANE_SIZE * 0.15, PLANE_SIZE * 0.85, 0.15]))
        w_name.move_to(np.array([0.15, PLANE_SIZE * 0.5, PLANE_SIZE * 0.85]))
        for t in (v_name, h_name, w_name):
            self.add_fixed_orientation_mobjects(t)

        scene1 = VGroup(axes, O, plane_h, plane_v, plane_w)
        self.play(
            LaggedStart(
                Create(axes),
                FadeIn(O),
                FadeIn(plane_h),
                FadeIn(plane_v),
                FadeIn(plane_w),
                FadeIn(x_lab),
                FadeIn(y_lab),
                FadeIn(z_lab),
                FadeIn(o_lab),
                FadeIn(v_name),
                FadeIn(h_name),
                FadeIn(w_name),
                lag_ratio=0.08,
            ),
            run_time=2.5,
        )
        self.wait(WAIT_AFTER_BEAT)

        # ==================== 镜头2：投射 ====================
        # 组合体占据第一角空间：原点为墙角，实体全部在 x,y,z > 0
        base = make_prism(BASE_DIM)
        base.move_to(np.array([BASE_DIM[0] / 2, BASE_DIM[1] / 2, BASE_DIM[2] / 2]))

        step = make_prism(STEP_DIM)
        step.move_to(
            np.array([STEP_DIM[0] / 2, STEP_DIM[1] / 2, BASE_DIM[2] + STEP_DIM[2] / 2])
        )
        solid = VGroup(base, step)

        # 外包盒顶点（用于投射线示范）
        xmax, ymax, zmax = BASE_DIM[0], BASE_DIM[1], BASE_DIM[2] + STEP_DIM[2]
        corners = [
            np.array([0, 0, 0]), np.array([xmax, 0, 0]), np.array([xmax, ymax, 0]), np.array([0, ymax, 0]),
            np.array([0, 0, zmax]), np.array([xmax, 0, zmax]), np.array([xmax, ymax, zmax]), np.array([0, ymax, zmax]),
            # 台阶棱线点
            np.array([STEP_DIM[0], 0, BASE_DIM[2]]), np.array([STEP_DIM[0], ymax, BASE_DIM[2]]),
        ]

        projectors = VGroup()
        for p in corners:
            # 向 V 面（y=0）
            projectors.add(dashed_projector(p, np.array([p[0], 0, p[2]])))
            # 向 H 面（z=0）
            projectors.add(dashed_projector(p, np.array([p[0], p[1], 0])))
            # 向 W 面（x=0）
            projectors.add(dashed_projector(p, np.array([0, p[1], p[2]])))

        # 简化轮廓：阶梯形主视、俯视、左视（与组合体外廓一致）
        v_outline = outline_on_v([
            (0, 0), (xmax, 0), (xmax, BASE_DIM[2]), (STEP_DIM[0], BASE_DIM[2]),
            (STEP_DIM[0], zmax), (0, zmax), (0, 0),
        ])
        h_outline = outline_on_h([
            (0, 0), (xmax, 0), (xmax, ymax), (0, ymax), (0, 0),
        ])
        w_outline = outline_on_w([
            (0, 0), (ymax, 0), (ymax, zmax), (0, zmax), (0, 0),
        ])

        view_labels = VGroup(
            Text("主视图", font=CHINESE_FONT, font_size=22, color=OUTLINE_COLOR),
            Text("俯视图", font=CHINESE_FONT, font_size=22, color=OUTLINE_COLOR),
            Text("左视图", font=CHINESE_FONT, font_size=22, color=OUTLINE_COLOR),
        )
        view_labels[0].move_to(np.array([xmax / 2, 0.25, zmax * 0.55]))
        view_labels[1].move_to(np.array([xmax / 2, ymax / 2, 0.25]))
        view_labels[2].move_to(np.array([0.25, ymax / 2, zmax * 0.55]))
        for t in view_labels:
            self.add_fixed_orientation_mobjects(t)

        self.play(FadeIn(solid), run_time=1.0)
        self.play(LaggedStart(*[Create(l) for l in projectors], lag_ratio=0.02), run_time=2.0)
        self.play(
            Create(v_outline), Create(h_outline), Create(w_outline),
            FadeIn(view_labels),
            run_time=1.6,
        )
        self.wait(WAIT_AFTER_BEAT)

        # ==================== 镜头3：展开 ====================
        unfold_group_h = VGroup(plane_h, h_outline, view_labels[1])
        unfold_group_w = VGroup(plane_w, w_outline, view_labels[2])
        unfold_group_v = VGroup(plane_v, v_outline, view_labels[0])

        self.play(
            FadeOut(solid),
            FadeOut(projectors),
            FadeOut(axes),
            FadeOut(O),
            FadeOut(x_lab),
            FadeOut(y_lab),
            FadeOut(z_lab),
            FadeOut(o_lab),
            FadeOut(v_name),
            FadeOut(h_name),
            FadeOut(w_name),
            run_time=0.8,
        )

        hinge_x = ORIGIN  # H 与 V 共用 X 轴棱线
        hinge_z = ORIGIN  # V 与 W 共用 Z 轴棱线

        # H 绕 X 轴向下旋转 90°，贴到 V 面下方（第一角展开）
        self.play(
            Rotate(unfold_group_h, -90 * DEGREES, axis=RIGHT, about_point=hinge_x),
            run_time=ROT_UNFOLD,
        )
        self.wait(0.4)
        # W 绕 Z 轴向右旋转 90°，贴到 V 面右侧
        self.play(
            Rotate(unfold_group_w, -90 * DEGREES, axis=OUT, about_point=hinge_z),
            run_time=ROT_UNFOLD,
        )
        self.play(
            self.move_camera(phi=0, theta=-90 * DEGREES, gamma=0, zoom=1.15),
            run_time=1.8,
        )
        self.wait(WAIT_AFTER_BEAT)

        # ==================== 镜头4：规律高亮 ====================
        # 展开后布局：V 居中上方，H 在 V 正下方，W 在 V 正右方（与国标展开一致）
        len_x = xmax
        len_y = ymax
        len_z = zmax

        # 长对正：V 与 H 之间竖直方向对齐同长（X 向尺寸）
        line_chang = DashedLine(
            np.array([0, -0.15, len_z + 0.3]),
            np.array([len_x, -0.15, len_z + 0.3]),
            color=HIGHLIGHT_COLOR, dash_length=0.1,
        )
        text_chang = Text("长对正", font=CHINESE_FONT, font_size=32, color=HIGHLIGHT_COLOR)
        text_chang.next_to(line_chang, UP, buff=0.15)
        self.add_fixed_in_frame_mobjects(line_chang, text_chang)

        # 高平齐：V 与 W 之间水平方向对齐同高（Z 向）
        line_gao = DashedLine(
            np.array([len_x + 0.35, 0, len_z]),
            np.array([len_x + 0.35, 0, 0]),
            color=HIGHLIGHT_COLOR, dash_length=0.1,
        )
        text_gao = Text("高平齐", font=CHINESE_FONT, font_size=32, color=HIGHLIGHT_COLOR)
        text_gao.next_to(line_gao, RIGHT, buff=0.12)
        self.add_fixed_in_frame_mobjects(line_gao, text_gao)

        # 宽相等：H 与 W 之间对应宽度（Y 向）
        line_kuan = DashedLine(
            np.array([len_x + 0.35, len_y, 0]),
            np.array([len_x, len_y, 0]),
            color=HIGHLIGHT_COLOR, dash_length=0.1,
        )
        text_kuan = Text("宽相等", font=CHINESE_FONT, font_size=32, color=HIGHLIGHT_COLOR)
        text_kuan.next_to(line_kuan, DOWN, buff=0.12)
        self.add_fixed_in_frame_mobjects(line_kuan, text_kuan)

        self.play(Create(line_chang), FadeIn(text_chang), run_time=0.9)
        self.wait(0.6)
        self.play(Create(line_gao), FadeIn(text_gao), run_time=0.9)
        self.wait(0.6)
        self.play(Create(line_kuan), FadeIn(text_kuan), run_time=0.9)
        self.wait(WAIT_AFTER_BEAT)


# ---------------------------------------------------------------------------
# 终端渲染（1080p / 60fps）：
#   manim -pqh --format=mp4 --fps 60 -r 1920,1080 projection_demo.py ProjectionDemo
#
# 预览低清快渲（调试节奏用）：
#   manim -pql projection_demo.py ProjectionDemo
# ---------------------------------------------------------------------------