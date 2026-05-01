"""
西州将军铜门 - 生产协同管理系统 (SaaS 尊享视觉优化版)
- 优化：输入框增加清晰描边边界，不再模糊。
- 优化：顶部导航选中状态采用原生 Primary 渲染，状态对比极其醒目。
- 优化：上传组件支持拖拽与 Ctrl+V 快捷截图粘贴。
- 完全遵循 PEP8 标准缩进，代码清爽安全。
"""
import sys
import os
import uuid
import streamlit as st
import ezdxf  
import io
import datetime
import math
import re
import json
import base64
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

# ===================== 环境与路径配置 =====================
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(base_path, 'data')
os.makedirs(DATA_DIR, exist_ok=True)

HISTORY_FILE = os.path.join(DATA_DIR, 'order_history.json')
CUSTOM_OPTIONS_FILE = os.path.join(DATA_DIR, 'custom_options.json')
TASKS_DB_FILE = os.path.join(DATA_DIR, 'tasks_database.json')
USERS_DB_FILE = os.path.join(DATA_DIR, 'users_database.json')

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

# ===================== 数据库引擎：用户权限 =====================
class UserDatabaseManager:
    def __init__(self, file_path):
        self.file_path = file_path
        if not os.path.exists(self.file_path):
            default_users = {
                "admin": {"password": "888888", "role": "超级管理员", "name": "系统管理员", "default_module": "后台管理"},
                "A": {"password": "123", "role": "录入员", "name": "销售录入", "default_module": "图纸信息录入"},
                "B": {"password": "123", "role": "绘图员", "name": "技术深化", "default_module": "图纸绘制"},
                "C": {"password": "123", "role": "总工", "name": "审核总工", "default_module": "图纸审核"}
            }
            self.save(default_users)

    def load_all_users(self) -> Dict:
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}

    def save(self, users: Dict):
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(users, f, ensure_ascii=False, indent=2)

    def authenticate(self, uid: str, pwd: str) -> Optional[Dict]:
        users = self.load_all_users()
        if uid in users and users[uid]["password"] == pwd:
            user_info = users[uid].copy()
            user_info["uid"] = uid
            return user_info
        return None

    def add_or_update_user(self, uid: str, pwd: str, role: str, name: str):
        users = self.load_all_users()
        module_map = {
            "超级管理员": "后台管理",
            "录入员": "图纸信息录入",
            "绘图员": "图纸绘制",
            "总工": "图纸审核"
        }
        users[uid] = {
            "password": pwd,
            "role": role,
            "name": name,
            "default_module": module_map.get(role, "图纸信息录入")
        }
        self.save(users)

    def delete_user(self, uid: str):
        users = self.load_all_users()
        if uid in users and uid != "admin":
            del users[uid]
            self.save(users)

user_db = UserDatabaseManager(USERS_DB_FILE)

# ===================== 数据库引擎：任务流转 =====================
class TaskDatabaseManager:
    def __init__(self, file_path):
        self.file_path = file_path
        if not os.path.exists(self.file_path):
            self.save([])

    def load_all_tasks(self) -> List[Dict]:
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []

    def save(self, tasks: List[Dict]):
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(tasks, f, ensure_ascii=False, indent=2)

    def add_task(self, new_task: Dict):
        tasks = self.load_all_tasks()
        tasks.insert(0, new_task)
        self.save(tasks)

    def update_task(self, task_id: str, updated_data: Dict):
        tasks = self.load_all_tasks()
        for i, task in enumerate(tasks):
            if task["id"] == task_id:
                tasks[i].update(updated_data)
                break
        self.save(tasks)

    def get_task(self, task_id: str) -> Optional[Dict]:
        tasks = self.load_all_tasks()
        for task in tasks:
            if task["id"] == task_id:
                return task
        return None

    def delete_task(self, task_id: str):
        tasks = self.load_all_tasks()
        filtered_tasks = []
        for t in tasks:
            if t["id"] != task_id:
                filtered_tasks.append(t)
        self.save(filtered_tasks)

task_db = TaskDatabaseManager(TASKS_DB_FILE)

# ===================== 本地字典记忆类 =====================
class HistoryManager:
    def __init__(self, file_path):
        self.file_path = file_path

    def load(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {"dhdw": [], "gdmc": [], "ys": []}
        return {"dhdw": [], "gdmc": [], "ys": []}

    def save(self, history):
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception:
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
            except Exception:
                return {"materials": [], "handles": [], "hinges": []}
        return {"materials": [], "handles": [], "hinges": []}

    def save(self, options):
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(options, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

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

    def add_material(self, value):
        self._add("materials", value)

    def add_handle(self, value):
        self._add("handles", value)

    def add_hinge(self, value):
        self._add("hinges", value)

    def get_all_materials(self):
        custom = self.load().get("materials", [])
        return list(dict.fromkeys(custom + CONFIG.MATERIAL_OPTIONS.copy()))

    def get_all_handles(self):
        custom = self.load().get("handles", [])
        return list(dict.fromkeys(custom + CONFIG.HANDLE_OPTIONS.copy()))

    def get_all_hinges(self):
        custom = self.load().get("hinges", [])
        return list(dict.fromkeys(custom + list(CONFIG.HINGE_TYPES.keys())))


# ===================== UI 深度重构高级系统 (Apple Style) =====================
def set_custom_style():
    st.markdown("""
    <style>
    /* 全局高级背景调色与字体 */
    .stApp { 
        background-color: #F2F2F7; 
        font-family: "PingFang SC", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; 
    }
    
    /* 隐藏默认占位 */
    header, footer, .stDeployButton { visibility: hidden !important; display: none !important; }

    /* ======== 容器悬浮卡片 ======== */
    div[data-testid="stVerticalBlock"] > div > div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #FFFFFF !important; 
        border-radius: 12px !important; 
        border: 1px solid rgba(0,0,0,0.05) !important;
        box-shadow: 0 4px 20px rgba(0,0,0,0.03) !important; 
        padding: 20px 24px !important;
        transition: box-shadow 0.3s ease;
    }
    div[data-testid="stVerticalBlock"] > div > div[data-testid="stVerticalBlockBorderWrapper"]:hover {
        box-shadow: 0 8px 30px rgba(0,0,0,0.08) !important;
    }
    
    /* ======== 交互输入框精致化与【明确边界】 ======== */
    /* 添加了明显的 border: 1px solid #C7C7CC */
    .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] > div, .stTextArea textarea {
        font-size: 14px !important; 
        border-radius: 6px !important; 
        min-height: 38px !important;
        background-color: #FAFAFC !important; 
        border: 1px solid #C7C7CC !important;  
        transition: all 0.2s ease;
    }
    .stTextInput input:focus, .stNumberInput input:focus, .stSelectbox div[data-baseweb="select"] > div:focus-within, .stTextArea textarea:focus {
        background-color: #FFFFFF !important; 
        border: 1px solid #007AFF !important;
        box-shadow: 0 0 0 3px rgba(0, 122, 255, 0.15) !important;
    }
    label, .stRadio label, .stCheckbox label { 
        font-size: 13px !important; 
        font-weight: 500 !important; 
        color: #8E8E93 !important; 
        margin-bottom: -2px !important; 
    }
    h4 { 
        font-size: 17px !important; 
        font-weight: 600 !important; 
        color: #1C1C1E !important; 
        margin-bottom: 16px !important; 
        padding-bottom: 10px !important; 
        border-bottom: 1px solid #F2F2F7; 
    }

    /* ======== 按钮基础样式 ======== */
    .stButton > button { 
        border-radius: 8px !important; 
        font-weight: 600 !important; 
        transition: transform 0.1s ease, box-shadow 0.1s ease !important;
    }
    .stButton > button:active {
        transform: scale(0.97) !important;
    }
    .stButton > button[kind="primary"] { 
        background-color: #007AFF !important; 
        color: white !important; 
        border: none !important; 
        box-shadow: 0 4px 10px rgba(0, 122, 255, 0.2) !important;
    }
    .stButton > button[kind="secondary"] { 
        background-color: #FFFFFF !important; 
        color: #1C1C1E !important; 
        border: 1px solid #C7C7CC !important; 
    }
    div[data-testid="column"] { 
        padding: 0 6px !important; 
    }

    /* ======== 图纸点击卡片 (伪装成按钮) ======== */
    .drawing-card-btn > button {
        background-color: #FFFFFF !important;
        border: 1px solid #E5E5EA !important;
        border-radius: 10px !important;
        text-align: left !important;
        padding: 16px 20px !important;
        height: 100% !important;
        color: #1C1C1E !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.02) !important;
        transition: all 0.2s ease;
    }
    .drawing-card-btn > button:hover {
        border-color: #007AFF !important;
        box-shadow: 0 6px 16px rgba(0, 122, 255, 0.1) !important;
        transform: translateY(-2px);
    }
    .drawing-card-btn > button:active { transform: scale(0.98); }

    /* ======== 红色删除按钮 ======== */
    .delete-btn > button {
        background-color: #FFF0F0 !important;
        color: #FF3B30 !important;
        border: 1px solid #FFD1D1 !important;
        border-radius: 10px !important;
        height: 100% !important;
    }
    .delete-btn > button:hover {
        background-color: #FF3B30 !important;
        color: #FFFFFF !important;
    }

    /* 状态徽章 */
    .badge { 
        display: inline-block; 
        padding: 4px 12px; 
        border-radius: 12px; 
        font-size: 12px; 
        font-weight: 600; 
    }
    .badge-pending { background-color: #F2F2F7; color: #1C1C1E; }
    .badge-review { background-color: #FFF5E5; color: #FF9500; }
    .badge-modify { background-color: #FFE5E5; color: #FF3B30; }
    .badge-success { background-color: #E5FBE5; color: #34C759; }
    </style>
    """, unsafe_allow_html=True)

def init_session_state():
    if "logged_in" not in st.session_state: 
        st.session_state["logged_in"] = False
    if "user_id" not in st.session_state: 
        st.session_state["user_id"] = None
    if "user_name" not in st.session_state: 
        st.session_state["user_name"] = None
    if "user_role" not in st.session_state: 
        st.session_state["user_role"] = None
    if "current_module" not in st.session_state: 
        st.session_state["current_module"] = None
    if "active_task_id" not in st.session_state: 
        st.session_state["active_task_id"] = None
        
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

def load_task_to_session(task):
    for k, v in task["params"].items(): 
        st.session_state[k] = v

def get_current_form_data():
    keys = ["dhdw", "gdmc", "ys", "zzcl", "zmls", "fmls", "st_val", "hysl", "sel_hys", "qh", "mshd", "sm", "ddh", "sl", "hhxd", "dhrq", "door_type", "mother_door_width", "mid_door_width", "has_pillar", "pillar_width_str", "sel_kx", "sel_nk", "sel_qc", "qc_height", "has_mm", "mm_height", "has_outer", "trim_front_in", "has_inner", "trim_back_in", "dw", "dh", "overlap", "fw_left_str", "fw_right_str", "fw_top_str", "th_str", "left_right_gap_str", "top_bottom_gap_str", "middle_gap", "use_light_size", "light_w", "light_h", "threshold_type", "dxk", "gxk", "pdk", "zmks", "fmks", "sel_bz"]
    result = {}
    for k in keys:
        if k in st.session_state:
            result[k] = st.session_state[k]
    return result

def get_status_badge(status):
    mapping = {
        "待绘制": "badge-pending", 
        "待审核": "badge-review", 
        "待修改": "badge-modify", 
        "已通过": "badge-success"
    }
    css_class = mapping.get(status, "badge-pending")
    return f'<span class="badge {css_class}">{status}</span>'


# ===================== 表单与解析组件 =====================
class DimensionCalculator:
    def __init__(self, params: Dict[str, Any]): 
        self.p = params
        
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

class EzdxfDrawer:
    def __init__(self, doc, ms, hinge_block_name, progress_callback=None):
        self.doc = doc
        self.ms = ms
        self.hinge_block_name = hinge_block_name
        self.progress_callback = progress_callback or (lambda x: None)
        if self.hinge_block_name not in self.doc.blocks: 
            block = self.doc.blocks.new(name=self.hinge_block_name)
            block.add_lwpolyline([(-5, -40), (5, -40), (5, 40), (-5, 40)], close=True)

    def update_progress(self, msg): 
        self.progress_callback(msg)

    def batch_add_layers(self, layers_dict):
        for name, color in layers_dict.items():
            if name not in self.doc.layers: 
                self.doc.layers.add(name, color=color)

    def draw_poly(self, points, layer, closed=True): 
        self.ms.add_lwpolyline(points, close=closed, dxfattribs={'layer': layer})

    def draw_line(self, p1, p2, layer): 
        self.ms.add_line(p1, p2, dxfattribs={'layer': layer})

    def draw_dim(self, p1, p2, text_pos, rotation, layer, text_override=""):
        dimstyle = "23231" if "23231" in self.doc.dimstyles else "Standard"
        angle_deg = math.degrees(rotation)
        final_text = text_override if text_override else "<>"
        dim = self.ms.add_linear_dim(base=text_pos, p1=p1, p2=p2, angle=angle_deg, text=final_text, dimstyle=dimstyle, dxfattribs={'layer': layer})
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

def draw_door_in_frame(drawer: EzdxfDrawer, view_name: str, p: Dict, is_back: bool, use_light_size: bool = False, light_w: int = 0, light_h: int = 0):
    drawer.update_progress(f"开始绘制{view_name}门体...")
    
    left_width = p['left_width_back'] if is_back else p['left_width_front']
    right_width = p['right_width_back'] if is_back else p['right_width_front']
    fw_top = p['fw_top_back'] if is_back else p['fw_top_front']
    th = p['th_back'] if is_back else p['th_front']
    trim_w = p['trim_back'] if is_back else p['trim_front']
    overlap = p['overlap'] if trim_w > 0 else 0
    dw = p['dw']
    dh = p['dh']
    
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
    except Exception:
        hys_count = 3

    frame_center_x = 0.0
    frame_center_y = 0.0
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
        W = trim_w
        O = overlap
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
            mm_left = ix1
            mm_right = ix4
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

    pillar_width_front = 0
    pillar_width_back = 0
    if door_type == "两定两开" and has_pillar and pillar_width_str:
        parts = parse_dim_str(pillar_width_str, 55, 70)
        pillar_out = parts[0]
        pillar_in = parts[1]
        if nk_choice == "内开":
            pillar_width_front = pillar_in
            pillar_width_back = pillar_out
        else:
            pillar_width_front = pillar_out
            pillar_width_back = pillar_in

    panel_positions = []
    
    if door_type == "单门":
        panel_x1 = left_width + left_gap
        panel_x2 = dw - right_width - right_gap
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
            if is_back:
                if door_open_dir == "左开":
                    eff_dir = "右开"
                else:
                    eff_dir = "左开"
            else:
                eff_dir = door_open_dir
                
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
            "DHDW": info.get("DHDW", ""), 
            "GDMC": info.get("GDMC", ""), 
            "ZZCL": info.get("ZZCL", ""), 
            "DHRQ": info.get("DHRQ", ""),
            "DDH": info.get("DDH", ""), 
            "SL": info.get("SL", ""), 
            "YS": info.get("YS", ""), 
            "ZMLS": info.get("ZMLS", ""),
            "FMLS": info.get("FMLS", ""), 
            "ST": info.get("ST", ""), 
            "HYSL": info.get("HYSL", ""), 
            "QH": info.get("QH", ""),
            "MSHD": info.get("MSHD", ""), 
            "HHXD": info.get("HHXD", ""), 
            "BZ": info.get("BZ", ""), 
            "DOOR_TYPE": info.get("DOOR_TYPE", ""),
            "MOTHER_DOOR_WIDTH": info.get("MOTHER_DOOR_WIDTH", ""), 
            "HYYS": info.get("HYYS", ""), 
            "DXK": info.get("DXK", ""),
            "GXK": info.get("GXK", ""), 
            "PXK": info.get("PXK", ""), 
            "MX": info.get("MX", ""), 
            "QC_HEIGHT": info.get("QC_HEIGHT", ""),
            "MM_HEIGHT": info.get("MM_HEIGHT", ""), 
            "ZMKS": info.get("ZMKS", "按图"), 
            "FMKS": info.get("FMKS", "按图"),
        }
        
        nk = checks.get("nk", "内开")
        kx = checks.get("kx", "右开")
        qc = checks.get("qc", "无")
        bz = checks.get("bz", "全包")
        threshold = checks.get("threshold", "高低槛")
        
        has_pillar = False
        if checks.get("lz", "无") == "有":
            has_pillar = True
            
        has_mm = False
        if checks.get("mm", "无") == "有":
            has_mm = True
        
        check_attrs = {
            "OUTER": "√" if "外" in checks.get("bb", []) else "",
            "INNER": "√" if "内" in checks.get("bb", []) else "",
            "NK": "√" if nk == "内开" else "",
            "WK": "√" if nk == "外开" else "",
            "KX_RIGHT": "√" if kx == "右开" else "",
            "KX_LEFT": "√" if kx == "左开" else "",
            "LZ_YES": "√" if has_pillar else "",
            "LZ_NO": "" if has_pillar else "√",
            "MM_YES": "√" if has_mm else "",
            "MM_NO": "" if has_mm else "√",
            "QC_GLASS": "√" if qc == "玻璃" else "",
            "QC_SEAL": "√" if qc == "封闭" else "",
            "BZ_QB": "√" if bz == "全包" else "",
            "BZ_MX": "√" if bz == "木箱" else "",
            "GDK": "√" if threshold == "高低槛" else "",
            "PDK": "√" if threshold == "平底槛" else "",
        }
        
        all_attrs = {**base_attrs, **check_attrs}

        for insert in ms.query('INSERT'):
            to_replace = []
            for attrib in insert.attribs:
                tag = attrib.dxf.tag.strip().upper()
                if tag == "BZ":
                    ms.add_mtext(all_attrs["BZ"], dxfattribs={
                        'insert': attrib.dxf.insert, 
                        'char_height': attrib.dxf.height, 
                        'layer': attrib.dxf.layer, 
                        'style': attrib.dxf.style
                    }).dxf.width = 1200 
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
                    if bz == "全包":
                        attrib.dxf.text = "全包"
                    else:
                        attrib.dxf.text = "木箱"
            
            for old_attrib in to_replace:
                old_attrib.destroy()

        sel_hys = checks.get('hys', '葫芦头合页')
        hinge_name = CONFIG.HINGE_TYPES.get(sel_hys, "hlt")
        drawer = EzdxfDrawer(doc, ms, hinge_name, progress_callback)
        drawer.batch_add_layers({
            "A-DOOR-FRAME": 4, 
            "A-DOOR-PANEL": 2, 
            "A-DOOR-TRIM": 1, 
            "YQ_DIM": 3, 
            "A-DOOR-mark": 7
        })

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
        
        use_light = draw_p.get("use_light_size", False)
        lw = draw_p.get("light_w", 0)
        lh = draw_p.get("light_h", 0)
        
        draw_door_in_frame(drawer, "正面", draw_p, False, use_light, lw, lh)
        draw_door_in_frame(drawer, "背面", draw_p, True, use_light, lw, lh)

        buffer = io.StringIO()
        doc.write(buffer)
        return "图纸生成成功！", buffer
        
    except Exception as e:
        import traceback
        return f"生成出错: {str(e)}\n{traceback.format_exc()}", None

def parse_gap_str(gap_str: str, default: int = 0) -> Tuple[int, int]:
    if not gap_str.strip(): 
        return (default, default)
    try:
        parts = gap_str.replace("，", "/").replace(",", "/").split("/")
        if len(parts) == 2:
            return (int(parts[0].strip()), int(parts[1].strip()))
        else:
            return (int(parts[0].strip()), int(parts[0].strip()))
    except Exception:
        return (default, default)

def parse_dim_str(val_str: str, default_out: float, default_in: float) -> Tuple[float, float]:
    try:
        parts = val_str.replace('，', '/').replace(',', '/').split('/')
        if len(parts) >= 2:
            return (float(parts[0]), float(parts[1]))
        else:
            return (float(parts[0]), float(parts[0]))
    except Exception:
        return (default_out, default_in)


# ===================== 表单复用组件 =====================
def render_main_form(options_mgr):
    col_left, col_mid, col_right = st.columns([1, 1, 1])
    with col_left:
        with st.container(border=True):
            st.markdown("#### 📝 订单基础信息")
            c1, c2 = st.columns(2)
            st.session_state["dhdw"] = c1.text_input("订货单位/客户", value=st.session_state["dhdw"])
            st.session_state["gdmc"] = c2.text_input("项目名称", value=st.session_state["gdmc"])
            c3, c4 = st.columns(2)
            st.session_state["ddh"] = c3.text_input("订单号", value=st.session_state["ddh"])
            dhrq = c4.date_input("交期/日期", value=datetime.datetime.strptime(st.session_state["dhrq"], "%Y.%m.%d").date())
            st.session_state["dhrq"] = dhrq.strftime("%Y.%m.%d")
            c5, c6 = st.columns(2)
            st.session_state["sl"] = c5.text_input("数量(樘)", value=st.session_state["sl"])
            st.session_state["hhxd"] = c6.text_input("制单人", value=st.session_state["hhxd"])
            
        with st.container(border=True):
            st.markdown("#### 🎨 材质与外观")
            c1, c2 = st.columns(2)
            mats = options_mgr.get_all_materials()
            if st.session_state["zzcl"] in mats:
                mat_index = mats.index(st.session_state["zzcl"])
            else:
                mat_index = 0
            sel_mat = c1.selectbox("制作材料", mats, index=mat_index)
            cust_mat = c1.text_input("自定义材料", placeholder="输入覆盖", label_visibility="collapsed")
            if cust_mat:
                st.session_state["zzcl"] = cust_mat
            else:
                st.session_state["zzcl"] = sel_mat
                
            st.session_state["ys"] = c2.text_input("表面颜色", value=st.session_state["ys"])
            c3, c4 = st.columns(2)
            st.session_state["zmks"] = c3.text_input("正面款式", value=st.session_state["zmks"])
            st.session_state["fmks"] = c4.text_input("反面款式", value=st.session_state["fmks"])
            c5, c6 = st.columns(2)
            st.session_state["mshd"] = c5.number_input("门扇厚度(mm)", value=st.session_state["mshd"], step=5)
            st.session_state["qh"] = c6.text_input("墙厚(mm)", value=st.session_state["qh"], placeholder="选填")
            
            bz_options = ["全包", "木箱"]
            if st.session_state["sel_bz"] in bz_options:
                bz_index = bz_options.index(st.session_state["sel_bz"])
            else:
                bz_index = 0
            st.session_state["sel_bz"] = st.radio("包装方式", bz_options, horizontal=True, index=bz_index)

    with col_mid:
        with st.container(border=True):
            st.markdown("#### 📐 结构与开向")
            dt_options = ["单门", "对开门", "子母门", "两定两开", "折叠四开门"]
            if st.session_state["door_type"] in dt_options:
                dt_index = dt_options.index(st.session_state["door_type"])
            else:
                dt_index = 0
            st.session_state["door_type"] = st.selectbox("门型", dt_options, index=dt_index)
            
            c1, c2 = st.columns(2)
            kx_options = ["左开", "右开"]
            if st.session_state["sel_kx"] in kx_options:
                kx_index = kx_options.index(st.session_state["sel_kx"])
            else:
                kx_index = 1
            st.session_state["sel_kx"] = c1.radio("左右开向", kx_options, horizontal=True, index=kx_index)
            
            nk_options = ["内开", "外开"]
            if st.session_state["sel_nk"] in nk_options:
                nk_index = nk_options.index(st.session_state["sel_nk"])
            else:
                nk_index = 0
            st.session_state["sel_nk"] = c2.radio("内外开向", nk_options, horizontal=True, index=nk_index)
            
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
            
            th_options = ["高低槛", "平底槛"]
            if st.session_state["threshold_type"] in th_options:
                th_index = th_options.index(st.session_state["threshold_type"])
            else:
                th_index = 0
            st.session_state["threshold_type"] = c4.radio("下槛方案", th_options, horizontal=True, label_visibility="collapsed", index=th_index)
            
            if st.session_state["threshold_type"] == "高低槛": 
                st.session_state["th_str"] = st.text_input("下槛高度 (低/高)", value=st.session_state["th_str"])
            else: 
                st.session_state["pdk"] = st.text_input("平底槛厚度(mm)", value=st.session_state["pdk"])

    with col_right:
        with st.container(border=True):
            st.markdown("#### ⚙️ 五金锁具")
            hdls = options_mgr.get_all_handles()
            c1, c2 = st.columns(2)
            
            if st.session_state["zmls"] in hdls:
                zm_idx = hdls.index(st.session_state["zmls"])
            else:
                zm_idx = 0
            st.session_state["zmls"] = c1.selectbox("正面拉手", hdls, index=zm_idx)
            
            if st.session_state["fmls"] in hdls:
                fm_idx = hdls.index(st.session_state["fmls"])
            else:
                fm_idx = 0
            st.session_state["fmls"] = c2.selectbox("反面拉手", hdls, index=fm_idx)
            
            lks = CONFIG.LOCK_OPTIONS.copy()
            if st.session_state["st_val"] in lks:
                lk_idx = lks.index(st.session_state["st_val"])
            else:
                lk_idx = 0
            st.session_state["st_val"] = c1.selectbox("锁体类型", lks, index=lk_idx)
            
            hgs = options_mgr.get_all_hinges()
            if st.session_state["sel_hys"] in hgs:
                hg_idx = hgs.index(st.session_state["sel_hys"])
            else:
                hg_idx = 0
            st.session_state["sel_hys"] = c2.selectbox("合页样式", hgs, index=hg_idx)
            
            hys_opts = ["3个/扇", "2个/扇", "4个/扇", "5个/扇"]
            if st.session_state["hysl"] in hys_opts:
                hys_idx = hys_opts.index(st.session_state["hysl"])
            else:
                hys_idx = 0
            st.session_state["hysl"] = st.selectbox("单扇合页数量", hys_opts, index=hys_idx)
            
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
            qc_opts = ["无", "玻璃", "封闭"]
            if st.session_state["sel_qc"] in qc_opts:
                qc_idx = qc_opts.index(st.session_state["sel_qc"])
            else:
                qc_idx = 0
            st.session_state["sel_qc"] = c6.selectbox("气窗", qc_opts, index=qc_idx)
            
            st.session_state["has_mm"] = c7.checkbox("门楣", value=st.session_state["has_mm"])
            
            is_two_fixed = False
            if st.session_state["door_type"] == "两定两开":
                is_two_fixed = True
                
            st.session_state["has_pillar"] = c8.checkbox("立柱", value=st.session_state["has_pillar"], disabled=not is_two_fixed)
            
            c9, c10 = st.columns(2)
            if st.session_state["sel_qc"] != "无": 
                st.session_state["qc_height"] = c9.number_input("气窗高", value=st.session_state["qc_height"], step=10)
            if st.session_state["has_mm"]: 
                st.session_state["mm_height"] = c10.number_input("门楣高", value=st.session_state["mm_height"], step=10)
            if st.session_state["has_pillar"] and is_two_fixed: 
                st.session_state["pillar_width_str"] = st.text_input("立柱宽(外/内)", value=st.session_state["pillar_width_str"])
                
        with st.container(border=True):
            st.session_state["sm"] = st.text_area("车间生产批注", value=st.session_state["sm"], height=68, placeholder="补充图纸外的额外加工要求...")


def generate_cad_trigger(history_mgr):
    for key in ["dhdw", "gdmc", "ys"]:
        if st.session_state.get(key): 
            history_mgr.add(key, st.session_state[key])
            
    outer_width = st.session_state["trim_front_in"] if st.session_state["has_outer"] else 0
    overlap = st.session_state.get("overlap", 20)
    note_line = f"门套宽/压墙/压框={outer_width}/{outer_width - overlap}/{overlap}mm"
    current_note = st.session_state.get("sm", "")
    
    if note_line not in current_note:
        if current_note.strip():
            final_note = current_note + "\n" + note_line
        else:
            final_note = note_line
    else:
        final_note = current_note

    parts_left = parse_dim_str(st.session_state.get("fw_left_str", "60/60"), 60, 60)
    left_out = parts_left[0]
    left_in = parts_left[1]
    
    parts_right = parse_dim_str(st.session_state.get("fw_right_str", "60/60"), 60, 60)
    right_out = parts_right[0]
    right_in = parts_right[1]
    
    parts_top = parse_dim_str(st.session_state.get("fw_top_str", "60/60"), 60, 60)
    fw_top_out = parts_top[0]
    fw_top_in = parts_top[1]
    
    parts_th = parse_dim_str(st.session_state.get("th_str", "60/60"), 60, 60)
    th_out = parts_th[0]
    th_in = parts_th[1]

    if st.session_state["sel_nk"] == "内开":
        lwf = left_in
        rwf = right_in
        lwb = left_out
        rwb = right_out
        ftf = fw_top_in
        ftb = fw_top_out
        thf = th_in
        thb = th_out
    else:
        lwf = left_out
        rwf = right_out
        lwb = left_in
        rwb = right_in
        ftf = fw_top_out
        ftb = fw_top_in
        thf = th_out
        thb = th_in

    dw = st.session_state["dw"]
    dh = st.session_state["dh"]
    
    if st.session_state.get("use_light_size", False):
        lw = st.session_state.get("light_w", 0)
        lh = st.session_state.get("light_h", 0)
        if lw > 0 and lh > 0:
            calc_p = {
                "dw": dw, "dh": dh, 
                "left_width_front": lwf, "right_width_front": rwf, 
                "left_width_back": lwb, "right_width_back": rwb, 
                "fw_top_front": ftf, "fw_top_back": ftb, 
                "th_front": thf, "th_back": thb, 
                "nk": st.session_state["sel_nk"]
            }
            calc = DimensionCalculator(calc_p)
            res_light = calc.calculate_from_light_size(lw, lh, st.session_state["sel_nk"] == "外开")
            dw = res_light[0]
            dh = res_light[1]

    ttype = st.session_state.get("threshold_type", "高低槛")
    if ttype == "平底槛": 
        dxk_val = ""
        gxk_val = ""
        pdk_val = st.session_state.get("pdk", "")
    else: 
        parts = st.session_state.get("th_str", "55/70").split("/")
        if len(parts) > 1:
            dxk_val = parts[0]
            gxk_val = parts[-1]
        else:
            dxk_val = parts[0]
            gxk_val = parts[0]
        pdk_val = ""
        
    if st.session_state["door_type"] == "两定两开":
        dt_cn = "两定两开门"
    else:
        dt_cn = st.session_state["door_type"]
        
    qh_val = ""
    if st.session_state['qh']:
        qh_val = f"{st.session_state['qh']} mm"
        
    mshd_val = f"{st.session_state['mshd']} mm"
    
    qc_height_val = 0
    if st.session_state["sel_qc"] != "无":
        qc_height_val = st.session_state["qc_height"]
        
    mm_height_val = 0
    if st.session_state["has_mm"]:
        mm_height_val = st.session_state["mm_height"]
    
    info_map = {
        "DHDW": st.session_state["dhdw"], 
        "GDMC": st.session_state["gdmc"], 
        "ZZCL": st.session_state["zzcl"], 
        "DHRQ": st.session_state["dhrq"], 
        "DDH": st.session_state["ddh"], 
        "SL": st.session_state["sl"],
        "YS": st.session_state["ys"], 
        "ZMLS": st.session_state["zmls"], 
        "FMLS": st.session_state["fmls"], 
        "ST": st.session_state["st_val"], 
        "HYSL": st.session_state["hysl"], 
        "QH": qh_val,
        "MSHD": mshd_val, 
        "HHXD": st.session_state["hhxd"], 
        "BZ": final_note,
        "DOOR_TYPE": st.session_state["door_type"], 
        "MOTHER_DOOR_WIDTH": st.session_state["mother_door_width"], 
        "MID_DOOR_WIDTH": st.session_state["mid_door_width"], 
        "PILLAR_WIDTH_STR": st.session_state["pillar_width_str"],
        "HAS_PILLAR": st.session_state["has_pillar"], 
        "HYYS": st.session_state["sel_hys"], 
        "DXK": dxk_val, 
        "GXK": gxk_val, 
        "PXK": pdk_val, 
        "MX": dt_cn, 
        "QC_HEIGHT": qc_height_val,
        "HAS_MM": st.session_state["has_mm"], 
        "MM_HEIGHT": mm_height_val, 
        "ZMKS": st.session_state["zmks"], 
        "FMKS": st.session_state["fmks"]
    }
    
    out_mark = ""
    if st.session_state["has_outer"]:
        out_mark = "√"
    
    in_mark = ""
    if st.session_state["has_inner"]:
        in_mark = "√"
        
    nk_mark = ""
    if st.session_state["sel_nk"] == "内开":
        nk_mark = "√"
        
    wk_mark = ""
    if st.session_state["sel_nk"] == "外开":
        wk_mark = "√"
        
    kxr_mark = ""
    if st.session_state["sel_kx"] == "右开":
        kxr_mark = "√"
        
    kxl_mark = ""
    if st.session_state["sel_kx"] == "左开":
        kxl_mark = "√"
        
    lz_y = ""
    lz_n = "√"
    if st.session_state["has_pillar"]:
        lz_y = "√"
        lz_n = ""
        
    mm_y = ""
    mm_n = "√"
    if st.session_state["has_mm"]:
        mm_y = "√"
        mm_n = ""
        
    qc_g = ""
    if st.session_state["sel_qc"] == "玻璃":
        qc_g = "√"
        
    qc_s = ""
    if st.session_state["sel_qc"] == "封闭":
        qc_s = "√"
        
    bz_q = ""
    if st.session_state["sel_bz"] == "全包":
        bz_q = "√"
        
    bz_m = ""
    if st.session_state["sel_bz"] == "木箱":
        bz_m = "√"
        
    gdk_m = ""
    if st.session_state["threshold_type"] == "高低槛":
        gdk_m = "√"
        
    pdk_m = ""
    if st.session_state["threshold_type"] == "平底槛":
        pdk_m = "√"
    
    check_map = {
        "kx": st.session_state["sel_kx"], 
        "nk": st.session_state["sel_nk"], 
        "qc": st.session_state["sel_qc"], 
        "lz": "有" if st.session_state["has_pillar"] else "无", 
        "bz": st.session_state["sel_bz"], 
        "hys": st.session_state["sel_hys"], 
        "mm": "有" if st.session_state["has_mm"] else "无",
        "OUTER": out_mark,
        "INNER": in_mark,
        "NK": nk_mark,
        "WK": wk_mark,
        "KX_RIGHT": kxr_mark,
        "KX_LEFT": kxl_mark,
        "LZ_YES": lz_y,
        "LZ_NO": lz_n,
        "MM_YES": mm_y,
        "MM_NO": mm_n,
        "QC_GLASS": qc_g,
        "QC_SEAL": qc_s,
        "BZ_QB": bz_q,
        "BZ_MX": bz_m,
        "GDK": gdk_m,
        "PDK": pdk_m
    }
    
    trim_f = 0
    if st.session_state["has_outer"]:
        trim_f = st.session_state["trim_front_in"]
        
    trim_b = 0
    if st.session_state["has_inner"]:
        trim_b = st.session_state["trim_back_in"]
    
    draw_params = {
        "dw": dw, "dh": dh, 
        "left_width_front": lwf, "right_width_front": rwf, 
        "left_width_back": lwb, "right_width_back": rwb, 
        "fw_top_front": ftf, "fw_top_back": ftb, 
        "th_front": thf, "th_back": thb,
        "trim_front": trim_f, 
        "trim_back": trim_b,
        "overlap": overlap, 
        "door_type": st.session_state["door_type"], 
        "mother_door_width": st.session_state["mother_door_width"], 
        "mid_door_width": st.session_state["mid_door_width"], 
        "pillar_width_str": st.session_state["pillar_width_str"], 
        "has_pillar": st.session_state["has_pillar"], 
        "kx": st.session_state["sel_kx"], "nk": st.session_state["sel_nk"],
        "qc": st.session_state["sel_qc"], 
        "qc_height": qc_height_val, 
        "has_mm": st.session_state["has_mm"], 
        "mm_height": mm_height_val, 
        "hys": st.session_state["sel_hys"], "hysl": st.session_state["hysl"],
        "left_right_gap": parse_gap_str(st.session_state["left_right_gap_str"], 0), 
        "top_bottom_gap": parse_gap_str(st.session_state["top_bottom_gap_str"], 0), 
        "middle_gap": st.session_state["middle_gap"],
        "use_light_size": st.session_state["use_light_size"], 
        "light_w": st.session_state["light_w"], 
        "light_h": st.session_state["light_h"], 
        "zmls": st.session_state["zmls"], 
        "fmls": st.session_state["fmls"],
    }
    
    return info_map, check_map, draw_params


# ===================== 登录拦截 =====================
def render_login():
    st.markdown("<div style='height: 10vh;'></div>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align:center; color:#1C1C1E; font-weight:700;'>🏭 西州将军 - 智能协同平台</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#8E8E93;'>Sign in to continue</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        with st.container(border=True):
            uid = st.text_input("账号")
            pwd = st.text_input("密码", type="password")
            
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            if st.button("登 录", use_container_width=True, type="primary"):
                user_info = user_db.authenticate(uid, pwd)
                if user_info:
                    st.session_state["logged_in"] = True
                    st.session_state["user_id"] = uid
                    st.session_state["user_name"] = user_info["name"]
                    st.session_state["user_role"] = user_info["role"]
                    st.session_state["current_module"] = user_info["default_module"]
                    st.rerun()
                else:
                    st.error("账号或密码错误！")

def render_admin_dashboard():
    st.markdown("### ⚙️ 系统后台管理")
    st.markdown("在这里您可以管理系统内所有员工的账号和权限。")
    
    users = user_db.load_all_users()
    
    with st.container(border=True):
        st.markdown("#### 添加/更新账号")
        c1, c2, c3, c4 = st.columns(4)
        new_uid = c1.text_input("账号 (用于登录)", placeholder="例: zhangsan")
        new_name = c2.text_input("姓名", placeholder="例: 销售-张三")
        new_pwd = c3.text_input("密码", placeholder="设置初始密码")
        new_role = c4.selectbox("分配角色", ["录入员", "绘图员", "总工", "超级管理员"])
        
        if st.button("保存账号", type="primary"):
            if new_uid and new_name and new_pwd:
                user_db.add_or_update_user(new_uid, new_pwd, new_role, new_name)
                st.success(f"✅ 成功保存账号: {new_uid}")
                st.rerun()
            else:
                st.warning("请填写完整账号信息。")

    st.markdown("#### 当前用户列表")
    for u_id, u_info in users.items():
        with st.container(border=True):
            col_info, col_del = st.columns([8, 2])
            with col_info:
                st.markdown(f"**{u_info['name']}** (账号: `{u_id}`) | 角色: `{u_info['role']}` | 密码: `{u_info['password']}`")
            with col_del:
                if u_id == "admin":
                    st.markdown("<span style='color:#8E8E93;'>系统内置不可删</span>", unsafe_allow_html=True)
                else:
                    if st.button("删除", key=f"del_u_{u_id}"):
                        user_db.delete_user(u_id)
                        st.rerun()


# ===================== 顶部高级导航栏 =====================
def render_top_nav():
    st.markdown("<div style='padding-top:10px;'></div>", unsafe_allow_html=True)
    
    nav_items = [
        {"title": "📝 图纸信息录入", "module": "图纸信息录入"},
        {"title": "📐 图纸绘制", "module": "图纸绘制"},
        {"title": "👁️ 图纸审核", "module": "图纸审核"}
    ]
    
    if st.session_state.get("user_role") == "超级管理员":
        nav_items.append({"title": "⚙️ 后台管理", "module": "后台管理"})
        
    num_navs = len(nav_items)
    cols = st.columns([2] * num_navs + [1, 2])
    
    for i, item in enumerate(nav_items):
        is_active = False
        if st.session_state["current_module"] == item["module"]:
            is_active = True
            
        with cols[i]:
            if is_active:
                if st.button(item["title"], use_container_width=True, type="primary", key=f"nav_{item['module']}"):
                    pass
            else:
                if st.button(item["title"], use_container_width=True, type="secondary", key=f"nav_{item['module']}"):
                    st.session_state["current_module"] = item["module"]
                    st.session_state["active_task_id"] = None
                    st.rerun()

    with cols[-1]:
        st.markdown(f"<div style='text-align:right; color:#8E8E93; font-size:13px; margin-top:2px;'>{st.session_state['user_name']}</div>", unsafe_allow_html=True)
        if st.button("退出登录", use_container_width=True):
            st.session_state["logged_in"] = False
            st.rerun()
            
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

# ===================== 主程序 =====================
def main():
    st.set_page_config(page_title="西州将军 | 协同平台", layout="wide")
    init_session_state()
    set_custom_style()

    if not st.session_state.get("logged_in", False):
        render_login()
        st.stop()

    render_top_nav()

    history_mgr = HistoryManager(HISTORY_FILE)
    options_mgr = CustomOptionsManager(CUSTOM_OPTIONS_FILE)

    current_module = st.session_state.get("current_module")

    # ==================== 模块 0：后台管理 ====================
    if current_module == "后台管理":
        if st.session_state.get("user_role") != "超级管理员":
            st.error("您没有权限访问此页面。")
        else:
            render_admin_dashboard()

    # ==================== 模块 1：图纸信息录入 ====================
    elif current_module == "图纸信息录入":
        batch_text = st.text_input("✨ 智能文本识别", placeholder="粘贴销售聊天记录，回车自动解析并填充参数...", label_visibility="collapsed")
        if batch_text:
            parsed = parse_batch_text(batch_text)  
            if parsed:
                for k, v in parsed.items(): 
                    st.session_state[k] = v
                st.rerun()
        
        st.markdown("#### 🖼️ 客户沟通记录与参考图")
        ref_img_file = st.file_uploader("📥 拖拽图片到此处，或点击框内按 Ctrl+V (Mac按 Cmd+V) 直接粘贴截图", type=['jpg', 'png', 'jpeg'], accept_multiple_files=False)
        ref_img_b64 = None
        if ref_img_file is not None:
            ref_img_b64 = base64.b64encode(ref_img_file.getvalue()).decode('utf-8')
            st.success("参考图已就绪！将随订单一起提交。")
            
        st.divider()
        render_main_form(options_mgr)
        
        c1, c2 = st.columns([1, 1])
        with c1:
            if st.button("📤 提交订单 (流转至绘图部)", type="primary", use_container_width=True):
                task_id = str(uuid.uuid4())[:8]
                new_task = {
                    "id": task_id, 
                    "date": st.session_state["dhrq"], 
                    "status": "待绘制",
                    "customer": st.session_state["dhdw"], 
                    "project": st.session_state["gdmc"], 
                    "door_type": st.session_state["door_type"],
                    "size": f"{st.session_state['dw']} x {st.session_state['dh']} (洞口)", 
                    "params": get_current_form_data(),
                    "ref_img_b64": ref_img_b64,
                    "drawing_img_b64": None, 
                    "review_feedback": ""
                }
                task_db.add_task(new_task)
                st.success(f"✅ 订单提交成功！(编号: {task_id})，绘图员已可查收。")
        
        with c2:
            if st.button("⚡ 快速生成CAD (仅下载不流转)", type="secondary", use_container_width=True):
                info_map, check_map, draw_params = generate_cad_trigger(history_mgr)
                def prog_cb(m): 
                    pass
                result, buffer = run_integrated_system(info_map, check_map, draw_params, prog_cb)
                if buffer: 
                    st.download_button("⬇️ 点击下载 DXF", data=buffer.getvalue(), file_name=f"排版图纸_{st.session_state['dhdw']}.dxf", mime="application/dxf", use_container_width=True)

    # ==================== 模块 2：图纸绘制 ====================
    elif current_module == "图纸绘制":
        active_id = st.session_state.get("active_task_id")
        
        if active_id:
            active_task = task_db.get_task(active_id)
            if not active_task:
                st.error("任务不存在")
                st.session_state["active_task_id"] = None
                st.rerun()
                
            c_back, c_title = st.columns([1, 9])
            with c_back:
                if st.button("← 返回列表"):
                    st.session_state["active_task_id"] = None
                    st.rerun()
            with c_title:
                st.markdown(f"<h4 style='margin-bottom:0;'>正在处理：{active_task['customer']} - {active_task['project']} {get_status_badge(active_task['status'])}</h4>", unsafe_allow_html=True)
                
            if active_task.get("ref_img_b64"):
                with st.expander("🖼️ 查看前端销售上传的参考图 / 沟通记录"):
                    try:
                        ref_bytes = base64.b64decode(active_task["ref_img_b64"])
                        st.image(ref_bytes, use_column_width=True)
                    except Exception:
                        pass
                
            if active_task['status'] == "待修改" and active_task['review_feedback']: 
                st.error(f"🛑 审核驳回意见：\n\n{active_task['review_feedback']}")

            render_main_form(options_mgr)
            
            c_gen, c_upload = st.columns([1, 1])
            with c_gen:
                if st.button("⚡ 生成基准 CAD 底图", type="secondary", use_container_width=True):
                    info_map, check_map, draw_params = generate_cad_trigger(history_mgr)
                    def prog_cb(m): 
                        pass
                    result, buffer = run_integrated_system(info_map, check_map, draw_params, prog_cb)
                    if buffer: 
                        st.download_button("⬇️ 下载 DXF 进行深化", data=buffer.getvalue(), file_name=f"基准图纸_{active_task['id']}.dxf", mime="application/dxf", use_container_width=True)
            
            with c_upload:
                uploaded_file = st.file_uploader("📥 上传深化完成的图纸图片 (支持拖拽/截图粘贴)，提交给总工审核", label_visibility="collapsed")
                if st.button("📤 提交审核", type="primary", use_container_width=True):
                    if uploaded_file is not None:
                        img_b64 = base64.b64encode(uploaded_file.getvalue()).decode('utf-8')
                        task_db.update_task(active_task["id"], {
                            "drawing_img_b64": img_b64, 
                            "status": "待审核", 
                            "params": get_current_form_data()
                        })
                        st.session_state["active_task_id"] = None
                        st.success("成功提交给总工！")
                        st.rerun()
                    else: 
                        st.warning("请先上传图纸文件！")
                            
        else:
            filter_date = st.date_input("检索日期", value=datetime.date.today())
            filter_date_str = filter_date.strftime("%Y.%m.%d")
            all_tasks = task_db.load_all_tasks()
            
            tasks_to_show = []
            for t in all_tasks:
                if t["date"] == filter_date_str:
                    tasks_to_show.append(t)
            
            if not tasks_to_show: 
                st.info("🎉 暂无待处理任务！")
            else:
                for task in tasks_to_show:
                    with st.container():
                        col_card, col_del = st.columns([9.2, 0.8])
                        with col_card:
                            st.markdown('<div class="drawing-card-btn">', unsafe_allow_html=True)
                            btn_text = f"📂 {task['customer']} - {task['project']} \n\n 门型：{task['door_type']} | 洞口：{task['size']} | 状态：{task['status']}"
                            if st.button(btn_text, key=f"btn_{task['id']}", use_container_width=True):
                                load_task_to_session(task)
                                st.session_state["active_task_id"] = task["id"]
                                st.rerun()
                            st.markdown('</div>', unsafe_allow_html=True)
                        with col_del:
                            st.markdown('<div class="delete-btn">', unsafe_allow_html=True)
                            if st.button("🗑️", key=f"del_{task['id']}", use_container_width=True, help="删除此订单"):
                                task_db.delete_task(task['id'])
                                st.rerun()
                            st.markdown('</div>', unsafe_allow_html=True)

    # ==================== 模块 3：图纸审核 ====================
    elif current_module == "图纸审核":
        active_id = st.session_state.get("active_task_id")
        if active_id:
            active_task = task_db.get_task(active_id)
            if not active_task: 
                st.error("任务不存在")
                st.session_state["active_task_id"] = None
                st.rerun()
                
            if st.button("← 返回待审列表", type="secondary"): 
                st.session_state["active_task_id"] = None
                st.rerun()
                
            c_img, c_info = st.columns([6, 4])
            with c_img:
                st.markdown("#### 图纸预览")
                st.caption("🔍 提示：鼠标停在图片上，点击右上角 `⤢` 即可全屏放大。")
                if active_task.get("drawing_img_b64"):
                    try:
                        img_bytes = base64.b64decode(active_task["drawing_img_b64"])
                        st.image(img_bytes, use_column_width=True)
                    except Exception: 
                        st.info("图片解析失败。")
                else: 
                    st.warning("绘图员未上传预览图。")
                    
                if active_task.get("ref_img_b64"):
                    with st.expander("🖼️ 查看前端录入的原单/参考图"):
                        try:
                            ref_bytes = base64.b64decode(active_task["ref_img_b64"])
                            st.image(ref_bytes, use_column_width=True)
                        except Exception:
                            pass
            
            with c_info:
                st.markdown("#### 核心参数核对")
                p = active_task["params"]
                with st.container(border=True):
                    st.write(f"**客户:** {p.get('dhdw')} | **项目:** {p.get('gdmc')}")
                    st.write(f"**门型:** {p.get('door_type')} | **洞口:** {p.get('dw')}x{p.get('dh')}")
                    st.write(f"**开向:** {p.get('sel_kx')}{p.get('sel_nk')}")
                    st.write(f"**材质:** {p.get('zzcl')} | **颜色:** {p.get('ys')}")
                
                st.markdown("#### 审核意见")
                feedback = st.text_area("输入修改要求", value=active_task["review_feedback"], height=120, placeholder="如：右侧压框尺寸不对，请改成 30mm...")
                
                cb1, cb2 = st.columns(2)
                with cb1:
                    if st.button("❌ 打回修改", type="secondary", use_container_width=True):
                        task_db.update_task(active_task["id"], {"status": "待修改", "review_feedback": feedback})
                        st.session_state["active_task_id"] = None
                        st.rerun()
                with cb2:
                    if st.button("✅ 审核通过", type="primary", use_container_width=True):
                        task_db.update_task(active_task["id"], {"status": "已通过", "review_feedback": "通过"})
                        st.session_state["active_task_id"] = None
                        st.rerun()
        else:
            all_tasks = task_db.load_all_tasks()
            review_tasks = []
            for t in all_tasks:
                if t["status"] in ["待审核", "已通过"]:
                    review_tasks.append(t)
                    
            if not review_tasks: 
                st.info("✅ 目前没有需要审核的图纸。")
            else:
                for task in review_tasks:
                    with st.container():
                        col_card, col_action = st.columns([8.5, 1.5])
                        with col_card:
                            st.markdown('<div class="drawing-card-btn">', unsafe_allow_html=True)
                            btn_txt = f"🔍 {task['customer']} - {task['project']} \n\n 提交时间：{task['date']} | 状态：{task['status']}"
                            if st.button(btn_txt, key=f"rev_{task['id']}", use_container_width=True):
                                st.session_state["active_task_id"] = task["id"]
                                st.rerun()
                            st.markdown('</div>', unsafe_allow_html=True)
                        with col_action:
                            pass 

if __name__ == "__main__":
    main()
