def get_colors():
    with open("static/css/val.css") as f:
        # parse first css rule
        css = f.read()
        lines = css.split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("val"):
                name, color = line.split(":")
                name = name.strip()
                color = color.strip()
                if color.endswith(";"):
                    color = color[:-1]
                assert color.startswith("rgb")
                color = color[4:-1]
                color = [int(c.strip()) for c in color.split(",")]
                yield (name, tuple(color))

with open("static/css/val.gen.css", "w") as f:
    def template(name, color):
        v = name
        colors_nums = ", ".join(str(c) for c in color)

        return f"""
.{v} {{
    background-color: rgba({colors_nums}, 0.5);
    cursor: default;
}}

.{v}:hover, .{v}.hover, .{v}-hover .{v} {{
    background-color: rgba({colors_nums}, 1.0);
}}"""
    colors = [
        "red",
        "orange",
        "yellow",
    ]

    f.write("".join([template(name, color) for name, color in get_colors()]))