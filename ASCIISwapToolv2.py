#!/usr/bin/env python3
"""
clone_one_latest_shot_gui.py

Standalone Python3 utility with a Tkinter GUI to:

  • Select a source-shot folder (must include ep_###/sq_###/sh_### in its path)
  • Select a destination-shot folder (also including ep_###/sq_###/sh_###)
  • Find exactly one Maya ASCII file (*.ma) under source: the one with the highest-numbered version (_v###)
  • In that single .ma:
      – Replace every occurrence of old_ep_/old_sq_/old_sh_ with new_ep_/new_sq_/new_sh_
      – Replace its version suffix (_v###) with _v001
  • Write out only that single rewritten .ma into the destination folder (creating it if necessary)

All other files—textures, caches, additional .ma versions—are ignored.
Result: dest-root contains exactly one .ma (version 001) with updated tokens,
and the UI provides clear feedback and failsafes.

Requirements:
  – Python 3.6+
  – No external dependencies (uses only the standard library’s Tkinter, os, re, sys)
"""

import os
import re
import sys
import tkinter as tk
from tkinter import filedialog, messagebox

# --------------------- Helper Functions ---------------------

def find_token(pattern, path):
    """
    Return the first substring in 'path' matching regex 'pattern', or None.
    """
    m = re.search(pattern, path.replace("\\", "/"))
    return m.group() if m else None


def find_all_ma_files(root_folder):
    """
    Recursively collect all absolute paths under 'root_folder' matching '*_v###.ma'.
    """
    matches = []
    version_regex = re.compile(r".*_v\d+\.ma$", re.IGNORECASE)
    for dirpath, _, filenames in os.walk(root_folder):
        for fn in filenames:
            if version_regex.match(fn):
                matches.append(os.path.join(dirpath, fn))
    return matches


def extract_version_number(filename):
    """
    Given a filename ending in '_v###.ma', return the integer ###.
    Returns None if the pattern is not found.
    """
    m = re.search(r"_v(\d+)\.ma$", filename, re.IGNORECASE)
    return int(m.group(1)) if m else None


def select_highest_version(ma_paths):
    """
    Given a list of absolute paths to '*.ma' ending in '_v###.ma',
    return the single path whose numeric suffix is highest.
    If the list is empty, returns None.
    """
    best_path = None
    best_ver = -1
    for p in ma_paths:
        fn = os.path.basename(p)
        ver = extract_version_number(fn)
        if ver is not None and ver > best_ver:
            best_ver = ver
            best_path = p
    return best_path

# --------------------- GUI Class ---------------------

class CloneOneLatestGUI(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        master.title("Clone Latest Maya Shot")
        master.resizable(False, False)
        self.grid(padx=12, pady=12)

        # Constants for widget sizing
        entry_width = 50
        button_width = 20
        status_wrap = 400

        # Source folder selection
        tk.Label(self, text="Source Shot Folder:").grid(row=0, column=0, sticky="w")
        self.src_entry = tk.Entry(self, width=entry_width)
        self.src_entry.grid(row=1, column=0, padx=(0, 8))
        tk.Button(self, text="Browse…", width=12, command=self.browse_source).grid(row=1, column=1)

        # Destination folder selection
        tk.Label(self, text="Destination Shot Folder:").grid(row=2, column=0, sticky="w", pady=(12, 0))
        self.dst_entry = tk.Entry(self, width=entry_width)
        self.dst_entry.grid(row=3, column=0, padx=(0, 8))
        tk.Button(self, text="Browse…", width=12, command=self.browse_dest).grid(row=3, column=1)

        # Action button
        self.clone_button = tk.Button(
            self, text="Clone Latest .ma ? v001", width=button_width, command=self.clone_latest
        )
        self.clone_button.grid(row=4, column=0, columnspan=2, pady=(18, 0))

        # Status label
        self.status_label = tk.Label(self, text="", fg="red", wraplength=status_wrap, justify="left")
        self.status_label.grid(row=5, column=0, columnspan=2, pady=(12, 0))

    def browse_source(self):
        folder = filedialog.askdirectory(title="Select Source Shot Folder")
        if folder:
            self.src_entry.delete(0, tk.END)
            self.src_entry.insert(0, folder)
            self.status_label.config(text="")

    def browse_dest(self):
        folder = filedialog.askdirectory(title="Select Destination Shot Folder")
        if folder:
            self.dst_entry.delete(0, tk.END)
            self.dst_entry.insert(0, folder)
            self.status_label.config(text="")

    def clone_latest(self):
        source_root = self.src_entry.get().strip()
        dest_root = self.dst_entry.get().strip()

        # 1) Validate inputs
        if not source_root or not os.path.isdir(source_root):
            messagebox.showerror("Error", "Please choose a valid Source Shot folder.")
            return
        if not dest_root:
            messagebox.showerror("Error", "Please choose a Destination Shot folder.")
            return

        src_norm = source_root.replace("\\", "/")
        dst_norm = dest_root.replace("\\", "/")

        old_ep = find_token(r"ep_\d+", src_norm)
        old_sq = find_token(r"sq_\d+", src_norm)
        old_sh = find_token(r"sh_\d+", src_norm)
        if not (old_ep and old_sq and old_sh):
            messagebox.showerror(
                "Error",
                f"Source folder must contain ep_###, sq_###, and sh_###.\n"
                f"Found: ep={old_ep}, sq={old_sq}, sh={old_sh}"
            )
            return

        new_ep = find_token(r"ep_\d+", dst_norm)
        new_sq = find_token(r"sq_\d+", dst_norm)
        new_sh = find_token(r"sh_\d+", dst_norm)
        if not (new_ep and new_sq and new_sh):
            messagebox.showerror(
                "Error",
                f"Destination folder must contain ep_###, sq_###, and sh_###.\n"
                f"Found: ep={new_ep}, sq={new_sq}, sh={new_sh}"
            )
            return

        # Prevent identical source/dest
        if os.path.normpath(source_root) == os.path.normpath(dest_root):
            messagebox.showerror("Error", "Source and Destination folders must differ.")
            return

        # 2) Gather all versioned .ma files
        all_ma = find_all_ma_files(source_root)
        if not all_ma:
            messagebox.showerror("Error", "No Maya ASCII files matching '*_v###.ma' found under source folder.")
            return

        # 3) Select the file with the highest version
        latest_ma = select_highest_version(all_ma)
        if not latest_ma:
            messagebox.showerror("Error", "Could not determine the latest-version .ma file.")
            return

        latest_fn = os.path.basename(latest_ma)            # e.g. "scene_lighting_v005.ma"
        base_noext, _ = os.path.splitext(latest_fn)         # e.g. "scene_lighting_v005"
        m = re.match(r"^(.*)_v\d+$", base_noext, re.IGNORECASE)
        if not m:
            messagebox.showerror(
                "Error",
                f"Latest .ma filename does not match pattern '*_v###.ma':\n  {latest_fn}"
            )
            return

        base_before_ver = m.group(1)  # e.g. "scene_lighting"

        # 4) Compute new filename and ensure dest folder exists
        new_fn = f"{base_before_ver}_v001.ma"
        try:
            os.makedirs(dest_root, exist_ok=True)
        except Exception as e:
            messagebox.showerror("Error", f"Could not create Destination folder:\n{e}")
            return

        dest_fullpath = os.path.join(dest_root, new_fn)

        # If the destination file already exists, ask for overwrite confirmation
        if os.path.isfile(dest_fullpath):
            resp = messagebox.askyesno(
                "Overwrite?",
                f"A file named '{new_fn}' already exists in the destination.\nDo you want to overwrite it?"
            )
            if not resp:
                self.status_label.config(text="Operation canceled by user.", fg="orange")
                return

        # 5) Read, replace tokens, write out
        try:
            with open(latest_ma, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read source .ma:\n{latest_ma}\n{e}")
            return

        # Replace old tokens globally
        content = content.replace(old_ep, new_ep)
        content = content.replace(old_sq, new_sq)
        content = content.replace(old_sh, new_sh)
        # Replace versioned filename occurrences (with .ma)
        content = content.replace(latest_fn, new_fn)
        # Replace versioned base (without .ma)
        content = content.replace(base_noext, f"{base_before_ver}_v001")

        try:
            with open(dest_fullpath, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to write new .ma:\n{dest_fullpath}\n{e}")
            return

        messagebox.showinfo(
            "Success",
            f"Cloned:\n  {latest_ma}\n?\n  {dest_fullpath}\n\n"
            f"(Tokens: {old_ep}?{new_ep}, {old_sq}?{new_sq}, {old_sh}?{new_sh}; version ? v001)"
        )
        self.status_label.config(text="Clone completed successfully.", fg="green")

# --------------------- Main Execution ---------------------

def main():
    root = tk.Tk()
    app = CloneOneLatestGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
