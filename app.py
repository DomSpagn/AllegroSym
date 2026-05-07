import flet as ft
import flet.canvas as cv

import json
import os
import shutil
import sys
from datetime import date
from pathlib import Path

APP_VERSION = "v0.1"
BUILD_DATE = "06-05-2026"
AUTHOR = " Domenico Spagnuolo"
JSONS_DIR = os.path.join(os.path.dirname(__file__), "JSONS")
CONF_FILE = os.path.join(JSONS_DIR, "asym_conf.json")
PACKAGE_LIST_FILE = os.path.join(JSONS_DIR, "package_list.json")
ICON_PATH = os.path.join(os.path.dirname(__file__), "Images", "ASym.ico")


def pkg_display_name(p: dict) -> str:
    """Canonical display name shown everywhere: 'NAMEPINS'."""
    return f"{p['name']}{p['pins']}"
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
        "pick_3d": "3D Image…",
        "delete": "Delete",
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
        "pick_3d": "Immagine 3D…",
        "delete": "Elimina",
    },
}


def load_config():
    os.makedirs(JSONS_DIR, exist_ok=True)
    # Migrate from old location if needed
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


def get_strings(lang: str) -> dict:
    return STRINGS.get(lang, STRINGS["en"])


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


# ── Wizard ───────────────────────────────────────────────────────────────────

def show_wizard(page: ft.Page, on_complete):
    s = get_strings("en")
    chosen_folder = {"path": ""}

    # Refs for live-updatable labels
    lbl_lang           = ft.Ref[ft.Text]()
    lbl_theme          = ft.Ref[ft.Text]()
    lbl_output         = ft.Ref[ft.Text]()
    output_folder_text = ft.Ref[ft.Text]()
    btn_browse         = ft.Ref[ft.ElevatedButton]()
    btn_finish         = ft.Ref[ft.ElevatedButton]()
    lang_dd_ref        = ft.Ref[ft.Dropdown]()
    theme_dd_ref       = ft.Ref[ft.Dropdown]()

    def refresh_ui():
        lbl_lang.current.value     = s["language"]
        lbl_theme.current.value    = s["select_theme"]
        lbl_output.current.value   = s["output_folder"]
        btn_browse.current.content = s["browse"]
        btn_finish.current.content = s["finish"]
        lang_dd_ref.current.label  = s["language"]
        theme_dd_ref.current.label = s["select_theme"]
        theme_dd_ref.current.options = [
            ft.dropdown.Option("dark",  s["dark"]),
            ft.dropdown.Option("light", s["light"]),
        ]
        page.update()

    def on_lang_change(e):
        nonlocal s
        s = get_strings(e.control.value)
        refresh_ui()

    def on_theme_change(e):
        page.theme_mode = ft.ThemeMode.DARK if e.control.value == "dark" else ft.ThemeMode.LIGHT
        page.update()

    file_picker = ft.FilePicker()
    page.overlay.append(file_picker)

    async def pick_folder(_):
        result = await file_picker.get_directory_path()
        if result:
            chosen_folder["path"] = os.path.join(result, "ASymOut")
            output_folder_text.current.value = chosen_folder["path"]
            page.update()

    def on_finish(e):
        lang  = lang_dd_ref.current.value  or "en"
        theme = theme_dd_ref.current.value or "dark"
        out   = chosen_folder["path"]
        if out:
            os.makedirs(out, exist_ok=True)
        cfg   = {"language": lang, "theme": theme, "output_folder": out}
        save_config(cfg)
        if file_picker in page.services:
            page.services.remove(file_picker)
        on_complete(cfg)

    page.views.clear()
    page.views.append(
        ft.View(
            route="/wizard",
            controls=[
                ft.Column(
                    [
                        ft.Image(src="AllegroSym.png", width=200, height=200),
                        ft.Divider(),
                        ft.Text(ref=lbl_lang, value=s["language"], size=14, weight=ft.FontWeight.W_600),
                        ft.Dropdown(
                            ref=lang_dd_ref,
                            label=s["language"],
                            width=300,
                            value="en",
                            options=[
                                ft.dropdown.Option("en", "English"),
                                ft.dropdown.Option("it", "Italian"),
                            ],
                            on_change=on_lang_change,
                        ),
                        ft.Text(ref=lbl_theme, value=s["select_theme"], size=14, weight=ft.FontWeight.W_600),
                        ft.Dropdown(
                            ref=theme_dd_ref,
                            label=s["select_theme"],
                            width=300,
                            value="dark",
                            options=[
                                ft.dropdown.Option("dark",  s["dark"]),
                                ft.dropdown.Option("light", s["light"]),
                            ],
                            on_change=on_theme_change,
                        ),
                        ft.Text(ref=lbl_output, value=s["output_folder"], size=14, weight=ft.FontWeight.W_600),
                        ft.ElevatedButton(
                            s["browse"],
                            ref=btn_browse,
                            icon=ft.icons.FOLDER_OPEN,
                            on_click=pick_folder,
                        ),
                        ft.Text(ref=output_folder_text, value="", size=12),
                        ft.Divider(),
                        ft.ElevatedButton(
                            s["finish"],
                            ref=btn_finish,
                            icon=ft.icons.CHECK_CIRCLE,
                            color=ft.colors.ORANGE,
                            on_click=on_finish,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=16,
                    scroll=ft.ScrollMode.AUTO,
                )
            ],
            vertical_alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
    )
    page.update()


# ── Main Window ──────────────────────────────────────────────────────────────

def show_main(page: ft.Page, cfg: dict):
    lang = cfg.get("language", "en")
    s = get_strings(lang)

    out_folder = cfg.get("output_folder", "")
    if out_folder:
        os.makedirs(out_folder, exist_ok=True)

    def apply_theme(theme_name: str):
        page.theme_mode = (
            ft.ThemeMode.DARK if theme_name == "dark" else ft.ThemeMode.LIGHT
        )
        page.update()

    apply_theme(cfg.get("theme", "dark"))

    def close_dlg(dlg):
        page.close(dlg)

    # ── About dialog ────────────────────────────────────────────────────────
    def show_about(e):
        dlg = ft.AlertDialog(
            title=ft.Row(
                [
                    ft.Image(src=ICON_PATH, width=32, height=32),
                    ft.Text(s["about_title"], size=18, weight=ft.FontWeight.BOLD),
                ],
                spacing=8,
            ),
            content=ft.Column(
                [
                    ft.Text(f"{s['version']}: {APP_VERSION}", size=14),
                    ft.Text(f"{s['build_date']}: {BUILD_DATE}", size=14),
                    ft.Text(f"{s['author']}: {AUTHOR}", size=14),
                ],
                tight=True,
                spacing=8,
            ),
            actions=[ft.TextButton(s["close"], on_click=lambda _: close_dlg(dlg))],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.open(dlg)

    # ── User Manual ─────────────────────────────────────────────────────────
    def show_user_manual(e):
        manuals_dir = os.path.join(os.path.dirname(__file__), "User Manuals")
        files = list(Path(manuals_dir).glob("*")) if os.path.isdir(manuals_dir) else []
        if files:
            os.startfile(str(files[0]))
        else:
            _info_dialog(s["user_manual"], s["no_manual"])

    # ── Release Notes ────────────────────────────────────────────────────────
    def show_release_notes(e):
        rn_dir = os.path.join(os.path.dirname(__file__), "Release Notes")
        files = list(Path(rn_dir).glob("*")) if os.path.isdir(rn_dir) else []
        if files:
            os.startfile(str(files[0]))
        else:
            _info_dialog(s["release_notes"], s["no_release_notes"])

    def _info_dialog(title: str, message: str):
        dlg = ft.AlertDialog(
            title=ft.Text(title),
            content=ft.Text(message),
            actions=[ft.TextButton(s["close"], on_click=lambda _: close_dlg(dlg))],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.open(dlg)

    # ── Language dialog ──────────────────────────────────────────────────────
    def show_language_dialog(e):
        dlg_s = {"strings": s}

        title_ref   = ft.Ref[ft.Text]()
        close_ref   = ft.Ref[ft.TextButton]()
        save_ref    = ft.Ref[ft.ElevatedButton]()
        dd_ref      = ft.Ref[ft.Dropdown]()

        close_text_ref = ft.Ref[ft.Text]()
        save_text_ref  = ft.Ref[ft.Text]()

        def on_lang_preview(ev):
            ns = get_strings(ev.control.value)
            dlg_s["strings"] = ns
            title_ref.current.value       = ns["language"]
            dd_ref.current.label          = ns["language"]
            close_text_ref.current.value  = ns["close"]
            save_text_ref.current.value   = ns["save"]
            page.update()

        lang_dd = ft.Dropdown(
            ref=dd_ref,
            label=s["language"],
            width=260,
            value=cfg.get("language", "en"),
            options=[
                ft.dropdown.Option("en", "English"),
                ft.dropdown.Option("it", "Italiano"),
            ],
            on_change=on_lang_preview,
        )

        def on_save(_):
            cfg["language"] = dd_ref.current.value
            save_config(cfg)
            page.close(dlg)
            show_main(page, cfg)

        dlg = ft.AlertDialog(
            title=ft.Text(ref=title_ref, value=s["language"]),
            content=lang_dd,
            actions=[
                ft.TextButton(ref=close_ref, content=ft.Text(ref=close_text_ref, value=s["close"]), on_click=lambda _: close_dlg(dlg)),
                ft.ElevatedButton(ref=save_ref, content=ft.Text(ref=save_text_ref, value=s["save"]), on_click=on_save),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.open(dlg)

    # ── Output Folder dialog ─────────────────────────────────────────────────
    def show_output_folder_dialog(e):
        out_text = ft.TextField(
            label=s["output_folder"],
            value=cfg.get("output_folder", ""),
            width=320,
            read_only=True,
        )
        chosen = {"path": cfg.get("output_folder", "")}

        fp = ft.FilePicker()
        page.overlay.append(fp)

        async def pick_folder(_):
            result = await fp.get_directory_path()
            if result:
                chosen["path"] = os.path.join(result, "ASymOut")
                out_text.value = chosen["path"]
                page.update()

        def on_save(_):
            cfg["output_folder"] = chosen["path"]
            if chosen["path"]:
                os.makedirs(chosen["path"], exist_ok=True)
            save_config(cfg)
            if fp in page.overlay:
                page.overlay.remove(fp)
            page.close(dlg)

        def on_close(_):
            if fp in page.overlay:
                page.overlay.remove(fp)
            page.close(dlg)

        dlg = ft.AlertDialog(
            title=ft.Text(s["output_folder"]),
            content=ft.Row(
                [out_text, ft.IconButton(icon=ft.icons.FOLDER_OPEN, on_click=pick_folder)],
                tight=True,
            ),
            actions=[
                ft.TextButton(s["close"], on_click=on_close),
                ft.ElevatedButton(s["save"], on_click=on_save),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.open(dlg)

    # ── Toggle Theme ─────────────────────────────────────────────────────────
    def toggle_theme(e):
        current = cfg.get("theme", "dark")
        new_theme = "light" if current == "dark" else "dark"
        cfg["theme"] = new_theme
        save_config(cfg)
        apply_theme(new_theme)

    # ── Package management ────────────────────────────────────────────────────
    packages = load_packages()

    new_sym_btn_ref  = ft.Ref[ft.IconButton]()
    edit_sym_btn_ref = ft.Ref[ft.IconButton]()
    save_pkg_btn_ref = ft.Ref[ft.ElevatedButton]()
    del_btn_ref       = ft.Ref[ft.ElevatedButton]()
    add_pkg_panel_title_ref    = ft.Ref[ft.Text]()
    edit_fields_container_ref  = ft.Ref[ft.Container]()
    _pkg_mode = {"mode": "add", "original_idx": -1}

    def update_symbol_buttons():
        enabled = len(packages) > 0
        new_sym_btn_ref.current.disabled  = not enabled
        edit_sym_btn_ref.current.disabled = not enabled
        new_sym_btn_ref.current.opacity   = 1.0 if enabled else 0.35
        edit_sym_btn_ref.current.opacity  = 1.0 if enabled else 0.35
        page.update()

    # ── Field widgets ─────────────────────────────────────────────────────────
    # New Symbol panel fields
    sym_name_field = ft.TextField(label=s.get("symbol_name", "Symbol Name"), width=320, autofocus=True)

    pkg_dropdown = ft.Dropdown(
        label=s.get("package_type", "Package Type"),
        width=320,
        options=[ft.dropdown.Option(pkg_display_name(p)) for p in packages],
    )

    # Add Package panel fields
    def _check_save_enabled(e=None):
        name_ok = bool(pkg_name_field.value.strip())
        pins_str = pkg_pins_field.value.strip()
        pins_ok = pins_str.isdigit() and int(pins_str) > 0
        # Show/clear error on pins field
        if pins_str == "":
            pkg_pins_field.error_text  = None
            pkg_pins_field.border_color = None
        elif not pins_ok:
            pkg_pins_field.error_text  = "Inserire un intero positivo non nullo"
            pkg_pins_field.border_color = ft.colors.RED
        else:
            pkg_pins_field.error_text  = None
            pkg_pins_field.border_color = None
        enabled = name_ok and pins_ok
        if save_pkg_btn_ref.current:
            save_pkg_btn_ref.current.disabled = not enabled
            save_pkg_btn_ref.current.opacity  = 1.0 if enabled else 0.35
        page.update()

    pkg_name_field    = ft.TextField(label=s.get("package_name", "Package Name"), width=280, on_change=_check_save_enabled)
    pkg_pins_field    = ft.TextField(label=s.get("package_pins", "Number of Pins"), width=280, on_change=_check_save_enabled)
    fp_path_text      = ft.Text(value="", size=11, italic=True)
    pkg_images        = {"footprint": ""}

    # Delete Package panel fields
    def _on_del_dd_select(e):
        enabled = bool(del_pkg_dd.value)
        if del_btn_ref.current:
            del_btn_ref.current.disabled = not enabled
            del_btn_ref.current.opacity  = 1.0 if enabled else 0.35
            page.update()

    del_pkg_dd = ft.Dropdown(label=s.get("package_name", "Package"), width=280, on_change=_on_del_dd_select)

    # Edit Package – selection dropdown (shown at top of panel in edit mode)
    def _on_edit_sel_change(e):
        dname = edit_sel_dd.value
        if not dname:
            if edit_fields_container_ref.current:
                edit_fields_container_ref.current.visible = False
            page.update()
            return
        pkg = next((p for p in packages if pkg_display_name(p) == dname), None)
        if pkg:
            _pkg_mode["original_idx"] = packages.index(pkg)
            pkg_name_field.value      = pkg["name"]
            pkg_pins_field.value      = str(pkg["pins"])
            fp_path_text.value        = os.path.basename(pkg.get("footprint", "")) if pkg.get("footprint") else ""
            pkg_images["footprint"]   = pkg.get("footprint", "")
            if edit_fields_container_ref.current:
                edit_fields_container_ref.current.visible = True
            _check_save_enabled()
            page.update()

    edit_sel_dd = ft.Dropdown(
        label=s.get("package_name", "Package"),
        width=280,
        on_change=_on_edit_sel_change,
    )
    edit_sel_container = ft.Container(
        visible=False,
        alignment=ft.alignment.center,
        content=ft.Column(
            [edit_sel_dd],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.only(bottom=4),
    )

    # ── File pickers ─────────────────────────────────────────────────────────
    fp_picker = ft.FilePicker()
    page.overlay.append(fp_picker)

    async def pick_footprint(_):
        files = await fp_picker.pick_files(
            dialog_title=s.get("pick_footprint", "Select Footprint Image"),
            allowed_extensions=["png", "jpg", "jpeg", "bmp"],
        )
        if files:
            pkg_images["footprint"] = files[0].path
            fp_path_text.value = os.path.basename(files[0].path)
            page.update()

    # ── Handlers ─────────────────────────────────────────────────────────────
    def _collapse_window():
        pass  # window resizing removed; layout driven by scroll

    def new_symbol(e):
        add_pkg_panel.visible  = False
        del_pkg_panel.visible  = False
        pkg_list_panel.visible = False
        sym_name_field.value  = ""
        pkg_dropdown.value    = None
        pkg_dropdown.options  = [ft.dropdown.Option(pkg_display_name(p)) for p in packages]
        new_sym_panel.visible = True
        page.update()

    def edit_symbol(e):
        pass  # placeholder

    def show_add_package(e):
        _pkg_mode["mode"]        = "add"
        _pkg_mode["original_idx"] = -1
        new_sym_panel.visible    = False
        del_pkg_panel.visible    = False
        pkg_list_panel.visible   = False
        edit_sel_container.visible = False
        if add_pkg_panel_title_ref.current:
            add_pkg_panel_title_ref.current.value = s.get("add_package", "Add Package")
            add_pkg_panel_title_ref.current.color = ft.colors.ORANGE
        if edit_fields_container_ref.current:
            edit_fields_container_ref.current.visible = True
        pkg_name_field.value    = ""
        pkg_pins_field.value    = ""
        fp_path_text.value      = ""
        pkg_images["footprint"] = ""
        add_pkg_panel.visible   = True
        _check_save_enabled()
        page.update()

    def show_edit_package(e):
        if not packages:
            return
        _pkg_mode["mode"]        = "edit"
        _pkg_mode["original_idx"] = -1
        new_sym_panel.visible    = False
        del_pkg_panel.visible    = False
        pkg_list_panel.visible   = False
        edit_sel_dd.options      = [ft.dropdown.Option(pkg_display_name(p)) for p in packages]
        edit_sel_dd.value        = None
        edit_sel_container.visible = True
        if add_pkg_panel_title_ref.current:
            add_pkg_panel_title_ref.current.value = s.get("edit_package", "Edit Package")
            add_pkg_panel_title_ref.current.color = ft.colors.ORANGE
        if edit_fields_container_ref.current:
            edit_fields_container_ref.current.visible = False
        pkg_name_field.value    = ""
        pkg_pins_field.value    = ""
        fp_path_text.value      = ""
        pkg_images["footprint"] = ""
        if save_pkg_btn_ref.current:
            save_pkg_btn_ref.current.disabled = True
            save_pkg_btn_ref.current.opacity  = 0.35
        add_pkg_panel.visible   = True
        page.update()

    def save_package(_):
        name     = pkg_name_field.value.strip()
        pins_str = pkg_pins_field.value.strip()
        if not name or not (pins_str.isdigit() and int(pins_str) > 0):
            return
        pins     = int(pins_str)
        mode     = _pkg_mode["mode"]
        orig_idx = _pkg_mode["original_idx"]

        # ── Duplicate check ───────────────────────────────────────────────
        for i, p in enumerate(packages):
            if p["name"] == name and p["pins"] == pins:
                if mode == "add" or (mode == "edit" and i != orig_idx):
                    pkg_name_field.error_text   = "Package con stesso nome e pin già esistente"
                    pkg_name_field.border_color = ft.colors.RED
                    page.update()
                    return
        pkg_name_field.error_text   = None
        pkg_name_field.border_color = None

        if mode == "add":
            pkg_dir = os.path.join(os.path.dirname(__file__), "Images", name)
            os.makedirs(pkg_dir, exist_ok=True)
            fp_dest = ""
            if pkg_images["footprint"]:
                ext     = os.path.splitext(pkg_images["footprint"])[1]
                fp_dest = os.path.join(pkg_dir, f"footprint{ext}")
                shutil.copy2(pkg_images["footprint"], fp_dest)
            packages.append({"name": name, "pins": pins, "footprint": fp_dest})

        else:  # edit
            orig_pkg  = packages[orig_idx]
            old_name  = orig_pkg["name"]
            old_dir   = os.path.join(os.path.dirname(__file__), "Images", old_name)
            pkg_dir   = os.path.join(os.path.dirname(__file__), "Images", name)

            # Rename folder if name changed
            if old_name != name and os.path.isdir(old_dir):
                os.rename(old_dir, pkg_dir)
            os.makedirs(pkg_dir, exist_ok=True)

            fp_dest = orig_pkg.get("footprint", "")

            # Remap path to new folder if name changed
            if old_name != name and fp_dest:
                fp_dest = fp_dest.replace(old_dir, pkg_dir)

            # Overwrite footprint if a new file was picked
            if pkg_images["footprint"] and pkg_images["footprint"] != orig_pkg.get("footprint", ""):
                ext     = os.path.splitext(pkg_images["footprint"])[1]
                fp_dest = os.path.join(pkg_dir, f"footprint{ext}")
                shutil.copy2(pkg_images["footprint"], fp_dest)

            packages[orig_idx] = {"name": name, "pins": pins, "footprint": fp_dest}

        save_packages(packages)
        add_pkg_panel.visible = False
        _collapse_window()
        update_symbol_buttons()

    def cancel_add_pkg(_):
        add_pkg_panel.visible = False
        _collapse_window()
        page.update()

    def show_delete_package(e):
        if not packages:
            return
        del_pkg_dd.options    = [ft.dropdown.Option(pkg_display_name(p)) for p in packages]
        del_pkg_dd.value      = None
        new_sym_panel.visible = False
        add_pkg_panel.visible = False
        pkg_list_panel.visible = False
        del_pkg_panel.visible = True
        if del_btn_ref.current:
            del_btn_ref.current.disabled = True
            del_btn_ref.current.opacity  = 0.35
        page.update()

    def confirm_delete(_):
        dname = del_pkg_dd.value
        if not dname:
            return
        pkg = next((p for p in packages if pkg_display_name(p) == dname), None)
        if not pkg:
            return
        folder_name = pkg["name"]
        packages[:] = [p for p in packages if pkg_display_name(p) != dname]
        save_packages(packages)
        pkg_dir = os.path.join(os.path.dirname(__file__), "Images", folder_name)
        if os.path.isdir(pkg_dir):
            shutil.rmtree(pkg_dir)
        del_pkg_panel.visible = False
        _collapse_window()
        update_symbol_buttons()

    def cancel_delete(_):
        del_pkg_panel.visible = False
        _collapse_window()
        page.update()

    def show_packages(e):
        new_sym_panel.visible  = False
        add_pkg_panel.visible  = False
        del_pkg_panel.visible  = False
        # Rebuild the list each time
        if packages:
            rows = []
            for p in packages:
                rows.append(
                    ft.Row(
                        [
                            ft.Icon(ft.icons.MEMORY, size=16),
                            ft.Text(pkg_display_name(p), size=13, weight=ft.FontWeight.W_500, expand=True),
                        ],
                        spacing=8,
                    )
                )
            pkg_list_col.controls = rows
            pkg_list_col.controls.append(
                ft.TextButton(s.get("close", "Close"), on_click=lambda _: (_collapse_window(), setattr(pkg_list_panel, 'visible', False), page.update()))
            )
        else:
            pkg_list_col.controls = [
                ft.Text(s.get("no_packages", "No packages defined yet."), italic=True),
                ft.TextButton(s.get("close", "Close"), on_click=lambda _: (_collapse_window(), setattr(pkg_list_panel, 'visible', False), page.update())),
            ]
        pkg_list_panel.visible = True
        page.update()

    # ── Panels ────────────────────────────────────────────────────────────────
    pkg_list_col = ft.Column([], spacing=6)

    pkg_list_panel = ft.Container(
        visible=False,
        padding=ft.padding.symmetric(horizontal=24, vertical=12),
        content=ft.Column(
            [
                ft.Text(s.get("show_packages", "Show Packages"), size=16, weight=ft.FontWeight.W_600, color=ft.colors.BLUE),
                ft.Divider(height=1),
                pkg_list_col,
            ],
            spacing=10,
        ),
    )

    new_sym_panel = ft.Container(
        visible=False,
        expand=True,
        alignment=ft.alignment.top_center,
        padding=ft.padding.symmetric(horizontal=24, vertical=12),
        content=ft.Column(
            [
                ft.Text(s.get("new_symbol", "New Symbol"), size=16, weight=ft.FontWeight.W_600, color=ft.colors.ORANGE),
                sym_name_field,
                pkg_dropdown,
            ],
            spacing=12,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )

    add_pkg_panel = ft.Container(
        visible=False,
        expand=True,
        padding=ft.padding.symmetric(horizontal=24, vertical=12),
        content=ft.Column(
            [
                ft.Text(
                    ref=add_pkg_panel_title_ref,
                    value=s.get("add_package", "Add Package"),
                    size=16,
                    weight=ft.FontWeight.W_600,
                    color=ft.colors.ORANGE,
                    text_align=ft.TextAlign.CENTER,
                ),
                edit_sel_container,
                ft.Container(
                    ref=edit_fields_container_ref,
                    expand=False,
                    content=ft.Column(
                        [
                            pkg_name_field,
                            pkg_pins_field,
                            ft.Column(
                                [
                                    ft.ElevatedButton("Footprint", icon=ft.icons.IMAGE, on_click=pick_footprint),
                                    fp_path_text,
                                ],
                                spacing=4,
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            ft.Row(
                                [
                                    ft.ElevatedButton(
                                        s.get("save", "Save"),
                                        ref=save_pkg_btn_ref,
                                        icon=ft.icons.SAVE,
                                        on_click=save_package,
                                        color=ft.colors.WHITE,
                                        bgcolor=ft.colors.GREEN_700,
                                        disabled=True,
                                        opacity=0.35,
                                    ),
                                    ft.ElevatedButton(
                                        s.get("close", "Cancel"),
                                        on_click=cancel_add_pkg,
                                        color=ft.colors.WHITE,
                                        bgcolor=ft.colors.GREY_600,
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.CENTER,
                                spacing=8,
                            ),
                        ],
                        spacing=12,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ),
            ],
            spacing=12,
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )

    del_pkg_panel = ft.Container(
        visible=False,
        padding=ft.padding.symmetric(horizontal=24, vertical=12),
        content=ft.Column(
            [
                ft.Text(
                    s.get("delete_package", "Delete Package"),
                    size=16,
                    weight=ft.FontWeight.W_600,
                    color=ft.colors.ORANGE,
                ),
                del_pkg_dd,
                ft.Row(
                    [
                        ft.ElevatedButton(
                            s.get("delete", "Delete"),
                            ref=del_btn_ref,
                            icon=ft.icons.DELETE,
                            color=ft.colors.RED,
                            on_click=confirm_delete,
                            disabled=True,
                            opacity=0.35,
                        ),
                        ft.TextButton(s.get("close", "Cancel"), on_click=cancel_delete),
                    ],
                    spacing=8,
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
            ],
            spacing=12,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )

    # ── Unified Command Bar ───────────────────────────────────────────────────
    top_bar = ft.Container(
        content=ft.Row(
            [
                ft.Row(
                    [
                        ft.IconButton(
                            ref=new_sym_btn_ref,
                            icon=ft.icons.ADD_BOX,
                            icon_color=ft.colors.GREEN,
                            tooltip=s.get("new_symbol", "New Symbol"),
                            on_click=new_symbol,
                            disabled=len(packages) == 0,
                            opacity=1.0 if len(packages) > 0 else 0.35,
                        ),
                        ft.IconButton(
                            ref=edit_sym_btn_ref,
                            icon=ft.icons.EDIT,
                            icon_color=ft.colors.TEAL,
                            tooltip=s.get("edit_symbol", "Edit Symbol"),
                            on_click=edit_symbol,
                            disabled=len(packages) == 0,
                            opacity=1.0 if len(packages) > 0 else 0.35,
                        ),
                        ft.VerticalDivider(width=1, thickness=1, color=ft.colors.OUTLINE),
                        ft.IconButton(
                            icon=ft.icons.MEMORY,
                            icon_color=ft.colors.BLUE,
                            tooltip=s.get("add_package", "Add Package"),
                            on_click=show_add_package,
                        ),
                        ft.IconButton(
                            icon=ft.icons.DEVELOPER_BOARD,
                            icon_color=ft.colors.TEAL,
                            tooltip=s.get("edit_package", "Edit Package"),
                            on_click=show_edit_package,
                        ),
                        ft.IconButton(
                            icon=ft.icons.MEMORY_OUTLINED,
                            icon_color=ft.colors.RED,
                            tooltip=s.get("delete_package", "Delete Package"),
                            on_click=show_delete_package,
                        ),
                        ft.IconButton(
                            icon=ft.icons.LIST_ALT,
                            icon_color=ft.colors.PURPLE,
                            tooltip=s.get("show_packages", "Show Packages"),
                            on_click=show_packages,
                        ),
                    ],
                    spacing=0,
                    height=40,
                ),
                ft.Row(
                    [
                        ft.PopupMenuButton(
                            icon=ft.icons.SETTINGS,
                            tooltip=s["settings"],
                            items=[
                                ft.PopupMenuItem(
                                    content=ft.Row([ft.Icon(ft.icons.FOLDER), ft.Text(s["output_folder"])], spacing=8),
                                    on_click=show_output_folder_dialog,
                                ),
                                ft.PopupMenuItem(
                                    content=ft.Row([ft.Icon(ft.icons.LANGUAGE), ft.Text(s["language"])], spacing=8),
                                    on_click=show_language_dialog,
                                ),
                            ],
                        ),
                        ft.IconButton(icon=ft.icons.WB_SUNNY, tooltip=s["toggle_theme"], on_click=toggle_theme),
                        ft.PopupMenuButton(
                            icon=ft.icons.HELP,
                            tooltip=s["help"],
                            items=[
                                ft.PopupMenuItem(content=ft.Row([ft.Icon(ft.icons.INFO), ft.Text(s["about"])], spacing=8), on_click=show_about),
                                ft.PopupMenuItem(content=ft.Row([ft.Icon(ft.icons.MENU_BOOK), ft.Text(s["user_manual"])], spacing=8), on_click=show_user_manual),
                                ft.PopupMenuItem(content=ft.Row([ft.Icon(ft.icons.ARTICLE), ft.Text(s["release_notes"])], spacing=8), on_click=show_release_notes),
                            ],
                        ),
                    ],
                    spacing=0,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        ),
        padding=ft.padding.symmetric(horizontal=8, vertical=2),
    )

    body = ft.Column(
        [new_sym_panel, add_pkg_panel, del_pkg_panel, pkg_list_panel],
        expand=True,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        scroll=ft.ScrollMode.AUTO,
    )

    page.views.clear()
    page.views.append(
        ft.View(
            route="/main",
            controls=[
                ft.Column(
                    [top_bar, ft.Divider(height=1), body],
                    expand=True,
                )
            ],
        )
    )
    page.update()
