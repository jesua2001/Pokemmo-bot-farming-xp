POKEMON BOT - PRIMERA VERSION

Que hace:
- Camina A/D automaticamente.
- Detecta visualmente el boton LUCHA.
- Pulsa Z para entrar en LUCHA.
- Detecta el menu de movimientos.
- Pulsa Z para usar el primer movimiento.
- Cuando termina el combate vuelve a caminar.

Archivos:
- bot.py
- battle_menu.png
- move_menu.png
- requirements.txt

INSTALACION (Windows / PowerShell):

1. Instala Python 3.11 o 3.12.
2. Abre una terminal dentro de esta carpeta.
3. Ejecuta:

   py -m pip install -r requirements.txt

4. Abre el juego y deja la misma escala/resolucion que en las capturas.
5. Ejecuta:

   py bot.py

Controles:
- F8: pausar / reanudar
- F9: cerrar
- Tambien puedes mover el raton a una esquina de la pantalla para activar
  la parada de emergencia de PyAutoGUI.

Si tu tecla de confirmar no es Z, cambia en bot.py:

CONFIRM_KEY = "z"

Si caminas con flechas en vez de A/D, cambia:

MOVE_LEFT = "left"
MOVE_RIGHT = "right"

Si detecta mal los menus, ajusta MATCH_THRESHOLD. Prueba normalmente entre
0.75 y 0.90. Cuanto mas alto, mas estricta es la deteccion.
