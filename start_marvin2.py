import app as marvin


# Keep Marvin's existing app.py logic exactly as-is.
# The only thing we change is which dashboard template
# gets used for the main screen.

original_render_template = marvin.render_template


def render_template_marvin2(template_name, *args, **kwargs):

    if template_name == "dashboard.html":
        template_name = "dashboard2.html"

    return original_render_template(
        template_name,
        *args,
        **kwargs,
    )


marvin.render_template = render_template_marvin2


if __name__ == "__main__":

    print()
    print("=" * 60)
    print("MARVIN 2 - NEW DASHBOARD LAYOUT")
    print("=" * 60)
    print()
    print("Using template: dashboard2.html")
    print()
    print("Open:")
    print("http://127.0.0.1:5001")
    print()

    marvin.app.run(
        host="0.0.0.0",
        port=5001,
        debug=False,
    )
