import os
import math
import base64
import textwrap
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
from moviepy import ImageClip, ColorClip, CompositeVideoClip, concatenate_videoclips, vfx

from agent_01 import company_id
from agent_03 import load_scripts, hex_to_rgb

IMAGE_MODEL = "gpt-image-2.6-sunburst"
load_dotenv(override=True)
openai = OpenAI()

output_folder = "outputs"
W, H = 720, 1280              # vertical 9:16
FPS = 24
SCENE_SECONDS = 4.5           # 3 scenes
POSTER_SECONDS = 4.5
END_SECONDS = 4.0
TRANSITION = 0.5              # crossfade length; total = 22 - 4 x 0.5 = 20s
MOTIONS = ["zoom_in", "pan_left", "zoom_out"]
FONT_BOLD = r"C:\Windows\Fonts\arialbd.ttf"

def create_scene_still(scene, work_folder):
    print(f"ANIMATION AGENT: drawing still for scene {scene['scene_number']}", flush=True)
    prompt = (f"{scene['visual']}\n\nVertical cinematic photograph for a social media ad. "
              "Absolutely no text, letters, words, logos or watermarks in the image.")

    result = openai.images.generate(model=IMAGE_MODEL, prompt=prompt, size="1024x1536")
    path = os.path.join(work_folder, f"scene_{scene['scene_number']}_still.png")
    with open(path, "wb") as f:
        f.write(base64.b64decode(result.data[0].b64_json))
    return path

def fit_to_frame(image_path, out_path):
    # 2:3 image -> 9:16 frame: sharp image in the middle, blurred copy behind it
    image = Image.open(image_path).convert("RGB")
    background = ImageOps.fit(image, (W, H)).filter(ImageFilter.GaussianBlur(30))
    foreground = ImageOps.contain(image, (W, H))
    background.paste(foreground, ((W - foreground.width) // 2, (H - foreground.height) // 2))
    background.save(out_path)
    return out_path

def end_card_background(poster_path, out_path):
    image = Image.open(poster_path).convert("RGB")
    background = ImageOps.fit(image, (W, H)).filter(ImageFilter.GaussianBlur(25))
    background = Image.blend(background, Image.new("RGB", (W, H), "black"), 0.5)
    background.save(out_path)
    return out_path

def make_vignette(out_path, strength=160):
    # Dark soft edges: a cheap "cinematic" look that also makes text easier to read
    mask = Image.new("L", (W, H), strength)
    ImageDraw.Draw(mask).ellipse((-W // 4, -H // 10, W + W // 4, H + H // 10), fill=0)
    mask = mask.filter(ImageFilter.GaussianBlur(120))
    vignette = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    vignette.putalpha(mask)
    vignette.save(out_path)
    return out_path

def text_block_image(text, out_path, font_size=64, max_chars=16, box_color=(0, 0, 0, 150)):
    font = ImageFont.truetype(FONT_BOLD, font_size)
    lines = textwrap.wrap(text.upper(), width=max_chars) or [""]
    line_h = int(font_size * 1.2)

    measure = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    text_w = max(measure.textlength(line, font=font) for line in lines)
    pad = 36
    img_w, img_h = int(text_w + pad * 2), line_h * len(lines) + pad * 2

    img = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    if box_color:
        draw.rounded_rectangle((0, 0, img_w, img_h), radius=30, fill=box_color)
    y = pad
    for line in lines:
        line_w = draw.textlength(line, font=font)
        draw.text(((img_w - line_w) / 2, y), line, font=font, fill="white")
        y += line_h
    img.save(out_path)
    return out_path, img_w, img_h

def ease_out(progress):
    # Fast start, gentle stop: what makes motion look "designed" instead of robotic
    progress = max(0, min(1, progress))
    return 1 - (1 - progress) ** 3

def animated_text(text, seconds, out_path, y_ratio=0.75, delay=0.4, font_size=64, box_color=(0, 0, 0, 150)):
    path, tw, th = text_block_image(text, out_path, font_size, box_color=box_color)
    x = (W - tw) / 2
    y_end = H * y_ratio - th / 2
    rise = 80                                         # slides up 80px

    clip = (ImageClip(path)
            .with_duration(seconds - delay)
            .with_start(delay)
            .with_position(lambda t: (x, y_end + rise * (1 - ease_out(t / 0.6))))
            .with_effects([vfx.CrossFadeIn(0.5), vfx.CrossFadeOut(0.4)]))
    return clip

def ken_burns(image_path, seconds, mode="zoom_in", strength=0.15):
    clip = ImageClip(image_path).with_duration(seconds)
    if mode == "zoom_in":
        moving = clip.resized(lambda t: 1 + strength * t / seconds).with_position("center")
    elif mode == "zoom_out":
        moving = clip.resized(lambda t: 1 + strength * (1 - t / seconds)).with_position("center")
    else:                                             # pan_left
        big = clip.resized(1 + strength)
        extra_w, extra_h = W * strength, H * strength
        moving = big.with_position(lambda t: (-extra_w * t / seconds, -extra_h / 2))
    return CompositeVideoClip([moving], size=(W, H)).with_duration(seconds)

def accent_bar(rgb, seconds, y, delay=0.2, width=None):
    # Brand-coloured line that slides in from the left
    width = width or W - 200
    bar = ColorClip(size=(width, 10), color=rgb).with_duration(seconds - delay).with_start(delay)
    return bar.with_position(lambda t: (-width + (100 + width) * ease_out(t / 0.6), y))

def build_scene(image_path, seconds, mode, text, rgb, text_path, vignette_path):
    layers = [ken_burns(image_path, seconds, mode),
              ImageClip(vignette_path).with_duration(seconds)]
    if text.strip():
        layers.append(accent_bar(rgb, seconds, int(H * 0.75) - 150))
        layers.append(animated_text(text, seconds, text_path))
    return CompositeVideoClip(layers, size=(W, H)).with_duration(seconds)

def build_end_card(poster_path, company_name, cta, rgb, work):
    background = ImageClip(end_card_background(poster_path, os.path.join(work, "end_bg.png"))).with_duration(END_SECONDS)

    name = animated_text(company_name, END_SECONDS, os.path.join(work, "end_name.png"),
                         y_ratio=0.38, delay=0.2, font_size=44, box_color=None)

    cta_path, _, _ = text_block_image(cta, os.path.join(work, "end_cta.png"),
                                      font_size=68, box_color=(*rgb, 235))
    button = (ImageClip(cta_path)
              .with_duration(END_SECONDS - 0.5)
              .with_start(0.5)
              .resized(lambda t: 1 + 0.04 * math.sin(2 * math.pi * t))   # gentle pulse, once per second
              .with_position("center")
              .with_effects([vfx.CrossFadeIn(0.4)]))

    return CompositeVideoClip([background, name, button], size=(W, H)).with_duration(END_SECONDS)

def create_campaign_video(company_name, scripts_path, poster_path):
    print(f"ANIMATION AGENT: creating video for {company_name}", flush=True)
    script = load_scripts(scripts_path)
    scenes = script["storyboard"]
    palette = script["poster"]["colour_palette"]
    rgb = hex_to_rgb(palette[0]["hex"]) if palette else (255, 255, 255)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    work = os.path.join(output_folder, f"{company_id(company_name)}_video_parts_{stamp}")
    os.makedirs(work, exist_ok=True)
    vignette_path = make_vignette(os.path.join(work, "vignette.png"))
    clips = []

    # 1. Three story scenes
    for i, scene in enumerate(scenes[:3]):
        n = scene["scene_number"]
        still = create_scene_still(scene, work)
        framed = fit_to_frame(still, os.path.join(work, f"scene_{n}_framed.png"))
        clips.append(build_scene(framed, SCENE_SECONDS, MOTIONS[i % len(MOTIONS)],
                                 scene["on_screen_text"], rgb,
                                 os.path.join(work, f"text_{n}.png"), vignette_path))

    # 2. Poster with a slow zoom
    poster_frame = fit_to_frame(poster_path, os.path.join(work, "poster_framed.png"))
    clips.append(ken_burns(poster_frame, POSTER_SECONDS, "zoom_in", strength=0.06))

    # 3. End card with the pulsing call to action
    clips.append(build_end_card(poster_path, company_name, script["poster"]["call_to_action"], rgb, work))

    # 4. Crossfade everything together
    print("ANIMATION AGENT: rendering video (this runs on your CPU, a few minutes)", flush=True)
    clips = [clips[0]] + [c.with_effects([vfx.CrossFadeIn(TRANSITION)]) for c in clips[1:]]
    final = concatenate_videoclips(clips, method="compose", padding=-TRANSITION)
    final = final.with_effects([vfx.FadeIn(0.4), vfx.FadeOut(0.6)])

    video_path = os.path.join(output_folder, f"{company_id(company_name)}_video_{stamp}.mp4")
    final.write_videofile(video_path, fps=FPS, codec="libx264", audio=False,
                          bitrate="4000k", preset="medium", threads=4, logger="bar")
    duration = final.duration
    final.close()

    size_mb = os.path.getsize(video_path) / (1024 * 1024)
    print(f"ANIMATION AGENT: saved {video_path} ({duration:.0f}s, {size_mb:.1f} MB)", flush=True)
    return video_path
