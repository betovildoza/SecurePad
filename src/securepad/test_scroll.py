import flet as ft

def main(page: ft.Page):
    num_col = ft.Text("1", size=14, text_align="right")
    
    def on_change(e):
        n = e.control.value.count("\n") + 1
        num_col.value = "\n".join(str(i+1) for i in range(n))
        e.control.min_lines = n
        page.update()

    t = ft.TextField(multiline=True, min_lines=1, on_change=on_change, size=14, expand=True, border=ft.InputBorder.NONE)
    
    lv = ft.ListView(expand=True, controls=[
        ft.Row([ ft.Container(content=num_col, width=40), t ], vertical_alignment=ft.CrossAxisAlignment.START)
    ])
    page.add(lv)

ft.app(target=main)
