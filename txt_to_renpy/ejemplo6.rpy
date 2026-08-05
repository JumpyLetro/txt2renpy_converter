# Archivo generado automaticamente desde rpy_txt_conversor.py
define personaje = Character("Personaje")
define narrador = Character("Narrador")
define clara = Character("Clara")
define ella = Character("Ella")

label start:
    "El reloj de la cocina marcaba una hora imposible y nadie quiso preguntarse por qué."

    narrador "He dejado la llave bajo la maceta {i}azul{/i}."

    "La ventana estaba abierta, aunque la tormenta parecía venir desde dentro de la casa."

    show clara con una calma demasiado ensayada
    clara "No toques esa caja {b}todavía{/b}."

    "El pasillo olía a madera mojada y a {b}{i}flores quemadas{/i}{/b}."

    narrador "Si escuchas tres golpes, {b}no respondas{/b}."

    "Clara apretó la linterna hasta que los nudillos se le pusieron blancos."

    hide clara
    show ella normal
    ella "Entonces tendremos que cruzar el jardín {b}{i}antes del amanecer{/i}{/b}."

    "En el buzón apareció una carta sin sello, sin nombre y sin sombra."

    narrador "Esta noche {i}nadie{/i} va a dormir."

    return
