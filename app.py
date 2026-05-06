import flet as ft
import json
import os
import sys
from datetime import date
from pathlib import Path

APP_VERSION = "v0.1"
BUILD_DATE = "06-05-2026"
AUTHOR = "Domenico Spagnuolo"
CONF_FILE = "allegrosym_conf.json"
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
    },
}


def load_config():
    if os.path.exists(CONF_FILE):
        try:
            with open(CONF_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None


def save_config(cfg: dict):
    with open(CONF_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4, ensure_ascii=False)


def get_strings(lang: str) -> dict:
    return STRINGS.get(lang, STRINGS["en"])


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
    page.services.append(file_picker)

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
                        ft.Image(src=ICON_PATH, width=64, height=64),
                        ft.Text("AllegroSym", size=28, weight=ft.FontWeight.BOLD),
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
                            on_select=on_lang_change,
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
                            on_select=on_theme_change,
                        ),
                        ft.Text(ref=lbl_output, value=s["output_folder"], size=14, weight=ft.FontWeight.W_600),
                        ft.ElevatedButton(
                            s["browse"],
                            ref=btn_browse,
                            icon=ft.Icons.FOLDER_OPEN,
                            on_click=pick_folder,
                        ),
                        ft.Text(ref=output_folder_text, value="", size=12),
                        ft.Divider(),
                        ft.ElevatedButton(
                            s["finish"],
                            ref=btn_finish,
                            icon=ft.Icons.CHECK_CIRCLE,
                            color=ft.Colors.ORANGE,
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
        page.pop_dialog()

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
        page.show_dialog(dlg)

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
        page.show_dialog(dlg)

    # ── Language dialog ──────────────────────────────────────────────────────
    def show_language_dialog(e):
        dlg_s = {"strings": s}

        title_ref   = ft.Ref[ft.Text]()
        close_ref   = ft.Ref[ft.TextButton]()
        save_ref    = ft.Ref[ft.ElevatedButton]()
        dd_ref      = ft.Ref[ft.Dropdown]()

        def on_lang_preview(ev):
            ns = get_strings(ev.control.value)
            dlg_s["strings"] = ns
            title_ref.current.value        = ns["language"]
            dd_ref.current.label           = ns["language"]
            close_ref.current.content      = ns["close"]
            save_ref.current.content       = ns["save"]
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
            on_select=on_lang_preview,
        )

        def on_save(_):
            cfg["language"] = dd_ref.current.value
            save_config(cfg)
            page.pop_dialog()
            show_main(page, cfg)

        dlg = ft.AlertDialog(
            title=ft.Text(ref=title_ref, value=s["language"]),
            content=lang_dd,
            actions=[
                ft.TextButton(ref=close_ref, content=s["close"], on_click=lambda _: close_dlg(dlg)),
                ft.ElevatedButton(ref=save_ref, content=s["save"], on_click=on_save),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.show_dialog(dlg)

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
        page.services.append(fp)

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
            if fp in page.services:
                page.services.remove(fp)
            page.pop_dialog()

        def on_close(_):
            if fp in page.services:
                page.services.remove(fp)
            page.pop_dialog()

        dlg = ft.AlertDialog(
            title=ft.Text(s["output_folder"]),
            content=ft.Row(
                [out_text, ft.IconButton(icon=ft.Icons.FOLDER_OPEN, on_click=pick_folder)],
                tight=True,
            ),
            actions=[
                ft.TextButton(s["close"], on_click=on_close),
                ft.ElevatedButton(s["save"], on_click=on_save),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.show_dialog(dlg)

    # ── Toggle Theme ─────────────────────────────────────────────────────────
    def toggle_theme(e):
        current = cfg.get("theme", "dark")
        new_theme = "light" if current == "dark" else "dark"
        cfg["theme"] = new_theme
        save_config(cfg)
        apply_theme(new_theme)

    # ── Toolbar (top-right row of icon buttons) ───────────────────────────────
    toolbar = ft.Row(
        [
            ft.PopupMenuButton(
                icon=ft.Icons.SETTINGS,
                tooltip=s["settings"],
                items=[
                    ft.PopupMenuItem(
                        content=ft.Row([ft.Icon(ft.Icons.FOLDER), ft.Text(s["output_folder"])], spacing=8),
                        on_click=show_output_folder_dialog,
                    ),
                    ft.PopupMenuItem(
                        content=ft.Row([ft.Icon(ft.Icons.LANGUAGE), ft.Text(s["language"])], spacing=8),
                        on_click=show_language_dialog,
                    ),
                ],
            ),
            ft.IconButton(
                icon=ft.Icons.WB_SUNNY,
                tooltip=s["toggle_theme"],
                on_click=toggle_theme,
            ),
            ft.PopupMenuButton(
                icon=ft.Icons.HELP,
                tooltip=s["help"],
                items=[
                    ft.PopupMenuItem(
                        content=ft.Row([ft.Icon(ft.Icons.INFO), ft.Text(s["about"])], spacing=8),
                        on_click=show_about,
                    ),
                    ft.PopupMenuItem(
                        content=ft.Row([ft.Icon(ft.Icons.MENU_BOOK), ft.Text(s["user_manual"])], spacing=8),
                        on_click=show_user_manual,
                    ),
                    ft.PopupMenuItem(
                        content=ft.Row([ft.Icon(ft.Icons.ARTICLE), ft.Text(s["release_notes"])], spacing=8),
                        on_click=show_release_notes,
                    ),
                ],
            ),
        ],
        alignment=ft.MainAxisAlignment.END,
    )

    body = ft.Column(
        [],
        expand=True,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    page.views.clear()
    page.views.append(
        ft.View(
            route="/main",
            controls=[
                ft.Column(
                    [toolbar, body],
                    expand=True,
                )
            ],
        )
    )
    page.update()
