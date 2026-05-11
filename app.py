import base64
import math
import os
import shutil
from pathlib import Path

import flet as ft
import flet.canvas as cv
from flet.core.painting import Paint, PaintingStyle

import config as _cfg_mod
from config import (
    APP_VERSION, BUILD_DATE, AUTHOR, ICON_PATH,
    SYSTEM_IMAGES_DIR,
    get_strings, save_config,
    load_packages, save_packages, pkg_display_name,
    load_symbols, save_symbols,
)
from pin_detection import detect_orange_pins
from wizard import show_wizard  # re-exported for main.py compatibility


def show_main(page: ft.Page, cfg: dict):
    lang = cfg.get("language", "en")
    s = get_strings(lang)

    out_folder = cfg.get("output_folder", "")
    if out_folder:
        os.makedirs(out_folder, exist_ok=True)

    def _build_theme(primary_color: str) -> ft.Theme:
        """Build a theme with the given primary color for dropdown hover."""
        return ft.Theme(
            color_scheme=ft.ColorScheme(primary=primary_color),
        )

    def apply_theme(theme_name: str, primary_color: str = ft.colors.BLUE):
        page.theme_mode = (
            ft.ThemeMode.DARK if theme_name == "dark" else ft.ThemeMode.LIGHT
        )
        _t = _build_theme(primary_color)
        page.theme      = _t
        page.dark_theme = _t
        page.update()

    apply_theme(cfg.get("theme", "dark"))

    def close_dlg(dlg):
        page.close(dlg)

    # -- About dialog ---------------------------------------------------------
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

    # -- User Manual ----------------------------------------------------------
    def show_user_manual(e):
        manuals_dir = os.path.join(os.path.dirname(__file__), "User Manuals")
        files = list(Path(manuals_dir).glob("*")) if os.path.isdir(manuals_dir) else []
        if files:
            os.startfile(str(files[0]))
        else:
            _info_dialog(s["user_manual"], s["no_manual"])

    # -- Release Notes --------------------------------------------------------
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

    # -- Language dialog ------------------------------------------------------
    def show_language_dialog(e):
        dlg_s = {"strings": s}
        title_ref      = ft.Ref[ft.Text]()
        close_ref      = ft.Ref[ft.TextButton]()
        save_ref       = ft.Ref[ft.ElevatedButton]()
        dd_ref         = ft.Ref[ft.Dropdown]()
        close_text_ref = ft.Ref[ft.Text]()
        save_text_ref  = ft.Ref[ft.Text]()

        def on_lang_preview(ev):
            ns = get_strings(ev.control.value)
            dlg_s["strings"] = ns
            title_ref.current.value      = ns["language"]
            dd_ref.current.label         = ns["language"]
            close_text_ref.current.value = ns["close"]
            save_text_ref.current.value  = ns["save"]
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
                ft.TextButton(
                    ref=close_ref,
                    content=ft.Text(ref=close_text_ref, value=s["close"]),
                    on_click=lambda _: close_dlg(dlg),
                ),
                ft.ElevatedButton(
                    ref=save_ref,
                    content=ft.Text(ref=save_text_ref, value=s["save"]),
                    on_click=on_save,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.open(dlg)

    # -- Output Folder dialog -------------------------------------------------
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

    # -- Toggle Theme ---------------------------------------------------------
    def toggle_theme(e):
        current = cfg.get("theme", "dark")
        new_theme = "light" if current == "dark" else "dark"
        cfg["theme"] = new_theme
        save_config(cfg)
        primary = ft.colors.ORANGE if _mode.get("current") == "package" else ft.colors.BLUE
        apply_theme(new_theme, primary_color=primary)
        # Refresh static preview if a footprint is loaded but not yet saved
        fp = pkg_images.get("footprint", "")
        if fp and add_pkg_panel.visible:
            themed = _theme_fp_path(fp)
            if themed and os.path.isfile(themed):
                _build_static_preview(themed)
        # Refresh interactive preview in New Symbol if active
        sym_fp = _sym_pkg_ref.get("footprint", "")
        if sym_fp and new_sym_panel.visible:
            themed = _theme_fp_path(sym_fp)
            if themed and os.path.isfile(themed):
                _build_interactive_preview(themed)

    # -- Package management state ----------------------------------------------
    packages = load_packages()
    symbols  = load_symbols()

    new_sym_btn_ref            = ft.Ref[ft.IconButton]()
    del_sym_btn_ref            = ft.Ref[ft.IconButton]()
    show_sym_btn_ref           = ft.Ref[ft.IconButton]()
    save_pkg_btn_ref           = ft.Ref[ft.ElevatedButton]()
    del_btn_ref                = ft.Ref[ft.ElevatedButton]()
    save_cancel_row_ref        = ft.Ref[ft.Row]()
    _bottom_bar_ref             = ft.Ref[ft.Container]()
    add_pkg_panel_title_ref    = ft.Ref[ft.Text]()
    edit_fields_container_ref  = ft.Ref[ft.Container]()  # kept for layout helpers
    footprint_preview_ref      = ft.Ref[ft.Container]()
    fp_canvas_ref              = ft.Ref[cv.Canvas]()
    del_pkg_btn_ref            = ft.Ref[ft.IconButton]()

    _pkg_mode = {"mode": "add", "original_idx": -1}
    _orig_pkg_values = {"name": "", "pins": "", "footprint": ""}  # unused, kept for safety
    _fp_state = {"pins": [], "scale_x": 1.0, "scale_y": 1.0}
    _pin_method = {"value": None, "waiting_pin1": False}
    _sym_pkg_ref = {"footprint": ""}  # footprint path active in New Symbol interactive preview
    pin_method_dd_ref               = ft.Ref[ft.Dropdown]()
    _pin_hint_ref                   = ft.Ref[ft.Text]()
    _pin_hover_tooltip_ref          = ft.Ref[ft.Container]()
    _alphanumeric_pkg_container_ref = ft.Ref[ft.Container]()
    _alphanumeric_pkg_dd_ref        = ft.Ref[ft.Dropdown]()
    _alphanumeric_pkg_type          = {"value": None}
    _FP_PREVIEW_W = 900
    new_sym_fp_preview_ref          = ft.Ref[ft.Container]()
    new_sym_right_col_ref           = ft.Ref[ft.Container]()
    _new_sym_content_ref            = ft.Ref[ft.Container]()
    _new_sym_bottom_bar_ref         = ft.Ref[ft.Container]()
    _next_sym_bar_ref               = ft.Ref[ft.Container]()
    _next_sym_btn_ref               = ft.Ref[ft.TextButton]()
    _new_sym_title_ref              = ft.Ref[ft.Text]()
    generate_sym_btn_ref            = ft.Ref[ft.ElevatedButton]()
    def update_symbol_buttons():
        pkg_ok = len(packages) > 0
        sym_ok = len(symbols) > 0
        for ref in (new_sym_btn_ref, del_pkg_btn_ref):
            ref.current.disabled = not pkg_ok
            ref.current.opacity  = 1.0 if pkg_ok else 0.35
        del_sym_btn_ref.current.disabled = not sym_ok
        del_sym_btn_ref.current.opacity  = 1.0 if sym_ok else 0.35
        page.update()

    # -- Field widgets ---------------------------------------------------------
    def _check_sym_parts(e=None):
        val = sym_parts_field.value.strip()
        if val == "":
            sym_parts_field.error_text   = None
            sym_parts_field.border_color = None
        elif not (val.isdigit() and int(val) > 0):
            sym_parts_field.error_text   = s.get("positive_integer_error", "Please enter a positive non-zero integer")
            sym_parts_field.border_color = ft.colors.RED
        else:
            sym_parts_field.error_text   = None
            sym_parts_field.border_color = None
        page.update()

    sym_name_field = ft.TextField(
        label=s.get("symbol_name", "Symbol Name"), width=320, autofocus=True,
        on_change=lambda e: _update_next_btn_state(),
    )
    sym_parts_field = ft.TextField(
        label=s.get("symbol_parts", "Number of Symbol Parts"), width=320,
        on_change=lambda e: (_check_sym_parts(e), _update_next_btn_state()),
    )
    pkg_dropdown = ft.Dropdown(
        label=s.get("package_type", "Package Type"),
        width=320,
        options=[ft.dropdown.Option(pkg_display_name(p)) for p in packages],
    )
    ref_des_dropdown = ft.Dropdown(
        label=s.get("reference_designator", "Reference Designator"),
        width=320,
        options=[
            ft.dropdown.Option("B",   "B - fan"),
            ft.dropdown.Option("BT",  "BT - battery"),
            ft.dropdown.Option("C",   "C - capacitor"),
            ft.dropdown.Option("D",   "D - diode, Schottky, Zener, TVS, bridge, miscellaneous"),
            ft.dropdown.Option("DS",  "DS - lamp, LED"),
            ft.dropdown.Option("E",   "E - antenna, arrester"),
            ft.dropdown.Option("F",   "F - fuse, fuse holder"),
            ft.dropdown.Option("J",   "J - connector"),
            ft.dropdown.Option("K",   "K - relay, mosfet relay"),
            ft.dropdown.Option("L",   "L - inductor"),
            ft.dropdown.Option("LED", "LED - display"),
            ft.dropdown.Option("LS",  "LS - buzzer"),
            ft.dropdown.Option("Q",   "Q - BJT, MOSFET, JFET, IGBT, diac, triac, module"),
            ft.dropdown.Option("R",   "R - fixed resistor, variable resistor"),
            ft.dropdown.Option("RT",  "RT - NTC, PTC"),
            ft.dropdown.Option("RV",  "RV - VDR"),
            ft.dropdown.Option("S",   "S - pushbutton, switch, thermal"),
            ft.dropdown.Option("T",   "T - transformer driver, transformer power, transformer sense"),
            ft.dropdown.Option("U",   "U - analog IC, logic IC, memory, optocoupler IC, transducer, MCU, DSP, MPU, FPGA"),
            ft.dropdown.Option("W",   "W - wire"),
            ft.dropdown.Option("X",   "X - battery holder, fuse clip"),
            ft.dropdown.Option("Y",   "Y - quartz, resonator"),
        ],
    )

    def _check_save_enabled(e=None):
        name_ok  = bool(pkg_name_field.value.strip())
        pins_str = pkg_pins_field.value.strip()
        pins_ok  = pins_str.isdigit() and int(pins_str) > 0
        fp_ok    = bool(pkg_images["footprint"])

        if pins_str == "":
            pkg_pins_field.error_text   = None
            pkg_pins_field.border_color = None
        elif not pins_ok:
            pkg_pins_field.error_text   = s.get("positive_integer_error", "Please enter a positive non-zero integer")
            pkg_pins_field.border_color = ft.colors.RED
        else:
            pkg_pins_field.error_text   = None
            pkg_pins_field.border_color = None

        row_visible = fp_ok
        if save_pkg_btn_ref.current:
            save_enabled = name_ok and pins_ok
            save_pkg_btn_ref.current.disabled = not save_enabled
            save_pkg_btn_ref.current.opacity  = 1.0 if save_enabled else 0.35
        if _bottom_bar_ref.current:
            _bottom_bar_ref.current.visible = row_visible
        page.update()

    pkg_name_field = ft.TextField(
        label=s.get("package_name", "Package Name"), width=280, on_change=_check_save_enabled
    )
    pkg_pins_field = ft.TextField(
        label=s.get("package_pins", "Number of Pins"), width=280, on_change=_check_save_enabled
    )
    fp_path_text = ft.Text(value="", size=11, italic=True)
    pkg_images   = {"footprint": "", "footprint_is_temp": False}

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
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=8,
        wrap=True,
    )
    _footprint_pick_btn = ft.ElevatedButton(
        s.get("footprint_btn", "Footprint Image"),
        icon=ft.icons.IMAGE,
        on_click=lambda e: pick_footprint(e),
    )

    # -- Delete Package dropdown -----------------------------------------------
    def _on_del_dd_select(e):
        enabled = bool(del_pkg_dd.value)
        if del_btn_ref.current:
            del_btn_ref.current.disabled = not enabled
            del_btn_ref.current.opacity  = 1.0 if enabled else 0.35
            page.update()

    del_pkg_dd = ft.Dropdown(
        label=s.get("package_name", "Package"), width=280, on_change=_on_del_dd_select,
        focused_border_color=ft.colors.ORANGE,
        focused_color=ft.colors.ORANGE,
    )

    # -- Canvas helpers --------------------------------------------------------
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
            has_id   = bool(pin.get("number", "").strip())
            has_name = bool(pin.get("name", "").strip())
            if has_id and has_name:
                color = ft.colors.LIGHT_BLUE_400
            elif has_id:
                color = ft.colors.RED_400
            else:
                color = ft.colors.ORANGE_400
            shapes.append(cv.Rect(
                dx, dy, dw, dh,
                paint=Paint(color=color, stroke_width=2, style=PaintingStyle.STROKE),
            ))
            if has_id:
                lbl = pin.get("number", "")
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
        _check_generate_sym_enabled()

    def _check_generate_sym_enabled():
        if generate_sym_btn_ref.current is None:
            return
        all_populated = bool(_fp_state["pins"]) and all(
            p.get("number", "").strip() and p.get("name", "").strip() and p.get("part_number", "").strip()
            for p in _fp_state["pins"]
        )
        generate_sym_btn_ref.current.disabled = not all_populated
        generate_sym_btn_ref.current.opacity  = 1.0 if all_populated else 0.35
        if generate_sym_btn_ref.current.page:
            generate_sym_btn_ref.current.update()
        # Nascondi l'hint quando il pulsante Generate Symbol è abilitato
        if all_populated and _pin_hint_ref.current:
            _pin_hint_ref.current.visible = False
            _pin_hint_ref.current.update()

    # -- Layout helpers --------------------------------------------------------
    def _set_centered_layout():
        if edit_fields_container_ref.current is None:
            return
        edit_fields_container_ref.current.content = ft.Container(
            expand=True,
            alignment=ft.alignment.center,
            content=ft.Column(
                [pkg_name_field, pkg_pins_field, _footprint_pick_btn, fp_path_text],
                spacing=12,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                tight=True,
            ),
        )
        edit_fields_container_ref.current.update()

    def _set_two_col_layout():
        """2-column layout: fields left, image right (scrollable). Save/Cancel in bottom bar."""
        if edit_fields_container_ref.current is None:
            return
        edit_fields_container_ref.current.content = ft.Row(
            [
                ft.Container(
                    width=260,
                    padding=ft.padding.only(right=12),
                    alignment=ft.alignment.center,
                    content=ft.Column(
                        [pkg_name_field, pkg_pins_field, _footprint_pick_btn, fp_path_text],
                        spacing=12,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        tight=True,
                    ),
                ),
                ft.Container(
                    expand=4,
                    alignment=ft.alignment.center,
                    content=ft.Column(
                        [
                            ft.Container(
                                ref=footprint_preview_ref,
                                visible=False,
                                content=None,
                                alignment=ft.alignment.center,
                                expand=True,
                            )
                        ],
                        expand=True,
                        scroll=ft.ScrollMode.AUTO,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ),
            ],
            expand=True,
            spacing=0,
            vertical_alignment=ft.CrossAxisAlignment.STRETCH,
        )
        edit_fields_container_ref.current.update()

    def _set_new_sym_centered_layout():
        if _new_sym_content_ref.current is None:
            return
        _new_sym_content_ref.current.content = ft.Container(
            expand=True,
            alignment=ft.alignment.center,
            content=ft.Column(
                [sym_name_field, sym_parts_field, pkg_dropdown, ref_des_dropdown],
                spacing=12,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                tight=True,
            ),
        )
        _new_sym_content_ref.current.update()

    def _set_new_sym_two_col_layout():
        if _new_sym_content_ref.current is None:
            return
        _new_sym_content_ref.current.content = ft.Row(
            [
                ft.Container(
                    expand=1,
                    padding=ft.padding.only(right=12),
                    alignment=ft.alignment.center,
                    content=ft.Column(
                        [sym_name_field, sym_parts_field, pkg_dropdown, ref_des_dropdown],
                        spacing=12,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        tight=True,
                    ),
                ),
                ft.Container(
                    ref=new_sym_right_col_ref,
                    expand=4,
                    alignment=ft.alignment.top_center,
                    content=ft.Container(
                        ref=new_sym_fp_preview_ref,
                        alignment=ft.alignment.center,
                        content=None,
                    ),
                ),
            ],
            expand=True,
            spacing=0,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )
        _new_sym_content_ref.current.update()

    # -- Preview builder -------------------------------------------------------
    def _on_pin_method_change(e):
        method = e.control.value
        _pin_method["value"] = method
        _pin_method["waiting_pin1"] = False
        _alphanumeric_pkg_type["value"] = None
        if _alphanumeric_pkg_dd_ref.current:
            _alphanumeric_pkg_dd_ref.current.value = None
        # Reset all pin IDs and names
        for pin in _fp_state["pins"]:
            pin["number"] = ""
            pin["name"]   = ""
        _refresh_canvas()
        if _alphanumeric_pkg_container_ref.current:
            _alphanumeric_pkg_container_ref.current.visible = (method == "alphanumeric")
        if method in ("clockwise", "counterclockwise"):
            _pin_method["waiting_pin1"] = True
            hint = (
                "Clicca sul Pin 1 per avviare la numerazione automatica"
                if lang == "it" else
                "Click on Pin 1 to start auto-numbering"
            )
            if _pin_hint_ref.current:
                _pin_hint_ref.current.value = hint
                _pin_hint_ref.current.visible = True
                _pin_hint_ref.current.update()
        elif method == "manual":
            hint = (
                "Clicca su un pin per assegnargli le sue proprietà"
                if lang == "it" else
                "Click on a pin to assign it its properties"
            )
            if _pin_hint_ref.current:
                _pin_hint_ref.current.value = hint
                _pin_hint_ref.current.visible = True
                _pin_hint_ref.current.update()
        else:
            if _pin_hint_ref.current:
                _pin_hint_ref.current.visible = False
                _pin_hint_ref.current.update()
        page.update()

    def _on_alphanumeric_pkg_change(e):
        _alphanumeric_pkg_type["value"] = e.control.value
        if e.control.value:
            _pin_method["waiting_pin1"] = True
            hint = (
                "Clicca sul Pin 1 per avviare la numerazione automatica"
                if lang == "it" else
                "Click on Pin 1 to start auto-numbering"
            )
            if _pin_hint_ref.current:
                _pin_hint_ref.current.value = hint
                _pin_hint_ref.current.visible = True
                _pin_hint_ref.current.update()
        else:
            _pin_method["waiting_pin1"] = False
            if _pin_hint_ref.current:
                _pin_hint_ref.current.visible = False
                _pin_hint_ref.current.update()
        page.update()

    def _build_interactive_preview(image_path: str):
        """Build interactive image (pin numbering) for the New Symbol view."""
        _pin_method["value"] = None
        _pin_method["waiting_pin1"] = False

        try:
            from PIL import Image as _PILImage
            orig_w, orig_h = _PILImage.open(image_path).size
        except Exception:
            orig_w, orig_h = 400, 400

        _interactive_w = int(_FP_PREVIEW_W * 0.75)
        scale = _interactive_w / max(orig_w, 1)
        preview_h = int(orig_h * scale)
        _fp_state["scale_x"] = scale
        _fp_state["scale_y"] = scale

        if not _fp_state["pins"]:
            _fp_state["pins"] = [
                {"bbox_orig": bb, "name": "", "number": ""}
                for bb in detect_orange_pins(image_path)
            ]

        try:
            with open(image_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode()
            img_ctrl = ft.Image(
                src_base64=img_b64,
                width=_interactive_w,
                height=preview_h,
                fit=ft.ImageFit.FILL,
            )
        except Exception:
            img_ctrl = ft.Container(
                width=_interactive_w, height=preview_h, bgcolor=ft.colors.GREY_800
            )

        canvas_ctrl = cv.Canvas(
            ref=fp_canvas_ref,
            shapes=_build_pin_shapes(),
            width=_interactive_w,
            height=preview_h,
        )
        tap_layer = ft.GestureDetector(
            on_tap_down=_handle_img_tap,
            on_hover=_handle_img_hover,
            content=canvas_ctrl,
        )
        tooltip_overlay = ft.Container(
            ref=_pin_hover_tooltip_ref,
            visible=False,
            left=0,
            top=0,
            bgcolor=ft.colors.with_opacity(0.82, ft.colors.WHITE),
            border_radius=6,
            padding=ft.padding.symmetric(horizontal=10, vertical=6),
            content=ft.Column(controls=[], spacing=2,
                              horizontal_alignment=ft.CrossAxisAlignment.START),
        )
        preview_stack = ft.Stack(
            [img_ctrl, tap_layer, tooltip_overlay], width=_interactive_w, height=preview_h
        )

        pin_method_dd = ft.Dropdown(
            ref=pin_method_dd_ref,
            label=s.get("select_pin_numbering", "Pin Numbering Method"),
            width=360,
            options=[
                ft.dropdown.Option("manual",           s.get("pin_method_manual",           "Manual")),
                ft.dropdown.Option("clockwise",        s.get("pin_method_clockwise",        "Clockwise")),
                ft.dropdown.Option("counterclockwise", s.get("pin_method_counterclockwise", "Counterclockwise")),
                ft.dropdown.Option("alphanumeric",     s.get("pin_method_alphanumeric",     "Alphanumeric Matrix")),
            ],
            on_change=_on_pin_method_change,
        )
        hint_text = ft.Text(
            ref=_pin_hint_ref,
            value="",
            size=13,
            italic=True,
            color=ft.colors.RED,
            text_align=ft.TextAlign.CENTER,
            visible=False,
        )
        alphanumeric_pkg_container = ft.Container(
            ref=_alphanumeric_pkg_container_ref,
            visible=False,
            alignment=ft.alignment.center,
            content=ft.Dropdown(
                ref=_alphanumeric_pkg_dd_ref,
                label=s.get("package_type", "Package Type"),
                width=360,
                options=[
                    ft.dropdown.Option(t, t)
                    for t in ("BGA", "LGA", "PGA", "CSP", "VGA", "LFBGA", "SiP")
                ],
                on_change=_on_alphanumeric_pkg_change,
            ),
        )

        preview_column = ft.Column(
            [pin_method_dd, alphanumeric_pkg_container, hint_text, preview_stack],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
        )

        if new_sym_fp_preview_ref.current is not None:
            new_sym_fp_preview_ref.current.content = preview_column
            new_sym_fp_preview_ref.current.update()

    def _build_static_preview(image_path: str):
        """Build a non-interactive static image preview for Add/Edit Package."""
        _set_two_col_layout()

        try:
            from PIL import Image as _PILImage
            orig_w, orig_h = _PILImage.open(image_path).size
        except Exception:
            orig_w, orig_h = 400, 400

        _static_w = int(_FP_PREVIEW_W * 0.75)
        scale = _static_w / max(orig_w, 1)
        preview_h = int(orig_h * scale)
        _fp_state["scale_x"] = scale
        _fp_state["scale_y"] = scale

        if not _fp_state["pins"]:
            _fp_state["pins"] = [
                {"bbox_orig": bb, "name": "", "number": ""}
                for bb in detect_orange_pins(image_path)
            ]

        try:
            with open(image_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode()
            img_ctrl = ft.Image(
                src_base64=img_b64,
                width=_static_w,
                height=preview_h,
                fit=ft.ImageFit.FILL,
            )
        except Exception:
            img_ctrl = ft.Container(
                width=_static_w, height=preview_h, bgcolor=ft.colors.GREY_800
            )

        if footprint_preview_ref.current is not None:
            footprint_preview_ref.current.content = img_ctrl
            footprint_preview_ref.current.visible = True
            footprint_preview_ref.current.update()

    # -- Pin auto-numbering ----------------------------------------------------
    def _auto_number_pins(pin1_idx: int, direction: str):
        pins = _fp_state["pins"]
        n = len(pins)
        if n == 0:
            return
        centers = [(p["bbox_orig"][0] + p["bbox_orig"][2] / 2.0,
                    p["bbox_orig"][1] + p["bbox_orig"][3] / 2.0) for p in pins]
        cen_x = sum(c[0] for c in centers) / n
        cen_y = sum(c[1] for c in centers) / n
        p1x, p1y = centers[pin1_idx]
        base_angle = math.atan2(p1y - cen_y, p1x - cen_x)

        def _rel_angle(i):
            px, py = centers[i]
            a = math.atan2(py - cen_y, px - cen_x) - base_angle
            return a % (2 * math.pi)

        indices = sorted(range(n), key=_rel_angle)
        if direction == "counterclockwise":
            rest = indices[1:]
            rest.reverse()
            indices = [indices[0]] + rest
        for num, idx in enumerate(indices, start=1):
            pins[idx]["number"] = str(num)
        _pin_method["waiting_pin1"] = False
        if _pin_hint_ref.current:
            _pin_hint_ref.current.value = (
                "Clicca su un pin per assegnargli le sue proprietà"
                if lang == "it" else
                "Click on a pin to assign it its properties"
            )
            _pin_hint_ref.current.visible = True
            _pin_hint_ref.current.update()
        _refresh_canvas()

    def _auto_number_alphanumeric():
        pins = _fp_state["pins"]
        n = len(pins)
        if n == 0:
            return
        centers = [(p["bbox_orig"][0] + p["bbox_orig"][2] / 2.0,
                    p["bbox_orig"][1] + p["bbox_orig"][3] / 2.0) for p in pins]
        sorted_by_y = sorted(range(n), key=lambda i: centers[i][1])
        y_vals = [centers[i][1] for i in sorted_by_y]
        y_range = (y_vals[-1] - y_vals[0]) if n > 1 else 1
        row_threshold = max(y_range / max(int(n ** 0.5), 1) * 0.6, 5)
        rows = []
        current_row = [sorted_by_y[0]]
        for idx in sorted_by_y[1:]:
            if abs(centers[idx][1] - centers[current_row[0]][1]) <= row_threshold:
                current_row.append(idx)
            else:
                rows.append(sorted(current_row, key=lambda i: centers[i][0]))
                current_row = [idx]
        rows.append(sorted(current_row, key=lambda i: centers[i][0]))
        for row_i, row_pins in enumerate(rows):
            row_letter = chr(ord("A") + row_i)
            for col_i, pin_idx in enumerate(row_pins):
                pins[pin_idx]["number"] = f"{row_letter}{col_i + 1}"
        _pin_method["waiting_pin1"] = False
        if _pin_hint_ref.current:
            _pin_hint_ref.current.value = (
                "Clicca su un pin per assegnargli le sue proprietà"
                if lang == "it" else
                "Click on a pin to assign it its properties"
            )
            _pin_hint_ref.current.visible = True
            _pin_hint_ref.current.update()
        _refresh_canvas()

    # -- Image hover/tap handlers ------------------------------------------------
    def _handle_img_hover(e):
        cx, cy = e.local_x, e.local_y
        sx = _fp_state["scale_x"]
        sy = _fp_state["scale_y"]
        for pin in _fp_state["pins"]:
            x, y, w, h = pin["bbox_orig"]
            dx = x * sx
            dy = y * sy
            dw = max(w * sx, 8.0)
            dh = max(h * sy, 8.0)
            if dx - 3 <= cx <= dx + dw + 3 and dy - 3 <= cy <= dy + dh + 3:
                pin_id    = pin.get("number", "").strip()
                pin_name  = pin.get("name", "").strip()
                negated   = pin.get("negated", False)
                active_low_val = s.get("true_val", "True") if negated else s.get("false_val", "False")
                active_low_color = ft.colors.LIGHT_BLUE_400 if negated else ft.colors.ORANGE
                part_num  = pin.get("part_number", "1")
                has_id      = bool(pin_id)
                has_name    = bool(pin_name)
                has_part    = bool(str(part_num).strip())
                all_filled  = has_id and has_name and has_part
                if all_filled and _pin_hover_tooltip_ref.current:
                    lbl_pin_name   = s.get("pin_name_col", "Pin Name")
                    lbl_active_low = s.get("active_low_col", "Active Low")
                    tip = _pin_hover_tooltip_ref.current
                    tip.content.controls = [
                        ft.Text(f"Pin ID: {pin_id}", size=12, italic=True, weight=ft.FontWeight.BOLD, color=ft.colors.BLACK),
                        ft.Text(f"{lbl_pin_name}: {pin_name}", size=12, italic=True, weight=ft.FontWeight.BOLD, color=ft.colors.BLACK),
                        ft.Row([
                            ft.Text(f"{lbl_active_low}: ", size=12, italic=True, weight=ft.FontWeight.BOLD, color=ft.colors.BLACK),
                            ft.Text(active_low_val, size=12, italic=True, weight=ft.FontWeight.BOLD, color=active_low_color),
                        ], spacing=0, tight=True),
                        ft.Text(f"Part #: {part_num}", size=12, italic=True, weight=ft.FontWeight.BOLD, color=ft.colors.BLACK),
                    ]
                    estimated_h = 4 * 20 + 12
                    tip.left = dx
                    tip.top  = max(0, dy - estimated_h - 4)
                    tip.visible = True
                    tip.update()
                elif _pin_hover_tooltip_ref.current and _pin_hover_tooltip_ref.current.visible:
                    _pin_hover_tooltip_ref.current.visible = False
                    _pin_hover_tooltip_ref.current.update()
                return
        if _pin_hover_tooltip_ref.current and _pin_hover_tooltip_ref.current.visible:
            _pin_hover_tooltip_ref.current.visible = False
            _pin_hover_tooltip_ref.current.update()

    def _handle_img_tap(e):
        if not _pin_method["value"]:
            return
        cx, cy = e.local_x, e.local_y
        sx = _fp_state["scale_x"]
        sy = _fp_state["scale_y"]
        method = _pin_method["value"]
        for i, pin in enumerate(_fp_state["pins"]):
            x, y, w, h = pin["bbox_orig"]
            dx = x * sx
            dy = y * sy
            dw = max(w * sx, 8.0)
            dh = max(h * sy, 8.0)
            if dx - 3 <= cx <= dx + dw + 3 and dy - 3 <= cy <= dy + dh + 3:
                if method in ("clockwise", "counterclockwise") and _pin_method["waiting_pin1"]:
                    _auto_number_pins(i, method)
                elif method == "alphanumeric" and _pin_method["waiting_pin1"]:
                    _auto_number_alphanumeric()
                else:
                    _show_pin_dialog(i)
                return

    def _show_pin_dialog(pin_idx: int):
        pin = _fp_state["pins"][pin_idx]
        has_id = bool(pin.get("number", "").strip())
        number_field = ft.TextField(
            label=s.get("pin_id", "Pin ID"), value=pin.get("number", ""), width=220, autofocus=not has_id
        )
        name_field = ft.TextField(
            label=s.get("pin_name", "Pin Name"), value=pin.get("name", ""), width=220, autofocus=has_id
        )
        # Calcola il numero di parti dal campo sym_parts_field
        _parts_str = sym_parts_field.value.strip()
        _num_parts = int(_parts_str) if _parts_str.isdigit() and int(_parts_str) > 0 else 1
        _saved_part = str(pin.get("part_number", "1"))
        part_dd = ft.Dropdown(
            label="Part #",
            width=220,
            value=_saved_part if _saved_part and int(_saved_part) <= _num_parts else "1",
            options=[ft.dropdown.Option(str(i)) for i in range(1, _num_parts + 1)],
        )
        neg_checkbox = ft.Checkbox(
            label=s.get("pin_active_low", "Active Low"),
            value=pin.get("negated", False),
        )
        save_btn_ref = ft.Ref[ft.ElevatedButton]()

        def _check_pin_save_enabled(e=None):
            enabled = (bool(number_field.value.strip())
                       and bool(name_field.value.strip())
                       and bool(part_dd.value))
            if save_btn_ref.current:
                save_btn_ref.current.disabled = not enabled
                save_btn_ref.current.opacity  = 1.0 if enabled else 0.35
                save_btn_ref.current.update()

        def _on_field_submit(e):
            """Trigger Save when Enter is pressed and Save is enabled."""
            if (bool(number_field.value.strip())
                    and bool(name_field.value.strip())
                    and bool(part_dd.value)):
                on_pin_save(e)

        number_field.on_change = _check_pin_save_enabled
        name_field.on_change   = _check_pin_save_enabled
        part_dd.on_change      = _check_pin_save_enabled
        number_field.on_submit = _on_field_submit
        name_field.on_submit   = _on_field_submit

        def on_pin_save(_):
            new_id = number_field.value.strip()
            duplicate = any(
                i != pin_idx and _fp_state["pins"][i].get("number", "").strip() == new_id
                for i in range(len(_fp_state["pins"]))
            )
            if duplicate and new_id:
                number_field.error_text   = s.get("pin_id_duplicate", "Pin ID already used by another pin")
                number_field.border_color = ft.colors.RED
                page.update()
                return
            number_field.error_text   = None
            number_field.border_color = None
            _fp_state["pins"][pin_idx]["number"]      = new_id
            _fp_state["pins"][pin_idx]["name"]        = name_field.value.strip()
            _fp_state["pins"][pin_idx]["negated"]     = neg_checkbox.value
            _fp_state["pins"][pin_idx]["part_number"] = part_dd.value or "1"
            page.close(dlg)
            _refresh_canvas()

        _initial_enabled = (bool(pin.get("number", "").strip())
                            and bool(pin.get("name", "").strip())
                            and bool(pin.get("part_number", "").strip()))
        dlg = ft.AlertDialog(
            title=ft.Text(f"Pin {pin_idx + 1}"),
            content=ft.Column(
                [number_field, name_field, part_dd, neg_checkbox],
                tight=True,
                spacing=8,
            ),
            actions=[
                ft.TextButton(s.get("close", "Cancel"), on_click=lambda _: page.close(dlg)),
                ft.ElevatedButton(
                    s.get("save", "Save"),
                    ref=save_btn_ref,
                    on_click=on_pin_save,
                    disabled=not _initial_enabled,
                    opacity=1.0 if _initial_enabled else 0.35,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.open(dlg)

    # -- Footprint file picker -------------------------------------------------
    def _on_fp_result(e: ft.FilePickerResultEvent):
        if e.files:
            src = e.files[0].path
            dark_path, _light_path = _make_themed_images(src)
            pkg_images["footprint"] = dark_path
            pkg_images["footprint_is_temp"] = True
            fp_path_text.value = os.path.basename(dark_path)
            _fp_state["pins"] = []
            _build_static_preview(_theme_fp_path(dark_path))
            _check_save_enabled()

    def _make_themed_images(src_path: str):
        """Copy src to PACKAGES_IMAGES_DIR/stem_d.png; generate stem_l.png with inverted colors.
        Returns (dark_path, light_path).
        """
        from PIL import Image as _PILImg
        import numpy as np
        base_name = os.path.splitext(os.path.basename(src_path))[0]
        # Strip existing _d/_l suffix if re-loading
        for sfx in ("_d", "_l"):
            if base_name.endswith(sfx):
                base_name = base_name[:-len(sfx)]
                break
        dark_path  = os.path.join(_cfg_mod.PACKAGES_IMAGES_DIR, base_name + "_d.png")
        light_path = os.path.join(_cfg_mod.PACKAGES_IMAGES_DIR, base_name + "_l.png")
        img = _PILImg.open(src_path).convert("RGBA")
        # Dark copy
        img.save(dark_path)
        # Light copy: invert RGB, keep alpha
        arr = np.array(img, dtype=np.uint8)
        arr[..., :3] = 255 - arr[..., :3]
        _PILImg.fromarray(arr).save(light_path)
        return dark_path, light_path

    def _theme_fp_path(fp: str) -> str:
        """Return _d or _l variant of a footprint path based on current theme."""
        if not fp:
            return fp
        stem, ext = os.path.splitext(fp)
        if stem.endswith("_d") or stem.endswith("_l"):
            base = stem[:-2]
            suffix = "_l" if page.theme_mode == ft.ThemeMode.LIGHT else "_d"
            candidate = base + suffix + ext
            if os.path.isfile(candidate):
                return candidate
        return fp

    fp_picker = ft.FilePicker(on_result=_on_fp_result)
    page.overlay.append(fp_picker)

    def pick_footprint(_):
        fp_picker.pick_files(
            dialog_title=s.get("pick_footprint", "Select Footprint Image"),
            allowed_extensions=["png"],
        )
        page.update()

    # -- State reset helper ----------------------------------------------------
    def _reset_pkg_state():
        # Remove temp _d/_l images if footprint was loaded but never saved
        _fp = pkg_images.get("footprint", "")
        if _fp and pkg_images.get("footprint_is_temp") and os.path.isfile(_fp) and _fp.endswith("_d.png"):
            os.remove(_fp)
            _lp = _fp[:-6] + "_l.png"
            if os.path.isfile(_lp):
                os.remove(_lp)
        pkg_name_field.value    = ""
        pkg_pins_field.value    = ""
        fp_path_text.value      = ""
        pkg_images["footprint"] = ""
        pkg_images["footprint_is_temp"] = False
        _fp_state["pins"]       = []
        _pin_method["value"]    = None
        _pin_method["waiting_pin1"] = False
        _alphanumeric_pkg_type["value"] = None

    # -- Package CRUD handlers -------------------------------------------------
    def _update_next_btn_state():
        """Enable 'Next' only when all fields are populated."""
        parts_str = sym_parts_field.value.strip()
        all_ok = (
            bool(sym_name_field.value.strip()) and
            (parts_str.isdigit() and int(parts_str) > 0) and
            bool(pkg_dropdown.value) and
            bool(ref_des_dropdown.value)
        )
        if _next_sym_btn_ref.current:
            _next_sym_btn_ref.current.disabled = not all_ok
            _next_sym_btn_ref.current.opacity  = 1.0 if all_ok else 0.35
        page.update()

    def _on_next_click(e):
        """Transition to interactive preview after all fields are confirmed."""
        dname = pkg_dropdown.value
        if not dname:
            return
        pkg = next((p for p in packages if pkg_display_name(p) == dname), None)
        if _next_sym_bar_ref.current:
            _next_sym_bar_ref.current.visible = False
        if pkg and pkg.get("footprint") and os.path.isfile(pkg["footprint"]):
            _fp_state["pins"] = [
                {"bbox_orig": tuple(p["bbox_orig"]), "name": p.get("name", ""), "number": p.get("number", "")}
                for p in pkg.get("pins_data", [])
            ]
            _sym_pkg_ref["footprint"] = pkg["footprint"]
            _set_new_sym_two_col_layout()
            _build_interactive_preview(_theme_fp_path(pkg["footprint"]))
        if _new_sym_bottom_bar_ref.current:
            _new_sym_bottom_bar_ref.current.visible = True
        page.update()

    def _on_pkg_type_change(e):
        """Called when the user selects a package in the New Symbol dropdown."""
        _update_next_btn_state()

    def _on_ref_des_change(e):
        """Called when the user selects a reference designator."""
        _update_next_btn_state()

    def new_symbol(e):
        add_pkg_panel.visible   = False
        del_pkg_panel.visible   = False
        del_sym_panel.visible   = False
        sym_list_panel.visible  = False
        pkg_list_panel.visible  = False
        search_pkg_panel.visible = False
        sym_name_field.value    = ""
        sym_parts_field.value   = ""
        sym_parts_field.error_text   = None
        sym_parts_field.border_color = None
        pkg_dropdown.value      = None
        pkg_dropdown.options    = [ft.dropdown.Option(pkg_display_name(p)) for p in packages]
        ref_des_dropdown.value  = None
        _reset_pkg_state()
        _set_new_sym_centered_layout()
        if _next_sym_btn_ref.current:
            _next_sym_btn_ref.current.disabled = True
            _next_sym_btn_ref.current.opacity  = 0.35
        if _next_sym_bar_ref.current:
            _next_sym_bar_ref.current.visible = True
        if _new_sym_bottom_bar_ref.current:
            _new_sym_bottom_bar_ref.current.visible = False
        new_sym_panel.visible   = True
        page.update()

    def _generate_symbol(e):
        """Called by the Generate Symbol button  saves the symbol and creates its folder."""
        import sqlite3
        name      = sym_name_field.value.strip()
        parts_str = sym_parts_field.value.strip()
        if not name:
            return
        num_parts    = int(parts_str) if parts_str.isdigit() and int(parts_str) > 0 else 1
        package_type = pkg_dropdown.value or ""
        ref_des      = ref_des_dropdown.value or ""
        pins         = _fp_state.get("pins", [])

        # Ricava il numero di pin dal package selezionato
        pkg_pin_count = 0
        if package_type:
            matched_pkg = next(
                (p for p in packages if pkg_display_name(p) == package_type), None
            )
            if matched_pkg:
                pkg_pin_count = matched_pkg.get("pins", 0)

        sym_dir = os.path.join(out_folder, "Symbols", name)
        os.makedirs(sym_dir, exist_ok=True)

        # Crea/popola il database SQLite del simbolo
        db_path = os.path.join(sym_dir, f"{name}.db")
        con = sqlite3.connect(db_path)
        con.execute(
            "CREATE TABLE IF NOT EXISTS symbol_data ("
            "\"Pin ID\" TEXT,"
            "\"Pin Name\" TEXT,"
            "\"Active Low\" TEXT,"
            "\"Package Type\" TEXT,"
            "\"Part #\" TEXT)"
        )
        con.execute("DELETE FROM symbol_data")
        rows = []
        if pins:
            for pin in pins:
                rows.append((
                    pin.get("number", ""),
                    pin.get("name", ""),
                    "True" if pin.get("negated", False) else "False",
                    package_type,
                    pin.get("part_number", "1"),
                ))
        else:
            # Nessun pin definito: inserisce una riga con i dati base
            rows.append(("", "", "False", package_type, "1"))
        con.executemany(
            "INSERT INTO symbol_data VALUES (?, ?, ?, ?, ?)", rows
        )
        con.commit()
        con.close()

        # -- Struttura cartelle DEHDL symbol ----------------------------------
        dehdl_dir = os.path.join(sym_dir, "DEHDL symbol")

        # chips/
        chips_dir = os.path.join(dehdl_dir, "chips")
        os.makedirs(chips_dir, exist_ok=True)

        chips_prt_path = os.path.join(chips_dir, "chips.prt")
        # Costruisce il contenuto di chips.prt
        primitive_id = f"{name}_{pkg_pin_count}PIN" if pkg_pin_count else name

        # Genera la lista dei pin tra PIN e END_PIN
        # Prepara la lista con (y, x_sort_key, pin_id, y) per ordinamento
        pin_entries = []
        for pin in pins:
            pin_id = pin.get("number", "").strip()
            try:
                y = int(pin.get("part_number", "1"))
            except (ValueError, TypeError):
                y = 1
            # Chiave di ordinamento per x: numerica se possibile, altrimenti stringa
            try:
                x_key = (0, int(pin_id))
            except (ValueError, TypeError):
                x_key = (1, pin_id)
            pin_entries.append((y, x_key, pin_id, y))

        pin_entries.sort(key=lambda e: (e[0], e[1]))

        pin_lines = []
        for y, x_key, pin_id, part_y in pin_entries:
            vec = ["0"] * num_parts
            if 1 <= part_y <= num_parts:
                vec[part_y - 1] = pin_id if pin_id else "0"
            vec_str = ",".join(vec)
            pin_lines.append(f"  'N{pin_id}-{part_y}':")
            pin_lines.append(f"   PIN_NUMBER='({vec_str})';")

        pin_block = "\n".join(pin_lines) + "\n" if pin_lines else ""

        chips_prt_content = (
            "FILE_TYPE=LIBRARY_PARTS ;\n"
            f"PRIMITIVE '{name}','{primitive_id}';\n"
            " PIN\n"
            f"{pin_block}"
            " END_PIN;\n"
            " BODY\n"
            "  C_PATH='/LOGIC.1.1.1P';\n"
            "  C_VIEW='CHIPS_PRT.1';  \n"
            f"  PHYS_DES_PREFIX='{ref_des}';\n"
            "  SIZE='1';  \n"
            f"  PART_NAME='{name}';\n"
            " END_BODY;\n"
            "END_PRIMITIVE;\n"
            "END.\n"
        )
        with open(chips_prt_path, "w", encoding="utf-8") as f:
            f.write(chips_prt_content)
        # Crea master.tag con il contenuto 'chips.prt' nella stessa directory
        with open(os.path.join(chips_dir, "master.tag"), "w", encoding="utf-8") as f:
            f.write("chips.prt")

        # entity/
        os.makedirs(os.path.join(dehdl_dir, "entity"), exist_ok=True)



        # sym_1  sym_N/
        for part_num in range(1, num_parts + 1):
            sym_part_dir = os.path.join(dehdl_dir, f"sym_{part_num}")
            os.makedirs(sym_part_dir, exist_ok=True)
            with open(os.path.join(sym_part_dir, "master.tag"), "w", encoding="utf-8") as f:
                f.write("symbol.css")
            open(os.path.join(sym_part_dir, "symbol.css"), "a").close()

        entry = {
            "name":    name,
            "parts":   num_parts,
            "package": package_type,
            "folder":  sym_dir,
        }
        existing = next((i for i, s_ in enumerate(symbols) if s_["name"] == name), None)
        if existing is not None:
            symbols[existing] = entry
        else:
            symbols.append(entry)
        save_symbols(symbols)
        symbols[:] = load_symbols()
        new_sym_panel.visible = False
        update_symbol_buttons()

    def _on_del_sym_dd_select(e):
        enabled = bool(del_sym_dd.value)
        if del_sym_confirm_btn_ref.current:
            del_sym_confirm_btn_ref.current.disabled = not enabled
            del_sym_confirm_btn_ref.current.opacity  = 1.0 if enabled else 0.35
            page.update()

    def show_delete_symbol(e):
        if not symbols:
            return
        del_sym_dd.options = [ft.dropdown.Option(s_["name"]) for s_ in symbols]
        del_sym_dd.value   = None
        new_sym_panel.visible  = False
        add_pkg_panel.visible  = False
        del_pkg_panel.visible  = False
        sym_list_panel.visible = False
        pkg_list_panel.visible = False
        search_pkg_panel.visible = False
        if del_sym_confirm_btn_ref.current:
            del_sym_confirm_btn_ref.current.disabled = True
            del_sym_confirm_btn_ref.current.opacity  = 0.35
        del_sym_panel.visible = True
        page.update()

    def confirm_delete_symbol(_):
        name = del_sym_dd.value
        if not name:
            return
        sym = next((s_ for s_ in symbols if s_["name"] == name), None)
        if not sym:
            return
        symbols[:] = [s_ for s_ in symbols if s_["name"] != name]
        save_symbols(symbols)
        symbols[:] = load_symbols()
        folder = sym.get("folder", "")
        if folder and os.path.isdir(folder):
            shutil.rmtree(folder)
        del_sym_panel.visible = False
        update_symbol_buttons()

    def cancel_delete_symbol(_):
        del_sym_panel.visible = False
        page.update()

    def show_add_package(e):
        _pkg_mode["mode"]          = "add"
        _pkg_mode["original_idx"]  = -1
        new_sym_panel.visible      = False
        del_pkg_panel.visible      = False
        del_sym_panel.visible      = False
        sym_list_panel.visible     = False
        pkg_list_panel.visible     = False
        search_pkg_panel.visible   = False
        _reset_pkg_state()
        _set_centered_layout()
        if _bottom_bar_ref.current:
            _bottom_bar_ref.current.visible = False
        add_pkg_panel.visible = True
        _check_save_enabled()
        page.update()

    def save_package(_):
        name     = pkg_name_field.value.strip()
        pins_str = pkg_pins_field.value.strip()
        if not name or not (pins_str.isdigit() and int(pins_str) > 0):
            return
        pins     = int(pins_str)
        mode     = _pkg_mode["mode"]
        orig_idx = _pkg_mode["original_idx"]

        for i, p in enumerate(packages):
            if p["name"] == name and p["pins"] == pins:
                if mode == "add" or (mode == "edit" and i != orig_idx):
                    pkg_name_field.error_text   = s.get("pkg_duplicate", "Package with same name and pins already exists")
                    pkg_name_field.border_color = ft.colors.RED
                    page.update()
                    return
        pkg_name_field.error_text   = None
        pkg_name_field.border_color = None

        pins_data = [
            {"bbox_orig": list(p["bbox_orig"]), "name": p["name"], "number": p["number"]}
            for p in _fp_state["pins"]
        ]

        if mode == "add":
            fp_dest = ""
            if pkg_images["footprint"]:
                d_src   = pkg_images["footprint"]
                fp_dest = os.path.join(_cfg_mod.PACKAGES_IMAGES_DIR, f"{name}{pins}_d.png")
                if d_src != fp_dest:
                    shutil.move(d_src, fp_dest)
                d_stem = os.path.splitext(d_src)[0]
                l_src  = d_stem[:-2] + "_l.png"
                fp_dest_l = os.path.join(_cfg_mod.PACKAGES_IMAGES_DIR, f"{name}{pins}_l.png")
                if os.path.isfile(l_src) and l_src != fp_dest_l:
                    shutil.move(l_src, fp_dest_l)
            packages.append({"name": name, "pins": pins, "footprint": fp_dest, "pins_data": pins_data})
            pkg_images["footprint_is_temp"] = False
        save_packages(packages)
        packages[:] = load_packages()
        add_pkg_panel.visible = False
        update_symbol_buttons()

    def cancel_add_pkg(_):
        _reset_pkg_state()
        _set_centered_layout()
        if _bottom_bar_ref.current:
            _bottom_bar_ref.current.visible = False
        add_pkg_panel.visible = False
        page.update()

    # -- Search Package (footprint guide) ------------------------------------
    def show_search_package(e):
        new_sym_panel.visible  = False
        add_pkg_panel.visible  = False
        del_pkg_panel.visible  = False
        del_sym_panel.visible  = False
        sym_list_panel.visible = False
        pkg_list_panel.visible = False
        search_pkg_panel.visible = True
        page.update()

    def show_delete_package(e):
        if not packages:
            return
        del_pkg_dd.options     = [ft.dropdown.Option(pkg_display_name(p)) for p in packages]
        del_pkg_dd.value       = None
        new_sym_panel.visible  = False
        add_pkg_panel.visible  = False
        del_sym_panel.visible  = False
        sym_list_panel.visible = False
        pkg_list_panel.visible = False
        search_pkg_panel.visible = False
        del_pkg_panel.visible  = True
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
        fp_path = pkg.get("footprint", "")
        packages[:] = [p for p in packages if pkg_display_name(p) != dname]
        save_packages(packages)
        packages[:] = load_packages()
        if fp_path and os.path.isfile(fp_path):
            os.remove(fp_path)
            stem, ext = os.path.splitext(fp_path)
            if stem.endswith("_d"):
                l_path = stem[:-2] + "_l" + ext
                if os.path.isfile(l_path):
                    os.remove(l_path)
        del_pkg_panel.visible = False
        update_symbol_buttons()

    def cancel_delete(_):
        del_pkg_panel.visible = False
        page.update()

    def _show_footprint_popup(pkg):
        fp = _theme_fp_path(pkg.get("footprint", ""))
        if fp and os.path.isfile(fp):
            img_ctrl = ft.Image(src=fp, width=500, fit=ft.ImageFit.CONTAIN)
        else:
            img_ctrl = ft.Text(s.get("no_footprint_image", "No image available."), italic=True)
        dlg = ft.AlertDialog(
            title=ft.Text(pkg_display_name(pkg), weight=ft.FontWeight.BOLD),
            content=ft.Container(content=img_ctrl, alignment=ft.alignment.center),
            actions=[ft.TextButton(s.get("close", "Close"), on_click=lambda _: page.close(dlg))],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.open(dlg)

    def show_packages(e):
        new_sym_panel.visible    = False
        add_pkg_panel.visible    = False
        del_pkg_panel.visible    = False
        del_sym_panel.visible    = False
        sym_list_panel.visible   = False
        search_pkg_panel.visible = False

        def _build_pkg_rows(filter_text=""):
            ft_lower = filter_text.strip().lower()
            filtered = [p for p in packages if ft_lower in pkg_display_name(p).lower()] if ft_lower else packages

            def _make_pkg_row(p):
                return ft.Container(
                    content=ft.Column(
                        [
                            ft.Row(
                                [ft.Icon(ft.icons.MEMORY, size=16),
                                 ft.Text(pkg_display_name(p), size=13,
                                         weight=ft.FontWeight.W_500, expand=True)],
                                spacing=8,
                            ),
                            ft.Text(
                                f"{s.get('created_at_label', 'Created')}: {p.get('created_at', '')}",
                                size=11, italic=True, color=ft.colors.GREY_500,
                            ),
                        ],
                        spacing=2,
                    ),
                    on_click=lambda _, pkg=p: _show_footprint_popup(pkg),
                    ink=True,
                    border_radius=ft.border_radius.all(6),
                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                )

            rows = [_make_pkg_row(p) for p in filtered] if filtered else [
                ft.Text(s.get("no_packages", "No packages defined yet."), italic=True)
            ]
            rows.append(
                ft.TextButton(
                    s.get("close", "Close"),
                    on_click=lambda _: (setattr(pkg_list_panel, "visible", False), page.update()),
                )
            )
            return rows

        pkg_search_field = ft.TextField(
            hint_text=s.get("search_package_hint", "Search package"),
            prefix_icon=ft.icons.SEARCH,
            width=220,
            height=38,
            content_padding=ft.padding.symmetric(horizontal=10, vertical=4),
            border_radius=ft.border_radius.all(8),
            on_change=lambda ev: (
                setattr(pkg_list_col, "controls", _build_pkg_rows(ev.control.value)),
                page.update(),
            ),
        )

        if packages:
            pkg_list_col.controls = _build_pkg_rows()
        else:
            pkg_list_col.controls = [
                ft.Text(s.get("no_packages", "No packages defined yet."), italic=True),
                ft.TextButton(
                    s.get("close", "Close"),
                    on_click=lambda _: (setattr(pkg_list_panel, "visible", False), page.update()),
                ),
            ]

        pkg_list_panel.content = ft.Column(
            [
                ft.Row(
                    [
                        ft.Text(s.get("show_packages", "Show Packages"), size=16,
                                weight=ft.FontWeight.W_600, color=ft.colors.ORANGE, expand=True),
                        pkg_search_field,
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Divider(height=1),
                pkg_list_col,
            ],
            spacing=10,
        )
        pkg_list_panel.visible = True
        page.update()

    def _show_symbol_db_popup(sym):
        import sqlite3
        folder = sym.get("folder", "")
        name   = sym.get("name", "")
        db_path = os.path.join(folder, f"{name}.db")
        rows = []
        if os.path.isfile(db_path):
            try:
                con = sqlite3.connect(db_path)
                # Ordina per Pin ID: prima numericamente se possibile, poi alfabeticamente
                cur = con.execute(
                    "SELECT \"Pin ID\", \"Pin Name\", \"Active Low\", \"Package Type\", \"Part #\" "
                    "FROM symbol_data "
                    "ORDER BY CAST(\"Pin ID\" AS INTEGER), \"Pin ID\""
                )
                rows = cur.fetchall()
                con.close()
            except Exception:
                rows = []

        # Estrai Package Type dal primo record (tutti uguali)
        package_type = rows[0][3] if rows else ""

        # Colonne visibili: Pin ID, Pin Name, Active Low, Part # (Package Type escluso)
        col_pin_name   = s.get("pin_name_col", "Pin Name")
        col_active_low = s.get("active_low_col", "Active Low")
        display_columns = ["Pin ID", col_pin_name, col_active_low, "Part #"]

        def _cell_val(row, col):
            mapping = {"Pin ID": 0, col_pin_name: 1, col_active_low: 2, "Package Type": 3, "Part #": 4}
            v = row[mapping[col]]
            return str(v) if v is not None else ""

        def _make_cell(row, col):
            val = _cell_val(row, col)
            if col == col_active_low:
                is_true = val.strip().lower() in ("true", "1", "yes")
                display = s.get("true_val", "True") if is_true else s.get("false_val", "False")
                color   = ft.colors.LIGHT_BLUE_400 if is_true else ft.colors.ORANGE
                content = ft.Text(display, color=color, weight=ft.FontWeight.BOLD)
            else:
                content = ft.Text(val)
            return ft.DataCell(ft.Container(content=content, alignment=ft.alignment.center, expand=True))

        data_rows = [
            ft.DataRow(cells=[_make_cell(row, c) for c in display_columns])
            for row in rows
        ] if rows else [
            ft.DataRow(cells=[
                ft.DataCell(ft.Container(
                    content=ft.Text(""),
                    alignment=ft.alignment.center,
                    expand=True,
                )) for _ in display_columns
            ])
        ]

        table = ft.DataTable(
            columns=[ft.DataColumn(ft.Text(c, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)) for c in display_columns],
            rows=data_rows,
            border=ft.border.all(1, ft.colors.OUTLINE),
            border_radius=ft.border_radius.all(6),
            horizontal_lines=ft.BorderSide(1, ft.colors.OUTLINE),
            heading_row_color=ft.colors.with_opacity(0.05, ft.colors.ON_SURFACE),
        )

        dlg = ft.AlertDialog(
            title=ft.Text(name, weight=ft.FontWeight.BOLD),
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Text(package_type, size=13, italic=True, color=ft.colors.ORANGE) if package_type else ft.Container(),
                        ft.Container(height=8),
                        ft.Container(
                            content=ft.Row([table], scroll=ft.ScrollMode.AUTO, alignment=ft.MainAxisAlignment.CENTER),
                            alignment=ft.alignment.center,
                        ),
                    ],
                    tight=True,
                ),
                width=680,
            ),
            actions=[ft.TextButton(s.get("close", "Close"), on_click=lambda _: page.close(dlg))],
            actions_alignment=ft.MainAxisAlignment.CENTER,
        )
        page.open(dlg)

    def show_symbols(e):
        new_sym_panel.visible  = False
        add_pkg_panel.visible  = False
        del_pkg_panel.visible  = False
        del_sym_panel.visible  = False
        pkg_list_panel.visible = False
        search_pkg_panel.visible = False

        def _build_sym_rows(filter_text=""):
            ft_lower = filter_text.strip().lower()
            filtered = [sym for sym in symbols if ft_lower in sym["name"].lower()] if ft_lower else symbols

            def _make_sym_row(sym):
                return ft.Container(
                    content=ft.Column(
                        [
                            ft.Row(
                                [ft.Icon(ft.icons.CATEGORY, size=16),
                                 ft.Text(sym["name"], size=13,
                                         weight=ft.FontWeight.W_500, expand=True)],
                                spacing=8,
                            ),
                            ft.Text(
                                f"{s.get('package_type', 'Package')}: {sym.get('package', '')}  ¦  "
                                f"{s.get('created_at_label', 'Created')}: {sym.get('created_at', '')}",
                                size=11, italic=True, color=ft.colors.GREY_500,
                            ),
                        ],
                        spacing=2,
                    ),
                    on_click=lambda _, sym_=sym: _show_symbol_db_popup(sym_),
                    ink=True,
                    border_radius=ft.border_radius.all(6),
                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                )

            rows = [_make_sym_row(sym) for sym in filtered] if filtered else [
                ft.Text(s.get("no_symbols", "No symbols created yet."), italic=True)
            ]
            rows.append(
                ft.TextButton(
                    s.get("close", "Close"),
                    on_click=lambda _: (setattr(sym_list_panel, "visible", False), page.update()),
                )
            )
            return rows

        sym_search_field = ft.TextField(
            hint_text=s.get("search_symbol_hint", "Search symbol"),
            prefix_icon=ft.icons.SEARCH,
            width=220,
            height=38,
            content_padding=ft.padding.symmetric(horizontal=10, vertical=4),
            border_radius=ft.border_radius.all(8),
            on_change=lambda ev: (
                setattr(sym_list_col, "controls", _build_sym_rows(ev.control.value)),
                page.update(),
            ),
        )

        if symbols:
            sym_list_col.controls = _build_sym_rows()
        else:
            sym_list_col.controls = [
                ft.Text(s.get("no_symbols", "No symbols created yet."), italic=True),
                ft.TextButton(
                    s.get("close", "Close"),
                    on_click=lambda _: (setattr(sym_list_panel, "visible", False), page.update()),
                ),
            ]

        sym_list_panel.content = ft.Column(
            [
                ft.Row(
                    [
                        ft.Text(s.get("show_symbols", "Show Symbols"), size=16,
                                weight=ft.FontWeight.W_600, color=ft.colors.ORANGE, expand=True),
                        sym_search_field,
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Divider(height=1),
                sym_list_col,
            ],
            spacing=10,
        )
        sym_list_panel.visible = True
        page.update()

    # -- Panels ----------------------------------------------------------------
    pkg_list_col = ft.Column([], spacing=6)

    pkg_list_panel = ft.Container(
        visible=False,
        padding=ft.padding.symmetric(horizontal=24, vertical=12),
        content=ft.Column(
            [
                ft.Text(s.get("show_packages", "Show Packages"), size=16,
                        weight=ft.FontWeight.W_600, color=ft.colors.ORANGE),
                ft.Divider(height=1),
                pkg_list_col,
            ],
            spacing=10,
        ),
    )

    sym_list_col = ft.Column([], spacing=6)

    sym_list_panel = ft.Container(
        visible=False,
        padding=ft.padding.symmetric(horizontal=24, vertical=12),
        content=ft.Column(
            [
                ft.Text(s.get("show_symbols", "Show Symbols"), size=16,
                        weight=ft.FontWeight.W_600, color=ft.colors.ORANGE),
                ft.Divider(height=1),
                sym_list_col,
            ],
            spacing=10,
        ),
    )

    pkg_dropdown.on_change     = _on_pkg_type_change
    ref_des_dropdown.on_change = _on_ref_des_change

    # \u2500\u2500 Delete Symbol dropdown + confirm button ref \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    del_sym_confirm_btn_ref = ft.Ref[ft.ElevatedButton]()

    del_sym_dd = ft.Dropdown(
        label=s.get("symbol_name", "Symbol Name"), width=280, on_change=_on_del_sym_dd_select
    )

    del_sym_panel = ft.Container(
        visible=False,
        expand=True,
        padding=ft.padding.symmetric(horizontal=12, vertical=12),
        content=ft.Column(
            [
                ft.Text(
                    s.get("delete_symbol", "Delete Symbol"),
                    size=16,
                    weight=ft.FontWeight.W_600,
                    color=ft.colors.ORANGE,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Container(
                    expand=True,
                    alignment=ft.alignment.center,
                    content=ft.Column(
                        [
                            del_sym_dd,
                            ft.Row(
                                [
                                    ft.ElevatedButton(
                                        s.get("delete", "Delete"),
                                        ref=del_sym_confirm_btn_ref,
                                        icon=ft.icons.DELETE,
                                        color=ft.colors.RED,
                                        on_click=confirm_delete_symbol,
                                        disabled=True,
                                        opacity=0.35,
                                    ),
                                    ft.TextButton(s.get("close", "Cancel"), on_click=cancel_delete_symbol),
                                ],
                                spacing=8,
                                alignment=ft.MainAxisAlignment.CENTER,
                            ),
                        ],
                        spacing=12,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        tight=True,
                    ),
                ),
            ],
            spacing=8,
            expand=True,
        ),
    )

    _new_sym_action_row = ft.Row(
        [
            ft.ElevatedButton(
                s.get("generate_symbol", "Generate Symbol"),
                ref=generate_sym_btn_ref,
                icon=ft.icons.BOLT,
                on_click=_generate_symbol,
                color=ft.colors.WHITE,
                bgcolor=ft.colors.GREEN_700,
                disabled=True,
                opacity=0.35,
            ),
            ft.ElevatedButton(
                s.get("close", "Cancel"),
                on_click=lambda e: (
                    setattr(new_sym_panel, "visible", False) or page.update()
                ),
                color=ft.colors.WHITE,
                bgcolor=ft.colors.GREY_600,
            ),
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=8,
        wrap=True,
    )

    new_sym_panel = ft.Container(
        visible=False,
        expand=True,
        padding=ft.padding.symmetric(horizontal=12, vertical=12),
        content=ft.Column(
            [
                # Frame 1  title
                ft.Text(
                    ref=_new_sym_title_ref,
                    value=s.get("new_symbol", "New Symbol"),
                    size=16,
                    weight=ft.FontWeight.W_600,
                    color=ft.colors.ORANGE,
                    text_align=ft.TextAlign.CENTER,
                ),
                # Frame 2  main content (centered fields or two-col with preview)
                ft.Container(
                    ref=_new_sym_content_ref,
                    expand=True,
                    content=ft.Container(
                        expand=True,
                        alignment=ft.alignment.center,
                        content=ft.Column(
                            [sym_name_field, sym_parts_field, pkg_dropdown, ref_des_dropdown],
                            spacing=12,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            tight=True,
                        ),
                    ),
                ),
                # Frame 2.5  Next button (always visible, enabled only when all fields ok)
                ft.Container(
                    ref=_next_sym_bar_ref,
                    visible=True,
                    alignment=ft.alignment.center,
                    padding=ft.padding.symmetric(vertical=10),
                    content=ft.TextButton(
                        s.get("next", "Next"),
                        ref=_next_sym_btn_ref,
                        on_click=_on_next_click,
                        disabled=True,
                        opacity=0.35,
                    ),
                ),
                # Frame 3  bottom action bar
                ft.Container(
                    ref=_new_sym_bottom_bar_ref,
                    visible=False,
                    alignment=ft.alignment.center,
                    padding=ft.padding.symmetric(vertical=10),
                    content=_new_sym_action_row,
                ),
            ],
            spacing=8,
            expand=True,
        ),
    )

    add_pkg_panel = ft.Container(
        visible=False,
        expand=True,
        padding=ft.padding.symmetric(horizontal=12, vertical=12),
        content=ft.Column(
            [
                ft.Text(
                    s.get("add_package", "Add Package"),
                    size=16,
                    weight=ft.FontWeight.W_600,
                    color=ft.colors.ORANGE,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Container(
                        ref=edit_fields_container_ref,
                        expand=True,
                        alignment=ft.alignment.center,
                        content=ft.Column(
                            [pkg_name_field, pkg_pins_field, _footprint_pick_btn, fp_path_text],
                            spacing=12,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            tight=True,
                        ),
                    ),
                ft.Container(
                    ref=_bottom_bar_ref,
                    visible=False,
                    alignment=ft.alignment.center,
                    padding=ft.padding.symmetric(vertical=10),
                    content=_save_cancel_row,
                ),
            ],
            spacing=8,
            expand=True,
        ),
    )

    del_pkg_panel = ft.Container(
        visible=False,
        expand=True,
        padding=ft.padding.symmetric(horizontal=12, vertical=12),
        content=ft.Column(
            [
                ft.Text(
                    s.get("delete_package", "Delete Package"),
                    size=16,
                    weight=ft.FontWeight.W_600,
                    color=ft.colors.ORANGE,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Container(
                    expand=True,
                    alignment=ft.alignment.center,
                    content=ft.Column(
                        [
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
                        tight=True,
                    ),
                ),
            ],
            spacing=8,
            expand=True,
        ),
    )

    # -- Mode selector state ---------------------------------------------------
    _mode            = {"current": "symbol"}
    _sym_mode_btn_ref = ft.Ref[ft.ElevatedButton]()
    _pkg_mode_btn_ref = ft.Ref[ft.ElevatedButton]()
    _sym_actions_ref  = ft.Ref[ft.Row]()
    _pkg_actions_ref  = ft.Ref[ft.Row]()

    def _switch_mode(mode: str):
        _mode["current"] = mode
        is_sym = mode == "symbol"
        # Aggiorna il colore hover dei dropdown in base alla sezione
        _t = _build_theme(ft.colors.BLUE if is_sym else ft.colors.ORANGE)
        page.theme      = _t
        page.dark_theme = _t
        if _sym_mode_btn_ref.current:
            _sym_mode_btn_ref.current.bgcolor = ft.colors.BLUE if is_sym else ft.colors.GREY_700
            _sym_mode_btn_ref.current.color   = ft.colors.WHITE
            _sym_mode_btn_ref.current.update()
        if _pkg_mode_btn_ref.current:
            _pkg_mode_btn_ref.current.bgcolor = ft.colors.ORANGE if not is_sym else ft.colors.GREY_700
            _pkg_mode_btn_ref.current.color   = ft.colors.WHITE
            _pkg_mode_btn_ref.current.update()
        if _sym_actions_ref.current:
            _sym_actions_ref.current.visible = is_sym
            _sym_actions_ref.current.update()
        if _pkg_actions_ref.current:
            _pkg_actions_ref.current.visible = not is_sym
            _pkg_actions_ref.current.update()

        # Resetto la visibilità di tutti i pannelli (pulisco le view)
        new_sym_panel.visible = False
        del_sym_panel.visible = False
        add_pkg_panel.visible = False
        del_pkg_panel.visible = False
        pkg_list_panel.visible = False
        sym_list_panel.visible = False
        search_pkg_panel.visible = False
        page.update()

    def _on_symbol_mode(e):
        _switch_mode("symbol")

    def _on_package_mode(e):
        _switch_mode("package")

    # -- Command bar -----------------------------------------------------------
    top_bar = ft.Container(
        content=ft.Row(
            [
                # -- Left: mode selector buttons ------------------------------
                ft.Row(
                    [
                        ft.ElevatedButton(
                            ref=_sym_mode_btn_ref,
                            text=s.get("symbol_mode", "Symbol"),
                            bgcolor=ft.colors.BLUE,
                            color=ft.colors.WHITE,
                            on_click=_on_symbol_mode,
                            style=ft.ButtonStyle(
                                shape=ft.RoundedRectangleBorder(radius=4),
                            ),
                        ),
                        ft.ElevatedButton(
                            ref=_pkg_mode_btn_ref,
                            text="Package",
                            bgcolor=ft.colors.GREY_700,
                            color=ft.colors.WHITE,
                            on_click=_on_package_mode,
                            style=ft.ButtonStyle(
                                shape=ft.RoundedRectangleBorder(radius=4),
                            ),
                        ),
                    ],
                    spacing=4,
                    height=40,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                # -- Center: action buttons ------------------------------------
                ft.Row(
                    [
                        ft.Row(
                            ref=_sym_actions_ref,
                            controls=[
                                ft.IconButton(
                                    ref=new_sym_btn_ref,
                                    icon=ft.icons.TASK_ALT,
                                    icon_color=ft.colors.GREEN,
                                    tooltip=s.get("new_symbol", "New Symbol"),
                                    on_click=new_symbol,
                                    disabled=len(packages) == 0,
                                    opacity=1.0 if packages else 0.35,
                                ),
                                ft.IconButton(
                                    ref=show_sym_btn_ref,
                                    icon=ft.icons.VIEW_LIST,
                                    icon_color=ft.colors.BLUE,
                                    tooltip=s.get("show_symbols", "Show Symbols"),
                                    on_click=show_symbols,
                                ),
                                ft.IconButton(
                                    ref=del_sym_btn_ref,
                                    icon=ft.icons.DELETE,
                                    icon_color=ft.colors.RED,
                                    tooltip=s.get("delete_symbol", "Delete Symbol"),
                                    on_click=show_delete_symbol,
                                    disabled=len(symbols) == 0,
                                    opacity=1.0 if symbols else 0.35,
                                ),
                            ],
                            visible=True,
                            spacing=0,
                        ),
                        ft.Row(
                            ref=_pkg_actions_ref,
                            controls=[
                                ft.IconButton(
                                    icon=ft.icons.MEMORY,
                                    icon_color=ft.colors.GREEN,
                                    tooltip=s.get("add_package", "Add Package"),
                                    on_click=show_add_package,
                                ),
                                ft.IconButton(
                                    icon=ft.icons.LIST_ALT,
                                    icon_color=ft.colors.BLUE,
                                    tooltip=s.get("show_packages", "Show Packages"),
                                    on_click=show_packages,
                                ),
                                ft.IconButton(
                                    icon=ft.icons.SEARCH,
                                    icon_color=ft.colors.ORANGE,
                                    tooltip=s.get("search_package", "Search Package"),
                                    on_click=show_search_package,
                                ),
                                ft.IconButton(
                                    ref=del_pkg_btn_ref,
                                    icon=ft.icons.DELETE_FOREVER,
                                    icon_color=ft.colors.RED,
                                    tooltip=s.get("delete_package", "Delete Package"),
                                    on_click=show_delete_package,
                                    disabled=len(packages) == 0,
                                    opacity=1.0 if packages else 0.35,
                                ),
                            ],
                            visible=False,
                            spacing=0,
                        ),
                    ],
                    expand=True,
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    height=40,
                ),
                # -- Right: settings/help --------------------------------------
                ft.Row(
                    [
                        ft.PopupMenuButton(
                            icon=ft.icons.SETTINGS,
                            tooltip=s["settings"],
                            items=[
                                ft.PopupMenuItem(
                                    content=ft.Row(
                                        [ft.Icon(ft.icons.FOLDER), ft.Text(s["output_folder"])],
                                        spacing=8,
                                    ),
                                    on_click=show_output_folder_dialog,
                                ),
                                ft.PopupMenuItem(
                                    content=ft.Row(
                                        [ft.Icon(ft.icons.LANGUAGE), ft.Text(s["language"])],
                                        spacing=8,
                                    ),
                                    on_click=show_language_dialog,
                                ),
                            ],
                        ),
                        ft.IconButton(
                            icon=ft.icons.WB_SUNNY,
                            tooltip=s["toggle_theme"],
                            on_click=toggle_theme,
                        ),
                        ft.PopupMenuButton(
                            icon=ft.icons.HELP,
                            tooltip=s["help"],
                            items=[
                                ft.PopupMenuItem(
                                    content=ft.Row(
                                        [ft.Icon(ft.icons.INFO), ft.Text(s["about"])],
                                        spacing=8,
                                    ),
                                    on_click=show_about,
                                ),
                                ft.PopupMenuItem(
                                    content=ft.Row(
                                        [ft.Icon(ft.icons.MENU_BOOK), ft.Text(s["user_manual"])],
                                        spacing=8,
                                    ),
                                    on_click=show_user_manual,
                                ),
                                ft.PopupMenuItem(
                                    content=ft.Row(
                                        [ft.Icon(ft.icons.ARTICLE), ft.Text(s["release_notes"])],
                                        spacing=8,
                                    ),
                                    on_click=show_release_notes,
                                ),
                            ],
                        ),
                    ],
                    spacing=0,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(horizontal=8, vertical=4),
    )

    def _step_row(number: str, spans):
        return ft.Row(
            [
                ft.Container(
                    content=ft.Text(
                        number,
                        size=15,
                        weight=ft.FontWeight.BOLD,
                        color=ft.colors.ORANGE,
                    ),
                    width=28,
                    alignment=ft.alignment.top_left,
                ),
                ft.Text(spans=spans, size=14),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

    search_pkg_panel = ft.Container(
        visible=False,
        expand=True,
        padding=ft.padding.symmetric(horizontal=32, vertical=20),
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(ft.icons.SEARCH, color=ft.colors.ORANGE, size=20),
                        ft.Text(
                            s.get("search_package", "Search Package"),
                            size=16,
                            weight=ft.FontWeight.W_600,
                            color=ft.colors.ORANGE,
                        ),
                        ft.Container(expand=True),
                        ft.TextButton(
                            s.get("close", "Close"),
                            on_click=lambda _: (
                                setattr(search_pkg_panel, "visible", False)
                                or page.update()
                            ),
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=8,
                ),
                ft.Divider(height=1),
                ft.Column(
                    [
                        _step_row("1.", [
                            ft.TextSpan(s.get("fp_guide_step1_pre", "Go to ")),
                            ft.TextSpan(
                                "SnapEDA",
                                on_click=lambda _: page.launch_url("https://www.snapeda.com"),
                                style=ft.TextStyle(
                                    color=ft.colors.BLUE,
                                    decoration=ft.TextDecoration.UNDERLINE,
                                    weight=ft.FontWeight.BOLD,
                                ),
                            ),
                            ft.TextSpan(s.get("fp_guide_step1_post", "  (snapeda.com)")),
                        ]),
                        _step_row("2.", [
                            ft.TextSpan(s.get("fp_guide_step2", "Search and select the device for which you want to create the symbol.")),
                        ]),
                        _step_row("3.", [
                            ft.TextSpan(s.get("fp_guide_step3", "Find the footprint image on the device page.")),
                        ]),
                        _step_row("4.", [
                            ft.TextSpan(s.get("fp_guide_step4", "Save the image in PNG format where you want and with the desired name.")),
                        ]),
                        ft.Container(height=20),
                        ft.Container(
                            content=ft.Image(
                                src="SystemImages/snapeda.gif",
                                width=500,
                                fit=ft.ImageFit.CONTAIN,
                                border_radius=ft.border_radius.all(10),
                            ),
                            alignment=ft.alignment.center,
                            expand=True,
                        ),
                    ],
                    spacing=16,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    expand=True,
                ),
            ],
            spacing=14,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        ),
    )

    body = ft.Column(
        [new_sym_panel, del_sym_panel, add_pkg_panel, del_pkg_panel,
         pkg_list_panel, sym_list_panel, search_pkg_panel],
        expand=True,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    page.views.clear()
    page.views.append(
        ft.View(
            route="/main",
            controls=[
                ft.Column(
                    [top_bar, body],
                    expand=True,
                )
            ],
        )
    )
    page.update()

