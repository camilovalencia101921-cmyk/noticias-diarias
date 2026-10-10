"""Ilustraciones SVG simples por categoría (color del tema + dibujo grande).

Se incrustan una sola vez como <symbol> y cada tarjeta las reutiliza con <use>.
Si existe assets/categorias/<tema>.png o .jpg, la página usa esa imagen.
"""

# Dibujos en un lienzo de 100x100, trazo blanco. "{c}" no se usa: el fondo lo pone el color del tema.
DIBUJOS = {
    # --- serias ---
    "seguridad": '<path d="M50 16 L76 26 V48 C76 66 64 78 50 84 C36 78 24 66 24 48 V26 Z"/><path d="M38 50 l9 9 l16 -18"/>',
    "orden_publico": '<path d="M22 44 L62 30 V70 L22 56 Z"/><path d="M62 38 C74 40 74 60 62 62"/><path d="M30 57 L36 76 H44 L40 60"/>',
    "economia": '<path d="M20 80 H82"/><rect x="26" y="56" width="10" height="20"/><rect x="44" y="42" width="10" height="34"/><rect x="62" y="28" width="10" height="48"/>',
    "inteligencia_artificial": '<rect x="32" y="32" width="36" height="36" rx="4"/><path d="M42 32 V20 M58 32 V20 M42 68 V80 M58 68 V80 M32 42 H20 M32 58 H20 M68 42 H80 M68 58 H80"/><circle cx="50" cy="50" r="7"/>',
    "fenomenos_naturales": '<path d="M14 80 L40 36 L50 50 L60 34 L86 80 Z"/><path d="M46 30 C44 22 52 20 50 12 M58 26 C58 20 64 18 62 12"/>',
    "geopolitica": '<circle cx="50" cy="50" r="30"/><ellipse cx="50" cy="50" rx="13" ry="30"/><path d="M20 50 H80 M26 34 H74 M26 66 H74"/>',
    "guerras": '<circle cx="50" cy="50" r="26"/><circle cx="50" cy="50" r="12"/><path d="M50 14 V34 M50 66 V86 M14 50 H34 M66 50 H86"/>',
    "justicia": '<path d="M50 18 V80 M34 80 H66 M24 30 H76"/><path d="M24 30 L14 54 H34 Z M76 30 L66 54 H86 Z"/>',
    "mercados": '<path d="M16 72 L36 52 L50 62 L82 28"/><path d="M66 28 H82 V44"/><path d="M16 82 H84"/>',
    "politica": '<path d="M20 80 H80 M24 72 H76 M26 46 H74 L50 26 Z"/><path d="M32 48 V70 M44 48 V70 M56 48 V70 M68 48 V70"/>',
    "ciberseguridad": '<rect x="28" y="46" width="44" height="34" rx="5"/><path d="M36 46 V36 C36 22 64 22 64 36 V46"/><circle cx="50" cy="62" r="4"/><path d="M50 66 V72"/>',
    "energia": '<path d="M56 12 L28 56 H48 L42 88 L72 42 H52 Z"/>',
    "salud": '<path d="M42 20 H58 V42 H80 V58 H58 V80 H42 V58 H20 V42 H42 Z"/>',
    "tecnologia": '<rect x="34" y="16" width="32" height="68" rx="6"/><path d="M44 74 H56"/><path d="M14 40 H34 M14 60 H34 M66 30 H86 M66 50 H86"/><circle cx="14" cy="40" r="2"/><circle cx="86" cy="30" r="2"/>',
    "contratacion": '<path d="M28 16 H60 L72 28 V84 H28 Z"/><path d="M36 38 H62 M36 48 H62 M36 58 H52"/><circle cx="62" cy="68" r="8"/><path d="M68 74 L78 84"/>',
    # --- ocio ---
    "anime": '<path d="M50 14 L59 40 L86 40 L64 56 L72 82 L50 66 L28 82 L36 56 L14 40 L41 40 Z"/>',
    "futbol": '<circle cx="50" cy="50" r="32"/><path d="M50 36 L63 45 L58 60 H42 L37 45 Z"/><path d="M50 36 V18 M63 45 L80 40 M58 60 L68 76 M42 60 L32 76 M37 45 L20 40"/>',
    "baloncesto": '<circle cx="50" cy="50" r="32"/><path d="M18 50 H82 M50 18 V82"/><path d="M27 27 C40 40 40 60 27 73 M73 27 C60 40 60 60 73 73"/>',
    "freestyle": '<rect x="38" y="14" width="24" height="40" rx="12"/><path d="M28 44 C28 70 72 70 72 44"/><path d="M50 66 V84 M38 84 H62"/>',
    "historia_antigua": '<path d="M18 30 H82 L50 14 Z"/><path d="M18 84 H82 M22 76 H78"/><path d="M28 34 V74 M42 34 V74 M58 34 V74 M72 34 V74"/>',
    "espiritualidad": '<path d="M50 18 C44 28 44 34 50 38 C56 34 56 28 50 18 Z"/><rect x="40" y="42" width="20" height="40" rx="3"/><path d="M30 86 H70"/>',
    "cine": '<rect x="18" y="40" width="64" height="42" rx="4"/><path d="M18 40 L76 24 L80 36 M30 37 L36 28 M46 33 L52 24 M62 28 L68 20"/>',
    # --- local ---
    "local_seguridad": '<path d="M50 16 L76 26 V48 C76 66 64 78 50 84 C36 78 24 66 24 48 V26 Z"/><path d="M50 34 V56 M50 64 V66"/>',
    "local_orden_publico": '<path d="M14 50 H86 M14 66 H86"/><path d="M22 50 L30 66 M38 50 L46 66 M54 50 L62 66 M70 50 L78 66"/><path d="M22 66 V82 M78 66 V82 M22 50 V40 M78 50 V40"/>',
    "local_movilidad_servicios": '<rect x="24" y="18" width="52" height="56" rx="8"/><path d="M24 50 H76 M34 74 V84 M66 74 V84"/><circle cx="36" cy="62" r="4"/><circle cx="64" cy="62" r="4"/>',
    "local_otros": '<path d="M50 86 C50 86 24 58 24 40 C24 24 36 14 50 14 C64 14 76 24 76 40 C76 58 50 86 50 86 Z"/><circle cx="50" cy="40" r="10"/>',
    "general": '<rect x="18" y="24" width="64" height="52" rx="4"/><path d="M28 36 H72 M28 48 H56 M28 58 H66"/>',
}


def simbolos(colores):
    """colores: {clave: '#hex'}. Devuelve un <svg> oculto con todos los símbolos."""
    partes = []
    for clave, dibujo in DIBUJOS.items():
        color = colores.get(clave, "#455A64")
        partes.append(
            f'<symbol id="ilu-{clave}" viewBox="0 0 100 100" preserveAspectRatio="xMidYMid slice">'
            f'<rect width="100" height="100" fill="{color}"/>'
            f'<g fill="none" stroke="#fff" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round" opacity=".88">'
            f'{dibujo}</g></symbol>')
    return '<svg width="0" height="0" style="position:absolute" aria-hidden="true">' + "".join(partes) + "</svg>"
