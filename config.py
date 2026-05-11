import json
import os
import shutil
import sqlite3
from datetime import date, datetime

APP_VERSION = "v0.2"
BUILD_DATE = date.today().strftime("%d-%m-%Y")
AUTHOR = " Domenico Spagnuolo"

# Global paths for system assets
SYSTEM_IMAGES_DIR = os.path.join(os.path.dirname(__file__), "SystemImages")
ICON_PATH = os.path.join(SYSTEM_IMAGES_DIR, "ASym.ico")

# These will be updated dynamically based on output_folder
JSONS_DIR = os.path.join(os.path.dirname(__file__), "JSONS")
CONF_FILE = os.path.join(JSONS_DIR, "asym_conf.json")
SYMBOL_LIST_FILE = os.path.join(JSONS_DIR, "symbol_list.json")
DB_DIR = os.path.join(os.path.dirname(__file__), "db")
PACKAGES_DB = os.path.join(DB_DIR, "packages.db")
SYMBOLS_DB = os.path.join(DB_DIR, "symbols.db")
SYMBOLS_DIR = os.path.join(os.path.dirname(__file__), "Symbols")
PACKAGES_IMAGES_DIR = os.path.join(os.path.dirname(__file__), "Packages")

def init_paths(output_folder: str):
    """Updates global paths to point inside the user-selected ASymOut folder."""
    global DB_DIR, PACKAGES_DB, SYMBOLS_DB, SYMBOLS_DIR, PACKAGES_IMAGES_DIR
    
    if not output_folder:
        return

    # ASymOut structure:
    # ASymOut/
    #   db/
    #   Symbols/
    #   Packages/ (for uploaded png images)
    # JSONS/ stays in the project directory
    
    # JSONS stays in the project directory (not in ASymOut)
    # JSONS_DIR, CONF_FILE, SYMBOL_LIST_FILE are intentionally left pointing to the project folder

    DB_DIR = os.path.join(output_folder, "db")
    PACKAGES_DB = os.path.join(DB_DIR, "packages.db")
    SYMBOLS_DB = os.path.join(DB_DIR, "symbols.db")
    
    SYMBOLS_DIR = os.path.join(output_folder, "Symbols")
    PACKAGES_IMAGES_DIR = os.path.join(output_folder, "Packages")
    
    # Ensure they exist
    os.makedirs(JSONS_DIR, exist_ok=True)
    os.makedirs(DB_DIR, exist_ok=True)
    os.makedirs(SYMBOLS_DIR, exist_ok=True)
    os.makedirs(PACKAGES_IMAGES_DIR, exist_ok=True)


def _now_str() -> str:
    return datetime.now().strftime("%d/%m/%y %H:%M:%S")


def _init_packages_db():
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR, exist_ok=True)
    with sqlite3.connect(PACKAGES_DB) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS packages (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL,
                pins        INTEGER NOT NULL,
                footprint   TEXT DEFAULT '',
                pins_data   TEXT DEFAULT '[]',
                created_at  TEXT NOT NULL DEFAULT '',
                UNIQUE(name, pins)
            )
        """)
        # Ensure created_at exists (may have been dropped in a previous migration)
        try:
            conn.execute("ALTER TABLE packages ADD COLUMN created_at TEXT NOT NULL DEFAULT ''")
        except Exception:
            pass
        # Drop updated_at if still present
        try:
            conn.execute("ALTER TABLE packages DROP COLUMN updated_at")
        except Exception:
            pass


def _migrate_packages_from_json():
    # Legacy migration removed: package_list.json is no longer used.
    pass


def _init_symbols_db():
    os.makedirs(DB_DIR, exist_ok=True)
    with sqlite3.connect(SYMBOLS_DB) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS symbols (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL UNIQUE,
                parts       INTEGER DEFAULT 1,
                package     TEXT DEFAULT '',
                folder      TEXT DEFAULT '',
                created_at  TEXT NOT NULL DEFAULT ''
            )
        """)
        # Ensure created_at exists (may have been dropped in a previous migration)
        try:
            conn.execute("ALTER TABLE symbols ADD COLUMN created_at TEXT NOT NULL DEFAULT ''")
        except Exception:
            pass
        # Drop updated_at if still present
        try:
            conn.execute("ALTER TABLE symbols DROP COLUMN updated_at")
        except Exception:
            pass


def _migrate_symbols_from_json():
    if not os.path.exists(SYMBOL_LIST_FILE):
        return
    try:
        with sqlite3.connect(SYMBOLS_DB) as conn:
            if conn.execute("SELECT COUNT(*) FROM symbols").fetchone()[0] > 0:
                return
        with open(SYMBOL_LIST_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        now = _now_str()
        with sqlite3.connect(SYMBOLS_DB) as conn:
            for sym in data:
                conn.execute(
                    "INSERT OR IGNORE INTO symbols "
                    "(name, parts, package, folder, created_at) "
                    "VALUES (?,?,?,?,?)",
                    (sym["name"], sym.get("parts", 1), sym.get("package", ""),
                     sym.get("folder", ""), now),
                )
    except Exception:
        pass

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
        "created_at_label": "Created",
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
        "delete_symbol": "Delete Symbol",
        "no_symbols": "No symbols created yet.",
        "show_symbols": "Show Symbols",

        "generate_symbol": "Generate Symbol",
        "symbol_parts": "Number of Symbol Parts",
        "pin_name": "Pin Name",
        "pin_active_low": "Active Low",
        "select_pin_numbering": "Pin Numbering Method",
        "pin_method_manual": "Manual",
        "pin_method_clockwise": "Clockwise",
        "pin_method_counterclockwise": "Counterclockwise",
        "pin_method_alphanumeric": "Alphanumeric Matrix",
        "search_package": "Search Package",
        "fp_guide_step1_pre": "Go to ",
        "fp_guide_step1_post": "  (snapeda.com).",
        "fp_guide_step2": "Search and select the device for which you want to create the symbol.",
        "fp_guide_step3": "Find the footprint image on the device page.",
        "fp_guide_step4": "Save the image in PNG format where you want and with the desired name.",
        "pin_id": "Pin ID",
        "pin_id_duplicate": "Pin ID already used by another pin",
        "pkg_duplicate": "Package with same name and pins already exists",
        "no_footprint_image": "No image available.",
        "search_package_hint": "Search package…",
        "search_symbol_hint": "Search symbol…",
        "positive_integer_error": "Please enter a positive non-zero integer",
        "reference_designator": "Reference Designator",
        "next": "Next",
        "symbol_mode": "Symbol",
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
        "created_at_label": "Creato",
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
        "delete_symbol": "Elimina Simbolo",
        "no_symbols": "Nessun simbolo ancora creato.",
        "show_symbols": "Mostra Simboli",

        "generate_symbol": "Genera Simbolo",
        "symbol_parts": "Numero Parti Simbolo",
        "pin_name": "Nome Pin",
        "pin_active_low": "Active Low",
        "select_pin_numbering": "Metodo di Numerazione Pin",
        "pin_method_manual": "Manuale",
        "pin_method_clockwise": "Orario",
        "pin_method_counterclockwise": "Antiorario",
        "pin_method_alphanumeric": "Matrice alfanumerica",
        "search_package": "Ricerca Package",
        "fp_guide_step1_pre": "Vai sul sito ",
        "fp_guide_step1_post": "  (snapeda.com).",
        "fp_guide_step2": "Cerca e seleziona il dispositivo di cui vuoi creare il simbolo.",
        "fp_guide_step3": "Individua l'immagine del footprint nella pagina del dispositivo.",
        "fp_guide_step4": "Salva l'immagine in formato PNG dove desideri e con il nome voluto.",
        "pin_id": "Pin ID",
        "pin_id_duplicate": "Pin ID già utilizzato da un altro pin",
        "pkg_duplicate": "Package con stesso nome e pin già esistente",
        "no_footprint_image": "Nessuna immagine disponibile.",
        "search_package_hint": "Cerca package…",
        "search_symbol_hint": "Cerca simbolo…",
        "positive_integer_error": "Inserire un intero positivo non nullo",
        "reference_designator": "Designatore di Riferimento",
        "next": "Avanti",
        "symbol_mode": "Simbolo",
    },
}


def get_strings(lang: str) -> dict:
    return STRINGS.get(lang, STRINGS["en"])


def pkg_display_name(p: dict) -> str:
    return f"{p['name']}{p['pins']}"


def load_config():
    # If standard location doesn't have it, look in root / legacy
    root_conf = os.path.join(os.path.dirname(__file__), "asym_conf.json")
    legacy_conf = os.path.join(os.path.dirname(__file__), "JSONS", "asym_conf.json")
    
    config_to_load = None
    if os.path.exists(CONF_FILE):
        config_to_load = CONF_FILE
    elif os.path.exists(root_conf):
        config_to_load = root_conf
    elif os.path.exists(legacy_conf):
        config_to_load = legacy_conf

    if config_to_load:
        try:
            with open(config_to_load, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                if cfg.get("output_folder"):
                    init_paths(cfg["output_folder"])
                return cfg
        except Exception:
            pass
    return None


def save_config(cfg: dict):
    if cfg.get("output_folder"):
        init_paths(cfg["output_folder"])
    os.makedirs(JSONS_DIR, exist_ok=True)
    with open(CONF_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4, ensure_ascii=False)


def load_packages() -> list:
    _init_packages_db()
    _migrate_packages_from_json()
    try:
        with sqlite3.connect(PACKAGES_DB) as conn:
            rows = conn.execute(
                "SELECT name, pins, footprint, pins_data, created_at "
                "FROM packages ORDER BY id"
            ).fetchall()
        result = []
        for name, pins, footprint, pins_data_str, created_at in rows:
            try:
                pins_data = json.loads(pins_data_str) if pins_data_str else []
            except Exception:
                pins_data = []
            result.append({
                "name": name, "pins": pins, "footprint": footprint,
                "pins_data": pins_data, "created_at": created_at,
            })
        return result
    except Exception:
        return []


def save_packages(packages: list):
    _init_packages_db()
    now = _now_str()
    try:
        with sqlite3.connect(PACKAGES_DB) as conn:
            existing = {
                (r[0], r[1]): r[2]
                for r in conn.execute(
                    "SELECT name, pins, created_at FROM packages"
                ).fetchall()
            }
            conn.execute("DELETE FROM packages")
            for p in packages:
                key = (p["name"], p["pins"])
                created_at = existing.get(key, now)
                conn.execute(
                    "INSERT INTO packages "
                    "(name, pins, footprint, pins_data, created_at) "
                    "VALUES (?,?,?,?,?)",
                    (p["name"], p["pins"], p.get("footprint", ""),
                     json.dumps(p.get("pins_data", [])), created_at),
                )
    except Exception:
        pass


def load_symbols() -> list:
    _init_symbols_db()
    _migrate_symbols_from_json()
    try:
        with sqlite3.connect(SYMBOLS_DB) as conn:
            rows = conn.execute(
                "SELECT name, parts, package, folder, created_at "
                "FROM symbols ORDER BY id"
            ).fetchall()
        return [
            {"name": name, "parts": parts, "package": package,
             "folder": folder, "created_at": created_at}
            for name, parts, package, folder, created_at in rows
        ]
    except Exception:
        return []


def save_symbols(symbols: list):
    _init_symbols_db()
    now = _now_str()
    try:
        with sqlite3.connect(SYMBOLS_DB) as conn:
            existing = {
                r[0]: r[1]
                for r in conn.execute(
                    "SELECT name, created_at FROM symbols"
                ).fetchall()
            }
            conn.execute("DELETE FROM symbols")
            for sym in symbols:
                created_at = existing.get(sym["name"], now)
                conn.execute(
                    "INSERT INTO symbols "
                    "(name, parts, package, folder, created_at) "
                    "VALUES (?,?,?,?,?)",
                    (sym["name"], sym.get("parts", 1), sym.get("package", ""),
                     sym.get("folder", ""), created_at),
                )
    except Exception:
        pass
