#!/usr/bin/env python3
"""
launcher_simple_improved.py
- 啟動 backend (python backend/app.py --host --port)
- 啟動 frontend (flutter run -d all)，自動找 flutter 或 使用 FLUTTER_PATH
- Windows 上若是 .bat，會用 shell=True fallback
"""
import subprocess
import signal
import sys
import time
from pathlib import Path
import argparse
import shutil
import os
import socket

PROJECT_ROOT = Path(__file__).parent.resolve()
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIR = PROJECT_ROOT / "frontend"

processes = {}

def is_port_free(host: str, port: int) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind((host, port))
        s.close()
        return True
    except OSError:
        return False

def find_free_port(start_port: int, host="0.0.0.0", max_tries=50):
    port = start_port
    for _ in range(max_tries):
        if is_port_free(host, port):
            return port
        port += 1
    return None

def start_backend(port, host="0.0.0.0"):
    if not BACKEND_DIR.exists():
        print(f"❌ 找不到 backend 目錄: {BACKEND_DIR}")
        return None
    backend_app = BACKEND_DIR / "app.py"
    if not backend_app.exists():
        print(f"❌ 找不到 backend/app.py: {backend_app}")
        return None

    cmd = [sys.executable, "app.py", "--host", host, "--port", str(port)]
    print("🔧 啟動 Backend:", " ".join(cmd), "cwd=", BACKEND_DIR)
    p = subprocess.Popen(cmd, cwd=str(BACKEND_DIR))
    return p

def start_frontend():
    if not FRONTEND_DIR.exists():
        print(f"❌ 找不到 frontend 目錄: {FRONTEND_DIR}")
        return None

    # 1) 先嘗試 which
    flutter_exec = shutil.which("flutter")
    # 2) 若找不到，嘗試環境變數
    if not flutter_exec:
        flutter_exec = os.environ.get("FLUTTER_PATH") or os.environ.get("FLUTTER_HOME")
    # 3) 最後嘗試常見路徑
    if not flutter_exec:
        candidate = Path("C:/flutter/bin/flutter")
        if candidate.exists():
            flutter_exec = str(candidate)
        candidate_bat = Path("C:/flutter/bin/flutter.bat")
        if not flutter_exec and candidate_bat.exists():
            flutter_exec = str(candidate_bat)

    if not flutter_exec:
        print("⚠️ 找不到 `flutter` 可執行檔（未在 PATH）。已跳過 Frontend 啟動。")
        print("   → 可先在同一個終端把 C:\\flutter\\bin 加到 PATH，或設定 FLUTTER_PATH 環境變數")
        return None

    # 如果路徑是 msys style (例如 /c/flutter/...), 嘗試轉成 windows 路徑
    if str(flutter_exec).startswith("/"):
        parts = str(flutter_exec).lstrip("/").split("/")
        if parts:
            drive = parts[0].upper() + ":"
            rest = "\\".join(parts[1:])
            flutter_exec = drive + "\\" + rest
            if flutter_exec.endswith("flutter"):
                flutter_exec += ".bat" if os.name == "nt" else ""

    # 若是 .bat，就用 shell=True（可以確保 Windows cmd 會處理 .bat）
    use_shell = False
    if str(flutter_exec).lower().endswith(".bat"):
        use_shell = True

    cmd_list = [str(flutter_exec), "run", "-d", "all"]

    print("📱 啟動 Frontend:", " ".join(cmd_list), "cwd=", FRONTEND_DIR, "shell=", use_shell)

    try:
        if use_shell:
            # 使用 shell 並把 command 組成字串（在 Windows 上會透過 cmd.exe 執行 .bat）
            cmd_str = f'"{flutter_exec}" run -d all'
            p = subprocess.Popen(cmd_str, cwd=str(FRONTEND_DIR), shell=True)
        else:
            p = subprocess.Popen(cmd_list, cwd=str(FRONTEND_DIR))
        return p
    except FileNotFoundError as e:
        print("❌ 無法啟動 flutter (FileNotFoundError):", e)
        print("   檢查是否在同一個終端設定了 PATH，或試試 `$env:PATH += \";C:\\flutter\\bin\"`（PowerShell）")
        return None
    except Exception as e:
        print("❌ 啟動 Frontend 時發生例外:", e)
        return None

def stop_all():
    print("\n🛑 停止所有服務...")
    for name, p in list(processes.items()):
        try:
            if p and p.poll() is None:
                print(f"  停止 {name} (pid={p.pid})...")
                p.terminate()
                p.wait(timeout=5)
        except Exception:
            try:
                p.kill()
            except Exception:
                pass
    print("✅ 已停止")

def signal_handler(signum, frame):
    print(f"\n🔔 收到訊號 {signum}，準備關閉...")
    stop_all()
    sys.exit(0)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-frontend", action="store_true", help="跳過 Frontend 啟動")
    parser.add_argument("--backend-port", type=int, default=5000, help="建議後端起始埠號")
    parser.add_argument("--host", default="0.0.0.0", help="Backend host")
    args = parser.parse_args()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    free_port = find_free_port(args.backend_port, host=args.host, max_tries=50)
    if free_port is None:
        print(f"❌ 無法找到可用埠，從 {args.backend_port} 開始搜尋失敗")
        sys.exit(1)
    if free_port != args.backend_port:
        print(f"⚠️ 埠 {args.backend_port} 被佔用，改用 {free_port}")

    processes['backend'] = start_backend(free_port, host=args.host)

    if not args.skip_frontend:
        processes['frontend'] = start_frontend()
    else:
        print("ℹ️ 已選擇跳過 Frontend 啟動 (--skip-frontend)")

    try:
        while True:
            alive = False
            for name, p in processes.items():
                if p is None:
                    continue
                if p.poll() is None:
                    alive = True
                else:
                    print(f"⚠️ {name} 已退出 (code={p.returncode})")
            if not alive:
                print("所有子程序已結束。")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🔔 使用者中斷")
    finally:
        stop_all()

if __name__ == "__main__":
    main()
