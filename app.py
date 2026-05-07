import flet as ft
import json
import os
import shutil
import sys
import threading
import io
from datetime import date
from pathlib import Path

APP_VERSION = "v0.1"
BUILD_DATE = "06-05-2026"
AUTHOR = "Domenico Spagnuolo"
JSONS_DIR = os.path.join(os.path.dirname(__file__), "JSONS")
CONF_FILE = os.path.join(JSONS_DIR, "asym_conf.json")
PACKAGE_LIST_FILE = os.path.join(JSONS_DIR, "package_list.json")
ICON_PATH = os.path.join(os.path.dirname(__file__), "Images", "ASym.ico")

# ── 3D conversion ────────────────────────────────────────────────────────────

def convert_stp_to_glb(stp_path: str) -> str:
    """Convert a STEP file to GLB in a subprocess (suppresses all OCCT output).
    Returns the GLB path, or empty string on failure."""
    glb_path = os.path.splitext(stp_path)[0] + ".glb"
    if os.path.exists(glb_path) and os.path.getmtime(glb_path) >= os.path.getmtime(stp_path):
        return glb_path
    script = (
        "import trimesh, sys\n"
        f"scene = trimesh.load({stp_path!r})\n"
        f"scene.export({glb_path!r})\n"
    )
    import subprocess
    result = subprocess.run(
        [sys.executable, "-c", script],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if result.returncode == 0 and os.path.exists(glb_path):
        return glb_path
    return ""


# Cache loaded meshes to avoid re-parsing on every render
_mesh_cache: dict = {}


def pkg_display_name(p: dict) -> str:
    """Canonical display name shown everywhere: 'NAMEPINS'."""
    return f"{p['name']}{p['pins']}"


def _load_meshes(path: str) -> list:
    """Load and cache meshes from a GLB file."""
    if path in _mesh_cache:
        return _mesh_cache[path]
    import trimesh
    obj = trimesh.load(path)
    if isinstance(obj, trimesh.Scene):
        meshes = [g for g in obj.geometry.values()
                  if hasattr(g, "triangles") and len(g.triangles) > 0]
    elif hasattr(obj, "triangles"):
        meshes = [obj]
    else:
        meshes = []
    _mesh_cache[path] = meshes
    return meshes


def _mesh_base_color(mesh) -> "np.ndarray":
    """Extract a representative RGB [0-1] color from a trimesh mesh."""
    import numpy as np
    try:
        vc = mesh.visual.to_color().vertex_colors  # RGBA uint8
        if vc is not None and len(vc):
            return np.clip(vc[:, :3].mean(axis=0) / 255.0, 0, 1)
    except Exception:
        pass
    return np.array([0.18, 0.18, 0.18])  # fallback: dark grey (IC body)


def render_3d_snapshot(path: str, azim: float = 45.0, elev: float = 30.0) -> bytes:
    """Render a STEP/GLB mesh to PNG bytes using matplotlib with multi-light shading."""
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    meshes = _load_meshes(path)
    if not meshes:
        return b""

    # Three-point lighting (unit vectors)
    lights = [
        (np.array([0.6,  0.8,  1.0]),  0.65),   # key   (top-front-right)
        (np.array([-1.0, 0.3,  0.5]),  0.20),   # fill  (left)
        (np.array([0.0, -1.0, -0.3]),  0.10),   # back
    ]
    for v, _ in lights:
        v /= np.linalg.norm(v)
    ambient = 0.25

    fig = plt.figure(figsize=(3, 3), facecolor="#d0d0d0")
    ax = fig.add_subplot(111, projection="3d", facecolor="#d0d0d0")

    max_tris = 8000
    for mesh in meshes:
        tris    = mesh.triangles
        normals = mesh.face_normals          # (N,3)
        base    = _mesh_base_color(mesh)

        if len(tris) > max_tris:
            step = len(tris) // max_tris + 1
            tris    = tris[::step]
            normals = normals[::step]

        # Per-face intensity = ambient + sum of clamped diffuse contributions
        intensity = np.full(len(normals), ambient)
        for lvec, lstr in lights:
            intensity += lstr * np.clip(normals @ lvec, 0, 1)
        intensity = np.clip(intensity, 0, 1)[:, np.newaxis]

        face_colors = np.clip(intensity * base, 0, 1)

        poly = Poly3DCollection(tris, linewidth=0, zsort="average")
        poly.set_facecolor(face_colors)
        poly.set_edgecolor("none")
        ax.add_collection3d(poly)

    all_v = np.vstack([m.vertices for m in meshes])
    mn, mx = all_v.min(0), all_v.max(0)
    mid = (mn + mx) / 2
    r   = max((mx - mn).max() / 2 * 1.2, 1e-6)
    ax.set_xlim(mid[0] - r, mid[0] + r)
    ax.set_ylim(mid[1] - r, mid[1] + r)
    ax.set_zlim(mid[2] - r, mid[2] + r)
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor=fig.get_facecolor(),
                bbox_inches="tight", dpi=100, pad_inches=0.02)
    plt.close(fig)
    buf.seek(0)
    return buf.read()


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

    fp_preview_img = ft.Image(src="", width=200, height=200, fit=ft.BoxFit.CONTAIN, visible=False)
    fp_preview_label = ft.Text("2D Preview", size=11, italic=True, visible=False)

    view3d_img_ref  = ft.Ref[ft.Image]()
    view3d_ring_ref = ft.Ref[ft.Container]()
    view3d_label    = ft.Text("3D Model", size=11, italic=True, visible=False)
    _3d_state: dict = {"azim": 45.0, "elev": 30.0, "path": "", "rendering": False}

    def _do_render():
        path = _3d_state["path"]
        if not path or _3d_state["rendering"]:
            return
        _3d_state["rendering"] = True
        try:
            png_bytes = render_3d_snapshot(path, _3d_state["azim"], _3d_state["elev"])
            if png_bytes and view3d_img_ref.current:
                view3d_img_ref.current.src        = png_bytes
                view3d_img_ref.current.visible    = True
                if view3d_ring_ref.current:
                    view3d_ring_ref.current.visible = False
                page.update()
        except Exception as ex:
            print(f"[3D render] {ex}")
        finally:
            _3d_state["rendering"] = False

    def _on_3d_scroll(e):
        # scroll_delta is an Offset with .x and .y
        dx = getattr(e.scroll_delta, "x", 0) or 0
        dy = getattr(e.scroll_delta, "y", 0) or 0
        _3d_state["azim"] = (_3d_state["azim"] + dx * 1.5) % 360
        _3d_state["elev"] = max(-89, min(89, _3d_state["elev"] - dy * 1.5))
        threading.Thread(target=_do_render, daemon=True).start()

    def _on_3d_pan(e):
        # local_delta is an Offset with .x and .y
        dx = getattr(e.local_delta, "x", 0) or 0
        dy = getattr(e.local_delta, "y", 0) or 0
        _3d_state["azim"] = (_3d_state["azim"] + dx * 0.5) % 360
        _3d_state["elev"] = max(-89, min(89, _3d_state["elev"] - dy * 0.5))
        threading.Thread(target=_do_render, daemon=True).start()

    def _on_pkg_select(e):
        dname = pkg_dropdown.value
        fp_preview_img.visible   = False
        fp_preview_label.visible = False
        view3d_label.visible     = False
        _3d_state["path"]        = ""
        if view3d_img_ref.current:
            view3d_img_ref.current.visible = False
        has_2d = has_3d = False
        if dname:
            pkg = next((p for p in packages if pkg_display_name(p) == dname), None)
            if pkg and pkg.get("footprint") and os.path.isfile(pkg["footprint"]):
                fp_preview_img.src       = pkg["footprint"]
                fp_preview_img.visible   = True
                fp_preview_label.visible = True
                has_2d = True
            if pkg and pkg.get("image3d") and os.path.isfile(pkg["image3d"]):
                glb = convert_stp_to_glb(pkg["image3d"])
                if glb:
                    _3d_state["path"]    = glb
                    _3d_state["azim"]    = 45.0
                    _3d_state["elev"]    = 30.0
                    view3d_label.visible = True
                    if view3d_ring_ref.current:
                        view3d_ring_ref.current.visible = True
                    has_3d = True
                    threading.Thread(target=_do_render, daemon=True).start()
        if has_2d or has_3d:
            page.window.min_height = 520
            page.window.height     = 520
        else:
            page.window.min_height = 280
            page.window.height     = 280
        page.window.update()
        page.update()

    pkg_dropdown = ft.Dropdown(
        label=s.get("package_type", "Package Type"),
        width=320,
        options=[ft.dropdown.Option(pkg_display_name(p)) for p in packages],
        on_select=_on_pkg_select,
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
            pkg_pins_field.border_color = ft.Colors.RED
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
    img3d_path_text   = ft.Text(value="", size=11, italic=True)
    pkg_images        = {"footprint": "", "3d": ""}

    # Delete Package panel fields
    def _on_del_dd_select(e):
        enabled = bool(del_pkg_dd.value)
        if del_btn_ref.current:
            del_btn_ref.current.disabled = not enabled
            del_btn_ref.current.opacity  = 1.0 if enabled else 0.35
            page.update()

    del_pkg_dd = ft.Dropdown(label=s.get("package_name", "Package"), width=280, on_select=_on_del_dd_select)

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
            img3d_path_text.value     = os.path.basename(pkg.get("image3d", ""))   if pkg.get("image3d")   else ""
            pkg_images["footprint"]   = pkg.get("footprint", "")
            pkg_images["3d"]          = pkg.get("image3d", "")
            if edit_fields_container_ref.current:
                edit_fields_container_ref.current.visible = True
            page.window.min_height = 580
            page.window.height     = 580
            page.window.update()
            _check_save_enabled()
            page.update()

    edit_sel_dd = ft.Dropdown(
        label=s.get("package_name", "Package"),
        width=280,
        on_select=_on_edit_sel_change,
    )
    edit_sel_container = ft.Container(
        visible=False,
        content=ft.Column(
            [edit_sel_dd],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.only(bottom=4),
    )

    # ── File pickers ─────────────────────────────────────────────────────────
    fp_picker    = ft.FilePicker()
    img3d_picker = ft.FilePicker()
    page.services.append(fp_picker)
    page.services.append(img3d_picker)

    async def pick_footprint(_):
        files = await fp_picker.pick_files(
            dialog_title=s.get("pick_footprint", "Select Footprint Image"),
            allowed_extensions=["png", "jpg", "jpeg", "bmp"],
        )
        if files:
            pkg_images["footprint"] = files[0].path
            fp_path_text.value = os.path.basename(files[0].path)
            page.update()

    async def pick_3d(_):
        files = await img3d_picker.pick_files(
            dialog_title=s.get("pick_3d", "Select 3D Model"),
            allowed_extensions=["stp", "step"],
        )
        if files:
            pkg_images["3d"] = files[0].path
            img3d_path_text.value = os.path.basename(files[0].path)
            page.update()

    # ── Handlers ─────────────────────────────────────────────────────────────
    def _collapse_window():
        page.window.height     = 120
        page.window.min_height = 120
        page.window.update()

    def new_symbol(e):
        add_pkg_panel.visible = False
        del_pkg_panel.visible = False
        sym_name_field.value  = ""
        pkg_dropdown.value    = None
        pkg_dropdown.options  = [ft.dropdown.Option(pkg_display_name(p)) for p in packages]
        fp_preview_img.visible   = False
        fp_preview_label.visible = False
        new_sym_panel.visible = True
        page.window.min_height = 280
        page.window.height     = 280
        page.window.update()
        page.update()

    def edit_symbol(e):
        pass  # placeholder

    def show_add_package(e):
        _pkg_mode["mode"]        = "add"
        _pkg_mode["original_idx"] = -1
        new_sym_panel.visible    = False
        del_pkg_panel.visible    = False
        edit_sel_container.visible = False
        if add_pkg_panel_title_ref.current:
            add_pkg_panel_title_ref.current.value = s.get("add_package", "Add Package")
            add_pkg_panel_title_ref.current.color = ft.Colors.ORANGE
        if edit_fields_container_ref.current:
            edit_fields_container_ref.current.visible = True
        pkg_name_field.value    = ""
        pkg_pins_field.value    = ""
        fp_path_text.value      = ""
        img3d_path_text.value   = ""
        pkg_images["footprint"] = ""
        pkg_images["3d"]        = ""
        add_pkg_panel.visible   = True
        page.window.min_height  = 500
        page.window.height      = 500
        page.window.update()
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
            add_pkg_panel_title_ref.current.color = ft.Colors.ORANGE
        if edit_fields_container_ref.current:
            edit_fields_container_ref.current.visible = False
        pkg_name_field.value    = ""
        pkg_pins_field.value    = ""
        fp_path_text.value      = ""
        img3d_path_text.value   = ""
        pkg_images["footprint"] = ""
        pkg_images["3d"]        = ""
        if save_pkg_btn_ref.current:
            save_pkg_btn_ref.current.disabled = True
            save_pkg_btn_ref.current.opacity  = 0.35
        add_pkg_panel.visible   = True
        page.window.min_height  = 240
        page.window.height      = 240
        page.window.update()
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
                    pkg_name_field.border_color = ft.Colors.RED
                    page.update()
                    return
        pkg_name_field.error_text   = None
        pkg_name_field.border_color = None

        if mode == "add":
            pkg_dir = os.path.join(os.path.dirname(__file__), "Images", name)
            os.makedirs(pkg_dir, exist_ok=True)
            fp_dest = img3d_dest = ""
            if pkg_images["footprint"]:
                ext     = os.path.splitext(pkg_images["footprint"])[1]
                fp_dest = os.path.join(pkg_dir, f"footprint{ext}")
                shutil.copy2(pkg_images["footprint"], fp_dest)
            if pkg_images["3d"]:
                ext         = os.path.splitext(pkg_images["3d"])[1]
                img3d_dest  = os.path.join(pkg_dir, f"3d{ext}")
                shutil.copy2(pkg_images["3d"], img3d_dest)
            packages.append({"name": name, "pins": pins, "footprint": fp_dest, "image3d": img3d_dest})

        else:  # edit
            orig_pkg  = packages[orig_idx]
            old_name  = orig_pkg["name"]
            old_dir   = os.path.join(os.path.dirname(__file__), "Images", old_name)
            pkg_dir   = os.path.join(os.path.dirname(__file__), "Images", name)

            # Rename folder if name changed
            if old_name != name and os.path.isdir(old_dir):
                os.rename(old_dir, pkg_dir)
            os.makedirs(pkg_dir, exist_ok=True)

            fp_dest    = orig_pkg.get("footprint", "")
            img3d_dest = orig_pkg.get("image3d",   "")

            # Remap paths to new folder if name changed
            if old_name != name:
                if fp_dest:
                    fp_dest    = fp_dest.replace(old_dir, pkg_dir)
                if img3d_dest:
                    img3d_dest = img3d_dest.replace(old_dir, pkg_dir)

            # Overwrite footprint if a new file was picked
            if pkg_images["footprint"] and pkg_images["footprint"] != orig_pkg.get("footprint", ""):
                ext     = os.path.splitext(pkg_images["footprint"])[1]
                fp_dest = os.path.join(pkg_dir, f"footprint{ext}")
                shutil.copy2(pkg_images["footprint"], fp_dest)

            # Overwrite 3d if a new file was picked
            if pkg_images["3d"] and pkg_images["3d"] != orig_pkg.get("image3d", ""):
                ext        = os.path.splitext(pkg_images["3d"])[1]
                img3d_dest = os.path.join(pkg_dir, f"3d{ext}")
                shutil.copy2(pkg_images["3d"], img3d_dest)

            packages[orig_idx] = {"name": name, "pins": pins, "footprint": fp_dest, "image3d": img3d_dest}
            # Invalidate 3d mesh cache for old/new paths
            _mesh_cache.pop(orig_pkg.get("image3d", ""), None)
            _mesh_cache.pop(img3d_dest, None)

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
        del_pkg_panel.visible = True
        if del_btn_ref.current:
            del_btn_ref.current.disabled = True
            del_btn_ref.current.opacity  = 0.35
        page.window.min_height = 260
        page.window.height     = 260
        page.window.update()
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
                            ft.Icon(ft.Icons.MEMORY, size=16),
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
        needed_height = max(260, 180 + len(packages) * 42)
        page.window.min_height = needed_height
        page.window.height     = needed_height
        page.window.update()
        page.update()

    # ── Panels ────────────────────────────────────────────────────────────────
    pkg_list_col = ft.Column([], spacing=6)

    pkg_list_panel = ft.Container(
        visible=False,
        padding=ft.padding.symmetric(horizontal=24, vertical=12),
        content=ft.Column(
            [
                ft.Text(s.get("show_packages", "Show Packages"), size=16, weight=ft.FontWeight.W_600, color=ft.Colors.BLUE),
                ft.Divider(height=1),
                pkg_list_col,
            ],
            spacing=10,
        ),
    )

    new_sym_panel = ft.Container(
        visible=False,
        padding=ft.padding.symmetric(horizontal=24, vertical=12),
        content=ft.Column(
            [
                ft.Text(s.get("new_symbol", "New Symbol"), size=16, weight=ft.FontWeight.W_600),
                sym_name_field,
                pkg_dropdown,
                ft.Row(
                    [
                        ft.Column(
                            [fp_preview_label, fp_preview_img],
                            spacing=4,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Column(
                            [
                                view3d_label,
                                ft.GestureDetector(
                                    content=ft.Container(
                                        width=200,
                                        height=200,
                                        border=ft.border.all(1, ft.Colors.BLUE_700),
                                        border_radius=8,
                                        clip_behavior=ft.ClipBehavior.HARD_EDGE,
                                        bgcolor="#1a1a2e",
                                        content=ft.Stack(
                                            [
                                                ft.Image(
                                                    ref=view3d_img_ref,
                                                    src=b"",
                                                    width=200,
                                                    height=200,
                                                    fit=ft.BoxFit.CONTAIN,
                                                    visible=False,
                                                ),
                                                ft.Container(
                                                    ref=view3d_ring_ref,
                                                    width=200,
                                                    height=200,
                                                    alignment=ft.Alignment(0, 0),
                                                    content=ft.ProgressRing(width=32, height=32, stroke_width=3),
                                                    visible=False,
                                                ),
                                            ]
                                        ),
                                    ),
                                    on_scroll=_on_3d_scroll,
                                    on_pan_update=_on_3d_pan,
                                ),
                            ],
                            spacing=4,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    ],
                    spacing=16,
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
            ],
            spacing=12,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )

    add_pkg_panel = ft.Container(
        visible=False,
        padding=ft.padding.symmetric(horizontal=24, vertical=12),
        content=ft.Column(
            [
                ft.Text(
                    ref=add_pkg_panel_title_ref,
                    value=s.get("add_package", "Add Package"),
                    size=16,
                    weight=ft.FontWeight.W_600,
                    color=ft.Colors.ORANGE,
                ),
                edit_sel_container,
                ft.Container(
                    ref=edit_fields_container_ref,
                    content=ft.Column(
                        [
                            pkg_name_field,
                            pkg_pins_field,
                            ft.Column(
                                [
                                    ft.Text("Images", size=12, weight=ft.FontWeight.W_500),
                                    ft.Column(
                                        [
                                            ft.ElevatedButton("2D", icon=ft.Icons.IMAGE, on_click=pick_footprint),
                                            fp_path_text,
                                            ft.ElevatedButton("3D", icon=ft.Icons.VIEW_IN_AR, on_click=pick_3d),
                                            img3d_path_text,
                                        ],
                                        spacing=4,
                                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                    ),
                                ],
                                spacing=6,
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            ft.Row(
                                [
                                    ft.ElevatedButton(
                                        s.get("save", "Save"),
                                        ref=save_pkg_btn_ref,
                                        icon=ft.Icons.SAVE,
                                        on_click=save_package,
                                        color=ft.Colors.WHITE,
                                        bgcolor=ft.Colors.GREEN_700,
                                        disabled=True,
                                        opacity=0.35,
                                    ),
                                    ft.ElevatedButton(
                                        s.get("close", "Cancel"),
                                        on_click=cancel_add_pkg,
                                        color=ft.Colors.WHITE,
                                        bgcolor=ft.Colors.GREY_600,
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
                    color=ft.Colors.ORANGE,
                ),
                del_pkg_dd,
                ft.Row(
                    [
                        ft.ElevatedButton(
                            s.get("delete", "Delete"),
                            ref=del_btn_ref,
                            icon=ft.Icons.DELETE,
                            color=ft.Colors.RED,
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
                            icon=ft.Icons.ADD_BOX,
                            icon_color=ft.Colors.GREEN,
                            tooltip=s.get("new_symbol", "New Symbol"),
                            on_click=new_symbol,
                            disabled=len(packages) == 0,
                            opacity=1.0 if len(packages) > 0 else 0.35,
                        ),
                        ft.IconButton(
                            ref=edit_sym_btn_ref,
                            icon=ft.Icons.EDIT,
                            icon_color=ft.Colors.TEAL,
                            tooltip=s.get("edit_symbol", "Edit Symbol"),
                            on_click=edit_symbol,
                            disabled=len(packages) == 0,
                            opacity=1.0 if len(packages) > 0 else 0.35,
                        ),
                        ft.IconButton(
                            icon=ft.Icons.MEMORY,
                            icon_color=ft.Colors.BLUE,
                            tooltip=s.get("add_package", "Add Package"),
                            on_click=show_add_package,
                        ),
                        ft.IconButton(
                            icon=ft.Icons.EDIT_NOTE,
                            icon_color=ft.Colors.TEAL,
                            tooltip=s.get("edit_package", "Edit Package"),
                            on_click=show_edit_package,
                        ),
                        ft.IconButton(
                            icon=ft.Icons.LIST_ALT,
                            icon_color=ft.Colors.PURPLE,
                            tooltip=s.get("show_packages", "Show Packages"),
                            on_click=show_packages,
                        ),
                        ft.IconButton(
                            icon=ft.Icons.DELETE_SWEEP,
                            icon_color=ft.Colors.RED,
                            tooltip=s.get("delete_package", "Delete Package"),
                            on_click=show_delete_package,
                        ),
                    ],
                    spacing=0,
                ),
                ft.Row(
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
                        ft.IconButton(icon=ft.Icons.WB_SUNNY, tooltip=s["toggle_theme"], on_click=toggle_theme),
                        ft.PopupMenuButton(
                            icon=ft.Icons.HELP,
                            tooltip=s["help"],
                            items=[
                                ft.PopupMenuItem(content=ft.Row([ft.Icon(ft.Icons.INFO), ft.Text(s["about"])], spacing=8), on_click=show_about),
                                ft.PopupMenuItem(content=ft.Row([ft.Icon(ft.Icons.MENU_BOOK), ft.Text(s["user_manual"])], spacing=8), on_click=show_user_manual),
                                ft.PopupMenuItem(content=ft.Row([ft.Icon(ft.Icons.ARTICLE), ft.Text(s["release_notes"])], spacing=8), on_click=show_release_notes),
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
