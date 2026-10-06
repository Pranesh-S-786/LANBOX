"""
Tkinter GUI for LANBOX Client.
Provides a modern, clean interface for login, registration, online user tracking,
public lobby chat, and 1-to-1 direct messaging.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from common.config import DEFAULT_SERVER_PORT, DEFAULT_CLIENT_CONNECT_HOST, TYPE_DIRECT_MSG, TYPE_BROADCAST_MSG
from client.client_core import LANBoxClient

class LANBoxGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("LANBOX - LAN Collaboration & Chat")
        self.root.geometry("900x600")
        self.root.minsize(750, 480)

        # Core networking client
        self.client = LANBoxClient()
        self.client.on_message_received = self._on_message_received_safe
        self.client.on_user_list_updated = self._on_user_list_updated_safe
        self.client.on_history_received = self._on_history_received_safe
        self.client.on_disconnected = self._on_disconnected_safe

        # Active conversation target: '__public__' for Public Lobby, or username string for direct chat
        self.current_target = '__public__'
        self.user_online_status = {}  # {username: bool}
        self.chat_history_cache = {
            '__public__': []  # list of msg dicts
        }

        # Setup modern TTK styles and colors
        self._setup_styles()

        # Container frame for switching screens
        self.container = ttk.Frame(self.root)
        self.container.pack(fill="both", expand=True)

        # Show initial authentication screen
        self.show_auth_screen()

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')

        # Color Palette
        self.BG_MAIN = "#f5f7fb"
        self.BG_SIDEBAR = "#1e293b"
        self.TEXT_SIDEBAR = "#e2e8f0"
        self.ACCENT_COLOR = "#2563eb"
        self.ONLINE_GREEN = "#10b981"
        self.OFFLINE_GRAY = "#94a3b8"

        self.root.configure(bg=self.BG_MAIN)
        self.style.configure("TFrame", background=self.BG_MAIN)
        self.style.configure("TLabel", background=self.BG_MAIN, font=("Segoe UI", 10))
        self.style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"), foreground="#1e293b")
        self.style.configure("SubHeader.TLabel", font=("Segoe UI", 9), foreground="#64748b")
        self.style.configure("Status.TLabel", font=("Segoe UI", 9, "italic"), foreground="#dc2626")

        self.style.configure("Primary.TButton",
                             font=("Segoe UI", 10, "bold"),
                             background=self.ACCENT_COLOR,
                             foreground="#ffffff",
                             padding=6)
        self.style.map("Primary.TButton",
                       background=[("active", "#1d4ed8")])

        self.style.configure("Secondary.TButton",
                             font=("Segoe UI", 10),
                             padding=6)

    # -------------------------------------------------------------------------
    # Screen 1: Authentication (Login / Register)
    # -------------------------------------------------------------------------
    def show_auth_screen(self):
        # Clear container
        for widget in self.container.winfo_children():
            widget.destroy()

        auth_frame = ttk.Frame(self.container, padding="30 20")
        auth_frame.place(relx=0.5, rely=0.5, anchor="center")

        # Title Card
        title_lbl = ttk.Label(auth_frame, text="📦 LANBOX", style="Header.TLabel", font=("Segoe UI", 22, "bold"))
        title_lbl.pack(pady=(0, 2))
        sub_lbl = ttk.Label(auth_frame, text="LAN-Based Communication & Collaboration Platform", style="SubHeader.TLabel")
        sub_lbl.pack(pady=(0, 20))

        # Inputs Card
        card = ttk.LabelFrame(auth_frame, text="Connect & Sign In", padding="20 15")
        card.pack(fill="x", expand=True)

        # Server IP & Port
        conn_grid = ttk.Frame(card)
        conn_grid.pack(fill="x", pady=5)

        ttk.Label(conn_grid, text="Server IP:").grid(row=0, column=0, sticky="w", padx=(0, 5))
        self.host_entry = ttk.Entry(conn_grid, width=16)
        self.host_entry.insert(0, DEFAULT_CLIENT_CONNECT_HOST)
        self.host_entry.grid(row=0, column=1, padx=(0, 10))

        ttk.Label(conn_grid, text="Port:").grid(row=0, column=2, sticky="w", padx=(0, 5))
        self.port_entry = ttk.Entry(conn_grid, width=8)
        self.port_entry.insert(0, str(DEFAULT_SERVER_PORT))
        self.port_entry.grid(row=0, column=3)

        # Username
        ttk.Label(card, text="Username:").pack(anchor="w", pady=(10, 2))
        self.user_entry = ttk.Entry(card, width=32, font=("Segoe UI", 10))
        self.user_entry.pack(fill="x")
        self.user_entry.focus()

        # Password
        ttk.Label(card, text="Password:").pack(anchor="w", pady=(10, 2))
        self.pass_entry = ttk.Entry(card, width=32, show="•", font=("Segoe UI", 10))
        self.pass_entry.pack(fill="x")
        self.pass_entry.bind("<Return>", lambda e: self._handle_auth("login"))

        # Status Message Label
        self.auth_status_lbl = ttk.Label(card, text="", style="Status.TLabel", wraplength=280)
        self.auth_status_lbl.pack(pady=(8, 4))

        # Buttons
        btn_frame = ttk.Frame(card)
        btn_frame.pack(fill="x", pady=(10, 5))

        self.login_btn = ttk.Button(btn_frame, text="Log In", style="Primary.TButton", command=lambda: self._handle_auth("login"))
        self.login_btn.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self.reg_btn = ttk.Button(btn_frame, text="Register", style="Secondary.TButton", command=lambda: self._handle_auth("register"))
        self.reg_btn.pack(side="right", fill="x", expand=True, padx=(5, 0))

    def _handle_auth(self, action: str):
        host = self.host_entry.get().strip()
        port_str = self.port_entry.get().strip()
        username = self.user_entry.get().strip()
        password = self.pass_entry.get()

        if not host or not port_str:
            self.auth_status_lbl.config(text="Please specify Server IP and Port.", foreground="#dc2626")
            return
        try:
            port = int(port_str)
        except ValueError:
            self.auth_status_lbl.config(text="Port must be a valid number.", foreground="#dc2626")
            return

        if not username or not password:
            self.auth_status_lbl.config(text="Username and password are required.", foreground="#dc2626")
            return

        # Connect to server if not connected
        if not self.client.is_connected:
            self.auth_status_lbl.config(text="Connecting to server...", foreground="#2563eb")
            self.root.update()
            ok, msg = self.client.connect(host, port)
            if not ok:
                self.auth_status_lbl.config(text=f"Connection error: {msg}", foreground="#dc2626")
                return

        if action == "register":
            self.auth_status_lbl.config(text="Registering user...", foreground="#2563eb")
            self.root.update()
            ok, msg = self.client.register(username, password)
            if ok:
                self.auth_status_lbl.config(text=f"{msg} You can now log in!", foreground="#16a34a")
            else:
                self.auth_status_lbl.config(text=f"Registration failed: {msg}", foreground="#dc2626")
        
        elif action == "login":
            self.auth_status_lbl.config(text="Logging in...", foreground="#2563eb")
            self.root.update()
            ok, msg = self.client.login(username, password)
            if ok:
                # Successfully logged in -> open Main Chat GUI
                self.show_main_chat_screen()
                # Request initial public history and user list
                self.client.request_history('__public__')
                self.client.refresh_user_list()
            else:
                self.auth_status_lbl.config(text=f"Login failed: {msg}", foreground="#dc2626")

    # -------------------------------------------------------------------------
    # Screen 2: Main Chat Application Screen
    # -------------------------------------------------------------------------
    def show_main_chat_screen(self):
        for widget in self.container.winfo_children():
            widget.destroy()

        # Top App Header Bar
        top_bar = tk.Frame(self.container, bg="#0f172a", height=50)
        top_bar.pack(side="top", fill="x")

        title_lbl = tk.Label(top_bar, text="📦 LANBOX", font=("Segoe UI", 12, "bold"), fg="#38bdf8", bg="#0f172a")
        title_lbl.pack(side="left", padx=(15, 10), pady=10)

        user_info = f"Logged in as: {self.client.current_user}"
        user_lbl = tk.Label(top_bar, text=user_info, font=("Segoe UI", 10), fg="#f8fafc", bg="#0f172a")
        user_lbl.pack(side="left", padx=10, pady=10)

        server_info = f"Server: {self.client.server_host}:{self.client.server_port}"
        server_lbl = tk.Label(top_bar, text=server_info, font=("Segoe UI", 9), fg="#94a3b8", bg="#0f172a")
        server_lbl.pack(side="left", padx=10, pady=10)

        logout_btn = tk.Button(top_bar, text="Logout", font=("Segoe UI", 9), bg="#ef4444", fg="white",
                               relief="flat", padx=10, pady=2, command=self._handle_logout)
        logout_btn.pack(side="right", padx=15, pady=10)

        # Body Layout: Sidebar (Left) + Chat Area (Right)
        body = ttk.Frame(self.container)
        body.pack(side="bottom", fill="both", expand=True)

        # ----------------- Left Sidebar -----------------
        sidebar = tk.Frame(body, bg=self.BG_SIDEBAR, width=240)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        # Public Lobby Shortcut Button
        lobby_btn = tk.Button(sidebar, text="📢 Public LAN Lobby", font=("Segoe UI", 10, "bold"),
                              bg="#334155", fg="white", relief="flat", anchor="w", padx=12, pady=8,
                              command=lambda: self._select_conversation('__public__'))
        lobby_btn.pack(fill="x", padx=10, pady=(15, 10))

        # Users Section Title
        users_title = tk.Label(sidebar, text="DIRECT MESSAGES", font=("Segoe UI", 8, "bold"),
                               fg="#94a3b8", bg=self.BG_SIDEBAR, anchor="w")
        users_title.pack(fill="x", padx=14, pady=(10, 4))

        # Scrollable Users List
        users_list_frame = tk.Frame(sidebar, bg=self.BG_SIDEBAR)
        users_list_frame.pack(fill="both", expand=True, padx=5, pady=5)

        self.users_listbox = tk.Listbox(
            users_list_frame,
            bg=self.BG_SIDEBAR,
            fg=self.TEXT_SIDEBAR,
            selectbackground="#2563eb",
            selectforeground="white",
            font=("Segoe UI", 10),
            borderwidth=0,
            highlightthickness=0,
            activestyle="none"
        )
        self.users_listbox.pack(side="left", fill="both", expand=True)
        self.users_listbox.bind("<<ListboxSelect>>", self._on_user_selected)

        user_scroll = ttk.Scrollbar(users_list_frame, orient="vertical", command=self.users_listbox.yview)
        user_scroll.pack(side="right", fill="y")
        self.users_listbox.config(yscrollcommand=user_scroll.set)

        # ----------------- Right Chat Area -----------------
        chat_area = tk.Frame(body, bg="#ffffff")
        chat_area.pack(side="right", fill="both", expand=True)

        # Conversation Header
        self.chat_header_lbl = tk.Label(
            chat_area,
            text="📢 Public LAN Lobby",
            font=("Segoe UI", 12, "bold"),
            bg="#f1f5f9",
            fg="#0f172a",
            anchor="w",
            padx=15,
            pady=10
        )
        self.chat_header_lbl.pack(fill="x")

        # Chat Messages History Box
        msg_frame = tk.Frame(chat_area, bg="#ffffff")
        msg_frame.pack(fill="both", expand=True, padx=15, pady=10)

        self.chat_text = tk.Text(
            msg_frame,
            wrap="word",
            bg="#ffffff",
            fg="#1e293b",
            font=("Segoe UI", 10),
            borderwidth=0,
            highlightthickness=0,
            padx=8,
            pady=8,
            state="disabled"
        )
        self.chat_text.pack(side="left", fill="both", expand=True)

        chat_scroll = ttk.Scrollbar(msg_frame, orient="vertical", command=self.chat_text.yview)
        chat_scroll.pack(side="right", fill="y")
        self.chat_text.config(yscrollcommand=chat_scroll.set)

        # Configure Text Tags for clean, colorful chat rendering
        self.chat_text.tag_config("meta_my", font=("Segoe UI", 9, "bold"), foreground="#2563eb")
        self.chat_text.tag_config("meta_other", font=("Segoe UI", 9, "bold"), foreground="#059669")
        self.chat_text.tag_config("meta_system", font=("Segoe UI", 9, "italic"), foreground="#64748b")
        self.chat_text.tag_config("timestamp", font=("Segoe UI", 8), foreground="#94a3b8")
        self.chat_text.tag_config("content", font=("Segoe UI", 10), foreground="#0f172a")

        # Message Input Box & Controls
        input_container = tk.Frame(chat_area, bg="#f8fafc", height=60, padx=15, pady=10)
        input_container.pack(fill="x", side="bottom")

        self.msg_entry = tk.Entry(input_container, font=("Segoe UI", 10), bg="#ffffff", fg="#0f172a", relief="solid", bd=1)
        self.msg_entry.pack(side="left", fill="x", expand=True, padx=(0, 10), ipady=6)
        self.msg_entry.bind("<Return>", lambda e: self._send_message())
        self.msg_entry.focus()

        send_btn = tk.Button(
            input_container,
            text="Send",
            font=("Segoe UI", 10, "bold"),
            bg=self.ACCENT_COLOR,
            fg="white",
            activebackground="#1d4ed8",
            activeforeground="white",
            relief="flat",
            padx=18,
            pady=5,
            command=self._send_message
        )
        send_btn.pack(side="right")

    # -------------------------------------------------------------------------
    # Thread-Safe UI Callback Dispatchers (Invoked from background thread)
    # -------------------------------------------------------------------------
    def _on_message_received_safe(self, msg: dict):
        self.root.after(0, self._handle_incoming_message, msg)

    def _on_user_list_updated_safe(self, users: list):
        self.root.after(0, self._handle_user_list_update, users)

    def _on_history_received_safe(self, target: str | None, history: list):
        self.root.after(0, self._handle_history_response, target, history)

    def _on_disconnected_safe(self, reason: str):
        self.root.after(0, self._handle_server_disconnect, reason)

    # -------------------------------------------------------------------------
    # UI Actions & Event Handlers
    # -------------------------------------------------------------------------
    def _select_conversation(self, target: str):
        """Switches active conversation view to Public Lobby or a Direct User."""
        self.current_target = target
        if target == '__public__':
            self.chat_header_lbl.config(text="📢 Public LAN Lobby")
        else:
            is_online = self.user_online_status.get(target, False)
            status_str = "Online" if is_online else "Offline"
            status_icon = "●" if is_online else "○"
            self.chat_header_lbl.config(text=f"💬 Chat with {target} ({status_icon} {status_str})")

        # Request history from server if cache is empty
        if target not in self.chat_history_cache:
            self.chat_history_cache[target] = []
            self.client.request_history(target)
        else:
            self._render_conversation(target)

    def _on_user_selected(self, event):
        selection = self.users_listbox.curselection()
        if not selection:
            return
        
        selected_text = self.users_listbox.get(selection[0])
        # Format is "● username" or "○ username"
        parts = selected_text.split(" ", 1)
        if len(parts) == 2:
            target_user = parts[1].strip()
            self._select_conversation(target_user)

    def _handle_user_list_update(self, user_list: list):
        """Updates the sidebar users list with real-time online/offline statuses."""
        self.users_listbox.delete(0, tk.END)
        current_user = self.client.current_user

        self.user_online_status.clear()
        for u in user_list:
            username = u.get("username")
            is_online = u.get("online", False)
            self.user_online_status[username] = is_online

            if username == current_user:
                continue  # Don't list ourselves in DM list

            status_icon = "●" if is_online else "○"
            display_str = f"{status_icon} {username}"
            self.users_listbox.insert(tk.END, display_str)

        # Update header if currently chatting with someone
        if self.current_target != '__public__':
            self._select_conversation(self.current_target)

    def _send_message(self):
        text = self.msg_entry.get().strip()
        if not text:
            return

        self.msg_entry.delete(0, tk.END)

        if self.current_target == '__public__':
            self.client.send_broadcast_message(text)
        else:
            self.client.send_direct_message(self.current_target, text)

    def _handle_incoming_message(self, msg: dict):
        """Handles an incoming direct message or broadcast message from server."""
        msg_type = msg.get("type")
        sender = msg.get("sender")
        recipient = msg.get("recipient")
        content = msg.get("content")
        timestamp = msg.get("timestamp")

        if msg_type == TYPE_BROADCAST_MSG:
            conv_key = '__public__'
        else:
            # Direct Message: belongs to conversation with the other party
            conv_key = recipient if sender == self.client.current_user else sender

        if conv_key not in self.chat_history_cache:
            self.chat_history_cache[conv_key] = []

        self.chat_history_cache[conv_key].append(msg)

        # If this message belongs to the currently active conversation, render it
        if self.current_target == conv_key:
            self._append_message_to_text_widget(msg)

    def _handle_history_response(self, target: str | None, history: list):
        conv_key = '__public__' if target in (None, 'public', '__public__') else target
        self.chat_history_cache[conv_key] = history
        if self.current_target == conv_key:
            self._render_conversation(conv_key)

    def _render_conversation(self, conv_key: str):
        """Clears and re-renders all messages for the active conversation."""
        self.chat_text.config(state="normal")
        self.chat_text.delete("1.0", tk.END)
        self.chat_text.config(state="disabled")

        messages = self.chat_history_cache.get(conv_key, [])
        for msg in messages:
            self._append_message_to_text_widget(msg)

    def _append_message_to_text_widget(self, msg: dict):
        """Appends a single formatted message to the Tkinter Text widget."""
        sender = msg.get("sender", "Unknown")
        content = msg.get("content", "")
        timestamp = msg.get("timestamp", "")
        is_me = (sender == self.client.current_user)

        self.chat_text.config(state="normal")

        # Sender & Time Header
        time_display = f" [{timestamp}]" if timestamp else ""
        if is_me:
            self.chat_text.insert(tk.END, f"You{time_display}:\n", "meta_my")
        else:
            self.chat_text.insert(tk.END, f"{sender}{time_display}:\n", "meta_other")

        # Message Body
        self.chat_text.insert(tk.END, f"  {content}\n\n", "content")
        self.chat_text.see(tk.END)
        self.chat_text.config(state="disabled")

    def _handle_server_disconnect(self, reason: str):
        messagebox.showwarning("Connection Lost", reason)
        self.show_auth_screen()

    def _handle_logout(self):
        self.client.disconnect()
        self.show_auth_screen()

    def _on_close(self):
        self.client.disconnect()
        self.root.destroy()
