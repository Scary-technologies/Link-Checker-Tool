import csv
import requests
from requests.exceptions import RequestException
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class LinkCheckerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ابزار بررسی لینک")
        self.create_widgets()

    def create_widgets(self):
        frame = ttk.Frame(self.root, padding="10")
        frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        input_label = ttk.Label(frame, text="فایل ورودی:")
        input_label.grid(row=0, column=0, sticky=tk.W)
        self.input_entry = ttk.Entry(frame, width=50)
        self.input_entry.grid(row=0, column=1, sticky=(tk.W, tk.E))
        input_browse_button = ttk.Button(frame, text="انتخاب", command=self.browse_file)
        input_browse_button.grid(row=0, column=2)
        self.add_tooltip(self.input_entry, "فایل متنی حاوی لینک‌ها را انتخاب کنید.")

        output_label = ttk.Label(frame, text="فایل خروجی:")
        output_label.grid(row=1, column=0, sticky=tk.W)
        self.output_entry = ttk.Entry(frame, width=50)
        self.output_entry.grid(row=1, column=1, sticky=(tk.W, tk.E))
        output_browse_button = ttk.Button(frame, text="ذخیره به‌عنوان", command=self.save_file)
        output_browse_button.grid(row=1, column=2)
        self.add_tooltip(self.output_entry, "محل ذخیره فایل خروجی را مشخص کنید.")

        format_label = ttk.Label(frame, text="فرمت خروجی:")
        format_label.grid(row=2, column=0, sticky=tk.W)
        self.format_var = tk.StringVar(value='CSV')
        format_combobox = ttk.Combobox(frame, textvariable=self.format_var, values=['CSV', 'Text'], state='readonly')
        format_combobox.grid(row=2, column=1, sticky=(tk.W, tk.E))

        workers_label = ttk.Label(frame, text="تعداد پردازشگرها:")
        workers_label.grid(row=3, column=0, sticky=tk.W)
        self.workers_var = tk.IntVar(value=min(10, os.cpu_count() or 1))
        workers_spinbox = ttk.Spinbox(frame, from_=1, to=50, textvariable=self.workers_var)
        workers_spinbox.grid(row=3, column=1, sticky=(tk.W, tk.E))

        progress_label = ttk.Label(frame, text="پیشرفت:")
        progress_label.grid(row=4, column=0, columnspan=3, sticky=tk.W, pady=(10, 0))
        self.progress_bar = ttk.Progressbar(frame, orient="horizontal", length=400, mode="determinate")
        self.progress_bar.grid(row=5, column=0, columnspan=3, pady=(0, 10))

        self.progress_label = ttk.Label(frame, text="")
        self.progress_label.grid(row=6, column=0, columnspan=3, sticky=tk.W)

        start_button = ttk.Button(frame, text="شروع بررسی", command=self.start_check_links)
        start_button.grid(row=7, column=0, columnspan=3, pady=(10, 0))
        self.add_tooltip(start_button, "بررسی لینک‌ها را شروع کنید.")

    def add_tooltip(self, widget, text):
        tooltip = tk.Toplevel(widget)
        tooltip.withdraw()
        tooltip.overrideredirect(True)
        label = tk.Label(tooltip, text=text, background="yellow", relief="solid", borderwidth=1)
        label.pack()

        def enter(event):
            x = widget.winfo_rootx() + 20
            y = widget.winfo_rooty() + 20
            tooltip.geometry(f"+{x}+{y}")
            tooltip.deiconify()

        def leave(event):
            tooltip.withdraw()

        widget.bind("<Enter>", enter)
        widget.bind("<Leave>", leave)

    def browse_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        if file_path:
            self.input_entry.delete(0, tk.END)
            self.input_entry.insert(0, file_path)

    def save_file(self):
        formats = {
            'CSV': (".csv", ["CSV files", "*.csv"]),
            'Text': (".txt", ["Text files", "*.txt"])
        }
        selected_format = self.format_var.get()
        extension, filetype = formats.get(selected_format, formats['CSV'])
        file_path = filedialog.asksaveasfilename(defaultextension=extension, filetypes=[(filetype[0], filetype[1])])
        if file_path:
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, file_path)

    def start_check_links(self):
        input_file = self.input_entry.get()
        output_file = self.output_entry.get()
        output_format = self.format_var.get().lower()
        max_workers = self.workers_var.get()
        if not input_file or not output_file:
            messagebox.showerror("خطا", "لطفاً فایل ورودی و خروجی را مشخص کنید.")
            return

        def progress_callback(progress, message):
            self.progress_bar['value'] = progress
            self.progress_label.config(text=message)
            self.root.update_idletasks()

        def run_check_links():
            try:
                self.check_links(input_file, output_file, output_format, max_workers, progress_callback)
                messagebox.showinfo("اتمام", "بررسی لینک‌ها با موفقیت انجام شد.")
            except Exception as e:
                logging.error("Error checking links", exc_info=True)
                messagebox.showerror("خطا", str(e))

        thread = threading.Thread(target=run_check_links)
        thread.start()

    def check_links(self, input_file, output_file, output_format, max_workers, progress_callback=None):
        with open(input_file, 'r', encoding='utf-8') as txtfile:
            links = txtfile.readlines()

        total_links = len(links)
        broken_links = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_link = {executor.submit(self.check_link, link): link for link in links}
            for idx, future in enumerate(as_completed(future_to_link), start=1):
                result = future.result()
                if result:
                    broken_links.append(result)
                if progress_callback:
                    progress_callback(int((idx / total_links) * 100), f"Checking link {idx}/{total_links} - Broken: {len(broken_links)}")

        if output_format == 'csv':
            with open(output_file, mode='w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['Link', 'Error'])
                for link, error in broken_links:
                    writer.writerow([link, error])

        if progress_callback:
            progress_callback(100, f"Broken links saved to {output_file}")

    def check_link(self, link):
        link = link.strip()
        if link:
            try:
                response = requests.head(link, timeout=10, allow_redirects=True)
                if response.status_code == 404:
                    return link, "404 Not Found"
                elif response.status_code >= 400:
                    return link, f"Error {response.status_code}"
            except requests.Timeout:
                return link, "Timeout"
            except requests.ConnectionError:
                return link, "Connection Error"
            except requests.RequestException as e:
                return link, str(e)
        return None

if __name__ == "__main__":
    root = tk.Tk()
    app = LinkCheckerApp(root)
    root.mainloop()