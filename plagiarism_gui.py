import os
import threading
import csv
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ---------- ROOT ----------
root = tk.Tk()
root.title("Plagiarism Checker")
root.geometry("1000x650")

# ---------- GLOBAL ----------
results_store = []
file_listboxes = []   # [(folder_path, listbox)]

# ---------- LEFT FRAME ----------
left_frame = tk.Frame(root)
left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=6)

tk.Label(left_frame, text="Folders & Files").pack(anchor=tk.W)

folders_frame = tk.Frame(left_frame)
folders_frame.pack(fill=tk.X)

files_frame = tk.Frame(left_frame)
files_frame.pack(fill=tk.X)

# ---------- PREVIEW ----------
tk.Label(left_frame, text="Preview (Highlighted)").pack(anchor=tk.W, pady=(8, 0))
preview = scrolledtext.ScrolledText(left_frame, width=40, height=12, state=tk.DISABLED)
preview.pack()

# ---------- ADD FOLDER ----------
def add_folder():
    folder = filedialog.askdirectory()
    if not folder:
        return

    for f, _ in file_listboxes:
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
        exportselection=False
    )
    lb.pack(pady=(2, 6))

    populate_file_list(folder, lb)
    file_listboxes.append((folder, lb))

# ---------- POPULATE FILES ----------
def populate_file_list(folder, listbox):
    listbox.delete(0, tk.END)
    for f in sorted(os.listdir(folder)):
        if f.lower().endswith(".txt"):
            listbox.insert(tk.END, f)

# ---------- GET SELECTED FILES ----------
def get_selected_files():
    selected = []
    for folder, lb in file_listboxes:
        sel = lb.curselection()
        if sel:
            selected.append(os.path.join(folder, lb.get(sel[0])))
    return selected

# ---------- HIGHLIGHT COMMON ----------
def highlight_common_words():
    selected = get_selected_files()
    if len(selected) != 2:
        messagebox.showwarning(
            "Selection Error",
            "Select EXACTLY 1 file from EACH of 2 folders."
        )
        return

    try:
        text1 = open(selected[0], encoding="utf-8").read()
        text2 = open(selected[1], encoding="utf-8").read()
    except:
        messagebox.showerror("Error", "Unable to read files")
        return

    words2 = set(text2.split())

    preview.config(state=tk.NORMAL)
    preview.delete("1.0", tk.END)
    preview.insert(tk.END, text1)
    preview.tag_config("common", background="red", foreground="white")

    for word in text1.split():
        idx = "1.0"
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
def compute_results(filepaths):
    texts = [open(f, encoding="utf-8").read() for f in filepaths]
    names = [os.path.basename(f) for f in filepaths]

    tfidf = TfidfVectorizer().fit_transform(texts)
    sim = cosine_similarity(tfidf)[0][1] * 100

    return [{
        "file1": names[0],
        "file2": names[1],
        "sim": sim
    }]

# ---------- RUN CHECK ----------
def run_check():
    global results_store
    selected = get_selected_files()

    if len(selected) != 2:
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
        result = compute_results(selected)[0]
        results_store.append(result)

        tag = "high" if result["sim"] > 60 else "mid" if result["sim"] >= 21 else "low"

        tree.insert(
            "",
            tk.END,
            values=(result["file1"], result["file2"], f"{result['sim']:.2f}"),
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
    global results_store, file_listboxes

    for _, lb in file_listboxes:
        lb.destroy()

    file_listboxes.clear()
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
