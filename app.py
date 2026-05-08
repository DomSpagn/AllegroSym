import base64
import math
import os
import shutil
from pathlib import Path

import flet as ft
import flet.canvas as cv
from flet.core.painting import Paint, PaintingStyle

from config import (
    APP_VERSION, BUILD_DATE, AUTHOR, ICON_PATH,
    get_strings, save_config,
    load_packages, save_packages, pkg_display_name,
)
from pin_detection import detect_orange_pins
from wizard import show_wizard  # re-exported for main.py compatibility


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

    # ── About dialog ─────────────────────────────────────────────────────────
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

    # ── User Manual ──────────────────────────────────────────────────────────
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

    # ── Package management state ──────────────────────────────────────────────
    packages = load_packages()

    new_sym_btn_ref            = ft.Ref[ft.IconButton]()
    edit_sym_btn_ref           = ft.Ref[ft.IconButton]()
    save_pkg_btn_ref           = ft.Ref[ft.ElevatedButton]()
    del_btn_ref                = ft.Ref[ft.ElevatedButton]()
    save_cancel_row_ref        = ft.Ref[ft.Row]()
    _bottom_bar_ref             = ft.Ref[ft.Container]()
    add_pkg_panel_title_ref    = ft.Ref[ft.Text]()
    edit_fields_container_ref  = ft.Ref[ft.Container]()
    footprint_preview_ref      = ft.Ref[ft.Container]()
    fp_canvas_ref              = ft.Ref[cv.Canvas]()
    edit_pkg_btn_ref           = ft.Ref[ft.IconButton]()
    del_pkg_btn_ref            = ft.Ref[ft.IconButton]()

    _pkg_mode = {"mode": "add", "original_idx": -1}
    _orig_pkg_values = {"name": "", "pins": "", "footprint": ""}
    _fp_state = {"pins": [], "scale_x": 1.0, "scale_y": 1.0}
    _pin_method = {"value": None, "waiting_pin1": False}
    pin_method_dd_ref               = ft.Ref[ft.Dropdown]()
    _pin_hint_ref                   = ft.Ref[ft.Text]()
    _alphanumeric_pkg_container_ref = ft.Ref[ft.Container]()
    _alphanumeric_pkg_dd_ref        = ft.Ref[ft.Dropdown]()
    _alphanumeric_pkg_type          = {"value": None}
    _FP_PREVIEW_W = 900
    new_sym_fp_preview_ref          = ft.Ref[ft.Container]()
    new_sym_right_col_ref           = ft.Ref[ft.Container]()

    def update_symbol_buttons():
        enabled = len(packages) > 0
        for ref in (new_sym_btn_ref, edit_sym_btn_ref, edit_pkg_btn_ref, del_pkg_btn_ref):
            ref.current.disabled = not enabled
            ref.current.opacity  = 1.0 if enabled else 0.35
        page.update()

    # ── Field widgets ─────────────────────────────────────────────────────────
    sym_name_field = ft.TextField(
        label=s.get("symbol_name", "Symbol Name"), width=320, autofocus=True
    )
    pkg_dropdown = ft.Dropdown(
        label=s.get("package_type", "Package Type"),
        width=320,
        options=[ft.dropdown.Option(pkg_display_name(p)) for p in packages],
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
            pkg_pins_field.error_text   = "Inserire un intero positivo non nullo"
            pkg_pins_field.border_color = ft.colors.RED
        else:
            pkg_pins_field.error_text   = None
            pkg_pins_field.border_color = None

        if _pkg_mode["mode"] == "edit":
            changed = (
                pkg_name_field.value.strip() != _orig_pkg_values["name"]
                or pins_str != _orig_pkg_values["pins"]
                or pkg_images["footprint"] != _orig_pkg_values["footprint"]
            )
            # Mostra la row appena il package è caricato; Save abilitato solo se cambiato
            row_visible = fp_ok
            if save_pkg_btn_ref.current:
                save_enabled = name_ok and pins_ok and changed
                save_pkg_btn_ref.current.disabled = not save_enabled
                save_pkg_btn_ref.current.opacity  = 1.0 if save_enabled else 0.35
        else:
            # Add Package: mostra la row Save/Cancel appena compare l'immagine;
            # il pulsante Save è disabilitato finché nome e pin non sono validi.
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
    pkg_images   = {"footprint": ""}

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

    # ── Delete Package dropdown ───────────────────────────────────────────────
    def _on_del_dd_select(e):
        enabled = bool(del_pkg_dd.value)
        if del_btn_ref.current:
            del_btn_ref.current.disabled = not enabled
            del_btn_ref.current.opacity  = 1.0 if enabled else 0.35
            page.update()

    del_pkg_dd = ft.Dropdown(
        label=s.get("package_name", "Package"), width=280, on_change=_on_del_dd_select
    )

    # ── Edit Package selection dropdown ──────────────────────────────────────
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
            _orig_pkg_values["name"]      = pkg["name"]
            _orig_pkg_values["pins"]      = str(pkg["pins"])
            _orig_pkg_values["footprint"] = pkg.get("footprint", "")
            _fp_state["pins"] = [
                {"bbox_orig": tuple(p["bbox_orig"]), "name": p.get("name", ""), "number": p.get("number", "")}
                for p in pkg.get("pins_data", [])
            ]
            if edit_fields_container_ref.current:
                edit_fields_container_ref.current.visible = True
            edit_sel_container.visible = False
            if pkg.get("footprint") and os.path.isfile(pkg["footprint"]):
                _build_static_preview(pkg["footprint"])
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
        expand=True,
        alignment=ft.alignment.center,
        content=ft.Column(
            [edit_sel_dd],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            tight=True,
        ),
    )

    # ── Canvas helpers ────────────────────────────────────────────────────────
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

    # ── Layout helpers ────────────────────────────────────────────────────────
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

    # ── Preview builder ───────────────────────────────────────────────────────
    def _on_pin_method_change(e):
        method = e.control.value
        _pin_method["value"] = method
        _pin_method["waiting_pin1"] = False
        _alphanumeric_pkg_type["value"] = None
        if _alphanumeric_pkg_dd_ref.current:
            _alphanumeric_pkg_dd_ref.current.value = None
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
        else:
            if _pin_hint_ref.current:
                _pin_hint_ref.current.visible = False
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
        else:
            _pin_method["waiting_pin1"] = False
            if _pin_hint_ref.current:
                _pin_hint_ref.current.visible = False
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

        scale = _FP_PREVIEW_W / max(orig_w, 1)
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
                width=_FP_PREVIEW_W,
                height=preview_h,
                fit=ft.ImageFit.FILL,
            )
        except Exception:
            img_ctrl = ft.Container(
                width=_FP_PREVIEW_W, height=preview_h, bgcolor=ft.colors.GREY_800
            )

        canvas_ctrl = cv.Canvas(
            ref=fp_canvas_ref,
            shapes=_build_pin_shapes(),
            width=_FP_PREVIEW_W,
            height=preview_h,
        )
        tap_layer = ft.GestureDetector(on_tap_down=_handle_img_tap, content=canvas_ctrl)
        preview_stack = ft.Stack(
            [img_ctrl, tap_layer], width=_FP_PREVIEW_W, height=preview_h
        )

        pin_method_dd = ft.Dropdown(
            ref=pin_method_dd_ref,
            label=s.get("select_pin_numbering", "Select the pin numbering method"),
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
            color=ft.colors.AMBER,
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

    # ── Pin auto-numbering ────────────────────────────────────────────────────
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
            _pin_hint_ref.current.visible = False
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
            _pin_hint_ref.current.visible = False
        _refresh_canvas()

    # ── Image tap handler ─────────────────────────────────────────────────────
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
        number_field = ft.TextField(
            label="Pin ID", value=pin.get("number", ""), width=220, autofocus=True
        )

        def on_pin_save(_):
            new_id = number_field.value.strip()
            duplicate = any(
                i != pin_idx and _fp_state["pins"][i].get("number", "").strip() == new_id
                for i in range(len(_fp_state["pins"]))
            )
            if duplicate and new_id:
                number_field.error_text   = "Pin ID già utilizzato da un altro pin"
                number_field.border_color = ft.colors.RED
                page.update()
                return
            number_field.error_text   = None
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

    # ── Footprint file picker ─────────────────────────────────────────────────
    def _on_fp_result(e: ft.FilePickerResultEvent):
        if e.files:
            pkg_images["footprint"] = e.files[0].path
            fp_path_text.value = os.path.basename(e.files[0].path)
            _fp_state["pins"] = []
            _build_static_preview(e.files[0].path)
            _check_save_enabled()

    fp_picker = ft.FilePicker(on_result=_on_fp_result)
    page.overlay.append(fp_picker)

    def pick_footprint(_):
        fp_picker.pick_files(
            dialog_title=s.get("pick_footprint", "Select Footprint Image"),
            allowed_extensions=["png"],
        )
        page.update()

    # ── State reset helper ────────────────────────────────────────────────────
    def _reset_pkg_state():
        pkg_name_field.value    = ""
        pkg_pins_field.value    = ""
        fp_path_text.value      = ""
        pkg_images["footprint"] = ""
        _fp_state["pins"]       = []
        _pin_method["value"]    = None
        _pin_method["waiting_pin1"] = False
        _alphanumeric_pkg_type["value"] = None

    # ── Package CRUD handlers ─────────────────────────────────────────────────
    def _on_pkg_type_change(e):
        """Called when the user selects a package in the New Symbol dropdown."""
        dname = e.control.value
        if not dname:
            if new_sym_right_col_ref.current:
                new_sym_right_col_ref.current.visible = False
            page.update()
            return
        pkg = next((p for p in packages if pkg_display_name(p) == dname), None)
        if pkg and pkg.get("footprint") and os.path.isfile(pkg["footprint"]):
            _fp_state["pins"] = [
                {"bbox_orig": tuple(p["bbox_orig"]), "name": p.get("name", ""), "number": p.get("number", "")}
                for p in pkg.get("pins_data", [])
            ]
            _build_interactive_preview(pkg["footprint"])
            if new_sym_right_col_ref.current:
                new_sym_right_col_ref.current.visible = True
        else:
            if new_sym_right_col_ref.current:
                new_sym_right_col_ref.current.visible = False
        page.update()

    def new_symbol(e):
        add_pkg_panel.visible  = False
        del_pkg_panel.visible  = False
        pkg_list_panel.visible = False
        sym_name_field.value   = ""
        pkg_dropdown.value     = None
        pkg_dropdown.options   = [ft.dropdown.Option(pkg_display_name(p)) for p in packages]
        _reset_pkg_state()
        if new_sym_right_col_ref.current:
            new_sym_right_col_ref.current.visible = False
        new_sym_panel.visible  = True
        page.update()

    def edit_symbol(e):
        pass  # placeholder

    def show_add_package(e):
        _pkg_mode["mode"]          = "add"
        _pkg_mode["original_idx"]  = -1
        new_sym_panel.visible      = False
        del_pkg_panel.visible      = False
        pkg_list_panel.visible     = False
        edit_sel_container.visible = False
        if add_pkg_panel_title_ref.current:
            add_pkg_panel_title_ref.current.value = s.get("add_package", "Add Package")
            add_pkg_panel_title_ref.current.color = ft.colors.ORANGE
        if edit_fields_container_ref.current:
            edit_fields_container_ref.current.visible = True
        _reset_pkg_state()
        _set_centered_layout()
        if _bottom_bar_ref.current:
            _bottom_bar_ref.current.visible = False
        add_pkg_panel.visible = True
        _check_save_enabled()
        page.update()

    def show_edit_package(e):
        if not packages:
            return
        _pkg_mode["mode"]          = "edit"
        _pkg_mode["original_idx"]  = -1
        new_sym_panel.visible      = False
        del_pkg_panel.visible      = False
        pkg_list_panel.visible     = False
        edit_sel_dd.options        = [ft.dropdown.Option(pkg_display_name(p)) for p in packages]
        edit_sel_dd.value          = None
        edit_sel_container.visible = True
        if add_pkg_panel_title_ref.current:
            add_pkg_panel_title_ref.current.value = s.get("edit_package", "Edit Package")
            add_pkg_panel_title_ref.current.color = ft.colors.ORANGE
        if edit_fields_container_ref.current:
            edit_fields_container_ref.current.visible = False
        _reset_pkg_state()
        _set_centered_layout()
        if _bottom_bar_ref.current:
            _bottom_bar_ref.current.visible = False
        if save_pkg_btn_ref.current:
            save_pkg_btn_ref.current.disabled = True
            save_pkg_btn_ref.current.opacity  = 0.35
        add_pkg_panel.visible = True
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
                    pkg_name_field.error_text   = "Package con stesso nome e pin già esistente"
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
            pkg_dir = os.path.join(os.path.dirname(__file__), "Images", f"{name}{pins}")
            os.makedirs(pkg_dir, exist_ok=True)
            fp_dest = ""
            if pkg_images["footprint"]:
                ext     = os.path.splitext(pkg_images["footprint"])[1]
                fp_dest = os.path.join(pkg_dir, f"{name}{pins}{ext}")
                shutil.copy2(pkg_images["footprint"], fp_dest)
            packages.append({"name": name, "pins": pins, "footprint": fp_dest, "pins_data": pins_data})
        else:  # edit
            orig_pkg = packages[orig_idx]
            old_name = orig_pkg["name"]
            old_pins = orig_pkg["pins"]
            old_dir  = os.path.join(os.path.dirname(__file__), "Images", f"{old_name}{old_pins}")
            pkg_dir  = os.path.join(os.path.dirname(__file__), "Images", f"{name}{pins}")
            if (old_name != name or old_pins != pins) and os.path.isdir(old_dir):
                os.rename(old_dir, pkg_dir)
            os.makedirs(pkg_dir, exist_ok=True)
            fp_dest = orig_pkg.get("footprint", "")
            if (old_name != name or old_pins != pins) and fp_dest:
                fp_dest = os.path.join(pkg_dir, os.path.basename(fp_dest))
            if pkg_images["footprint"] and pkg_images["footprint"] != orig_pkg.get("footprint", ""):
                ext     = os.path.splitext(pkg_images["footprint"])[1]
                fp_dest = os.path.join(pkg_dir, f"{name}{pins}{ext}")
                shutil.copy2(pkg_images["footprint"], fp_dest)
            packages[orig_idx] = {"name": name, "pins": pins, "footprint": fp_dest, "pins_data": pins_data}

        save_packages(packages)
        add_pkg_panel.visible = False
        update_symbol_buttons()

    def cancel_add_pkg(_):
        _reset_pkg_state()
        _set_centered_layout()
        if _bottom_bar_ref.current:
            _bottom_bar_ref.current.visible = False
        add_pkg_panel.visible = False
        page.update()

    def show_delete_package(e):
        if not packages:
            return
        del_pkg_dd.options     = [ft.dropdown.Option(pkg_display_name(p)) for p in packages]
        del_pkg_dd.value       = None
        new_sym_panel.visible  = False
        add_pkg_panel.visible  = False
        pkg_list_panel.visible = False
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
        folder_name = f"{pkg['name']}{pkg['pins']}"
        packages[:] = [p for p in packages if pkg_display_name(p) != dname]
        save_packages(packages)
        pkg_dir = os.path.join(os.path.dirname(__file__), "Images", folder_name)
        if os.path.isdir(pkg_dir):
            shutil.rmtree(pkg_dir)
        del_pkg_panel.visible = False
        update_symbol_buttons()

    def cancel_delete(_):
        del_pkg_panel.visible = False
        page.update()

    def show_packages(e):
        new_sym_panel.visible  = False
        add_pkg_panel.visible  = False
        del_pkg_panel.visible  = False
        if packages:
            pkg_list_col.controls = [
                ft.Row(
                    [ft.Icon(ft.icons.MEMORY, size=16),
                     ft.Text(pkg_display_name(p), size=13, weight=ft.FontWeight.W_500, expand=True)],
                    spacing=8,
                )
                for p in packages
            ]
        else:
            pkg_list_col.controls = [
                ft.Text(s.get("no_packages", "No packages defined yet."), italic=True),
            ]
        pkg_list_col.controls.append(
            ft.TextButton(
                s.get("close", "Close"),
                on_click=lambda _: (setattr(pkg_list_panel, "visible", False), page.update()),
            )
        )
        pkg_list_panel.visible = True
        page.update()

    # ── Panels ────────────────────────────────────────────────────────────────
    pkg_list_col = ft.Column([], spacing=6)

    pkg_list_panel = ft.Container(
        visible=False,
        padding=ft.padding.symmetric(horizontal=24, vertical=12),
        content=ft.Column(
            [
                ft.Text(s.get("show_packages", "Show Packages"), size=16,
                        weight=ft.FontWeight.W_600, color=ft.colors.BLUE),
                ft.Divider(height=1),
                pkg_list_col,
            ],
            spacing=10,
        ),
    )

    pkg_dropdown.on_change = _on_pkg_type_change

    new_sym_panel = ft.Container(
        visible=False,
        expand=True,
        padding=ft.padding.symmetric(horizontal=12, vertical=12),
        content=ft.Row(
            [
                # Left 1/5 — symbol name + package selector
                ft.Container(
                    expand=1,
                    padding=ft.padding.only(right=12),
                    alignment=ft.alignment.top_center,
                    content=ft.Column(
                        [
                            ft.Text(
                                s.get("new_symbol", "New Symbol"),
                                size=16,
                                weight=ft.FontWeight.W_600,
                                color=ft.colors.ORANGE,
                            ),
                            sym_name_field,
                            pkg_dropdown,
                        ],
                        spacing=12,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ),
                # Right 4/5 — interactive footprint image (shown after package selection)
                ft.Container(
                    ref=new_sym_right_col_ref,
                    expand=4,
                    visible=False,
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
                            [pkg_name_field, pkg_pins_field, _footprint_pick_btn,
                             fp_path_text],
                            spacing=12,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            tight=True,
                        ),
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

    # ── Command bar ───────────────────────────────────────────────────────────
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
                            opacity=1.0 if packages else 0.35,
                        ),
                        ft.IconButton(
                            ref=edit_sym_btn_ref,
                            icon=ft.icons.EDIT,
                            icon_color=ft.colors.TEAL,
                            tooltip=s.get("edit_symbol", "Edit Symbol"),
                            on_click=edit_symbol,
                            disabled=len(packages) == 0,
                            opacity=1.0 if packages else 0.35,
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
                            opacity=1.0 if packages else 0.35,
                        ),
                        ft.IconButton(
                            ref=del_pkg_btn_ref,
                            icon=ft.icons.MEMORY_OUTLINED,
                            icon_color=ft.colors.RED,
                            tooltip=s.get("delete_package", "Delete Package"),
                            on_click=show_delete_package,
                            disabled=len(packages) == 0,
                            opacity=1.0 if packages else 0.35,
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
        ),
        padding=ft.padding.symmetric(horizontal=8, vertical=2),
    )

    body = ft.Column(
        [new_sym_panel, add_pkg_panel, del_pkg_panel, pkg_list_panel],
        expand=True,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
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

