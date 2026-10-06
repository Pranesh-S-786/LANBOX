"""
LANBOX Packaging & Build Script.
Packages the LANBOX Client and Server into standalone Windows executables (.exe) using PyInstaller.
"""
import subprocess
import sys
import os
import shutil

def build():
    print("=" * 60)
    print("           LANBOX STANDALONE EXECUTABLE BUILDER            ")
    print("=" * 60)

    # 1. Ensure PyInstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("[*] PyInstaller not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    # Base paths
    root_dir = os.path.dirname(os.path.abspath(__file__))
    dist_dir = os.path.join(root_dir, "dist")
    build_dir = os.path.join(root_dir, "build")

    # Clean previous builds
    for d in [dist_dir, build_dir]:
        if os.path.exists(d):
            try:
                shutil.rmtree(d)
            except Exception:
                pass

    print("\n[1/2] Building LANBOX Server (lanbox_server.exe)...")
    server_entry = os.path.join(root_dir, "server", "main_server.py")
    server_cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=LANBOX_Server",
        "--onefile",
        "--console",
        "--paths=" + root_dir,
        server_entry
    ]
    subprocess.check_call(server_cmd)

    print("\n[2/2] Building LANBOX Client (lanbox_client.exe)...")
    client_entry = os.path.join(root_dir, "client", "main_client.py")
    client_cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=LANBOX_Client",
        "--onefile",
        "--windowed",  # No console window for desktop GUI
        "--paths=" + root_dir,
        client_entry
    ]
    subprocess.check_call(client_cmd)

    print("\n" + "=" * 60)
    print("                BUILD SUCCESSFUL!                          ")
    print("=" * 60)
    print(f"Generated standalone binaries are in: {dist_dir}")
    print(" - LANBOX_Server.exe (Run on the host machine)")
    print(" - LANBOX_Client.exe (Distribute to all Wi-Fi users)")
    print("=" * 60)

if __name__ == "__main__":
    build()
