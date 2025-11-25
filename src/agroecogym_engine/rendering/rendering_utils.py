
import cv2  # noqa: E402
import os
def generate_video(image_folder=".", video_name="farm.avi"):
    """
    Generates an avi video from a collection of png files generated when rendering a farm with farm.render()
    """
    # os.chdir("/home/ganesh/Desktop/video")
    images = [
        img
        for img in os.listdir(image_folder)
        if ("day-" in img)
        and (img.endswith(".jpg") or img.endswith(".jpeg") or img.endswith("png"))
    ]

    fourcc = cv2.VideoWriter_fourcc(*"DIVX")

    maxX, maxY = 64 * 6, 64 * 6

    # Array images should only consider
    # the image files ignoring others if any

    frame = cv2.imread(os.path.join(image_folder, images[0]))

    # setting the frame width, height width
    # the width, height of first image
    y, x, layers = frame.shape

    width, height = (x, y)
    if x > maxX:
        x2 = maxX
        y2 = (int)((x2 / x) * y)
        width, height = (x2, y2)
        if y2 > maxY:
            y3 = maxY
            x3 = (int)((y3 / y2) * x2)
            width, height = (x3, y3)
    else:
        if y > maxY:
            y3 = maxY
            x3 = (int)((y3 / y) * x)
            width, height = (x3, y3)

    video = cv2.VideoWriter(video_name, fourcc, 1, (width, height))

    # Appending the images to the video one by one
    for image in images:
        im = cv2.imread(os.path.join(image_folder, image))
        im = cv2.resize(im, (width, height), interpolation=cv2.INTER_AREA)
        video.write(im)

    # Deallocating memories taken for window creation
    cv2.destroyAllWindows()
    video.release()  # releasing the video generated


def generate_gif(image_folder=".", video_name="farm.gif"):
    """
    Generates an animated gif from a collection of png files generated when rendering a farm with farm.render().
    This way of generating gif is very slow, inefficient, and unreliable. An alternative should be found.
    """
    import imageio.v2 as imageio

    # TODO: This way of generating gif is very slow, inefficient, and unreliable. An alternative should be found.
    # os.chdir("/home/ganesh/Desktop/video")
    images = [
        imageio.imread(img)
        for img in os.listdir(image_folder)
        if ("day-" in img)
        and (img.endswith(".jpg") or img.endswith(".jpeg") or img.endswith("png"))
    ]

    imageio.mimsave(video_name, images)
