"""
SecurePad - Main UI (Flet)
==========================
Dark/Light mode, auto-lock (10 min), find & replace,
font controls, export/import .key recovery.
"""

import flet as ft
import os
import threading
import time
from typing import Optional

from .crypto_engine import (
    encrypt_content,
    decrypt_content,
    export_recovery_key,
    decrypt_with_recovery_key,
    get_key_id_from_file,
    get_salt_from_file,
    SecurityError,
    secure_wipe,
    secure_wipe_str,
)

# ──────────────────────────────────────────────────────────
# App State
# ──────────────────────────────────────────────────────────
APP_NAME    = "SecurePad"
LOCK_SECS   = 600   # 10 minutes
FONTS_MONO  = ["Courier New", "Consolas", "Menlo", "DejaVu Sans Mono"]
FONTS_SANS  = ["Segoe UI", "Roboto", "Arial", "Helvetica"]

DARK = {
    "bg":        "#111111",
    "surface":   "#1A1A1A",
    "panel":     "#222222",
    "border":    "#333333",
    "text":      "#E0E0E0",
    "muted":     "#777777",
    "accent":    "#4A9EFF",
    "danger":    "#FF4444",
    "success":   "#44BB77",
}
LIGHT = {
    "bg":        "#F5F5F5",
    "surface":   "#FFFFFF",
    "panel":     "#EBEBEB",
    "border":    "#CCCCCC",
    "text":      "#1A1A1A",
    "muted":     "#888888",
    "accent":    "#1565C0",
    "danger":    "#C62828",
    "success":   "#2E7D32",
}


def main(page: ft.Page):
    # ── Page setup ──────────────────────────────────────────
    page.title       = APP_NAME
    page.window_width  = 900
    page.window_height = 650
    page.window_min_width  = 600
    page.window_min_height = 400
    page.padding     = 0
    page.spacing     = 0

    # ── App state ────────────────────────────────────────────
    state = {
        "dark_mode":     True,
        "font_family":   "Courier New",
        "font_size":     14,
        "current_file":  None,        # path str
        "file_bytes":    None,        # bytes of open .spd
        "key_id":        None,        # bytes
        "salt":          None,        # bytes
        "unlocked":      False,
        "dirty":         False,       # unsaved changes
        "last_activity": time.time(),
        "lock_timer":    None,
    }

    # ── Theme helpers ────────────────────────────────────────
    def C(key: str) -> str:
        return (DARK if state["dark_mode"] else LIGHT)[key]

    def apply_theme():
        page.bgcolor = C("bg")
        page.update()

    # ── Activity reset ───────────────────────────────────────
    def touch():
        state["last_activity"] = time.time()

    # ── Auto-lock timer ──────────────────────────────────────
    def lock_loop():
        while True:
            time.sleep(5)
            if state["unlocked"]:
                idle = time.time() - state["last_activity"]
                if idle >= LOCK_SECS:
                    do_lock()

    lock_thread = threading.Thread(target=lock_loop, daemon=True)
    lock_thread.start()

    # ──────────────────────────────────────────────────────────
    # Controls (declared early so callbacks can reference them)
    # ──────────────────────────────────────────────────────────
    editor = ft.TextField(
        multiline=True,
        expand=True,
        border=ft.InputBorder.NONE,
        cursor_color="#4A9EFF",
        text_style=ft.TextStyle(
            font_family="Courier New",
            size=14,
            color="#E0E0E0",
        ),
        bgcolor="transparent",
        on_change=lambda e: (touch(), mark_dirty()),
    )

    status_bar = ft.Text("", size=11, color=DARK["muted"])
    title_text = ft.Text(APP_NAME, size=14, weight=ft.FontWeight.W_500)

    # ── Password dialog ──────────────────────────────────────
    pwd_field = ft.TextField(
        password=True,
        can_reveal_password=True,
        label="Contraseña Maestra",
        border_color="#4A9EFF",
        focused_border_color="#4A9EFF",
        text_style=ft.TextStyle(font_family="Courier New"),
        autofocus=True,
    )
    pwd_error = ft.Text("", color=DARK["danger"], size=12)
    pwd_title = ft.Text("Desbloquear archivo", size=16, weight=ft.FontWeight.W_600)
    pwd_hint  = ft.Text("", size=11, color=DARK["muted"])

    # ── Find & Replace bar ───────────────────────────────────
    find_field    = ft.TextField(label="Buscar",      dense=True, width=200)
    replace_field = ft.TextField(label="Reemplazar",  dense=True, width=200)
    find_bar_visible = ft.Ref[ft.Row]()

    # ──────────────────────────────────────────────────────────
    # Core actions
    # ──────────────────────────────────────────────────────────
    def mark_dirty():
        if not state["dirty"]:
            state["dirty"] = True
            update_title()

    def update_title():
        fname = os.path.basename(state["current_file"]) if state["current_file"] else "Sin título"
        dirty = " •" if state["dirty"] else ""
        locked = " 🔒" if not state["unlocked"] else ""
        title_text.value = f"{APP_NAME}  —  {fname}{dirty}{locked}"
        page.update()

    def set_status(msg: str, color: str = ""):
        status_bar.value = msg
        status_bar.color = color or C("muted")
        page.update()

    def do_lock():
        state["unlocked"] = False
        editor.value = ""
        # Wipe any password held in memory
        secure_wipe_str(pwd_field.value or "")
        pwd_field.value = ""
        show_lock_screen()
        update_title()
        set_status("🔒 Sesión bloqueada por inactividad.")

    # ──────────────────────────────────────────────────────────
    # Lock / unlock screen
    # ──────────────────────────────────────────────────────────
    lock_screen  = ft.Ref[ft.Container]()
    editor_area  = ft.Ref[ft.Column]()

    def show_lock_screen():
        if lock_screen.current:
            lock_screen.current.visible = True
        if editor_area.current:
            editor_area.current.visible = False
        page.update()

    def hide_lock_screen():
        if lock_screen.current:
            lock_screen.current.visible = False
        if editor_area.current:
            editor_area.current.visible = True
        page.update()

    def attempt_unlock(e=None):
        touch()
        pwd = pwd_field.value or ""
        if not pwd:
            pwd_error.value = "Ingresa tu contraseña."
            page.update()
            return

        if state["file_bytes"] is None:
            # New unlock with no file → just open editor blank
            state["unlocked"] = True
            pwd_error.value = ""
            hide_lock_screen()
            update_title()
            return

        try:
            set_status("⏳ Derivando clave… (puede tardar unos segundos)")
            page.update()
            plaintext = decrypt_content(state["file_bytes"], pwd)
            state["unlocked"] = True
            editor.value = plaintext
            editor.text_style = ft.TextStyle(
                font_family=state["font_family"],
                size=state["font_size"],
                color=C("text"),
            )
            pwd_error.value = ""
            secure_wipe_str(pwd)
            pwd_field.value = ""
            hide_lock_screen()
            update_title()
            set_status(f"✅ Archivo abierto: {os.path.basename(state['current_file'])}", C("success"))
        except SecurityError as ex:
            pwd_error.value = str(ex)
            secure_wipe_str(pwd)
            pwd_field.value = ""
            set_status("❌ Firma de Seguridad Inválida.", C("danger"))
        except Exception as ex:
            pwd_error.value = f"Error: {ex}"
            set_status("❌ Error al abrir el archivo.", C("danger"))
        page.update()

    pwd_field.on_submit = attempt_unlock

    # ──────────────────────────────────────────────────────────
    # File operations
    # ──────────────────────────────────────────────────────────
    def new_file(e=None):
        touch()
        state["current_file"] = None
        state["file_bytes"]   = None
        state["key_id"]       = None
        state["salt"]         = None
        state["unlocked"]     = False
        state["dirty"]        = False
        editor.value = ""
        pwd_field.value = ""
        pwd_error.value = ""
        pwd_title.value = "Nueva nota — establece contraseña"
        pwd_hint.value  = "Esta será la contraseña para cifrar el archivo."
        show_lock_screen()
        update_title()
        set_status("📄 Nueva nota. Define una contraseña para guardar.")

    def open_file_picker_result(e: ft.FilePickerResultEvent):
        touch()
        if not e.files:
            return
        path = e.files[0].path
        try:
            with open(path, "rb") as f:
                raw = f.read()
            state["current_file"] = path
            state["file_bytes"]   = raw
            state["key_id"]       = get_key_id_from_file(raw)
            state["salt"]         = get_salt_from_file(raw)
            state["unlocked"]     = False
            state["dirty"]        = False
            editor.value = ""
            pwd_field.value = ""
            pwd_error.value = ""
            pwd_title.value = f"Abrir: {os.path.basename(path)}"
            pwd_hint.value  = "Ingresa la contraseña maestra para descifrar."
            show_lock_screen()
            update_title()
            set_status(f"📂 Archivo cargado: {os.path.basename(path)}")
        except Exception as ex:
            set_status(f"❌ Error al leer archivo: {ex}", C("danger"))

    def save_file_picker_result(e: ft.FilePickerResultEvent):
        touch()
        if not e.path:
            return
        path = e.path if e.path.endswith(".spd") else e.path + ".spd"
        do_save(path)

    def do_save(path: str):
        pwd = pwd_field.value or ""
        # If we have a password prompt open (new file), use that pwd
        # If already unlocked, ask for confirmation password via mini dialog
        if not state["unlocked"] and not pwd:
            set_status("⚠️ Ingresa la contraseña antes de guardar.", C("danger"))
            return

        # For new files, use the pwd_field value; for open files ask re-encrypt
        save_pwd = pwd if not state["unlocked"] else None

        if save_pwd is None:
            # Already unlocked → reuse last password (ask via dialog)
            open_save_password_dialog(path)
            return

        _execute_save(path, save_pwd)

    save_pwd_field = ft.TextField(
        password=True,
        can_reveal_password=True,
        label="Contraseña para cifrar",
        autofocus=True,
        border_color="#4A9EFF",
        text_style=ft.TextStyle(font_family="Courier New"),
    )
    save_error = ft.Text("", color=DARK["danger"], size=12)

    def open_save_password_dialog(path: str):
        def confirm(e):
            p = save_pwd_field.value or ""
            if not p:
                save_error.value = "La contraseña no puede estar vacía."
                page.update()
                return
            dlg.open = False
            page.update()
            _execute_save(path, p)
            secure_wipe_str(p)
            save_pwd_field.value = ""

        save_pwd_field.on_submit = confirm
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Guardar como"),
            content=ft.Column([
                ft.Text("Ingresa la contraseña para re-cifrar el archivo.", size=13),
                save_pwd_field,
                save_error,
            ], tight=True),
            actions=[
                ft.TextButton("Guardar", on_click=confirm),
                ft.TextButton("Cancelar", on_click=lambda e: setattr(dlg, "open", False) or page.update()),
            ],
        )
        page.dialog = dlg
        dlg.open = True
        page.update()

    def _execute_save(path: str, password: str):
        try:
            set_status("⏳ Cifrando…")
            page.update()
            file_bytes, key_id = encrypt_content(editor.value or "", password)
            with open(path, "wb") as f:
                f.write(file_bytes)
            state["current_file"] = path
            state["file_bytes"]   = file_bytes
            state["key_id"]       = key_id
            state["salt"]         = get_salt_from_file(file_bytes)
            state["unlocked"]     = True
            state["dirty"]        = False
            secure_wipe_str(password)
            hide_lock_screen()
            update_title()
            set_status(f"💾 Guardado: {os.path.basename(path)}", C("success"))
        except Exception as ex:
            set_status(f"❌ Error al guardar: {ex}", C("danger"))

    # ──────────────────────────────────────────────────────────
    # Recovery key export/import
    # ──────────────────────────────────────────────────────────
    rec_master_pwd  = ft.TextField(password=True, can_reveal_password=True,
                                    label="Contraseña Maestra actual",
                                    text_style=ft.TextStyle(font_family="Courier New"))
    rec_export_pwd  = ft.TextField(password=True, can_reveal_password=True,
                                    label="Contraseña para el archivo .key",
                                    text_style=ft.TextStyle(font_family="Courier New"))
    rec_export_err  = ft.Text("", color=DARK["danger"], size=12)

    def open_export_key_dialog(e=None):
        if not state["current_file"] or not state["unlocked"]:
            set_status("⚠️ Abre y desbloquea un archivo primero.", C("danger"))
            return

        def do_export(e):
            mp = rec_master_pwd.value or ""
            rp = rec_export_pwd.value or ""
            if not mp or not rp:
                rec_export_err.value = "Ambas contraseñas son requeridas."
                page.update()
                return
            try:
                key_bytes = export_recovery_key(
                    mp,
                    state["salt"],
                    state["key_id"],
                    rp,
                )
                out_path = state["current_file"].replace(".spd", "") + ".key"
                with open(out_path, "wb") as f:
                    f.write(key_bytes)
                dlg.open = False
                page.update()
                secure_wipe_str(mp)
                secure_wipe_str(rp)
                rec_master_pwd.value = ""
                rec_export_pwd.value = ""
                set_status(f"🔑 Archivo .key exportado: {os.path.basename(out_path)}", C("success"))
            except SecurityError as ex:
                rec_export_err.value = str(ex)
                page.update()
            except Exception as ex:
                rec_export_err.value = f"Error: {ex}"
                page.update()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Exportar Clave de Recuperación"),
            content=ft.Column([
                ft.Text("Genera un archivo .key para recuperar tu nota si olvidas la contraseña.", size=12),
                rec_master_pwd,
                rec_export_pwd,
                rec_export_err,
            ], tight=True, width=380),
            actions=[
                ft.TextButton("Exportar .key", on_click=do_export),
                ft.TextButton("Cancelar", on_click=lambda e: setattr(dlg, "open", False) or page.update()),
            ],
        )
        page.dialog = dlg
        dlg.open = True
        page.update()

    def open_import_key_dialog(e=None):
        rec_file_path = ft.Ref[str]()
        rec_spd_path  = ft.Ref[str]()
        rec_import_pwd = ft.TextField(password=True, can_reveal_password=True,
                                       label="Contraseña del archivo .key",
                                       text_style=ft.TextStyle(font_family="Courier New"))
        rec_import_err = ft.Text("", color=DARK["danger"], size=12)
        rec_key_label  = ft.Text("Sin archivo .key seleccionado", size=12, color=DARK["muted"])
        rec_spd_label  = ft.Text("Sin archivo .spd seleccionado", size=12, color=DARK["muted"])

        def key_picked(ev: ft.FilePickerResultEvent):
            if ev.files:
                rec_file_path.current = ev.files[0].path
                rec_key_label.value = os.path.basename(ev.files[0].path)
                page.update()

        def spd_picked(ev: ft.FilePickerResultEvent):
            if ev.files:
                rec_spd_path.current = ev.files[0].path
                rec_spd_label.value = os.path.basename(ev.files[0].path)
                page.update()

        fp_key = ft.FilePicker(on_result=key_picked)
        fp_spd = ft.FilePicker(on_result=spd_picked)
        page.overlay.extend([fp_key, fp_spd])

        def do_import(e):
            rp = rec_import_pwd.value or ""
            kp = rec_file_path.current
            sp = rec_spd_path.current
            if not rp or not kp or not sp:
                rec_import_err.value = "Selecciona ambos archivos e ingresa la contraseña."
                page.update()
                return
            try:
                with open(kp, "rb") as f:
                    key_bytes = f.read()
                with open(sp, "rb") as f:
                    spd_bytes = f.read()
                plaintext, _ = decrypt_with_recovery_key(spd_bytes, key_bytes, rp)
                state["current_file"] = sp
                state["file_bytes"]   = spd_bytes
                state["key_id"]       = get_key_id_from_file(spd_bytes)
                state["salt"]         = get_salt_from_file(spd_bytes)
                state["unlocked"]     = True
                state["dirty"]        = False
                editor.value = plaintext
                dlg.open = False
                page.update()
                secure_wipe_str(rp)
                rec_import_pwd.value = ""
                hide_lock_screen()
                update_title()
                set_status("🔑 Archivo recuperado con .key", C("success"))
            except SecurityError as ex:
                rec_import_err.value = str(ex)
                page.update()
            except Exception as ex:
                rec_import_err.value = f"Error: {ex}"
                page.update()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Recuperar con archivo .key"),
            content=ft.Column([
                ft.Text("Selecciona el archivo .spd cifrado y el .key de recuperación.", size=12),
                ft.Row([
                    ft.ElevatedButton("Elegir .spd", on_click=lambda e: fp_spd.pick_files(
                        allowed_extensions=["spd"])),
                    rec_spd_label,
                ]),
                ft.Row([
                    ft.ElevatedButton("Elegir .key", on_click=lambda e: fp_key.pick_files(
                        allowed_extensions=["key"])),
                    rec_key_label,
                ]),
                rec_import_pwd,
                rec_import_err,
            ], tight=True, width=420),
            actions=[
                ft.TextButton("Recuperar", on_click=do_import),
                ft.TextButton("Cancelar", on_click=lambda e: setattr(dlg, "open", False) or page.update()),
            ],
        )
        page.dialog = dlg
        dlg.open = True
        page.update()

    # ──────────────────────────────────────────────────────────
    # Find & Replace
    # ──────────────────────────────────────────────────────────
    find_bar_row = ft.Ref[ft.Container]()

    def toggle_find_bar(e=None):
        touch()
        if find_bar_row.current:
            find_bar_row.current.visible = not find_bar_row.current.visible
            page.update()

    def do_find(e=None):
        touch()
        needle = find_field.value or ""
        text   = editor.value or ""
        if needle and needle in text:
            idx = text.index(needle)
            set_status(f"🔍 '{needle}' encontrado en posición {idx}.", C("accent"))
        else:
            set_status(f"🔍 '{needle}' no encontrado.", C("muted"))

    def do_replace(e=None):
        touch()
        needle  = find_field.value or ""
        replace = replace_field.value or ""
        if needle and editor.value:
            new_text = editor.value.replace(needle, replace)
            count = editor.value.count(needle)
            editor.value = new_text
            mark_dirty()
            set_status(f"🔄 {count} reemplazo(s) realizados.", C("success"))
            page.update()

    # ──────────────────────────────────────────────────────────
    # Settings dialog
    # ──────────────────────────────────────────────────────────
    def open_settings(e=None):
        touch()
        font_dd = ft.Dropdown(
            label="Tipo de letra",
            value=state["font_family"],
            options=[ft.dropdown.Option(f) for f in FONTS_MONO + FONTS_SANS],
            width=220,
        )
        size_slider = ft.Slider(
            min=10, max=28, value=state["font_size"],
            divisions=18, label="{value}",
        )
        theme_sw = ft.Switch(label="Modo oscuro", value=state["dark_mode"])

        def apply_settings(e):
            state["font_family"] = font_dd.value
            state["font_size"]   = int(size_slider.value)
            state["dark_mode"]   = theme_sw.value
            editor.text_style = ft.TextStyle(
                font_family=state["font_family"],
                size=state["font_size"],
                color=C("text"),
            )
            apply_theme()
            dlg.open = False
            page.update()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Ajustes"),
            content=ft.Column([
                font_dd,
                ft.Text("Tamaño de fuente", size=13),
                size_slider,
                theme_sw,
            ], tight=True, width=300),
            actions=[
                ft.TextButton("Aplicar", on_click=apply_settings),
                ft.TextButton("Cancelar", on_click=lambda e: setattr(dlg, "open", False) or page.update()),
            ],
        )
        page.dialog = dlg
        dlg.open = True
        page.update()

    # ──────────────────────────────────────────────────────────
    # File pickers
    # ──────────────────────────────────────────────────────────
    fp_open = ft.FilePicker(on_result=open_file_picker_result)
    fp_save = ft.FilePicker(on_result=save_file_picker_result)
    page.overlay.extend([fp_open, fp_save])

    def open_file(e=None):
        touch()
        fp_open.pick_files(allowed_extensions=["spd"], dialog_title="Abrir archivo SecurePad")

    def save_file_as(e=None):
        touch()
        if not state["unlocked"] and state["file_bytes"] is None:
            # New file: set password from pwd_field
            if not pwd_field.value:
                set_status("⚠️ Establece una contraseña primero.", C("danger"))
                return
        fp_save.save_file(
            file_name="nota.spd",
            dialog_title="Guardar archivo SecurePad",
            allowed_extensions=["spd"],
        )

    def save_file(e=None):
        touch()
        if state["current_file"] and state["unlocked"]:
            open_save_password_dialog(state["current_file"])
        else:
            save_file_as()

    # ──────────────────────────────────────────────────────────
    # Keyboard shortcuts
    # ──────────────────────────────────────────────────────────
    def on_keyboard(e: ft.KeyboardEvent):
        touch()
        ctrl = e.ctrl
        if ctrl and e.key == "S":
            save_file()
        elif ctrl and e.key == "O":
            open_file()
        elif ctrl and e.key == "N":
            new_file()
        elif ctrl and e.key == "F":
            toggle_find_bar()
        elif ctrl and e.key == "L":
            do_lock()

    page.on_keyboard_event = on_keyboard

    # ──────────────────────────────────────────────────────────
    # Build UI
    # ──────────────────────────────────────────────────────────

    # ── Toolbar ─────────────────────────────────────────────
    def btn(icon, tooltip, action, color=None):
        return ft.IconButton(
            icon=icon,
            tooltip=tooltip,
            on_click=action,
            icon_color=color or C("text"),
            icon_size=19,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=6),
                padding=ft.padding.all(6),
            ),
        )

    toolbar = ft.Container(
        content=ft.Row([
            title_text,
            ft.Container(expand=True),
            btn(ft.icons.ADD_OUTLINED,      "Nuevo  Ctrl+N",       new_file),
            btn(ft.icons.FOLDER_OPEN_OUTLINED, "Abrir  Ctrl+O",    open_file),
            btn(ft.icons.SAVE_OUTLINED,     "Guardar  Ctrl+S",     save_file),
            ft.VerticalDivider(width=1, color=C("border")),
            btn(ft.icons.SEARCH_OUTLINED,   "Buscar  Ctrl+F",      toggle_find_bar),
            btn(ft.icons.SETTINGS_OUTLINED, "Ajustes",             open_settings),
            ft.VerticalDivider(width=1, color=C("border")),
            btn(ft.icons.KEY_OUTLINED,      "Exportar .key",       open_export_key_dialog, C("accent")),
            btn(ft.icons.LOCK_RESET_OUTLINED,"Recuperar con .key", open_import_key_dialog, C("accent")),
            btn(ft.icons.LOCK_OUTLINED,     "Bloquear  Ctrl+L",    do_lock, C("danger")),
        ], spacing=2, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        bgcolor=C("panel"),
        padding=ft.padding.symmetric(horizontal=12, vertical=6),
        border=ft.border.only(bottom=ft.BorderSide(1, C("border"))),
    )

    # ── Find bar ────────────────────────────────────────────
    find_bar = ft.Container(
        ref=find_bar_row,
        visible=False,
        content=ft.Row([
            find_field,
            replace_field,
            ft.ElevatedButton("Buscar",      on_click=do_find,    height=36),
            ft.ElevatedButton("Reemplazar",  on_click=do_replace, height=36),
            ft.IconButton(ft.icons.CLOSE, on_click=toggle_find_bar, icon_size=16),
        ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        bgcolor=C("panel"),
        padding=ft.padding.symmetric(horizontal=12, vertical=6),
        border=ft.border.only(bottom=ft.BorderSide(1, C("border"))),
    )

    # ── Editor area ─────────────────────────────────────────
    editor_column = ft.Column(
        ref=editor_area,
        visible=False,
        controls=[
            find_bar,
            ft.Container(
                content=editor,
                expand=True,
                bgcolor=C("surface"),
                padding=ft.padding.all(16),
            ),
        ],
        expand=True,
        spacing=0,
    )

    # ── Lock screen ─────────────────────────────────────────
    lock_container = ft.Container(
        ref=lock_screen,
        visible=True,
        expand=True,
        bgcolor=C("bg"),
        content=ft.Column([
            ft.Container(height=60),
            ft.Icon(ft.icons.LOCK_OUTLINED, size=56, color=C("accent")),
            ft.Container(height=16),
            pwd_title,
            ft.Container(height=8),
            ft.Container(
                content=ft.Column([
                    pwd_hint,
                    ft.Container(height=8),
                    pwd_field,
                    ft.Container(height=6),
                    pwd_error,
                    ft.Container(height=16),
                    ft.Row([
                        ft.ElevatedButton(
                            "Desbloquear",
                            icon=ft.icons.LOCK_OPEN_OUTLINED,
                            on_click=attempt_unlock,
                            style=ft.ButtonStyle(
                                bgcolor=C("accent"),
                                color=ft.colors.WHITE,
                                shape=ft.RoundedRectangleBorder(radius=8),
                                padding=ft.padding.symmetric(horizontal=24, vertical=12),
                            ),
                        ),
                    ], alignment=ft.MainAxisAlignment.CENTER),
                    ft.Container(height=24),
                    ft.Row([
                        ft.TextButton(
                            "📂 Abrir otro archivo",
                            on_click=open_file,
                        ),
                        ft.TextButton(
                            "🔑 Recuperar con .key",
                            on_click=open_import_key_dialog,
                        ),
                    ], alignment=ft.MainAxisAlignment.CENTER),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, tight=True),
                width=380,
                bgcolor=C("surface"),
                border_radius=12,
                padding=ft.padding.all(28),
                border=ft.border.all(1, C("border")),
            ),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
    )

    # ── Status bar ──────────────────────────────────────────
    status = ft.Container(
        content=ft.Row([
            status_bar,
            ft.Container(expand=True),
            ft.Text("AES-256-GCM · PBKDF2·200K", size=10, color=C("muted")),
        ]),
        bgcolor=C("panel"),
        padding=ft.padding.symmetric(horizontal=12, vertical=4),
        border=ft.border.only(top=ft.BorderSide(1, C("border"))),
    )

    # ── Root layout ─────────────────────────────────────────
    page.add(
        ft.Column([
            toolbar,
            ft.Stack([
                lock_container,
                editor_column,
            ], expand=True),
            status,
        ], spacing=0, expand=True)
    )

    apply_theme()
    set_status("🔒 Bienvenido a SecurePad. Abre un archivo o crea uno nuevo.")
    update_title()


def run():
    ft.app(target=main)
