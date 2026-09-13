load("render.star", "render")
load("http.star", "http")
load("color.star", "color")
load("encoding/json.star", "json")

def convert_code_to_color(code):
    if code == 63:
        # Red: #DB291C
        return color.rgb(219, 41, 28)
    elif code == 64:
        # Orange: #FF7503
        return color.rgb(255, 117, 3)
    elif code == 65:
        # Yellow: #FFB81D
        return color.rgb(255, 184, 29)
    elif code == 66:
        # Green: #019A44
        return color.rgb(1, 154, 68)
    elif code == 67:
        # Blue: #0084D5
        return color.rgb(0, 132, 213)
    elif code == 68:
        # Violet: #702F8B
        return color.rgb(112, 47, 139)
    elif code == 69:
        return color.rgb(255, 255, 255)
    elif code == 70:
        return color.rgb(0, 0, 0)
    elif code == 71:
        return color.rgb(255, 255, 255)
    else:
        return color.rgb(44, 44, 44)


def generate_row(row_data):

    children = []

    for i in range(0,21):

        bit_color=convert_code_to_color(row_data[i])

        children.append(render.Box(
            width=3,
            height=5,
            child=render.Box(
                width=2,
                height=3,
                color="#2C2C2C",
                child=render.Box(
                    width=2,
                    height=2,
                    color=bit_color,
                )
            ),
        ))

    return render.Row(
        children=children
    )

def generate_grid(grid_data):

    children = []

    for i in range(0,6):
        children.append(generate_row(grid_data[i]))

    return render.Column(
        expanded=True,
        children=children
    )
    

def main(config):

    grid_data = json.decode(config.get("message_body"))

    background_color = "#1F1F1F"
    background_color = "#111111"

    return render.Root(
        child = render.Box(
            color = background_color,
            child = generate_grid(grid_data)
        )
    )
