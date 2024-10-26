import csv
import requests
from requests.exceptions import RequestException
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
import threading
import json
import openpyxl
from concurrent.futures import ThreadPoolExecutor, as_completed

def check_links(input_file, output_file, output_format, max_workers, progress_callback=None):
    if progress_callback:
        progress_callback(0, f"Reading links from {input_file}")
    with open(input_file, 'r', encoding='utf-8') as txtfile:
        links = txtfile.readlines()

    total_links = len(links)
    broken_links = []

    def check_link(link):
        link = link.strip()
        if link:
            try:
                response = requests.get(link, timeout=10)
                if response.status_code == 404:
                    return link
            except RequestException:
                return link
        return None

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_link = {executor.submit(check_link, link): link for link in links}
        for idx, future in enumerate(as_completed(future_to_link), start=1):
            result = future.result()
            if result:
                broken_links.append(result)
            if progress_callback:
                progress_callback(int((idx / total_links) * 100), f"Checking link {idx}/{total_links}")

    if output_format == 'csv':
        with open(output_file, mode='w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['404 Links'])
            for link in broken_links:
                writer.writerow([link])
    elif output_format == 'json':
        with open(output_file, mode='w', encoding='utf-8') as jsonfile:
            json.dump({'404 Links': broken_links}, jsonfile, indent=4)
    elif output_format == 'txt':
        with open(output_file, mode='w', encoding='utf-8') as txtfile:
            for link in broken_links:
                txtfile.write(link + '\n')
    elif output_format == 'xlsx':
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = 'Broken Links'
        sheet.append(['404 Links'])
        for link in broken_links:
            sheet.append([link])
        workbook.save(output_file)

    if progress_callback:
        progress_callback(100, f"Broken links saved to {output_file}")

def browse_file(entry_widget):
    file_path = filedialog.askopenfilename()
    if file_path:
        entry_widget.delete(0, tk.END)
        entry_widget.insert(0, file_path)

def save_file(entry_widget, format_var):
    formats = {
        'CSV': (".csv", ["CSV files", "*.csv"]),
        'JSON': (".json", ["JSON files", "*.json"]),
        'Text': (".txt", ["Text files", "*.txt"]),
        'Excel': (".xlsx", ["Excel files", "*.xlsx"])
    }
    selected_format = format_var.get()
    extension, filetype = formats.get(selected_format, formats['CSV'])
    file_path = filedialog.asksaveasfilename(defaultextension=extension, filetypes=[(filetype[0], filetype[1])])
    if file_path:
        entry_widget.delete(0, tk.END)
        entry_widget.insert(0, file_path)

def start_check_links(input_entry, output_entry, format_var, workers_var, progress_bar, progress_label):
    input_file = input_entry.get()
    output_file = output_entry.get()
    output_format = format_var.get().lower()
    max_workers = workers_var.get()
    if not input_file or not output_file:
        messagebox.showerror("Error", "Please specify both input and output files.")
        return

    def progress_callback(progress, message):
        progress_bar['value'] = progress
        progress_label.config(text=message)
        root.update_idletasks()

    def run_check_links():
        try:
            check_links(input_file, output_file, output_format, max_workers, progress_callback)
            messagebox.showinfo("Completed", "Link check completed successfully.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    thread = threading.Thread(target=run_check_links)
    thread.start()

root = tk.Tk()
root.title("Link Checker Tool")


frame = ttk.Frame(root, padding="10")
frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
root.columnconfigure(0, weight=1)
root.rowconfigure(0, weight=1)

input_label = ttk.Label(frame, text="Input File:")
input_label.grid(row=0, column=0, sticky=tk.W)
input_entry = ttk.Entry(frame, width=50)
input_entry.grid(row=0, column=1, sticky=(tk.W, tk.E))
input_browse_button = ttk.Button(frame, text="Browse", command=lambda: browse_file(input_entry))
input_browse_button.grid(row=0, column=2)

output_label = ttk.Label(frame, text="Output File:")
output_label.grid(row=1, column=0, sticky=tk.W)
output_entry = ttk.Entry(frame, width=50)
output_entry.grid(row=1, column=1, sticky=(tk.W, tk.E))
output_browse_button = ttk.Button(frame, text="Save As", command=lambda: save_file(output_entry, format_var))
output_browse_button.grid(row=1, column=2)

format_label = ttk.Label(frame, text="Output Format:")
format_label.grid(row=2, column=0, sticky=tk.W)
format_var = tk.StringVar(value='CSV')
format_combobox = ttk.Combobox(frame, textvariable=format_var, values=['CSV', 'JSON', 'Text', 'Excel'])
format_combobox.grid(row=2, column=1, sticky=(tk.W, tk.E))

workers_label = ttk.Label(frame, text="Number of Workers:")
workers_label.grid(row=3, column=0, sticky=tk.W)
workers_var = tk.IntVar(value=10)
workers_spinbox = ttk.Spinbox(frame, from_=1, to=50, textvariable=workers_var)
workers_spinbox.grid(row=3, column=1, sticky=(tk.W, tk.E))

progress_label = ttk.Label(frame, text="Progress:")
progress_label.grid(row=4, column=0, columnspan=3, sticky=tk.W, pady=(10, 0))
progress_bar = ttk.Progressbar(frame, orient="horizontal", length=400, mode="determinate")
progress_bar.grid(row=5, column=0, columnspan=3, pady=(0, 10))

start_button = ttk.Button(frame, text="Start Check", command=lambda: start_check_links(input_entry, output_entry, format_var, workers_var, progress_bar, progress_label))
start_button.grid(row=6, column=0, columnspan=3, pady=(10, 0))

root.mainloop()
