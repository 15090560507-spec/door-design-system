"""
西州将军铜门 - 生产下单系统 (云端无损平替版)
- 完全保留原版所有功能、计算逻辑和 UI 界面。
- 底层平滑切换为 ezdxf，完美支持 Streamlit Cloud 部署下载。
"""
import sys
import os

# 兼容 PyInstaller 打包后的路径
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(base_path, 'data')
os.makedirs(DATA_DIR, exist_ok=True)

import streamlit as st
import ezdxf  # 核心替换：使用 ezdxf 替代 win32com
import io
import datetime
import math
import re
import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

# ===================== 数据文件路径 =====================
HISTORY_FILE = os.path.join(DATA_DIR, 'order_history.json')
CUSTOM_OPTIONS_FILE = os.path.join(DATA_DIR, 'custom_options.json')


# ===================== 核心配置 =====================
@dataclass
class Config:
    HINGE_TYPES: Dict[str, str] = field(default_factory=lambda: {
        "葫芦头合页": "hlt",
        "可拆卸合页": "kcx",
        "暗合页": "暗合页块",
        "明合页暗装": "明合页暗装块",
        "明合页": "明合页块"
    })
    BRIGHT_HINGE_TYPES: List[str] = field(default_factory=lambda: ["明合页"])
    HINGE_CONFIG: Dict[str, int] = field(default_factory=lambda: {
        "first_offset": 200,
        "second_offset": 200,
        "subsequent_spacing": 360,
        "min_clearance": 50
    })
    MATERIAL_OPTIONS: List[str] = field(default_factory=lambda: [
        "0.8的不锈钢镀铜", "1.0的不锈钢镀铜", "1.2的不锈钢镀铜",
        "0.8的纯铜", "1.0的纯铜", "1.2的纯铜", "纯铝"
    ])
    HANDLE_OPTIONS: List[str] = field(default_factory=lambda: [
        "标配拉手", "铝雕拉手", "铝雕滑盖拉手", "铝雕长拉手", "自制长拉手", "背包拉手"
    ])
    LOCK_OPTIONS: List[str] = field(default_factory=lambda: [
        "标准锁体", "防盗锁体", "霸王锁体", "快装锁体"
    ])


CONFIG = Config()


# ===================== 管理类 (保持不变) =====================
class HistoryManager:
    def __init__(self, file_path):
        self.file_path = file_path

    def load(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {"dhdw": [], "gdmc": [], "ys": []}
        return {"dhdw": [], "gdmc": [], "ys": []}

    def save(self, history):
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except:
            pass

    def add(self, field, value):
        if not value.strip():
            return
        history = self.load()
        if field not in history:
            history[field] = []
        if value not in history[field]:
            history[field].insert(0, value)
            history[field] = history[field][:20]
        self.save(history)


class CustomOptionsManager:
    def __init__(self, file_path):
        self.file_path = file_path

    def load(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {"materials": [], "handles": [], "hinges": []}
        return {"materials": [], "handles": [], "hinges": []}

    def save(self, options):
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(options, f, ensure_ascii=False, indent=2)
        except:
            pass

    def add_material(self, value):
        self._add("materials", value)

    def add_handle(self, value):
        self._add("handles", value)

    def add_hinge(self, value):
        self._add("hinges", value)

    def _add(self, key, value):
        if not value.strip():
            return
        options = self.load()
        if key not in options:
            options[key] = []
        if value not in options[key]:
            options[key].insert(0, value)
            options[key] = options[key][:30]
        self.save(options)

    def get_all_materials(self):
        custom = self.load().get("materials", [])
        base = CONFIG.MATERIAL_OPTIONS.copy()
        result = []
        for item in custom:
            if item not in result: result.append(item)
        for item in base:
            if item not in result: result.append(item)
        return result

    def get_all_handles(self):
        custom = self.load().get("handles", [])
        base = CONFIG.HANDLE_OPTIONS.copy()
        result = []
        for item in custom:
            if item not in result: result.append(item)
        for item in base:
            if item not in result: result.append(item)
        return result

    def get_all_hinges(self):
        custom = self.load().get("hinges", [])
        base = list(CONFIG.HINGE_TYPES.keys())
        result = []
        for item in custom:
            if item not in result: result.append(item)
        for item in base:
            if item not in result: result.append(item)
        return result


# ===================== 尺寸计算核心 (保持不变) =====================
class DimensionCalculator:
    def __init__(self, params: Dict[str, Any]):
        self.p = params

    def calculate_light_size(self, is_back: bool = False) -> Tuple[int, int]:
        dw = self.p['dw']
        dh = self.p['dh']
        is_external = self.p.get('nk', '内开') == '外开'
        if is_back:
            if is_external:
                left = self.p.get('left_width_back', 0)
                right = self.p.get('right_width_back', 0)
                top = self.p.get('fw_top_back', 55)
                th = self.p.get('th_back', 55)
            else:
                left = self.p.get('left_width_front', 0)
                right = self.p.get('right_width_front', 0)
                top = self.p.get('fw_top_front', 55)
                th = self.p.get('th_front', 55)
        else:
            if not is_external:
                left = self.p.get('left_width_front', 0)
                right = self.p.get('right_width_front', 0)
                top = self.p.get('fw_top_front', 55)
                th = self.p.get('th_front', 55)
            else:
                left = self.p.get('left_width_front', 0)
                right = self.p.get('right_width_front', 0)
                top = self.p.get('fw_top_front', 55)
                th = self.p.get('th_front', 55)
        light_w = dw - left - right
        light_h = dh - top - th
        return int(light_w), int(light_h)

    def calculate_from_light_size(self, light_w: int, light_h: int, is_back: bool = False) -> Tuple[int, int]:
        is_external = self.p.get('nk', '内开') == '外开'
        if is_back:
            if is_external:
                left = self.p.get('left_width_back', 0)
                right = self.p.get('right_width_back', 0)
                top = self.p.get('fw_top_back', 55)
                th = self.p.get('th_back', 55)
            else:
                left = self.p.get('left_width_front', 0)
                right = self.p.get('right_width_front', 0)
                top = self.p.get('fw_top_front', 55)
                th = self.p.get('th_front', 55)
        else:
            if not is_external:
                left = self.p.get('left_width_front', 0)
                right = self.p.get('right_width_front', 0)
                top = self.p.get('fw_top_front', 55)
                th = self.p.get('th_front', 55)
            else:
                left = self.p.get('left_width_front', 0)
                right = self.p.get('right_width_front', 0)
                top = self.p.get('fw_top_front', 55)
                th = self.p.get('th_front', 55)
        dw = light_w + left + right
        dh = light_h + top + th
        return int(max(300, dw)), int(max(600, dh))


# ===================== 云端绘图类 (替换 win32com) =====================
class EzdxfDrawer:
    def __init__(self, doc, ms, hinge_block_name, progress_callback=None):
        self.doc = doc
        self.ms = ms
        self.hinge_block_name = hinge_block_name
        self.progress_callback = progress_callback or (lambda x: None)
        self.update_progress("初始化云端绘图环境...")
        self._setup_hinge_block()

    def update_progress(self, msg):
        self.progress_callback(msg)

    def _setup_hinge_block(self):
        # 确保图纸中有合页图块，如果没有则创建一个简单的矩形图块代替
        if self.hinge_block_name not in self.doc.blocks:
            block = self.doc.blocks.new(name=self.hinge_block_name)
            points = [(-5, -40), (5, -40), (5, 40), (-5, 40)]
            block.add_lwpolyline(points, close=True)

    def batch_add_layers(self, layers_dict):
        for name, color in layers_dict.items():
            if name not in self.doc.layers:
                self.doc.layers.add(name, color=color)
        self.update_progress(f"创建 {len(layers_dict)} 个图层完成")

    def draw_poly(self, points, layer, closed=True):
        self.ms.add_lwpolyline(points, close=closed, dxfattribs={'layer': layer})

    def draw_line(self, p1, p2, layer):
        self.ms.add_line(p1, p2, dxfattribs={'layer': layer})

    def draw_dim(self, p1, p2, text_pos, rotation, layer, text_override=""):
        angle_deg = math.degrees(rotation)
        actual_text = text_override if text_override else "<>"
        
        # 🚀 核心修改：检查模板中是否有你设置好的样式，如果有就用它！
        # 如果你以后想换成截图里的 "GB-35-02"，就把这里的 23231 改掉即可
        target_style = "23231" 
        style_to_use = target_style if target_style in self.doc.dimstyles else "Standard"

        dim = self.ms.add_linear_dim(
            base=text_pos,
            p1=p1,
            p2=p2,
            angle=angle_deg,
            text=actual_text,
            dimstyle=style_to_use,  # 🚀 强制使用你的专属标注格式
            dxfattribs={'layer': layer}
        )
        dim.render()

    def draw_text(self, text_str, pos, height, layer):
        self.ms.add_text(
            text_str,
            dxfattribs={'layer': layer, 'height': height}
        ).set_placement(pos)

    def insert_hinge_block(self, insert_point, layer="A-DOOR-FRAME"):
        self.ms.add_blockref(self.hinge_block_name, insert_point, dxfattribs={'layer': layer})


# ===================== 批量文本解析 (保持不变) =====================
def parse_batch_text(text: str) -> Dict[str, Any]:
    # (解析逻辑完全保持原版不变，为了篇幅安全完整保留)
    result = {}
    if not text.strip(): return result
    text = text.strip().replace("\n", "").replace(" ", "")
    dhdw_match = re.search(r"订货单位([^，；。\d]+)", text)
    if dhdw_match: result["dhdw"] = dhdw_match.group(1).strip()
    gdmc_match = re.search(r"工地名称([^，；。\d外包套洞口宽拉手]+)", text)
    if gdmc_match: result["gdmc"] = gdmc_match.group(1).strip()
    mat_match = re.search(r"(\d+\.?\d*的不锈钢镀铜|\d+\.?\d*的纯铜|\d+\.?\d*的纯铝)", text)
    if mat_match:
        result["zzcl"] = mat_match.group(1).strip()
    else:
        mat_match = re.search(r"制作材料[:=]([^,；;]+)", text)
        if mat_match: result["zzcl"] = mat_match.group(1).strip()
    if re.search(r"\d+\.?\d*#色", text):
        result["ys"] = "红古铜"
    else:
        ys_match = re.search(r"(红古铜|黄古铜|古铜|拉丝金|拉丝银)", text)
        if ys_match:
            result["ys"] = ys_match.group(1).strip()
        else:
            ys_match = re.search(r"颜色[:=]([^,；;]+)", text)
            if ys_match: result["ys"] = ys_match.group(1).strip()
    zmls_match = re.search(r"(标配拉手|铝雕拉手|铝雕滑盖拉手|铝雕长拉手|自制长拉手)", text)
    if zmls_match:
        result["zmls"] = zmls_match.group(1).strip()
    else:
        zmls_match = re.search(r"正面拉手[:=]([^,；;]+)", text)
        if zmls_match: result["zmls"] = zmls_match.group(1).strip()
    fmls_match = re.search(r"反面拉手[:=]([^,；;]+)", text)
    if fmls_match: result["fmls"] = fmls_match.group(1).strip()
    if "单门" in text:
        result["door_type"] = "单门"
    elif "对开门" in text:
        result["door_type"] = "对开门"
    elif "子母门" in text:
        result["door_type"] = "子母门"
        mother_match = re.search(r"母门宽度[:=](\d+)mm?", text)
        if mother_match: result["mother_door_width"] = int(mother_match.group(1))
    elif "折叠四开门" in text:
        result["door_type"] = "折叠四开门"
        mid_width_match = re.search(r"中门宽度[:=](\d+)mm?", text)
        if mid_width_match: result["mid_door_width"] = int(mid_width_match.group(1))
    elif "两定两开" in text or "两定两开门" in text:
        result["door_type"] = "两定两开"
        mid_width_match = re.search(r"中门宽度[:=](\d+)mm?", text)
        if mid_width_match: result["mid_door_width"] = int(mid_width_match.group(1))
        pillar_match = re.search(r"立柱宽度[:=]([^,；;]+)", text)
        if pillar_match: result["pillar_width_str"] = pillar_match.group(1).strip()
        if "有立柱" in text:
            result["has_pillar"] = True
        elif "无立柱" in text:
            result["has_pillar"] = False
    if "内右开" in text:
        result["sel_nk"] = "内开"; result["sel_kx"] = "右开"
    elif "内左开" in text:
        result["sel_nk"] = "内开"; result["sel_kx"] = "左开"
    elif "外右开" in text:
        result["sel_nk"] = "外开"; result["sel_kx"] = "右开"
    elif "外左开" in text:
        result["sel_nk"] = "外开"; result["sel_kx"] = "左开"
    elif "左开" in text:
        result["sel_kx"] = "左开"
    elif "右开" in text:
        result["sel_kx"] = "右开"
    if "内开" in text:
        result["sel_nk"] = "内开"
    elif "外开" in text:
        result["sel_nk"] = "外开"
    outer_match = re.search(r"外包套[:=]?(\d+)", text)
    if outer_match:
        result["has_outer"] = True; result["trim_front_in"] = int(outer_match.group(1))
    elif "无外包套" in text:
        result["has_outer"] = False
    inner_match = re.search(r"内包套[:=]?(\d+)", text)
    if inner_match:
        result["has_inner"] = True; result["trim_back_in"] = int(inner_match.group(1))
    elif "无内包套" in text:
        result["has_inner"] = False
    dw_dh_match = re.search(r"洞口宽(\d+)\*(\d+)", text)
    if dw_dh_match:
        result["dw"] = int(dw_dh_match.group(1)); result["dh"] = int(dw_dh_match.group(2))
    else:
        dw_match = re.search(r"洞口宽[:=](\d+)", text)
        if dw_match: result["dw"] = int(dw_match.group(1))
        dh_match = re.search(r"洞口高[:=](\d+)", text)
        if dh_match: result["dh"] = int(dh_match.group(1))
    light_match = re.search(r"见光宽(\d+)\*(\d+)", text)
    if light_match:
        result["light_w"] = int(light_match.group(1)); result["light_h"] = int(light_match.group(2)); result[
            "use_light_size"] = True
    else:
        light_w_match = re.search(r"见光宽[:=]?(\d+)", text)
        light_h_match = re.search(r"见光高[:=]?(\d+)", text)
        if light_w_match and light_h_match:
            result["light_w"] = int(light_w_match.group(1));
            result["light_h"] = int(light_h_match.group(1));
            result["use_light_size"] = True
    hhxd_match = re.search(r"绘图员[:=]([^,；;]+)", text)
    if hhxd_match: result["hhxd"] = hhxd_match.group(1).strip()
    sl_match = re.search(r"数量[:=]([^,；;]+)", text)
    if sl_match: result["sl"] = sl_match.group(1).strip()
    ddh_match = re.search(r"订单号[:=]([^,；;]+)", text)
    if ddh_match: result["ddh"] = ddh_match.group(1).strip()
    hysl_match = re.search(r"合页数量[:=](\d+)个", text)
    if hysl_match: result["hysl"] = f"{hysl_match.group(1)}个/扇"
    hinge_match = re.search(r"(葫芦头合页|可拆卸合页|暗合页|明合页暗装|明合页)", text)
    if hinge_match: result["sel_hys"] = hinge_match.group(1).strip()
    lock_match = re.search(r"(标准锁体|防盗锁体|霸王锁体|快装锁体)", text)
    if lock_match: result["st_val"] = lock_match.group(1).strip()
    qh_match = re.search(r"墙厚[:=](\d+)", text)
    if qh_match: result["qh"] = int(qh_match.group(1))
    mshd_match = re.search(r"门扇厚度[:=](\d+)", text)
    if mshd_match: result["mshd"] = int(mshd_match.group(1))
    sm_match = re.search(r"备注[:=]([^,；;]+)", text)
    if sm_match: result["sm"] = sm_match.group(1).strip()
    if "气窗玻璃" in text:
        result["sel_qc"] = "玻璃"
    elif "气窗封闭" in text:
        result["sel_qc"] = "封闭"
    elif "无气窗" in text:
        result["sel_qc"] = "无"
    qc_h_match = re.search(r"气窗高度[:=](\d+)", text)
    if qc_h_match: result["qc_height"] = int(qc_h_match.group(1))
    if "有门楣" in text:
        result["has_mm"] = True
    elif "无门楣" in text:
        result["has_mm"] = False
    mm_height_match = re.search(r"门楣高度[:=](\d+)", text)
    if mm_height_match: result["mm_height"] = int(mm_height_match.group(1))
    overlap_match = re.search(r"门套压框宽[:=](\d+)", text)
    if overlap_match: result["overlap"] = int(overlap_match.group(1))
    fw_left_match = re.search(r"左框[:=]([^,；;]+)", text)
    if fw_left_match:
        result["fw_left_str"] = fw_left_match.group(1).strip()
    else:
        result["fw_left_str"] = "60/60"
    fw_right_match = re.search(r"右框[:=]([^,；;]+)", text)
    if fw_right_match:
        result["fw_right_str"] = fw_right_match.group(1).strip()
    else:
        result["fw_right_str"] = "60/60"
    fw_top_match = re.search(r"上框宽[:=]([^,；;]+)", text)
    if fw_top_match:
        result["fw_top_str"] = fw_top_match.group(1).strip()
    else:
        result["fw_top_str"] = "60/60"
    th_match = re.search(r"下槛高[:=]([^,；;]+)", text)
    if th_match:
        result["th_str"] = th_match.group(1).strip()
    else:
        result["th_str"] = "60/60"
    lr_gap_match = re.search(r"左右门缝[:=]([^,；;]+)", text)
    if lr_gap_match: result["left_right_gap_str"] = lr_gap_match.group(1).strip()
    tb_gap_match = re.search(r"上下门缝[:=]([^,；;]+)", text)
    if tb_gap_match: result["top_bottom_gap_str"] = tb_gap_match.group(1).strip()
    mid_gap_match = re.search(r"中缝隙[:=](\d+)", text)
    if mid_gap_match: result["middle_gap"] = int(mid_gap_match.group(1))
    pillar_match = re.search(r"立柱宽度[:=]([^,；;]+)", text)
    if pillar_match: result["pillar_width_str"] = pillar_match.group(1).strip()
    zmks_match = re.search(r"正面款式[:=]([^,；;]+)", text)
    if zmks_match: result["zmks"] = zmks_match.group(1).strip()
    fmks_match = re.search(r"反面款式[:=]([^,；;]+)", text)
    if fmks_match: result["fmks"] = fmks_match.group(1).strip()
    if "高低槛" in text:
        result["threshold_type"] = "高低槛"
    elif "平底槛" in text:
        result["threshold_type"] = "平底槛"
    dxk_match = re.search(r"高低槛尺寸[:=](\d+)/(\d+)", text)
    if dxk_match: result["dxk"] = dxk_match.group(1).strip(); result["gxk"] = dxk_match.group(2).strip()
    pdk_match = re.search(r"平底槛尺寸[:=](\d+)", text)
    if pdk_match: result["pdk"] = pdk_match.group(1).strip()
    return result


# ===================== 绘图核心函数 (仅修改调用类型，内部逻辑原封不动) =====================
def draw_door_in_frame(drawer: EzdxfDrawer, view_name: str, p: Dict, is_back: bool,
                       use_light_size: bool = False, light_w: int = 0, light_h: int = 0):
    drawer.update_progress(f"开始绘制{view_name}门体...")

    left_width = p['left_width_back'] if is_back else p['left_width_front']
    right_width = p['right_width_back'] if is_back else p['right_width_front']
    fw_top = p['fw_top_back'] if is_back else p['fw_top_front']
    th = p['th_back'] if is_back else p['th_front']
    trim_w = p['trim_back'] if is_back else p['trim_front']
    overlap = p['overlap'] if trim_w > 0 else 0
    dw, dh = p['dw'], p['dh']

    door_type = p.get('door_type', '单门')
    mother_door_width = p.get('mother_door_width', 600)
    mid_door_width = p.get('mid_door_width', 400)
    pillar_width_str = p.get('pillar_width_str', '55/70')
    has_pillar = p.get('has_pillar', False)
    door_open_dir = p.get('kx', '右开')
    nk_choice = p.get('nk', '内开')

    left_gap, right_gap = p.get('left_right_gap', (0, 0))
    top_gap, bottom_gap = p.get('top_bottom_gap', (0, 0))
    middle_gap = p.get('middle_gap', 0)

    qc_choice = p.get('qc', '无')
    qc_height = p.get('qc_height', 400)
    has_mm = p.get('has_mm', False)
    mm_height = p.get('mm_height', 200)
    hys_choice = p.get('hys', '葫芦头合页')
    hysl_str = p.get('hysl', '3个/扇')
    try:
        hys_count = int(''.join([c for c in hysl_str if c.isdigit()]))
    except:
        hys_count = 3

    frame_center_x, frame_center_y = 0.0, 0.0
    front_total_width = dw + 2 * p.get('trim_front', 0)
    if not is_back:
        offset_x = frame_center_x - front_total_width / 2
    else:
        front_offset_x = frame_center_x - front_total_width / 2
        back_total_width = dw + 2 * p.get('trim_back', 0)
        offset_x = front_offset_x + front_total_width + back_total_width + 300
    offset_y = frame_center_y

    def off(pt):
        return (pt[0] + offset_x, pt[1] + offset_y)

    drawer.update_progress(f"绘制{view_name}门框...")
    drawer.draw_poly([off((0, 0)), off((left_width, 0)), off((left_width, dh)), off((0, dh))], 'A-DOOR-FRAME')
    drawer.draw_poly([off((dw - right_width, 0)), off((dw, 0)), off((dw, dh)), off((dw - right_width, dh))],
                     'A-DOOR-FRAME')

    qc_h = qc_height if qc_choice in ["玻璃", "封闭"] else 0
    top_frame_bottom = dh - fw_top
    drawer.draw_poly([off((left_width, top_frame_bottom)), off((dw - right_width, top_frame_bottom)),
                      off((dw - right_width, dh)), off((left_width, dh))], 'A-DOOR-FRAME')
    if qc_h > 0:
        mid_frame_top = top_frame_bottom - qc_h
        mid_frame_bottom = mid_frame_top - fw_top
        drawer.draw_poly([off((left_width, mid_frame_bottom)), off((dw - right_width, mid_frame_bottom)),
                          off((dw - right_width, mid_frame_top)), off((left_width, mid_frame_top))], 'A-DOOR-FRAME')
        if th > 0:
            drawer.draw_poly([off((left_width, 0)), off((dw - right_width, 0)),
                              off((dw - right_width, th)), off((left_width, th))], 'A-DOOR-FRAME')
    else:
        if th > 0:
            drawer.draw_poly([off((left_width, 0)), off((dw - right_width, 0)),
                              off((dw - right_width, th)), off((left_width, th))], 'A-DOOR-FRAME')

    if trim_w > 0:
        drawer.update_progress(f"绘制{view_name}门套...")
        W, O = trim_w, overlap
        mm_offset = mm_height if has_mm else 0
        ix1, iy1 = O, 0
        ix2, iy2 = O, dh - O + mm_offset
        ix3, iy3 = dw - O, dh - O + mm_offset
        ix4, iy4 = dw - O, 0
        ox1, oy1 = O - W, 0
        ox2, oy2 = O - W, dh - O + W + mm_offset
        ox3, oy3 = dw - O + W, dh - O + W + mm_offset
        ox4, oy4 = dw - O + W, 0
        drawer.draw_poly([off((ox1, oy1)), off((ox2, oy2)), off((ox3, oy3)), off((ox4, oy4)),
                          off((ix4, iy4)), off((ix3, iy3)), off((ix2, iy2)), off((ix1, iy1))], 'A-DOOR-TRIM')
        drawer.draw_line(off((ix2, iy2)), off((ox2, oy2)), 'A-DOOR-TRIM')
        drawer.draw_line(off((ix3, iy3)), off((ox3, oy3)), 'A-DOOR-TRIM')
        if has_mm and mm_height > 0:
            mm_bottom = dh - O
            mm_top = mm_bottom + mm_height
            mm_left, mm_right = ix1, ix4
            drawer.draw_poly([off((mm_left, mm_top)), off((mm_right, mm_top)),
                              off((mm_right, mm_bottom)), off((mm_left, mm_bottom))], 'A-DOOR-TRIM')
    else:
        ox1, oy1, ox4, oy4, ox3, oy3 = 0, 0, dw, 0, dw, dh
        ix1, iy1, ix4, iy4, ix3, iy3 = 0, 0, dw, 0, dw, dh

    if qc_h > 0:
        qc_top = top_frame_bottom
        qc_bottom = top_frame_bottom - qc_h
        drawer.draw_poly([off((left_width, qc_bottom)), off((dw - right_width, qc_bottom)),
                          off((dw - right_width, qc_top)), off((left_width, qc_top))], 'A-DOOR-FRAME')

    if qc_h > 0:
        panel_y_top = top_frame_bottom - qc_h - fw_top - top_gap
        panel_y_bot = th + bottom_gap
    else:
        panel_y_top = dh - fw_top - top_gap
        panel_y_bot = th + bottom_gap

    pillar_width_front, pillar_width_back = 0, 0
    if door_type == "两定两开" and has_pillar and pillar_width_str:
        pillar_out, pillar_in = parse_dim_str(pillar_width_str, 55, 70)
        if nk_choice == "内开":
            pillar_width_front, pillar_width_back = pillar_in, pillar_out
        else:
            pillar_width_front, pillar_width_back = pillar_out, pillar_in

    panel_positions = []
    if door_type == "单门":
        panel_x1, panel_x2 = left_width + left_gap, dw - right_width - right_gap
        drawer.draw_poly([off((panel_x1, panel_y_bot)), off((panel_x2, panel_y_bot)), off((panel_x2, panel_y_top)),
                          off((panel_x1, panel_y_top))], 'A-DOOR-PANEL')
        panel_positions.append((panel_x1, panel_x2))

    elif door_type == "对开门":
        total_door_width = dw - left_width - right_width - left_gap - right_gap
        single_panel_width = (total_door_width - middle_gap) / 2
        left_panel_x1 = left_width + left_gap
        left_panel_x2 = left_panel_x1 + single_panel_width
        drawer.draw_poly(
            [off((left_panel_x1, panel_y_bot)), off((left_panel_x2, panel_y_bot)), off((left_panel_x2, panel_y_top)),
             off((left_panel_x1, panel_y_top))], 'A-DOOR-PANEL')
        right_panel_x1, right_panel_x2 = left_panel_x2 + middle_gap, left_panel_x2 + middle_gap + single_panel_width
        drawer.draw_poly(
            [off((right_panel_x1, panel_y_bot)), off((right_panel_x2, panel_y_bot)), off((right_panel_x2, panel_y_top)),
             off((right_panel_x1, panel_y_top))], 'A-DOOR-PANEL')
        panel_positions.extend([(left_panel_x1, left_panel_x2), (right_panel_x1, right_panel_x2)])

    elif door_type == "子母门":
        total_door_width = dw - left_width - right_width - left_gap - right_gap
        mother_width = max(500, min(mother_door_width, total_door_width - middle_gap - 100))
        son_width = total_door_width - mother_width - middle_gap
        if is_back:
            if door_open_dir == "右开":
                mother_panel_x1 = left_width + left_gap;
                mother_panel_x2 = mother_panel_x1 + mother_width
                son_panel_x1 = mother_panel_x2 + middle_gap;
                son_panel_x2 = son_panel_x1 + son_width
            else:
                son_panel_x1 = left_width + left_gap;
                son_panel_x2 = son_panel_x1 + son_width
                mother_panel_x1 = son_panel_x2 + middle_gap;
                mother_panel_x2 = mother_panel_x1 + mother_width
        else:
            if door_open_dir == "右开":
                son_panel_x1 = left_width + left_gap;
                son_panel_x2 = son_panel_x1 + son_width
                mother_panel_x1 = son_panel_x2 + middle_gap;
                mother_panel_x2 = mother_panel_x1 + mother_width
            else:
                mother_panel_x1 = left_width + left_gap;
                mother_panel_x2 = mother_panel_x1 + mother_width
                son_panel_x1 = mother_panel_x2 + middle_gap;
                son_panel_x2 = son_panel_x1 + son_width
        drawer.draw_poly(
            [off((son_panel_x1, panel_y_bot)), off((son_panel_x2, panel_y_bot)), off((son_panel_x2, panel_y_top)),
             off((son_panel_x1, panel_y_top))], 'A-DOOR-PANEL')
        drawer.draw_poly([off((mother_panel_x1, panel_y_bot)), off((mother_panel_x2, panel_y_bot)),
                          off((mother_panel_x2, panel_y_top)), off((mother_panel_x1, panel_y_top))], 'A-DOOR-PANEL')
        panel_positions.extend([(son_panel_x1, son_panel_x2), (mother_panel_x1, mother_panel_x2)])
        if not is_back: drawer.draw_dim(off((mother_panel_x1, panel_y_bot - 100)),
                                        off((mother_panel_x2, panel_y_bot - 100)),
                                        off((mother_panel_x1 - 100, panel_y_bot - 150)), 0, 'YQ_DIM',
                                        f"母门宽 {mother_width}")

    elif door_type == "折叠四开门":
        total_door_width = dw - left_width - right_width - left_gap - right_gap
        mid_total_width = 2 * mid_door_width + middle_gap
        side_width = (total_door_width - mid_total_width) / 2
        left_side_x1 = left_width + left_gap;
        left_side_x2 = left_side_x1 + side_width
        left_mid_x1 = left_side_x2;
        left_mid_x2 = left_mid_x1 + mid_door_width
        right_mid_x1 = left_mid_x2 + middle_gap;
        right_mid_x2 = right_mid_x1 + mid_door_width
        right_side_x1 = right_mid_x2;
        right_side_x2 = right_side_x1 + side_width
        drawer.draw_poly(
            [off((left_side_x1, panel_y_bot)), off((left_side_x2, panel_y_bot)), off((left_side_x2, panel_y_top)),
             off((left_side_x1, panel_y_top))], 'A-DOOR-PANEL')
        drawer.draw_poly(
            [off((left_mid_x1, panel_y_bot)), off((left_mid_x2, panel_y_bot)), off((left_mid_x2, panel_y_top)),
             off((left_mid_x1, panel_y_top))], 'A-DOOR-PANEL')
        drawer.draw_poly(
            [off((right_mid_x1, panel_y_bot)), off((right_mid_x2, panel_y_bot)), off((right_mid_x2, panel_y_top)),
             off((right_mid_x1, panel_y_top))], 'A-DOOR-PANEL')
        drawer.draw_poly(
            [off((right_side_x1, panel_y_bot)), off((right_side_x2, panel_y_bot)), off((right_side_x2, panel_y_top)),
             off((right_side_x1, panel_y_top))], 'A-DOOR-PANEL')
        panel_positions.extend([(left_side_x1, left_side_x2), (left_mid_x1, left_mid_x2), (right_mid_x1, right_mid_x2),
                                (right_side_x1, right_side_x2)])
        if not is_back:
            total_mid_width = (left_mid_x2 - left_mid_x1) + (right_mid_x2 - right_mid_x1) + middle_gap
            drawer.draw_dim(off((left_mid_x1, panel_y_bot - 150)), off((right_mid_x2, panel_y_bot - 150)),
                            off((left_mid_x1 + total_mid_width / 2, panel_y_bot - 200)), 0, 'YQ_DIM',
                            f"中门宽度 {total_mid_width}mm")

    elif door_type == "两定两开":
        total_door_width = dw - left_width - right_width - left_gap - right_gap
        mid_total_width = 2 * mid_door_width + middle_gap
        pillar_total = 2 * pillar_width_front if has_pillar else 0
        side_width = (total_door_width - mid_total_width - pillar_total) / 2
        left_side_x1 = left_width + left_gap;
        left_side_x2 = left_side_x1 + side_width
        left_pillar_x1 = left_side_x2;
        left_pillar_x2 = left_pillar_x1 + pillar_width_front if has_pillar else left_pillar_x1
        left_mid_x1 = left_pillar_x2;
        left_mid_x2 = left_mid_x1 + mid_door_width
        right_mid_x1 = left_mid_x2 + middle_gap;
        right_mid_x2 = right_mid_x1 + mid_door_width
        right_pillar_x1 = right_mid_x2;
        right_pillar_x2 = right_pillar_x1 + pillar_width_front if has_pillar else right_pillar_x1
        right_side_x1 = right_pillar_x2;
        right_side_x2 = right_side_x1 + side_width
        drawer.draw_poly(
            [off((left_side_x1, panel_y_bot)), off((left_side_x2, panel_y_bot)), off((left_side_x2, panel_y_top)),
             off((left_side_x1, panel_y_top))], 'A-DOOR-PANEL')
        if has_pillar: drawer.draw_poly(
            [off((left_pillar_x1, panel_y_bot)), off((left_pillar_x2, panel_y_bot)), off((left_pillar_x2, panel_y_top)),
             off((left_pillar_x1, panel_y_top))], 'A-DOOR-FRAME')
        drawer.draw_poly(
            [off((left_mid_x1, panel_y_bot)), off((left_mid_x2, panel_y_bot)), off((left_mid_x2, panel_y_top)),
             off((left_mid_x1, panel_y_top))], 'A-DOOR-PANEL')
        drawer.draw_poly(
            [off((right_mid_x1, panel_y_bot)), off((right_mid_x2, panel_y_bot)), off((right_mid_x2, panel_y_top)),
             off((right_mid_x1, panel_y_top))], 'A-DOOR-PANEL')
        if has_pillar: drawer.draw_poly([off((right_pillar_x1, panel_y_bot)), off((right_pillar_x2, panel_y_bot)),
                                         off((right_pillar_x2, panel_y_top)), off((right_pillar_x1, panel_y_top))],
                                        'A-DOOR-FRAME')
        drawer.draw_poly(
            [off((right_side_x1, panel_y_bot)), off((right_side_x2, panel_y_bot)), off((right_side_x2, panel_y_top)),
             off((right_side_x1, panel_y_top))], 'A-DOOR-PANEL')
        panel_positions.extend([(left_side_x1, left_side_x2), (left_mid_x1, left_mid_x2), (right_mid_x1, right_mid_x2),
                                (right_side_x1, right_side_x2)])
        if not is_back:
            total_mid_width = (left_mid_x2 - left_mid_x1) + (right_mid_x2 - right_mid_x1) + middle_gap
            drawer.draw_dim(off((left_mid_x1, panel_y_bot - 150)), off((right_mid_x2, panel_y_bot - 150)),
                            off((left_mid_x1 + total_mid_width / 2, panel_y_bot - 200)), 0, 'YQ_DIM',
                            f"中门宽度 {total_mid_width}mm")

    # ===================== 尺寸标注 =====================
    drawer.update_progress(f"绘制{view_name}尺寸标注...")
    rad90 = math.radians(90)
    if trim_w > 0:
        outer_left, outer_right, outer_bottom, outer_top = ox1, ox4, 0, oy3
    else:
        outer_left, outer_right, outer_bottom, outer_top = 0, dw, 0, dh

    dims_h = []
    if trim_w > 0:
        dims_h.append(("含包套总宽", outer_left, outer_right, -400, True, "含包套总宽 <>"))
        dims_h.append(("门套宽", ox1, ix1, -200, True, f" {trim_w}"))
    if use_light_size and light_w > 0:
        if (nk_choice == "内开" and not is_back) or (nk_choice == "外开" and is_back):
            dims_h.append(
                ("见光宽", left_width + left_gap, dw - right_width - right_gap, -200, True, f"见光宽 {light_w}"))
    dims_h.append(("洞口宽", 0, dw, -300, True, None))

    dims_v = []
    if trim_w > 0: dims_v.append(("含包套总高", outer_bottom, outer_top, 400, True, "含包套总高 <>"))
    if has_mm and mm_height > 0 and trim_w > 0: dims_v.append(
        ("门楣高度", dh - O + mm_height, dh - O, 300, True, f"门楣高度 {mm_height}"))
    if qc_h > 0: dims_v.append(("气窗高度", top_frame_bottom - qc_h, top_frame_bottom, 300, True, f"气窗高度 {qc_h}"))
    if use_light_size and light_h > 0:
        if (nk_choice == "内开" and not is_back) or (nk_choice == "外开" and is_back):
            dims_v.append(("见光高", panel_y_bot, panel_y_top, 200, True, f"见光高 {light_h}"))
    dims_v.append(("洞口高", 0, dh, 300, True, None))

    for name, x1, x2, y_offset, condition, text in dims_h:
        if condition: drawer.draw_dim(off((x1, y_offset)), off((x2, y_offset)),
                                      off((x1 + (x2 - x1) / 2, y_offset - 50)), 0, 'YQ_DIM', text)
    for name, y1, y2, x_offset, condition, text in dims_v:
        if condition: drawer.draw_dim(off((outer_right + x_offset, y1)), off((outer_right + x_offset, y2)),
                                      off((outer_right + x_offset + 50, y1 + (y2 - y1) / 2)), rad90, 'YQ_DIM', text)
    drawer.draw_text(f"{view_name}", off((dw / 2 - 60, outer_top + 300)), 80, 'A-DOOR-mark')

    # ===================== 合页绘制 =====================
    hinge_ys = []
    if hys_count >= 1: hinge_ys.append(panel_y_bot + CONFIG.HINGE_CONFIG["first_offset"])
    if hys_count >= 2: hinge_ys.append(panel_y_top - CONFIG.HINGE_CONFIG["second_offset"])
    for i in range(2, hys_count):
        curr_y = hinge_ys[-1] - CONFIG.HINGE_CONFIG["subsequent_spacing"]
        if curr_y > panel_y_bot + CONFIG.HINGE_CONFIG["min_clearance"]:
            hinge_ys.append(curr_y)
        else:
            break

    hinge_x_list = []
    if door_type == "单门":
        if (nk_choice == "外开" and not is_back) or (nk_choice == "内开" and is_back):
            hinge_x_list.append(
                left_width + 5 if door_open_dir in ["左开", "右开" if is_back else "左开"] else dw - right_width - 5)
    elif door_type == "对开门":
        if (nk_choice == "外开" and not is_back) or (nk_choice == "内开" and is_back):
            hinge_x_list.extend([left_width + 5, dw - right_width - 5])
    elif door_type == "子母门":
        if is_back:
            hinge_x_left, hinge_x_right = (left_width + 5, dw - right_width - 5) if door_open_dir == "右开" else (
                left_width + 5, dw - right_width - 5)
        else:
            hinge_x_left, hinge_x_right = (left_width + 5, dw - right_width - 5)
        if (nk_choice == "外开" and not is_back) or (nk_choice == "内开" and is_back):
            hinge_x_list.extend([hinge_x_left, hinge_x_right])
    elif door_type == "折叠四开门":
        if len(panel_positions) >= 4 and ((nk_choice == "外开" and not is_back) or (nk_choice == "内开" and is_back)):
            hinge_x_list = [left_width + 5, panel_positions[0][1] + 5, panel_positions[2][1] + 5, dw - right_width - 5]
    elif door_type == "两定两开":
        if len(panel_positions) >= 4 and ((nk_choice == "外开" and not is_back) or (nk_choice == "内开" and is_back)):
            if has_pillar:
                hinge_x_list = [panel_positions[1][0] - 5, panel_positions[2][1] + 5]
            else:
                hinge_x_list = [panel_positions[0][1] + 5, panel_positions[2][1] + 5]

    for hinge_x in hinge_x_list:
        for hinge_y in hinge_ys:
            drawer.insert_hinge_block(off((hinge_x, hinge_y)))
    drawer.update_progress(f"{view_name}门体绘制完成")


def run_integrated_system(info: Dict, checks: Dict, draw_p: Dict, progress_callback):
    try:
        progress_callback("正在启动云端图纸引擎...")

        # 尝试加载服务器上的模板文件
        template_path = os.path.join(base_path, "template.dxf")  # 🚀 把 DATA_DIR 改成了 base_path
        if os.path.exists(template_path):
            doc = ezdxf.readfile(template_path)
            progress_callback("已成功加载图框模板。")
        else:
            doc = ezdxf.new('R2010')
            progress_callback("警告: 未在 data/ 文件夹找到 template.dxf，正在白纸上绘制...")

        ms = doc.modelspace()

        # ========== 提取所有填表属性 (完全按照你原版对齐) ==========
        base_attrs = {
            "DHDW": info.get("DHDW", ""), "GDMC": info.get("GDMC", ""),
            "ZZCL": info.get("ZZCL", ""), "DHRQ": info.get("DHRQ", ""),
            "DDH": info.get("DDH", ""), "SL": info.get("SL", ""),
            "YS": info.get("YS", ""), "ZMLS": info.get("ZMLS", ""),
            "FMLS": info.get("FMLS", ""), "ST": info.get("ST", ""),
            "HYSL": info.get("HYSL", ""), "QH": info.get("QH", ""),
            "MSHD": info.get("MSHD", ""), "HHXD": info.get("HHXD", ""),
            "BZ": info.get("BZ", ""), "DOOR_TYPE": info.get("DOOR_TYPE", ""),
            "MOTHER_DOOR_WIDTH": info.get("MOTHER_DOOR_WIDTH", ""),
            "HYYS": info.get("HYYS", ""), "DXK": info.get("DXK", ""),
            "GXK": info.get("GXK", ""), "PDK": info.get("PDK", ""),
            "MX": info.get("MX", ""), "QC_HEIGHT": info.get("QC_HEIGHT", ""),
            "MM_HEIGHT": info.get("MM_HEIGHT", ""), "ZMKS": info.get("ZMKS", "按图"),
            "FMKS": info.get("FMKS", "按图"),
        }

        bb_values = checks.get("bb", [])
        has_outer = "外" in bb_values
        has_inner = "内" in bb_values
        nk = checks.get("nk", "内开")
        kx = checks.get("kx", "右开")
        qc = checks.get("qc", "无")
        has_pillar = checks.get("has_pillar", False)
        has_mm = checks.get("has_mm", False)
        bz = checks.get("bz", "全包")

        check_attrs = {
            "OUTER": "√" if has_outer else "", "INNER": "√" if has_inner else "",
            "NK": "√" if nk == "内开" else "", "WK": "√" if nk == "外开" else "",
            "KX_RIGHT": "√" if kx == "右开" else "", "KX_LEFT": "√" if kx == "左开" else "",
            "LZ_YES": "√" if has_pillar else "", "LZ_NO": "" if has_pillar else "√",
            "MM_YES": "√" if has_mm else "", "MM_NO": "" if has_mm else "√",
            "QC_GLASS": "√" if qc == "玻璃" else "", "QC_SEAL": "√" if qc == "封闭" else "",
            "BZ_QB": "√" if bz == "全包" else "", "BZ_MX": "√" if bz == "木箱" else "",
        }

        qc_text = "玻璃" if qc == "玻璃" else ("封闭" if qc == "封闭" else "无")
        all_attrs = {**base_attrs, **check_attrs}

        # 遍历图框属性并赋值 (平替原版 form_block.GetAttributes())
        for insert in ms.query('INSERT[name=="ORDER_FORM"]'):
            for attrib in insert.attribs:
                tag = attrib.dxf.tag.strip().upper()
                if tag in all_attrs:
                    attrib.dxf.text = str(all_attrs[tag])
                elif tag == "QC_TEXT":
                    attrib.dxf.text = qc_text
                elif tag == "BZ_TYPE":
                    attrib.dxf.text = "全包" if bz == "全包" else "木箱"

        # ========== 绘制图形 ==========
        selected_hinge = checks.get('hys', '葫芦头合页')
        hinge_block_name = CONFIG.HINGE_TYPES.get(selected_hinge, "hlt")
        drawer = EzdxfDrawer(doc, ms, hinge_block_name, progress_callback)
        layers = {"A-DOOR-FRAME": 4, "A-DOOR-PANEL": 2, "A-DOOR-TRIM": 1, "YQ_DIM": 3, "A-DOOR-mark": 7}
        drawer.batch_add_layers(layers)

        draw_p["door_type"] = info.get("DOOR_TYPE", "单门")
        draw_p["mother_door_width"] = info.get("MOTHER_DOOR_WIDTH", 600)
        draw_p["mid_door_width"] = info.get("MID_DOOR_WIDTH", 400)
        draw_p["pillar_width_str"] = info.get("PILLAR_WIDTH_STR", "55/70")
        draw_p["has_pillar"] = info.get("HAS_PILLAR", False)
        draw_p["qc_height"] = info.get("QC_HEIGHT", 400)
        draw_p["has_mm"] = info.get("HAS_MM", False)
        draw_p["mm_height"] = info.get("MM_HEIGHT", 200)
        use_light_size = draw_p.get("use_light_size", False)
        light_w = draw_p.get("light_w", 0)
        light_h = draw_p.get("light_h", 0)
        draw_door_in_frame(drawer, "正面", draw_p, False, use_light_size, light_w, light_h)
        draw_door_in_frame(drawer, "背面", draw_p, True, use_light_size, light_w, light_h)

        # 压缩并导出到流
        buffer = io.StringIO()
        doc.write(buffer)
        return "图纸生成成功！", buffer

    except Exception as e:
        return f"生成出错: {str(e)}", None


# ===================== 辅助函数 (保持不变) =====================
def parse_gap_str(gap_str: str, default: int = 0) -> Tuple[int, int]:
    if not gap_str.strip(): return (default, default)
    try:
        gap_str = gap_str.replace("，", "/").replace(",", "/")
        parts = gap_str.split("/")
        if len(parts) == 2:
            return (int(parts[0].strip()), int(parts[1].strip()))
        else:
            return (int(parts[0].strip()), int(parts[0].strip()))
    except:
        return (default, default)


def parse_dim_str(val_str: str, default_out: float, default_in: float) -> Tuple[float, float]:
    try:
        parts = val_str.replace('，', '/').replace(',', '/').split('/')
        if len(parts) >= 2:
            return (float(parts[0]), float(parts[1]))
        else:
            return (float(parts[0]), float(parts[0]))
    except:
        return (default_out, default_in)


# ===================== Streamlit 界面 (全盘原样保留) =====================
def set_custom_style():
    st.markdown("""
    <style>
    .stApp { max-width: 1400px; margin: 0 auto; padding: 20px 40px; background-color: #f8f9fa; }
    .stForm { background-color: #ffffff; padding: 24px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); margin-bottom: 20px; }
    .stButton>button { border-radius: 8px; padding: 8px 24px; font-weight: 500; }
    .progress-text { font-size: 12px; color: #6c757d; }
    div[data-testid="stHorizontalBlock"] > div:first-child { padding-right: 16px; }
    </style>
    """, unsafe_allow_html=True)


def init_session_state():
    defaults = {
        "dhdw": "", "gdmc": "", "ys": "", "zzcl": "0.8的不锈钢镀铜",
        "zmls": "标配拉手", "fmls": "标配拉手", "st_val": "标准锁体",
        "hysl": "3个/扇", "sel_hys": "葫芦头合页",
        "qh": "", "mshd": 80, "sm": "", "ddh": "", "sl": "1 樘", "hhxd": "D",
        "dhrq": datetime.date.today().strftime("%Y.%m.%d"),
        "door_type": "单门", "mother_door_width": 600, "mid_door_width": 400,
        "has_pillar": False, "pillar_width_str": "55/70",
        "sel_kx": "右开", "sel_nk": "内开", "sel_qc": "无", "qc_height": 400,
        "has_mm": False, "mm_height": 200, "has_outer": True, "trim_front_in": 80,
        "has_inner": False, "trim_back_in": 80, "dw": 900, "dh": 2100, "overlap": 20,
        "fw_left_str": "60/60", "fw_right_str": "60/60", "fw_top_str": "60/60", "th_str": "60/60",
        "left_right_gap_str": "0/0", "top_bottom_gap_str": "0/0", "middle_gap": 0,
        "use_light_size": False, "light_w": 0, "light_h": 0,
        "threshold_type": "高低槛", "dxk": "55", "gxk": "75", "pdk": "55",
        "zmks": "按图", "fmks": "按图"
    }
    for key, value in defaults.items():
        if key not in st.session_state: st.session_state[key] = value


def main():
    init_session_state()
    set_custom_style()
    st.set_page_config(page_title="西州将军智能下单系统", layout="wide")
    st.title("西州将军铜门 - 生产下单系统")

    history_mgr = HistoryManager(HISTORY_FILE)
    options_mgr = CustomOptionsManager(CUSTOM_OPTIONS_FILE)

    with st.container():
        st.subheader("批量参数输入")
        batch_text = st.text_area("批量输入", height=80,
                                  placeholder="示例：订货单位胡燕 工地名称曹操 0.8的不锈钢镀铜 红古铜 标配拉手 对开门内右开 洞口宽1000*2600")
        col_parse, _ = st.columns([1, 8])
        with col_parse:
            if st.button("解析填充", type="primary"):
                parsed = parse_batch_text(batch_text)
                if parsed:
                    for key, value in parsed.items():
                        if key in st.session_state: st.session_state[key] = value
                    st.success(f"已解析并填充 {len(parsed)} 个参数")
                    st.rerun()
                else:
                    st.warning("未能解析到有效参数，请检查输入格式")
    st.divider()

    st.subheader("基础信息")
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        dhdw = st.text_input("订货单位", key="dhdw", placeholder="输入订货单位")
        if dhdw: history_mgr.add("dhdw", dhdw)
    with col2:
        gdmc = st.text_input("工地名称", key="gdmc", placeholder="输入工地名称")
        if gdmc: history_mgr.add("gdmc", gdmc)
    with col3:
        ys = st.text_input("颜色", key="ys", placeholder="输入颜色")
        if ys: history_mgr.add("ys", ys)
    with col4:
        dhrq = st.date_input("订货日期", value=datetime.datetime.strptime(st.session_state["dhrq"], "%Y.%m.%d").date())
        st.session_state["dhrq"] = dhrq.strftime("%Y.%m.%d")
    with col5:
        st.text_input("绘图员", key="hhxd")

    col_b1, col_b2, col_b3, col_b4 = st.columns(4)
    with col_b1:
        st.text_input("数量 (樘)", key="sl")
    with col_b2:
        st.text_input("订单号", key="ddh")
    with col_b3:
        st.text_input("墙厚 (mm)", key="qh", placeholder="mm")
    with col_b4:
        st.number_input("门扇厚度 (mm)", value=st.session_state.get("mshd", 80), step=5, key="mshd", min_value=0)

    col_c1, col_c2, col_c3, col_c4, col_c5 = st.columns(5)
    with col_c1:
        st.text_input("正面款式", key="zmks", value=st.session_state.get("zmks", "按图"))
    with col_c2:
        st.text_input("反面款式", key="fmks", value=st.session_state.get("fmks", "按图"))

    col_d1, col_d2, col_d3, col_d4, col_d5 = st.columns(5)
    with col_d1:
        all_materials = options_mgr.get_all_materials()
        current_mat = st.session_state.get("zzcl", "0.8的不锈钢镀铜")
        mat_idx = all_materials.index(current_mat) if current_mat in all_materials else 0
        selected_mat = st.selectbox("制作材料", all_materials, index=mat_idx, key="zzcl_select")
        custom_mat = st.text_input("或自定义材料", key="zzcl_custom", placeholder="输入其他材料")
        if custom_mat and custom_mat != selected_mat: selected_mat = custom_mat
        if selected_mat not in CONFIG.MATERIAL_OPTIONS and selected_mat not in all_materials: options_mgr.add_material(
            selected_mat)
        st.session_state["zzcl"] = selected_mat
    with col_d2:
        all_handles = options_mgr.get_all_handles()
        current_zmls = st.session_state.get("zmls", "标配拉手")
        zmls_idx = all_handles.index(current_zmls) if current_zmls in all_handles else 0
        selected_zmls = st.selectbox("正面拉手", all_handles, index=zmls_idx, key="zmls_select")
        custom_zmls = st.text_input("或自定义正面拉手", key="zmls_custom", placeholder="输入其他拉手")
        if custom_zmls and custom_zmls != selected_zmls: selected_zmls = custom_zmls
        if selected_zmls not in CONFIG.HANDLE_OPTIONS and selected_zmls not in all_handles: options_mgr.add_handle(
            selected_zmls)
        st.session_state["zmls"] = selected_zmls
    with col_d3:
        current_fmls = st.session_state.get("fmls", "标配拉手")
        fmls_idx = all_handles.index(current_fmls) if current_fmls in all_handles else 0
        selected_fmls = st.selectbox("反面拉手", all_handles, index=fmls_idx, key="fmls_select")
        custom_fmls = st.text_input("或自定义反面拉手", key="fmls_custom", placeholder="输入其他拉手")
        if custom_fmls and custom_fmls != selected_fmls: selected_fmls = custom_fmls
        if selected_fmls not in CONFIG.HANDLE_OPTIONS and selected_fmls not in all_handles: options_mgr.add_handle(
            selected_fmls)
        st.session_state["fmls"] = selected_fmls
    with col_d4:
        all_locks = CONFIG.LOCK_OPTIONS.copy()
        current_lock = st.session_state.get("st_val", "标准锁体")
        lock_idx = all_locks.index(current_lock) if current_lock in all_locks else 0
        selected_lock = st.selectbox("锁体", all_locks, index=lock_idx, key="st_val_select")
        custom_lock = st.text_input("或自定义锁体", key="st_val_custom", placeholder="输入其他锁体")
        if custom_lock and custom_lock != selected_lock: selected_lock = custom_lock
        st.session_state["st_val"] = selected_lock
    with col_d5:
        hinge_opts = options_mgr.get_all_hinges()
        current_hinge = st.session_state.get("sel_hys", "葫芦头合页")
        hinge_idx = hinge_opts.index(current_hinge) if current_hinge in hinge_opts else 0
        selected_hinge = st.selectbox("合页类型", hinge_opts, index=hinge_idx, key="sel_hys_select")
        custom_hinge = st.text_input("或自定义合页", key="sel_hys_custom", placeholder="输入其他合页")
        if custom_hinge and custom_hinge != selected_hinge: selected_hinge = custom_hinge
        if selected_hinge not in CONFIG.HINGE_TYPES and selected_hinge not in hinge_opts: options_mgr.add_hinge(
            selected_hinge)
        st.session_state["sel_hys"] = selected_hinge

    col_e1, col_e2, col_e3, col_e4, col_e5 = st.columns(5)
    with col_e1:
        st.selectbox("合页数量", ["2个/扇", "3个/扇", "4个/扇", "5个/扇"], key="hysl")
    with col_e2:
        qc_choice = st.radio("气窗", ["无", "玻璃", "封闭"], horizontal=True, key="sel_qc")
        if qc_choice != "无": st.number_input("气窗高度 (mm)", value=st.session_state.get("qc_height", 400), step=10,
                                              key="qc_height")
    with col_e3:
        mm_option = st.radio("门楣", ["无", "有"], horizontal=True, key="mm_option")
        has_mm = (mm_option == "有")
        st.session_state["has_mm"] = has_mm
        if has_mm: st.number_input("门楣高度 (mm)", value=st.session_state.get("mm_height", 200), step=10,
                                   key="mm_height")
    with col_e4:
        st.radio("包装", ["全包", "木箱"], horizontal=True, key="sel_bz")

    st.write("下槛信息（仅用于图框显示）")
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        threshold_type = st.radio("下槛类型", ["高低槛", "平底槛"], horizontal=True, key="threshold_type")
    with col_f2:
        if threshold_type == "高低槛":
            dxk_gxk = st.text_input("高低槛尺寸 (低/高)", key="dxk_gxk_input",
                                    value=f"{st.session_state.get('dxk', '55')}/{st.session_state.get('gxk', '75')}")
            if "/" in dxk_gxk:
                parts = dxk_gxk.split("/")
                st.session_state["dxk"] = parts[0].strip();
                st.session_state["gxk"] = parts[1].strip()
            else:
                st.session_state["dxk"] = dxk_gxk; st.session_state["gxk"] = dxk_gxk
            st.session_state["pdk"] = ""
        else:
            pdk = st.text_input("平底槛尺寸 (mm)", key="pdk_input", value=st.session_state.get("pdk", "60"))
            st.session_state["pdk"] = pdk
            st.session_state["dxk"] = "";
            st.session_state["gxk"] = ""

    st.write("备注")
    sm = st.text_area("备注", key="sm", height=120, placeholder="可输入额外说明，支持多行")
    st.divider()

    st.subheader("绘图参数")
    col_p1, col_p2 = st.columns([1, 2])
    with col_p1:
        door_type = st.radio("门型", ["单门", "对开门", "子母门", "折叠四开门", "两定两开"], horizontal=True,
                             key="door_type")
        if door_type in ["折叠四开门", "两定两开"]: st.number_input("中门宽度 (单扇)",
                                                                    value=st.session_state.get("mid_door_width", 400),
                                                                    step=10, key="mid_door_width")
        if door_type == "子母门": st.number_input("母门宽度", value=st.session_state["mother_door_width"], step=10,
                                                  key="mother_door_width")
        if door_type == "两定两开":
            pillar_option = st.radio("立柱", ["无立柱", "有立柱"], horizontal=True, key="pillar_option")
            st.session_state["has_pillar"] = (pillar_option == "有立柱")
            if st.session_state["has_pillar"]: st.text_input("立柱宽度 (外/内)", key="pillar_width_str",
                                                             value=st.session_state.get("pillar_width_str", "55/70"))
    with col_p2:
        col_kx, col_nk = st.columns(2)
        with col_kx: st.radio("左右开", ["左开", "右开"], horizontal=True, key="sel_kx")
        with col_nk: st.radio("内外开", ["内开", "外开"], horizontal=True, key="sel_nk")

    st.write("尺寸输入")
    col_size1, col_size2, col_size3, col_size4 = st.columns([1, 1, 1, 4])
    with col_size1:
        use_light = st.checkbox("使用见光尺寸", key="use_light_size")
    with col_size2:
        if use_light:
            st.number_input("见光宽", value=st.session_state.get("light_w", 0), step=10, key="light_w")
        else:
            st.number_input("洞口宽", value=st.session_state["dw"], step=10, key="dw")
    with col_size3:
        if use_light:
            st.number_input("见光高", value=st.session_state.get("light_h", 0), step=10, key="light_h")
        else:
            st.number_input("洞口高", value=st.session_state["dh"], step=10, key="dh")
    with col_size4:
        if use_light: st.caption("见光尺寸标注位置：内开门标在正面，外开门标在背面")

    st.write("门套包边")
    col_t1, col_t2, col_t3, col_t4, col_t5 = st.columns(5)
    with col_t1:
        has_outer = st.checkbox("外包套(正面)", value=st.session_state.get("has_outer", True), key="has_outer")
    with col_t2:
        st.number_input("外包宽度", value=st.session_state.get("trim_front_in", 80), step=10, key="trim_front_in",
                        disabled=not has_outer)
    with col_t3:
        has_inner = st.checkbox("内包套(反面)", value=st.session_state.get("has_inner", False), key="has_inner")
    with col_t4:
        st.number_input("内包宽度", value=st.session_state.get("trim_back_in", 80), step=10, key="trim_back_in",
                        disabled=not has_inner)
    with col_t5:
        st.number_input("压框宽", value=st.session_state["overlap"], step=1, key="overlap")

    st.write("门框/门槛尺寸（影响绘图）")
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1:
        st.text_input("左框 (外/内)", key="fw_left_str", value=st.session_state.get("fw_left_str", "60/60"))
    with col_f2:
        st.text_input("右框 (外/内)", key="fw_right_str", value=st.session_state.get("fw_right_str", "60/60"))
    with col_f3:
        st.text_input("上框 (外/内)", key="fw_top_str", value=st.session_state.get("fw_top_str", "60/60"))
    with col_f4:
        st.text_input("下槛 (低/高)", key="th_str", value=st.session_state.get("th_str", "60/60"))

    st.divider()
    progress_placeholder = st.empty()

    if st.button("生成图纸", type="primary", use_container_width=True):
        if st.session_state.get("dhdw"): history_mgr.add("dhdw", st.session_state["dhdw"])
        if st.session_state.get("gdmc"): history_mgr.add("gdmc", st.session_state["gdmc"])
        if st.session_state.get("ys"): history_mgr.add("ys", st.session_state["ys"])

        outer_width = st.session_state["trim_front_in"] if st.session_state["has_outer"] else 0
        overlap = st.session_state.get("overlap", 20)
        press_wall = outer_width - overlap
        note_line = f"门套宽/压墙/压框={outer_width}/{press_wall}/{overlap}mm"
        spacer = "                    " # 这里是20个空格，你可以根据图纸宽度增减
        current_note = st.session_state.get("sm", "").replace('\n', spacer).replace('\r', '')
        final_note = current_note + (spacer + note_line if current_note.strip() else note_line) if note_line not in current_note else current_note

        trim_front = st.session_state["trim_front_in"] if st.session_state["has_outer"] else 0
        trim_back = st.session_state["trim_back_in"] if st.session_state["has_inner"] else 0
        left_out, left_in = parse_dim_str(st.session_state.get("fw_left_str", "60/60"), 60, 60)
        right_out, right_in = parse_dim_str(st.session_state.get("fw_right_str", "60/60"), 60, 60)
        fw_top_out, fw_top_in = parse_dim_str(st.session_state.get("fw_top_str", "60/60"), 60, 60)
        th_out, th_in = parse_dim_str(st.session_state.get("th_str", "60/60"), 60, 60)

        if st.session_state["sel_nk"] == "内开":
            left_width_front, right_width_front = left_in, right_in
            left_width_back, right_width_back = left_out, right_out
            fw_top_front, fw_top_back = fw_top_in, fw_top_out
            th_front, th_back = th_in, th_out
        else:
            left_width_front, right_width_front = left_out, right_out
            left_width_back, right_width_back = left_in, right_in
            fw_top_front, fw_top_back = fw_top_out, fw_top_in
            th_front, th_back = th_out, th_in

        dw, dh = st.session_state["dw"], st.session_state["dh"]
        if st.session_state.get("use_light_size", False):
            light_w, light_h = st.session_state.get("light_w", 0), st.session_state.get("light_h", 0)
            if light_w > 0 and light_h > 0:
                calc = DimensionCalculator({
                    "dw": dw, "dh": dh, "left_width_front": left_width_front, "right_width_front": right_width_front,
                    "left_width_back": left_width_back, "right_width_back": right_width_back,
                    "fw_top_front": fw_top_front,
                    "fw_top_back": fw_top_back, "th_front": th_front, "th_back": th_back,
                    "nk": st.session_state.get("sel_nk", "内开")
                })
                dw, dh = calc.calculate_from_light_size(light_w, light_h, st.session_state["sel_nk"] == "外开")

        threshold_type = st.session_state.get("threshold_type", "高低槛")
        if threshold_type == "高低槛":
            dxk_val, gxk_val, pdk_val = st.session_state.get("dxk", ""), st.session_state.get("gxk", ""), ""
        else:
            dxk_val, gxk_val, pdk_val = "", "", st.session_state.get("pdk", "")

        qh_display = f"{st.session_state.get('qh', '')} mm" if str(st.session_state.get("qh", "")).strip() else ""
        mshd_display = f"{st.session_state.get('mshd', 80)} mm"
        door_type_cn = {"单门": "单门", "对开门": "对开门", "子母门": "子母门", "折叠四开门": "折叠四开门",
                        "两定两开": "两定两开门"}.get(st.session_state.get("door_type", "单门"), "单门")
        qc_choice = st.session_state.get("sel_qc", "无")
        qc_height = st.session_state.get("qc_height", 400) if qc_choice != "无" else 0
        has_mm = st.session_state.get("has_mm", False)
        mm_height = st.session_state.get("mm_height", 200) if has_mm else 0

        info_map = {
            "DHDW": st.session_state.get("dhdw", ""), "GDMC": st.session_state.get("gdmc", ""),
            "ZZCL": st.session_state.get("zzcl", ""),
            "DHRQ": st.session_state.get("dhrq", ""), "DDH": st.session_state.get("ddh", ""),
            "SL": st.session_state.get("sl", ""),
            "YS": st.session_state.get("ys", ""), "ZMLS": st.session_state.get("zmls", ""),
            "FMLS": st.session_state.get("fmls", ""),
            "ST": st.session_state.get("st_val", ""), "HYSL": st.session_state.get("hysl", ""), "QH": qh_display,
            "MSHD": mshd_display, "HHXD": st.session_state.get("hhxd", ""), "BZ": final_note,
            "DOOR_TYPE": st.session_state.get("door_type", "单门"),
            "MOTHER_DOOR_WIDTH": st.session_state.get("mother_door_width", 600),
            "MID_DOOR_WIDTH": st.session_state.get("mid_door_width", 400),
            "PILLAR_WIDTH_STR": st.session_state.get("pillar_width_str", "55/70"),
            "HAS_PILLAR": st.session_state.get("has_pillar", False), "HYYS": st.session_state.get("sel_hys", ""),
            "DXK": dxk_val, "GXK": gxk_val, "PDK": pdk_val, "MX": door_type_cn, "QC_HEIGHT": qc_height,
            "HAS_MM": has_mm, "MM_HEIGHT": mm_height, "ZMKS": st.session_state.get("zmks", "按图"),
            "FMKS": st.session_state.get("fmks", "按图"),
        }

        check_map = {
            "kx": st.session_state.get("sel_kx", "右开"), "nk": st.session_state.get("sel_nk", "内开"),
            "qc": qc_choice, "lz": "有" if st.session_state.get("has_pillar", False) else "无",
            "bz": st.session_state.get("sel_bz", "全包"), "hys": st.session_state.get("sel_hys", "葫芦头合页"),
            "mm": "有" if has_mm else "无",
            "bb": (["外"] if st.session_state.get("has_outer") else []) + (
                ["内"] if st.session_state.get("has_inner") else [])
        }

        left_gap, right_gap = parse_gap_str(st.session_state.get("left_right_gap_str", "0/0"), 0)
        top_gap, bottom_gap = parse_gap_str(st.session_state.get("top_bottom_gap_str", "0/0"), 0)

        draw_params = {
            "dw": dw, "dh": dh, "left_width_front": left_width_front, "right_width_front": right_width_front,
            "left_width_back": left_width_back, "right_width_back": right_width_back, "fw_top_front": fw_top_front,
            "fw_top_back": fw_top_back, "th_front": th_front, "th_back": th_back, "trim_front": trim_front,
            "trim_back": trim_back,
            "overlap": st.session_state.get("overlap", 20), "door_type": st.session_state.get("door_type", "单门"),
            "mother_door_width": st.session_state.get("mother_door_width", 600),
            "mid_door_width": st.session_state.get("mid_door_width", 400),
            "pillar_width_str": st.session_state.get("pillar_width_str", "55/70"),
            "has_pillar": st.session_state.get("has_pillar", False),
            "kx": st.session_state.get("sel_kx", "右开"), "nk": st.session_state.get("sel_nk", "内开"), "qc": qc_choice,
            "qc_height": qc_height,
            "has_mm": has_mm, "mm_height": mm_height, "hys": st.session_state.get("sel_hys", "葫芦头合页"),
            "hysl": st.session_state.get("hysl", "3个/扇"),
            "left_right_gap": (left_gap, right_gap), "top_bottom_gap": (top_gap, bottom_gap),
            "middle_gap": st.session_state.get("middle_gap", 0),
            "use_light_size": st.session_state.get("use_light_size", False),
            "light_w": st.session_state.get("light_w", 0), "light_h": st.session_state.get("light_h", 0)
        }

        def progress_callback(msg):
            progress_placeholder.markdown(f'<p class="progress-text">正在: {msg}</p>', unsafe_allow_html=True)

        result, buffer = run_integrated_system(info_map, check_map, draw_params, progress_callback)
        if buffer is not None:
            st.success(result)
            st.download_button(
                label="⬇️ 点击下载 DXF 图纸",
                data=buffer.getvalue(),
                file_name=f"门业图纸_{st.session_state.get('ddh', '未命名')}.dxf",
                mime="application/dxf",
                type="primary",
                use_container_width=True
            )
        else:
            st.error(result)


if __name__ == "__main__":
    main()
