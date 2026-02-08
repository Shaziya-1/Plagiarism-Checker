import os
import threading
import csv
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ---------- ROOT ----------
root = tk.Tk()
root.title("Multi-Folder Plagiarism Checker")
root.geometry("1000x650")

# ---------- GLOBAL ----------
all_folders = []        # [(folder_path, listbox)]
results_store = []      # comparison results

# ---------- LEFT FRAME ----------
left_frame = tk.Frame(root)
left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=6)

tk.Label(left_frame, text="Folders & Files").pack(anchor=tk.W)

folders_frame = tk.Frame(left_frame)
folders_frame.pack(fill=tk.X)

files_frame = tk.Frame(left_frame)
files_frame.pack(fill=tk.X)

tk.Label(left_frame, text="Preview (Highlighted)").pack(anchor=tk.W, pady=(8, 0))
preview = scrolledtext.ScrolledText(left_frame, width=40, height=12, state=tk.DISABLED)
preview.pack()

# ---------- ADD FOLDER ----------
def add_folder():
    folder = filedialog.askdirectory()
    if not folder:
        return

    for f, _ in all_folders:
        if f == folder:
            messagebox.showinfo("Info", "Folder already added")
            return

    tk.Label(
        folders_frame,
        text=f"Folder: {os.path.basename(folder)}",
        bg="lightgray",
        width=45
    ).pack(pady=2)

    lb = tk.Listbox(
        files_frame,
        width=40,
        height=6,
        selectmode=tk.SINGLE,
        exportselection=False   # ⭐ VERY IMPORTANT
    )
    lb.pack(pady=(2, 6))

    populate_file_list(folder, lb)
    lb.bind("<Double-1>", lambda e, f=folder, l=lb: preview_file(f, l))

    all_folders.append((folder, lb))

# ---------- POPULATE FILES ----------
def populate_file_list(folder, listbox):
    listbox.delete(0, tk.END)
    for f in sorted(os.listdir(folder)):
        if f.lower().endswith(".txt"):
            listbox.insert(tk.END, f)

# ---------- GET SELECTED FILES ----------
def get_selected_files():
    selected = []
    for folder, lb in all_folders:
        sel = lb.curselection()
        if sel:
            selected.append(os.path.join(folder, lb.get(sel[0])))
    return selected

# ---------- PREVIEW ----------
def preview_file(folder, listbox):
    sel = listbox.curselection()
    if not sel:
        return

    path = os.path.join(folder, listbox.get(sel[0]))
    try:
        text = open(path, encoding="utf-8").read()
    except:
        text = "[Unable to read file]"

    preview.config(state=tk.NORMAL)
    preview.delete("1.0", tk.END)
    preview.insert(tk.END, text)
    preview.config(state=tk.DISABLED)

# ---------- HIGHLIGHT COMMON ----------
def highlight_common_words():
    files = get_selected_files()
    if len(files) != 2:
        messagebox.showwarning(
            "Selection Error",
            "Select EXACTLY 1 file from EACH of 2 folders."
        )
        return

    text1 = open(files[0], encoding="utf-8").read()
    text2 = open(files[1], encoding="utf-8").read()

    words2 = set(text2.split())

    preview.config(state=tk.NORMAL)
    preview.delete("1.0", tk.END)
    preview.insert(tk.END, text1)
    preview.tag_config("common", background="red", foreground="white")

    idx = "1.0"
    for word in text1.split():
        while True:
            idx = preview.search(word, idx, stopindex=tk.END)
            if not idx:
                break
            end = f"{idx}+{len(word)}c"
            if word in words2:
                preview.tag_add("common", idx, end)
            idx = end

    preview.config(state=tk.DISABLED)

# ---------- RIGHT FRAME ----------
right_frame = tk.Frame(root)
right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=6)

tree = ttk.Treeview(
    right_frame,
    columns=("File1", "File2", "Similarity"),
    show="headings"
)
tree.heading("File1", text="File 1")
tree.heading("File2", text="File 2")
tree.heading("Similarity", text="Similarity (%)")
tree.pack(fill=tk.BOTH, expand=True)

tree.tag_configure("high", background="#ffd6d6")
tree.tag_configure("mid", background="#fff0d6")
tree.tag_configure("low", background="#e8ffd6")

progress = ttk.Progressbar(right_frame, mode="indeterminate")
progress.pack(fill=tk.X, pady=4)

status_lbl = tk.Label(right_frame, text="Ready")
status_lbl.pack(anchor=tk.W)

# ---------- COMPUTE ----------
def compute_similarity(file1, file2):
    texts = [
        open(file1, encoding="utf-8").read(),
        open(file2, encoding="utf-8").read()
    ]
    tfidf = TfidfVectorizer().fit_transform(texts)
    sim = cosine_similarity(tfidf)[0][1] * 100
    return sim

# ---------- RUN CHECK ----------
def run_check():
    global results_store

    files = get_selected_files()
    if len(files) != 2:
        messagebox.showwarning(
            "Selection Error",
            "Select EXACTLY 1 file from EACH of 2 folders."
        )
        return

    run_btn.config(state=tk.DISABLED)
    highlight_btn.config(state=tk.DISABLED)
    export_btn.config(state=tk.DISABLED)
    clear_btn.config(state=tk.DISABLED)

    progress.start()
    status_lbl.config(text="Computing...")

    def worker():
        sim = compute_similarity(files[0], files[1])
        result = {
            "file1": os.path.basename(files[0]),
            "file2": os.path.basename(files[1]),
            "sim": sim
        }
        results_store.append(result)

        tag = "high" if sim > 60 else "mid" if sim >= 21 else "low"

        tree.insert(
            "",
            tk.END,
            values=(result["file1"], result["file2"], f"{sim:.2f}"),
            tags=(tag,)
        )

        progress.stop()
        status_lbl.config(text="Done")

        run_btn.config(state=tk.NORMAL)
        highlight_btn.config(state=tk.NORMAL)
        export_btn.config(state=tk.NORMAL)
        clear_btn.config(state=tk.NORMAL)

    threading.Thread(target=worker).start()

# ---------- EXPORT ----------
def export_csv():
    if not results_store:
        messagebox.showinfo("Info", "No results to export")
        return

    path = filedialog.asksaveasfilename(defaultextension=".csv")
    if not path:
        return

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["File 1", "File 2", "Similarity (%)"])
        for r in results_store:
            writer.writerow([r["file1"], r["file2"], f"{r['sim']:.2f}"])

    messagebox.showinfo("Exported", "CSV saved successfully")

# ---------- CLEAR ----------
def clear_all():
    global all_folders, results_store

    for _, lb in all_folders:
        lb.destroy()
    all_folders.clear()
    results_store.clear()

    for w in folders_frame.winfo_children():
        w.destroy()

    preview.config(state=tk.NORMAL)
    preview.delete("1.0", tk.END)
    preview.config(state=tk.DISABLED)

    tree.delete(*tree.get_children())
    status_lbl.config(text="Cleared")

# ---------- BUTTONS ----------
btn_frame = tk.Frame(left_frame)
btn_frame.pack(fill=tk.X, pady=6)

tk.Button(btn_frame, text="Add Folder", command=add_folder).pack(fill=tk.X)
run_btn = tk.Button(left_frame, text="Run Check", command=run_check)
run_btn.pack(fill=tk.X, pady=2)
highlight_btn = tk.Button(left_frame, text="Highlight Common", command=highlight_common_words)
highlight_btn.pack(fill=tk.X, pady=2)
export_btn = tk.Button(left_frame, text="Export CSV", command=export_csv)
export_btn.pack(fill=tk.X, pady=2)
clear_btn = tk.Button(left_frame, text="Clear All", command=clear_all)
clear_btn.pack(fill=tk.X, pady=2)

# ---------- START ----------
root.mainloop()
