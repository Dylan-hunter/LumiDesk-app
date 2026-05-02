from __future__ import annotations

import json
import math
import os
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QDate, QPoint, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QPainter, QPen, QTextCharFormat
from PySide6.QtWidgets import (
    QApplication,
    QCalendarWidget,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QStyle,
    QSystemTrayIcon,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

import holidays
from lunar_python import Solar

APP_NAME = "LumiDesk"
APP_DIR_NAME = "LumiDesk"


def resource_path(*parts: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base.joinpath(*parts)


def app_data_dir() -> Path:
    if os.name == "nt":
        base = os.environ.get("APPDATA")
        if base:
            return Path(base) / APP_DIR_NAME
    return Path.home() / ".lumidesk"


DATA_DIR = app_data_dir()
DATA_FILE = DATA_DIR / "data.json"
WEATHER_GEOCODE = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_FORECAST = "https://api.open-meteo.com/v1/forecast"


THEMES: Dict[str, Dict[str, str]] = {
    "Aurora Night": {
        "bg": "#0b1020",
        "card": "rgba(255,255,255,0.08)",
        "card2": "rgba(255,255,255,0.06)",
        "text": "#f6f7fb",
        "muted": "#aab3c8",
        "accent": "#89f7fe",
        "accent2": "#66a6ff",
        "danger": "#ff8ea1",
        "success": "#8ce99a",
        "border": "rgba(255,255,255,0.14)",
        "calendar_holiday": "#ffd166",
        "calendar_note": "#8ce99a",
    },
    "Mist Latte": {
        "bg": "#f3ede7",
        "card": "rgba(255,255,255,0.92)",
        "card2": "rgba(255,255,255,0.82)",
        "text": "#312b2b",
        "muted": "#7a6f6a",
        "accent": "#b08968",
        "accent2": "#ddb892",
        "danger": "#cf6a6a",
        "success": "#679267",
        "border": "rgba(49,43,43,0.10)",
        "calendar_holiday": "#bc6c25",
        "calendar_note": "#588157",
    },
    "Skyline Blue": {
        "bg": "#eaf4ff",
        "card": "rgba(255,255,255,0.88)",
        "card2": "rgba(255,255,255,0.72)",
        "text": "#102542",
        "muted": "#527096",
        "accent": "#3e92cc",
        "accent2": "#2a628f",
        "danger": "#d85757",
        "success": "#2f8f6b",
        "border": "rgba(16,37,66,0.12)",
        "calendar_holiday": "#e76f51",
        "calendar_note": "#2a9d8f",
    },
}

COUNTRIES = {
    "CN": "中国 Mainland",
    "TW": "台湾 Taiwan",
    "HK": "香港 Hong Kong",
    "US": "美国 United States",
    "JP": "日本 Japan",
    "KR": "韩国 Korea",
    "GB": "英国 United Kingdom",
}

WEEKDAY_LABELS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

WEATHER_CODE_MAP = {
    0: "晴朗",
    1: "大致晴",
    2: "局部多云",
    3: "阴天",
    45: "雾",
    48: "冻雾",
    51: "毛毛雨",
    53: "小雨",
    55: "中雨",
    56: "冻毛雨",
    57: "强冻毛雨",
    61: "小阵雨",
    63: "降雨",
    65: "大雨",
    66: "冻雨",
    67: "强冻雨",
    71: "小雪",
    73: "降雪",
    75: "大雪",
    77: "冰粒",
    80: "阵雨",
    81: "强阵雨",
    82: "暴雨",
    85: "阵雪",
    86: "强阵雪",
    95: "雷暴",
    96: "雷暴夹冰雹",
    99: "强雷暴夹冰雹",
}


@dataclass
class AlarmItem:
    time: str
    label: str
    repeat_daily: bool = True
    enabled: bool = True
    last_triggered: str = ""


class JsonStore:
    def __init__(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.data = self._load()

    def _default(self) -> Dict[str, Any]:
        return {
            "settings": {
                "theme": "Aurora Night",
                "clock_style": "Aurora Digital",
                "city": "Taipei",
                "weather_country": "TW",
                "holiday_regions": ["CN", "TW", "US", "JP"],
                "always_on_top": False,
            },
            "date_notes": {},
            "sticky_notes": [
                {
                    "title": "欢迎来到 LumiDesk",
                    "body": "这里可以写今天最重要的一件事。\n\n也可以当灵感便签纸用。",
                    "color": "#ffd166",
                },
                {
                    "title": "小惊喜",
                    "body": "试试切换主题和时钟样式，桌面氛围会完全不一样。",
                    "color": "#89f7fe",
                },
            ],
            "alarms": [asdict(AlarmItem(time="07:30", label="早安，开启新的一天", repeat_daily=True))],
        }

    def _load(self) -> Dict[str, Any]:
        if not DATA_FILE.exists():
            data = self._default()
            self._save_raw(data)
            return data
        try:
            return json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = self._default()
            self._save_raw(data)
            return data

    def _save_raw(self, payload: Dict[str, Any]) -> None:
        DATA_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def save(self) -> None:
        self._save_raw(self.data)


class Card(QFrame):
    def __init__(self, title: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(18, 16, 18, 16)
        self.layout.setSpacing(12)
        self.header = QLabel(title)
        self.header.setObjectName("cardTitle")
        self.layout.addWidget(self.header)


class DigitalClockFace(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.now = datetime.now()
        self.style_name = "Aurora Digital"
        self.setMinimumHeight(160)

    def set_style(self, style_name: str) -> None:
        self.style_name = style_name
        self.update()

    def set_time(self, now: datetime) -> None:
        self.now = now
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(8, 8, -8, -8)

        if self.style_name == "Minimal Flip":
            painter.setPen(Qt.NoPen)
            block_w = rect.width() / 6.8
            gap = 10
            items = list(self.now.strftime("%H%M%S"))
            x = rect.left()
            for idx, char in enumerate(items):
                box = QRectF(x, rect.top() + 18, block_w, rect.height() - 36)
                painter.setBrush(QColor(255, 255, 255, 28))
                painter.drawRoundedRect(box, 20, 20)
                painter.setPen(QColor("#ffffff"))
                font = QFont("Arial", int(rect.height() * 0.33), QFont.Bold)
                painter.setFont(font)
                painter.drawText(box, Qt.AlignCenter, char)
                painter.setPen(Qt.NoPen)
                x += block_w + gap
                if idx in (1, 3):
                    dot_rect = QRectF(x - 2, rect.top() + rect.height() * 0.35, 6, 6)
                    painter.setBrush(QColor(255, 255, 255, 180))
                    painter.drawEllipse(dot_rect)
                    painter.drawEllipse(QRectF(dot_rect.left(), dot_rect.top() + 18, 6, 6))
            painter.end()
            return

        if self.style_name == "Aurora Digital":
            painter.setPen(QColor(255, 255, 255, 220))
            time_font = QFont("Segoe UI", int(rect.height() * 0.34), QFont.Bold)
            painter.setFont(time_font)
            painter.drawText(rect, Qt.AlignCenter, self.now.strftime("%H:%M:%S"))
            painter.setPen(QColor(255, 255, 255, 150))
            sub_font = QFont("Segoe UI", 13)
            painter.setFont(sub_font)
            painter.drawText(rect.adjusted(0, 84, 0, 0), Qt.AlignCenter, self.now.strftime("%Y-%m-%d  %A"))
        else:
            painter.setPen(QColor(255, 255, 255, 240))
            time_font = QFont("Consolas", int(rect.height() * 0.32), QFont.Bold)
            painter.setFont(time_font)
            painter.drawText(rect.adjusted(0, -8, 0, 0), Qt.AlignCenter, self.now.strftime("%H:%M"))
            painter.setPen(QColor(255, 255, 255, 150))
            sub_font = QFont("Segoe UI", 12)
            painter.setFont(sub_font)
            painter.drawText(rect.adjusted(0, 70, 0, 0), Qt.AlignCenter, self.now.strftime("%S 秒 · %m/%d"))
        painter.end()


class AnalogClockFace(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.now = datetime.now()
        self.setMinimumHeight(220)

    def set_time(self, now: datetime) -> None:
        self.now = now
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        side = min(self.width(), self.height())
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.translate(self.width() / 2, self.height() / 2)
        painter.scale(side / 220.0, side / 220.0)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(255, 255, 255, 24))
        painter.drawEllipse(-96, -96, 192, 192)

        painter.setPen(QPen(QColor(255, 255, 255, 135), 2))
        for i in range(60):
            if i % 5 == 0:
                painter.drawLine(0, -82, 0, -92)
            else:
                painter.drawLine(0, -86, 0, -92)
            painter.rotate(6)

        hour = self.now.hour % 12 + self.now.minute / 60.0
        minute = self.now.minute + self.now.second / 60.0
        second = self.now.second

        painter.save()
        painter.rotate(30 * hour)
        painter.setPen(QPen(QColor("#ffffff"), 7, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(0, 10, 0, -48)
        painter.restore()

        painter.save()
        painter.rotate(6 * minute)
        painter.setPen(QPen(QColor(220, 240, 255), 4, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(0, 16, 0, -70)
        painter.restore()

        painter.save()
        painter.rotate(6 * second)
        painter.setPen(QPen(QColor("#ff8ea1"), 2, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(0, 18, 0, -78)
        painter.restore()

        painter.setBrush(QColor("#ffffff"))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPoint(0, 0), 5, 5)
        painter.end()


class ClockCard(Card):
    def __init__(self, store: JsonStore) -> None:
        super().__init__("🕒 时钟氛围区")
        self.store = store
        top = QHBoxLayout()
        self.greeting = QLabel()
        self.greeting.setObjectName("heroText")
        self.style_combo = QComboBox()
        self.style_combo.addItems(["Aurora Digital", "Orbit Analog", "Minimal Flip"])
        self.style_combo.setCurrentText(self.store.data["settings"].get("clock_style", "Aurora Digital"))
        top.addWidget(self.greeting)
        top.addStretch(1)
        top.addWidget(QLabel("样式"))
        top.addWidget(self.style_combo)
        self.layout.addLayout(top)

        self.digital_face = DigitalClockFace()
        self.analog_face = AnalogClockFace()
        self.clock_holder = QVBoxLayout()
        self.layout.addLayout(self.clock_holder)
        self.clock_holder.addWidget(self.digital_face)
        self.clock_holder.addWidget(self.analog_face)

        self.subtitle = QLabel()
        self.subtitle.setObjectName("mutedLabel")
        self.layout.addWidget(self.subtitle)
        self.layout.addStretch(1)

        self.style_combo.currentTextChanged.connect(self.on_style_changed)
        self.on_style_changed(self.style_combo.currentText())
        self.tick(datetime.now())

    def on_style_changed(self, style_name: str) -> None:
        self.store.data["settings"]["clock_style"] = style_name
        self.store.save()
        self.digital_face.set_style(style_name)
        is_analog = style_name == "Orbit Analog"
        self.digital_face.setVisible(not is_analog)
        self.analog_face.setVisible(is_analog)

    def tick(self, now: datetime) -> None:
        self.digital_face.set_time(now)
        self.analog_face.set_time(now)
        hour = now.hour
        if 5 <= hour < 12:
            msg = "早安，今天也发光。"
        elif 12 <= hour < 18:
            msg = "下午好，节奏正刚好。"
        elif 18 <= hour < 23:
            msg = "晚上好，适合整理灵感。"
        else:
            msg = "夜深了，也别忘记休息。"
        self.greeting.setText(msg)
        self.subtitle.setText(f"{now.strftime('%Y-%m-%d')} · {WEEKDAY_LABELS[now.weekday()]} · {now.strftime('%H:%M:%S')}")


class WeatherCard(Card):
    def __init__(self, store: JsonStore) -> None:
        super().__init__("🌤 天气")
        self.store = store

        row = QHBoxLayout()
        self.city_input = QLineEdit(self.store.data["settings"].get("city", "Taipei"))
        self.country_input = QLineEdit(self.store.data["settings"].get("weather_country", "TW"))
        self.country_input.setMaximumWidth(70)
        self.refresh_btn = QPushButton("刷新")
        row.addWidget(self.city_input, 1)
        row.addWidget(self.country_input)
        row.addWidget(self.refresh_btn)
        self.layout.addLayout(row)

        self.summary = QLabel("正在等待天气数据…")
        self.summary.setObjectName("heroText")
        self.detail = QLabel("")
        self.detail.setWordWrap(True)
        self.detail.setObjectName("mutedLabel")
        self.layout.addWidget(self.summary)
        self.layout.addWidget(self.detail)

        self.daily_table = QTableWidget(0, 3)
        self.daily_table.setHorizontalHeaderLabels(["日期", "天气", "温度"])
        self.daily_table.horizontalHeader().setStretchLastSection(True)
        self.daily_table.verticalHeader().setVisible(False)
        self.daily_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.daily_table.setSelectionMode(QTableWidget.NoSelection)
        self.daily_table.setMaximumHeight(180)
        self.layout.addWidget(self.daily_table)

        self.refresh_btn.clicked.connect(self.refresh)
        self.refresh()

    def _fetch_json(self, base_url: str, params: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{base_url}?{urllib.parse.urlencode(params, doseq=True)}"
        with urllib.request.urlopen(url, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def refresh(self) -> None:
        city = self.city_input.text().strip() or "Taipei"
        country = self.country_input.text().strip().upper() or "TW"
        self.store.data["settings"]["city"] = city
        self.store.data["settings"]["weather_country"] = country
        self.store.save()
        try:
            geo = self._fetch_json(
                WEATHER_GEOCODE,
                {"name": city, "count": 1, "language": "zh", "format": "json", "countryCode": country},
            )
            results = geo.get("results") or []
            if not results:
                raise ValueError("找不到该城市")
            place = results[0]
            lat, lon = place["latitude"], place["longitude"]
            tz = place.get("timezone", "auto")
            forecast = self._fetch_json(
                WEATHER_FORECAST,
                {
                    "latitude": lat,
                    "longitude": lon,
                    "timezone": tz,
                    "current": [
                        "temperature_2m",
                        "apparent_temperature",
                        "weather_code",
                        "wind_speed_10m",
                        "is_day",
                    ],
                    "daily": ["weather_code", "temperature_2m_max", "temperature_2m_min"],
                    "forecast_days": 5,
                },
            )
            current = forecast.get("current", {})
            weather_code = int(current.get("weather_code", 0))
            desc = WEATHER_CODE_MAP.get(weather_code, f"天气代码 {weather_code}")
            self.summary.setText(
                f"{place.get('name', city)} · {current.get('temperature_2m', '--')}°C · {desc}"
            )
            self.detail.setText(
                f"体感 {current.get('apparent_temperature', '--')}°C，风速 {current.get('wind_speed_10m', '--')} km/h。"
                f"\n坐标：{lat:.2f}, {lon:.2f} · 时区：{tz}"
            )
            daily = forecast.get("daily", {})
            times = daily.get("time", [])
            codes = daily.get("weather_code", [])
            maxs = daily.get("temperature_2m_max", [])
            mins = daily.get("temperature_2m_min", [])
            self.daily_table.setRowCount(len(times))
            for row, day_str in enumerate(times):
                label = datetime.fromisoformat(day_str).strftime("%m-%d")
                self.daily_table.setItem(row, 0, QTableWidgetItem(label))
                self.daily_table.setItem(row, 1, QTableWidgetItem(WEATHER_CODE_MAP.get(int(codes[row]), "--")))
                self.daily_table.setItem(row, 2, QTableWidgetItem(f"{mins[row]}° ~ {maxs[row]}°"))
            self.daily_table.resizeColumnsToContents()
        except Exception as exc:
            self.summary.setText("天气读取失败")
            self.detail.setText(f"原因：{exc}")
            self.daily_table.setRowCount(0)


class AlarmDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("添加闹钟")
        layout = QFormLayout(self)
        self.hour = QSpinBox()
        self.hour.setRange(0, 23)
        self.minute = QSpinBox()
        self.minute.setRange(0, 59)
        self.label_edit = QLineEdit("提醒一下自己")
        self.repeat_box = QCheckBox("每日重复")
        self.repeat_box.setChecked(True)
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self.accept)
        layout.addRow("小时", self.hour)
        layout.addRow("分钟", self.minute)
        layout.addRow("内容", self.label_edit)
        layout.addRow("", self.repeat_box)
        layout.addRow(save_btn)

    def result_item(self) -> AlarmItem:
        return AlarmItem(
            time=f"{self.hour.value():02d}:{self.minute.value():02d}",
            label=self.label_edit.text().strip() or "提醒一下自己",
            repeat_daily=self.repeat_box.isChecked(),
            enabled=True,
        )


class AlarmTimerCard(Card):
    alarmTriggered = Signal(str)

    def __init__(self, store: JsonStore) -> None:
        super().__init__("⏰ 定时与闹钟")
        self.store = store
        self.remaining_seconds = 0
        self.timer_running = False

        timer_group = QGroupBox("倒计时")
        timer_layout = QHBoxLayout(timer_group)
        self.min_spin = QSpinBox()
        self.min_spin.setRange(0, 180)
        self.min_spin.setValue(25)
        self.sec_spin = QSpinBox()
        self.sec_spin.setRange(0, 59)
        self.timer_label = QLabel("25:00")
        self.timer_label.setObjectName("heroText")
        self.start_timer_btn = QPushButton("开始")
        self.pause_timer_btn = QPushButton("暂停")
        self.reset_timer_btn = QPushButton("重置")
        timer_layout.addWidget(QLabel("分钟"))
        timer_layout.addWidget(self.min_spin)
        timer_layout.addWidget(QLabel("秒"))
        timer_layout.addWidget(self.sec_spin)
        timer_layout.addSpacing(10)
        timer_layout.addWidget(self.timer_label)
        timer_layout.addStretch(1)
        timer_layout.addWidget(self.start_timer_btn)
        timer_layout.addWidget(self.pause_timer_btn)
        timer_layout.addWidget(self.reset_timer_btn)
        self.layout.addWidget(timer_group)

        alarm_top = QHBoxLayout()
        alarm_top.addWidget(QLabel("闹钟列表"))
        alarm_top.addStretch(1)
        self.add_alarm_btn = QPushButton("添加")
        self.delete_alarm_btn = QPushButton("删除")
        alarm_top.addWidget(self.add_alarm_btn)
        alarm_top.addWidget(self.delete_alarm_btn)
        self.layout.addLayout(alarm_top)

        self.alarm_table = QTableWidget(0, 4)
        self.alarm_table.setHorizontalHeaderLabels(["时间", "内容", "重复", "状态"])
        self.alarm_table.horizontalHeader().setStretchLastSection(True)
        self.alarm_table.verticalHeader().setVisible(False)
        self.alarm_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.alarm_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.alarm_table.setMaximumHeight(220)
        self.layout.addWidget(self.alarm_table)

        self.timer_tick = QTimer(self)
        self.timer_tick.timeout.connect(self.on_timer_tick)

        self.start_timer_btn.clicked.connect(self.start_timer)
        self.pause_timer_btn.clicked.connect(self.pause_timer)
        self.reset_timer_btn.clicked.connect(self.reset_timer)
        self.add_alarm_btn.clicked.connect(self.add_alarm)
        self.delete_alarm_btn.clicked.connect(self.delete_alarm)
        self.alarm_table.cellDoubleClicked.connect(self.toggle_alarm)

        self.refresh_alarm_table()
        self.reset_timer()

    def alarms(self) -> List[AlarmItem]:
        return [AlarmItem(**item) for item in self.store.data.get("alarms", [])]

    def save_alarms(self, alarms_list: List[AlarmItem]) -> None:
        self.store.data["alarms"] = [asdict(item) for item in alarms_list]
        self.store.save()
        self.refresh_alarm_table()

    def refresh_alarm_table(self) -> None:
        alarms_list = self.alarms()
        self.alarm_table.setRowCount(len(alarms_list))
        for row, item in enumerate(alarms_list):
            self.alarm_table.setItem(row, 0, QTableWidgetItem(item.time))
            self.alarm_table.setItem(row, 1, QTableWidgetItem(item.label))
            self.alarm_table.setItem(row, 2, QTableWidgetItem("每天" if item.repeat_daily else "一次"))
            self.alarm_table.setItem(row, 3, QTableWidgetItem("开启" if item.enabled else "关闭"))
        self.alarm_table.resizeColumnsToContents()

    def start_timer(self) -> None:
        if self.remaining_seconds <= 0:
            self.remaining_seconds = self.min_spin.value() * 60 + self.sec_spin.value()
        if self.remaining_seconds <= 0:
            return
        self.timer_running = True
        self.timer_tick.start(1000)

    def pause_timer(self) -> None:
        self.timer_running = False
        self.timer_tick.stop()

    def reset_timer(self) -> None:
        self.pause_timer()
        self.remaining_seconds = self.min_spin.value() * 60 + self.sec_spin.value()
        self.update_timer_label()

    def on_timer_tick(self) -> None:
        if not self.timer_running:
            return
        self.remaining_seconds -= 1
        self.update_timer_label()
        if self.remaining_seconds <= 0:
            self.pause_timer()
            self.alarmTriggered.emit("倒计时结束，休息一下吧。")

    def update_timer_label(self) -> None:
        mins, secs = divmod(max(self.remaining_seconds, 0), 60)
        self.timer_label.setText(f"{mins:02d}:{secs:02d}")

    def add_alarm(self) -> None:
        dlg = AlarmDialog(self)
        if dlg.exec():
            alarms_list = self.alarms()
            alarms_list.append(dlg.result_item())
            alarms_list.sort(key=lambda x: x.time)
            self.save_alarms(alarms_list)

    def delete_alarm(self) -> None:
        row = self.alarm_table.currentRow()
        if row < 0:
            return
        alarms_list = self.alarms()
        alarms_list.pop(row)
        self.save_alarms(alarms_list)

    def toggle_alarm(self, row: int, column: int) -> None:
        alarms_list = self.alarms()
        alarms_list[row].enabled = not alarms_list[row].enabled
        self.save_alarms(alarms_list)

    def check_alarms(self, now: datetime) -> None:
        alarms_list = self.alarms()
        current_key = now.strftime("%Y-%m-%d %H:%M")
        changed = False
        for item in alarms_list:
            if not item.enabled:
                continue
            if now.strftime("%H:%M") == item.time and item.last_triggered != current_key:
                item.last_triggered = current_key
                self.alarmTriggered.emit(f"{item.time} · {item.label}")
                changed = True
                if not item.repeat_daily:
                    item.enabled = False
        if changed:
            self.save_alarms(alarms_list)


class CalendarCard(Card):
    def __init__(self, store: JsonStore) -> None:
        super().__init__("🗓 日历 / 节假日 / 节气")
        self.store = store
        self.updating_formats = False

        top = QHBoxLayout()
        self.region_boxes: Dict[str, QCheckBox] = {}
        selected_regions = set(self.store.data["settings"].get("holiday_regions", ["CN", "TW", "US", "JP"]))
        for code, label in COUNTRIES.items():
            box = QCheckBox(code)
            box.setToolTip(label)
            box.setChecked(code in selected_regions)
            box.stateChanged.connect(self.on_regions_changed)
            self.region_boxes[code] = box
            top.addWidget(box)
        top.addStretch(1)
        self.layout.addLayout(top)

        splitter = QSplitter(Qt.Horizontal)
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        splitter.addWidget(self.calendar)

        side = QWidget()
        side_layout = QVBoxLayout(side)
        self.info = QTextEdit()
        self.info.setReadOnly(True)
        self.info.setMinimumHeight(180)
        self.note_edit = QPlainTextEdit()
        self.note_edit.setPlaceholderText("写下这一天的安排、纪念、灵感…")
        note_btn_row = QHBoxLayout()
        self.save_note_btn = QPushButton("保存当天便签")
        self.clear_note_btn = QPushButton("清空")
        note_btn_row.addWidget(self.save_note_btn)
        note_btn_row.addWidget(self.clear_note_btn)
        self.upcoming_list = QListWidget()
        side_layout.addWidget(QLabel("日期详情"))
        side_layout.addWidget(self.info)
        side_layout.addWidget(QLabel("当日便签"))
        side_layout.addWidget(self.note_edit)
        side_layout.addLayout(note_btn_row)
        side_layout.addWidget(QLabel("近期节假日"))
        side_layout.addWidget(self.upcoming_list)
        splitter.addWidget(side)
        splitter.setSizes([460, 320])
        self.layout.addWidget(splitter)

        self.calendar.selectionChanged.connect(self.on_selection_changed)
        self.calendar.currentPageChanged.connect(self.refresh_formats)
        self.save_note_btn.clicked.connect(self.save_day_note)
        self.clear_note_btn.clicked.connect(self.clear_day_note)

        self.refresh_formats()
        self.on_selection_changed()

    def selected_regions(self) -> List[str]:
        return [code for code, box in self.region_boxes.items() if box.isChecked()]

    def on_regions_changed(self) -> None:
        self.store.data["settings"]["holiday_regions"] = self.selected_regions()
        self.store.save()
        self.refresh_formats()
        self.on_selection_changed()

    def refresh_formats(self) -> None:
        if self.updating_formats:
            return
        self.updating_formats = True
        self.calendar.setDateTextFormat(QDate(), QTextCharFormat())
        shown_year = self.calendar.yearShown()
        shown_month = self.calendar.monthShown()
        days_in_month = QDate(shown_year, shown_month, 1).daysInMonth()
        regions = self.selected_regions()
        holiday_maps = {}
        for code in regions:
            try:
                holiday_maps[code] = holidays.country_holidays(code, years=[shown_year])
            except Exception:
                holiday_maps[code] = {}

        for day in range(1, days_in_month + 1):
            qd = QDate(shown_year, shown_month, day)
            iso = qd.toString("yyyy-MM-dd")
            fmt = QTextCharFormat()
            notes = self.store.data.get("date_notes", {})
            is_note = bool(notes.get(iso, "").strip())
            holiday_hits = []
            py_date = date(shown_year, shown_month, day)
            for code, hol in holiday_maps.items():
                if py_date in hol:
                    holiday_hits.append(f"{code}: {hol.get(py_date)}")

            jieqi = self.get_jieqi(py_date)
            if holiday_hits and is_note:
                fmt.setBackground(QColor("#8ce99a"))
                fmt.setForeground(QColor("#102542"))
                fmt.setFontWeight(QFont.Bold)
            elif holiday_hits:
                fmt.setForeground(QColor("#d97706"))
                fmt.setFontWeight(QFont.Bold)
            elif jieqi:
                fmt.setForeground(QColor("#3e92cc"))
                fmt.setFontItalic(True)
            elif is_note:
                fmt.setForeground(QColor("#2f8f6b"))
                fmt.setFontUnderline(True)
            self.calendar.setDateTextFormat(qd, fmt)

        self.populate_upcoming_list()
        self.updating_formats = False

    def populate_upcoming_list(self) -> None:
        self.upcoming_list.clear()
        today = date.today()
        regions = self.selected_regions()
        upcoming: List[tuple[date, str]] = []
        for code in regions:
            try:
                hols = holidays.country_holidays(code, years=[today.year, today.year + 1])
                for d, name in hols.items():
                    if d >= today:
                        upcoming.append((d, f"{d.isoformat()} · {code} · {name}"))
            except Exception:
                continue
        for d in sorted(set(upcoming))[:12]:
            self.upcoming_list.addItem(d[1])

    def get_jieqi(self, py_date: date) -> str:
        try:
            lunar = Solar.fromYmd(py_date.year, py_date.month, py_date.day).getLunar()
            exact = lunar.getJieQi()
            if exact:
                return exact
            return ""
        except Exception:
            return ""

    def build_detail_text(self, py_date: date) -> str:
        lines = [f"公历：{py_date.isoformat()}  {WEEKDAY_LABELS[py_date.weekday()]}"]
        try:
            lunar = Solar.fromYmd(py_date.year, py_date.month, py_date.day).getLunar()
            lunar_text = f"农历：{lunar.getMonthInChinese()}月{lunar.getDayInChinese()}"
            ganzhi = f"干支：{lunar.getYearInGanZhi()}年 {lunar.getMonthInGanZhi()}月 {lunar.getDayInGanZhi()}日"
            lines.append(lunar_text)
            lines.append(ganzhi)
            festivals = []
            try:
                festivals.extend(lunar.getFestivals())
            except Exception:
                pass
            try:
                festivals.extend(lunar.getOtherFestivals())
            except Exception:
                pass
            jieqi = self.get_jieqi(py_date)
            if jieqi:
                lines.append(f"节气：{jieqi}")
            if festivals:
                lines.append(f"传统节日：{'、'.join(festivals)}")
        except Exception:
            pass

        for code in self.selected_regions():
            try:
                hols = holidays.country_holidays(code, years=[py_date.year])
                if py_date in hols:
                    lines.append(f"{code} 假日：{hols.get(py_date)}")
            except Exception:
                continue

        note = self.store.data.get("date_notes", {}).get(py_date.isoformat(), "").strip()
        if note:
            lines.append("\n【当日便签】")
            lines.append(note)
        return "\n".join(lines)

    def on_selection_changed(self) -> None:
        py_date = self.calendar.selectedDate().toPython()
        iso = py_date.isoformat()
        self.info.setPlainText(self.build_detail_text(py_date))
        self.note_edit.setPlainText(self.store.data.get("date_notes", {}).get(iso, ""))

    def save_day_note(self) -> None:
        py_date = self.calendar.selectedDate().toPython()
        iso = py_date.isoformat()
        self.store.data.setdefault("date_notes", {})[iso] = self.note_edit.toPlainText().rstrip()
        self.store.save()
        self.refresh_formats()
        self.on_selection_changed()

    def clear_day_note(self) -> None:
        py_date = self.calendar.selectedDate().toPython()
        iso = py_date.isoformat()
        self.store.data.setdefault("date_notes", {}).pop(iso, None)
        self.note_edit.clear()
        self.store.save()
        self.refresh_formats()
        self.on_selection_changed()


class StickyNotesCard(Card):
    def __init__(self, store: JsonStore) -> None:
        super().__init__("📝 便签纸")
        self.store = store

        layout = QHBoxLayout()
        left = QVBoxLayout()
        self.list_widget = QListWidget()
        btn_row = QHBoxLayout()
        self.add_btn = QPushButton("新增")
        self.del_btn = QPushButton("删除")
        btn_row.addWidget(self.add_btn)
        btn_row.addWidget(self.del_btn)
        left.addWidget(self.list_widget)
        left.addLayout(btn_row)

        right = QVBoxLayout()
        self.title_edit = QLineEdit()
        self.color_btn = QPushButton("选择便签颜色")
        self.body_edit = QPlainTextEdit()
        self.save_btn = QPushButton("保存便签")
        right.addWidget(QLabel("标题"))
        right.addWidget(self.title_edit)
        right.addWidget(self.color_btn)
        right.addWidget(QLabel("内容"))
        right.addWidget(self.body_edit)
        right.addWidget(self.save_btn)
        layout.addLayout(left, 1)
        layout.addLayout(right, 2)
        self.layout.addLayout(layout)

        self.current_color = "#ffd166"
        self.add_btn.clicked.connect(self.add_note)
        self.del_btn.clicked.connect(self.delete_note)
        self.save_btn.clicked.connect(self.save_current_note)
        self.color_btn.clicked.connect(self.pick_color)
        self.list_widget.currentRowChanged.connect(self.load_note)

        self.refresh_list()
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)

    def notes(self) -> List[Dict[str, str]]:
        return self.store.data.setdefault("sticky_notes", [])

    def refresh_list(self) -> None:
        self.list_widget.clear()
        for item in self.notes():
            title = item.get("title") or "未命名便签"
            display = QListWidgetItem(title)
            display.setBackground(QColor(item.get("color", "#ffd166")))
            self.list_widget.addItem(display)

    def add_note(self) -> None:
        self.notes().append({"title": "新的便签", "body": "", "color": "#ffd166"})
        self.store.save()
        self.refresh_list()
        self.list_widget.setCurrentRow(self.list_widget.count() - 1)

    def delete_note(self) -> None:
        row = self.list_widget.currentRow()
        if row < 0:
            return
        self.notes().pop(row)
        self.store.save()
        self.refresh_list()
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(max(0, row - 1))
        else:
            self.title_edit.clear()
            self.body_edit.clear()

    def load_note(self, row: int) -> None:
        if row < 0 or row >= len(self.notes()):
            return
        item = self.notes()[row]
        self.title_edit.setText(item.get("title", ""))
        self.body_edit.setPlainText(item.get("body", ""))
        self.current_color = item.get("color", "#ffd166")
        self.color_btn.setStyleSheet(f"background:{self.current_color}; color:#000;")

    def save_current_note(self) -> None:
        row = self.list_widget.currentRow()
        if row < 0:
            self.add_note()
            row = self.list_widget.currentRow()
        self.notes()[row] = {
            "title": self.title_edit.text().strip() or "未命名便签",
            "body": self.body_edit.toPlainText().rstrip(),
            "color": self.current_color,
        }
        self.store.save()
        self.refresh_list()
        self.list_widget.setCurrentRow(row)

    def pick_color(self) -> None:
        color = QColorDialog.getColor(QColor(self.current_color), self, "选择便签颜色")
        if color.isValid():
            self.current_color = color.name()
            self.color_btn.setStyleSheet(f"background:{self.current_color}; color:#000;")


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.store = JsonStore()
        self.setWindowTitle(f"{APP_NAME} · 惊喜桌面助手")
        self.resize(1500, 940)

        app_icon_path = resource_path("assets", "lumidesk.png")
        app_icon = QIcon(str(app_icon_path)) if app_icon_path.exists() else self.style().standardIcon(QStyle.SP_ComputerIcon)
        self.setWindowIcon(app_icon)

        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(app_icon)
        self.tray.setToolTip(APP_NAME)
        tray_menu = self.menuBar().addMenu("系统")
        show_action = QAction("显示窗口", self)
        show_action.triggered.connect(self.showNormal)
        tray_menu.addAction(show_action)
        self.always_top_action = QAction("窗口置顶", self, checkable=True)
        self.always_top_action.setChecked(self.store.data["settings"].get("always_on_top", False))
        self.always_top_action.triggered.connect(self.toggle_always_on_top)
        tray_menu.addAction(self.always_top_action)
        self.tray.show()

        root = QWidget()
        self.setCentralWidget(root)
        main_layout = QVBoxLayout(root)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(14)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        app_title = QLabel("LumiDesk")
        app_title.setObjectName("appTitle")
        app_subtitle = QLabel("把时钟、日历、天气、提醒和便签，做成一个会发光的桌面角落。")
        app_subtitle.setObjectName("mutedLabel")
        title_box.addWidget(app_title)
        title_box.addWidget(app_subtitle)
        header.addLayout(title_box)
        header.addStretch(1)
        header.addWidget(QLabel("主题"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(THEMES.keys())
        self.theme_combo.setCurrentText(self.store.data["settings"].get("theme", "Aurora Night"))
        header.addWidget(self.theme_combo)
        main_layout.addLayout(header)

        grid = QGridLayout()
        grid.setSpacing(14)
        main_layout.addLayout(grid, 1)

        self.clock_card = ClockCard(self.store)
        self.weather_card = WeatherCard(self.store)
        self.calendar_card = CalendarCard(self.store)
        self.alarm_card = AlarmTimerCard(self.store)
        self.notes_card = StickyNotesCard(self.store)

        grid.addWidget(self.clock_card, 0, 0, 1, 1)
        grid.addWidget(self.weather_card, 0, 1, 1, 1)
        grid.addWidget(self.calendar_card, 1, 0, 1, 2)
        grid.addWidget(self.alarm_card, 2, 0, 1, 1)
        grid.addWidget(self.notes_card, 2, 1, 1, 1)

        grid.setRowStretch(1, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        self.theme_combo.currentTextChanged.connect(self.apply_theme)
        self.alarm_card.alarmTriggered.connect(self.notify)

        self.tick_timer = QTimer(self)
        self.tick_timer.timeout.connect(self.on_tick)
        self.tick_timer.start(1000)

        self.apply_theme(self.theme_combo.currentText())
        self.toggle_always_on_top(self.always_top_action.isChecked())
        self.on_tick()

    def toggle_always_on_top(self, checked: bool) -> None:
        self.store.data["settings"]["always_on_top"] = checked
        self.store.save()
        self.setWindowFlag(Qt.WindowStaysOnTopHint, checked)
        self.show()

    def apply_theme(self, theme_name: str) -> None:
        self.store.data["settings"]["theme"] = theme_name
        self.store.save()
        theme = THEMES[theme_name]
        self.setStyleSheet(
            f"""
            QWidget {{
                background: {theme['bg']};
                color: {theme['text']};
                font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
                font-size: 13px;
            }}
            QMainWindow::separator {{ background: transparent; }}
            QFrame#card {{
                background: {theme['card']};
                border: 1px solid {theme['border']};
                border-radius: 22px;
            }}
            QLabel#appTitle {{ font-size: 34px; font-weight: 800; }}
            QLabel#cardTitle {{ font-size: 18px; font-weight: 700; }}
            QLabel#heroText {{ font-size: 22px; font-weight: 700; }}
            QLabel#mutedLabel {{ color: {theme['muted']}; }}
            QLineEdit, QComboBox, QSpinBox, QTextEdit, QPlainTextEdit, QListWidget, QTableWidget, QCalendarWidget {{
                background: {theme['card2']};
                border: 1px solid {theme['border']};
                border-radius: 14px;
                padding: 8px;
                selection-background-color: {theme['accent2']};
            }}
            QPushButton, QToolButton {{
                background: {theme['accent2']};
                color: white;
                border: none;
                border-radius: 12px;
                padding: 10px 14px;
                font-weight: 700;
            }}
            QPushButton:hover {{ background: {theme['accent']}; }}
            QGroupBox {{
                border: 1px solid {theme['border']};
                border-radius: 16px;
                margin-top: 10px;
                padding-top: 10px;
                background: {theme['card2']};
                font-weight: 700;
            }}
            QGroupBox::title {{ left: 12px; padding: 0 6px; }}
            QHeaderView::section {{
                background: {theme['card']};
                border: none;
                padding: 8px;
                font-weight: 700;
            }}
            QScrollBar:vertical {{ width: 10px; background: transparent; margin: 6px; }}
            QScrollBar::handle:vertical {{ background: {theme['accent2']}; border-radius: 5px; min-height: 20px; }}
            """
        )
        self.clock_card.update()
        self.calendar_card.refresh_formats()

    def notify(self, message: str) -> None:
        QApplication.beep()
        self.tray.showMessage(APP_NAME, message, QSystemTrayIcon.Information, 5000)
        QMessageBox.information(self, "提醒", message)

    def on_tick(self) -> None:
        now = datetime.now()
        self.clock_card.tick(now)
        self.alarm_card.check_alarms(now)


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    icon_path = resource_path("assets", "lumidesk.png")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
