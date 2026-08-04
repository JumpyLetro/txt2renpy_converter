# txt2renpy_coverter
Un convertidor de archivos .txt a archivos .rpy y viceversa muy básico. Funciona en inglés y español. //A very basic converter from .txt files to .rpy files and vice-versa. Works in English and Spanish.

Como es una tremenda vibecodeada lo dejo con la licencia Unlicense, que lo aproveche quien quiera. Es uno de esos pequeños útiles que van bien.

Ejemplo de uso

## Uso

Todos los archivos de entrada se leen desde la carpeta donde esté el código.

### Ejemplo de cómo convertir TXT español a Ren'Py

```bash
python rpy_txt_conversor.py --input txt --language esp --file ejemplo.txt
```


## Otros

El archivo  `convergence_test.py` sirve de prueba de que las conversiones hechas por el código no degeneran: si transformas un .txt a .rpy y después a .txt de nuevo y finalmente a un segundo .rpy, los dos archivos .rpy serán idénticos. Tanto con el código para texto en español como en inglés.
