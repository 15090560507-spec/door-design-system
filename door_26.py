"""
西州将军铜门 - 生产下单系统 (Pro Dashboard 高级版 - 语法修复纯净版)
- 全新横向三栏看板布局，极简 Apple/iOS 质感 UI，全屏无滑动沉浸式操作。
- 完全保留原版所有 ezdxf 绘图功能和扣减计算逻辑。
- 修复了此前因强行压缩代码行数导致的 Python SyntaxError (分号后接 if 语句) 问题。
"""
import sys
import os
import streamlit as st
import ezdxf  
import io
import datetime
import math
import re
import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

# 兼容 PyInstaller 打包后的路径
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(base_path, 'data')
os.makedirs(DATA_DIR, exist_ok=True)

# ===================== 数据文件路径 =====================
HISTORY_FILE = os.path.join(DATA_DIR, 'order_history.json')
CUSTOM_OPTIONS_FILE = os.path.join(DATA_DIR, 'custom_options.json')

# ===================== 核心配置 =====================
@dataclass
class Config:
    HINGE_TYPES: Dict[str, str] = field(default_factory=lambda: {
        "葫芦头合页": "hlt", "可拆卸合页": "kcx", "暗合页": "暗合页块",
        "明合页暗装": "明合页暗装块", "明合页": "明合页块"
    })
    BRIGHT_HINGE_TYPES: List[str] = field(default_factory=lambda: ["明合页"])
    HINGE_CONFIG: Dict[str, int] = field(default_factory=lambda: {
        "first_offset": 200, "second_offset": 200, "subsequent_spacing": 360, "min_clearance": 50
    })
    MATERIAL_OPTIONS: List[str] = field(default_factory=lambda: [
        "0.8的不锈钢镀铜", "1.0的不锈钢镀铜", "1.2的不锈钢镀铜", "0.8的纯铜", "1.0的纯铜", "1.2的纯铜", "纯铝"
    ])
    HANDLE_OPTIONS: List[str] = field(default_factory=lambda: [
        "标配拉手", "铝雕拉手", "铝雕滑盖拉手", "铝雕长拉手", "自制长拉手", "背包拉手"
    ])
    LOCK_OPTIONS: List[str] = field(default_factory=lambda: [
        "标准锁体", "防盗锁体", "霸王锁体", "快装锁体"
    ])

CONFIG = Config()

# ===================== 管理类 =====================
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
        return list(dict.fromkeys(custom + CONFIG.MATERIAL_OPTIONS.copy()))

    def get_all_handles(self):
        custom = self.load().get("handles", [])
        return list(dict.fromkeys(custom + CONFIG.HANDLE_OPTIONS.copy()))

    def get_all_hinges(self):
        custom = self.load().get("hinges", [])
        return list(dict.fromkeys(custom + list(CONFIG.HINGE_TYPES.keys())))

# ===================== 尺寸计算核心 =====================
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
        return int(dw - left - right), int(dh - top - th)

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
        return int(max(300, light_w + left + right)), int(max(600, light_h + top + th))

# ===================== 云端绘图类 =====================
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
        if self.hinge_block_name not in self.doc.blocks:
            block = self.doc.blocks.new(name=self.hinge_block_name)
            block.add_lwpolyline([(-5, -40), (5, -40), (5, 40), (-5, 40)], close=True)

    def batch_add_layers(self, layers_dict):
        for name, color in layers_dict.items():
            if name not in self.doc.layers:
                self.doc.layers.add(name, color=color)
        self.update_progress("创建图层完成")

    def draw_poly(self, points, layer, closed=True):
        self.ms.add_lwpolyline(points, close=closed, dxfattribs={'layer': layer})

    def draw_line(self, p1, p2, layer):
        self.ms.add_line(p1, p2, dxfattribs={'layer': layer})

    def draw_dim(self, p1, p2, text_pos, rotation, layer, text_override=""):
        dimstyle = "23231" if "23231" in self.doc.dimstyles else "Standard"
        dim = self.ms.add_linear_dim(
            base=text_pos,
            p1=p1,
            p2=p2,
            angle=math.degrees(rotation),
            text=text_override if text_override else "<>",
            dimstyle=dimstyle,
            dxfattribs={'layer': layer}
        )
        dim.render()

    def draw_text(self, text_str, pos, height, layer):
        self.ms.add_text(text_str, dxfattribs={'layer': layer, 'height': height}).set_placement(pos)

    def insert_hinge_block(self, insert_point, layer="A-DOOR-FRAME"):
        self.ms.add_blockref(self.hinge_block_name, insert_point, dxfattribs={'layer': layer})

    def insert_custom_block(self, block_name, insert_point, layer="A-DOOR-PANEL"):
        if block_name not in self.doc.blocks:
            block = self.doc.blocks.new(name=block_name)
            block.add_lwpolyline([(-15, -150), (15, -150), (15, 150), (-15, 150)], close=True)
        self.ms.add_blockref(block_name, insert_point, dxfattribs={'layer': layer})

# ===================== 批量文本解析 =====================
def parse_batch_text(text: str) -> Dict[str, Any]:
    result = {}
    if not text.strip():
        return result
    text = text.strip().replace("\n", "").replace(" ", "")
    
    dhdw_match = re.search(r"订货单位([^，；。\d]+)", text)
    if dhdw_match:
        result["dhdw"] = dhdw_match.group(1).strip()
        
    gdmc_match = re.search(r"工地名称([^，；。\d外包套洞口宽拉手]+)", text)
    if gdmc_match:
        result["gdmc"] = gdmc_match.group(1).strip()
        
    mat_match = re.search(r"(\d+\.?\d*的不锈钢镀铜|\d+\.?\d*的纯铜|\d+\.?\d*的纯铝)", text)
    if mat_match:
        result["zzcl"] = mat_match.group(1).strip()
    else:
        m2 = re.search(r"制作材料[:=]([^,；;]+)", text)
        if m2:
            result["zzcl"] = m2.group(1).strip()
            
    if re.search(r"\d+\.?\d*#色", text):
        result["ys"] = "红古铜"
    else:
        ys1 = re.search(r"(红古铜|黄古铜|古铜|拉丝金|拉丝银)", text)
        if ys1:
            result["ys"] = ys1.group(1).strip()
        else:
            ys2 = re.search(r"颜色[:=]([^,；;]+)", text)
            if ys2:
                result["ys"] = ys2.group(1).strip()
                
    zmls = re.search(r"(标配拉手|铝雕拉手|铝雕滑盖拉手|铝雕长拉手|自制长拉手)", text)
    if zmls:
        result["zmls"] = zmls.group(1).strip()
    else:
        zm2 = re.search(r"正面拉手[:=]([^,；;]+)", text)
        if zm2:
            result["zmls"] = zm2.group(1).strip()
            
    fmls = re.search(r"反面拉手[:=]([^,；;]+)", text)
    if fmls:
        result["fmls"] = fmls.group(1).strip()
        
    if "单门" in text:
        result["door_type"] = "单门"
    elif "对开门" in text:
        result["door_type"] = "对开门"
    elif "子母门" in text:
        result["door_type"] = "子母门"
        m = re.search(r"母门宽度[:=](\d+)mm?", text)
        if m:
            result["mother_door_width"] = int(m.group(1))
    elif "折叠四开门" in text:
        result["door_type"] = "折叠四开门"
        m = re.search(r"中门宽度[:=](\d+)mm?", text)
        if m:
            result["mid_door_width"] = int(m.group(1))
    elif "两定两开" in text or "两定两开门" in text:
        result["door_type"] = "两定两开"
        m = re.search(r"中门宽度[:=](\d+)mm?", text)
        if m:
            result["mid_door_width"] = int(m.group(1))
        m2 = re.search(r"立柱宽度[:=]([^,；;]+)", text)
        if m2:
            result["pillar_width_str"] = m2.group(1).strip()
        if "有立柱" in text:
            result["has_pillar"] = True
        elif "无立柱" in text:
            result["has_pillar"] = False
            
    if "内右开" in text:
        result["sel_nk"] = "内开"
        result["sel_kx"] = "右开"
    elif "内左开" in text:
        result["sel_nk"] = "内开"
        result["sel_kx"] = "左开"
    elif "外右开" in text:
        result["sel_nk"] = "外开"
        result["sel_kx"] = "右开"
    elif "外左开" in text:
        result["sel_nk"] = "外开"
        result["sel_kx"] = "左开"
    elif "左开" in text:
        result["sel_kx"] = "左开"
    elif "右开" in text:
        result["sel_kx"] = "右开"
        
    if "内开" in text:
        result["sel_nk"] = "内开"
    elif "外开" in text:
        result["sel_nk"] = "外开"
        
    out_m = re.search(r"外包套[:=]?(\d+)", text)
    if out_m:
        result["has_outer"] = True
        result["trim_front_in"] = int(out_m.group(1))
    elif "无外包套" in text:
        result["has_outer"] = False
        
    in_m = re.search(r"内包套[:=]?(\d+)", text)
    if in_m:
        result["has_inner"] = True
        result["trim_back_in"] = int(in_m.group(1))
    elif "无内包套" in text:
        result["has_inner"] = False
        
    dw_dh = re.search(r"洞口宽(\d+)\*(\d+)", text)
    if dw_dh:
        result["dw"] = int(dw_dh.group(1))
        result["dh"] = int(dw_dh.group(2))
    else:
        d1 = re.search(r"洞口宽[:=](\d+)", text)
        if d1:
            result["dw"] = int(d1.group(1))
        d2 = re.search(r"洞口高[:=](\d+)", text)
        if d2:
            result["dh"] = int(d2.group(1))
            
    li_m = re.search(r"见光宽(\d+)\*(\d+)", text)
    if li_m:
        result["light_w"] = int(li_m.group(1))
        result["light_h"] = int(li_m.group(2))
        result["use_light_size"] = True
    else:
        lw = re.search(r"见光宽[:=]?(\d+)", text)
        lh = re.search(r"见光高[:=]?(\d+)", text)
        if lw and lh:
            result["light_w"] = int(lw.group(1))
            result["light_h"] = int(lh.group(1))
            result["use_light_size"] = True
            
    h1 = re.search(r"绘图员[:=]([^,；;]+)", text)
    if h1:
        result["hhxd"] = h1.group(1).strip()
        
    s1 = re.search(r"数量[:=]([^,；;]+)", text)
    if s1:
        result["sl"] = s1.group(1).strip()
        
    d1 = re.search(r"订单号[:=]([^,；;]+)", text)
    if d1:
        result["ddh"] = d1.group(1).strip()
        
    hy1 = re.search(r"合页数量[:=](\d+)个", text)
    if hy1:
        result["hysl"] = f"{hy1.group(1)}个/扇"
        
    h2 = re.search(r"(葫芦头合页|可拆卸合页|暗合页|明合页暗装|明合页)", text)
    if h2:
        result["sel_hys"] = h2.group(1).strip()
        
    l1 = re.search(r"(标准锁体|防盗锁体|霸王锁体|快装锁体)", text)
    if l1:
        result["st_val"] = l1.group(1).strip()
        
    q1 = re.search(r"墙厚[:=](\d+)", text)
    if q1:
        result["qh"] = int(q1.group(1))
        
    m1 = re.search(r"门扇厚度[:=](\d+)", text)
    if m1:
        result["mshd"] = int(m1.group(1))
        
    sm1 = re.search(r"备注[:=]([^,；;]+)", text)
    if sm1:
        result["sm"] = sm1.group(1).strip()
        
    if "气窗玻璃" in text:
        result["sel_qc"] = "玻璃"
    elif "气窗封闭" in text:
        result["sel_qc"] = "封闭"
    elif "无气窗" in text:
        result["sel_qc"] = "无"
        
    qc1 = re.search(r"气窗高度[:=](\d+)", text)
    if qc1:
        result["qc_height"] = int(qc1.group(1))
        
    if "有门楣" in text:
        result["has_mm"] = True
    elif "无门楣" in text:
        result["has_mm"] = False
        
    mm1 = re.search(r"门楣高度[:=](\d+)", text)
    if mm1:
        result["mm_height"] = int(mm1.group(1))
        
    ov1 = re.search(r"门套压框宽[:=](\d+)", text)
    if ov1:
        result["overlap"] = int(ov1.group(1))
        
    f1 = re.search(r"左框[:=]([^,；;]+)", text)
    if f1:
        result["fw_left_str"] = f1.group(1).strip()
    else:
        result["fw_left_str"] = "60/60"
        
    f2 = re.search(r"右框[:=]([^,；;]+)", text)
    if f2:
        result["fw_right_str"] = f2.group(1).strip()
    else:
        result["fw_right_str"] = "60/60"
        
    f3 = re.search(r"上框宽[:=]([^,；;]+)", text)
    if f3:
        result["fw_top_str"] = f3.group(1).strip()
    else:
        result["fw_top_str"] = "60/60"
        
    t1 = re.search(r"下槛高[:=]([^,；;]+)", text)
    if t1:
        result["th_str"] = t1.group(1).strip()
    else:
        result["th_str"] = "60/60"
        
    g1 = re.search(r"左右门缝[:=]([^,；;]+)", text)
    if g1:
        result["left_right_gap_str"] = g1.group(1).strip()
        
    g2 = re.search(r"上下门缝[:=]([^,；;]+)", text)
    if g2:
        result["top_bottom_gap_str"] = g2.group(1).strip()
        
    g3 = re.search(r"中缝隙[:=](\d+)", text)
    if g3:
        result["middle_gap"] = int(g3.group(1))
        
    p1 = re.search(r"立柱宽度[:=]([^,；;]+)", text)
    if p1:
        result["pillar_width_str"] = p1.group(1).strip()
        
    z1 = re.search(r"正面款式[:=]([^,；;]+)", text)
    if z1:
        result["zmks"] = z1.group(1).strip()
        
    fm1 = re.search(r"反面款式[:=]([^,；;]+)", text)
    if fm1:
        result["fmks"] = fm1.group(1).strip()
        
    if "高低槛" in text:
        result["threshold_type"] = "高低槛"
    elif "平底槛" in text:
        result["threshold_type"] = "平底槛"
        
    d_x = re.search(r"高低槛尺寸[:=](\d+)/(\d+)", text)
    if d_x:
        result["dxk"] = d_x.group(1).strip()
        result["gxk"] = d_x.group(2).strip()
        
    p_k = re.search(r"平底槛尺寸[:=](\d+)", text)
    if p_k:
        result["pdk"] = p_k.group(1).strip()
        
    return result

# ===================== 绘图核心函数 =====================
def draw_door_in_frame(drawer: EzdxfDrawer, view_name: str, p: Dict, is_back: bool, use_light_size: bool = False, light_w: int = 0, light_h: int = 0):
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
        offset_x = (frame_center_x - front_total_width / 2) + front_total_width + (dw + 2 * p.get('trim_back', 0)) + 300
    
    offset_y = frame_center_y

    def off(pt):
        return (pt[0] + offset_x, pt[1] + offset_y)

    drawer.draw_poly([off((0, 0)), off((left_width, 0)), off((left_width, dh)), off((0, dh))], 'A-DOOR-FRAME')
    drawer.draw_poly([off((dw - right_width, 0)), off((dw, 0)), off((dw, dh)), off((dw - right_width, dh))], 'A-DOOR-FRAME')

    qc_h = qc_height if qc_choice in ["玻璃", "封闭"] else 0
    top_frame_bottom = dh - fw_top
    
    drawer.draw_poly([off((left_width, top_frame_bottom)), off((dw - right_width, top_frame_bottom)), off((dw - right_width, dh)), off((left_width, dh))], 'A-DOOR-FRAME')
    
    if qc_h > 0:
        mid_frame_top = top_frame_bottom - qc_h
        mid_frame_bottom = mid_frame_top - fw_top
        drawer.draw_poly([off((left_width, mid_frame_bottom)), off((dw - right_width, mid_frame_bottom)), off((dw - right_width, mid_frame_top)), off((left_width, mid_frame_top))], 'A-DOOR-FRAME')
        if th > 0:
            drawer.draw_poly([off((left_width, 0)), off((dw - right_width, 0)), off((dw - right_width, th)), off((left_width, th))], 'A-DOOR-FRAME')
    else:
        if th > 0:
            drawer.draw_poly([off((left_width, 0)), off((dw - right_width, 0)), off((dw - right_width, th)), off((left_width, th))], 'A-DOOR-FRAME')

    if trim_w > 0:
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
        
        drawer.draw_poly([off((ox1, oy1)), off((ox2, oy2)), off((ox3, oy3)), off((ox4, oy4)), off((ix4, iy4)), off((ix3, iy3)), off((ix2, iy2)), off((ix1, iy1))], 'A-DOOR-TRIM')
        drawer.draw_line(off((ix2, iy2)), off((ox2, oy2)), 'A-DOOR-TRIM')
        drawer.draw_line(off((ix3, iy3)), off((ox3, oy3)), 'A-DOOR-TRIM')
        
        if has_mm and mm_height > 0:
            mm_bottom = dh - O
            mm_top = mm_bottom + mm_height
            mm_left, mm_right = ix1, ix4
            drawer.draw_poly([off((mm_left, mm_top)), off((mm_right, mm_top)), off((mm_right, mm_bottom)), off((mm_left, mm_bottom))], 'A-DOOR-TRIM')
    else:
        ox1, oy1, ox4, oy4, ox3, oy3 = 0, 0, dw, 0, dw, dh
        ix1, iy1, ix4, iy4, ix3, iy3 = 0, 0, dw, 0, dw, dh

    if qc_h > 0:
        qc_top = top_frame_bottom
        qc_bottom = top_frame_bottom - qc_h
        drawer.draw_poly([off((left_width, qc_bottom)), off((dw - right_width, qc_bottom)), off((dw - right_width, qc_top)), off((left_width, qc_top))], 'A-DOOR-FRAME')

    if qc_h > 0:
        panel_y_top = top_frame_bottom - qc_h - fw_top - top_gap
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
        drawer.draw_poly([off((panel_x1, panel_y_bot)), off((panel_x2, panel_y_bot)), off((panel_x2, panel_y_top)), off((panel_x1, panel_y_top))], 'A-DOOR-PANEL')
        panel_positions.append((panel_x1, panel_x2))
        
    elif door_type == "对开门":
        total_door_width = dw - left_width - right_width - left_gap - right_gap
        single_panel_width = (total_door_width - middle_gap) / 2
        left_panel_x1 = left_width + left_gap
        left_panel_x2 = left_panel_x1 + single_panel_width
        right_panel_x1 = left_panel_x2 + middle_gap
        right_panel_x2 = right_panel_x1 + single_panel_width
        
        drawer.draw_poly([off((left_panel_x1, panel_y_bot)), off((left_panel_x2, panel_y_bot)), off((left_panel_x2, panel_y_top)), off((left_panel_x1, panel_y_top))], 'A-DOOR-PANEL')
        drawer.draw_poly([off((right_panel_x1, panel_y_bot)), off((right_panel_x2, panel_y_bot)), off((right_panel_x2, panel_y_top)), off((right_panel_x1, panel_y_top))], 'A-DOOR-PANEL')
        panel_positions.extend([(left_panel_x1, left_panel_x2), (right_panel_x1, right_panel_x2)])
        
    elif door_type == "子母门":
        total_door_width = dw - left_width - right_width - left_gap - right_gap
        mother_width = max(500, min(mother_door_width, total_door_width - middle_gap - 100))
        son_width = total_door_width - mother_width - middle_gap
        
        is_mother_right = (is_back and door_open_dir == "左开") or (not is_back and door_open_dir == "右开")
        if is_mother_right:
            son_panel_x1 = left_width + left_gap
            son_panel_x2 = son_panel_x1 + son_width
            mother_panel_x1 = son_panel_x2 + middle_gap
            mother_panel_x2 = mother_panel_x1 + mother_width
        else:
            mother_panel_x1 = left_width + left_gap
            mother_panel_x2 = mother_panel_x1 + mother_width
            son_panel_x1 = mother_panel_x2 + middle_gap
            son_panel_x2 = son_panel_x1 + son_width
            
        drawer.draw_poly([off((son_panel_x1, panel_y_bot)), off((son_panel_x2, panel_y_bot)), off((son_panel_x2, panel_y_top)), off((son_panel_x1, panel_y_top))], 'A-DOOR-PANEL')
        drawer.draw_poly([off((mother_panel_x1, panel_y_bot)), off((mother_panel_x2, panel_y_bot)), off((mother_panel_x2, panel_y_top)), off((mother_panel_x1, panel_y_top))], 'A-DOOR-PANEL')
        panel_positions.extend([(son_panel_x1, son_panel_x2), (mother_panel_x1, mother_panel_x2)])
        
        if not is_back:
            drawer.draw_dim(off((mother_panel_x1, panel_y_bot - 100)), off((mother_panel_x2, panel_y_bot - 100)), off((mother_panel_x1 - 100, panel_y_bot - 150)), 0, 'YQ_DIM', f"母门宽 {mother_width}")
            
    elif door_type == "折叠四开门":
        total_door_width = dw - left_width - right_width - left_gap - right_gap
        mid_total_width = 2 * mid_door_width + middle_gap
        side_width = (total_door_width - mid_total_width) / 2
        lx1 = left_width + left_gap
        lx2 = lx1 + side_width
        lmx1 = lx2
        lmx2 = lmx1 + mid_door_width
        rmx1 = lmx2 + middle_gap
        rmx2 = rmx1 + mid_door_width
        rx1 = rmx2
        rx2 = rx1 + side_width
        
        drawer.draw_poly([off((lx1, panel_y_bot)), off((lx2, panel_y_bot)), off((lx2, panel_y_top)), off((lx1, panel_y_top))], 'A-DOOR-PANEL')
        drawer.draw_poly([off((lmx1, panel_y_bot)), off((lmx2, panel_y_bot)), off((lmx2, panel_y_top)), off((lmx1, panel_y_top))], 'A-DOOR-PANEL')
        drawer.draw_poly([off((rmx1, panel_y_bot)), off((rmx2, panel_y_bot)), off((rmx2, panel_y_top)), off((rmx1, panel_y_top))], 'A-DOOR-PANEL')
        drawer.draw_poly([off((rx1, panel_y_bot)), off((rx2, panel_y_bot)), off((rx2, panel_y_top)), off((rx1, panel_y_top))], 'A-DOOR-PANEL')
        
        panel_positions.extend([(lx1, lx2), (lmx1, lmx2), (rmx1, rmx2), (rx1, rx2)])
        
        if not is_back:
            drawer.draw_dim(off((lmx1, panel_y_bot - 150)), off((rmx2, panel_y_bot - 150)), off((lmx1 + mid_total_width / 2, panel_y_bot - 200)), 0, 'YQ_DIM', f"中门宽度 {mid_total_width}mm")
            
    elif door_type == "两定两开":
        total_door_width = dw - left_width - right_width - left_gap - right_gap
        pillar_total = 2 * pillar_width_front if has_pillar else 0
        mid_total_width = 2 * mid_door_width + middle_gap
        side_width = (total_door_width - mid_total_width - pillar_total) / 2
        
        lx1 = left_width + left_gap
        lx2 = lx1 + side_width
        lpx1 = lx2
        lpx2 = lpx1 + pillar_width_front if has_pillar else lpx1
        lmx1 = lpx2
        lmx2 = lmx1 + mid_door_width
        rmx1 = lmx2 + middle_gap
        rmx2 = rmx1 + mid_door_width
        rpx1 = rmx2
        rpx2 = rpx1 + pillar_width_front if has_pillar else rpx1
        rx1 = rpx2
        rx2 = rx1 + side_width
        
        drawer.draw_poly([off((lx1, panel_y_bot)), off((lx2, panel_y_bot)), off((lx2, panel_y_top)), off((lx1, panel_y_top))], 'A-DOOR-PANEL')
        if has_pillar:
            drawer.draw_poly([off((lpx1, panel_y_bot)), off((lpx2, panel_y_bot)), off((lpx2, panel_y_top)), off((lpx1, panel_y_top))], 'A-DOOR-FRAME')
        drawer.draw_poly([off((lmx1, panel_y_bot)), off((lmx2, panel_y_bot)), off((lmx2, panel_y_top)), off((lmx1, panel_y_top))], 'A-DOOR-PANEL')
        drawer.draw_poly([off((rmx1, panel_y_bot)), off((rmx2, panel_y_bot)), off((rmx2, panel_y_top)), off((rmx1, panel_y_top))], 'A-DOOR-PANEL')
        if has_pillar:
            drawer.draw_poly([off((rpx1, panel_y_bot)), off((rpx2, panel_y_bot)), off((rpx2, panel_y_top)), off((rpx1, panel_y_top))], 'A-DOOR-FRAME')
        drawer.draw_poly([off((rx1, panel_y_bot)), off((rx2, panel_y_bot)), off((rx2, panel_y_top)), off((rx1, panel_y_top))], 'A-DOOR-PANEL')
        
        panel_positions.extend([(lx1, lx2), (lmx1, lmx2), (rmx1, rmx2), (rx1, rx2)])

    # ===================== 尺寸标注 =====================
    rad90 = math.radians(90)
    
    if trim_w > 0:
        outer_left, outer_right, outer_bottom, outer_top = ox1, ox4, 0, oy3
    else:
        outer_left, outer_right, outer_bottom, outer_top = 0, dw, 0, dh
        
    dims_h = []
    if trim_w > 0:
        dims_h.append(("含包套总宽", outer_left, outer_right, -400, True, "含包套总宽 <>"))
        dims_h.append(("门套宽", ox1, ix1, -200, True, f" {trim_w}"))
        
    if use_light_size and light_w > 0 and ((nk_choice == "内开" and not is_back) or (nk_choice == "外开" and is_back)):
        dims_h.append(("见光宽", left_width + left_gap, dw - right_width - right_gap, -200, True, f"见光宽 {light_w}"))
        
    dims_h.append(("洞口宽", 0, dw, -300, True, None))

    dims_v = []
    if trim_w > 0:
        dims_v.append(("含包套总高", outer_bottom, outer_top, 400, True, "含包套总高 <>"))
        
    if has_mm and mm_height > 0 and trim_w > 0:
        dims_v.append(("门楣高度", dh - O + mm_height, dh - O, 300, True, f"门楣高度 {mm_height}"))
        
    if qc_h > 0: 
        mid_frame_top = top_frame_bottom - qc_h
        dims_v.append(("气窗上部高度", mid_frame_top, dh, 200, True, None))
        dims_v.append(("门板下部高度", 0, mid_frame_top, 200, True, None))
        
    if use_light_size and light_h > 0 and ((nk_choice == "内开" and not is_back) or (nk_choice == "外开" and is_back)):
        dims_v.append(("见光高", panel_y_bot, panel_y_top, 100, True, f"见光高 {light_h}"))
        
    dims_v.append(("洞口高", 0, dh, 300, True, None))

    for name, x1, x2, y_offset, condition, text in dims_h:
        if condition:
            drawer.draw_dim(off((x1, y_offset)), off((x2, y_offset)), off((x1 + (x2 - x1) / 2, y_offset - 50)), 0, 'YQ_DIM', text)
            
    for name, y1, y2, x_offset, condition, text in dims_v:
        if condition:
            drawer.draw_dim(off((outer_right + x_offset, y1)), off((outer_right + x_offset, y2)), off((outer_right + x_offset + 50, y1 + (y2 - y1) / 2)), rad90, 'YQ_DIM', text)
            
    drawer.draw_text(f"{view_name}", off((dw / 2 - 60, outer_top + 300)), 80, 'A-DOOR-mark')

    # ===================== 合页绘制 =====================
    hinge_ys = []
    if hys_count >= 1:
        hinge_ys.append(panel_y_bot + CONFIG.HINGE_CONFIG["first_offset"])
    if hys_count >= 2:
        hinge_ys.append(panel_y_top - CONFIG.HINGE_CONFIG["second_offset"])
        
    for i in range(2, hys_count):
        curr_y = hinge_ys[-1] - CONFIG.HINGE_CONFIG["subsequent_spacing"]
        if curr_y > panel_y_bot + CONFIG.HINGE_CONFIG["min_clearance"]:
            hinge_ys.append(curr_y)
        else:
            break

    hinge_x_list = []
    is_hinge_visible = (nk_choice == "外开" and not is_back) or (nk_choice == "内开" and is_back)
    
    if is_hinge_visible:
        if door_type == "单门":
            if (is_back and door_open_dir == "左开") or (not is_back and door_open_dir == "右开"):
                hinge_x_list.append(dw - right_width - 5)
            else:
                hinge_x_list.append(left_width + 5)
        elif door_type in ["对开门", "子母门"]:
            hinge_x_list.extend([left_width + 5, dw - right_width - 5])
        elif door_type == "折叠四开门" and len(panel_positions) >= 4:
            hinge_x_list.extend([left_width + 5, panel_positions[0][1] + 5, panel_positions[2][1] + 5, dw - right_width - 5])
        elif door_type == "两定两开" and len(panel_positions) >= 4:
            if has_pillar:
                hinge_x_list.extend([panel_positions[1][0] - 5, panel_positions[2][1] + 5])
            else:
                hinge_x_list.extend([panel_positions[0][1] + 5, panel_positions[2][1] + 5])

    for hinge_x in hinge_x_list:
        for hinge_y in hinge_ys:
            drawer.insert_hinge_block(off((hinge_x, hinge_y)))
            
    # ===================== 标配拉手绘制 =====================
    current_handle = p.get('fmls') if is_back else p.get('zmls')
    
    if current_handle == "标配拉手":
        handles_to_draw = []
        handle_y = panel_y_bot + 1000 
        
        if door_type == "单门":
            eff_dir = "右开" if (is_back and door_open_dir == "左开") else ("左开" if is_back else door_open_dir)
            if eff_dir == "左开":
                handles_to_draw.append((panel_positions[0][1] - 60, "ZBPLS"))
            else:
                handles_to_draw.append((panel_positions[0][0] + 60, "YBPLS"))
                
        elif door_type in ["对开门", "子母门"] and len(panel_positions) >= 2:
            handles_to_draw.extend([(panel_positions[0][1] - 60, "ZBPLS"), (panel_positions[1][0] + 60, "YBPLS")])
            
        elif door_type in ["折叠四开门", "两定两开"] and len(panel_positions) >= 4:
            handles_to_draw.extend([(panel_positions[1][1] - 60, "ZBPLS"), (panel_positions[2][0] + 60, "YBPLS")])
            
        for hx, hblock in handles_to_draw:
            drawer.insert_custom_block(hblock, off((hx, handle_y)), layer="A-DOOR-PANEL")

    drawer.update_progress(f"{view_name}绘制完成")

def run_integrated_system(info: Dict, checks: Dict, draw_p: Dict, progress_callback):
    try:
        progress_callback("正在启动云端图纸引擎...")
        template_path = os.path.join(base_path, "template.dxf")  
        
        if os.path.exists(template_path):
            doc = ezdxf.readfile(template_path)
        else:
            doc = ezdxf.new('R2010')
            
        ms = doc.modelspace()

        base_attrs = {
            "DHDW": info.get("DHDW", ""), "GDMC": info.get("GDMC", ""), "ZZCL": info.get("ZZCL", ""), "DHRQ": info.get("DHRQ", ""),
            "DDH": info.get("DDH", ""), "SL": info.get("SL", ""), "YS": info.get("YS", ""), "ZMLS": info.get("ZMLS", ""),
            "FMLS": info.get("FMLS", ""), "ST": info.get("ST", ""), "HYSL": info.get("HYSL", ""), "QH": info.get("QH", ""),
            "MSHD": info.get("MSHD", ""), "HHXD": info.get("HHXD", ""), "BZ": info.get("BZ", ""), "DOOR_TYPE": info.get("DOOR_TYPE", ""),
            "MOTHER_DOOR_WIDTH": info.get("MOTHER_DOOR_WIDTH", ""), "HYYS": info.get("HYYS", ""), "DXK": info.get("DXK", ""),
            "GXK": info.get("GXK", ""), "PXK": info.get("PXK", ""), "MX": info.get("MX", ""), "QC_HEIGHT": info.get("QC_HEIGHT", ""),
            "MM_HEIGHT": info.get("MM_HEIGHT", ""), "ZMKS": info.get("ZMKS", "按图"), "FMKS": info.get("FMKS", "按图"),
        }
        
        nk = checks.get("nk", "内开")
        kx = checks.get("kx", "右开")
        qc = checks.get("qc", "无")
        bz = checks.get("bz", "全包")
        threshold = checks.get("threshold", "高低槛")
        
        has_pillar = (checks.get("lz", "无") == "有")
        has_mm = (checks.get("mm", "无") == "有")
        
        check_attrs = {
            "OUTER": "√" if "外" in checks.get("bb", []) else "", "INNER": "√" if "内" in checks.get("bb", []) else "",
            "NK": "√" if nk == "内开" else "", "WK": "√" if nk == "外开" else "", "KX_RIGHT": "√" if kx == "右开" else "", "KX_LEFT": "√" if kx == "左开" else "",
            "LZ_YES": "√" if has_pillar else "", "LZ_NO": "" if has_pillar else "√", "MM_YES": "√" if has_mm else "", "MM_NO": "" if has_mm else "√",
            "QC_GLASS": "√" if qc == "玻璃" else "", "QC_SEAL": "√" if qc == "封闭" else "", "BZ_QB": "√" if bz == "全包" else "", "BZ_MX": "√" if bz == "木箱" else "",
            "GDK": "√" if threshold == "高低槛" else "", "PDK": "√" if threshold == "平底槛" else "",
        }
        
        all_attrs = {**base_attrs, **check_attrs}

        for insert in ms.query('INSERT'):
            to_replace = []
            for attrib in insert.attribs:
                tag = attrib.dxf.tag.strip().upper()
                if tag == "BZ":
                    ms.add_mtext(all_attrs["BZ"], dxfattribs={'insert': attrib.dxf.insert, 'char_height': attrib.dxf.height, 'layer': attrib.dxf.layer, 'style': attrib.dxf.style}).dxf.width = 1200 
                    to_replace.append(attrib)
                elif tag in all_attrs:
                    attrib.dxf.text = str(all_attrs[tag])
                elif tag == "QC_TEXT":
                    if qc == "玻璃":
                        attrib.dxf.text = "玻璃"
                    elif qc == "封闭":
                        attrib.dxf.text = "封闭"
                    else:
                        attrib.dxf.text = "无"
                elif tag == "BZ_TYPE":
                    attrib.dxf.text = "全包" if bz == "全包" else "木箱"
            
            for old_attrib in to_replace:
                old_attrib.destroy()

        drawer = EzdxfDrawer(doc, ms, CONFIG.HINGE_TYPES.get(checks.get('hys', '葫芦头合页'), "hlt"), progress_callback)
        drawer.batch_add_layers({"A-DOOR-FRAME": 4, "A-DOOR-PANEL": 2, "A-DOOR-TRIM": 1, "YQ_DIM": 3, "A-DOOR-mark": 7})

        draw_p.update({
            "door_type": info.get("DOOR_TYPE", "单门"), 
            "mother_door_width": info.get("MOTHER_DOOR_WIDTH", 600), 
            "mid_door_width": info.get("MID_DOOR_WIDTH", 400), 
            "pillar_width_str": info.get("PILLAR_WIDTH_STR", "55/70"), 
            "has_pillar": info.get("HAS_PILLAR", False), 
            "qc_height": info.get("QC_HEIGHT", 400), 
            "has_mm": info.get("HAS_MM", False), 
            "mm_height": info.get("MM_HEIGHT", 200)
        })
        
        draw_door_in_frame(drawer, "正面", draw_p, False, draw_p.get("use_light_size", False), draw_p.get("light_w", 0), draw_p.get("light_h", 0))
        draw_door_in_frame(drawer, "背面", draw_p, True, draw_p.get("use_light_size", False), draw_p.get("light_w", 0), draw_p.get("light_h", 0))

        buffer = io.StringIO()
        doc.write(buffer)
        return "图纸生成成功！", buffer
        
    except Exception as e:
        import traceback
        return f"生成出错: {str(e)}\n{traceback.format_exc()}", None

def parse_gap_str(gap_str: str, default: int = 0) -> Tuple[int, int]:
    if not gap_str.strip(): return (default, default)
    try:
        parts = gap_str.replace("，", "/").replace(",", "/").split("/")
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

# ===================== UI 深度重构 (Apple/iOS 风格极简三栏) =====================
def set_custom_style():
    st.markdown("""
    <style>
    /* 全局背景浅灰，突出卡片的纯白质感 */
    .stApp { background-color: #F5F5F7; font-family: -apple-system, BlinkMacSystemFont, sans-serif; }
    
    /* 隐藏默认 Header 和 Footer */
    header, footer, .stDeployButton { visibility: hidden !important; display: none !important; }
    
    /* 卡片容器统一样式 (通过 Container Border 拦截) */
    div[data-testid="stVerticalBlock"] > div > div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #FFFFFF !important;
        border-radius: 12px !important;
        border: none !important;
        box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04) !important;
        padding: 16px 20px !important;
        transition: box-shadow 0.2s ease;
    }
    div[data-testid="stVerticalBlock"] > div > div[data-testid="stVerticalBlockBorderWrapper"]:hover {
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08) !important;
    }
    
    /* 缩小输入框体积，文字更加紧凑精致 */
    .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] > div {
        font-size: 13px !important;
        border-radius: 8px !important;
        min-height: 34px !important;
        background-color: #F9F9FB !important;
        border: 1px solid transparent !important;
    }
    .stTextInput input:focus, .stSelectbox div[data-baseweb="select"] > div:focus-within {
        background-color: #FFFFFF !important;
        border: 1px solid #007AFF !important;
        box-shadow: 0 0 0 2px rgba(0, 122, 255, 0.15) !important;
    }
    
    /* 标签文字微缩且弱化 */
    label, .stRadio label, .stCheckbox label {
        font-size: 12px !important;
        font-weight: 500 !important;
        color: #86868B !important;
        margin-bottom: -4px !important;
    }
    
    /* 卡片标题 */
    h4 {
        font-size: 16px !important;
        font-weight: 600 !important;
        color: #1D1D1F !important;
        margin-bottom: 16px !important;
        padding-bottom: 8px !important;
        border-bottom: 1px solid #E5E5EA;
    }

    /* 按钮 iOS 蓝质感 */
    .stButton > button {
        border-radius: 10px !important;
        font-weight: 600 !important;
        letter-spacing: 0.5px;
        min-height: 44px;
    }
    .stButton > button[kind="primary"] {
        background-color: #007AFF !important;
        color: white !important;
        border: none !important;
    }
    .stButton > button[kind="primary"]:hover { background-color: #005ecb !important; }
    
    /* 减少列之间的过大间距 */
    div[data-testid="column"] { padding: 0 6px !important; }
    </style>
    """, unsafe_allow_html=True)

def init_session_state():
    defaults = {
        "dhdw": "", "gdmc": "", "ys": "", "zzcl": "0.8的不锈钢镀铜", "zmls": "标配拉手", "fmls": "背包拉手", "st_val": "标准锁体",
        "hysl": "3个/扇", "sel_hys": "暗合页", "qh": "", "mshd": 80, "sm": "", "ddh": "", "sl": "1 樘", "hhxd": "D",
        "dhrq": datetime.date.today().strftime("%Y.%m.%d"), "door_type": "单门", "mother_door_width": 600, "mid_door_width": 400,
        "has_pillar": False, "pillar_width_str": "55/70", "sel_kx": "右开", "sel_nk": "内开", "sel_qc": "无", "qc_height": 400,
        "has_mm": False, "mm_height": 200, "has_outer": True, "trim_front_in": 160, "has_inner": False, "trim_back_in": 140, 
        "dw": 900, "dh": 2100, "overlap": 20, "fw_left_str": "60/60", "fw_right_str": "60/60", "fw_top_str": "60/60", "th_str": "55/70",
        "left_right_gap_str": "0/0", "top_bottom_gap_str": "0/0", "middle_gap": 0, "use_light_size": False, "light_w": 0, "light_h": 0,
        "threshold_type": "高低槛", "dxk": "55", "gxk": "75", "pdk": "60", "zmks": "按图", "fmks": "按图", "sel_bz": "全包"
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def main():
    st.set_page_config(page_title="西州将军 | 智能看板", layout="wide")
    init_session_state()
    set_custom_style()

    history_mgr = HistoryManager(HISTORY_FILE)
    options_mgr = CustomOptionsManager(CUSTOM_OPTIONS_FILE)

    # --- 顶栏：智能识别与全局标题 ---
    top_c1, top_c2 = st.columns([7, 3])
    with top_c1:
        st.markdown("<h3 style='color:#1D1D1F; font-weight:700; margin-top:0;'>西州将军铜门 | 生产BOM与CAD排版中控台</h3>", unsafe_allow_html=True)
    with top_c2:
        batch_text = st.text_input("✨ 智能文本识别", placeholder="粘贴聊天记录，回车自动解析图纸参数...", label_visibility="collapsed")
        if batch_text:
            parsed = parse_batch_text(batch_text)  
            if parsed:
                for k, v in parsed.items(): 
                    st.session_state[k] = v
                st.rerun()

    st.write("") # 微小间距

    # ==================== 三栏主控制台 ====================
    col_left, col_mid, col_right = st.columns([1, 1, 1])

    # ---------------- 栏 1：基础与订单 ----------------
    with col_left:
        with st.container(border=True):
            st.markdown("#### 📝 订单基础信息")
            c1, c2 = st.columns(2)
            st.session_state["dhdw"] = c1.text_input("订货单位", value=st.session_state["dhdw"])
            st.session_state["gdmc"] = c2.text_input("工地/项目名称", value=st.session_state["gdmc"])
            
            c3, c4 = st.columns(2)
            st.session_state["ddh"] = c3.text_input("订单号", value=st.session_state["ddh"])
            dhrq = c4.date_input("订货日期", value=datetime.datetime.strptime(st.session_state["dhrq"], "%Y.%m.%d").date())
            st.session_state["dhrq"] = dhrq.strftime("%Y.%m.%d")
            
            c5, c6 = st.columns(2)
            st.session_state["sl"] = c5.text_input("数量(樘)", value=st.session_state["sl"])
            st.session_state["hhxd"] = c6.text_input("制单人", value=st.session_state["hhxd"])

        with st.container(border=True):
            st.markdown("#### 🎨 材质与外观")
            c1, c2 = st.columns(2)
            mats = options_mgr.get_all_materials()
            mat_idx = mats.index(st.session_state["zzcl"]) if st.session_state["zzcl"] in mats else 0
            sel_mat = c1.selectbox("制作材料", mats, index=mat_idx)
            cust_mat = c1.text_input("自定义材料", placeholder="输入覆盖", label_visibility="collapsed")
            st.session_state["zzcl"] = cust_mat if cust_mat else sel_mat
            
            st.session_state["ys"] = c2.text_input("表面颜色", value=st.session_state["ys"])

            c3, c4 = st.columns(2)
            st.session_state["zmks"] = c3.text_input("正面款式", value=st.session_state["zmks"])
            st.session_state["fmks"] = c4.text_input("反面款式", value=st.session_state["fmks"])

            c5, c6 = st.columns(2)
            st.session_state["mshd"] = c5.number_input("门扇厚度(mm)", value=st.session_state["mshd"], step=5)
            st.session_state["qh"] = c6.text_input("墙厚(mm)", value=st.session_state["qh"], placeholder="选填")
            
            st.session_state["sel_bz"] = st.radio("包装方式", ["全包", "木箱"], horizontal=True, index=["全包", "木箱"].index(st.session_state["sel_bz"]))

    # ---------------- 栏 2：核心规格与门框 ----------------
    with col_mid:
        with st.container(border=True):
            st.markdown("#### 📐 结构与开向")
            st.session_state["door_type"] = st.selectbox("门型", ["单门", "对开门", "子母门", "两定两开", "折叠四开门"], 
                                                          index=["单门", "对开门", "子母门", "两定两开", "折叠四开门"].index(st.session_state["door_type"]))
            
            c1, c2 = st.columns(2)
            st.session_state["sel_kx"] = c1.radio("左右开向", ["左开", "右开"], horizontal=True, index=["左开", "右开"].index(st.session_state["sel_kx"]))
            st.session_state["sel_nk"] = c2.radio("内外开向", ["内开", "外开"], horizontal=True, index=["内开", "外开"].index(st.session_state["sel_nk"]))

        with st.container(border=True):
            st.markdown("#### 📏 尺寸输入中心")
            st.session_state["use_light_size"] = st.checkbox("切换为见光尺寸 (内开见正/外开见背)", value=st.session_state["use_light_size"])
            c1, c2 = st.columns(2)
            if st.session_state["use_light_size"]:
                st.session_state["light_w"] = c1.number_input("见光宽(W)", value=st.session_state["light_w"], step=10)
                st.session_state["light_h"] = c2.number_input("见光高(H)", value=st.session_state["light_h"], step=10)
            else:
                st.session_state["dw"] = c1.number_input("洞口总宽(W)", value=st.session_state["dw"], step=10)
                st.session_state["dh"] = c2.number_input("洞口总高(H)", value=st.session_state["dh"], step=10)
            
            if st.session_state["door_type"] == "子母门":
                st.session_state["mother_door_width"] = st.number_input("母门单扇宽", value=st.session_state["mother_door_width"], step=10)
            elif st.session_state["door_type"] in ["折叠四开门", "两定两开"]:
                st.session_state["mid_door_width"] = st.number_input("中门单扇宽", value=st.session_state["mid_door_width"], step=10)

        with st.container(border=True):
            st.markdown("#### 🚪 边框与下槛截面")
            c1, c2 = st.columns(2)
            st.session_state["fw_left_str"] = c1.text_input("左框宽 (外/内)", value=st.session_state["fw_left_str"])
            st.session_state["fw_right_str"] = c2.text_input("右框宽 (外/内)", value=st.session_state["fw_right_str"])
            c3, c4 = st.columns(2)
            st.session_state["fw_top_str"] = c3.text_input("上框宽 (外/内)", value=st.session_state["fw_top_str"])
            
            st.session_state["threshold_type"] = c4.radio("下槛方案", ["高低槛", "平底槛"], horizontal=True, label_visibility="collapsed", index=["高低槛", "平底槛"].index(st.session_state["threshold_type"]))
            
            if st.session_state["threshold_type"] == "高低槛":
                st.session_state["th_str"] = st.text_input("下槛高度 (低/高)", value=st.session_state["th_str"])
            else:
                st.session_state["pdk"] = st.text_input("平底槛厚度(mm)", value=st.session_state["pdk"])

    # ---------------- 栏 3：五金与输出 ----------------
    with col_right:
        with st.container(border=True):
            st.markdown("#### ⚙️ 五金锁具")
            hdls = options_mgr.get_all_handles()
            c1, c2 = st.columns(2)
            zidx = hdls.index(st.session_state["zmls"]) if st.session_state["zmls"] in hdls else 0
            st.session_state["zmls"] = c1.selectbox("正面拉手", hdls, index=zidx)
            fidx = hdls.index(st.session_state["fmls"]) if st.session_state["fmls"] in hdls else 0
            st.session_state["fmls"] = c2.selectbox("反面拉手", hdls, index=fidx)

            lks = CONFIG.LOCK_OPTIONS.copy()
            lidx = lks.index(st.session_state["st_val"]) if st.session_state["st_val"] in lks else 0
            st.session_state["st_val"] = c1.selectbox("锁体类型", lks, index=lidx)
            
            hgs = options_mgr.get_all_hinges()
            hidx = hgs.index(st.session_state["sel_hys"]) if st.session_state["sel_hys"] in hgs else 0
            st.session_state["sel_hys"] = c2.selectbox("合页样式", hgs, index=hidx)
            st.session_state["hysl"] = st.selectbox("单扇合页数量", ["3个/扇", "2个/扇", "4个/扇", "5个/扇"], index=["3个/扇", "2个/扇", "4个/扇", "5个/扇"].index(st.session_state["hysl"]))

        with st.container(border=True):
            st.markdown("#### 🧩 包套与附加件")
            c1, c2, c3 = st.columns(3)
            st.session_state["has_outer"] = c1.checkbox("外包套", value=st.session_state["has_outer"])
            st.session_state["has_inner"] = c2.checkbox("内包套", value=st.session_state["has_inner"])
            if st.session_state["has_outer"] or st.session_state["has_inner"]:
                st.session_state["overlap"] = c3.number_input("压框", value=st.session_state["overlap"], step=1)
            
            c4, c5 = st.columns(2)
            if st.session_state["has_outer"]: 
                st.session_state["trim_front_in"] = c4.number_input("外包套宽", value=st.session_state["trim_front_in"], step=10)
            if st.session_state["has_inner"]: 
                st.session_state["trim_back_in"] = c5.number_input("内包套宽", value=st.session_state["trim_back_in"], step=10)

            c6, c7, c8 = st.columns(3)
            st.session_state["sel_qc"] = c6.selectbox("气窗", ["无", "玻璃", "封闭"], index=["无", "玻璃", "封闭"].index(st.session_state["sel_qc"]))
            st.session_state["has_mm"] = c7.checkbox("门楣", value=st.session_state["has_mm"])
            st.session_state["has_pillar"] = c8.checkbox("立柱", value=st.session_state["has_pillar"], disabled=(st.session_state["door_type"] != "两定两开"))

            c9, c10 = st.columns(2)
            if st.session_state["sel_qc"] != "无": 
                st.session_state["qc_height"] = c9.number_input("气窗高", value=st.session_state["qc_height"], step=10)
            if st.session_state["has_mm"]: 
                st.session_state["mm_height"] = c10.number_input("门楣高", value=st.session_state["mm_height"], step=10)
            if st.session_state["has_pillar"] and st.session_state["door_type"] == "两定两开": 
                st.session_state["pillar_width_str"] = st.text_input("立柱宽(外/内)", value=st.session_state["pillar_width_str"])

        with st.container(border=True):
            st.session_state["sm"] = st.text_area("车间生产批注", value=st.session_state["sm"], height=68, placeholder="补充图纸外的额外加工要求...")
            
            progress_placeholder = st.empty()
            
            if st.button("🚀 生成生产下料CAD排版", type="primary", use_container_width=True):
                for key in ["dhdw", "gdmc", "ys"]:
                    if st.session_state.get(key): 
                        history_mgr.add(key, st.session_state[key])

                outer_width = st.session_state["trim_front_in"] if st.session_state["has_outer"] else 0
                overlap = st.session_state.get("overlap", 20)
                note_line = f"门套宽/压墙/压框={outer_width}/{outer_width - overlap}/{overlap}mm"
                
                current_note = st.session_state.get("sm", "")
                if note_line not in current_note:
                    final_note = current_note + ("\n" + note_line if current_note.strip() else note_line)
                else:
                    final_note = current_note

                left_out, left_in = parse_dim_str(st.session_state.get("fw_left_str", "60/60"), 60, 60)
                right_out, right_in = parse_dim_str(st.session_state.get("fw_right_str", "60/60"), 60, 60)
                fw_top_out, fw_top_in = parse_dim_str(st.session_state.get("fw_top_str", "60/60"), 60, 60)
                th_out, th_in = parse_dim_str(st.session_state.get("th_str", "60/60"), 60, 60)

                if st.session_state["sel_nk"] == "内开":
                    lwf, rwf, lwb, rwb = left_in, right_in, left_out, right_out
                    ftf, ftb, thf, thb = fw_top_in, fw_top_out, th_in, th_out
                else:
                    lwf, rwf, lwb, rwb = left_out, right_out, left_in, right_in
                    ftf, ftb, thf, thb = fw_top_out, fw_top_in, th_out, th_in

                dw, dh = st.session_state["dw"], st.session_state["dh"]
                if st.session_state.get("use_light_size", False):
                    lw, lh = st.session_state.get("light_w", 0), st.session_state.get("light_h", 0)
                    if lw > 0 and lh > 0:
                        calc = DimensionCalculator({
                            "dw": dw, "dh": dh, 
                            "left_width_front": lwf, "right_width_front": rwf, 
                            "left_width_back": lwb, "right_width_back": rwb, 
                            "fw_top_front": ftf, "fw_top_back": ftb, 
                            "th_front": thf, "th_back": thb, 
                            "nk": st.session_state["sel_nk"]
                        })
                        dw, dh = calc.calculate_from_light_size(lw, lh, st.session_state["sel_nk"] == "外开")

                ttype = st.session_state.get("threshold_type", "高低槛")
                if ttype == "平底槛":
                    dxk_val, gxk_val, pdk_val = "", "", st.session_state.get("pdk", "")
                else:
                    parts = st.session_state.get("th_str", "55/70").split("/")
                    dxk_val = parts[0]
                    gxk_val = parts[-1]
                    pdk_val = ""

                dt_cn = "两定两开门" if st.session_state["door_type"] == "两定两开" else st.session_state["door_type"]
                
                info_map = {
                    "DHDW": st.session_state["dhdw"], "GDMC": st.session_state["gdmc"], "ZZCL": st.session_state["zzcl"],
                    "DHRQ": st.session_state["dhrq"], "DDH": st.session_state["ddh"], "SL": st.session_state["sl"],
                    "YS": st.session_state["ys"], "ZMLS": st.session_state["zmls"], "FMLS": st.session_state["fmls"],
                    "ST": st.session_state["st_val"], "HYSL": st.session_state["hysl"], 
                    "QH": f"{st.session_state['qh']} mm" if st.session_state['qh'] else "",
                    "MSHD": f"{st.session_state['mshd']} mm", "HHXD": st.session_state["hhxd"], "BZ": final_note,
                    "DOOR_TYPE": st.session_state["door_type"], "MOTHER_DOOR_WIDTH": st.session_state["mother_door_width"],
                    "MID_DOOR_WIDTH": st.session_state["mid_door_width"], "PILLAR_WIDTH_STR": st.session_state["pillar_width_str"],
                    "HAS_PILLAR": st.session_state["has_pillar"], "HYYS": st.session_state["sel_hys"], 
                    "DXK": dxk_val, "GXK": gxk_val, "PXK": pdk_val, 
                    "MX": dt_cn, "QC_HEIGHT": st.session_state["qc_height"] if st.session_state["sel_qc"] != "无" else 0,
                    "HAS_MM": st.session_state["has_mm"], "MM_HEIGHT": st.session_state["mm_height"] if st.session_state["has_mm"] else 0,
                    "ZMKS": st.session_state["zmks"], "FMKS": st.session_state["fmks"]
                }

                check_map = {
                    "kx": st.session_state["sel_kx"], "nk": st.session_state["sel_nk"], "qc": st.session_state["sel_qc"],
                    "lz": "有" if st.session_state["has_pillar"] else "无", "bz": st.session_state["sel_bz"],
                    "hys": st.session_state["sel_hys"], "mm": "有" if st.session_state["has_mm"] else "无",
                    "bb": (["外"] if st.session_state["has_outer"] else []) + (["内"] if st.session_state["has_inner"] else []),
                    "threshold": st.session_state["threshold_type"] 
                }

                draw_params = {
                    "dw": dw, "dh": dh, "left_width_front": lwf, "right_width_front": rwf, "left_width_back": lwb, "right_width_back": rwb,
                    "fw_top_front": ftf, "fw_top_back": ftb, "th_front": thf, "th_back": thb,
                    "trim_front": st.session_state["trim_front_in"] if st.session_state["has_outer"] else 0,
                    "trim_back": st.session_state["trim_back_in"] if st.session_state["has_inner"] else 0,
                    "overlap": overlap, "door_type": st.session_state["door_type"], "mother_door_width": st.session_state["mother_door_width"],
                    "mid_door_width": st.session_state["mid_door_width"], "pillar_width_str": st.session_state["pillar_width_str"],
                    "has_pillar": st.session_state["has_pillar"], "kx": st.session_state["sel_kx"], "nk": st.session_state["sel_nk"],
                    "qc": st.session_state["sel_qc"], "qc_height": st.session_state["qc_height"] if st.session_state["sel_qc"] != "无" else 0,
                    "has_mm": st.session_state["has_mm"], "mm_height": st.session_state["mm_height"] if st.session_state["has_mm"] else 0,
                    "hys": st.session_state["sel_hys"], "hysl": st.session_state["hysl"],
                    "left_right_gap": parse_gap_str(st.session_state["left_right_gap_str"], 0),
                    "top_bottom_gap": parse_gap_str(st.session_state["top_bottom_gap_str"], 0), "middle_gap": st.session_state["middle_gap"],
                    "use_light_size": st.session_state["use_light_size"], "light_w": st.session_state["light_w"], "light_h": st.session_state["light_h"],
                    "zmls": st.session_state["zmls"], "fmls": st.session_state["fmls"],
                }

                def progress_callback(msg):
                    progress_placeholder.markdown(f'<p style="font-size:12px; color:#86868B;">正在执行: {msg}</p>', unsafe_allow_html=True)

                result, buffer = run_integrated_system(info_map, check_map, draw_params, progress_callback)
                
                if buffer is not None:
                    progress_placeholder.empty()
                    st.success(result)
                    st.download_button(
                        label="⬇️ 点击下载 DXF 生产排版图纸",
                        data=buffer.getvalue(),
                        file_name=f"排版图纸_{st.session_state['dhdw']}_{st.session_state.get('ddh', '未命名')}.dxf",
                        mime="application/dxf",
                        type="primary",
                        use_container_width=True
                    )
                else:
                    progress_placeholder.empty()
                    st.error(result)

if __name__ == "__main__":
    main()
