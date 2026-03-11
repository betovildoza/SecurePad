"""
SecurePad - Main UI  (Flet 0.82)
===================================
REGLAS FLET 0.82 (auditadas directo en el codigo fuente):

- FilePicker():  auto-registro via context.page._services — NO page.add() ni overlay
- Dialogs:       page.show_dialog(dlg) / page.pop_dialog()  — NO page.dialog = dlg
- pick_files() / save_file(): async, retornan resultado directo
- main(): async def
- ft.run(main)
- ft.Icons.* / ft.Colors.*
"""

import flet as ft
import os
import asyncio
import threading
import time

from .crypto_engine import (
    encrypt_content,
    decrypt_content,
    export_recovery_key,
    decrypt_with_recovery_key,
    get_key_id_from_file,
    get_salt_from_file,
    SecurityError,
    secure_wipe_str,
)

APP_NAME   = "SecurePad"
LOCK_SECS  = 600
FONTS_MONO = ["Courier New", "Consolas", "Menlo", "DejaVu Sans Mono"]
FONTS_SANS = ["Segoe UI", "Roboto", "Arial", "Helvetica"]

DARK = {
    "bg": "#111111", "surface": "#1A1A1A", "panel": "#222222",
    "border": "#333333", "text": "#E0E0E0", "muted": "#666666",
    "accent": "#4A9EFF", "danger": "#FF4444", "success": "#44BB77",
    "lineno": "#444444", "lineno_bg": "#161616",
}
LIGHT = {
    "bg": "#F5F5F5", "surface": "#FFFFFF", "panel": "#EBEBEB",
    "border": "#CCCCCC", "text": "#1A1A1A", "muted": "#888888",
    "accent": "#1565C0", "danger": "#C62828", "success": "#2E7D32",
    "lineno": "#AAAAAA", "lineno_bg": "#F0F0F0",
}


def _icon(name: str):
    try:
        return getattr(ft.Icons, name)
    except AttributeError:
        return getattr(ft.icons, name)


def _white():
    try:
        return ft.Colors.WHITE
    except AttributeError:
        return ft.colors.WHITE


# ── Dialog helper — usa page.show_dialog / page.pop_dialog ────────────────
def open_dialog(page: ft.Page, dlg: ft.AlertDialog):
    page.show_dialog(dlg)

def close_dialog(page: ft.Page):
    page.pop_dialog()


async def main(page: ft.Page):
    page.title   = APP_NAME
    page.padding = 0
    page.spacing = 0

    try:
        page.window.width      = 900
        page.window.height     = 950
        page.window.min_width  = 600
        page.window.min_height = 400
    except AttributeError:
        page.window_width      = 900
        page.window_height     = 950

    # ── FilePickers: solo instanciar — se auto-registran solos ────────────
    fp_open = ft.FilePicker()
    fp_save = ft.FilePicker()
    fp_key  = ft.FilePicker()
    fp_spd  = ft.FilePicker()

    # ── State ──────────────────────────────────────────────────────────────
    state = {
        "dark_mode": True, "font_family": "Courier New", "font_size": 14,
        "current_file": None, "file_bytes": None, "key_id": None, "salt": None,
        "unlocked": False, "dirty": False, "last_activity": time.time(),
        "cursor_line": 1, "cursor_col": 1,
    }

    def C(k):
        return (DARK if state["dark_mode"] else LIGHT)[k]

    def touch():
        state["last_activity"] = time.time()

    # ── Auto-lock ──────────────────────────────────────────────────────────
    def _lock_watcher():
        while True:
            time.sleep(5)
            if state["unlocked"] and time.time() - state["last_activity"] >= LOCK_SECS:
                page.run_task(do_lock)

    threading.Thread(target=_lock_watcher, daemon=True).start()

    # ── Line numbers ───────────────────────────────────────────────────────
    line_numbers = ft.Text(
        "1",
        font_family="Courier New",
        size=14,
        color=DARK["lineno"],
        text_align=ft.TextAlign.RIGHT,
        no_wrap=True,
    )

    def update_line_numbers(text: str, cursor_offset: int = -1):
        lines = text.split("\n") if text else [""]
        n = len(lines)
        line_numbers.value = "\n".join(str(i + 1) for i in range(n))
        line_numbers.color = C("lineno")

        # Update cursor position in status bar
        if cursor_offset >= 0 and text:
            before = text[:cursor_offset]
            line   = before.count("\n") + 1
            col    = len(before.split("\n")[-1]) + 1
            state["cursor_line"] = line
            state["cursor_col"]  = col
        update_status_position()
        page.update()

    # ── Controls ───────────────────────────────────────────────────────────
    editor = ft.TextField(
        multiline=True, expand=True,
        border=ft.InputBorder.NONE,
        cursor_color="#4A9EFF",
        text_style=ft.TextStyle(font_family="Courier New", size=14, color="#E0E0E0"),
        bgcolor="transparent",
        on_change=lambda e: (touch(), mark_dirty(), update_line_numbers(e.control.value or "")),
        on_selection_change=lambda e: (
            touch(),
            update_line_numbers(
                editor.value or "",
                e.selection.base_offset if e.selection else -1,
            )
        ),
    )

    status_bar   = ft.Text("", size=11, color=DARK["muted"])
    cursor_info  = ft.Text("Ln 1, Col 1", size=11, color=DARK["muted"])
    title_text   = ft.Text(APP_NAME, size=14, weight=ft.FontWeight.W_500)

    def update_status_position():
        cursor_info.value = f"Ln {state['cursor_line']}, Col {state['cursor_col']}"

    pwd_field = ft.TextField(
        password=True, can_reveal_password=True, label="Contrasena Maestra",
        border_color="#4A9EFF", focused_border_color="#4A9EFF",
        text_style=ft.TextStyle(font_family="Courier New"), autofocus=True,
    )
    pwd_error = ft.Text("", color=DARK["danger"], size=12)
    pwd_title = ft.Text("Desbloquear archivo", size=16, weight=ft.FontWeight.W_600)
    pwd_hint  = ft.Text("", size=11, color=DARK["muted"])

    find_field    = ft.TextField(label="Buscar",     dense=True, width=200)
    replace_field = ft.TextField(label="Reemplazar", dense=True, width=200)
    find_result   = ft.Text("", size=11, color=DARK["muted"])

    lock_screen_ref = ft.Ref[ft.Container]()
    editor_area_ref = ft.Ref[ft.Column]()
    find_bar_ref    = ft.Ref[ft.Container]()

    # ── Helpers ────────────────────────────────────────────────────────────
    def mark_dirty():
        if not state["dirty"]:
            state["dirty"] = True
            update_title()

    def update_title():
        fname = os.path.basename(state["current_file"]) if state["current_file"] else "Sin titulo"
        mod   = "  *" if state["dirty"] else ""
        lck   = "  [BLOQUEADO]" if not state["unlocked"] else ""
        title_text.value = f"{APP_NAME}  -  {fname}{mod}{lck}"
        page.update()

    def set_status(msg, color=""):
        status_bar.value = msg
        status_bar.color = color or C("muted")
        page.update()

    def show_lock_screen():
        if lock_screen_ref.current: lock_screen_ref.current.visible = True
        if editor_area_ref.current: editor_area_ref.current.visible = False
        page.update()

    def hide_lock_screen():
        if lock_screen_ref.current: lock_screen_ref.current.visible = False
        if editor_area_ref.current: editor_area_ref.current.visible = True
        page.update()

    async def do_lock(e=None):
        state["unlocked"] = False
        editor.value = ""
        line_numbers.value = "1"
        secure_wipe_str(pwd_field.value or "")
        pwd_field.value = ""
        show_lock_screen(); update_title()
        set_status("Sesion bloqueada.")

    # ── Unlock ─────────────────────────────────────────────────────────────
    async def attempt_unlock(e=None):
        touch()
        pwd = pwd_field.value or ""
        if not pwd:
            pwd_error.value = "Ingresa tu contrasena."
            page.update(); return

        if state["file_bytes"] is None:
            state["unlocked"] = True
            pwd_error.value   = ""
            hide_lock_screen(); update_title()
            update_line_numbers("")
            set_status("Nueva nota lista. Guarda con Ctrl+S.")
            return

        try:
            set_status("Derivando clave... (puede tardar unos segundos)")
            page.update()
            loop      = asyncio.get_event_loop()
            plaintext = await loop.run_in_executor(
                None, decrypt_content, state["file_bytes"], pwd
            )
            state["unlocked"] = True
            editor.value      = plaintext
            editor.text_style = ft.TextStyle(
                font_family=state["font_family"],
                size=state["font_size"], color=C("text"),
            )
            update_line_numbers(plaintext)
            pwd_error.value = ""
            secure_wipe_str(pwd); pwd_field.value = ""
            hide_lock_screen(); update_title()
            set_status(f"Abierto: {os.path.basename(state['current_file'])}", C("success"))
        except SecurityError as ex:
            pwd_error.value = str(ex)
            secure_wipe_str(pwd); pwd_field.value = ""
            set_status("Firma de Seguridad Invalida.", C("danger"))
        except Exception as ex:
            pwd_error.value = f"Error: {ex}"
        page.update()

    pwd_field.on_submit = attempt_unlock

    # ── New file ───────────────────────────────────────────────────────────
    async def new_file(e=None):
        touch()
        state.update({"current_file": None, "file_bytes": None, "key_id": None,
                      "salt": None, "unlocked": False, "dirty": False})
        editor.value = ""; pwd_field.value = ""; pwd_error.value = ""
        line_numbers.value = "1"
        pwd_title.value = "Nueva nota - establece contrasena"
        pwd_hint.value  = "Esta sera la contrasena para cifrar el archivo."
        show_lock_screen(); update_title()
        set_status("Nueva nota. Define una contrasena y guarda con Ctrl+S.")

    # ── Open file ──────────────────────────────────────────────────────────
    async def open_file(e=None):
        touch()
        files = await fp_open.pick_files(
            dialog_title="Abrir archivo SecurePad",
            allowed_extensions=["spd"],
        )
        if not files: return
        path = files[0].path
        if not path:
            set_status("No se pudo obtener la ruta.", C("danger")); return
        try:
            with open(path, "rb") as f: raw = f.read()
            state.update({
                "current_file": path, "file_bytes": raw,
                "key_id": get_key_id_from_file(raw),
                "salt":   get_salt_from_file(raw),
                "unlocked": False, "dirty": False,
            })
            editor.value = ""; pwd_field.value = ""; pwd_error.value = ""
            pwd_title.value = f"Abrir: {os.path.basename(path)}"
            pwd_hint.value  = "Ingresa la contrasena maestra para descifrar."
            show_lock_screen(); update_title()
            set_status(f"Cargado: {os.path.basename(path)}")
        except Exception as ex:
            set_status(f"Error al leer: {ex}", C("danger"))

    # ── Save ───────────────────────────────────────────────────────────────
    async def save_file(e=None):
        touch()
        if state["current_file"] and state["unlocked"]:
            await _save_with_pwd_dialog(state["current_file"])
        else:
            await save_file_as()

    async def save_file_as(e=None):
        touch()
        if not state["unlocked"] and not state["file_bytes"] and not pwd_field.value:
            set_status("Establece una contrasena primero.", C("danger")); return
        path = await fp_save.save_file(
            file_name="nota.spd",
            dialog_title="Guardar archivo SecurePad",
            allowed_extensions=["spd"],
        )
        if not path: return
        if not path.endswith(".spd"): path += ".spd"
        if not state["unlocked"] and pwd_field.value:
            await _execute_save(path, pwd_field.value)
        else:
            await _save_with_pwd_dialog(path)

    async def _save_with_pwd_dialog(path: str):
        done   = asyncio.Event()
        result = {"pwd": None}

        spf = ft.TextField(
            password=True, can_reveal_password=True,
            label="Contrasena para cifrar", autofocus=True,
            border_color="#4A9EFF",
            text_style=ft.TextStyle(font_family="Courier New"),
        )
        serr = ft.Text("", color=DARK["danger"], size=12)

        async def confirm(e):
            p = spf.value or ""
            if not p:
                serr.value = "La contrasena no puede estar vacia."
                page.update(); return
            result["pwd"] = p
            close_dialog(page)
            done.set()

        async def cancel(e):
            close_dialog(page)
            done.set()

        spf.on_submit = confirm
        dlg = ft.AlertDialog(
            modal=True, title=ft.Text("Guardar archivo"),
            content=ft.Column([ft.Text("Contrasena para cifrar:"), spf, serr], tight=True),
            actions=[
                ft.TextButton("Guardar",  on_click=confirm),
                ft.TextButton("Cancelar", on_click=cancel),
            ],
        )
        open_dialog(page, dlg)
        await done.wait()
        if result["pwd"]:
            await _execute_save(path, result["pwd"])
            secure_wipe_str(result["pwd"]); result["pwd"] = None

    async def _execute_save(path: str, password: str):
        try:
            set_status("Cifrando..."); page.update()
            loop = asyncio.get_event_loop()
            file_bytes, key_id = await loop.run_in_executor(
                None, encrypt_content, editor.value or "", password
            )
            with open(path, "wb") as f: f.write(file_bytes)
            state.update({
                "current_file": path, "file_bytes": file_bytes,
                "key_id": key_id, "salt": get_salt_from_file(file_bytes),
                "unlocked": True, "dirty": False,
            })
            secure_wipe_str(password)
            hide_lock_screen(); update_title()
            set_status(f"Guardado: {os.path.basename(path)}", C("success"))
        except Exception as ex:
            set_status(f"Error al guardar: {ex}", C("danger"))

    # ── Export recovery key ────────────────────────────────────────────────
    async def open_export_key_dialog(e=None):
        if not state["current_file"] or not state["unlocked"]:
            set_status("Abre y desbloquea un archivo primero.", C("danger")); return

        rec_mp  = ft.TextField(password=True, can_reveal_password=True,
                               label="Contrasena Maestra actual",
                               text_style=ft.TextStyle(font_family="Courier New"))
        rec_rp  = ft.TextField(password=True, can_reveal_password=True,
                               label="Contrasena para el .key",
                               text_style=ft.TextStyle(font_family="Courier New"))
        rec_err = ft.Text("", color=DARK["danger"], size=12)

        async def do_export(e):
            mp = rec_mp.value or ""; rp = rec_rp.value or ""
            if not mp or not rp:
                rec_err.value = "Ambas contrasenas son requeridas."; page.update(); return
            try:
                key_bytes = export_recovery_key(mp, state["salt"], state["key_id"], rp)
                out_path  = state["current_file"].replace(".spd", "") + ".key"
                with open(out_path, "wb") as f: f.write(key_bytes)
                close_dialog(page)
                secure_wipe_str(mp); secure_wipe_str(rp)
                set_status(f"🔑 .key exportado: {os.path.basename(out_path)}", C("success"))
            except SecurityError as ex:
                rec_err.value = str(ex); page.update()
            except Exception as ex:
                rec_err.value = f"Error: {ex}"; page.update()

        open_dialog(page, ft.AlertDialog(
            modal=True, title=ft.Text("Exportar Clave de Recuperacion"),
            content=ft.Column([
                ft.Text("Genera un .key para recuperar tu nota.", size=12),
                rec_mp, rec_rp, rec_err,
            ], tight=True, width=380),
            actions=[
                ft.TextButton("Exportar .key", on_click=do_export),
                ft.TextButton("Cancelar", on_click=lambda e: close_dialog(page)),
            ],
        ))

    # ── Import recovery key ────────────────────────────────────────────────
    async def open_import_key_dialog(e=None):
        key_path = [None]; spd_path = [None]
        rec_pwd  = ft.TextField(password=True, can_reveal_password=True,
                                label="Contrasena del .key",
                                text_style=ft.TextStyle(font_family="Courier New"))
        rec_err  = ft.Text("", color=DARK["danger"], size=12)
        key_lbl  = ft.Text("Sin .key seleccionado", size=12, color=DARK["muted"])
        spd_lbl  = ft.Text("Sin .spd seleccionado", size=12, color=DARK["muted"])

        async def pick_key(e):
            files = await fp_key.pick_files(allowed_extensions=["key"])
            if files and files[0].path:
                key_path[0] = files[0].path
                key_lbl.value = os.path.basename(files[0].path); page.update()

        async def pick_spd(e):
            files = await fp_spd.pick_files(allowed_extensions=["spd"])
            if files and files[0].path:
                spd_path[0] = files[0].path
                spd_lbl.value = os.path.basename(files[0].path); page.update()

        async def do_import(e):
            rp = rec_pwd.value or ""; kp = key_path[0]; sp = spd_path[0]
            if not rp or not kp or not sp:
                rec_err.value = "Selecciona ambos archivos e ingresa la contrasena."; page.update(); return
            try:
                with open(kp, "rb") as f: key_bytes = f.read()
                with open(sp, "rb") as f: spd_bytes = f.read()
                plaintext, _ = decrypt_with_recovery_key(spd_bytes, key_bytes, rp)
                state.update({
                    "current_file": sp, "file_bytes": spd_bytes,
                    "key_id": get_key_id_from_file(spd_bytes),
                    "salt":   get_salt_from_file(spd_bytes),
                    "unlocked": True, "dirty": False,
                })
                editor.value = plaintext
                update_line_numbers(plaintext)
                close_dialog(page)
                secure_wipe_str(rp); rec_pwd.value = ""
                hide_lock_screen(); update_title()
                set_status("Archivo recuperado con .key", C("success"))
            except SecurityError as ex:
                rec_err.value = str(ex); page.update()
            except Exception as ex:
                rec_err.value = f"Error: {ex}"; page.update()

        open_dialog(page, ft.AlertDialog(
            modal=True, title=ft.Text("Recuperar con .key"),
            content=ft.Column([
                ft.Text("Selecciona el .spd y el .key.", size=12),
                ft.Row([ft.ElevatedButton("Elegir .spd", on_click=pick_spd), spd_lbl]),
                ft.Row([ft.ElevatedButton("Elegir .key", on_click=pick_key), key_lbl]),
                rec_pwd, rec_err,
            ], tight=True, width=420),
            actions=[
                ft.TextButton("Recuperar", on_click=do_import),
                ft.TextButton("Cancelar",  on_click=lambda e: close_dialog(page)),
            ],
        ))

    # ── Find & Replace ─────────────────────────────────────────────────────
    def toggle_find_bar(e=None):
        touch()
        if find_bar_ref.current:
            find_bar_ref.current.visible = not find_bar_ref.current.visible
            page.update()

    def do_find(e=None):
        touch()
        needle = find_field.value or ""; text = editor.value or ""
        if not needle:
            return
        if needle in text:
            # Calculate line number of first occurrence
            idx  = text.index(needle)
            line = text[:idx].count("\n") + 1
            find_result.value = f"Encontrado en Ln {line}"
            find_result.color = C("success")
        else:
            find_result.value = f"'{needle}' no encontrado"
            find_result.color = C("danger")
        page.update()

    def do_replace(e=None):
        touch()
        needle = find_field.value or ""; rep = replace_field.value or ""
        if needle and editor.value:
            count = editor.value.count(needle)
            if count:
                editor.value = editor.value.replace(needle, rep)
                update_line_numbers(editor.value)
                mark_dirty()
                find_result.value = f"{count} reemplazo(s) realizados"
                find_result.color = C("success")
            else:
                find_result.value = f"'{needle}' no encontrado"
                find_result.color = C("danger")
            page.update()

    # ── Settings ───────────────────────────────────────────────────────────
    async def open_settings(e=None):
        touch()
        font_dd     = ft.Dropdown(
            label="Tipo de letra", value=state["font_family"], width=240,
            options=[ft.dropdown.Option(f) for f in FONTS_MONO + FONTS_SANS],
        )
        size_slider = ft.Slider(
            min=10, max=28, value=float(state["font_size"]),
            divisions=18, label="{value}",
        )
        theme_sw = ft.Switch(label="Modo oscuro", value=state["dark_mode"])

        def apply_settings(e):
            state["font_family"] = font_dd.value or state["font_family"]
            state["font_size"]   = int(size_slider.value)
            state["dark_mode"]   = theme_sw.value
            editor.text_style = ft.TextStyle(
                font_family=state["font_family"],
                size=state["font_size"],
                color=C("text"),
            )
            line_numbers.font_family = state["font_family"]
            line_numbers.size        = state["font_size"]
            line_numbers.color       = C("lineno")
            page.bgcolor = C("bg")
            close_dialog(page)
            page.update()

        open_dialog(page, ft.AlertDialog(
            modal=True, title=ft.Text("Ajustes"),
            content=ft.Column([
                font_dd,
                ft.Text("Tamano de fuente", size=13),
                size_slider,
                theme_sw,
            ], tight=True, width=320),
            actions=[
                ft.TextButton("Aplicar",  on_click=apply_settings),
                ft.TextButton("Cancelar", on_click=lambda e: close_dialog(page)),
            ],
        ))

    # ── Keyboard shortcuts ─────────────────────────────────────────────────
    async def on_keyboard(e):
        touch()
        if e.ctrl:
            if e.key == "S":   await save_file()
            elif e.key == "O": await open_file()
            elif e.key == "N": await new_file()
            elif e.key == "F": toggle_find_bar()
            elif e.key == "L": await do_lock()

    page.on_keyboard_event = on_keyboard

    # ── Build UI ───────────────────────────────────────────────────────────
    def btn(icon_name, tooltip, action, color=None):
        return ft.IconButton(
            icon=_icon(icon_name), tooltip=tooltip, on_click=action,
            icon_color=color or C("text"), icon_size=19,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=6),
                padding=ft.padding.all(6),
            ),
        )

    toolbar = ft.Container(
        content=ft.Row([
            title_text, ft.Container(expand=True),
            btn("ADD_OUTLINED",         "Nuevo  Ctrl+N",      new_file),
            btn("FOLDER_OPEN_OUTLINED", "Abrir  Ctrl+O",      open_file),
            btn("SAVE_OUTLINED",        "Guardar  Ctrl+S",    save_file),
            ft.VerticalDivider(width=1, color=C("border")),
            btn("SEARCH_OUTLINED",      "Buscar  Ctrl+F",     toggle_find_bar),
            btn("SETTINGS_OUTLINED",    "Ajustes",            open_settings),
            ft.VerticalDivider(width=1, color=C("border")),
            btn("KEY_OUTLINED",         "Exportar .key",      open_export_key_dialog, C("accent")),
            btn("LOCK_RESET_OUTLINED",  "Recuperar con .key", open_import_key_dialog, C("accent")),
            btn("LOCK_OUTLINED",        "Bloquear  Ctrl+L",   do_lock,                C("danger")),
        ], spacing=2, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        bgcolor=C("panel"),
        padding=ft.padding.symmetric(horizontal=12, vertical=6),
        border=ft.border.only(bottom=ft.BorderSide(1, C("border"))),
    )

    find_bar = ft.Container(
        ref=find_bar_ref, visible=False,
        content=ft.Row([
            find_field, replace_field,
            ft.ElevatedButton("Buscar",     on_click=do_find,    height=36),
            ft.ElevatedButton("Reemplazar", on_click=do_replace, height=36),
            find_result,
            ft.Container(expand=True),
            ft.IconButton(_icon("CLOSE"), on_click=toggle_find_bar, icon_size=16),
        ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        bgcolor=C("panel"),
        padding=ft.padding.symmetric(horizontal=12, vertical=6),
        border=ft.border.only(bottom=ft.BorderSide(1, C("border"))),
    )

    # ── Editor con numeros de linea a la izquierda ─────────────────────────
    editor_with_lines = ft.Row(
        controls=[
            # Panel de numeros de linea
            ft.Container(
                content=ft.Column(
                    controls=[line_numbers],
                    scroll=ft.ScrollMode.HIDDEN,
                ),
                bgcolor=C("lineno_bg"),
                padding=ft.padding.only(top=16, bottom=16, left=8, right=8),
                border=ft.border.only(right=ft.BorderSide(1, C("border"))),
                width=52,
            ),
            # Editor principal
            ft.Container(
                content=editor,
                expand=True,
                bgcolor=C("surface"),
                padding=ft.padding.all(16),
            ),
        ],
        expand=True,
        spacing=0,
        vertical_alignment=ft.CrossAxisAlignment.STRETCH,
    )

    editor_column = ft.Column(
        ref=editor_area_ref, visible=False,
        controls=[find_bar, editor_with_lines],
        expand=True, spacing=0,
    )

    lock_container = ft.Container(
        ref=lock_screen_ref, visible=True, expand=True, bgcolor=C("bg"),
        content=ft.Column([
            ft.Container(height=60),
            ft.Icon(_icon("LOCK_OUTLINED"), size=56, color=C("accent")),
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
                            icon=_icon("LOCK_OPEN_OUTLINED"),
                            on_click=attempt_unlock,
                            style=ft.ButtonStyle(
                                bgcolor=C("accent"), color=_white(),
                                shape=ft.RoundedRectangleBorder(radius=8),
                                padding=ft.padding.symmetric(horizontal=24, vertical=12),
                            ),
                        ),
                    ], alignment=ft.MainAxisAlignment.CENTER),
                    ft.Container(height=24),
                    ft.Row([
                        ft.TextButton("Abrir otro archivo", on_click=open_file),
                        ft.TextButton("Recuperar con .key", on_click=open_import_key_dialog),
                    ], alignment=ft.MainAxisAlignment.CENTER),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, tight=True),
                width=380, bgcolor=C("surface"), border_radius=12,
                padding=ft.padding.all(28),
                border=ft.border.all(1, C("border")),
            ),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
    )

    status = ft.Container(
        content=ft.Row([
            status_bar,
            ft.Container(expand=True),
            cursor_info,
            ft.Container(width=16),
            ft.Text("AES-256-GCM  PBKDF2-200K", size=10, color=C("muted")),
        ]),
        bgcolor=C("panel"),
        padding=ft.padding.symmetric(horizontal=12, vertical=4),
        border=ft.border.only(top=ft.BorderSide(1, C("border"))),
    )

    page.bgcolor = C("bg")
    page.add(
        ft.Column([
            toolbar,
            ft.Stack([lock_container, editor_column], expand=True),
            status,
        ], spacing=0, expand=True)
    )

    set_status("Bienvenido a SecurePad. Abre un archivo o crea uno nuevo.")
    update_title()


def run():
    ft.run(main)