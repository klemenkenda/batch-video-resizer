from pathlib import Path

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QIcon, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap
from PyQt6.QtWidgets import QApplication


def build_icon() -> QIcon:
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)

        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        rect = QRectF(1, 1, size - 2, size - 2)
        radius = size * 0.22
        bg = QPainterPath()
        bg.addRoundedRect(rect, radius, radius)

        grad = QLinearGradient(0, 0, size, size)
        grad.setColorAt(0.0, QColor("#2f6d99"))
        grad.setColorAt(1.0, QColor("#2f9f5f"))
        p.fillPath(bg, grad)

        p.setPen(QPen(QColor(255, 255, 255, 90), max(1.0, size * 0.03)))
        p.drawPath(bg)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#ffffff"))
        tri = QPainterPath()
        tri.moveTo(QPointF(size * 0.40, size * 0.30))
        tri.lineTo(QPointF(size * 0.72, size * 0.50))
        tri.lineTo(QPointF(size * 0.40, size * 0.70))
        tri.closeSubpath()
        p.drawPath(tri)

        p.setPen(QColor(255, 255, 255, 215))
        f = QFont("Segoe UI", max(6, int(size * 0.12)))
        f.setBold(True)
        p.setFont(f)
        p.drawText(QRectF(0, size * 0.72, size, size * 0.22), Qt.AlignmentFlag.AlignHCenter, "VR")

        p.end()
        icon.addPixmap(pix)

    return icon


def main() -> None:
    app = QApplication.instance() or QApplication([])

    root = Path(__file__).resolve().parents[1]
    assets = root / "assets"
    assets.mkdir(parents=True, exist_ok=True)

    icon = build_icon()
    out_path = assets / "app.ico"

    ok = icon.pixmap(256, 256).save(str(out_path), "ICO")
    if not ok:
        raise RuntimeError("Failed to save ICO file. Qt ICO plugin may be unavailable.")

    print(f"Generated icon: {out_path}")
    app.quit()


if __name__ == "__main__":
    main()
