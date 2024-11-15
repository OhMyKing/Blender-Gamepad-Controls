bl_info = {
    "name": "Gamepad Controls",
    "author": "OhMyKing",
    "version": (1, 1),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Gamepad",
    "description": "Control Blender with a gamepad",
    "category": "3D View",
}

import bpy
import mathutils
import threading
import time
from bpy.types import Operator, Panel, PropertyGroup
from bpy.props import FloatProperty, PointerProperty, BoolProperty


if "inputs" in locals():
    import importlib

    wheels = importlib.reload(wheels)
    wheels.load_wheels()
else:
    from . import wheels

    wheels.load_wheels()

# 动态检测函数
def check_gamepad_available():
    try:
        from inputs import get_gamepad
        # 尝试获取手柄事件，如果没有手柄会抛出异常
        events = get_gamepad()
        return True
    except:
        return False

from bpy_extras import view3d_utils


# 手柄状态类
class GamepadState:
    def __init__(self):
        self.left_stick_x = 0.0
        self.left_stick_y = 0.0
        self.right_stick_x = 0.0
        self.right_stick_y = 0.0
        self.buttons = {}
        self.button_states = {}
        self.dpad_up = 0
        self.dpad_down = 0
        self.dpad_left = 0
        self.dpad_right = 0

gamepad_state = GamepadState()

# 手柄输入监听线程
class GamepadThread(threading.Thread):
    def __init__(self):
        super().__init__()
        self.daemon = True
        self.running = True
        self.error_message = None
        self._consecutive_errors = 0  # 添加连续错误计数器
        self._max_consecutive_errors = 10  # 最大连续错误次数

    def run(self):
        while self.running:
            try:
                from inputs import get_gamepad
                events = get_gamepad()
                # 成功获取事件，重置错误计数
                self._consecutive_errors = 0
                self.error_message = None

                for event in events:
                    if self.running:  # 检查是否仍在运行
                        self.process_event(event)

            except ImportError:
                self.error_message = "未安装 'inputs' 包。请安装后重试。"
                self._consecutive_errors += 1
                time.sleep(1)

            except Exception as e:
                self._consecutive_errors += 1
                if "No gamepad found" in str(e):
                    self.error_message = "未检测到手柄。请确保手柄已连接。"
                else:
                    self.error_message = f"手柄错误: {e}"
                time.sleep(0.5)  # 减少等待时间，提高响应速度

            # 如果连续错误次数过多，可能需要关闭控制
            if self._consecutive_errors >= self._max_consecutive_errors:
                self.error_message = "多次无法检测到手柄，已自动关闭控制。"
                break

    def process_event(self, event):
        """处理手柄事件"""
        if event.code == 'ABS_X':
            gamepad_state.left_stick_x = event.state / 32768.0
        elif event.code == 'ABS_Y':
            gamepad_state.left_stick_y = event.state / 32768.0
        elif event.code == 'ABS_RX':
            gamepad_state.right_stick_x = event.state / 32768.0
        elif event.code == 'ABS_RY':
            gamepad_state.right_stick_y = event.state / 32768.0
        elif event.code == 'ABS_HAT0Y':
            if event.state == -1:
                gamepad_state.dpad_up = 1
                gamepad_state.dpad_down = 0
            elif event.state == 1:
                gamepad_state.dpad_down = 1
                gamepad_state.dpad_up = 0
            else:
                gamepad_state.dpad_up = 0
                gamepad_state.dpad_down = 0
        elif event.code == 'ABS_HAT0X':
            if event.state == -1:
                gamepad_state.dpad_left = 1
                gamepad_state.dpad_right = 0
            elif event.state == 1:
                gamepad_state.dpad_right = 1
                gamepad_state.dpad_left = 0
            else:
                gamepad_state.dpad_left = 0
                gamepad_state.dpad_right = 0
        elif event.code.startswith('BTN_'):
            gamepad_state.buttons[event.code] = event.state
            gamepad_state.button_states[event.code] = event.state

# 设置属性
class GamepadSettings(PropertyGroup):
    pan_speed: FloatProperty(
        name="平移速度",
        description="视角平移的速度",
        default=0.1,
        min=0.01,
        max=1.0
    )
    rotation_speed: FloatProperty(
        name="旋转速度",
        description="视角旋转的速度",
        default=0.05,
        min=0.01,
        max=1.0
    )
    zoom_speed: FloatProperty(
        name="缩放速度",
        description="视角缩放的速度",
        default=0.5,
        min=0.1,
        max=2.0
    )
    scale_speed: FloatProperty(
        name="物体缩放速度",
        description="物体缩放的速度",
        default=0.05,
        min=0.01,
        max=0.5
    )
    move_speed: FloatProperty(
        name="物体移动速度",
        description="物体移动的速度",
        default=0.1,
        min=0.01,
        max=1.0
    )
    object_rotation_speed: FloatProperty(
        name="物体旋转速度",
        description="物体旋转的速度",
        default=0.05,
        min=0.01,
        max=1.0
    )
    invert_x_axis: BoolProperty(
        name="反转X轴",
        description="反转X轴的控制方向",
        default=False
    )
    invert_y_axis: BoolProperty(
        name="反转Y轴",
        description="反转Y轴的控制方向",
        default=False
    )
    invert_z_axis: BoolProperty(
        name="反转Z轴",
        description="反转Z轴的控制方向",
        default=False
    )

    def update_enable_gamepad_control(self, context):
        if self.enable_gamepad_control:
            bpy.ops.gamepad.control('INVOKE_DEFAULT')
        else:
            # 操作器会检测到这个变化并自行取消
            pass

    enable_gamepad_control: BoolProperty(
        name="启用手柄控制",
        description="启用或禁用手柄控制",
        default=False,
        update=update_enable_gamepad_control
    )


# 主操作器
class GAMEPAD_OT_control(Operator):
    bl_idname = "gamepad.control"
    bl_label = "手柄控制"
    bl_description = "启动手柄控制"

    _timer = None
    _thread = None
    _last_error_time = 0  # 错误消息时间戳
    _last_error_message = None  # 上一次错误消息

    def modal(self, context, event):
        settings = context.scene.gamepad_settings

        # 检查线程状态
        if self._thread:
            if not self._thread.is_alive():
                # 线程已结束，说明发生了严重错误
                settings.enable_gamepad_control = False
                self.report({'WARNING'}, "手柄控制已自动关闭")
                self.cancel(context)
                return {'CANCELLED'}

            # 检查错误信息
            if self._thread.error_message:
                current_time = time.time()
                # 如果是新的错误消息或者距离上次显示超过3秒
                if (self._thread.error_message != self._last_error_message or
                        current_time - self._last_error_time > 3):
                    self.report({'WARNING'}, self._thread.error_message)
                    self._last_error_time = current_time
                    self._last_error_message = self._thread.error_message

                # 如果提示自动关闭控制，则关闭
                if "已自动关闭控制" in self._thread.error_message:
                    settings.enable_gamepad_control = False
                    self.cancel(context)
                    return {'CANCELLED'}

                # 如果提示未安装包，则关闭
                if "未安装 'inputs' 包" in self._thread.error_message:
                    settings.enable_gamepad_control = False
                    self.cancel(context)
                    return {'CANCELLED'}

        if not settings.enable_gamepad_control:
            self.cancel(context)
            return {'CANCELLED'}

        if event.type == 'TIMER':
            view3d = context.space_data.region_3d
            settings = context.scene.gamepad_settings

            self.handle_button_actions(context)

            if context.active_object and context.active_object.select_get():
                obj = context.active_object

                if abs(gamepad_state.left_stick_x) > 0.1 or abs(gamepad_state.left_stick_y) > 0.1:
                    move_speed = settings.move_speed
                    dx = gamepad_state.left_stick_x * move_speed
                    dy = -gamepad_state.left_stick_y * move_speed

                    if settings.invert_x_axis:
                        dx = -dx
                    if not settings.invert_y_axis:
                        dy = -dy

                    move_vector = mathutils.Vector((dx, dy, 0.0))
                    move_vector = view3d.view_rotation @ move_vector
                    obj.location += move_vector

                    obj.location = obj.location.copy()
                    obj.keyframe_insert(data_path='location', group="Location")

                if abs(gamepad_state.right_stick_x) > 0.1 or abs(gamepad_state.right_stick_y) > 0.1:
                    rot_speed = settings.object_rotation_speed

                    delta_rot_x = -gamepad_state.right_stick_y * rot_speed
                    delta_rot_z = -gamepad_state.right_stick_x * rot_speed

                    if settings.invert_x_axis:
                        delta_rot_x = -delta_rot_x
                    if settings.invert_z_axis:
                        delta_rot_z = -delta_rot_z

                    rot_euler = mathutils.Euler((delta_rot_x, 0, delta_rot_z), 'XYZ')
                    obj.rotation_euler.rotate(rot_euler)

                    obj.rotation_euler = obj.rotation_euler.copy()
                    obj.keyframe_insert(data_path='rotation_euler', group="Rotation")

                scale_speed = settings.scale_speed

                if gamepad_state.buttons.get('BTN_SOUTH'):
                    factor = 1.0 - scale_speed
                    obj.scale *= factor
                    obj.scale = obj.scale.copy()
                    obj.keyframe_insert(data_path='scale', group="Scale")
                if gamepad_state.buttons.get('BTN_EAST'):
                    factor = 1.0 + scale_speed
                    obj.scale *= factor
                    obj.scale = obj.scale.copy()
                    obj.keyframe_insert(data_path='scale', group="Scale")

                obj.update_tag()
                context.view_layer.update()

            else:
                if abs(gamepad_state.left_stick_x) > 0.1 or abs(gamepad_state.left_stick_y) > 0.1:
                    pan_speed = settings.pan_speed
                    dx = gamepad_state.left_stick_x * pan_speed
                    dy = -gamepad_state.left_stick_y * pan_speed

                    if settings.invert_x_axis:
                        dx = -dx
                    if not settings.invert_y_axis:
                        dy = -dy

                    view3d.view_location += view3d.view_rotation @ mathutils.Vector((dx, dy, 0.0))

                if abs(gamepad_state.right_stick_x) > 0.1 or abs(gamepad_state.right_stick_y) > 0.1:
                    rot_speed = settings.rotation_speed
                    euler = view3d.view_rotation.to_euler()

                    delta_euler_z = gamepad_state.right_stick_x * rot_speed
                    delta_euler_x = gamepad_state.right_stick_y * rot_speed

                    if settings.invert_z_axis:
                        delta_euler_z = -delta_euler_z
                    if settings.invert_x_axis:
                        delta_euler_x = -delta_euler_x

                    euler.z += delta_euler_z
                    euler.x += delta_euler_x
                    view3d.view_rotation = euler.to_quaternion()

                zoom_speed = settings.zoom_speed
                if gamepad_state.buttons.get('BTN_SOUTH'):
                    view3d.view_distance += zoom_speed
                if gamepad_state.buttons.get('BTN_EAST'):
                    view3d.view_distance -= zoom_speed

                self.handle_dpad_view_switch(context)

            context.area.tag_redraw()

            return {'RUNNING_MODAL'}  # 改为 RUNNING_MODAL 以确保持续运行

        elif event.type == 'ESC':
            self.cancel(context)
            return {'CANCELLED'}

        return {'PASS_THROUGH'}

    def handle_button_actions(self, context):
        if gamepad_state.button_states.get('BTN_WEST') == 1:
            self.simulate_keypress(context, 'Z', ctrl=True)
            gamepad_state.button_states['BTN_WEST'] = 0

        if gamepad_state.button_states.get('BTN_NORTH') == 1:
            self.simulate_keypress(context, 'Z', ctrl=True, shift=True)
            gamepad_state.button_states['BTN_NORTH'] = 0

    def handle_dpad_view_switch(self, context):
        if gamepad_state.dpad_up == 1:
            bpy.ops.view3d.view_axis(type='TOP')
            gamepad_state.dpad_up = 0

        if gamepad_state.dpad_down == 1:
            bpy.ops.view3d.view_axis(type='FRONT')
            gamepad_state.dpad_down = 0

        if gamepad_state.dpad_left == 1:
            bpy.ops.view3d.view_axis(type='LEFT')
            gamepad_state.dpad_left = 0

        if gamepad_state.dpad_right == 1:
            bpy.ops.view3d.view_axis(type='RIGHT')
            gamepad_state.dpad_right = 0

    def simulate_keypress(self, context, key, ctrl=False, shift=False, alt=False):
        try:
            if key == 'Z' and ctrl and not shift and not alt:
                bpy.ops.ed.undo()
            elif key == 'Z' and ctrl and shift and not alt:
                bpy.ops.ed.redo()
        except Exception as e:
            if 'undo' in str(e).lower():
                self.report({'INFO'}, "没有可以撤销的操作")
            elif 'redo' in str(e).lower():
                self.report({'INFO'}, "没有可以重做的操作")
            else:
                self.report({'WARNING'}, f"操作失败: {str(e)}")

    def execute(self, context):
        if context.area.type != 'VIEW_3D':
            self.report({'WARNING'}, "激活区域必须是3D视图")
            return {'CANCELLED'}

        # 重置手柄状态
        global gamepad_state
        gamepad_state = GamepadState()

        # 开始新线程
        self._thread = GamepadThread()
        self._thread.start()

        # 设置计时器
        wm = context.window_manager
        self._timer = wm.event_timer_add(1 / 60, window=context.window)
        wm.modal_handler_add(self)

        return {'RUNNING_MODAL'}

    def cancel(self, context):
        if self._timer:
            context.window_manager.event_timer_remove(self._timer)
        if self._thread:
            self._thread.running = False
            self._thread.join(timeout=1.0)  # 添加超时

        # 重置手柄状态
        global gamepad_state
        gamepad_state = GamepadState()


# UI 面板
class GAMEPAD_PT_panel(Panel):
    bl_label = "游戏手柄控制"
    bl_idname = "GAMEPAD_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Gamepad'

    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D'

    def check_inputs_package(self):
        try:
            import inputs
            return True
        except ImportError:
            return False

    def draw(self, context):
        layout = self.layout
        settings = context.scene.gamepad_settings

        box = layout.box()
        row = box.row()
        row.prop(settings, "enable_gamepad_control")

        # 检查 inputs 包是否安装
        inputs_available = self.check_inputs_package()

        if not inputs_available:
            box.label(text="请安装 'inputs' 包", icon='ERROR')
            box.label(text="pip install inputs", icon='CONSOLE')
            return

        # 如果 inputs 包已安装，显示其他设置
        if settings.enable_gamepad_control:
            box = layout.box()
            box.label(text="视角控制设置:", icon='VIEW3D')
            box.prop(settings, "pan_speed")
            box.prop(settings, "rotation_speed")
            box.prop(settings, "zoom_speed")

            box = layout.box()
            box.label(text="物体控制设置:", icon='OBJECT_DATA')
            box.prop(settings, "scale_speed")
            box.prop(settings, "move_speed")
            box.prop(settings, "object_rotation_speed")

            box = layout.box()
            box.label(text="轴向设置:", icon='ORIENTATION_GIMBAL')
            box.prop(settings, "invert_x_axis")
            box.prop(settings, "invert_y_axis")
            box.prop(settings, "invert_z_axis")

            # 添加控制说明
            help_box = layout.box()
            help_box.label(text="控制说明:", icon='HELP')
            col = help_box.column(align=True)
            col.label(text="左摇杆: 平移/物体移动")
            col.label(text="右摇杆: 旋转")
            col.label(text="A键(BTN_SOUTH): 放大/缩小")
            col.label(text="B键(BTN_EAST): 缩小/放大")
            col.label(text="X键(BTN_WEST): 撤销")
            col.label(text="Y键(BTN_NORTH): 重做")
            col.label(text="方向键: 切换视图")

classes = (
    GamepadSettings,
    GAMEPAD_OT_control,
    GAMEPAD_PT_panel,
)


def safe_register():
    """安全注册所有类"""
    try:
        # 注册属性组
        if not hasattr(bpy.types.Scene, "gamepad_settings"):
            bpy.utils.register_class(GamepadSettings)
            bpy.types.Scene.gamepad_settings = PointerProperty(type=GamepadSettings)

        # 注册操作器和面板
        bpy.utils.register_class(GAMEPAD_OT_control)
        bpy.utils.register_class(GAMEPAD_PT_panel)

        return True
    except Exception as e:
        print(f"游戏手柄插件注册失败: {str(e)}")
        return False


def safe_unregister():
    """安全注销所有类"""
    try:
        # 注销操作器和面板
        bpy.utils.unregister_class(GAMEPAD_PT_panel)
        bpy.utils.unregister_class(GAMEPAD_OT_control)

        # 注销属性组
        if hasattr(bpy.types.Scene, "gamepad_settings"):
            bpy.utils.unregister_class(GamepadSettings)
            del bpy.types.Scene.gamepad_settings

    except Exception as e:
        print(f"游戏手柄插件注销失败: {str(e)}")


def register():
    """插件注册入口点"""
    if not safe_register():
        # 如果注册失败，确保完全清理
        safe_unregister()
        return {'CANCELLED'}
    return {'FINISHED'}


def unregister():
    """插件注销入口点"""
    safe_unregister()


if __name__ == "__main__":
    register()