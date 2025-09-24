"""
Aplikasi GUI Steganografi Audio dengan Multiple-LSB
Menggunakan Tkinter untuk interface pengguna
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import threading
import traceback
from typing import Optional
import numpy as np

# Import modul lokal
from audio_handler import AudioHandler
from stegano import MultipleLSBSteganography, calculate_psnr, evaluate_audio_quality


class SteganographyApp:
    """
    Aplikasi GUI untuk steganografi audio
    """
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Steganografi Audio - Multiple LSB")
        self.root.geometry("800x600")
        
        # Initialize handlers
        self.audio_handler = AudioHandler()
        self.steganography = MultipleLSBSteganography()
        
        # Variables
        self.cover_file = tk.StringVar()
        self.secret_file = tk.StringVar()
        self.output_file = tk.StringVar()
        self.stego_file = tk.StringVar()
        self.extract_output = tk.StringVar()
        
        self.n_lsb = tk.IntVar(value=2)
        self.use_encryption = tk.BooleanVar()
        self.use_random_placement = tk.BooleanVar()
        self.encryption_key = tk.StringVar()
        self.stego_key = tk.StringVar()
        
        # Status variables
        self.status_text = tk.StringVar(value="Ready")
        self.psnr_text = tk.StringVar(value="PSNR: -")
        self.progress_var = tk.DoubleVar()
        
        self.setup_gui()
    
    def setup_gui(self):
        """
        Setup GUI components
        """
        # Main frame dengan padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="Steganografi Audio - Multiple LSB", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, pady=(0, 20))
        
        # Notebook untuk tabs
        notebook = ttk.Notebook(main_frame)
        notebook.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Tab Embed
        embed_frame = ttk.Frame(notebook, padding="10")
        notebook.add(embed_frame, text="Embed Message")
        self.setup_embed_tab(embed_frame)
        
        # Tab Extract
        extract_frame = ttk.Frame(notebook, padding="10")
        notebook.add(extract_frame, text="Extract Message")
        self.setup_extract_tab(extract_frame)
        
        # Status bar
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        status_frame.columnconfigure(0, weight=1)
        
        ttk.Label(status_frame, textvariable=self.status_text).grid(row=0, column=0, sticky=tk.W)
        ttk.Label(status_frame, textvariable=self.psnr_text).grid(row=0, column=1, sticky=tk.E)
        
        # Progress bar
        self.progress_bar = ttk.Progressbar(status_frame, variable=self.progress_var, 
                                          mode='determinate')
        self.progress_bar.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 0))
    
    def setup_embed_tab(self, parent):
        """
        Setup tab untuk embedding
        """
        parent.columnconfigure(1, weight=1)
        
        row = 0
        
        # Cover audio file
        ttk.Label(parent, text="Cover Audio (MP3):").grid(row=row, column=0, sticky=tk.W, pady=2)
        ttk.Entry(parent, textvariable=self.cover_file, width=50).grid(row=row, column=1, sticky=(tk.W, tk.E), padx=(10, 5), pady=2)
        ttk.Button(parent, text="Browse", command=self.browse_cover_file).grid(row=row, column=2, pady=2)
        row += 1
        
        # Secret file
        ttk.Label(parent, text="Secret File:").grid(row=row, column=0, sticky=tk.W, pady=2)
        ttk.Entry(parent, textvariable=self.secret_file, width=50).grid(row=row, column=1, sticky=(tk.W, tk.E), padx=(10, 5), pady=2)
        ttk.Button(parent, text="Browse", command=self.browse_secret_file).grid(row=row, column=2, pady=2)
        row += 1
        
        # Output file
        ttk.Label(parent, text="Output File:").grid(row=row, column=0, sticky=tk.W, pady=2)
        ttk.Entry(parent, textvariable=self.output_file, width=50).grid(row=row, column=1, sticky=(tk.W, tk.E), padx=(10, 5), pady=2)
        ttk.Button(parent, text="Save As", command=self.browse_output_file).grid(row=row, column=2, pady=2)
        row += 1
        
        # Separator
        ttk.Separator(parent, orient='horizontal').grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        row += 1
        
        # Options frame
        options_frame = ttk.LabelFrame(parent, text="Options", padding="5")
        options_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        options_frame.columnconfigure(1, weight=1)
        row += 1
        
        # n-LSB selection
        ttk.Label(options_frame, text="n-LSB:").grid(row=0, column=0, sticky=tk.W, pady=2)
        lsb_combo = ttk.Combobox(options_frame, textvariable=self.n_lsb, values=[1, 2, 3, 4], 
                                state="readonly", width=10)
        lsb_combo.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        
        # Use encryption checkbox
        encryption_check = ttk.Checkbutton(options_frame, text="Use Encryption", 
                                         variable=self.use_encryption,
                                         command=self.toggle_encryption)
        encryption_check.grid(row=1, column=0, sticky=tk.W, pady=2)
        
        # Encryption key
        self.encryption_key_entry = ttk.Entry(options_frame, textvariable=self.encryption_key, 
                                            show="*", state="disabled")
        self.encryption_key_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=2)
        
        # Use random placement checkbox
        random_check = ttk.Checkbutton(options_frame, text="Use Random Placement", 
                                     variable=self.use_random_placement,
                                     command=self.toggle_random_placement)
        random_check.grid(row=2, column=0, sticky=tk.W, pady=2)
        
        # Stego key
        self.stego_key_entry = ttk.Entry(options_frame, textvariable=self.stego_key, 
                                       state="disabled")
        self.stego_key_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=2)
        
        # Embed button
        embed_btn = ttk.Button(parent, text="Embed Message", command=self.embed_message, 
                              style="Accent.TButton")
        embed_btn.grid(row=row, column=0, columnspan=3, pady=20)
    
    def setup_extract_tab(self, parent):
        """
        Setup tab untuk extraction
        """
        parent.columnconfigure(1, weight=1)
        
        row = 0
        
        # Stego audio file
        ttk.Label(parent, text="Stego Audio (MP3):").grid(row=row, column=0, sticky=tk.W, pady=2)
        ttk.Entry(parent, textvariable=self.stego_file, width=50).grid(row=row, column=1, sticky=(tk.W, tk.E), padx=(10, 5), pady=2)
        ttk.Button(parent, text="Browse", command=self.browse_stego_file).grid(row=row, column=2, pady=2)
        row += 1
        
        # Output directory
        ttk.Label(parent, text="Extract to:").grid(row=row, column=0, sticky=tk.W, pady=2)
        ttk.Entry(parent, textvariable=self.extract_output, width=50).grid(row=row, column=1, sticky=(tk.W, tk.E), padx=(10, 5), pady=2)
        ttk.Button(parent, text="Browse", command=self.browse_extract_output).grid(row=row, column=2, pady=2)
        row += 1
        
        # Separator
        ttk.Separator(parent, orient='horizontal').grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        row += 1
        
        # Extract options frame
        extract_options_frame = ttk.LabelFrame(parent, text="Extract Options", padding="5")
        extract_options_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        extract_options_frame.columnconfigure(1, weight=1)
        row += 1
        
        # n-LSB for extraction (should match embedding)
        ttk.Label(extract_options_frame, text="n-LSB:").grid(row=0, column=0, sticky=tk.W, pady=2)
        extract_lsb_combo = ttk.Combobox(extract_options_frame, textvariable=self.n_lsb, 
                                       values=[1, 2, 3, 4], state="readonly", width=10)
        extract_lsb_combo.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        
        # Decryption key
        ttk.Label(extract_options_frame, text="Decryption Key:").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Entry(extract_options_frame, textvariable=self.encryption_key, 
                 show="*").grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=2)
        
        # Random placement (for extraction)
        ttk.Label(extract_options_frame, text="Stego Key (if random):").grid(row=2, column=0, sticky=tk.W, pady=2)
        ttk.Entry(extract_options_frame, textvariable=self.stego_key).grid(row=2, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=2)
        
        # Extract button
        extract_btn = ttk.Button(parent, text="Extract Message", command=self.extract_message, 
                               style="Accent.TButton")
        extract_btn.grid(row=row, column=0, columnspan=3, pady=20)
    
    def toggle_encryption(self):
        """Toggle encryption key entry state"""
        if self.use_encryption.get():
            self.encryption_key_entry.config(state="normal")
        else:
            self.encryption_key_entry.config(state="disabled")
            self.encryption_key.set("")
    
    def toggle_random_placement(self):
        """Toggle stego key entry state"""
        if self.use_random_placement.get():
            self.stego_key_entry.config(state="normal")
        else:
            self.stego_key_entry.config(state="disabled")
            self.stego_key.set("")
    
    def browse_cover_file(self):
        """Browse for cover audio file"""
        filename = filedialog.askopenfilename(
            title="Select Cover Audio (MP3)",
            filetypes=[
                ("MP3 files", "*.mp3"),
                ("All files", "*.*")
            ]
        )
        if filename:
            self.cover_file.set(filename)
    
    def browse_secret_file(self):
        """Browse for secret file"""
        filename = filedialog.askopenfilename(
            title="Select Secret File",
            filetypes=[
                ("All files", "*.*"),
                ("Text files", "*.txt"),
                ("Image files", "*.png *.jpg *.jpeg"),
                ("PDF files", "*.pdf")
            ]
        )
        if filename:
            self.secret_file.set(filename)
    
    def browse_output_file(self):
        """Browse for output file location"""
        filename = filedialog.asksaveasfilename(
            title="Save Stego Audio As (MP3)",
            defaultextension=".mp3",
            filetypes=[
                ("MP3 files", "*.mp3"),
                ("All files", "*.*")
            ]
        )
        if filename:
            self.output_file.set(filename)
    
    def browse_stego_file(self):
        """Browse for stego audio file"""
        filename = filedialog.askopenfilename(
            title="Select Stego Audio (MP3)",
            filetypes=[
                ("MP3 files", "*.mp3"),
                ("All files", "*.*")
            ]
        )
        if filename:
            self.stego_file.set(filename)
    
    def browse_extract_output(self):
        """Browse for extract output directory"""
        dirname = filedialog.askdirectory(
            title="Select Output Directory"
        )
        if dirname:
            self.extract_output.set(dirname)
    
    def update_progress(self, value, status="Processing..."):
        """Update progress bar and status"""
        self.progress_var.set(value)
        self.status_text.set(status)
        self.root.update_idletasks()
    
    def embed_message(self):
        """Embed secret message into cover audio"""
        # Validasi input
        if not self.cover_file.get():
            messagebox.showerror("Error", "Please select cover audio file")
            return
        
        if not self.secret_file.get():
            messagebox.showerror("Error", "Please select secret file")
            return
        
        if not self.output_file.get():
            messagebox.showerror("Error", "Please specify output file")
            return
        
        if self.use_encryption.get() and not self.encryption_key.get():
            messagebox.showerror("Error", "Please enter encryption key")
            return
        
        if self.use_random_placement.get() and not self.stego_key.get():
            messagebox.showerror("Error", "Please enter stego key for random placement")
            return
        
        # Run embedding in separate thread
        def embed_worker():
            try:
                self.update_progress(10, "Loading cover audio...")
                
                # Load cover audio
                cover_samples, sample_rate = self.audio_handler.load_mp3(self.cover_file.get())
                
                self.update_progress(20, "Loading secret file...")
                
                # Load secret file
                with open(self.secret_file.get(), 'rb') as f:
                    secret_data = f.read()
                
                secret_filename = os.path.basename(self.secret_file.get())
                
                self.update_progress(30, "Embedding message...")
                
                # Prepare parameters
                encryption_key = self.encryption_key.get() if self.use_encryption.get() else None
                stego_key = self.stego_key.get() if self.use_random_placement.get() else None
                
                # Embed message
                stego_samples, embed_status = self.steganography.embed(
                    audio_samples=cover_samples,
                    secret_data=secret_data,
                    n_lsb=self.n_lsb.get(),
                    filename=secret_filename,
                    encryption_key=encryption_key,
                    use_random_placement=self.use_random_placement.get(),
                    stego_key=stego_key
                )
                
                self.update_progress(70, "Calculating PSNR...")
                
                # Calculate PSNR
                psnr = calculate_psnr(cover_samples.astype(np.float64), 
                                    stego_samples.astype(np.float64))
                quality = evaluate_audio_quality(psnr)
                
                self.update_progress(90, "Saving stego audio...")
                
                # Save stego audio (always MP3)
                self.audio_handler.save_mp3(stego_samples, sample_rate, self.output_file.get())
                
                self.update_progress(100, f"Embedding completed! {embed_status}")
                self.psnr_text.set(f"PSNR: {psnr:.2f} dB ({quality})")
                
                messagebox.showinfo("Success", 
                                  f"Message embedded successfully!\n"
                                  f"PSNR: {psnr:.2f} dB ({quality})\n"
                                  f"Output: {self.output_file.get()}")
                
            except Exception as e:
                self.update_progress(0, "Error occurred")
                messagebox.showerror("Error", f"Embedding failed:\n{str(e)}")
                print(f"Embedding error: {traceback.format_exc()}")
        
        # Start embedding in background thread
        thread = threading.Thread(target=embed_worker)
        thread.daemon = True
        thread.start()
    
    def extract_message(self):
        """Extract secret message from stego audio"""
        # Validasi input
        if not self.stego_file.get():
            messagebox.showerror("Error", "Please select stego audio file")
            return
        
        if not self.extract_output.get():
            messagebox.showerror("Error", "Please specify output directory")
            return
        
        # Run extraction in separate thread
        def extract_worker():
            try:
                self.update_progress(10, "Loading stego audio...")
                
                # Load stego audio
                stego_samples, sample_rate = self.audio_handler.load_mp3(self.stego_file.get())
                
                self.update_progress(30, "Extracting message...")
                
                # Prepare parameters
                decryption_key = self.encryption_key.get() if self.encryption_key.get() else None
                stego_key = self.stego_key.get() if self.stego_key.get() else None
                use_random = bool(stego_key)
                
                # Extract message
                filename, extracted_data, extract_status = self.steganography.extract(
                    stego_samples=stego_samples,
                    n_lsb=self.n_lsb.get(),
                    decryption_key=decryption_key,
                    use_random_placement=use_random,
                    stego_key=stego_key
                )
                
                self.update_progress(80, "Saving extracted file...")
                
                # Save extracted data
                if not filename:
                    filename = "extracted_data"
                
                output_path = os.path.join(self.extract_output.get(), filename)
                
                # Handle file conflicts
                counter = 1
                base_path = output_path
                while os.path.exists(output_path):
                    name, ext = os.path.splitext(base_path)
                    output_path = f"{name}_{counter}{ext}"
                    counter += 1
                
                with open(output_path, 'wb') as f:
                    f.write(extracted_data)
                
                self.update_progress(100, f"Extraction completed! {extract_status}")
                
                messagebox.showinfo("Success", 
                                  f"Message extracted successfully!\n"
                                  f"File: {filename}\n"
                                  f"Size: {len(extracted_data)} bytes\n"
                                  f"Saved to: {output_path}")
                
            except Exception as e:
                self.update_progress(0, "Error occurred")
                messagebox.showerror("Error", f"Extraction failed:\n{str(e)}")
                print(f"Extraction error: {traceback.format_exc()}")
        
        # Start extraction in background thread
        thread = threading.Thread(target=extract_worker)
        thread.daemon = True
        thread.start()
    
    def run(self):
        """Run the application"""
        self.root.mainloop()


def main():
    """Main function"""
    try:
        app = SteganographyApp()
        app.run()
    except Exception as e:
        print(f"Application error: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()