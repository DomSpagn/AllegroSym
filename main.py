import flet as ft
from app import ICON_PATH, load_config, show_wizard, show_main


def main(page: ft.Page):
    page.title = "AllegroSym"
    try:
        page.window.icon = ICON_PATH
    except Exception:
        pass

    _maximized_once = [False]

    def on_window_event(e):
        if e.data == "show" and not _maximized_once[0]:
            _maximized_once[0] = True
            try:
                page.window.maximized = True
                page.update()
            except Exception:
                pass

    try:
        page.window.on_event = on_window_event
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
