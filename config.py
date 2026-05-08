import json
import os
import shutil
from datetime import date

APP_VERSION = "v0.2"
BUILD_DATE = date.today().strftime("%d-%m-%Y")
AUTHOR = " Domenico Spagnuolo"

JSONS_DIR = os.path.join(os.path.dirname(__file__), "JSONS")
CONF_FILE = os.path.join(JSONS_DIR, "asym_conf.json")
PACKAGE_LIST_FILE = os.path.join(JSONS_DIR, "package_list.json")
ICON_PATH = os.path.join(os.path.dirname(__file__), "Images", "ASym.ico")

STRINGS = {
    "en": {
        "wizard_title": "AllegroSym – First Setup",
        "select_language": "Select Language",
        "select_theme": "Select Theme",
        "select_output": "Output Folder (ASymOut)",
        "browse": "Browse…",
        "finish": "Finish",
        "dark": "Dark",
        "light": "Light",
        "english": "English",
        "italian": "Italian",
        "settings": "Settings",
        "toggle_theme": "Toggle Theme",
        "help": "Help",
        "output_folder": "Output Folder",
        "language": "Language",
        "about": "About",
        "user_manual": "User Manual",
        "release_notes": "Release Notes",
        "about_title": "About AllegroSym",
        "version": "Version",
        "build_date": "Build Date",
        "author": "Author",
        "close": "Close",
        "save": "Save",
        "settings_title": "Settings",
        "no_manual": "No User Manual found.",
        "no_release_notes": "No Release Notes found.",
        "main_title": "AllegroSym",
        "wizard_output_hint": "Choose a folder where ASymOut will be created",
        "new_symbol": "New Symbol",
        "edit_symbol": "Edit Symbol",
        "symbol_name": "Symbol Name",
        "package_type": "Package Type",
        "add_package": "Add Package",
        "edit_package": "Edit Package",
        "delete_package": "Delete Package",
        "show_packages": "Show Packages",
        "no_packages": "No packages defined yet.",
        "package_name": "Package Name",
        "package_pins": "Number of Pins",
        "pick_footprint": "Footprint Image…",
        "footprint_btn": "Footprint Image",
        "pick_3d": "3D Image…",
        "delete": "Delete",
        "select_pin_numbering": "Pin Numbering Method",
        "pin_method_manual": "Manual",
        "pin_method_clockwise": "Clockwise",
        "pin_method_counterclockwise": "Counterclockwise",
        "pin_method_alphanumeric": "Alphanumeric Matrix",
    },
    "it": {
        "wizard_title": "AllegroSym – Configurazione Iniziale",
        "select_language": "Seleziona Lingua",
        "select_theme": "Seleziona Tema",
        "select_output": "Cartella di Output (ASymOut)",
        "browse": "Sfoglia…",
        "finish": "Fine",
        "dark": "Scuro",
        "light": "Chiaro",
        "english": "Inglese",
        "italian": "Italiano",
        "settings": "Impostazioni",
        "toggle_theme": "Cambia Tema",
        "help": "Aiuto",
        "output_folder": "Cartella Output",
        "language": "Lingua",
        "about": "Informazioni",
        "user_manual": "Manuale Utente",
        "release_notes": "Note di Rilascio",
        "about_title": "Informazioni su AllegroSym",
        "version": "Versione",
        "build_date": "Data di Compilazione",
        "author": "Autore",
        "close": "Chiudi",
        "save": "Salva",
        "settings_title": "Impostazioni",
        "no_manual": "Nessun Manuale Utente trovato.",
        "no_release_notes": "Nessuna Nota di Rilascio trovata.",
        "main_title": "AllegroSym",
        "wizard_output_hint": "Scegli una cartella in cui creare ASymOut",
        "new_symbol": "Nuovo Simbolo",
        "edit_symbol": "Modifica Simbolo",
        "symbol_name": "Nome Simbolo",
        "package_type": "Tipo Package",
        "add_package": "Aggiungi Package",
        "edit_package": "Modifica Package",
        "delete_package": "Elimina Package",
        "show_packages": "Mostra Package",
        "no_packages": "Nessun package ancora definito.",
        "package_name": "Nome Package",
        "package_pins": "Numero Pin",
        "pick_footprint": "Immagine Footprint…",
        "footprint_btn": "Immagine Footprint",
        "pick_3d": "Immagine 3D…",
        "delete": "Elimina",
        "select_pin_numbering": "Metodo di Numerazione Pin",
        "pin_method_manual": "Manuale",
        "pin_method_clockwise": "Orario",
        "pin_method_counterclockwise": "Antiorario",
        "pin_method_alphanumeric": "Matrice alfanumerica",
    },
}


def get_strings(lang: str) -> dict:
    return STRINGS.get(lang, STRINGS["en"])


def pkg_display_name(p: dict) -> str:
    return f"{p['name']}{p['pins']}"


def load_config():
    os.makedirs(JSONS_DIR, exist_ok=True)
    old_conf = os.path.join(os.path.dirname(__file__), "allegrosym_conf.json")
    if os.path.exists(old_conf) and not os.path.exists(CONF_FILE):
        shutil.move(old_conf, CONF_FILE)
    if os.path.exists(CONF_FILE):
        try:
            with open(CONF_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None


def save_config(cfg: dict):
    os.makedirs(JSONS_DIR, exist_ok=True)
    with open(CONF_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4, ensure_ascii=False)


def load_packages() -> list:
    os.makedirs(JSONS_DIR, exist_ok=True)
    if os.path.exists(PACKAGE_LIST_FILE):
        try:
            with open(PACKAGE_LIST_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def save_packages(packages: list):
    os.makedirs(JSONS_DIR, exist_ok=True)
    with open(PACKAGE_LIST_FILE, "w", encoding="utf-8") as f:
        json.dump(packages, f, indent=4, ensure_ascii=False)
