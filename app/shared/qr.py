import io
from pathlib import Path

import qrcode
from PIL import Image, ImageDraw, ImageFont
from qrcode.constants import ERROR_CORRECT_M, ERROR_CORRECT_Q

FONT_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"
PROMO_COLOR = (15, 118, 110)


def _png(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def ticket_qr_png(payload: str, box_size: int = 12) -> bytes:
    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_Q, box_size=box_size, border=4)
    qr.add_data(payload)
    qr.make(fit=True)
    return _png(qr.make_image(fill_color="black", back_color="white").convert("RGB"))


def campaign_qr_png(url: str, promo_code: str, box_size: int = 10) -> bytes:
    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_M, box_size=box_size, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    code_img = qr.make_image(fill_color=PROMO_COLOR, back_color="white").convert("RGB")

    pad, banner = 24, 64
    width = code_img.width + pad * 2
    canvas = Image.new("RGB", (width, code_img.height + banner * 2 + pad), "white")
    draw = ImageDraw.Draw(canvas)
    bold = ImageFont.truetype(str(FONT_DIR / "DejaVuSans-Bold.ttf"), 26)
    small = ImageFont.truetype(str(FONT_DIR / "DejaVuSans-Bold.ttf"), 18)

    draw.rectangle([0, 0, width, banner], fill=PROMO_COLOR)
    draw.text((width / 2, banner / 2), "% PROMO", fill="white", font=bold, anchor="mm")
    canvas.paste(code_img, (pad, banner + pad // 2))
    bottom = banner + pad // 2 + code_img.height
    draw.text((width / 2, bottom + 22), promo_code, fill=PROMO_COLOR, font=bold, anchor="mm")
    draw.text((width / 2, bottom + 54), "NOT A TICKET", fill=(90, 90, 90), font=small, anchor="mm")
    draw.rectangle([0, 0, width - 1, canvas.height - 1], outline=PROMO_COLOR, width=6)
    return _png(canvas)
