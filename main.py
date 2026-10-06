import os
import random
import json
import datetime
import numpy as np
from PIL import Image, ImageEnhance, ImageOps
import piexif

HISTORY_FILE = "used_file_names.json"

# Listes de modèles d'iPhone pour la génération EXIF aléatoire
IPHONE_MODELS = [
    {"make": "Apple", "model": "iPhone 11", "software": "16.5", "focal": (26, 1), "fnum": (18, 10)},
    {"make": "Apple", "model": "iPhone 12", "software": "17.1.1", "focal": (26, 1), "fnum": (16, 10)},
    {"make": "Apple", "model": "iPhone 13", "software": "17.4", "focal": (26, 1), "fnum": (16, 10)},
    {"make": "Apple", "model": "iPhone 14", "software": "17.5.1", "focal": (26, 1), "fnum": (15, 10)},
    {"make": "Apple", "model": "iPhone 15", "software": "17.6", "focal": (24, 1), "fnum": (16, 10)},
]

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_history(history_set):
    with open(HISTORY_FILE, "w") as f:
        json.dump(list(history_set), f)

def generate_unique_filename(used_numbers_set):
    while True:
        rand_num = random.randint(1000, 9999)
        if rand_num not in used_numbers_set:
            used_numbers_set.add(rand_num)
            return f"IMG_{rand_num}.jpg"

def generate_iphone_exif():
    """Génère un bloc binaire EXIF réaliste simulant une prise de vue par iPhone."""
    device = random.choice(IPHONE_MODELS)
    
    # Génération d'une date de prise de vue récente aléatoire (dans les 30 derniers jours)
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
        piexif.ExifIFD.ColorSpace: 1,  # sRGB
        piexif.ExifIFD.ExifVersion: b"0232",
        piexif.ExifIFD.ComponentsConfiguration: b"\x01\x02\x03\x00",
        piexif.ExifIFD.FocalLength: device["focal"],
        piexif.ExifIFD.FNumber: device["fnum"],
        piexif.ExifIFD.ISOSpeedRatings: random.choice([50, 64, 80, 100, 125, 160]),
        piexif.ExifIFD.LensModel: f"{device['model']} back camera 5.96mm f/{device['fnum'][0]/10}",
    }

    exif_dict = {"0th": zeroth_ifd, "Exif": exif_ifd, "1st": {}, "GPS": {}, "Interop": {}}
    return piexif.dump(exif_dict)

def add_gaussian_noise_and_steganography(img, magnitude=2.5):
    """
    1. Ajoute un bruit gaussien (grain ISO) pour casser les fréquences du pHash.
    2. Applique une altération LSB (+1/-1 aléatoire sur des pixels) pour modifier la structure fine.
    """
    img_array = np.array(img).astype(np.int16)
    
    # Bruit gaussien
    noise = np.random.normal(0, magnitude, img_array.shape)
    img_array = img_array + noise
    
    # Stéganographie légère (perturbation des valeurs faibles)
    random_shifts = np.random.choice([-1, 0, 1], size=img_array.shape, p=[0.1, 0.8, 0.1])
    img_array = img_array + random_shifts

    noisy_array = np.clip(img_array, 0, 255).astype(np.uint8)
    return Image.fromarray(noisy_array)

def dynamic_crop_to_ratio(img, target_ratio=(3, 4)):
    """
    Recadrage 3:4 avec Micro-Crop dynamique (décalage du centre de 1% à 3%).
    """
    orig_w, orig_h = img.size
    target_aspect = target_ratio[0] / target_ratio[1]
    orig_aspect = orig_w / orig_h

    if orig_aspect > target_aspect:
        new_w = int(orig_h * target_aspect)
        new_h = orig_h
        max_offset = orig_w - new_w
        # Décalage aléatoire du centre
        left = random.randint(0, max_offset) if max_offset > 0 else 0
        top = 0
    else:
        new_w = orig_w
        new_h = int(orig_w / target_aspect)
        max_offset = orig_h - new_h
        left = 0
        top = random.randint(0, max_offset) if max_offset > 0 else 0

    return img.crop((left, top, left + new_w, top + new_h))

def process_single_image(img, output_path, target_width=1080):
    # 1. Micro-Flip Horizontal aléatoire (15% de chance si adapté)
    if random.random() < 0.15:
        img = ImageOps.mirror(img)

    # 2. Recadrage dynamique (Jitter Crop)
    img_cropped = dynamic_crop_to_ratio(img, target_ratio=(3, 4))

    # 3. Redimensionnement
    target_height = int(target_width * (4 / 3))
    img_resized = img_cropped.resize((target_width, target_height), Image.Resampling.LANCZOS)

    # 4. Nettoyage du canvas
    clean_img = Image.new(img_resized.mode, img_resized.size)
    clean_img.putdata(list(img_resized.getdata()))

    # 5. Micro-rotation (-0.5° à +0.5°)
    angle = random.uniform(-0.5, 0.5)
    clean_img = clean_img.rotate(angle, resample=Image.BICUBIC, expand=False)

    # 6. Luminosité, Contraste et Saturation
    clean_img = ImageEnhance.Brightness(clean_img).enhance(random.uniform(0.97, 1.03))
    clean_img = ImageEnhance.Contrast(clean_img).enhance(random.uniform(0.97, 1.03))
    clean_img = ImageEnhance.Color(clean_img).enhance(random.uniform(0.98, 1.02))

    # 7. Bruit numérique + Perturbation LSB
    clean_img = add_gaussian_noise_and_steganography(clean_img, magnitude=random.uniform(1.8, 3.2))

    # 8. Génération des faux EXIF iPhone
    exif_bytes = generate_iphone_exif()

    # 9. Sauvegarde avec EXIF injectés
    clean_img.save(
        output_path,
        format="JPEG",
        quality=random.randint(92, 96),
        optimize=True,
        exif=exif_bytes
    )

def process_folder_advanced(input_folder, output_base_folder, num_folders=10):
    valid_extensions = ('.jpg', '.jpeg', '.png', '.webp', '.heic')
    
    input_files = [f for f in os.listdir(input_folder) if f.lower().endswith(valid_extensions)]
    if not input_files:
        print("[-] Aucune image trouvée.")
        return

    used_numbers_set = load_history()
    print(f"[*] Noms en mémoire : {len(used_numbers_set)}")

    for folder_idx in range(1, num_folders + 1):
        subfolder_name = f"dossier_{folder_idx}"
        subfolder_path = os.path.join(output_base_folder, subfolder_name)
        os.makedirs(subfolder_path, exist_ok=True)

        for filename in input_files:
            in_path = os.path.join(input_folder, filename)
            out_filename = generate_unique_filename(used_numbers_set)
            out_path = os.path.join(subfolder_path, out_filename)

            try:
                with Image.open(in_path) as img:
                    if img.mode in ("RGBA", "P"):
                        img = img.convert("RGB")
                    img = ImageOps.exif_transpose(img)
                    process_single_image(img, out_path)
            except Exception as e:
                print(f"[-] Erreur sur {filename} : {e}")

        print(f"[+] {subfolder_name} généré.")

    save_history(used_numbers_set)
    print(f"\n[✓] Traitement terminé avec succès.")

if __name__ == "__main__":
    folder_in = "./photos_originales"
    folder_out = "./photos_traitees"
    
    process_folder_advanced(folder_in, folder_out, num_folders=10)
