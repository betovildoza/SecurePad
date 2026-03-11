"""
SecurePad – panels.py
=====================
Construye los dos paneles de la aplicación:
  · build_panel_setup()   → ft.Column (onboarding de semilla)
  · build_panel_editor()  → ft.Column (editor principal)

Ambos reciben controles y callbacks ya instanciados desde app.py.
No tocan prefs ni estado global directamente.
"""

import flet as ft
from .app import (
    APP_NAME, FONT_MONO, LINE_H, FONT_SZ, LINENO_W,
    DARK, icon, white, text_style,
)


# ─────────────────────────────────────────────────────────────────────────────
# PANEL SETUP
# ─────────────────────────────────────────────────────────────────────────────

def build_panel_setup(*, page: ft.Page, on_verified, S: dict):
    """
    Devuelve (panel_column, words_col_ref, confirm_inputs_list).
    words_col_ref y confirm_inputs_list se rellenan desde app.py
    una vez que se genera la frase.
    """
    step1_ref = ft.Ref[ft.Column]()
    step2_ref = ft.Ref[ft.Column]()

    confirm_inputs = [
        ft.TextField(
            label=f"Palabra {i + 1}", dense=True, width=160,
            text_style=text_style(DARK["text"], 13),
            border_color=DARK["border"],
        )
        for i in range(12)
    ]
    confirm_err = ft.Text("", color=DARK["danger"], size=12)
    words_col   = ft.Column()   # se rellena en app.py tras generate_seed_phrase()

    def _to_step2(e):
        if step1_ref.current: step1_ref.current.visible = False
        if step2_ref.current: step2_ref.current.visible = True
        page.update()

    async def _verify(e):
        phrase  = S.get("seed_phrase", "")
        entered = " ".join(f.value.strip().lower() for f in confirm_inputs)
        if entered != phrase.strip().lower():
            confirm_err.value = "Las palabras no coinciden. Revisa el orden y la ortografía."
            page.update()
            return
        await on_verified(phrase)

    step1 = ft.Column(
        ref=step1_ref, visible=True,
        horizontal_alignment=ft.CrossAxisAlignment.START,
        controls=[
            ft.Text("Tu semilla de recuperación", size=20,
                    weight=ft.FontWeight.BOLD, color=DARK["text"]),
            ft.Container(height=8),
            ft.Text(
                "Estas 12 palabras son la única forma de recuperar tus archivos "
                "si olvidas tu contraseña. Escríbelas en papel y guárdalas en "
                "un lugar seguro. NO las guardes digitalmente.",
                size=13, color=DARK["muted"],
            ),
            ft.Container(height=16),
            words_col,
            ft.Container(height=24),
            ft.FilledButton(
                "Ya las guardé, continuar →", on_click=_to_step2,
                style=ft.ButtonStyle(
                    bgcolor=DARK["accent"], color=white(),
                    shape=ft.RoundedRectangleBorder(radius=8),
                    padding=ft.Padding(left=24, right=24, top=12, bottom=12),
                ),
            ),
        ],
    )

    step2 = ft.Column(
        ref=step2_ref, visible=False,
        horizontal_alignment=ft.CrossAxisAlignment.START,
        controls=[
            ft.Text("Confirma tu semilla", size=20,
                    weight=ft.FontWeight.BOLD, color=DARK["text"]),
            ft.Container(height=8),
            ft.Text("Ingresa las 12 palabras en orden para verificar que las anotaste.",
                    size=13, color=DARK["muted"]),
            ft.Container(height=16),
            ft.Row(wrap=True, spacing=8, run_spacing=8, controls=confirm_inputs),
            ft.Container(height=8),
            confirm_err,
            ft.Container(height=16),
            ft.FilledButton(
                "Verificar y comenzar", on_click=_verify,
                style=ft.ButtonStyle(
                    bgcolor=DARK["success"], color=white(),
                    shape=ft.RoundedRectangleBorder(radius=8),
                    padding=ft.Padding(left=24, right=24, top=12, bottom=12),
                ),
            ),
        ],
    )

    panel = ft.Column(
        visible=True, expand=True,
        controls=[
            ft.Container(
                expand=True,
                padding=ft.Padding(left=40, right=40, top=30, bottom=30),
                bgcolor=DARK["bg"],
                content=ft.Column(
                    scroll=ft.ScrollMode.AUTO,
                    controls=[
                        ft.Row([
                            ft.Icon(icon("LOCK_OUTLINED"), color=DARK["accent"], size=28),
                            ft.Text(APP_NAME, size=22, weight=ft.FontWeight.BOLD,
                                    color=DARK["text"]),
                        ], spacing=10),
                        ft.Divider(color=DARK["border"]),
                        ft.Container(height=8),
                        ft.Column(controls=[step1, step2], spacing=0),
                    ],
                ),
            ),
        ],
    )

    return panel, words_col, confirm_inputs


# ─────────────────────────────────────────────────────────────────────────────
# PANEL EDITOR
# ─────────────────────────────────────────────────────────────────────────────

def build_panel_editor(
    *,
    page: ft.Page,
    S: dict,
    # controles del editor
    editor: ft.TextField,
    lineno_col: ft.Column,
    title_txt: ft.Text,
    status_txt: ft.Text,
    cursor_txt: ft.Text,
    pwd_field: ft.TextField,
    pwd_err: ft.Text,
    pwd_title: ft.Text,
    pwd_hint: ft.Text,
    find_f: ft.TextField,
    replace_f: ft.TextField,
    find_msg: ft.Text,
    # callbacks
    on_new, on_open, on_save,
    on_toggle_find, on_find, on_replace, on_replace_all,
    on_settings, on_lock, on_unlock,
    on_seed_recovery, on_reinsert_seed, on_reset_seed, on_editor_scroll,
    # refs
    r_lock, r_editor, r_findbar,
    r_toolbar, r_editor_container, r_lineno_container,
    r_status_bar, r_findbar_inner,
) -> ft.Column:
    """
    Ensambla el panel principal del editor con:
      · Toolbar con refs para theme swap
      · Find bar incremental
      · Editor + números de línea alineados
      · Lock screen
      · Status bar
    """

    def _icon_btn(ico, tip, fn, color=None):
        return ft.IconButton(
            icon=icon(ico), tooltip=tip, on_click=fn,
            icon_color=color or DARK["text"], icon_size=18,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=5),
                padding=ft.Padding(left=5, right=5, top=5, bottom=5),
            ),
        )

    # ── Toolbar ───────────────────────────────────────────────────────────
    toolbar = ft.Container(
        ref=r_toolbar,
        content=ft.Row([
            title_txt, ft.Container(expand=True),
            _icon_btn("ADD_OUTLINED",         "Nuevo  Ctrl+N",    on_new),
            _icon_btn("FOLDER_OPEN_OUTLINED", "Abrir  Ctrl+O",    on_open),
            _icon_btn("SAVE_OUTLINED",        "Guardar  Ctrl+S",  on_save),
            ft.VerticalDivider(width=1, color=DARK["border"]),
            _icon_btn("SEARCH_OUTLINED",      "Buscar  Ctrl+F",   on_toggle_find),
            _icon_btn("SETTINGS_OUTLINED",    "Ajustes",          on_settings),
            ft.VerticalDivider(width=1, color=DARK["border"]),
            _icon_btn("LOCK_OUTLINED",        "Bloquear  Ctrl+L", on_lock, DARK["danger"]),
        ], spacing=2, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        bgcolor=DARK["panel"],
        padding=ft.Padding(left=10, right=10, top=5, bottom=5),
        border=ft.Border(bottom=ft.BorderSide(1, DARK["border"])),
    )

    # ── Find bar ──────────────────────────────────────────────────────────
    find_bar = ft.Container(
        ref=r_findbar, visible=False,
        content=ft.Container(   # contenedor interno con ref para theme swap
            ref=r_findbar_inner,
            content=ft.Row([
                find_f, replace_f,
                ft.Row([
                    ft.IconButton(icon("SEARCH_OUTLINED"), on_click=on_find, tooltip="Siguiente", icon_color=DARK["accent"], icon_size=16),
                    ft.IconButton(icon("FIND_REPLACE_OUTLINED"), on_click=on_replace, tooltip="Reemplazar Actual", icon_size=16),
                    ft.IconButton(icon("PLAYLIST_ADD_CHECK_CIRCLE_OUTLINED"), on_click=on_replace_all, tooltip="Reemplazar Todo", icon_size=16),
                ], spacing=2),
                find_msg, ft.Container(expand=True),
                ft.IconButton(icon("CLOSE"), on_click=on_toggle_find, icon_size=14),
            ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=DARK["panel"],
            padding=ft.Padding(left=10, right=10, top=2, bottom=2),
            border=ft.Border(bottom=ft.BorderSide(1, DARK["border"])),
        ),
    )

    # ── Área de edición: números + editor ─────────────────────────────────
    #
    # CLAVE para alineación sin scroll asíncrono y Flet 0.82+:
    #   · Se elimina GestureDetector porque 'editor' ahora tiene min_lines=N.
    #   · Crecen sus Heights unificadamente en el DOM.
    #   · editor_area_scroll es la encargada pura del desvío vertical.
    #
    editor_row = ft.Row(
        expand=True, spacing=0,
        vertical_alignment=ft.CrossAxisAlignment.START,
        controls=[
            # Columna de números de línea
            ft.Container(
                ref=r_lineno_container,
                content=lineno_col,
                bgcolor=DARK["lineno_bg"],
                width=50,
                padding=ft.Padding(top=16, bottom=16, left=6, right=8),
                border=ft.Border(right=ft.BorderSide(1, DARK["border"])),
                clip_behavior=ft.ClipBehavior.HARD_EDGE,
            ),
            # Editor con min_lines
            ft.Container(
                ref=r_editor_container,
                expand=True,
                bgcolor=DARK["surface"],
                padding=ft.Padding(top=16, bottom=16, left=12, right=16),
                content=editor,
            ),
        ],
    )

    editor_area = ft.Column(
        expand=True,
        scroll=ft.ScrollMode.AUTO,
        controls=[editor_row],
    )

    editor_col = ft.Column(
        ref=r_editor, visible=False,
        expand=True, spacing=0,
        controls=[find_bar, editor_area],
    )

    # ── Lock screen ───────────────────────────────────────────────────────
    lock_box = ft.Container(
        ref=r_lock, visible=True, expand=True,
        bgcolor=DARK["bg"],
        content=ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(height=50),
                ft.Icon(icon("LOCK_OUTLINED"), size=52, color=DARK["accent"]),
                ft.Container(height=14),
                pwd_title,
                ft.Container(height=6),
                ft.Container(
                    content=ft.Column(
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        tight=True,
                        controls=[
                            pwd_hint, ft.Container(height=6),
                            pwd_field, ft.Container(height=4), pwd_err,
                            ft.Container(height=14),
                            ft.Row([
                                ft.FilledButton(
                                    "Desbloquear", icon=icon("LOCK_OPEN_OUTLINED"),
                                    on_click=on_unlock,
                                    style=ft.ButtonStyle(
                                        bgcolor=DARK["accent"], color=white(),
                                        shape=ft.RoundedRectangleBorder(radius=8),
                                        padding=ft.Padding(left=22, right=22, top=11, bottom=11),
                                    ),
                                ),
                            ], alignment=ft.MainAxisAlignment.CENTER),
                            ft.Container(height=20),
                            ft.Row([
                                ft.TextButton("Abrir otro archivo",    on_click=on_open),
                                ft.TextButton("Recuperar con semilla", on_click=on_seed_recovery),
                            ], alignment=ft.MainAxisAlignment.CENTER),
                            ft.Row([
                                ft.TextButton("Reinserción de Semilla", on_click=on_reinsert_seed, style=ft.ButtonStyle(color=DARK["accent"])),
                                ft.TextButton("Reset Semilla", on_click=on_reset_seed, style=ft.ButtonStyle(color=DARK["danger"])),
                            ], alignment=ft.MainAxisAlignment.CENTER),
                        ],
                    ),
                    width=370, bgcolor=DARK["surface"], border_radius=12,
                    padding=ft.Padding(left=26, right=26, top=26, bottom=26),
                    border=ft.Border(
                        top=ft.BorderSide(1, DARK["border"]), bottom=ft.BorderSide(1, DARK["border"]),
                        left=ft.BorderSide(1, DARK["border"]), right=ft.BorderSide(1, DARK["border"])
                    ),
                ),
            ],
        ),
    )

    # ── Security overlay (moved to app.py) ────────────────────────────────

    # ── Status bar ────────────────────────────────────────────────────────
    status_bar = ft.Container(
        ref=r_status_bar,
        content=ft.Row([
            status_txt, ft.Container(expand=True),
            cursor_txt,
            ft.Container(width=12),
            ft.Text("AES-256-GCM · PBKDF2-200K", size=10, color=DARK["muted"]),
        ]),
        bgcolor=DARK["panel"],
        padding=ft.Padding(left=12, right=12, top=4, bottom=4),
        border=ft.Border(top=ft.BorderSide(1, DARK["border"])),
    )

    # ── Ensamblado final ──────────────────────────────────────────────────
    return ft.Column(
        visible=False, expand=True, spacing=0,
        controls=[
            toolbar,
            ft.Stack(
                expand=True,
                controls=[lock_box, editor_col],
            ),
            status_bar,
        ],
    )
