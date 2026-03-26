import customtkinter as ctk
import pyperclip
import keyboard
import time
import sys
import os
import json
import ctypes 
from tkinter import filedialog as fd

SAVE_DIR = "savefile"
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

class StartupPrompt(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Tool Setup")
        self.geometry("320x280") 
        self.eval('tk::PlaceWindow . center') 
        self.resizable(False, False)
        
        self.selected_slots = None 
        self.loaded_data = None 

        # Main Brand Title
        ctk.CTkLabel(
            self, 
            text="EZ Copy Paste", 
            font=("Arial", 30, "bold"),
            text_color="#2FB6B6"
        ).pack(pady=(20, 5))

        # Smaller Question Label
        ctk.CTkLabel(
            self, 
            text="Select Number of Clipboard Slots:\n (1-10)", 
            font=("Arial", 12, "italic", "bold"),
        ).pack(pady=(0, 10))

        self.slot_var = ctk.StringVar(value="5") 
        self.dropdown = ctk.CTkOptionMenu(
            self, 
            values=[str(i) for i in range(1, 11)], 
            variable=self.slot_var,
            font=("Arial", 14),
            fg_color="#3a7ebf",
            button_color="#2b6196",
            button_hover_color="#1f4b7a"
        )
        self.dropdown.pack(pady=10)

        ctk.CTkButton(
            self, 
            text="Launch New", 
            command=self.launch_main,
            font=("Arial", 14, "bold"),
            fg_color="#2FA572",
            hover_color="#1F7A52"
        ).pack(pady=(15, 5))
        
        ctk.CTkButton(
            self, 
            text="Load Saved Profile", 
            command=self.load_profile,
            font=("Arial", 14, "bold"),
            fg_color="#d97706",
            hover_color="#b45309"
        ).pack(pady=5)

    def launch_main(self):
        self.selected_slots = int(self.slot_var.get())
        self.destroy() 
        
    def load_profile(self):
        filepath = fd.askopenfilename(
            initialdir=SAVE_DIR, title="Select Profile", filetypes=[("JSON Files", "*.json")]
        )
        if filepath:
            try:
                with open(filepath, 'r') as f: self.loaded_data = json.load(f)
                self.selected_slots = self.loaded_data.get("num_slots", 5)
                self.destroy()
            except Exception as e:
                print(f"Error loading file: {e}")

class MultiSlotClipboard(ctk.CTk):
    def __init__(self, num_slots, loaded_data=None):
        super().__init__()
        
        self.overrideredirect(True)
        self.attributes("-topmost", True) 

        self.is_dragging = False
        self.is_snapped = False
        self.is_hidden_snapped = False
        
        # Default hotkeys to OFF as requested
        self.hotkeys_enabled = loaded_data.get("hotkeys_enabled", False) if loaded_data else False

        self.update_idletasks() 
        try:
            hwnd = int(self.wm_frame(), 16) 
            GWL_EXSTYLE = -20
            WS_EX_NOACTIVATE = 0x08000000
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_NOACTIVATE)
        except Exception as e:
            pass

        self.drag_frame_left = ctk.CTkFrame(self, fg_color="#1e1e1e", width=25, cursor="fleur")
        self.drag_frame_left.pack(side="left", fill="y", padx=(5, 5), pady=5)
        drag_label_left = ctk.CTkLabel(self.drag_frame_left, text="⋮⋮", font=("Arial", 18, "bold"), text_color="gray")
        drag_label_left.pack(expand=True)
        self.bind_drag_events(self.drag_frame_left, drag_label_left)

        self.slots_container = ctk.CTkFrame(self, fg_color="transparent")
        self.slots_container.pack(side="left", fill="both", expand=True)

        self.sys_container = ctk.CTkFrame(self, fg_color="transparent")
        self.sys_container.pack(side="right", fill="y", padx=5, pady=10)

        self.build_system_buttons()

        if loaded_data:
            self.num_slots = loaded_data.get("num_slots", 5)
            self.slots = loaded_data.get("slots", [None] * self.num_slots)
            self.is_hidden = loaded_data.get("hidden", [False] * self.num_slots) 
            while len(self.slots) < self.num_slots: 
                self.slots.append(None)
                self.is_hidden.append(False)
            self.slots = self.slots[:self.num_slots]
            self.is_hidden = self.is_hidden[:self.num_slots]
        else:
            self.num_slots = num_slots
            self.slots = [None] * self.num_slots 
            self.is_hidden = [False] * self.num_slots 
            
        self.build_slots()
        self.after(100, self.check_hover_state)

    def manual_fill_popup(self, idx):
        # Create a small popup window
        popup = ctk.CTkToplevel(self)
        popup.title(f"Manual Fill - Slot {idx+1}")
        popup.geometry("300x200")
        popup.attributes("-topmost", True)
        self.eval(f'tk::PlaceWindow {popup.winfo_pathname(popup.winfo_id())} center')

        ctk.CTkLabel(popup, text=f"Enter text for Slot {idx+1}:", font=("Arial", 12, "bold")).pack(pady=10)
        
        # Text box for entry
        text_entry = ctk.CTkTextbox(popup, width=250, height=80)
        text_entry.pack(pady=5)
        
        # If the slot already has text, show it in the box
        if self.slots[idx]:
            text_entry.insert("0.0", self.slots[idx])

        def save_manual():
            content = text_entry.get("0.0", "end").strip()
            if content:
                self.slots[idx] = content
                self.is_hidden[idx] = False
                self.update_slot_visuals(idx)
                popup.destroy()

        ctk.CTkButton(popup, text="Save to Slot", fg_color="#2FA572", command=save_manual).pack(pady=10)

    def bind_drag_events(self, frame, label):
        frame.bind("<Button-1>", self.start_move)
        frame.bind("<B1-Motion>", self.do_move)
        frame.bind("<ButtonRelease-1>", self.stop_move)
        label.bind("<Button-1>", self.start_move)
        label.bind("<B1-Motion>", self.do_move)
        label.bind("<ButtonRelease-1>", self.stop_move)

    def build_system_buttons(self):
        # Right Drag Handle
        self.drag_frame_right = ctk.CTkFrame(self.sys_container, fg_color="#1e1e1e", width=25, cursor="fleur")
        self.drag_frame_right.pack(side="left", fill="y", padx=(0, 10)) 
        drag_label_right = ctk.CTkLabel(self.drag_frame_right, text="⋮⋮", font=("Arial", 18, "bold"), text_color="gray")
        drag_label_right.pack(expand=True)
        self.bind_drag_events(self.drag_frame_right, drag_label_right)

        # Hotkey Group (Label + Button)
        hotkey_group = ctk.CTkFrame(self.sys_container, fg_color="transparent")
        hotkey_group.pack(side="left", padx=(0, 10))

        # Dynamic Label for instructions
        self.hotkey_info_label = ctk.CTkLabel(
            hotkey_group, text="Hotkey OFF", font=("Arial", 9, "bold"), text_color="gray"
        )
        self.hotkey_info_label.pack(pady=(0, 2))

        self.hotkey_btn = ctk.CTkButton(
            hotkey_group, text="", width=55, height=32,
            font=("Arial", 11, "bold"), command=self.toggle_hotkeys
        )
        self.hotkey_btn.pack()
        self.update_hotkey_btn_visual()

        # System Buttons (Remaining exactly as your original script)
        ctk.CTkButton(
            self.sys_container, text="Save", width=55, height=45,
            font=("Arial", 12, "bold"), fg_color="#673ab7", hover_color="#512da8", command=self.save_profile
        ).pack(side="left", padx=(0, 5))
        
        ctk.CTkButton(
            self.sys_container, text="Load", width=55, height=45,
            font=("Arial", 12, "bold"), fg_color="#d97706", hover_color="#b45309", command=self.load_profile_in_app
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            self.sys_container, text="X", width=35, height=45,
            font=("Arial", 12, "bold"), fg_color="#802020", hover_color="#c93434", command=self.destroy
        ).pack(side="left")
    
    def build_slots(self):
        for widget in self.slots_container.winfo_children():
            widget.destroy()

        self.main_buttons = []
        self.action_frames = [] 
        self.hide_buttons = [] 
        self.clear_buttons = []
        
        calculated_width = 330 + (self.num_slots * 115) 
        self.geometry(f"{calculated_width}x65")

        for i in range(self.num_slots):
            slot_frame = ctk.CTkFrame(self.slots_container, fg_color="transparent")
            slot_frame.pack(side="left", pady=10, padx=5, fill="y")
            
            # Added \n to put the number on top and reduced font to 11
            btn = ctk.CTkButton(
                slot_frame, text=f"({i+1})\nEmpty", 
                command=lambda idx=i: self.handle_slot_click(idx),
                width=100, height=45, fg_color="#3a7ebf", font=("Arial", 10, "bold")
            )
            # Right-click to manually fill
            btn.bind("<Button-3>", lambda e, idx=i: self.manual_fill_popup(idx))
            btn.pack(side="left")
            self.main_buttons.append(btn)
            
            action_frame = ctk.CTkFrame(slot_frame, fg_color="transparent", width=28)
            self.action_frames.append(action_frame)

            # Changed ✖ to X and brightened the red to #d13232
            clear_btn = ctk.CTkButton(
                action_frame, text="X", width=28, height=21, 
                fg_color="#d13232", hover_color="#992626", font=("Arial", 11, "bold"),
                corner_radius=4, command=lambda idx=i: self.clear_slot(idx)
            )
            clear_btn.pack(side="top", pady=(0, 2))
            self.clear_buttons.append(clear_btn)

            hide_btn = ctk.CTkButton(
                action_frame, text="👁", width=28, height=21, 
                fg_color="#555555", hover_color="#333333", font=("Arial", 10),
                corner_radius=4, command=lambda idx=i: self.toggle_hide(idx)
            )
            hide_btn.pack(side="bottom")
            self.hide_buttons.append(hide_btn)
            
            if self.slots[i] is not None:
                self.update_slot_visuals(i)
        
        self.bind_hotkeys()

    def toggle_hotkeys(self):
        self.hotkeys_enabled = not self.hotkeys_enabled
        self.update_hotkey_btn_visual()
        self.bind_hotkeys()

    def update_hotkey_btn_visual(self):
        if self.hotkeys_enabled:
            self.hotkey_btn.configure(text="ON", fg_color="#2FA572", hover_color="#1F7A52")
            # Update the text to instructions when active
            self.hotkey_info_label.configure(text="Press Ctrl+Num", text_color="#2FA572")
        else:
            self.hotkey_btn.configure(text="OFF", fg_color="#555555", hover_color="#333333")
            # Update the text to status when inactive
            self.hotkey_info_label.configure(text="Hotkey OFF", text_color="gray")

    def bind_hotkeys(self):
        keyboard.unhook_all() 
        if not self.hotkeys_enabled:
            return 
        for i in range(self.num_slots):
            key_num = str(i + 1) if (i + 1) < 10 else "0" 
            keyboard.add_hotkey(f'ctrl+{key_num}', lambda idx=i: self.after(0, lambda: self.copy_to_clipboard_only(idx)))

    def copy_to_clipboard_only(self, idx):
        if self.slots[idx] is not None:
            pyperclip.copy(self.slots[idx])
            original_color = self.main_buttons[idx].cget("fg_color")
            self.main_buttons[idx].configure(fg_color="#45c990") 
            self.after(200, lambda: self.main_buttons[idx].configure(fg_color=original_color))

    def toggle_hide(self, idx):
        if self.slots[idx] is None: return
        self.is_hidden[idx] = not self.is_hidden[idx]
        self.update_slot_visuals(idx)

    def update_slot_visuals(self, idx):
        self.action_frames[idx].pack(side="right", fill="y", padx=(3, 0))
        if self.is_hidden[idx]:
            # Kept the slot number (idx+1) visible at the top even when hidden
            self.main_buttons[idx].configure(text=f"({idx+1})\n********", fg_color="#2FA572", hover_color="#1F7A52", width=69)
            self.hide_buttons[idx].configure(text="🔒", fg_color="#806000", hover_color="#997300")
        else:
            display_text = self.slots[idx].replace('\n', ' ')
            if len(display_text) > 8: display_text = display_text[:5] + "..."
            # Added f-string to keep the (Number) on the top line
            self.main_buttons[idx].configure(text=f"({idx+1})\n{display_text}", fg_color="#2FA572", hover_color="#1F7A52", width=69)
            self.hide_buttons[idx].configure(text="👁", fg_color="#555555", hover_color="#333333")

    def save_profile(self):
        filepath = fd.asksaveasfilename(initialdir=SAVE_DIR, defaultextension=".json", filetypes=[("JSON Files", "*.json")], title="Save Profile As")
        if filepath:
            data = {"num_slots": self.num_slots, "slots": self.slots, "hidden": self.is_hidden, "hotkeys_enabled": self.hotkeys_enabled}
            with open(filepath, 'w') as f: json.dump(data, f, indent=4)

    def load_profile_in_app(self):
        filepath = fd.askopenfilename(initialdir=SAVE_DIR, title="Select Profile", filetypes=[("JSON Files", "*.json")])
        if filepath:
            with open(filepath, 'r') as f: loaded_data = json.load(f)
            self.num_slots, self.slots, self.is_hidden = loaded_data.get("num_slots", 5), loaded_data.get("slots"), loaded_data.get("hidden")
            self.hotkeys_enabled = loaded_data.get("hotkeys_enabled", False)
            self.update_hotkey_btn_visual()
            self.build_slots()

    def start_move(self, event):
        self.is_dragging = True
        self._drag_start_x, self._drag_start_y = event.x, event.y

    def stop_move(self, event): self.is_dragging = False

    def do_move(self, event):
        x, y = self.winfo_x() - self._drag_start_x + event.x, self.winfo_y() - self._drag_start_y + event.y
        if y <= 15: y, self.is_snapped = 0, True
        else: self.is_snapped, self.is_hidden_snapped = False, False
        self.geometry(f"+{x}+{y}")

    def check_hover_state(self):
        if self.is_snapped and not self.is_dragging:
            mx, my, wx, wy, ww, wh = self.winfo_pointerx(), self.winfo_pointery(), self.winfo_x(), self.winfo_y(), self.winfo_width(), self.winfo_height()
            is_hovering = wx <= mx <= wx + ww and my <= wh
            if is_hovering and self.is_hidden_snapped: self.geometry(f"+{wx}+0"); self.is_hidden_snapped = False
            elif not is_hovering and not self.is_hidden_snapped: self.geometry(f"+{wx}+{-wh + 5}"); self.is_hidden_snapped = True
        self.after(100, self.check_hover_state)

    def handle_slot_click(self, idx):
        if self.slots[idx] is None:
            keyboard.send('ctrl+c')
            time.sleep(0.1) 
            clip = pyperclip.paste()
            if clip.strip(): self.slots[idx], self.is_hidden[idx] = clip, False; self.update_slot_visuals(idx)
        else:
            self.copy_to_clipboard_only(idx); time.sleep(0.05); keyboard.send('ctrl+v')

    def clear_slot(self, idx):
        self.slots[idx], self.is_hidden[idx] = None, False
        # Matches the new build_slots style
        self.main_buttons[idx].configure(text=f"({idx+1})\nEmpty", fg_color="#3a7ebf", hover_color="#2b6196", width=100)
        self.action_frames[idx].pack_forget()

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")  
    setup_app = StartupPrompt()
    setup_app.mainloop()
    if setup_app.selected_slots is not None:
        main_app = MultiSlotClipboard(num_slots=setup_app.selected_slots, loaded_data=setup_app.loaded_data)
        main_app.mainloop()
    else: sys.exit()
