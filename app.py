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
    pkg_pkgtype_wrapper_ref    = ft.Ref[ft.Container]()
    footprint_preview_ref      = ft.Ref[ft.Container]()
    fp_canvas_ref              = ft.Ref[cv.Canvas]()
    del_pkg_btn_ref            = ft.Ref[ft.IconButton]()

    _pkg_mode = {"mode": "add", "original_idx": -1}
    _orig_pkg_values = {"name": "", "pins": "", "footprint": ""}  # unused, kept for safety
    _fp_state = {"pins": [], "scale_x": 1.0, "scale_y": 1.0}
    _pin_method = {"value": None, "waiting_pin1": False}
    _sym_pkg_ref = {"footprint": ""}  # footprint path active in New Symbol interactive preview
    _selected_pkg_catalog_type = {"mount": "", "type": ""}  # package type of selected Package ID
    pin_method_dd_ref               = ft.Ref[ft.Dropdown]()
    pin_method_dd_wrapper_ref       = ft.Ref[ft.Container]()
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
    _new_sym_subtitle_ref           = ft.Ref[ft.Text]()
    _add_pkg_title_ref              = ft.Ref[ft.Text]()
    _new_sym_step3_title_ref        = ft.Ref[ft.Text]()
    _new_sym_step3_summary_ref      = ft.Ref[ft.Column]()
    _new_sym_step3_part_dd_ref      = ft.Ref[ft.Dropdown]()
    generate_sym_btn_ref            = ft.Ref[ft.ElevatedButton]()
    _sym_editor_content_ref         = ft.Ref[ft.Container]()

    # ── Step-3 symbol layout state ──────────────────────────────────────────
    _sym_pin_layout: dict = {}   # {str(pin_idx): {"side": "left"|"right"|"top"|"bottom"}}
    _sym_step3_part: dict = {"value": 1}
    _SYM_CANVAS_W    = 720
    _SYM_PIN_SPACING = 60
    _SYM_PIN_STUB    = 20
    _SYM_BODY_W      = 280
    _SYM_PAD_Y       = 50
    _SYM_PAD_X       = 50
    _SYM_SIDES       = ["left", "right", "top", "bottom"]
    _SYM_GRID        = 20   # canvas pixels between grid lines / snap step
    # ── Body resize state ───────────────────────────────────────────────────
    _sym_body_size: dict   = {}        # {part_str: {"w": px, "h": px}} user-set body size
    _sym_body_resize: dict = {         # resize-handle drag state
        "active": False,
        "orig_w": 0, "orig_h": 0,
        "orig_body_l": 0, "orig_body_r": 0, "orig_body_bot": 0,
        "pin_snapshot": {},
        "delta_x": 0.0, "delta_y": 0.0,
        "part_num": 1,
    }
    # ── Drag state ──────────────────────────────────────────────────────────
    _sym_canvas_ref  = ft.Ref[cv.Canvas]()
    _sym_pin_order: dict = {}   # {part_str: {side: [idx,...]}}
    _sym_editor_state: dict = {
        "hit_areas": [],   # [(x1,y1,x2,y2, pin_idx, side, row)]
        "canvas_h": 400, "canvas_w": 720,
        "body_top": 44, "body_bot": 300, "body_l": 220, "body_r": 500,
    }
    _sym_drag: dict = {
        "active": False, "pin_idx": None, "side": None,
        "orig_row": -1, "cur_x": 0.0, "cur_y": 0.0, "part_num": 1,
    }
    _sym_tap_pos: dict = {"x": 0.0, "y": 0.0}

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
        label=s.get("part_name", "Part Name"), width=320, autofocus=True,
        on_change=lambda e: _update_next_btn_state(),
    )
    sym_part_number_field = ft.TextField(
        label=s.get("part_number", "Part Number"), width=320,
        on_change=lambda e: _update_next_btn_state(),
    )
    sym_dup_error_text = ft.Text(
        value="",
        color=ft.colors.RED,
        size=24,
        visible=False,
        text_align=ft.TextAlign.CENTER,
        width=320,
    )
    sym_parts_field = ft.TextField(
        label=s.get("symbol_parts", "Number of Symbol Parts"), width=320,
        on_change=lambda e: (_check_sym_parts(e), _update_next_btn_state()),
    )
    pkg_dropdown = ft.Dropdown(
        label=s.get("package_id", "Package ID"),
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
        mnt_ok   = bool(pkg_mounting_dd.value)
        pkt_ok   = bool(pkg_pkgtype_dd.value)
        
        if pins_str == "":
            pkg_pins_field.error_text   = None
            pkg_pins_field.border_color = None
        elif not pins_ok:
            pkg_pins_field.error_text   = s.get("positive_integer_error", "Please enter a positive non-zero integer")
            pkg_pins_field.border_color = ft.colors.RED
        else:
            pkg_pins_field.error_text   = None
            pkg_pins_field.border_color = None
        fp_btn_ok = name_ok and pins_ok and mnt_ok and pkt_ok
        _footprint_pick_btn.disabled = not fp_btn_ok
        _footprint_pick_btn.opacity  = 1.0 if fp_btn_ok else 0.35
        if _footprint_pick_btn.page:
            _footprint_pick_btn.update()
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
        disabled=True,
        opacity=0.35,
    )

    # -- Mounting Type / Package Type dropdowns --------------------------------
    def _get_pkg_type_options(mnt: str):
        if mnt == "THT":
            return [
                ft.dropdown.Option("SIP/SIL",                         "SIP/SIL"),
                ft.dropdown.Option("DIP/DIL",                         "DIP/DIL"),
                ft.dropdown.Option("ZIP",                             "ZIP"),
                ft.dropdown.Option("PGA",                             "PGA"),
                ft.dropdown.Option("DO-15/DO-35/DO-41/DO-201/DO-201AD", "DO-15/DO-35/DO-41/DO-201/DO-201AD"),
            ]
        elif mnt == "SMT":
            return [
                ft.dropdown.Option("SOD",              "SOD"),
                ft.dropdown.Option("SOT",              "SOT"),
                ft.dropdown.Option("SOIC/SO",          "SOIC/SO"),
                ft.dropdown.Option("TSSOP/MSOP",       "TSSOP/MSOP"),
                ft.dropdown.Option("QFP/DFN/QFN",      "QFP/DFN/QFN"),
                ft.dropdown.Option("BGA/LBGA/FBGA",    "BGA/LBGA/FBGA"),
                ft.dropdown.Option("WLCSP",            "WLCSP"),
                ft.dropdown.Option("0201/0402/0603/0805/1206", "0201/0402/0603/0805/1206"),
            ]
        return []

    def _on_mounting_change(e):
        nonlocal pkg_pkgtype_dd
        mnt_val = pkg_mounting_dd.value
        new_opts = _get_pkg_type_options(mnt_val or "")
        # Ricrea il dropdown da zero: unico modo sicuro per forzare il reset visivo in Flet
        pkg_pkgtype_dd = ft.Dropdown(
            label=s.get("package_type", "Package Type"),
            width=280,
            options=new_opts,
            value=None,  # nessuna selezione → mostra solo la label
            disabled=not bool(mnt_val),
            opacity=1.0 if bool(mnt_val) else 0.5,
            on_change=_check_save_enabled,
        )
        if pkg_pkgtype_wrapper_ref.current:
            pkg_pkgtype_wrapper_ref.current.content = pkg_pkgtype_dd
            if pkg_pkgtype_wrapper_ref.current.page:
                pkg_pkgtype_wrapper_ref.current.update()
        _check_save_enabled()

    pkg_mounting_dd = ft.Dropdown(
        label=s.get("mounting_type", "Mounting Type"),
        width=280,
        options=[
            ft.dropdown.Option("SMT", "SMT"),
            ft.dropdown.Option("THT", "THT"),
        ],
        on_change=_on_mounting_change,
    )
    pkg_pkgtype_dd = ft.Dropdown(
        label=s.get("package_type", "Package Type"),
        width=280,
        options=[],
        disabled=True,
        opacity=0.5,
        on_change=_check_save_enabled,
    )
    # Wrapper container: sostituendo il suo content si ricrea il dropdown visivamente
    pkg_pkgtype_wrapper = ft.Container(
        ref=pkg_pkgtype_wrapper_ref,
        content=pkg_pkgtype_dd,
    )
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
                [pkg_mounting_dd, pkg_pkgtype_wrapper, pkg_pins_field, pkg_name_field, _footprint_pick_btn, fp_path_text],
                spacing=12,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                tight=True,
            ),
        )
        edit_fields_container_ref.current.update()
        if _add_pkg_title_ref.current:
            _add_pkg_title_ref.current.value = s.get("add_package", "Add Package") + " 1/2"

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
                        [pkg_mounting_dd, pkg_pkgtype_wrapper, pkg_pins_field, pkg_name_field, _footprint_pick_btn, fp_path_text],
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
        if _add_pkg_title_ref.current:
            _add_pkg_title_ref.current.value = s.get("add_package", "Add Package") + " 2/2"

    def _set_new_sym_centered_layout():
        if _new_sym_content_ref.current is None:
            return
        _new_sym_content_ref.current.content = ft.Container(
            expand=True,
            alignment=ft.alignment.center,
            content=ft.Column(
                [sym_name_field, sym_part_number_field, sym_parts_field, pkg_dropdown, ref_des_dropdown, sym_dup_error_text],
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
                        [sym_name_field, sym_part_number_field, sym_parts_field, pkg_dropdown, ref_des_dropdown, sym_dup_error_text],
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
        # Reset all pin IDs and names
        for pin in _fp_state["pins"]:
            pin["number"] = ""
            pin["name"]   = ""
        _refresh_canvas()
        if method in ("clockwise", "counterclockwise", "zigzag", "inline", "alphanumeric"):
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

    def _get_pin_method_opts(pkg_type: str) -> list:
        """Return the ft.dropdown.Option list for Pin Numbering Method based on package type."""
        _ALL_OPTS = {
            "manual":           ft.dropdown.Option("manual",           s.get("pin_method_manual",           "Manual")),
            "inline":           ft.dropdown.Option("inline",           s.get("pin_method_inline",           "In-line")),
            "clockwise":        ft.dropdown.Option("clockwise",        s.get("pin_method_clockwise",        "CW")),
            "counterclockwise": ft.dropdown.Option("counterclockwise", s.get("pin_method_counterclockwise", "CCW")),
            "zigzag":           ft.dropdown.Option("zigzag",           s.get("pin_method_zigzag",           "Zig-Zag")),
            "alphanumeric":     ft.dropdown.Option("alphanumeric",     s.get("pin_method_alphanumeric",     "Alphanumeric")),
        }
        _PKG_METHOD_MAP = {
            "SIP/SIL":                          ["manual", "inline"],
            "DIP/DIL":                          ["manual", "clockwise", "counterclockwise"],
            "ZIP":                              ["manual", "zigzag"],
            "PGA":                              ["manual", "alphanumeric"],
            "DO-15/DO-35/DO-41/DO-201/DO-201AD": ["manual", "inline"],
            "SOD":                              ["manual", "inline"],
            "SOT":                              ["manual", "clockwise", "counterclockwise"],
            "SOIC/SO":                          ["manual", "clockwise", "counterclockwise"],
            "TSSOP/MSOP":                       ["manual", "clockwise", "counterclockwise"],
            "QFP":                              ["manual", "clockwise", "counterclockwise"],
            "DFN":                              ["manual", "clockwise", "counterclockwise"],
            "QFN":                              ["manual", "clockwise", "counterclockwise"],
            "BGA/LBGA/FBGA":                    ["manual", "alphanumeric"],
            "WLCSP":                            ["manual", "alphanumeric"],
            "0201/0402/0603/0805/1206":         ["manual", "inline"],
        }
        methods = _PKG_METHOD_MAP.get(pkg_type, ["manual"])
        return [_ALL_OPTS[m] for m in methods if m in _ALL_OPTS]

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

        if not _fp_state["pins"] and image_path:
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
            options=_get_pin_method_opts(_selected_pkg_catalog_type.get("type", "")),
            on_change=_on_pin_method_change,
        )
        pin_method_dd_wrapper = ft.Container(
            ref=pin_method_dd_wrapper_ref,
            content=pin_method_dd,
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

        preview_column = ft.Column(
            [pin_method_dd_wrapper, hint_text, preview_stack],
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

    def _auto_number_zigzag(pin1_idx: int):
        """Zig-zag: detects layout orientation via largest gap, direction from pin1 position."""
        pins = _fp_state["pins"]
        n = len(pins)
        if n == 0:
            return
        centers = [(p["bbox_orig"][0] + p["bbox_orig"][2] / 2.0,
                    p["bbox_orig"][1] + p["bbox_orig"][3] / 2.0) for p in pins]
        xs = [c[0] for c in centers]
        ys = [c[1] for c in centers]
        p1x, p1y = centers[pin1_idx]

        # Find the axis with the largest single gap to determine split axis
        xs_s = sorted(set(xs))
        ys_s = sorted(set(ys))
        max_x_gap = max((xs_s[i+1] - xs_s[i] for i in range(len(xs_s)-1)), default=0)
        max_y_gap = max((ys_s[i+1] - ys_s[i] for i in range(len(ys_s)-1)), default=0)

        if max_x_gap >= max_y_gap:
            # Two columns (left / right): split along X at the largest gap
            split_x_idx = max(range(len(xs_s)-1), key=lambda i: xs_s[i+1] - xs_s[i])
            split_x = (xs_s[split_x_idx] + xs_s[split_x_idx + 1]) / 2
            group_a = [i for i in range(n) if centers[i][0] <= split_x]
            group_b = [i for i in range(n) if centers[i][0] >  split_x]
            if pin1_idx not in group_a:
                group_a, group_b = group_b, group_a
            # Direction: pin1 near top -> top->bottom; near bottom -> bottom->top
            a_ys = [centers[i][1] for i in group_a]
            pin1_rel = (p1y - min(a_ys)) / ((max(a_ys) - min(a_ys)) or 1)
            rev = pin1_rel > 0.5
            side_a = sorted(group_a, key=lambda i: centers[i][1], reverse=rev)
            side_b = sorted(group_b, key=lambda i: centers[i][1], reverse=rev)
        else:
            # Two rows (top / bottom): split along Y at the largest gap
            split_y_idx = max(range(len(ys_s)-1), key=lambda i: ys_s[i+1] - ys_s[i])
            split_y = (ys_s[split_y_idx] + ys_s[split_y_idx + 1]) / 2
            group_a = [i for i in range(n) if centers[i][1] <= split_y]
            group_b = [i for i in range(n) if centers[i][1] >  split_y]
            if pin1_idx not in group_a:
                group_a, group_b = group_b, group_a
            # Direction: pin1 near left -> left->right; near right -> right->left
            a_xs = [centers[i][0] for i in group_a]
            pin1_rel = (p1x - min(a_xs)) / ((max(a_xs) - min(a_xs)) or 1)
            rev = pin1_rel > 0.5
            side_a = sorted(group_a, key=lambda i: centers[i][0], reverse=rev)
            side_b = sorted(group_b, key=lambda i: centers[i][0], reverse=rev)

        # Rotate side_a so pin1 is first
        if pin1_idx in side_a:
            rot = side_a.index(pin1_idx)
            side_a = side_a[rot:] + side_a[:rot]
        # Rotate side_b to start at the pin closest to pin1
        if side_b:
            p1cx, p1cy = centers[pin1_idx]
            closest_b = min(side_b, key=lambda i: (centers[i][0]-p1cx)**2 + (centers[i][1]-p1cy)**2)
            rot_b = side_b.index(closest_b)
            side_b = side_b[rot_b:] + side_b[:rot_b]
        # Interleave: A[0], B[0], A[1], B[1], ...
        order = []
        for k in range(max(len(side_a), len(side_b))):
            if k < len(side_a):
                order.append(side_a[k])
            if k < len(side_b):
                order.append(side_b[k])
        for num, idx in enumerate(order, start=1):
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

    def _auto_number_inline(pin1_idx: int):
        """In-line: greedy nearest-neighbour walk starting from pin1."""
        pins = _fp_state["pins"]
        n = len(pins)
        if n == 0:
            return
        centers = [(p["bbox_orig"][0] + p["bbox_orig"][2] / 2.0,
                    p["bbox_orig"][1] + p["bbox_orig"][3] / 2.0) for p in pins]
        unvisited = list(range(n))
        current = pin1_idx
        unvisited.remove(current)
        order = [current]
        while unvisited:
            cx, cy = centers[current]
            nearest = min(unvisited,
                          key=lambda i: (centers[i][0]-cx)**2 + (centers[i][1]-cy)**2)
            order.append(nearest)
            unvisited.remove(nearest)
            current = nearest
        for num, idx in enumerate(order, start=1):
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
                elif method == "zigzag" and _pin_method["waiting_pin1"]:
                    _auto_number_zigzag(i)
                elif method == "inline" and _pin_method["waiting_pin1"]:
                    _auto_number_inline(i)
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
        pkg_mounting_dd.value   = None
        # Ricrea il dropdown a stato vuoto
        pkg_pkgtype_dd = ft.Dropdown(
            label=s.get("package_type", "Package Type"),
            width=280,
            options=[],
            disabled=True,
            opacity=0.5,
            on_change=_check_save_enabled,
        )
        if pkg_pkgtype_wrapper_ref.current:
            pkg_pkgtype_wrapper_ref.current.content = pkg_pkgtype_dd

    # -- Package CRUD handlers -------------------------------------------------
    def _update_next_btn_state():
        """Enable 'Next' only when all fields are populated and no duplicate (name, package)."""
        parts_str = sym_parts_field.value.strip()
        name_val  = sym_name_field.value.strip()
        pkg_val   = pkg_dropdown.value
        part_num_val = sym_part_number_field.value.strip()
        fields_ok = (
            bool(name_val) and
            bool(part_num_val) and
            (parts_str.isdigit() and int(parts_str) > 0) and
            bool(pkg_val) and
            bool(ref_des_dropdown.value)
        )
        # Check for existing (name, package) combination
        is_dup = False
        if fields_ok:
            is_dup = any(
                sym["name"] == name_val and sym.get("package", "") == pkg_val
                for sym in symbols
            )
        if is_dup:
            sym_dup_error_text.value   = s.get("sym_name_pkg_duplicate",
                "A symbol with this name and package already exists")
            sym_dup_error_text.visible = True
        else:
            sym_dup_error_text.visible = False
        all_ok = fields_ok and not is_dup
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
        # Check footprint exists before proceeding
        fp_check = pkg.get("footprint", "") if pkg else ""
        if not fp_check or not os.path.isfile(fp_check):
            dlg = ft.AlertDialog(
                title=ft.Row(
                    [
                        ft.Icon(ft.icons.ERROR_OUTLINE, color=ft.colors.RED_400, size=26),
                        ft.Text(s.get("missing_footprint_title", "Missing Footprint"),
                                weight=ft.FontWeight.BOLD),
                    ],
                    spacing=8,
                ),
                content=ft.Text(s.get("missing_footprint_body",
                    "The footprint image for this package is missing.\n"
                    "Delete the package and re-add it to restore the image.")),
                actions=[ft.TextButton(s.get("close", "Close"),
                                       on_click=lambda _: close_dlg(dlg))],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            page.open(dlg)
            return
        if _next_sym_bar_ref.current:
            _next_sym_bar_ref.current.visible = False
        if _new_sym_title_ref.current:
            _new_sym_title_ref.current.value = s.get("new_symbol", "New Symbol") + " 2/3"
        if _new_sym_subtitle_ref.current:
            _new_sym_subtitle_ref.current.value = s.get("step2_subtitle", "Define Pin Properties")
        _set_new_sym_two_col_layout()
        if pkg:
            _fp_state["pins"] = [
                {"bbox_orig": tuple(p["bbox_orig"]), "name": p.get("name", ""), "number": p.get("number", "")}
                for p in pkg.get("pins_data", [])
            ]
            fp = pkg.get("footprint", "")
            _sym_pkg_ref["footprint"] = fp
            _selected_pkg_catalog_type.update(_read_pkg_catalog_type(dname))
            _build_interactive_preview(_theme_fp_path(fp))
        if _new_sym_bottom_bar_ref.current:
            _new_sym_bottom_bar_ref.current.visible = True
        page.update()

    def _on_pkg_type_change(e):
        """Called when the user selects a package in the New Symbol dropdown."""
        _update_next_btn_state()
        # If pin_method_dd is mounted (step 2/3), rebuild it with options for the new package type
        if pin_method_dd_wrapper_ref.current and pin_method_dd_wrapper_ref.current.page:
            dname = pkg_dropdown.value
            cat = _read_pkg_catalog_type(dname) if dname else {"mount": "", "type": ""}
            # Reset pin method state
            _pin_method["value"] = None
            _pin_method["waiting_pin1"] = False
            if _pin_hint_ref.current:
                _pin_hint_ref.current.visible = False
            for pin in _fp_state["pins"]:
                pin["number"] = ""
                pin["name"]   = ""
            # Rebuild dropdown with new options
            new_dd = ft.Dropdown(
                ref=pin_method_dd_ref,
                label=s.get("select_pin_numbering", "Pin Numbering Method"),
                width=360,
                options=_get_pin_method_opts(cat.get("type", "")),
                value=None,
                on_change=_on_pin_method_change,
            )
            pin_method_dd_wrapper_ref.current.content = new_dd
            pin_method_dd_wrapper_ref.current.update()
            _refresh_canvas()
            page.update()

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
        sym_part_number_field.value = ""
        sym_parts_field.error_text   = None
        sym_parts_field.border_color = None
        pkg_dropdown.value      = None
        pkg_dropdown.options    = [ft.dropdown.Option(pkg_display_name(p)) for p in packages]
        ref_des_dropdown.value  = None
        sym_dup_error_text.visible = False
        _reset_pkg_state()
        _set_new_sym_centered_layout()
        if _new_sym_title_ref.current:
            _new_sym_title_ref.current.value = s.get("new_symbol", "New Symbol") + " 1/3"
        if _next_sym_btn_ref.current:
            _next_sym_btn_ref.current.disabled = True
            _next_sym_btn_ref.current.opacity  = 0.35
        if _next_sym_bar_ref.current:
            _next_sym_bar_ref.current.visible = True
        if _new_sym_bottom_bar_ref.current:
            _new_sym_bottom_bar_ref.current.visible = False
        _new_sym_step3_panel.visible = False
        new_sym_panel.visible   = True
        page.update()

    def _generate_symbol(e):
        """Called by the Generate Symbol button  saves the symbol and creates its folder."""
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

        # -- Struttura cartelle DEHDL symbol ----------------------------------
        dehdl_dir = sym_dir

        # chips/
        chips_dir = os.path.join(dehdl_dir, "chips")
        os.makedirs(chips_dir, exist_ok=True)

        chips_prt_path = os.path.join(chips_dir, "chips.prt")
        # Costruisce il contenuto di chips.prt
        primitive_id = f"{name}_{pkg_pin_count}PIN" if pkg_pin_count else name

        # Determina se chips.prt esiste già (stesso nome simbolo, package diverso → append)
        _chips_append = os.path.isfile(chips_prt_path)
        if _chips_append:
            with open(chips_prt_path, "r", encoding="utf-8") as _f:
                _existing_chips = _f.read()
            # Indice del nuovo PRIMITIVE (1-based)
            _prim_idx = _existing_chips.count("PRIMITIVE '") + 1
        else:
            _prim_idx = 1

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
            # In append usare _prim_idx come suffisso uniforme; altrimenti part_y
            pin_suffix = _prim_idx if _chips_append else part_y
            vec = ["0"] * num_parts
            if 1 <= part_y <= num_parts:
                vec[part_y - 1] = pin_id if pin_id else "0"
            vec_str = ",".join(vec)
            pin_lines.append(f"  'N{pin_id}-{pin_suffix}':")
            pin_lines.append(f"   PIN_NUMBER='({vec_str})';")

        pin_block = "\n".join(pin_lines) + "\n" if pin_lines else ""

        _primitive_body = (
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
        )

        if not _chips_append:
            # Scrittura completa del file
            chips_prt_content = (
                "FILE_TYPE=LIBRARY_PARTS ;\n"
                f"PRIMITIVE '{name}','{primitive_id}';\n"
                + _primitive_body
                + "END.\n"
            )
            with open(chips_prt_path, "w", encoding="utf-8") as f:
                f.write(chips_prt_content)
        else:
            # Append: rimuove "END." finale, inserisce riga vuota + nuovo PRIMITIVE
            _stripped = _existing_chips.rstrip()
            if _stripped.endswith("END."):
                _stripped = _stripped[:-len("END.")].rstrip()
            _append_block = (
                f"\nPRIMITIVE '{primitive_id}';\n"
                + _primitive_body
                + "END.\n"
            )
            with open(chips_prt_path, "w", encoding="utf-8") as f:
                f.write(_stripped + "\n" + _append_block)

        # Crea master.tag con il contenuto 'chips.prt' nella stessa directory
        with open(os.path.join(chips_dir, "master.tag"), "w", encoding="utf-8") as f:
            f.write("chips.prt")

        # part_table/part.ptf
        part_name_val   = sym_name_field.value.strip()
        part_number_val = sym_part_number_field.value.strip()
        package_id_val  = pkg_dropdown.value or ""
        pack_type_val   = f"{pkg_pin_count}PIN" if pkg_pin_count else "0PIN"
        part_table_dir  = os.path.join(dehdl_dir, "part_table")
        os.makedirs(part_table_dir, exist_ok=True)
        part_ptf_path   = os.path.join(part_table_dir, "part.ptf")
        if not os.path.isfile(part_ptf_path):
            part_ptf_content = (
                "FILE_TYPE = MULTI_PHYS_TABLE;\n"
                "\n"
                f"PART '{part_name_val}'\n"
                "CLASS = IC\n"
                "\n"
                "{==========================================================}\n"
                ":PACK_TYPE | VALUE | PACKAGE_TYPE ; \n"
                "{==========================================================}\n"
                f" '{pack_type_val}' | '{part_number_val}' | '{package_id_val}'\n"
                "\n"
                "END_PART\n"
                "\n"
                "END.\n"
            )
            with open(part_ptf_path, "w", encoding="utf-8") as f:
                f.write(part_ptf_content)

        # sym_1  sym_N/
        for part_num in range(1, num_parts + 1):
            sym_part_dir = os.path.join(dehdl_dir, f"sym_{part_num}")
            os.makedirs(sym_part_dir, exist_ok=True)
            with open(os.path.join(sym_part_dir, "master.tag"), "w", encoding="utf-8") as f:
                f.write("symbol.css")
            # Build symbol.css (Allegro DEHDL format)
            part_pins = [
                (i, p) for i, p in enumerate(pins)
                if str(p.get("part_number", "1")) == str(part_num)
            ]
            left_pins_s  = [(i, p) for i, p in part_pins
                            if _sym_pin_layout.get(str(i), {}).get("side", "left") == "left"]
            right_pins_s  = [(i, p) for i, p in part_pins
                            if _sym_pin_layout.get(str(i), {}).get("side", "left") == "right"]
            top_pins_s    = [(i, p) for i, p in part_pins
                            if _sym_pin_layout.get(str(i), {}).get("side", "left") == "top"]
            bottom_pins_s = [(i, p) for i, p in part_pins
                            if _sym_pin_layout.get(str(i), {}).get("side", "left") == "bottom"]

            # Use ordered positions from _sym_pin_order if available
            def _ordered(lst, side):
                pkey = str(part_num)
                if pkey in _sym_pin_order and side in _sym_pin_order[pkey]:
                    order   = _sym_pin_order[pkey][side]
                    pin_map = {i: p for i, p in lst}
                    return [(i, pin_map[i]) for i in order if i in pin_map]
                return lst

            left_pins_s   = _ordered(left_pins_s,   "left")
            right_pins_s  = _ordered(right_pins_s,  "right")
            top_pins_s    = _ordered(top_pins_s,    "top")
            bottom_pins_s = _ordered(bottom_pins_s, "bottom")

            # ── DEHDL coordinate conversion ─────────────────────────────────────
            # Symbol Grid: Size 0.05 in × Multiple 4 = 0.20 in = 200 mils per
            # canvas grid step (_SYM_GRID px).  Logic Grid: 0.05 × 5 = 250 mils.
            _DEHDL_MIL_PER_STEP = 100  # mils per _SYM_GRID canvas pixels

            # Recompute body layout for this part (mirrors _build_sym_shapes)
            _n_lr_g  = max(len(left_pins_s), len(right_pins_s), 1)
            _n_tb_g  = max(len(top_pins_s),  len(bottom_pins_s), 1)
            _auto_bh = int(round((_n_lr_g * _SYM_PIN_SPACING + 2 * _SYM_PAD_Y) / _SYM_GRID) * _SYM_GRID)
            _auto_bw = int(round(max(_SYM_BODY_W, _n_tb_g * _SYM_PIN_SPACING + 2 * _SYM_PAD_X) / _SYM_GRID) * _SYM_GRID)
            _bsz_g   = _sym_body_size.get(str(part_num), {})
            _body_h  = max(_SYM_GRID, int(round(_bsz_g.get("h", _auto_bh) / _SYM_GRID) * _SYM_GRID))
            _body_w  = max(_SYM_GRID, int(round(_bsz_g.get("w", _auto_bw) / _SYM_GRID) * _SYM_GRID))
            _cx_g    = _sym_editor_state.get("canvas_w", _SYM_CANVAS_W) / 2
            _body_l  = int(round((_cx_g - _body_w / 2) / _SYM_GRID) * _SYM_GRID)
            _body_r  = _body_l + _body_w
            _body_top = int(round((_SYM_PIN_STUB + 44) / _SYM_GRID) * _SYM_GRID)
            _body_bot = _body_top + _body_h

            def _snp_g(v): return int(round(v / _SYM_GRID) * _SYM_GRID)
            def _mx(cx):   return int(round((cx - _body_l) / _SYM_GRID)) * _DEHDL_MIL_PER_STEP
            def _my(cy):   return int(round((_body_bot - cy) / _SYM_GRID)) * _DEHDL_MIL_PER_STEP

            _bw_mil = _mx(_body_r)    # body width in mils
            _bh_mil = _my(_body_top)  # body height in mils

            def _gpos_g(pin_idx, side, row_or_col):
                """Return snapped canvas (gx, gy) for a pin, matching _build_sym_shapes."""
                layout = _sym_pin_layout.get(str(pin_idx), {})
                if "gx" in layout and "gy" in layout:
                    return _snp_g(layout["gx"]), _snp_g(layout["gy"])
                if side == "left":
                    return (_snp_g(_body_l - _SYM_PIN_STUB),
                            _snp_g(_body_top + _SYM_PAD_Y + row_or_col * _SYM_PIN_SPACING))
                if side == "right":
                    return (_snp_g(_body_r + _SYM_PIN_STUB),
                            _snp_g(_body_top + _SYM_PAD_Y + row_or_col * _SYM_PIN_SPACING))
                if side == "top":
                    return (_snp_g(_body_l + _SYM_PAD_X + row_or_col * _SYM_PIN_SPACING),
                            _snp_g(_body_top - _SYM_PIN_STUB))
                # bottom
                return (_snp_g(_body_l + _SYM_PAD_X + row_or_col * _SYM_PIN_SPACING),
                        _snp_g(_body_bot + _SYM_PIN_STUB))

            # Body edges (4 lines, origin at body bottom-left, Y upward)
            l_lines = [
                f"L 0 {_bh_mil} 0 0 -1 74\n",
                f"L 0 {_bh_mil} {_bw_mil} {_bh_mil} -1 74\n",
                f"L 0 0 {_bw_mil} 0 -1 74\n",
                f"L {_bw_mil} {_bh_mil} {_bw_mil} 0 -1 74\n",
            ]

            # Pin stubs + T text for pin name (inside body, centered on stub)
            _TEXT_OFFSET = _DEHDL_MIL_PER_STEP // 4   # 25 mils from body edge
            _STUB_MIL    = _DEHDL_MIL_PER_STEP         # stub length in mils
            # Overbar (Active Low) metrics — grid: Size=0.002in × Multiple=4 → 1 step = 8 mils
            _OB_STEP     = 8                                    # 1 Allegro grid step in mils
            _OB_CHAR_W   = 7 * _OB_STEP                        # per-char slope = 7 steps = 56 mils  (calibrated)
            _OB_CHAR_OFF = 3 * _OB_STEP                        # fixed offset   = 3 steps = 24 mils  tw=(7N-3)×8
            _OB_T_HEIGHT = 6 * _OB_STEP                        # T text height = 6 steps = 48 mils (= T size field)
            _OB_GAP      = 1 * _OB_STEP                        # overbar gap   = 1 step  =  8 mils above text top
            # overbar width = (7N-3)×8 mils  — cal: N=1→32, N=3→144, N=5→256, N=6→312, N=7→368
            t_lines  = []
            cx_lines = []
            for _pins_list, _side in (
                (left_pins_s,   "left"),
                (right_pins_s,  "right"),
                (top_pins_s,    "top"),
                (bottom_pins_s, "bottom"),
            ):
                for _row, (_pi, _pp) in enumerate(_pins_list):
                    _gx, _gy = _gpos_g(_pi, _side, _row)
                    if _side == "left":
                        _bx, _by = _body_l, _gy
                    elif _side == "right":
                        _bx, _by = _body_r, _gy
                    elif _side == "top":
                        _bx, _by = _gx, _body_top
                    else:
                        _bx, _by = _gx, _body_bot
                    _x1, _y1 = _mx(_gx), _my(_gy)
                    _x2, _y2 = _mx(_bx), _my(_by)
                    l_lines.append(f"L {_x1} {_y1} {_x2} {_y2} -1 74\n")

                    # T instructions: pin name inside body
                    # Format A: T X Y AngleX 0.00 48 0 0 0 0 FontStyle 74  (all sides)
                    # Format B: T X Y 0.00 0.00 0 0 0 2 0 FontStyle 74     (left/right only)
                    _pname = _pp.get("name", "")
                    _pnum  = _pp.get("number", "")
                    if _pname:
                        _negated = _pp.get("negated", False)
                        _fs = 2 if _negated else 3
                        _y_delta = 20  # mils below pin_y for Format A baseline
                        if _side == "left":
                            _tx_a, _ty_a, _ax = _TEXT_OFFSET, _y1 - _y_delta, 0.0
                            _tx_b, _ty_b       = _TEXT_OFFSET, _y1
                        elif _side == "right":
                            _tx_a = _bw_mil - (3 * _DEHDL_MIL_PER_STEP // 2)
                            _ty_a, _ax         = _y1 - _y_delta, 0.0
                            _tx_b, _ty_b       = _bw_mil - _TEXT_OFFSET, _y1
                        elif _side == "top":
                            _tx_a, _ty_a, _ax  = _x1 + _y_delta, _bh_mil - _TEXT_OFFSET, 90.0
                        else:  # bottom
                            _tx_a, _ty_a, _ax  = _x1 + _y_delta, _TEXT_OFFSET, 90.0
                        # Format A (all sides)
                        t_lines.append(
                            f"T {_tx_a} {_ty_a} {_ax:.2f} 0.00 48 0 0 0 0 {_fs} 74\n"
                            f"{_pname}\n"
                        )
                        # Overbar (Active Low): full width = N×40mils; pos = baseline + T_height + 2-step gap
                        if _negated:
                            _ob_n  = len(_pname)
                            _ob_tw = max(_ob_n * _OB_CHAR_W - _OB_CHAR_OFF, _OB_STEP)  # (7N-3)×8 mils
                            if _side in ("left", "right"):
                                # overbar = baseline + T_height(48) + 2-step gap(16)
                                _ob_y = _ty_a + _OB_T_HEIGHT + _OB_GAP
                                l_lines.append(f"L {_tx_a} {_ob_y} {_tx_a + _ob_tw} {_ob_y} -1 74\n")
                            else:
                                # Rotated 90° CCW: vertical line, 2 steps to the left of text top
                                _ob_x = _tx_a - _OB_T_HEIGHT - _OB_GAP
                                l_lines.append(f"L {_ob_x} {_ty_a} {_ob_x} {_ty_a + _ob_tw} -1 74\n")
                        # Format B (left/right only)
                        if _side in ("left", "right"):
                            t_lines.append(
                                f"T {_tx_b} {_ty_b} 0.00 0.00 0 0 0 2 0 {_fs} 74\n"
                                f"{_pname}\n"
                            )

                    # C + X instructions: DOT at external pin tip with $PN and PIN_NAME attributes
                    # $PN "?" appears above the stub line; PIN_NAME appears near the dot on the line
                    if _pnum or _pname:
                        _clabel = f"N{_pnum}-{part_num}\\NAC"
                        _mid_stub_x = (_x1 + _x2) // 2
                        _mid_stub_y = (_y1 + _y2) // 2
                        if _side == "left":
                            # C label: to the left of dot, L-justified, rot=0
                            _cl_x, _cl_y, _cl_rot, _cl_f, _cl_just = _x1 - _STUB_MIL, _y1 - 10, 0, 0, "L"
                            # $PN on stub, right-aligned toward body (just=2)
                            _pn_x, _pn_y, _pn_just = _mid_stub_x, _y1 + 20, 2
                            # PIN_NAME near the dot
                            _pnm_x, _pnm_y, _pnm_just = _x1 + 10, _y1, 4
                        elif _side == "right":
                            # C label: to the right of dot, L-justified, rot=0 (matches reference)
                            _cl_x, _cl_y, _cl_rot, _cl_f, _cl_just = _x1 + 15, _y1 - 10, 0, 0, "L"
                            # $PN on stub, left-aligned toward body (just=0)
                            _pn_x, _pn_y, _pn_just = _mid_stub_x, _y1 + 20, 0
                            # PIN_NAME near the dot
                            _pnm_x, _pnm_y, _pnm_just = _x1 - 10, _y1, 6
                        elif _side == "top":
                            # C label: just above dot, L-justified, rot=0, field9=1 (matches reference)
                            _cl_x, _cl_y, _cl_rot, _cl_f, _cl_just = _x1 + 10, _y1 + 15, 0, 1, "L"
                            # $PN below dot (toward body), left-aligned
                            _pn_x, _pn_y, _pn_just = _x1 - 20, _y1 - 25, 0
                            # PIN_NAME near the dot
                            _pnm_x, _pnm_y, _pnm_just = _x1, _y1 - 10, 0
                        else:  # bottom
                            # C label: well below dot, L-justified, rot=0, field9=1 (matches reference)
                            _cl_x, _cl_y, _cl_rot, _cl_f, _cl_just = _x1 + 10, _y1 - 215, 0, 1, "L"
                            # $PN above dot (toward body), left-aligned
                            _pn_x, _pn_y, _pn_just = _x1 - 20, _y1 + 15, 0
                            # PIN_NAME near the dot
                            _pnm_x, _pnm_y, _pnm_just = _x1, _y1 + 10, 0
                        cx_lines.append(
                            f'C {_x1} {_y1} "{_clabel}" {_cl_x} {_cl_y} {_cl_rot} 1 48 {_cl_f} {_cl_just}\n'
                            f'X "$PN" "?" {_pn_x} {_pn_y} 0.00 0.00 31 0 0 {_pn_just} 0 0 1 0 74\n'
                        )

            _p_lines = (
                'P "CATEGORY" "?" 360 545 0.00 0.00 36 0 0 1 0 0 0 0 0\n'
                'P "VOLTAGE" "?" 360 245 0.00 0.00 36 0 0 1 0 0 0 0 74\n'
                'P "TOLERANCE" "?" 360 145 0.00 0.00 36 0 0 1 0 0 0 0 74\n'
                'P "PACK_TYPE" "?" 360 -355 0.00 0.00 36 0 0 1 0 0 0 0 74\n'
                'P "PATH" "?" 360 -255 0.00 0.00 36 0 0 1 0 0 0 0 74\n'
                'P "COLOR" "?" 360 -155 0.00 0.00 36 0 0 1 0 0 0 0 74\n'
                'P "WATTAGE" "?" 360 -55 0.00 0.00 36 0 0 1 0 0 0 0 74\n'
                'P "TYPE" "?" 360 645 0.00 0.00 36 0 0 1 0 0 0 0 0\n'
                'P "TECHNOLOGY" "?" 360 845 0.00 0.00 36 0 0 1 0 0 0 0 0\n'
                'P "SUPPLIER" "?" 360 745 0.00 0.00 36 0 0 1 0 0 0 0 0\n'
                'P "VALUE" "?" 300 975 0.00 0.00 36 0 0 1 0 0 1 0 74\n'
                'P "$LOCATION" "?" 300 1025 0.00 0.00 36 0 0 1 0 0 1 0 74\n'
            )
            css_content = "".join(cx_lines) + "".join(l_lines) + "".join(t_lines) + _p_lines

            with open(os.path.join(sym_part_dir, "symbol.css"), "w", encoding="utf-8") as f:
                f.write(css_content)

        entry = {
            "name":    name,
            "parts":   num_parts,
            "package": package_type,
            "folder":  sym_dir,
        }
        existing = next(
            (i for i, s_ in enumerate(symbols)
             if s_["name"] == name and s_.get("package", "") == package_type),
            None,
        )
        if existing is not None:
            symbols[existing] = entry
        else:
            symbols.append(entry)
        save_symbols(symbols)
        symbols[:] = load_symbols()
        new_sym_panel.visible = False
        _new_sym_step3_panel.visible = False
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
        del_sym_dd.options = [ft.dropdown.Option(n) for n in dict.fromkeys(s_["name"] for s_ in symbols)]
        del_sym_dd.value   = None
        new_sym_panel.visible  = False
        _new_sym_step3_panel.visible = False
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
        _new_sym_step3_panel.visible = False
        del_pkg_panel.visible      = False
        del_sym_panel.visible      = False
        sym_list_panel.visible     = False
        pkg_list_panel.visible     = False
        search_pkg_panel.visible   = False
        _reset_pkg_state()
        _set_centered_layout()
        add_pkg_panel.visible      = True
        page.update()
        if _add_pkg_title_ref.current:
            _add_pkg_title_ref.current.value = s.get("add_package", "Add Package") + " 1/2"
        if _bottom_bar_ref.current:
            _bottom_bar_ref.current.visible = False
        add_pkg_panel.visible = True
        _check_save_enabled()
        page.update()

    # -- Catalogo PackagesCatalog in packages.db ------------------------------
    def _upsert_packages_catalog(name, pins, mount, pkg_type):
        import sqlite3 as _sqlite3
        from datetime import datetime as _dt
        pkg_id = f"{name}-{pins}"
        now    = _dt.now().strftime("%d/%m/%y %H:%M:%S")
        with _sqlite3.connect(_cfg_mod.PACKAGES_DB) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS PackagesCatalog ("
                "ID TEXT PRIMARY KEY, Name TEXT, NumPins INTEGER, "
                "Mount TEXT, Type TEXT, Created TEXT)"
            )
            try:
                conn.execute("ALTER TABLE PackagesCatalog ADD COLUMN Created TEXT")
            except Exception:
                pass
            conn.execute(
                "INSERT OR IGNORE INTO PackagesCatalog "
                "(ID, Name, NumPins, Mount, Type, Created) VALUES (?, ?, ?, ?, ?, ?)",
                (pkg_id, name, pins, mount, pkg_type, now),
            )
            conn.execute(
                "UPDATE PackagesCatalog SET Name=?, NumPins=?, Mount=?, Type=? WHERE ID=?",
                (name, pins, mount, pkg_type, pkg_id),
            )

    def _delete_packages_catalog(name, pins):
        import sqlite3 as _sqlite3
        pkg_id = f"{name}-{pins}"
        try:
            with _sqlite3.connect(_cfg_mod.PACKAGES_DB) as conn:
                conn.execute(
                    "DELETE FROM PackagesCatalog WHERE ID = ?", (pkg_id,)
                )
        except Exception:
            pass

    def _read_pkg_catalog_type(pkg_id: str):
        """Returns {"mount": str, "type": str} for the given Package ID."""
        import sqlite3 as _sqlite3
        try:
            with _sqlite3.connect(_cfg_mod.PACKAGES_DB) as conn:
                row = conn.execute(
                    "SELECT Mount, Type FROM PackagesCatalog WHERE ID = ?",
                    (pkg_id,),
                ).fetchone()
            if row:
                return {"mount": row[0] or "", "type": row[1] or ""}
        except Exception:
            pass
        return {"mount": "", "type": ""}

    def save_package(_):
        name     = pkg_name_field.value.strip()
        pins_str = pkg_pins_field.value.strip()
        if not name or not (pins_str.isdigit() and int(pins_str) > 0):
            return
        pins     = int(pins_str)
        mount    = pkg_mounting_dd.value or ""
        pkg_type = pkg_pkgtype_dd.value or ""
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
        _upsert_packages_catalog(name, pins, mount, pkg_type)
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
        _new_sym_step3_panel.visible = False
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
        _new_sym_step3_panel.visible = False
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
        fp_path  = pkg.get("footprint", "")
        pkg_name = pkg.get("name", "")
        pkg_pins = pkg.get("pins", 0)
        packages[:] = [p for p in packages if pkg_display_name(p) != dname]
        save_packages(packages)
        packages[:] = load_packages()
        _delete_packages_catalog(pkg_name, pkg_pins)
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

    def show_symbols(e):
        new_sym_panel.visible  = False
        _new_sym_step3_panel.visible = False
        add_pkg_panel.visible  = False
        del_pkg_panel.visible  = False
        del_sym_panel.visible  = False
        pkg_list_panel.visible = False
        search_pkg_panel.visible = False

        def _build_sym_rows(filter_text=""):
            ft_lower = filter_text.strip().lower()
            filtered = [sym for sym in symbols if ft_lower in sym["name"].lower()] if ft_lower else symbols

            if not filtered:
                return [
                    ft.Text(s.get("no_symbols", "No symbols created yet."), italic=True),
                    ft.TextButton(
                        s.get("close", "Close"),
                        on_click=lambda _: (setattr(sym_list_panel, "visible", False), page.update()),
                    ),
                ]

            # Group by name
            groups: dict = {}
            for sym in filtered:
                groups.setdefault(sym["name"], []).append(sym)

            rows = []
            for sym_name_key, entries in groups.items():
                pkg_rows = []
                for sym in entries:
                    pkg_rows.append(
                        ft.Text(
                            f"  • {s.get('package_type', 'Package')}: {sym.get('package', '')}  ¦  "
                            f"{s.get('created_at_label', 'Created')}: {sym.get('created_at', '')}",
                            size=11, italic=True, color=ft.colors.GREY_500,
                        )
                    )
                rows.append(
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Row(
                                    [ft.Icon(ft.icons.CATEGORY, size=16),
                                     ft.Text(sym_name_key, size=13,
                                             weight=ft.FontWeight.W_500, expand=True)],
                                    spacing=8,
                                ),
                                *pkg_rows,
                            ],
                            spacing=2,
                        ),
                        border_radius=ft.border_radius.all(6),
                        padding=ft.padding.symmetric(horizontal=8, vertical=4),
                    )
                )
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

    # \u2500\u2500 Delete Symbol dropdown + confirm button ref \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
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

    # ── Symbol editor helpers (Step 3) ─────────────────────────────────────

    def _show_sym_pin_layout_dialog(pin_idx: int, part_num: int):
        """Dialog to change the side (left/right/top/bottom) of a pin."""
        pin = _fp_state["pins"][pin_idx]
        key = str(pin_idx)
        cur = _sym_pin_layout.get(key, {"side": "left"})

        side_dd = ft.Dropdown(
            label=s.get("pin_side", "Side"),
            width=220,
            value=cur["side"],
            options=[
                ft.dropdown.Option("left",   s.get("left",   "Left")),
                ft.dropdown.Option("right",  s.get("right",  "Right")),
                ft.dropdown.Option("top",    s.get("top",    "Top")),
                ft.dropdown.Option("bottom", s.get("bottom", "Bottom")),
            ],
        )

        def _on_save(_):
            new_side = side_dd.value or "left"
            old_side = cur["side"]
            if new_side == old_side:
                # Preserve grid position; only update side key
                _sym_pin_layout.setdefault(key, {})["side"] = new_side
            else:
                # Clear gx/gy so the pin reinitialises at the default position for the new side
                _sym_pin_layout[key] = {"side": new_side}
                pkey = str(part_num)
                if pkey in _sym_pin_order:
                    try:
                        _sym_pin_order[pkey][old_side].remove(pin_idx)
                    except (ValueError, KeyError):
                        pass
                    _sym_pin_order[pkey].setdefault(new_side, [])
                    if pin_idx not in _sym_pin_order[pkey][new_side]:
                        _sym_pin_order[pkey][new_side].append(pin_idx)
            page.close(dlg)
            _refresh_sym_editor(part_num)

        pin_label = f"Pin {pin.get('number', pin_idx + 1)}"
        if pin.get("name"):
            pin_label += f"  –  {pin['name']}"

        dlg = ft.AlertDialog(
            title=ft.Text(pin_label, weight=ft.FontWeight.BOLD),
            content=side_dd,
            actions=[
                ft.TextButton(s.get("close", "Cancel"), on_click=lambda _: page.close(dlg)),
                ft.ElevatedButton(s.get("save", "Save"), on_click=_on_save),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.open(dlg)

    # ── Symbol editor: order helpers ────────────────────────────────────────

    def _init_sym_pin_order(part_num: int):
        """Ensure _sym_pin_order[part] has all 4 sides consistent with current pin data."""
        key = str(part_num)
        if key not in _sym_pin_order:
            _sym_pin_order[key] = {s: [] for s in _SYM_SIDES}
        for side in _SYM_SIDES:
            _sym_pin_order[key].setdefault(side, [])
            current_ids = [
                i for i, p in enumerate(_fp_state["pins"])
                if str(p.get("part_number", "1")) == str(part_num)
                and _sym_pin_layout.get(str(i), {}).get("side", "left") == side
            ]
            stored = _sym_pin_order[key][side]
            current_set = set(current_ids)
            new_order = [i for i in stored if i in current_set]
            for i in current_ids:
                if i not in set(new_order):
                    new_order.append(i)
            _sym_pin_order[key][side] = new_order

    def _get_ordered_pins(part_num: int, side: str):
        """Return [(pin_idx, pin)] in the stored drag order for part+side."""
        _init_sym_pin_order(part_num)
        order = _sym_pin_order[str(part_num)][side]
        pin_map = {
            i: p for i, p in enumerate(_fp_state["pins"])
            if str(p.get("part_number", "1")) == str(part_num)
            and _sym_pin_layout.get(str(i), {}).get("side", "left") == side
        }
        return [(i, pin_map[i]) for i in order if i in pin_map]

    # ── Symbol editor: shapes builder (4 sides) ─────────────────────────────

    def _build_sym_shapes(part_num: int, drag_idx=None, drag_x=None, drag_y=None):
        """Return (shapes, canvas_h) – grid-based pin placement with snap."""
        left_pins   = _get_ordered_pins(part_num, "left")
        right_pins  = _get_ordered_pins(part_num, "right")
        top_pins    = _get_ordered_pins(part_num, "top")
        bottom_pins = _get_ordered_pins(part_num, "bottom")

        n_lr  = max(len(left_pins), len(right_pins), 1)
        n_tb  = max(len(top_pins),  len(bottom_pins), 1)

        auto_h = int(round((n_lr * _SYM_PIN_SPACING + 2 * _SYM_PAD_Y) / _SYM_GRID) * _SYM_GRID)
        auto_w = int(round(max(_SYM_BODY_W, n_tb * _SYM_PIN_SPACING + 2 * _SYM_PAD_X) / _SYM_GRID) * _SYM_GRID)
        _bsz   = _sym_body_size.get(str(part_num), {})
        body_h = max(_SYM_GRID, int(round(_bsz.get("h", auto_h) / _SYM_GRID) * _SYM_GRID))
        body_w = max(_SYM_GRID, int(round(_bsz.get("w", auto_w) / _SYM_GRID) * _SYM_GRID))

        canvas_h = body_h + _SYM_PIN_STUB * 2 + 80   # provisional; recalculated after _gpos is defined
        canvas_w = _sym_editor_state.get("canvas_w", _SYM_CANVAS_W)

        cx       = canvas_w / 2
        body_l   = int(round((cx - body_w / 2) / _SYM_GRID) * _SYM_GRID)
        body_r   = body_l + body_w
        body_top = int(round((_SYM_PIN_STUB + 44) / _SYM_GRID) * _SYM_GRID)
        body_bot = body_top + body_h

        is_dark  = True   # canvas always uses dark background
        text_col = ft.colors.WHITE   # pin names
        pnum_col = ft.colors.WHITE   # pin IDs
        pin_col  = ft.colors.CYAN_300

        # ── Snap helper ──
        def _snap(v):
            return int(round(v / _SYM_GRID) * _SYM_GRID)

        # ── Get (or lazily initialise) grid position for a pin ──
        def _gpos(pin_idx, side, row_or_col):
            layout = _sym_pin_layout.get(str(pin_idx), {})
            if "gx" in layout and "gy" in layout:
                # Always re-snap in case the value was stored off-grid
                gx = _snap(layout["gx"])
                gy = _snap(layout["gy"])
                # Enforce pin stays strictly outside the body on its assigned side
                if side == "left"   and gx >= body_l:   gx = _snap(body_l - _SYM_GRID)
                elif side == "right"  and gx <= body_r:   gx = _snap(body_r + _SYM_GRID)
                elif side == "top"    and gy >= body_top: gy = _snap(body_top - _SYM_GRID)
                elif side == "bottom" and gy <= body_bot: gy = _snap(body_bot + _SYM_GRID)
                if gx != layout["gx"] or gy != layout["gy"]:
                    _sym_pin_layout[str(pin_idx)].update({"gx": gx, "gy": gy})
                return gx, gy
            if side == "left":
                gx = _snap(body_l - _SYM_PIN_STUB)
                gy = _snap(body_top + _SYM_PAD_Y + row_or_col * _SYM_PIN_SPACING)
            elif side == "right":
                gx = _snap(body_r + _SYM_PIN_STUB)
                gy = _snap(body_top + _SYM_PAD_Y + row_or_col * _SYM_PIN_SPACING)
            elif side == "top":
                gx = _snap(body_l + _SYM_PAD_X + row_or_col * _SYM_PIN_SPACING)
                gy = _snap(body_top - _SYM_PIN_STUB)
            else:
                gx = _snap(body_l + _SYM_PAD_X + row_or_col * _SYM_PIN_SPACING)
                gy = _snap(body_bot + _SYM_PIN_STUB)
            _sym_pin_layout.setdefault(str(pin_idx), {}).update({"gx": gx, "gy": gy})
            return gx, gy

        # ── Nearest body-edge side for a given (gx, gy) ──
        def _pos_side(gx, gy):
            dists = [
                (body_l - gx, "left"),
                (gx - body_r, "right"),
                (body_top - gy, "top"),
                (gy - body_bot, "bottom"),
            ]
            valid = [(d, sd) for d, sd in dists if d > 0]
            if not valid:
                valid = [(abs(d), sd) for d, sd in dists]
            return min(valid)[1]

        # ── Pre-scan all pin positions to set canvas_h dynamically ──
        # Runs here, after _gpos/_snap/_pos_side are defined.
        # _gpos is idempotent: the draw loop below will reuse cached positions.
        _all_ys = [body_top, body_bot]
        for _r, (_pi, _) in enumerate(left_pins):
            _, _gy = _gpos(_pi, "left",   _r); _all_ys.append(_gy)
        for _r, (_pi, _) in enumerate(right_pins):
            _, _gy = _gpos(_pi, "right",  _r); _all_ys.append(_gy)
        for _c, (_pi, _) in enumerate(top_pins):
            _, _gy = _gpos(_pi, "top",    _c); _all_ys.append(_gy)
        for _c, (_pi, _) in enumerate(bottom_pins):
            _, _gy = _gpos(_pi, "bottom", _c); _all_ys.append(_gy)
        canvas_h = int(round((max(_all_ys) + _SYM_PIN_STUB + 40) / _SYM_GRID)) * _SYM_GRID

        shapes: list    = []
        hit_areas: list = []   # [(x1,y1,x2,y2, pin_idx, side, row)]

        # ── Grid lines ──
        grid_c = ft.colors.with_opacity(0.70, ft.colors.GREY_300)
        for gx_g in range(0, int(canvas_w) + _SYM_GRID, _SYM_GRID):
            shapes.append(cv.Line(gx_g, 0, gx_g, int(canvas_h),
                paint=Paint(color=grid_c, stroke_width=0.5)))
        for gy_g in range(0, int(canvas_h) + _SYM_GRID, _SYM_GRID):
            shapes.append(cv.Line(0, gy_g, int(canvas_w), gy_g,
                paint=Paint(color=grid_c, stroke_width=0.5)))

        # ── Body ──
        shapes.append(cv.Rect(body_l, body_top, body_w, body_h,
            paint=Paint(
                color=ft.colors.with_opacity(0.04, ft.colors.BLUE_200),
                style=PaintingStyle.FILL)))
        shapes.append(cv.Rect(body_l, body_top, body_w, body_h,
            paint=Paint(color=ft.colors.BLUE_300, stroke_width=2,
                        style=PaintingStyle.STROKE)))

        # ── SE resize handle ──
        _rh = 8
        shapes.append(cv.Rect(body_r - _rh, body_bot - _rh, _rh * 2, _rh * 2,
            paint=Paint(color=ft.colors.BLUE_400, style=PaintingStyle.FILL)))
        hit_areas.append((body_r - _rh - 6, body_bot - _rh - 6,
                          body_r + _rh + 6, body_bot + _rh + 6, "resize", "se", None))

        # ── Snap-point cursor during drag ──
        if drag_idx is not None and drag_x is not None and drag_y is not None:
            sx, sy = _snap(drag_x), _snap(drag_y)
            shapes.append(cv.Circle(sx, sy, 10,
                paint=Paint(color=ft.colors.with_opacity(0.35, ft.colors.YELLOW_400),
                            style=PaintingStyle.FILL)))
            shapes.append(cv.Circle(sx, sy, 10,
                paint=Paint(color=ft.colors.YELLOW_400, stroke_width=2,
                            style=PaintingStyle.STROKE)))

        # ── Centre labels ──
        center_y = body_top + body_h / 2
        shapes.append(cv.Text(cx, center_y - 14,
            f"{ref_des_dropdown.value or 'REFDES'}?",
            style=ft.TextStyle(size=12, color=ft.colors.ORANGE_300, weight=ft.FontWeight.BOLD),
            alignment=ft.alignment.bottom_center, text_align=ft.TextAlign.CENTER,
            max_width=body_w - 8))
        shapes.append(cv.Text(cx, center_y + 2,
            sym_name_field.value.strip() or "Symbol",
            style=ft.TextStyle(size=14, color=ft.colors.ORANGE_300, weight=ft.FontWeight.BOLD),
            alignment=ft.alignment.top_center, text_align=ft.TextAlign.CENTER,
            max_width=body_w - 8))

        # ── Unified pin draw (stub from gx/gy tip to body edge) ──
        def _draw_pin(pin_idx, pin, gx, gy, side, row_or_col):
            is_ghost  = (pin_idx == drag_idx)
            px        = _snap(drag_x) if is_ghost and drag_x is not None else gx
            py        = _snap(drag_y) if is_ghost and drag_y is not None else gy
            act_side  = _pos_side(px, py) if is_ghost else side
            pcolor    = ft.colors.YELLOW_400 if is_ghost else pin_col
            sw        = 3 if is_ghost else 2
            neg       = pin.get("negated", False)
            pname     = pin.get("name", "")
            pnum      = pin.get("number", "")
            _ps12     = ft.TextStyle(size=12, color=text_col)
            _ob_paint = Paint(color=text_col, stroke_width=1.5)
            # ── Per-character width lookup — proportional font, size 12 ──────────
            # Tune each uppercase letter individually; default fallback = 7 px
            _CW12 = {
                # ── uppercase ──────────────────────────────────────────────────
                'A': 8, 'B': 7, 'C': 7, 'D': 8, 'E': 7, 'F': 6, 'G': 8,
                'H': 8, 'I': 4, 'J': 5, 'K': 8, 'L': 6, 'M':11, 'N': 9,
                'O': 9, 'P': 7, 'Q': 9, 'R': 7, 'S': 6, 'T': 6, 'U': 6,
                'V': 8, 'W':11, 'X': 7, 'Y': 7, 'Z': 7,
                # ── lowercase ──────────────────────────────────────────────────
                'a': 6, 'b': 7, 'c': 6, 'd': 7, 'e': 6, 'f': 4, 'g': 7,
                'h': 7, 'i': 3, 'j': 3, 'k': 6, 'l': 3, 'm':10, 'n': 7,
                'o': 7, 'p': 7, 'q': 7, 'r': 4, 's': 5, 't': 4, 'u': 7,
                'v': 6, 'w': 9, 'x': 6, 'y': 6, 'z': 5,
                # ── digits & symbols ───────────────────────────────────────────
                '0': 6, '1': 6, '2': 6, '3': 6, '4': 6, '5': 6, '6': 6,
                '7': 6, '8': 6, '9': 6,
                '_': 5, '-': 5, '.': 3, ',': 3, ':': 3, ';': 3, '/': 5,
            }
            def _tw12(s): return sum(_CW12.get(c, 7) for c in s)

            if act_side == "left":
                ix = body_l
                shapes.append(cv.Line(px, py, ix, py, paint=Paint(color=pcolor, stroke_width=sw)))
                shapes.append(cv.Text(ix + 3, py - 14, pnum,
                    style=ft.TextStyle(size=10, color=pnum_col),
                    alignment=ft.alignment.top_left, max_width=40))
                shapes.append(cv.Text(px - 2, py - 15, pname,
                    style=_ps12,
                    alignment=ft.alignment.top_right, text_align=ft.TextAlign.RIGHT,
                    max_width=max(int(px) - 4, 4)))
                if neg and pname:
                    _tw = _tw12(pname)
                    shapes.append(cv.Line(px - 2 - _tw, py - 16, px - 2, py - 16, paint=_ob_paint))
                if not is_ghost:
                    hit_areas.append((px - 8, py - 18, ix + 8, py + 26, pin_idx, side, row_or_col))
            elif act_side == "right":
                ix = body_r
                shapes.append(cv.Line(ix, py, px, py, paint=Paint(color=pcolor, stroke_width=sw)))
                shapes.append(cv.Text(ix - 3, py - 14, pnum,
                    style=ft.TextStyle(size=10, color=pnum_col),
                    alignment=ft.alignment.top_right, text_align=ft.TextAlign.RIGHT, max_width=40))
                shapes.append(cv.Text(px + 2, py - 15, pname,
                    style=_ps12,
                    alignment=ft.alignment.top_left, text_align=ft.TextAlign.LEFT,
                    max_width=int(canvas_w - px) - 4))
                if neg and pname:
                    _tw = _tw12(pname)
                    shapes.append(cv.Line(px + 2, py - 16, px + 2 + _tw, py - 16, paint=_ob_paint))
                if not is_ghost:
                    hit_areas.append((ix - 8, py - 18, px + 8, py + 26, pin_idx, side, row_or_col))
            elif act_side == "top":
                iy = body_top
                shapes.append(cv.Line(px, py, px, iy, paint=Paint(color=pcolor, stroke_width=sw)))
                shapes.append(cv.Text(px + 3, iy + 2, pnum,
                    style=ft.TextStyle(size=10, color=pnum_col),
                    alignment=ft.alignment.top_left, max_width=40))
                shapes.append(cv.Text(px, py - 4, pname,
                    style=_ps12,
                    alignment=ft.alignment.bottom_center, text_align=ft.TextAlign.CENTER,
                    max_width=_SYM_PIN_SPACING - 4))
                if neg and pname:
                    _tw = _tw12(pname)
                    _oy = py - 19   # 1px above text top (bottom_center at py-4, height~14px)
                    shapes.append(cv.Line(px - _tw // 2, _oy, px + _tw // 2, _oy, paint=_ob_paint))
                if not is_ghost:
                    hit_areas.append((px - 14, py - 18, px + 14, iy + 10, pin_idx, side, row_or_col))
            else:  # bottom
                iy = body_bot
                shapes.append(cv.Line(px, iy, px, py, paint=Paint(color=pcolor, stroke_width=sw)))
                shapes.append(cv.Text(px + 3, iy - 14, pnum,
                    style=ft.TextStyle(size=10, color=pnum_col),
                    alignment=ft.alignment.top_left, max_width=40))
                shapes.append(cv.Text(px, py + 2, pname,
                    style=_ps12,
                    alignment=ft.alignment.top_center, text_align=ft.TextAlign.CENTER,
                    max_width=_SYM_PIN_SPACING - 4))
                if neg and pname:
                    _tw = _tw12(pname)
                    shapes.append(cv.Line(px - _tw // 2, py + 1, px + _tw // 2, py + 1, paint=_ob_paint))
                if not is_ghost:
                    hit_areas.append((px - 14, iy - 10, px + 14, py + 18, pin_idx, side, row_or_col))

        for row, (pi, p) in enumerate(left_pins):
            _draw_pin(pi, p, *_gpos(pi, "left",   row), "left",   row)
        for row, (pi, p) in enumerate(right_pins):
            _draw_pin(pi, p, *_gpos(pi, "right",  row), "right",  row)
        for col, (pi, p) in enumerate(top_pins):
            _draw_pin(pi, p, *_gpos(pi, "top",    col), "top",    col)
        for col, (pi, p) in enumerate(bottom_pins):
            _draw_pin(pi, p, *_gpos(pi, "bottom", col), "bottom", col)

        _sym_editor_state.update({
            "hit_areas": hit_areas, "canvas_h": canvas_h, "canvas_w": canvas_w,
            "body_top": body_top,   "body_bot": body_bot,
            "body_l":   body_l,     "body_r":   body_r,
        })
        return shapes, canvas_h

    # ── Drag (pan) handlers ─────────────────────────────────────────────────

    def _clamp_pin_outside(sx, sy):
        """Snap (sx, sy) to the nearest grid point strictly outside the body rect."""
        st = _sym_editor_state
        bl, br = st["body_l"], st["body_r"]
        bt, bb = st["body_top"], st["body_bot"]
        dists = [
            (bl - sx, "left"),
            (sx - br, "right"),
            (bt - sy, "top"),
            (sy - bb, "bottom"),
        ]
        valid = [(d, sd) for d, sd in dists if d > 0]
        if not valid:
            valid = [(abs(d), sd) for d, sd in dists]
        near_side = min(valid)[1]
        if near_side == "left"  and sx >= bl: sx = bl - _SYM_GRID
        elif near_side == "right"  and sx <= br: sx = br + _SYM_GRID
        elif near_side == "top"    and sy >= bt: sy = bt - _SYM_GRID
        elif near_side == "bottom" and sy <= bb: sy = bb + _SYM_GRID
        return sx, sy

    def _on_sym_pan_start(e):
        tx, ty = e.local_x, e.local_y
        for x1, y1, x2, y2, item4, side, row in _sym_editor_state["hit_areas"]:
            if x1 <= tx <= x2 and y1 <= ty <= y2:
                if item4 == "resize":
                    st = _sym_editor_state
                    _sym_body_resize.update({
                        "active": True,
                        "part_num": _sym_step3_part["value"],
                        "orig_w":       st["body_r"] - st["body_l"],
                        "orig_h":       st["body_bot"] - st["body_top"],
                        "orig_body_l":  st["body_l"],
                        "orig_body_r":  st["body_r"],
                        "orig_body_bot": st["body_bot"],
                        "pin_snapshot": {
                            k: dict(v) for k, v in _sym_pin_layout.items()
                            if "gx" in v and "gy" in v
                        },
                        "delta_x": 0.0, "delta_y": 0.0,
                    })
                    return
                _sym_drag["active"]   = True
                _sym_drag["pin_idx"]  = item4
                _sym_drag["side"]     = side
                _sym_drag["orig_row"] = row
                _sym_drag["cur_x"]    = tx
                _sym_drag["cur_y"]    = ty
                _sym_drag["part_num"] = _sym_step3_part["value"]
                return

    def _on_sym_pan_update(e):
        if _sym_body_resize["active"]:
            _sym_body_resize["delta_x"] += e.delta_x
            _sym_body_resize["delta_y"] += e.delta_y
            max_body_w = int((_sym_editor_state.get("canvas_w", _SYM_CANVAS_W) - 2 * _SYM_PIN_STUB) / _SYM_GRID) * _SYM_GRID
            snap_w = int(round(max(_SYM_GRID,
                min(max_body_w,
                    _sym_body_resize["orig_w"] + 2 * _sym_body_resize["delta_x"])) / _SYM_GRID) * _SYM_GRID)
            snap_h = int(round(max(_SYM_GRID,
                _sym_body_resize["orig_h"] + _sym_body_resize["delta_y"]) / _SYM_GRID) * _SYM_GRID)
            _sym_body_size[str(_sym_body_resize["part_num"])] = {"w": snap_w, "h": snap_h}
            # Compute new body edges (mirrors _build_sym_shapes logic)
            def _snp(v): return int(round(v / _SYM_GRID) * _SYM_GRID)
            _cx         = _sym_editor_state.get("canvas_w", _SYM_CANVAS_W) / 2
            new_body_l  = _snp(_cx - snap_w / 2)
            new_body_r  = new_body_l + snap_w
            new_body_bot = _snp(_SYM_PIN_STUB + 44) + snap_h
            dl = new_body_l   - _sym_body_resize["orig_body_l"]
            dr = new_body_r   - _sym_body_resize["orig_body_r"]
            db = new_body_bot - _sym_body_resize["orig_body_bot"]
            # Move pins from snapshot by their respective edge delta
            for pidx_s, psnap in _sym_body_resize["pin_snapshot"].items():
                side  = _sym_pin_layout.get(pidx_s, {}).get("side", "left")
                entry = _sym_pin_layout.setdefault(pidx_s, {})
                if side == "left":
                    entry["gx"] = _snp(psnap["gx"] + dl)
                elif side == "right":
                    entry["gx"] = _snp(psnap["gx"] + dr)
                elif side == "bottom":
                    entry["gy"] = _snp(psnap["gy"] + db)
                # top: body_top is fixed, no adjustment needed
            shapes, _ = _build_sym_shapes(_sym_body_resize["part_num"])
            if _sym_canvas_ref.current:
                _sym_canvas_ref.current.shapes = shapes
                _sym_canvas_ref.current.update()
            return
        if not _sym_drag["active"]:
            return
        _sym_drag["cur_x"] += e.delta_x
        _sym_drag["cur_y"] += e.delta_y
        # Snap to grid for live preview
        snap_x = int(round(_sym_drag["cur_x"] / _SYM_GRID) * _SYM_GRID)
        snap_y = int(round(_sym_drag["cur_y"] / _SYM_GRID) * _SYM_GRID)
        snap_x, snap_y = _clamp_pin_outside(snap_x, snap_y)
        shapes, _ = _build_sym_shapes(
            _sym_drag["part_num"],
            drag_idx=_sym_drag["pin_idx"],
            drag_x=snap_x,
            drag_y=snap_y,
        )
        if _sym_canvas_ref.current:
            _sym_canvas_ref.current.shapes = shapes
            _sym_canvas_ref.current.update()

    def _on_sym_pan_end(e):
        if _sym_body_resize["active"]:
            _sym_body_resize["active"] = False
            _refresh_sym_editor(_sym_body_resize["part_num"])
            return
        if not _sym_drag["active"]:
            return
        _sym_drag["active"] = False
        part_num = _sym_drag["part_num"]
        pin_idx  = _sym_drag["pin_idx"]
        old_side = _sym_drag["side"]
        old_row  = _sym_drag["orig_row"]

        # Final snap
        snap_x = int(round(_sym_drag["cur_x"] / _SYM_GRID) * _SYM_GRID)
        snap_y = int(round(_sym_drag["cur_y"] / _SYM_GRID) * _SYM_GRID)
        snap_x, snap_y = _clamp_pin_outside(snap_x, snap_y)

        st       = _sym_editor_state
        body_l   = st["body_l"]
        body_r   = st["body_r"]
        body_top = st["body_top"]
        body_bot = st["body_bot"]

        # Nearest body-edge side for the drop point
        dists = [
            (body_l - snap_x, "left"),
            (snap_x - body_r, "right"),
            (body_top - snap_y, "top"),
            (snap_y - body_bot, "bottom"),
        ]
        valid = [(d, sd) for d, sd in dists if d > 0]
        if not valid:
            valid = [(abs(d), sd) for d, sd in dists]
        new_side = min(valid)[1]

        # Persist snapped position
        _sym_pin_layout.setdefault(str(pin_idx), {}).update({"gx": snap_x, "gy": snap_y})

        pkey = str(part_num)
        _sym_pin_order.setdefault(pkey, {sd: [] for sd in _SYM_SIDES})

        if new_side != old_side:
            _sym_pin_layout[str(pin_idx)]["side"] = new_side
            try:
                _sym_pin_order[pkey][old_side].remove(pin_idx)
            except (ValueError, KeyError):
                pass
            _sym_pin_order[pkey].setdefault(new_side, [])
            if pin_idx not in _sym_pin_order[pkey][new_side]:
                _sym_pin_order[pkey][new_side].append(pin_idx)
        else:
            # Reorder within same side using snap position
            order = _sym_pin_order[pkey].get(old_side, [])
            n     = len(order)
            if n > 1:
                new_row = (
                    round((snap_y - body_top - _SYM_PAD_Y) / _SYM_PIN_SPACING)
                    if old_side in ("left", "right")
                    else round((snap_x - body_l - _SYM_PAD_X) / _SYM_PIN_SPACING)
                )
                new_row = max(0, min(new_row, n - 1))
                if old_row != new_row and 0 <= old_row < n:
                    item = order.pop(old_row)
                    order.insert(new_row, item)

        _sym_drag["pin_idx"] = None
        _refresh_sym_editor(part_num)

    # ── Symbol editor: full rebuild ─────────────────────────────────────────

    def _refresh_sym_editor(part_num: int):
        """(Re)build the graphical symbol editor canvas for *part_num* and inject it."""
        if _sym_editor_content_ref.current is None:
            return

        # Make canvas fill the available width (page width minus panel padding)
        _sym_editor_state["canvas_w"] = max(_SYM_CANVAS_W, int(page.width or _SYM_CANVAS_W) - 24)

        # Default layout for pins not yet assigned
        for i in range(len(_fp_state["pins"])):
            if str(i) not in _sym_pin_layout:
                _sym_pin_layout[str(i)] = {"side": "left"}

        shapes, canvas_h = _build_sym_shapes(part_num)
        canvas_w = _sym_editor_state["canvas_w"]

        sym_canvas = cv.Canvas(
            ref=_sym_canvas_ref,
            shapes=shapes,
            width=canvas_w,
            height=canvas_h,
        )

        def _on_tap_down(e):
            _sym_tap_pos["x"] = e.local_x
            _sym_tap_pos["y"] = e.local_y

        def _on_tap(e):
            if _sym_drag["active"]:
                return
            tx, ty = _sym_tap_pos["x"], _sym_tap_pos["y"]
            for x1, y1, x2, y2, pidx, _s, _r in _sym_editor_state["hit_areas"]:
                if x1 <= tx <= x2 and y1 <= ty <= y2:
                    _show_sym_pin_layout_dialog(pidx, part_num)
                    return

        tap_layer = ft.GestureDetector(
            on_tap_down=_on_tap_down,
            on_tap=_on_tap,
            on_pan_start=_on_sym_pan_start,
            on_pan_update=_on_sym_pan_update,
            on_pan_end=_on_sym_pan_end,
            content=sym_canvas,
        )

        hint = s.get("drag_pin_hint", "Click a pin to change side  •  Drag a pin to reorder or move to another side")
        _sym_editor_content_ref.current.content = ft.Column(
            [
                ft.Text(hint, size=11, italic=True,
                        color=ft.colors.GREY_500, text_align=ft.TextAlign.CENTER),
                ft.Container(
                    content=ft.Column(
                        [ft.Stack(
                            [tap_layer],
                            width=canvas_w, height=canvas_h,
                        )],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        scroll=ft.ScrollMode.AUTO,
                        expand=True,
                    ),
                    expand=True,
                    alignment=ft.alignment.top_center,
                    bgcolor="#1e1e2e",
                    border_radius=6,
                ),
            ],
            spacing=6,
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
        _sym_editor_content_ref.current.update()

    def _on_step3_part_change(e):
        part_num = int(e.control.value or "1")
        _sym_step3_part["value"] = part_num
        _refresh_sym_editor(part_num)

    # ── End symbol editor helpers ───────────────────────────────────────────

    def _show_step3(e):
        """Show the New Symbol 3/3 full-screen view with symbol editor."""
        # Build part selector options
        parts_str = sym_parts_field.value.strip()
        num_parts = int(parts_str) if parts_str.isdigit() and int(parts_str) > 0 else 1
        if _new_sym_step3_part_dd_ref.current:
            _new_sym_step3_part_dd_ref.current.options = [
                ft.dropdown.Option(str(i)) for i in range(1, num_parts + 1)
            ]
            _new_sym_step3_part_dd_ref.current.value = "1"
        if _new_sym_step3_title_ref.current:
            _new_sym_step3_title_ref.current.value = s.get("new_symbol", "New Symbol") + " 3/3"
        _sym_step3_part["value"] = 1
        _sym_body_size.clear()
        new_sym_panel.visible = False
        _new_sym_step3_panel.visible = True
        page.update()
        _refresh_sym_editor(1)

    def _go_back_to_step2(e):
        _new_sym_step3_panel.visible = False
        new_sym_panel.visible = True
        page.update()

    def _go_back_to_step1(e):
        if _next_sym_bar_ref.current:
            _next_sym_bar_ref.current.visible = True
        if _new_sym_bottom_bar_ref.current:
            _new_sym_bottom_bar_ref.current.visible = False
        if _new_sym_title_ref.current:
            _new_sym_title_ref.current.value = s.get("new_symbol", "New Symbol") + " 1/3"
        if _new_sym_subtitle_ref.current:
            _new_sym_subtitle_ref.current.value = s.get("step1_subtitle", "Define Symbol Properties")
        _set_new_sym_centered_layout()
        page.update()

    _new_sym_action_row = ft.Row(
        [
            ft.ElevatedButton(
                s.get("next", "Next"),
                ref=generate_sym_btn_ref,
                icon=ft.icons.ARROW_FORWARD,
                on_click=_show_step3,
                color=ft.colors.WHITE,
                bgcolor=ft.colors.BLUE_700,
                disabled=True,
                opacity=0.35,
            ),
            ft.ElevatedButton(
                s.get("back", "Back"),
                icon=ft.icons.ARROW_BACK,
                on_click=_go_back_to_step1,
                color=ft.colors.WHITE,
                bgcolor=ft.colors.GREY_600,
            ),
            ft.ElevatedButton(
                s.get("close", "Cancel"),
                on_click=lambda e: (
                    setattr(new_sym_panel, "visible", False)
                    or setattr(_new_sym_step3_panel, "visible", False)
                    or page.update()
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
                ft.Text(
                    ref=_new_sym_subtitle_ref,
                    value=s.get("step1_subtitle", "Define Symbol Properties"),
                    size=12,
                    italic=True,
                    color=ft.colors.GREY_500,
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

    def _do_generate_from_step3(e):
        _new_sym_step3_panel.visible = False
        _generate_symbol(e)

    _new_sym_step3_panel = ft.Container(
        visible=False,
        expand=True,
        padding=ft.padding.symmetric(horizontal=12, vertical=12),
        content=ft.Column(
            [
                ft.Text(
                    ref=_new_sym_step3_title_ref,
                    value=s.get("new_symbol", "New Symbol") + " 3/3",
                    size=16,
                    weight=ft.FontWeight.W_600,
                    color=ft.colors.ORANGE,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Text(
                    s.get("step3_subtitle", "Define Pin Placement"),
                    size=12,
                    italic=True,
                    color=ft.colors.GREY_500,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Container(
                    alignment=ft.alignment.center,
                    padding=ft.padding.only(top=6, bottom=2),
                    content=ft.Dropdown(
                        ref=_new_sym_step3_part_dd_ref,
                        label=s.get("select_part", "Working on Part #"),
                        width=240,
                        options=[ft.dropdown.Option("1")],
                        value="1",
                        on_change=_on_step3_part_change,
                    ),
                ),
                # ── Graphical symbol editor canvas ──
                ft.Container(
                    ref=_sym_editor_content_ref,
                    expand=True,
                    alignment=ft.alignment.top_center,
                    content=None,
                ),
                ft.Container(
                    alignment=ft.alignment.center,
                    padding=ft.padding.symmetric(vertical=10),
                    content=ft.Row(
                        [
                            ft.ElevatedButton(
                                s.get("generate_symbol", "Generate Symbol"),
                                icon=ft.icons.BOLT,
                                on_click=_do_generate_from_step3,
                                color=ft.colors.WHITE,
                                bgcolor=ft.colors.GREEN_700,
                            ),
                            ft.ElevatedButton(
                                s.get("back", "Back"),
                                icon=ft.icons.ARROW_BACK,
                                on_click=_go_back_to_step2,
                                color=ft.colors.WHITE,
                                bgcolor=ft.colors.GREY_600,
                            ),
                            ft.ElevatedButton(
                                s.get("close", "Cancel"),
                                on_click=lambda e: (
                                    setattr(_new_sym_step3_panel, "visible", False)
                                    or setattr(new_sym_panel, "visible", False)
                                    or page.update()
                                ),
                                color=ft.colors.WHITE,
                                bgcolor=ft.colors.GREY_600,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=8,
                    ),
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
                    ref=_add_pkg_title_ref,
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
                            [pkg_name_field, pkg_pins_field, pkg_mounting_dd, pkg_pkgtype_wrapper, _footprint_pick_btn, fp_path_text],
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
        _new_sym_step3_panel.visible = False
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
        [new_sym_panel, _new_sym_step3_panel, del_sym_panel, add_pkg_panel, del_pkg_panel,
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

