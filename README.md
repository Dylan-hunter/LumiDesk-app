# LumiDesk

一个偏「高级桌面挂件 / 轻工作台」风格的 Python 桌面应用，集成了：

- 可切换样式的时钟（Aurora Digital / Orbit Analog / Minimal Flip）
- 倒计时与闹钟
- 日历
- 国内外节假日（可勾选地区）
- 24 节气与农历信息
- 日历便签
- 天气查询（城市搜索）
- 便签纸
- 主题切换
- 窗口置顶

## 项目结构

```text
surprise_desktop_app/
├─ main.py
├─ requirements.txt
├─ LumiDesk.spec
├─ build_windows_exe.bat
├─ version_info.txt
├─ assets/
│  ├─ lumidesk.png
│  └─ lumidesk.ico
└─ README.md
```

---

## 直接运行源码

### 1）安装 Python 3.10+
推荐 Python 3.11 或 3.12。

### 2）安装依赖
```bash
pip install -r requirements.txt
```

### 3）启动应用
```bash
python main.py
```

---

## Windows 打包成 EXE

### 最简单的方法
在 **Windows 电脑** 上双击：

```text
build_windows_exe.bat
```

它会自动完成：
- 创建 `.venv` 虚拟环境
- 安装依赖
- 安装 `pyinstaller`
- 根据 `LumiDesk.spec` 打包

打包完成后，exe 在：

```text
dist\LumiDesk.exe
```

### 手动命令方式
```bash
py -3 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt pyinstaller
pyinstaller --clean --noconfirm LumiDesk.spec
```

---

## 分发给别人怎么用

你可以把下面这个文件直接发给别人：

```text
dist\LumiDesk.exe
```

对方理论上可以双击直接运行，不需要再安装 Python。

如果你更稳一点，也可以把整个 `dist` 文件夹一起打包成 zip 再发给别人。

---

## 数据保存位置

应用会把便签、闹钟、设置保存在：

- **Windows**: `%APPDATA%\LumiDesk\data.json`
- **macOS / Linux**: `~/.lumidesk/data.json`

---

## 小说明

- 天气使用 Open-Meteo 接口，输入城市名 + 国家代码（如 `Taipei / TW`、`Shanghai / CN`、`Tokyo / JP`）即可。
- 双击闹钟表格行可以开关闹钟。
- 日历右侧可以记录某一天的便签。
- 月视图中：
  - 假日会高亮
  - 节气会变色
  - 写过便签的日期会有提示样式

---

## 如果打包失败，优先检查

### 1）Python 版本太新或太旧
优先用：
- Python 3.11
- Python 3.12

### 2）第一次打包被防火墙或杀毒拦截
Windows Defender 有时会对新生成的 exe 比较敏感，属于常见情况。

### 3）虚拟环境里依赖没装完整
重新执行：
```bash
pip install -r requirements.txt pyinstaller
```

### 4）想彻底重打包
删除这些目录后再重新执行：
```text
build/
dist/
__pycache__/
```

---

## 适合继续升级的方向

- 开机自启
- 更强的重复提醒（工作日 / 指定星期）
- 城市自动定位
- 番茄钟统计
- 多城市天气看板
- 云同步
- 桌面悬浮小组件模式
- 磨砂玻璃 / 亚克力视觉升级


## GitHub 云端打包 EXE

你不想在本地安装 PyInstaller，也可以直接用 **GitHub Actions** 云端生成 Windows exe。

项目里已经带好了工作流文件：

```text
.github/workflows/build-windows.yml
```

### 用法

1. 新建一个 GitHub 仓库
2. 把这个项目全部上传到仓库根目录
3. 打开仓库的 **Actions**
4. 找到 **Build LumiDesk Windows EXE**
5. 点击 **Run workflow**
6. 等待构建完成后，在该次运行页面底部下载 **LumiDesk-Windows-EXE** artifact

下载下来后，里面就会有：

```text
LumiDesk.exe
```

### 哪些文件一定要传到 GitHub

```text
main.py
requirements.txt
LumiDesk.spec
version_info.txt
assets/
.github/workflows/build-windows.yml
```
