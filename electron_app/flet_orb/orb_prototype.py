import flet as ft
from flet import Container, Page, Row, Text, AnimationCurve, Blur

def main(page: Page):
    page.title = "Glass‑morphism Orb Prototype"
    page.window_width = 300
    page.window_height = 300
    page.bgcolor = ft.colors.TRANSPARENT

    # Orb container with glass effect
    orb = Container(
        width=120,
        height=120,
        border_radius=60,                     # circular shape
        bgcolor=ft.colors.WHITE38,            # semi‑transparent white
        blur=Blur(radius=12),                 # backdrop blur (glass)
        alignment=ft.alignment.center,
        content=Text("🔮", size=48),
        # optional hover effect
        animate_opacity=ft.Animation(duration=250, curve=AnimationCurve.EASE_IN_OUT),
        opacity=0.85,
        on_hover=lambda e: setattr(orb, "opacity", 1.0) if e.data == "true" else setattr(orb, "opacity", 0.85),
    )

    # Uncomment the following block for drag interactivity
    # def on_drag(e):
    #     orb.left = e.page_x - orb.width / 2
    #     orb.top = e.page_y - orb.height / 2
    # orb.on_pointer_move = on_drag

    page.add(Row([orb], alignment=ft.alignment.center))

ft.app(target=main, view=ft.AppView.WEB_BROWSER)
