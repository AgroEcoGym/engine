
import numpy as np
from pathlib import Path
import os

file_path = Path(os.path.realpath(__file__))
CURRENT_DIR = file_path.parent

def make_rendering_image(farm):
    max_display_actions = farm.rules.actions_allowed["params"][
        "max_action_schedule_size"
    ]

    from PIL import Image, ImageDraw, ImageFont

    sprite_width, sprite_height = 64, 64
    scale_factor = 2
    im_width, im_height = sprite_width * scale_factor, sprite_height * scale_factor
    XX = np.sum([farm.fields[fi].X + 1 for fi in farm.fields])
    YY = np.max(
        [
            farm.fields[fi].Y
            + (int)(
                np.ceil(
                    len(
                        [
                            1
                            for e in farm.fields[fi].entities
                            if farm.fields[fi].entities[e].to_thumbnailimage()
                               is not None
                        ]
                    )
                    / farm.fields[fi].X
                )
            )
            for fi in farm.fields
        ]
    )
    font_size = im_width * XX // (6 * len(farm.fields))

    offsetx = im_width // 2
    offset_header = font_size * 2
    offset_sep = font_size // 2
    offset_foot = font_size * 2

    #print("Font dir",str(CURRENT_DIR) + "\Gidole-Regular.ttf")
    font = ImageFont.truetype(
        str(CURRENT_DIR) + "\Gidole-Regular.ttf", size=font_size
    )
    font_action = ImageFont.truetype(
        str(CURRENT_DIR) + "\Gidole-Regular.ttf",
        size=im_width * XX // (18 * len(farm.fields)),
    )

    left, top, right, bottom = font_action.getbbox("A")
    car_height = np.abs(top - bottom) * 1.33  # font_action.getsize("A")[1]
    # print("FONT:",height,font_action.getsize("A")[1])
    offset_actions = (int)(car_height * max_display_actions + 5 * im_height // 100)

    dashboard_picture = Image.new(
        "RGBA",
        (
            im_width * XX,
            im_height * YY
            + offset_header
            + offset_sep
            + offset_foot
            + offset_actions,
        ),
        (255, 255, 255, 255),
    )
    d = ImageDraw.Draw(dashboard_picture)

    day = (int)(
        farm.fields["Field-0"].entities["Weather-0"].variables["day#int365"].value
    )
    day_string = "Day {:03d}".format(day)

    d.text(
        (
            dashboard_picture.width // 2 - len(day_string) * font_size // 4,
            im_height * YY
            + offset_header
            + offset_sep
            + offset_foot // 4
            + offset_actions,
        ),
        day_string,
        font=font,
        fill=(100, 100, 100),
        stroke_width=2,
        stroke_fill="black",
    )

    # offset_field=0
    for fi in farm.fields:
        # day_string= 'Day {}'.format( (int) (farm.fields[fi].entities['Weather-0'].variables['day#int365'].value))
        text = fi  # "F-"+fi[-1:]
        # print("FFF", font.size,font.getsize("a"),font.getsize(fi))
        left, top, right, bottom = font.getbbox(text)
        width_text = (int)(np.abs(right - left))
        # print("FI size", width_text, font_action.getsize(text))
        # d.text((offsetx+ (farm.fields[fi].X+1)*im_width//2  -font.getsize(text)[0] // 2-im_width//2, offset_header//4), text, font=font, fill=(100, 100, 100), stroke_width=2,
        # stroke_fill="black")
        d.text(
            (
                offsetx + (farm.fields[fi].X) * im_width // 2 - width_text // 2,
                offset_header // 4,
            ),
            text,
            font=font,
            fill=(100, 100, 100),
            stroke_width=2,
            stroke_fill="black",
        )

        index = 0
        for e in farm.fields[fi].entities:
            image = farm.fields[fi].entities[e].to_fieldimage()
            image = image.resize(
                (image.width * scale_factor, image.height * scale_factor)
            )
            # image = image.resize((im_width, im_height))
            dashboard_picture.paste(image, (offsetx, offset_header), image)

            j = index // farm.fields[fi].X
            i = index - j * farm.fields[fi].X
            image_t = farm.fields[fi].entities[e].to_thumbnailimage()
            if image_t is not None:
                image_t = image_t.resize(
                    (image_t.width * scale_factor, image_t.height * scale_factor)
                )
                dd = ImageDraw.Draw(image_t)
                # dd.rectangle(((2,2),(im_width-2,im_height-2)), fill="#ff000000", outline="red")
                xx = offsetx + i * im_width
                yy = (
                        offset_header
                        + farm.fields[fi].Y * im_height
                        + offset_sep
                        + j * im_height
                )
                dashboard_picture.paste(image_t, (xx, yy), image_t)
                # d.rectangle(((xx,yy),(xx+im_width,yy+im_height)), fill="#ffffff00", outline="red")
                index += 1

        offset_field_y = (
                offset_header
                + farm.fields[fi].Y * im_height
                + offset_sep
                + ((index - 1) // farm.fields[fi].X + 1) * im_height
        )
        d.rectangle(
            (
                (offsetx, offset_field_y),
                (
                    offsetx + farm.fields[fi].X * im_width,
                    offset_field_y + offset_actions + im_width // 100,
                ),
            ),
            fill=(255, 255, 255, 255),
            outline=(0, 0, 0, 255),
            width=im_width // 100,
        )

        nb_a = 0
        if farm.state_manager.sim_core.last_farmgym_action:
            # print("LAST ACTION", farm.is_new_day, farm.last_farmgym_action)
            mor, aft = farm.state_manager.sim_core.last_farmgym_action
            if farm.state_manager.sim_core.is_observation_time:
                actions = aft
            else:
                actions = mor
            if actions:
                for a in actions:
                    # print("A", a)
                    fa_key, fi_key, entity_key, action_name, params = a
                    if a[1] == fi and nb_a <= max_display_actions:
                        text = action_name
                        # print("DISPLAY ACTION",action_name, params)
                        if isinstance(params, dict):
                            for p in params:
                                text += " " + str(params[p])
                        # if (type(params) == dict) and ("plot" in params.keys()):
                        #    text += " " + str(params["plot"])
                        xx_a = offsetx + im_width // 100
                        yy_a = offset_field_y + nb_a * car_height + im_width // 100
                        d.text(
                            (xx_a, yy_a),
                            text,
                            font=font_action,
                            fill=(100, 100, 100),
                            stroke_width=1,
                            stroke_fill="black",
                        )
                        nb_a += 1

        offsetx += (farm.fields[fi].X + 1) * im_width

        # offset_field+=(farm.fields[fi].X+1)*im_width

    # dashboard_picture.save("farm-day-" + "{:03d}".format(day) + ".png")
    return dashboard_picture