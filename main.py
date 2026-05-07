import flet as ft
from app import ICON_PATH, load_config, show_wizard, show_main


def main(page: ft.Page):
    page.title = "AllegroSym"
    try:
        page.window_icon = ICON_PATH
        page.window_maximized = True
    except Exception:
        pass

    cfg = load_config()

    if cfg is None:
        def on_wizard_complete(new_cfg):
            show_main(page, new_cfg)
        show_wizard(page, on_wizard_complete)
    else:
        show_main(page, cfg)


if __name__ == "__main__":
    ft.app(target=main)
