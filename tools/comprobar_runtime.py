"""Exercise the real portrait dependencies before doing expensive conversions."""
import sys as _sys, pathlib as _pl; _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent))
from idioma import t
import io
import sys


def comprobar():
    try:
        from PIL import Image
        import numpy as np
        import etcpak
        import texture2ddecoder
        image = Image.new('RGBA', (4, 4), (255, 0, 0, 255))
        buf = io.BytesIO()
        image.save(buf, format='PNG')
        buf.seek(0)
        assert Image.open(buf).convert('RGBA').getpixel((0, 0)) == (255, 0, 0, 255)
        assert np.array(image).shape == (4, 4, 4)
        block = etcpak.compress_bc3(image.tobytes(), 4, 4)
        assert texture2ddecoder.decode_bc3(block, 4, 4)[:4] == bytes((0, 0, 255, 255))
        print(t('Librerias comprobadas: lectura PNG y compresion de retratos OK.', 'Libraries checked: PNG reading and portrait compression OK.'), flush=True)
        return Image.__file__
    except Exception:
        import traceback
        print(t('Fallo en las librerias ANTES de convertir personajes.', 'Library failure BEFORE converting characters.'), flush=True)
        print('Python:', sys.executable, flush=True)
        print('Rutas de importacion:', sys.path, flush=True)
        pil = sys.modules.get('PIL')
        print('PIL:', repr(pil), 'archivo:', getattr(pil, '__file__', None), flush=True)
        traceback.print_exc()
        raise


if __name__ == '__main__':
    comprobar()
