"""
SecurePad – app.py  (Flet 0.82 — Stack swap, sin page.views)
=============================================================
Navegación: UN SOLO page.add() con ft.Stack[panel_setup, panel_editor].
Mejoras v4:
  · _update_editor_style() sincroniza size+height en TextField, StrutStyle
    y lineno_col simultáneamente.
  · Números de línea alineados: mismo font_family/size/line_height que editor.
  · Find: búsqueda incremental con cursor (find_f.on_submit → siguiente ocurrencia).
  · Theme swap: actualiza bgcolor/border de toolbar, editor_container, status_bar.
  · panel_setup / panel_editor en módulos separados (panels.py).
"""

import flet as ft
import os, asyncio, threading, time

from .crypto_engine import (
    encrypt_content, decrypt_content, decrypt_with_seed,
    generate_seed_phrase, validate_seed_phrase, hash_seed_phrase,
    SecurityError, secure_wipe_str,
)

# ── Constantes y helpers (movidos desde constants.py) ───────────────
APP_NAME  = "SecurePad"
LOCK_SECS = 600
FONT_MONO = "Courier New"
LINE_H    = 1.25
FONT_SZ   = 14
LINENO_W  = 52

PREFS_SEED_HASH  = "securepad.seed_hash"
PREFS_SETUP_DONE = "securepad.setup_done"

DARK = {
    "bg":       "#0F0F0F",
    "surface":  "#181818",
    "panel":    "#1E1E1E",
    "border":   "#2A2A2A",
    "text":     "#E0E0E0",
    "muted":    "#555555",
    "accent":   "#4A9EFF",
    "danger":   "#FF4444",
    "success":  "#3DBA6F",
    "lineno":   "#3A3A3A",
    "lineno_bg":"#141414",
    "overlay":  "#000000",
    "cursor":   "#4A9EFF",
}

LIGHT = {
    "bg":       "#F2F2F2",
    "surface":  "#FFFFFF",
    "panel":    "#E8E8E8",
    "border":   "#D0D0D0",
    "text":     "#1A1A1A",
    "muted":    "#999999",
    "accent":   "#1565C0",
    "danger":   "#C62828",
    "success":  "#2E7D32",
    "lineno":   "#BBBBBB",
    "lineno_bg":"#EBEBEB",
    "overlay":  "#000000",
    "cursor":   "#1565C0",
}

def icon(name: str):
    try:    return getattr(ft.Icons, name)
    except: return getattr(ft.icons, name)

def white():
    try:    return ft.Colors.WHITE
    except: return ft.colors.WHITE

def text_style(color: str, size: int = FONT_SZ, bold: bool = False) -> ft.TextStyle:
    return ft.TextStyle(
        font_family=FONT_MONO, size=size, color=color,
        height=LINE_H,
        weight=ft.FontWeight.BOLD if bold else ft.FontWeight.NORMAL,
    )

def strut(size: int = FONT_SZ) -> ft.StrutStyle:
    return ft.StrutStyle(
        font_family=FONT_MONO, size=size,
        height=LINE_H, force_strut_height=True,
    )

def theme(state: dict) -> dict:
    return DARK if state.get("dark", True) else LIGHT

def C(state: dict, key: str) -> str:
    return theme(state)[key]

def open_dlg(page: ft.Page, dlg: ft.AlertDialog):
    page.show_dialog(dlg)

def close_dlg(page: ft.Page):
    page.pop_dialog()

from .panels import build_panel_setup, build_panel_editor


async def main(page: ft.Page):

    # ── Ventana ───────────────────────────────────────────────────────────
    page.title   = APP_NAME
    page.padding = 0
    page.spacing = 0
    page.bgcolor = DARK["bg"]
    try:
        page.window.width      = 900
        page.window.height     = 950
        page.window.min_width  = 560
        page.window.min_height = 400
    except AttributeError:
        page.window_width  = 900
        page.window_height = 950

    # ── Servicios ─────────────────────────────────────────────────────────
    prefs   = ft.SharedPreferences()
    fp_open = ft.FilePicker()
    fp_save = ft.FilePicker()

    # ── Estado global ─────────────────────────────────────────────────────
    S: dict = {
        "dark":         True,
        "font_sz":      FONT_SZ,
        "current_file": None,
        "file_bytes":   None,
        "unlocked":     False,
        "dirty":        False,
        "last_act":     time.time(),
        "cursor_ln":    1,
        "cursor_col":   1,
        "scroll_px":    0.0,
        "seed_phrase":  None,
        "obscured":     False,
        "setup_done":   False,
        "find_idx":     0,       # posición del cursor de búsqueda
    }

    def _C(k): return C(S, k)
    def touch(): S["last_act"] = time.time()

    # ── Refs ──────────────────────────────────────────────────────────────
    r_lock    = ft.Ref[ft.Container]()
    r_editor  = ft.Ref[ft.Column]()
    r_findbar = ft.Ref[ft.Container]()
    r_overlay = ft.Ref[ft.Container]()

    # ── Refs de contenedores temáticos (para theme swap) ──────────────────
    r_toolbar         = ft.Ref[ft.Container]()
    r_editor_container= ft.Ref[ft.Container]()
    r_lineno_container= ft.Ref[ft.Container]()
    r_status_bar      = ft.Ref[ft.Container]()
    r_findbar_inner   = ft.Ref[ft.Container]()

    # ─────────────────────────────────────────────────────────────────────
    # Controles del editor
    # ─────────────────────────────────────────────────────────────────────
    editor = ft.TextField(
        multiline=True, min_lines=1, expand=True,
        content_padding=0,
        border=ft.InputBorder.NONE,
        cursor_color=DARK["cursor"],
        selection_color=DARK["accent"],
        text_style=text_style(DARK["text"], FONT_SZ),
        strut_style=strut(FONT_SZ),
        bgcolor="transparent",
        on_change=lambda e: _sync_linenos(e.control.value),
    )

    lineno_col = ft.Text(
        "1", font_family=FONT_MONO, size=FONT_SZ,
        color=DARK["lineno"], height=LINE_H,
        text_align=ft.TextAlign.RIGHT, no_wrap=True
    )

    status_txt = ft.Text("", size=11, color=DARK["muted"])
    cursor_txt = ft.Text("Ln 1, Col 1", size=11, color=DARK["muted"])
    title_txt  = ft.Text(APP_NAME, size=14, weight=ft.FontWeight.W_500,
                         color=DARK["text"])

    pwd_field = ft.TextField(
        password=True, can_reveal_password=True, label="Contraseña Maestra",
        border_color=DARK["accent"], focused_border_color=DARK["accent"],
        text_style=text_style(DARK["text"], FONT_SZ), autofocus=True,
    )
    pwd_err   = ft.Text("", color=DARK["danger"], size=12)
    pwd_title = ft.Text("Desbloquear", size=16, weight=ft.FontWeight.W_600,
                        color=DARK["text"])
    pwd_hint  = ft.Text("", size=11, color=DARK["muted"])

    find_f    = ft.TextField(label="Buscar",     dense=True, width=190, label_style=ft.TextStyle(color=DARK["muted"]))
    replace_f = ft.TextField(label="Reemplazar", dense=True, width=190, label_style=ft.TextStyle(color=DARK["muted"]))
    find_msg  = ft.Text("", size=11, color=DARK["muted"])

    # ─────────────────────────────────────────────────────────────────────
    # 1. _update_editor_style — sincroniza fuente + altura en todos los sitios
    # ─────────────────────────────────────────────────────────────────────
    def _update_editor_style():
        fam = S.get("font_family", FONT_MONO)
        sz  = S["font_sz"]
        col = _C("text")
        # TextField: text_style + strut_style deben moverse juntos
        editor.text_style  = ft.TextStyle(
            font_family=fam, size=sz, color=col, height=LINE_H,
        )
        editor.strut_style = ft.StrutStyle(
            font_family=fam, size=sz,
            height=LINE_H, force_strut_height=True,
        )
        editor.cursor_color = _C("cursor")
        editor.selection_color = _C("accent")
        # Números de línea: mismo size y height
        lineno_col.font_family = fam
        lineno_col.size   = sz
        lineno_col.color  = _C("lineno")
        lineno_col.height = LINE_H

    # ─────────────────────────────────────────────────────────────────────
    # 3. _apply_theme — actualiza bgcolor/border de contenedores principales
    # ─────────────────────────────────────────────────────────────────────
    def _apply_theme():
        T = DARK if S["dark"] else LIGHT
        page.bgcolor = T["bg"]

        if r_toolbar.current:
            r_toolbar.current.bgcolor = T["panel"]
            r_toolbar.current.border  = ft.Border(
                bottom=ft.BorderSide(1, T["border"]))
            
            # Actualizar color de iconos en toolbar
            for c in r_toolbar.current.content.controls:
                if isinstance(c, ft.IconButton):
                    # Preservar color del candado
                    if c.tooltip and "Bloquear" in c.tooltip:
                        c.icon_color = T["danger"]
                    else:
                        c.icon_color = T["text"]

        if r_findbar_inner.current:
            r_findbar_inner.current.bgcolor = T["panel"]
            r_findbar_inner.current.border  = ft.Border(
                bottom=ft.BorderSide(1, T["border"]))
            # Actualizar color de iconos en findbar
            row_controls = r_findbar_inner.current.content.controls
            for c in row_controls:
                if isinstance(c, ft.Row):
                    for sub_c in c.controls:
                        if isinstance(sub_c, ft.IconButton):
                            sub_c.icon_color = T["text"]
                elif isinstance(c, ft.IconButton):
                    c.icon_color = T["text"]

        if r_editor_container.current:
            r_editor_container.current.bgcolor = T["surface"]

        if r_lineno_container.current:
            r_lineno_container.current.bgcolor = T["lineno_bg"]
            r_lineno_container.current.border  = ft.Border(
                right=ft.BorderSide(1, T["border"]))

        if r_status_bar.current:
            r_status_bar.current.bgcolor = T["panel"]
            r_status_bar.current.border  = ft.Border(
                top=ft.BorderSide(1, T["border"]))

        find_f.bgcolor = T["surface"]
        replace_f.bgcolor = T["surface"]
        find_f.color = T["text"]
        replace_f.color = T["text"]
        find_f.label_style = ft.TextStyle(color=T["muted"])
        replace_f.label_style = ft.TextStyle(color=T["muted"])
        title_txt.color  = T["text"]
        status_txt.color = T["muted"]
        cursor_txt.color = T["muted"]
        pwd_title.color  = T["text"]
        pwd_hint.color   = T["muted"]
        find_msg.color   = T["muted"]
        _update_editor_style()
        page.update()

    # ─────────────────────────────────────────────────────────────────────
    # Helpers de UI
    # ─────────────────────────────────────────────────────────────────────
    def _set_status(msg, color=""):
        status_txt.value = msg
        status_txt.color = color or _C("muted")
        page.update()

    def _update_title():
        fname = os.path.basename(S["current_file"]) if S["current_file"] else "Sin título"
        mod   = " *" if S["dirty"] else ""
        lck   = " [BLOQUEADO]" if not S["unlocked"] else ""
        title_txt.value = f"{APP_NAME}  ·  {fname}{mod}{lck}"
        page.update()

    def _mark_dirty():
        if not S["dirty"]:
            S["dirty"] = True
            _update_title()

    def _sync_linenos(text: str):
        n  = max(1, text.count("\n") + 1) if text else 1
        # Generar un solo string con saltos de línea escalares
        lineno_col.value = "\n".join(str(i + 1) for i in range(n))
        editor.min_lines = n
        page.update()

    def _update_cursor(text, offset):
        before = text[:offset]
        ln  = before.count("\n") + 1
        col = len(before.split("\n")[-1]) + 1
        cursor_txt.value = f"Ln {ln}, Col {col}"
        page.update()

    def _show_lock():
        if r_lock.current:   r_lock.current.visible   = True
        if r_editor.current: r_editor.current.visible = False
        page.update()

    def _hide_lock():
        if r_lock.current:   r_lock.current.visible   = False
        if r_editor.current: r_editor.current.visible = True
        page.update()

    def _show_overlay(show: bool):
        if r_overlay.current:
            r_overlay.current.visible = show
            S["obscured"] = show
            page.update()

    editor.on_change = lambda e: (
        touch(), _mark_dirty(), _sync_linenos(e.control.value or "")
    )
    editor.on_selection_change = lambda e: (
        touch(),
        _update_cursor(editor.value or "",
                       e.selection.base_offset if e.selection else 0),
    )

    # ─────────────────────────────────────────────────────────────────────
    # Auto-lock + Lifecycle
    # ─────────────────────────────────────────────────────────────────────
    def _lock_watcher():
        while True:
            time.sleep(5)
            if S["unlocked"] and time.time() - S["last_act"] >= LOCK_SECS:
                page.run_task(_do_lock)

    threading.Thread(target=_lock_watcher, daemon=True).start()

    def _on_lifecycle(e):
        paused = (ft.AppLifecycleState.PAUSE, ft.AppLifecycleState.HIDE,
                  ft.AppLifecycleState.INACTIVE)
        _show_overlay(e.state in paused)

    page.on_app_lifecycle_state_change = _on_lifecycle

    # ─────────────────────────────────────────────────────────────────────
    # Lock / Unlock
    # ─────────────────────────────────────────────────────────────────────
    async def _do_lock(e=None):
        S["unlocked"] = False
        editor.value  = ""
        _sync_linenos("")
        secure_wipe_str(pwd_field.value or "")
        pwd_field.value = ""; pwd_err.value = ""
        _show_lock(); _update_title()
        _set_status("Sesión bloqueada.")

    async def _attempt_unlock(e=None):
        touch()
        pwd = pwd_field.value or ""
        if not pwd:
            pwd_err.value = "Ingresa tu contraseña."; page.update(); return

        if S["file_bytes"] is None:
            S["unlocked"] = True; pwd_err.value = ""
            _hide_lock(); _update_title(); _sync_linenos("")
            _set_status("Nueva nota lista. Ctrl+S para guardar.")
            return

        try:
            _set_status("Derivando clave…"); page.update()
            loop = asyncio.get_event_loop()
            pt   = await loop.run_in_executor(
                None, decrypt_content, S["file_bytes"], pwd)
            S["unlocked"] = True
            editor.value  = pt
            _update_editor_style()
            _sync_linenos(pt)
            pwd_err.value = ""; secure_wipe_str(pwd); pwd_field.value = ""
            _hide_lock(); _update_title()
            _set_status(f"Abierto: {os.path.basename(S['current_file'])}", _C("success"))
        except SecurityError as ex:
            pwd_err.value = str(ex)
            secure_wipe_str(pwd); pwd_field.value = ""
            _set_status("Tag de seguridad inválido.", _C("danger"))
        except Exception as ex:
            pwd_err.value = f"Error: {ex}"
        page.update()

    pwd_field.on_submit = _attempt_unlock

    # ─────────────────────────────────────────────────────────────────────
    # Recuperación, Inserción y Reset de semilla
    # ─────────────────────────────────────────────────────────────────────
    async def _open_reinsert_seed(e=None):
        done = asyncio.Event(); result = {"seed": None}
        sf = ft.TextField(
            label="Escribe la frase secreta de otro usuario", multiline=True,
            min_lines=2, max_lines=3,
            text_style=text_style(DARK["text"], 13),
            border_color=DARK["accent"],
        )
        err_t = ft.Text("", color=DARK["danger"], size=12)

        async def _ok(e):
            phrase = (sf.value or "").strip()
            if not validate_seed_phrase(phrase):
                err_t.value = "Semilla inválida."; page.update(); return
            # Sobreescribe explícitamente y bloquea en la memoria actual
            await prefs.set(PREFS_SEED_HASH, str(hash_seed_phrase(phrase)))
            result["seed"] = phrase; S["seed_phrase"] = phrase
            close_dlg(page); done.set()
            _set_status("Semilla de usuario inyectada.", _C("success"))

        open_dlg(page, ft.AlertDialog(
            modal=True, title=ft.Text("Inyectar semilla externa"),
            content=ft.Column([
                ft.Text("Permite decodificar archivos asociados a otra cuenta/llave.",
                        size=12, color=DARK["muted"]),
                sf, err_t,
            ], tight=True, width=440),
            actions=[
                ft.FilledButton("Inyectar", on_click=_ok, bgcolor=DARK["accent"], color=white()),
                ft.FilledButton("Cancelar", on_click=lambda e: (close_dlg(page), done.set()), bgcolor=DARK["panel"], color=DARK["text"]),
            ],
        ))
        await done.wait()

    async def _open_reset_seed(e=None):
        done = asyncio.Event()

        async def _confirm_final(e):
            await prefs.clear()
            S["seed_phrase"] = None
            S["setup_done"] = False
            close_dlg(page); done.set()
            # Reiniciar app programáticamente
            page.controls.clear()
            await main(page)

        async def _confirm_first(e):
            close_dlg(page)
            # Segunda confirmación
            open_dlg(page, ft.AlertDialog(
                modal=True, title=ft.Text("¡Advertencia Final!", color=DARK["danger"]),
                content=ft.Text("Vas a borrar de esta PC la huella de tu semilla.\n\n"
                                "Los archivos cifrados previamente seguirán existiendo pero no "
                                "podrás abrirlos mediante contraseñas guardadas sin insertar "
                                "manualmente la semilla correcta de estos.",
                                size=13, color=DARK["muted"]),
                actions=[
                    ft.FilledButton("Borrar Todo", on_click=_confirm_final, bgcolor=DARK["danger"], color=white()),
                    ft.FilledButton("Cancelar", on_click=lambda e: (close_dlg(page), done.set()), bgcolor=DARK["panel"], color=DARK["text"]),
                ],
            ))

        open_dlg(page, ft.AlertDialog(
            modal=True, title=ft.Text("Remover Semilla Local", color=DARK["danger"]),
            content=ft.Text("¿Estás seguro que deseas remover tu semilla almacenada y "
                            "resetear la aplicación a estado de fábrica?", size=13),
            actions=[
                ft.FilledButton("Sí, Remover", on_click=_confirm_first, bgcolor=DARK["danger"], color=white()),
                ft.FilledButton("Cancelar", on_click=lambda e: (close_dlg(page), done.set()), bgcolor=DARK["panel"], color=DARK["text"]),
            ],
        ))
        await done.wait()

    async def _open_seed_recovery(e=None):
        if S["file_bytes"] is None:
            _set_status("Abre un archivo primero.", _C("danger")); return

        seed_f = ft.TextField(
            label="Ingresa las 12 palabras separadas por espacios",
            multiline=True, min_lines=2, max_lines=3,
            text_style=text_style(DARK["text"], 13),
            border_color=DARK["accent"],
        )
        err_t = ft.Text("", color=DARK["danger"], size=12)

        async def _recover(e):
            phrase = (seed_f.value or "").strip()
            if not validate_seed_phrase(phrase):
                err_t.value = "Semilla inválida."; page.update(); return
            try:
                loop = asyncio.get_event_loop()
                pt = await loop.run_in_executor(
                    None, decrypt_with_seed, S["file_bytes"], phrase)
                S["unlocked"] = True
                editor.value  = pt
                _update_editor_style()
                _sync_linenos(pt); S["dirty"] = False
                close_dlg(page); secure_wipe_str(phrase); seed_f.value = ""
                _hide_lock(); _update_title()
                _set_status("Archivo recuperado con semilla.", _C("success"))
            except SecurityError as ex:
                err_t.value = str(ex); page.update()
            except Exception as ex:
                err_t.value = f"Error: {ex}"; page.update()

        open_dlg(page, ft.AlertDialog(
            modal=True, title=ft.Text("Recuperar con semilla mnemónica"),
            content=ft.Column([
                ft.Text("Ingresa las 12 palabras de tu semilla.",
                        size=12, color=DARK["muted"]),
                seed_f, err_t,
            ], tight=True, width=440),
            actions=[
                ft.TextButton("Recuperar", on_click=_recover),
                ft.TextButton("Cancelar",  on_click=lambda e: close_dlg(page)),
            ],
        ))

    # ─────────────────────────────────────────────────────────────────────
    # Nuevo / Abrir / Guardar
    # ─────────────────────────────────────────────────────────────────────
    async def _new_file(e=None):
        touch()
        S.update({"current_file": None, "file_bytes": None,
                  "unlocked": False, "dirty": False})
        editor.value = ""; pwd_field.value = ""; pwd_err.value = ""
        if r_findbar.current: r_findbar.current.visible = False
        find_f.value = ""; find_msg.value = ""; S["find_idx"] = 0
        pwd_title.value = "Nueva nota"
        pwd_hint.value  = "Elige una contraseña para cifrar este archivo."
        _show_lock(); _update_title()
        _set_status("Nueva nota. Ctrl+S para guardar.")

    async def _open_file(e=None):
        touch()
        files = await fp_open.pick_files(
            dialog_title="Abrir archivo SecurePad",
            allowed_extensions=["spd"],
        )
        if not files: return
        path = files[0].path
        if not path:
            _set_status("No se pudo obtener la ruta.", _C("danger")); return
        try:
            with open(path, "rb") as f: raw = f.read()
            S.update({"current_file": path, "file_bytes": raw,
                      "unlocked": False, "dirty": False})
            editor.value = ""; pwd_field.value = ""; pwd_err.value = ""
            if r_findbar.current: r_findbar.current.visible = False
            find_f.value = ""; find_msg.value = ""; S["find_idx"] = 0
            pwd_title.value = f"Abrir: {os.path.basename(path)}"
            pwd_hint.value  = "Ingresa la contraseña maestra."
            _show_lock(); _update_title()
            _set_status(f"Cargado: {os.path.basename(path)}")
        except Exception as ex:
            _set_status(f"Error al leer: {ex}", _C("danger"))

    async def _save(e=None):
        touch()
        if S["current_file"] and S["unlocked"]:
            await _save_with_dialog(S["current_file"])
        else:
            await _save_as()

    async def _save_as(e=None):
        touch()
        path = await fp_save.save_file(
            file_name="nota.spd", dialog_title="Guardar archivo SecurePad",
            allowed_extensions=["spd"],
        )
        if not path: return
        if not path.endswith(".spd"): path += ".spd"
        await _save_with_dialog(path)

    async def _save_with_dialog(path: str):
        done = asyncio.Event(); result = {"pwd": None}
        spf  = ft.TextField(
            password=True, can_reveal_password=True,
            label="Contraseña para cifrar", autofocus=True,
            border_color=DARK["accent"],
            text_style=text_style(DARK["text"], 13),
        )
        serr = ft.Text("", color=DARK["danger"], size=12)

        async def _confirm(e):
            p = spf.value or ""
            if not p:
                serr.value = "La contraseña no puede estar vacía."; page.update(); return
            result["pwd"] = p; close_dlg(page); done.set()

        spf.on_submit = _confirm
        open_dlg(page, ft.AlertDialog(
            modal=True, title=ft.Text("Guardar archivo"),
            content=ft.Column([ft.Text("Contraseña para cifrar:"), spf, serr], tight=True),
            actions=[
                ft.FilledButton("Guardar",  on_click=_confirm, bgcolor=DARK["accent"], color=white()),
                ft.FilledButton("Cancelar", on_click=lambda e: (close_dlg(page), done.set()), bgcolor=DARK["panel"], color=DARK["text"]),
            ],
        ))
        await done.wait()
        if result["pwd"]:
            await _execute_save(path, result["pwd"])
            secure_wipe_str(result["pwd"]); result["pwd"] = None

    async def _execute_save(path: str, password: str):
        seed = S.get("seed_phrase")
        if not seed and not S.get("setup_done", False):
            seed = await _ask_seed_for_save()
            if not seed: return
        if seed is None:
            seed = ""
        try:
            _set_status("Cifrando…"); page.update()
            loop = asyncio.get_event_loop()
            fb, _ = await loop.run_in_executor(
                None, encrypt_content, editor.value or "", password, seed)
            with open(path, "wb") as f: f.write(fb)
            S.update({"current_file": path, "file_bytes": fb,
                      "unlocked": True, "dirty": False})
            secure_wipe_str(password)
            _hide_lock(); _update_title()
            _set_status(f"Guardado: {os.path.basename(path)}", _C("success"))
        except Exception as ex:
            _set_status(f"Error al guardar: {ex}", _C("danger"))

    async def _ask_seed_for_save():
        done = asyncio.Event(); result = {"seed": None}
        sf = ft.TextField(
            label="Tus 12 palabras de semilla", multiline=True,
            min_lines=2, max_lines=3,
            text_style=text_style(DARK["text"], 13),
            border_color=DARK["accent"],
        )
        err_t = ft.Text("", color=DARK["danger"], size=12)

        async def _ok(e):
            phrase = (sf.value or "").strip()
            if not validate_seed_phrase(phrase):
                err_t.value = "Semilla inválida."; page.update(); return
            stored = await prefs.get(PREFS_SEED_HASH)
            if stored and hash_seed_phrase(phrase) != stored:
                err_t.value = "Esta semilla no coincide con la registrada."
                page.update(); return
            result["seed"] = phrase; S["seed_phrase"] = phrase
            close_dlg(page); done.set()

        open_dlg(page, ft.AlertDialog(
            modal=True, title=ft.Text("Confirmar semilla"),
            content=ft.Column([
                ft.Text("Necesitamos tu semilla para vincular la recuperación.",
                        size=12, color=DARK["muted"]),
                sf, err_t,
            ], tight=True, width=440),
            actions=[
                ft.TextButton("Continuar", on_click=_ok),
                ft.TextButton("Cancelar",
                              on_click=lambda e: (close_dlg(page), done.set())),
            ],
        ))
        await done.wait()
        return result["seed"]

    # ─────────────────────────────────────────────────────────────────────
    # 2. Find & Replace — búsqueda incremental con cursor
    # ─────────────────────────────────────────────────────────────────────
    def _do_find(e=None):
        """Avanza a la siguiente ocurrencia de la búsqueda."""
        needle = find_f.value or ""
        text   = editor.value or ""
        if not needle:
            find_msg.value = ""; page.update(); return

        # Buscar todas las ocurrencias
        positions = []
        start = 0
        while True:
            idx = text.lower().find(needle.lower(), start)
            if idx == -1: break
            positions.append(idx)
            start = idx + 1

        if not positions:
            find_msg.value = f"'{needle}' no encontrado"
            find_msg.color = _C("danger")
            S["find_idx"] = 0
            # Quitar selección
            editor.selection = ft.TextSelection(0, 0)
            page.update(); return

        # Avanzar cursor circular
        S["find_idx"] = S["find_idx"] % len(positions)
        pos = positions[S["find_idx"]]
        ln  = text[:pos].count("\n") + 1
        find_msg.value = f"Ocurrencia {S['find_idx']+1}/{len(positions)} — Ln {ln}"
        find_msg.color = _C("success")
        
        # Seleccionar texto y auto-scroll
        editor.selection = ft.TextSelection(pos, pos + len(needle))
        
        S["find_idx"] = (S["find_idx"] + 1) % len(positions)
        editor.update()
        page.update()

    def _do_replace(e=None):
        needle = find_f.value or ""; rep = replace_f.value or ""
        text   = editor.value or ""
        if not needle or not text: return
        
        # Validamos si actualmente tenemos una selección que coincide y procedemos al reemplazo uno a uno
        if editor.selection and editor.selection.end - editor.selection.start == len(needle):
            sel_text = text[editor.selection.start:editor.selection.end]
            if sel_text.lower() == needle.lower():
                editor.value = text[:editor.selection.start] + rep + text[editor.selection.end:]
                _sync_linenos(editor.value)
                _mark_dirty()
                
                # Ajustamos el puntero para que la siguiente búsqueda comience después del reemplazo
                # Para ello, retrocedemos manualmente el find_idx global ya que _do_find lo adelanta.
                if S.get("find_idx", 1) > 0:
                    S["find_idx"] -= 1

                _do_find()  # Salta a la siguiente coincidencia
                return

        find_msg.value = "Presiona 'Buscar' o Enter primero para fijar una selección"
        find_msg.color = _C("danger")
        page.update()

    def _do_replace_all(e=None):
        needle = find_f.value or ""; rep = replace_f.value or ""
        text   = editor.value or ""
        if not needle or not text: return
        
        # Cuenta cuantas ocurrencias existen por reemplazo total ignorando el case base original de Flet
        import re
        n = len(re.findall(re.escape(needle), text, flags=re.IGNORECASE))
        
        if n:
            editor.value = re.sub(re.escape(needle), rep, text, flags=re.IGNORECASE)
            _sync_linenos(editor.value); _mark_dirty()
            find_msg.value = f"{n} reemplazo(s) realizados"
            find_msg.color = _C("success")
            S["find_idx"] = 0
        else:
            find_msg.value = "No encontrado"; find_msg.color = _C("danger")
        page.update()

    async def _toggle_find(e=None):
        if r_findbar.current:
            r_findbar.current.visible = not r_findbar.current.visible
            if r_findbar.current.visible:
                S["find_idx"] = 0
                find_msg.value = ""
                page.update()
                # Focus workaround delay Flet 0.82
                await asyncio.sleep(0.1)
                await find_f.focus()
            else:
                page.update()

    # Enter en el campo de búsqueda → siguiente ocurrencia
    find_f.on_submit = _do_find

    # ─────────────────────────────────────────────────────────────────────
    # Settings
    # ─────────────────────────────────────────────────────────────────────
    async def _open_settings(e=None):
        font_sz_sl = ft.Slider(min=10, max=28, value=float(S["font_sz"]),
                               divisions=18, label="{value}")
        dark_sw = ft.Switch(label="Modo oscuro", value=S["dark"])
        
        fonts = ["Consolas", "Courier New", "Lucida Console", "Monospace", "Arial", "Roboto"]
        current_font = S.get("font_family", FONT_MONO)
        if current_font not in fonts: fonts.insert(0, current_font)
        font_dd = ft.Dropdown(
            label="Fuente",
            value=current_font,
            options=[ft.dropdown.Option(f) for f in fonts],
            width=280
        )

        def _apply(e):
            S["font_family"] = font_dd.value
            S["font_sz"] = int(font_sz_sl.value)
            S["dark"]    = dark_sw.value
            _apply_theme()          # actualiza bgcolor/borders
            _sync_linenos(editor.value or "")  # reconstruye con nuevo size
            close_dlg(page)
            page.update()

        open_dlg(page, ft.AlertDialog(
            modal=True, title=ft.Text("Ajustes"),
            content=ft.Column([
                font_dd,
                ft.Text("Tamaño de fuente", size=13, color=DARK["muted"]),
                font_sz_sl, dark_sw,
            ], tight=True, width=300),
            actions=[
                ft.FilledButton("Aplicar",  on_click=_apply, bgcolor=DARK["accent"], color=white()),
                ft.FilledButton("Cancelar", on_click=lambda e: close_dlg(page), bgcolor=DARK["panel"], color=DARK["text"]),
            ],
        ))

    # ─────────────────────────────────────────────────────────────────────
    # Keyboard shortcuts
    # ─────────────────────────────────────────────────────────────────────
    async def _on_kbd(e):
        touch()
        if e.ctrl:
            if   e.key == "S": await _save()
            elif e.key == "O": await _open_file()
            elif e.key == "N": await _new_file()
            elif e.key == "F": await _toggle_find()
            elif e.key == "L": await _do_lock()

    page.on_keyboard_event = _on_kbd

    # ─────────────────────────────────────────────────────────────────────
    # Botones de toolbar
    # ─────────────────────────────────────────────────────────────────────
    def _btn(ico, tip, fn, color=None):
        return ft.IconButton(
            icon=icon(ico), tooltip=tip, on_click=fn,
            icon_color=color or DARK["text"], icon_size=18,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=5),
                padding=ft.padding.all(5),
            ),
        )

    # ─────────────────────────────────────────────────────────────────────
    # Scroll del editor → sincroniza lineno_col
    # ─────────────────────────────────────────────────────────────────────
    def _on_editor_scroll(e):
        pass

    # ─────────────────────────────────────────────────────────────────────
    # Navegación: swap de paneles
    # ─────────────────────────────────────────────────────────────────────
    def _show_editor():
        panel_setup.visible  = False
        panel_editor.visible = True
        page.update()

    def _show_setup():
        panel_editor.visible = False
        panel_setup.visible  = True
        page.update()

    # ─────────────────────────────────────────────────────────────────────
    # Setup: verificación de semilla
    # ─────────────────────────────────────────────────────────────────────
    async def _on_setup_verified(phrase: str):
        await prefs.set(PREFS_SEED_HASH,  str(hash_seed_phrase(phrase)))
        await prefs.set(PREFS_SETUP_DONE, "true")
        S["seed_phrase"] = phrase
        S["setup_done"]  = True
        _set_status("Configuración completada. Bienvenido a SecurePad.", DARK["success"])
        _update_title()
        _show_editor()

    # ─────────────────────────────────────────────────────────────────────
    # Construcción de paneles (delegada a panels.py)
    # ─────────────────────────────────────────────────────────────────────
    panel_setup, setup_words_col, setup_confirm_inputs = build_panel_setup(
        page=page,
        on_verified=_on_setup_verified,
        S=S,
    )

    panel_editor = build_panel_editor(
        page=page,
        S=S,
        # controles
        editor=editor,
        lineno_col=lineno_col,
        title_txt=title_txt,
        status_txt=status_txt,
        cursor_txt=cursor_txt,
        pwd_field=pwd_field,
        pwd_err=pwd_err,
        pwd_title=pwd_title,
        pwd_hint=pwd_hint,
        find_f=find_f,
        replace_f=replace_f,
        find_msg=find_msg,
        # callbacks
        on_new=_new_file,
        on_open=_open_file,
        on_save=_save,
        on_toggle_find=_toggle_find,
        on_find=_do_find,
        on_replace=_do_replace,
        on_replace_all=_do_replace_all,
        on_settings=_open_settings,
        on_lock=_do_lock,
        on_unlock=_attempt_unlock,
        on_seed_recovery=_open_seed_recovery,
        on_reinsert_seed=_open_reinsert_seed,
        on_reset_seed=_open_reset_seed,
        on_editor_scroll=_on_editor_scroll,
        # refs
        r_lock=r_lock,
        r_editor=r_editor,
        r_findbar=r_findbar,
        r_toolbar=r_toolbar,
        r_editor_container=r_editor_container,
        r_lineno_container=r_lineno_container,
        r_status_bar=r_status_bar,
        r_findbar_inner=r_findbar_inner,
    )

    # ─────────────────────────────────────────────────────────────────────
    # Montar árbol (una sola vez)
    # ─────────────────────────────────────────────────────────────────────
    sec_overlay = ft.Container(
        ref=r_overlay, visible=False, opacity=1.0, margin=0,
        top=0, left=0, right=0, bottom=0,
        bgcolor="#000000",
        content=ft.Column(
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Icon(icon("LOCK_OUTLINED"), size=64, color="#333333"),
                ft.Text("SecurePad", color="#333333", size=18,
                        weight=ft.FontWeight.W_600),
            ],
        ),
    )

    page.add(ft.Stack(
        controls=[panel_setup, panel_editor, sec_overlay],
        expand=True,
    ))

    # ─────────────────────────────────────────────────────────────────────
    # Inicio: leer prefs → mostrar panel correcto
    # ─────────────────────────────────────────────────────────────────────
    try:
        if await prefs.contains_key(PREFS_SETUP_DONE):
            S["setup_done"] = (await prefs.get(PREFS_SETUP_DONE)) == "true"
    except Exception as ex:
        print(f"[SecurePad] Error leyendo prefs: {ex}")

    print(f"[SecurePad] Inicio — setup_done={S['setup_done']}")

    if S["setup_done"]:
        _set_status("Bienvenido a SecurePad. Ctrl+O para abrir, Ctrl+N para nuevo.")
        _update_title()
        panel_setup.visible  = False
        panel_editor.visible = True
        page.update()
    else:
        # Generar semilla y rellenar grilla de palabras del setup
        phrase = generate_seed_phrase()
        S["seed_phrase"] = phrase
        words  = phrase.split()
        setup_words_col.controls = [
            ft.Row(
                wrap=True, spacing=8, run_spacing=8,
                controls=[
                    ft.Container(
                        content=ft.Row([
                            ft.Text(f"{i+1}.", size=11, color=DARK["muted"], width=22),
                            ft.Text(w, size=14, weight=ft.FontWeight.W_600,
                                    color=DARK["text"], font_family=FONT_MONO,
                                    selectable=True),
                        ], spacing=4),
                        bgcolor=DARK["panel"], border_radius=6,
                        padding=ft.padding.symmetric(horizontal=10, vertical=6),
                        border=ft.border.all(1, DARK["border"]),
                    )
                    for i, w in enumerate(words)
                ],
            )
        ]
        panel_setup.visible  = True
        panel_editor.visible = False
        page.update()


def run():
    ft.run(main)
