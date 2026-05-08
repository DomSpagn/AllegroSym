import os

import flet as ft

from config import get_strings, save_config, SYSTEM_IMAGES_DIR


def show_wizard(page: ft.Page, on_complete):
    s = get_strings("en")
    chosen_folder = {"path": ""}

    lbl_lang           = ft.Ref[ft.Text]()
    lbl_theme          = ft.Ref[ft.Text]()
    lbl_output         = ft.Ref[ft.Text]()
    output_folder_text = ft.Ref[ft.Text]()
    btn_browse         = ft.Ref[ft.ElevatedButton]()
    btn_finish         = ft.Ref[ft.ElevatedButton]()
    lang_dd_ref        = ft.Ref[ft.Dropdown]()
    theme_dd_ref       = ft.Ref[ft.Dropdown]()

    def refresh_ui():
        lbl_lang.current.value       = s["language"]
        lbl_theme.current.value      = s["select_theme"]
        lbl_output.current.value     = s["output_folder"]
        btn_browse.current.content   = s["browse"]
        btn_finish.current.content   = s["finish"]
        lang_dd_ref.current.label    = s["language"]
        theme_dd_ref.current.label   = s["select_theme"]
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

    def on_folder_picked(e: ft.FilePickerResultEvent):
        if e.path:
            chosen_folder["path"] = os.path.join(e.path, "ASymOut")
            output_folder_text.current.value = chosen_folder["path"]
            page.update()

    file_picker = ft.FilePicker(on_result=on_folder_picked)
    page.overlay.append(file_picker)

    def pick_folder(_):
        file_picker.get_directory_path()

    def on_finish(e):
        lang  = lang_dd_ref.current.value  or "en"
        theme = theme_dd_ref.current.value or "dark"
        out   = chosen_folder["path"]
        if out:
            os.makedirs(out, exist_ok=True)
        cfg = {"language": lang, "theme": theme, "output_folder": out}
        save_config(cfg)
        if file_picker in page.overlay:
            page.overlay.remove(file_picker)
        on_complete(cfg)

    page.views.clear()
    page.views.append(
        ft.View(
            route="/wizard",
            controls=[
                ft.Column(
                    [
                        ft.Image(src=os.path.join(SYSTEM_IMAGES_DIR, "AllegroSym.png"), width=200, height=200),
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
