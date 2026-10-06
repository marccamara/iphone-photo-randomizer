import os
import random
import json
import datetime
import threading
import numpy as np
from PIL import Image, ImageEnhance, ImageOps
import piexif
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

HISTORY_FILE = "used_file_names.json"

IPHONE_MODELS = [
    {"make": "Apple", "model": "iPhone 11", "software": "16.5", "focal": (26, 1), "fnum": (18, 10)},
    {"make": "Apple", "model": "iPhone 12", "software": "17.1.1", "focal": (26, 1), "fnum": (16, 10)},
    {"make": "Apple", "model": "iPhone 13", "software": "17.4", "focal": (26, 1), "fnum": (16, 10)},
    {"make": "Apple", "model": "iPhone 14", "software": "17.5.1", "focal": (26, 1), "fnum": (15, 10)},
    {"make": "Apple", "model": "iPhone 15", "software": "17.6", "focal": (24, 1), "fnum": (16, 10)},
]

class PhotoRandomizerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Rando Camara - iOS Edition")
        self.root.geometry("380x650")
        self.root.config(bg="#0b0b0f") # Fond sombre style OLED

        self.input_dir = ""
        
        # Dossier de sortie configuré automatiquement dans l'app "Fichiers" d'iOS (~/Documents/photos_traitees)
        docs_path = os.path.expanduser("~/Documents")
        self.output_dir = os.path.join(docs_path, "photos_traitees")
        os.makedirs(self.output_dir, exist_ok=True)

        self.create_widgets()

    def create_widgets(self):
        # En-tête style "BioGenerator"
        header_frame = tk.Frame(self.root, bg="#0b0b0f")
        header_frame.pack(pady=20)

        title_label = tk.Label(header_frame, text="🍓 RandoCamara", font=("Helvetica", 22, "bold"), fg="#ff3366", bg="#0b0b0f")
        title_label.pack()

        subtitle_label = tk.Label(header_frame, text="Anti-Detect • Glassmorphism Edition", font=("Helvetica", 10), fg="#8a8a9e", bg="#0b0b0f")
        subtitle_label.pack(pady=2)

        # Section Sélection Dossier Source
        self.create_card("DOSSIER SOURCE (PHOTOS ORIGINALES)", self.select_input, "Sélectionner...", "input_lbl", show_btn=True)

        # Section Dossier de Sortie (Automatique dans l'app Fichiers)
        self.create_card("DOSSIER DE SORTIE (APPLI FICHIERS)", None, "Documents/photos_traitees", "output_lbl", show_btn=False)

        # Barre de progression
        progress_frame = tk.Frame(self.root, bg="#161622", bd=0)
        progress_frame.pack(padx=20, pady=15, fill="x")
        
        tk.Label(progress_frame, text="PROGRESSION DU TRAITEMENT", font=("Helvetica", 9, "bold"), fg="#ff3366", bg="#161622").pack(anchor="w", padx=10, pady=5)
        
        self.progress_bar = ttk.Progressbar(progress_frame, orient="horizontal", length=300, mode="determinate")
        self.progress_bar.pack(padx=10, pady=10, fill="x")

        self.status_label = tk.Label(progress_frame, text="En attente de lancement...", font=("Helvetica", 9), fg="#a0a0b2", bg="#161622")
        self.status_label.pack(anchor="w", padx=10, pady=5)

        # Bouton Principal de Lancement (style néon rose)
        self.btn_start = tk.Button(self.root, text="✨ Lancer le Randomizer", font=("Helvetica", 12, "bold"), fg="white", bg="#ff2d55", activebackground="#e0244c", bd=0, relief="flat", command=self.start_process_thread)
        self.btn_start.pack(padx=20, pady=20, fill="x", ipady=12)

    def create_card(self, title, command, default_text, attr_name, show_btn=True):
        card = tk.Frame(self.root, bg="#161622", bd=0)
        card.pack(padx=20, pady=8, fill="x")

        tk.Label(card, text=title, font=("Helvetica", 9, "bold"), fg="#ff3366", bg="#161622").pack(anchor="w", padx=12, pady=5)

        inner_frame = tk.Frame(card, bg="#1c1c2b")
        inner_frame.pack(padx=10, pady=5, fill="x")

        lbl = tk.Label(inner_frame, text=default_text, font=("Helvetica", 10), fg="#c0c0d0", bg="#1c1c2b", anchor="w")
        lbl.pack(side="left", padx=10, pady=10, fill="x", expand=True)
        setattr(self, attr_name, lbl)

        if show_btn:
            btn = tk.Button(inner_frame, text="📁", font=("Helvetica", 10), fg="white", bg="#2c2c3e", bd=0, command=command)
            btn.pack(side="right", padx=5, pady=5)

    def select_input(self):
        dir_path = filedialog.askdirectory()
        if dir_path:
            self.input_dir = dir_path
            self.input_lbl.config(text=os.path.basename(dir_path) or dir_path)

    def start_process_thread(self):
        if not self.input_dir:
            messagebox.showerror("Erreur", "Veuillez sélectionner le dossier source des photos originales !")
            return
        
        self.btn_start.config(state="disabled")
        threading.Thread(target=self.run_processing, daemon=True).start()

    def run_processing(self):
        try:
            self.status_label.config(text="Chargement de l'historique...")
            valid_extensions = ('.jpg', '.jpeg', '.png', '.webp', '.heic')
            input_files = [f for f in os.listdir(self.input_dir) if f.lower().endswith(valid_extensions)]
            
            if not input_files:
                self.status_label.config(text="Aucune image trouvée.")
                self.btn_start.config(state="normal")
                return

            used_numbers_set = self.load_history()
            num_folders = 10
            total_steps = len(input_files) * num_folders
            current_step = 0
            
            self.progress_bar["maximum"] = total_steps

            for folder_idx in range(1, num_folders + 1):
                subfolder_name = f"dossier_{folder_idx}"
                subfolder_path = os.path.join(self.output_dir, subfolder_name)
                os.makedirs(subfolder_path, exist_ok=True)

                for filename in input_files:
                    current_step += 1
                    self.progress_bar["value"] = current_step
                    self.status_label.config(text=f"Traitement : {subfolder_name}/{filename}")
                    
                    in_path = os.path.join(self.input_dir, filename)
                    out_filename = self.generate_unique_filename(used_numbers_set)
                    out_path = os.path.join(subfolder_path, out_filename)

                    try:
                        with Image.open(in_path) as img:
                            if img.mode in ("RGBA", "P"):
                                img = img.convert("RGB")
                            img = ImageOps.exif_transpose(img)
                            self.process_single_image(img, out_path)
                    except Exception as e:
                        print(f"Erreur {filename}: {e}")

            self.save_history(used_numbers_set)
            self.status_label.config(text="✓ Traitement terminé avec succès !")
            messagebox.showinfo("Succès", "Toutes les photos ont été randomisées dans l'app Fichiers !")
        except Exception as ex:
            self.status_label.config(text=f"Erreur critique : {ex}")
        finally:
            self.btn_start.config(state="normal")

    def load_history(self):
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r") as f:
                    return set(json.load(f))
            except:
                return set()
        return set()

    def save_history(self, history_set):
        with open(HISTORY_FILE, "w") as f:
            json.dump(list(history_set), f)

    def generate_unique_filename(self, used_numbers_set):
        while True:
            rand_num = random.randint(1000, 9999)
            if rand_num not in used_numbers_set:
                used_numbers_set.add(rand_num)
                return f"IMG_{rand_num}.jpg"

    def generate_iphone_exif(self):
        device = random.choice(IPHONE_MODELS)
        now = datetime.datetime.now()
        random_days = random.randint(1, 30)
        random_seconds = random.randint(0, 86400)
        photo_date = now - datetime.timedelta(days=random_days, seconds=random_seconds)
        date_str = photo_date.strftime("%Y:%m:%d %H:%M:%S")

        zeroth_ifd = {
            piexif.ImageIFD.Make: device["make"],
            piexif.ImageIFD.Model: device["model"],
            piexif.ImageIFD.Software: f"iOS {device['software']}",
            piexif.ImageIFD.Orientation: 1,
            piexif.ImageIFD.XResolution: (72, 1),
            piexif.ImageIFD.YResolution: (72, 1),
            piexif.ImageIFD.ResolutionUnit: 2,
            piexif.ImageIFD.DateTime: date_str,
        }

        exif_ifd = {
            piexif.ExifIFD.DateTimeOriginal: date_str,
            piexif.ExifIFD.DateTimeDigitized: date_str,
            piexif.ExifIFD.OffsetTimeOriginal: "+03:00",
            piexif.ExifIFD.ColorSpace: 1,
            piexif.ExifIFD.ExifVersion: b"0232",
            piexif.ExifIFD.ComponentsConfiguration: b"\x01\x02\x03\x00",
            piexif.ExifIFD.FocalLength: device["focal"],
            piexif.ExifIFD.FNumber: device["fnum"],
            piexif.ExifIFD.ISOSpeedRatings: random.choice([50, 64, 80, 100, 125, 160]),
            piexif.ExifIFD.LensModel: f"{device['model']} back camera 5.96mm f/{device['fnum'][0]/10}",
        }

        exif_dict = {"0th": zeroth_ifd, "Exif": exif_ifd, "1st": {}, "GPS": {}, "Interop": {}}
        return piexif.dump(exif_dict)

    def add_gaussian_noise_and_steganography(self, img, magnitude=2.5):
        img_array = np.array(img).astype(np.int16)
        noise = np.random.normal(0, magnitude, img_array.shape)
        img_array = img_array + noise
        random_shifts = np.random.choice([-1, 0, 1], size=img_array.shape, p=[0.1, 0.8, 0.1])
        img_array = img_array + random_shifts
        noisy_array = np.clip(img_array, 0, 255).astype(np.uint8)
        return Image.fromarray(noisy_array)

    def dynamic_crop_to_ratio(self, img, target_ratio=(3, 4)):
        orig_w, orig_h = img.size
        target_aspect = target_ratio[0] / target_ratio[1]
        orig_aspect = orig_w / orig_h

        if orig_aspect > target_aspect:
            new_w = int(orig_h * target_aspect)
            new_h = orig_h
            max_offset = orig_w - new_w
            left = random.randint(0, max_offset) if max_offset > 0 else 0
            top = 0
        else:
            new_w = orig_w
            new_h = int(orig_w / target_aspect)
            max_offset = orig_h - new_h
            left = 0
            top = random.randint(0, max_offset) if max_offset > 0 else 0

        return img.crop((left, top, left + new_w, top + new_h))

    def process_single_image(self, img, output_path, target_width=1080):
        if random.random() < 0.15:
            img = ImageOps.mirror(img)

        img_cropped = self.dynamic_crop_to_ratio(img, target_ratio=(3, 4))
        target_height = int(target_width * (4 / 3))
        img_resized = img_cropped.resize((target_width, target_height), Image.Resampling.LANCZOS)

        clean_img = Image.new(img_resized.mode, img_resized.size)
        clean_img.putdata(list(img_resized.getdata()))

        angle = random.uniform(-0.5, 0.5)
        clean_img = clean_img.rotate(angle, resample=Image.BICUBIC, expand=False)

        clean_img = ImageEnhance.Brightness(clean_img).enhance(random.uniform(0.97, 1.03))
        clean_img = ImageEnhance.Contrast(clean_img).enhance(random.uniform(0.97, 1.03))
        clean_img = ImageEnhance.Color(clean_img).enhance(random.uniform(0.98, 1.02))

        clean_img = self.add_gaussian_noise_and_steganography(clean_img, magnitude=random.uniform(1.8, 3.2))
        exif_bytes = self.generate_iphone_exif()

        clean_img.save(
            output_path,
            format="JPEG",
            quality=random.randint(92, 96),
            optimize=True,
            exif=exif_bytes
        )

if __name__ == "__main__":
    root = tk.Tk()
    app = PhotoRandomizerApp(root)
    root.mainloop()
