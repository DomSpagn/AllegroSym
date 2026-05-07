import base64
import flet as ft
import flet.canvas as cv
from flet.core.painting import Paint, PaintingStyle

import json
import os
import shutil
import sys
from collections import deque
from datetime import date
from pathlib import Path

APP_VERSION = "v0.2"
BUILD_DATE = date.today().strftime("%d-%m-%Y")
AUTHOR = " Domenico Spagnuolo"
JSONS_DIR = os.path.join(os.path.dirname(__file__), "JSONS")
CONF_FILE = os.path.join(JSONS_DIR, "asym_conf.json")
PACKAGE_LIST_FILE = os.path.join(JSONS_DIR, "package_list.json")
ICON_PATH = os.path.join(os.path.dirname(__file__), "Images", "ASym.ico")


def pkg_display_name(p: dict) -> str:
    """Canonical display name shown everywhere: 'NAMEPINS'."""
    return f"{p['name']}{p['pins']}"


def detect_orange_pins(image_path: str, min_area: int = 30) -> list:
    """Detect orange shapes (pins) in a PNG footprint image.
    Returns list of (x, y, w, h) bounding boxes in original image coordinates."""
    try:
        from PIL import Image as _PILImage
        import numpy as _np

        img = _PILImage.open(image_path).convert("RGB")
        arr = _np.array(img)
        r = arr[:, :, 0].astype(_np.int32)
        g = arr[:, :, 1].astype(_np.int32)
        b = arr[:, :, 2].astype(_np.int32)
        # Orange heuristic: R dominant, moderate G, low B
        mask = (r > 150) & (g > 50) & (g < 215) & (b < 100) & ((r - b) > 100)
        if not _np.any(mask):
            return []
        H, W = mask.shape
        CELL = 3
        grid_h = (H + CELL - 1) // CELL
        grid_w = (W + CELL - 1) // CELL
        grid = _np.zeros((grid_h, grid_w), dtype=bool)
        ys, xs = _np.where(mask)
        grid[ys // CELL, xs // CELL] = True
        visited = _np.zeros((grid_h, grid_w), dtype=bool)
        bboxes = []
        for gy in range(grid_h):
            for gx in range(grid_w):
                if grid[gy, gx] and not visited[gy, gx]:
                    queue = deque([(gy, gx)])
                    visited[gy, gx] = True
                    cells = [(gy, gx)]
                    while queue:
                        cy, cx = queue.popleft()
                        for dy in range(-1, 2):
                            for dx in range(-1, 2):
                                ny, nx = cy + dy, cx + dx
                                if 0 <= ny < grid_h and 0 <= nx < grid_w:
                                    if grid[ny, nx] and not visited[ny, nx]:
                                        visited[ny, nx] = True
                                        queue.append((ny, nx))
                                        cells.append((ny, nx))
                    min_gy = min(c[0] for c in cells) * CELL
                    max_gy = min(max(c[0] for c in cells) * CELL + CELL, H)
                    min_gx = min(c[1] for c in cells) * CELL
                    max_gx = min(max(c[1] for c in cells) * CELL + CELL, W)
                    area = (max_gy - min_gy) * (max_gx - min_gx)
                    if area >= min_area:
                        bboxes.append((min_gx, min_gy, max_gx - min_gx, max_gy - min_gy))
        return bboxes
    except Exception:
        return []
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
    save_cancel_row_ref        = ft.Ref[ft.Row]()
    add_pkg_panel_title_ref    = ft.Ref[ft.Text]()
    edit_fields_container_ref  = ft.Ref[ft.Container]()
    footprint_preview_ref      = ft.Ref[ft.Container]()
    fp_canvas_ref              = ft.Ref[cv.Canvas]()
    edit_pkg_btn_ref           = ft.Ref[ft.IconButton]()
    del_pkg_btn_ref            = ft.Ref[ft.IconButton]()
    _pkg_mode = {"mode": "add", "original_idx": -1}
    _fp_state = {"pins": [], "scale_x": 1.0, "scale_y": 1.0}
    _FP_PREVIEW_W = 900

    def update_symbol_buttons():
        enabled = len(packages) > 0
        new_sym_btn_ref.current.disabled  = not enabled
        edit_sym_btn_ref.current.disabled = not enabled
        new_sym_btn_ref.current.opacity   = 1.0 if enabled else 0.35
        edit_sym_btn_ref.current.opacity  = 1.0 if enabled else 0.35
        edit_pkg_btn_ref.current.disabled = not enabled
        edit_pkg_btn_ref.current.opacity  = 1.0 if enabled else 0.35
        del_pkg_btn_ref.current.disabled  = not enabled
        del_pkg_btn_ref.current.opacity   = 1.0 if enabled else 0.35
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
        fp_ok   = bool(pkg_images["footprint"])
        # All detected pins must have both name and number
        all_pins_ok = all(
            bool(p.get("number", "").strip())
            for p in _fp_state["pins"]
        )
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
        # Show Save/Cancel row only when everything is ready
        row_visible = name_ok and pins_ok and fp_ok and all_pins_ok
        if save_cancel_row_ref.current:
            save_cancel_row_ref.current.visible = row_visible
        page.update()

    pkg_name_field    = ft.TextField(label=s.get("package_name", "Package Name"), width=280, on_change=_check_save_enabled)
    pkg_pins_field    = ft.TextField(label=s.get("package_pins", "Number of Pins"), width=280, on_change=_check_save_enabled)
    fp_path_text      = ft.Text(value="", size=11, italic=True)
    pkg_images        = {"footprint": ""}

    # Controls shared between centered layout (no image) and 2-col layout (image)
    _save_cancel_row = ft.Row(
        [
            ft.ElevatedButton(
                s.get("save", "Save"),
                ref=save_pkg_btn_ref,
                icon=ft.icons.SAVE,
                on_click=lambda e: save_package(e),
                color=ft.colors.WHITE,
                bgcolor=ft.colors.GREEN_700,
            ),
            ft.ElevatedButton(
                s.get("close", "Cancel"),
                on_click=lambda e: cancel_add_pkg(e),
                color=ft.colors.WHITE,
                bgcolor=ft.colors.GREY_600,
            ),
        ],
        ref=save_cancel_row_ref,
        alignment=ft.MainAxisAlignment.START,
        spacing=8,
        visible=False,
        wrap=True,
    )
    _footprint_pick_btn = ft.ElevatedButton(
        s.get("footprint_btn", "Footprint Image"),
        icon=ft.icons.IMAGE,
        on_click=lambda e: pick_footprint(e),
    )

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
            # Load saved pin data
            _fp_state["pins"] = [
                {"bbox_orig": tuple(p["bbox_orig"]), "name": p.get("name", ""), "number": p.get("number", "")}
                for p in pkg.get("pins_data", [])
            ]
            if edit_fields_container_ref.current:
                edit_fields_container_ref.current.visible = True
            # Build preview if footprint exists
            if pkg.get("footprint") and os.path.isfile(pkg["footprint"]):
                _build_preview(pkg["footprint"])
            else:
                _set_centered_layout()
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

    # ── Footprint preview helpers ─────────────────────────────────────────────
    def _build_pin_shapes():
        shapes = []
        sx = _fp_state["scale_x"]
        sy = _fp_state["scale_y"]
        for pin in _fp_state["pins"]:
            x, y, w, h = pin["bbox_orig"]
            dx = x * sx
            dy = y * sy
            dw = max(w * sx, 4.0)
            dh = max(h * sy, 4.0)
            has_data = bool(pin.get("number", "").strip())
            color = ft.colors.LIGHT_BLUE_400 if has_data else ft.colors.ORANGE_400
            shapes.append(cv.Rect(
                dx, dy, dw, dh,
                paint=Paint(color=color, stroke_width=2, style=PaintingStyle.STROKE),
            ))
            if has_data:
                lbl = pin.get('number', '')
                shapes.append(cv.Text(
                    dx + dw / 2, dy + dh / 2, lbl,
                    style=ft.TextStyle(size=16, color=ft.colors.WHITE),
                    alignment=ft.alignment.center,
                    text_align=ft.TextAlign.CENTER,
                    max_width=dw,
                ))
        return shapes

    def _refresh_canvas():
        if fp_canvas_ref.current:
            fp_canvas_ref.current.shapes = _build_pin_shapes()
            fp_canvas_ref.current.update()
        _check_save_enabled()

    def _set_centered_layout():
        """Fields centered H+V – shown when no footprint image is selected."""
        if edit_fields_container_ref.current is None:
            return
        edit_fields_container_ref.current.content = ft.Container(
            expand=True,
            alignment=ft.alignment.center,
            content=ft.Column(
                [pkg_name_field, pkg_pins_field, _footprint_pick_btn, fp_path_text, _save_cancel_row],
                spacing=12,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                tight=True,
            ),
        )
        edit_fields_container_ref.current.update()

    def _set_two_col_layout():
        """2-column layout – fields left (260 px), interactive image right."""
        if edit_fields_container_ref.current is None:
            return
        edit_fields_container_ref.current.content = ft.Row(
            [
                ft.Container(
                    width=260,
                    padding=ft.padding.only(right=12),
                    alignment=ft.alignment.center,
                    content=ft.Column(
                        [pkg_name_field, pkg_pins_field, _footprint_pick_btn, fp_path_text, _save_cancel_row],
                        spacing=12,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        tight=True,
                    ),
                ),
                ft.Container(
                    expand=4,
                    alignment=ft.alignment.center,
                    content=ft.Container(
                        ref=footprint_preview_ref,
                        visible=False,
                        content=None,
                        alignment=ft.alignment.center,
                    ),
                ),
            ],
            expand=True,
            spacing=0,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        edit_fields_container_ref.current.update()

    def _build_preview(image_path: str):
        """Build the interactive footprint preview widget."""
        # Switch to 2-column layout (fields left, image right)
        _set_two_col_layout()
        try:
            from PIL import Image as _PILImage
            img_pil = _PILImage.open(image_path)
            orig_w, orig_h = img_pil.size
        except Exception:
            orig_w, orig_h = 400, 400

        scale = _FP_PREVIEW_W / max(orig_w, 1)
        preview_h = int(orig_h * scale)
        _fp_state["scale_x"] = scale
        _fp_state["scale_y"] = scale

        # Detect pins if not populated from saved data
        if not _fp_state["pins"]:
            bboxes = detect_orange_pins(image_path)
            _fp_state["pins"] = [{"bbox_orig": bb, "name": "", "number": ""} for bb in bboxes]

        # Image as base64
        try:
            with open(image_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode()
            img_ctrl = ft.Image(
                src_base64=img_b64,
                width=_FP_PREVIEW_W,
                height=preview_h,
                fit=ft.ImageFit.FILL,
            )
        except Exception:
            img_ctrl = ft.Container(width=_FP_PREVIEW_W, height=preview_h, bgcolor=ft.colors.GREY_800)

        canvas_ctrl = cv.Canvas(
            ref=fp_canvas_ref,
            shapes=_build_pin_shapes(),
            width=_FP_PREVIEW_W,
            height=preview_h,
        )
        tap_layer = ft.GestureDetector(
            on_tap_down=_handle_img_tap,
            content=canvas_ctrl,
        )
        preview_stack = ft.Stack(
            [img_ctrl, tap_layer],
            width=_FP_PREVIEW_W,
            height=preview_h,
        )
        if footprint_preview_ref.current is not None:
            footprint_preview_ref.current.content = preview_stack
            footprint_preview_ref.current.visible = True
            footprint_preview_ref.current.update()

    def _handle_img_tap(e):
        cx, cy = e.local_x, e.local_y
        sx = _fp_state["scale_x"]
        sy = _fp_state["scale_y"]
        for i, pin in enumerate(_fp_state["pins"]):
            x, y, w, h = pin["bbox_orig"]
            dx = x * sx
            dy = y * sy
            dw = max(w * sx, 8.0)
            dh = max(h * sy, 8.0)
            if dx - 3 <= cx <= dx + dw + 3 and dy - 3 <= cy <= dy + dh + 3:
                _show_pin_dialog(i)
                return

    def _show_pin_dialog(pin_idx: int):
        pin = _fp_state["pins"][pin_idx]
        number_field = ft.TextField(label="Pin ID", value=pin.get("number", ""), width=220, autofocus=True)

        def on_pin_save(_):
            new_id = number_field.value.strip()
            # Check uniqueness: no other pin (different index) can have the same Pin ID
            duplicate = any(
                i != pin_idx and _fp_state["pins"][i].get("number", "").strip() == new_id
                for i in range(len(_fp_state["pins"]))
            )
            if duplicate and new_id:
                number_field.error_text = "Pin ID già utilizzato da un altro pin"
                number_field.border_color = ft.colors.RED
                page.update()
                return
            number_field.error_text = None
            number_field.border_color = None
            _fp_state["pins"][pin_idx]["number"] = new_id
            page.close(dlg)
            _refresh_canvas()

        dlg = ft.AlertDialog(
            title=ft.Text(f"Pin {pin_idx + 1}"),
            content=ft.Column([number_field], tight=True, spacing=8),
            actions=[
                ft.TextButton(s.get("close", "Cancel"), on_click=lambda _: page.close(dlg)),
                ft.ElevatedButton(s.get("save", "Save"), on_click=on_pin_save),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.open(dlg)

    def _on_fp_result(e: ft.FilePickerResultEvent):
        if e.files:
            pkg_images["footprint"] = e.files[0].path
            fp_path_text.value = os.path.basename(e.files[0].path)
            _fp_state["pins"] = []  # reset so detect runs fresh
            _build_preview(e.files[0].path)
            _check_save_enabled()

    fp_picker = ft.FilePicker(on_result=_on_fp_result)
    page.overlay.append(fp_picker)

    def pick_footprint(_):
        fp_picker.pick_files(
            dialog_title=s.get("pick_footprint", "Select Footprint Image"),
            allowed_extensions=["png"],
        )
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
        _fp_state["pins"]       = []
        _set_centered_layout()
        if save_cancel_row_ref.current:
            save_cancel_row_ref.current.visible = False
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
        _fp_state["pins"]       = []
        _set_centered_layout()
        if save_cancel_row_ref.current:
            save_cancel_row_ref.current.visible = False
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
            pkg_dir = os.path.join(os.path.dirname(__file__), "Images", f"{name}{pins}")
            os.makedirs(pkg_dir, exist_ok=True)
            fp_dest = ""
            if pkg_images["footprint"]:
                ext     = os.path.splitext(pkg_images["footprint"])[1]
                fp_dest = os.path.join(pkg_dir, f"{name}{pins}{ext}")
                shutil.copy2(pkg_images["footprint"], fp_dest)
            pins_data = [{"bbox_orig": list(p["bbox_orig"]), "name": p["name"], "number": p["number"]} for p in _fp_state["pins"]]
            packages.append({"name": name, "pins": pins, "footprint": fp_dest, "pins_data": pins_data})

        else:  # edit
            orig_pkg  = packages[orig_idx]
            old_name  = orig_pkg["name"]
            old_pins  = orig_pkg["pins"]
            old_dir   = os.path.join(os.path.dirname(__file__), "Images", f"{old_name}{old_pins}")
            pkg_dir   = os.path.join(os.path.dirname(__file__), "Images", f"{name}{pins}")

            # Rename folder if name or pins changed
            if (old_name != name or old_pins != pins) and os.path.isdir(old_dir):
                os.rename(old_dir, pkg_dir)
            os.makedirs(pkg_dir, exist_ok=True)

            fp_dest = orig_pkg.get("footprint", "")

            # Remap path to new folder if name or pins changed
            if (old_name != name or old_pins != pins) and fp_dest:
                fp_dest = os.path.join(pkg_dir, os.path.basename(fp_dest))

            # Overwrite footprint if a new file was picked
            if pkg_images["footprint"] and pkg_images["footprint"] != orig_pkg.get("footprint", ""):
                ext     = os.path.splitext(pkg_images["footprint"])[1]
                fp_dest = os.path.join(pkg_dir, f"{name}{pins}{ext}")
                shutil.copy2(pkg_images["footprint"], fp_dest)

            packages[orig_idx] = {"name": name, "pins": pins, "footprint": fp_dest,
                                   "pins_data": [{"bbox_orig": list(p["bbox_orig"]), "name": p["name"], "number": p["number"]} for p in _fp_state["pins"]]}

        save_packages(packages)
        add_pkg_panel.visible = False
        _collapse_window()
        update_symbol_buttons()

    def cancel_add_pkg(_):
        _fp_state["pins"] = []
        pkg_images["footprint"] = ""
        _set_centered_layout()
        if save_cancel_row_ref.current:
            save_cancel_row_ref.current.visible = False
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
        folder_name = f"{pkg['name']}{pkg['pins']}"
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
        padding=ft.padding.symmetric(horizontal=12, vertical=12),
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
                    expand=True,
                    content=ft.Container(
                        expand=True,
                        alignment=ft.alignment.center,
                        content=ft.Column(
                            [pkg_name_field, pkg_pins_field, _footprint_pick_btn, fp_path_text, _save_cancel_row],
                            spacing=12,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            tight=True,
                        ),
                    ),
                ),
            ],
            spacing=8,
            expand=True,
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
                            ref=edit_pkg_btn_ref,
                            icon=ft.icons.DEVELOPER_BOARD,
                            icon_color=ft.colors.TEAL,
                            tooltip=s.get("edit_package", "Edit Package"),
                            on_click=show_edit_package,
                            disabled=len(packages) == 0,
                            opacity=1.0 if len(packages) > 0 else 0.35,
                        ),
                        ft.IconButton(
                            ref=del_pkg_btn_ref,
                            icon=ft.icons.MEMORY_OUTLINED,
                            icon_color=ft.colors.RED,
                            tooltip=s.get("delete_package", "Delete Package"),
                            on_click=show_delete_package,
                            disabled=len(packages) == 0,
                            opacity=1.0 if len(packages) > 0 else 0.35,
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
