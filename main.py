import flet as ft
from app import ICON_PATH, load_config, show_wizard, show_main


# ── Entry Point ───────────────────────────────────────────────────────────────

def main(page: ft.Page):
    page.title = "AllegroSym"
    page.window.icon = ICON_PATH

    cfg = load_config()

    if cfg is None:
        page.window.width = 500
        page.window.height = 780
        page.window.min_width = 400
        page.window.min_height = 600
        def on_wizard_complete(new_cfg):
            page.window.width = 900
            page.window.height = 120
            page.window.min_width = 600
            page.window.min_height = 120
            show_main(page, new_cfg)

        show_wizard(page, on_wizard_complete)
    else:
        page.window.width = 900
        page.window.height = 120
        page.window.min_width = 600
        page.window.min_height = 120
        show_main(page, cfg)


if __name__ == "__main__":
    ft.run(main, assets_dir="Images")
