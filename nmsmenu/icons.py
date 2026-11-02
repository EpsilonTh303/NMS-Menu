"""Small, local vector icon set matching the reference's thin line artwork."""
from functools import lru_cache
from PySide6 import QtCore, QtGui, QtSvg

SHAPES = {
    'settings': '<circle cx="12" cy="12" r="4"/><path d="m9 2 1 3h4l1-3 4 2-2 3 2 3h3v4h-3l-2 3 2 3-4 2-1-3h-4l-1 3-4-2 2-3-2-3H2v-4h3l2-3-2-3Z"/>',
    'signal': '<circle cx="12" cy="12" r="1"/><path d="M8 8a6 6 0 0 0 0 8m8-8a6 6 0 0 1 0 8M5 5a10 10 0 0 0 0 14M19 5a10 10 0 0 1 0 14"/>',
    'ship': '<path d="m12 3 3 8 7 5-8-1-2 5-2-5-8 1 7-5Z M9 11h6M8 16l-2 3m10-3 2 3"/>',
    'box': '<path d="m12 3 9 5-9 5-9-5Z M3 8v10l9 5 9-5V8M12 13v10"/>',
    'weapon': '<path d="m3 7 18-2-1 5-10 1-3 9H3l3-10H3ZM10 11l3 3h3v-4M7 7l10-1"/>',
    'history': '<path d="M3 11a9 9 0 1 1 2 7M3 5v6h6m3-4v6l4 2"/>',
    'route': '<circle cx="5" cy="19" r="2"/><circle cx="19" cy="5" r="2"/><path d="M7 19h6a4 4 0 0 0 0-8h-2a4 4 0 0 1 0-8h6"/>',
    'layers': '<path d="m12 3 10 6-10 6L2 9Zm-10 11 10 6 10-6M2 19l10 5 10-5"/>',
    'refresh': '<path d="M20 9A8 8 0 0 0 6 5L3 8m0-6v6h6M4 15a8 8 0 0 0 14 4l3-3m0 6v-6h-6"/>',
    'basket': '<path d="M3 9h18l-2 12H5ZM7 9l5-7 5 7M9 12v6m6-6v6"/>',
    'cart': '<path d="M2 3h3l3 13h12l2-10H6M8 11h13"/><circle cx="9" cy="21" r="1"/><circle cx="19" cy="21" r="1"/>',
    'folder': '<path d="M2 7V4h8l3 3h9v14H2ZM2 10h20"/>',
    'chip': '<rect x="6" y="6" width="12" height="12" rx="2"/><path d="M9 1v5m6-5v5M9 18v5m6-5v5M1 9h5m-5 6h5M18 9h5m-5 6h5"/><rect x="9" y="9" width="6" height="6"/>',
    'leaf': '<path d="M3 21 19 5M5 17C-1 5 13 2 22 2c0 11-5 22-17 15Z"/>',
    'garage': '<path d="m2 9 10-7 10 7v13H2ZM5 10h14v12M5 14h14M5 18h14"/>',
    'move': '<path d="M3 7h18m-4-4 4 4-4 4M21 17H3m4-4-4 4 4 4"/>',
    'split': '<path d="M12 3v6m0 0-7 8m7-8 7 8"/><circle cx="12" cy="3" r="2"/><circle cx="5" cy="20" r="2"/><circle cx="19" cy="20" r="2"/>',
    'hash': '<path d="m9 2-4 20M19 2l-4 20M2 8h21M1 16h21"/>',
    'link': '<path d="m9 15 6-6M9 7l3-3a5 5 0 0 1 7 7l-3 3M15 17l-3 3a5 5 0 0 1-7-7l3-3"/>',
    'info': '<circle cx="12" cy="12" r="10"/><path d="M12 11v7M12 6v1"/>',
    'pin': '<path d="M12 22S4 14 4 9a8 8 0 1 1 16 0c0 5-8 13-8 13Z"/><circle cx="12" cy="9" r="3"/>',
    'arrow': '<path d="M2 12h20m-7-7 7 7-7 7"/>',
    'check': '<path d="m4 12 5 5L21 5"/>',
    'star': '<path d="m12 2 3 7 8 1-6 5 2 8-7-4-7 4 2-8-6-5 8-1Z"/>',
    'save': '<path d="M3 2h15l4 4v16H2V2ZM7 2v7h10V2M6 22V13h12v9"/>',
}


@lru_cache(maxsize=128)
def pixmap(name, size=24, color='#bdd0d7'):
    data = f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><g fill="none" stroke="{color}" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round">{SHAPES[name]}</g></svg>'
    result = QtGui.QPixmap(size * 2, size * 2)
    result.fill(QtCore.Qt.GlobalColor.transparent)
    painter = QtGui.QPainter(result)
    QtSvg.QSvgRenderer(QtCore.QByteArray(data.encode())).render(painter)
    painter.end()
    result.setDevicePixelRatio(2)
    return result


@lru_cache(maxsize=64)
def icon(name):
    result = QtGui.QIcon()
    for mode, color in [(QtGui.QIcon.Mode.Normal, '#bdd0d7'),
                        (QtGui.QIcon.Mode.Active, '#fff0e8'),
                        (QtGui.QIcon.Mode.Selected, '#fff0e8'),
                        (QtGui.QIcon.Mode.Disabled, '#526a74')]:
        result.addPixmap(pixmap(name, 24, color), mode)
    return result


def for_text(text):
    text = text.lower()
    for words, name in [
        (('yük gemisi', 'fırkateyn'), 'ship'),
        (('envanter / donanım',), 'folder'),
        (('canlı kontroller',), 'signal'), (('canlı filo',), 'ship'),
        (('silah', 'aletin'), 'weapon'), (('filo ve', 'envanter'), 'box'),
        (('yol haritası',), 'route'), (('katalog', 'yerleşik'), 'layers'),
        (('donanım',), 'chip'), (('ara ve seç',), 'basket'),
        (('sepet',), 'cart'), (('yenile',), 'refresh'),
        (('taşı',), 'move'), (('böl',), 'split'), (('miktar',), 'hash'),
        (('birleştir', 'bağlantı'), 'link'), (('arşiv', 'garaj'), 'garage'),
        (('geri al', 'yedek'), 'history'), (('favori',), 'star'),
        (('kaydet',), 'save'), (('uygula', 'kurmak'), 'check'),
        (('plan', 'rapor', 'tarif'), 'folder'),
    ]:
        if any(word in text for word in words):
            return name
    return 'arrow'


@lru_cache(maxsize=16)
def resource_icon(resource):
    color = {'^LAUNCHSUB': '#20b6d8', '^OXYGEN': '#f35d47', '^STELLAR2': '#f3c25b'}.get(resource, '#46a590')
    result = QtGui.QPixmap(40, 40)
    result.fill(QtCore.Qt.GlobalColor.transparent)
    painter = QtGui.QPainter(result)
    painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
    gradient = QtGui.QRadialGradient(17, 15, 19)
    gradient.setColorAt(0, QtGui.QColor('#f1fcff'))
    gradient.setColorAt(.35, QtGui.QColor(color))
    gradient.setColorAt(1, QtGui.QColor('#09212a'))
    painter.setBrush(gradient)
    painter.setPen(QtCore.Qt.PenStyle.NoPen)
    painter.drawEllipse(5, 5, 30, 30)
    painter.end()
    result.setDevicePixelRatio(2)
    return QtGui.QIcon(result)
