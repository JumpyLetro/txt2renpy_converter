import argparse
from dataclasses import replace

from commons import (
    EN_RESTORE_CONFIG,
    EN_TXT_CONFIG,
    ES_RESTORE_CONFIG,
    ES_TXT_CONFIG,
    MAX_LINE_CHARS,
    USE_TWO_CHARACTER_ALTERNATION,
)
from renpy_to_txt_common import run_rpy_to_text
from txt_to_renpy_common import run_txt_to_rpy


FIRST_PERSON = EN_TXT_CONFIG.first_person
PRIMERA_PERSONA = ES_TXT_CONFIG.first_person


def eng_txt2rpy(input_filename, output_filename=None, max_line_chars=MAX_LINE_CHARS, use_two_character_alternation=USE_TWO_CHARACTER_ALTERNATION, first_person=FIRST_PERSON):
    """Runs English TXT/Markdown -> RPY using the path received."""
    config = replace(EN_TXT_CONFIG, first_person=first_person)
    input_path, output_path = run_txt_to_rpy(input_filename, output_filename, config, max_line_chars, use_two_character_alternation)
    print(f"Converted: {input_path} -> {output_path}")


def esp_txt2rpy(input_filename, output_filename=None, max_line_chars=MAX_LINE_CHARS, use_two_character_alternation=USE_TWO_CHARACTER_ALTERNATION, primera_persona=PRIMERA_PERSONA):
    """Runs Spanish TXT/Markdown -> RPY using the path received."""
    config = replace(ES_TXT_CONFIG, first_person=primera_persona)
    input_path, output_path = run_txt_to_rpy(input_filename, output_filename, config, max_line_chars, use_two_character_alternation)
    print(f"Convertido: {input_path} -> {output_path}")


def eng_rpy2txt(input_filename, output_filename=None):
    """Runs English RPY -> TXT/Markdown using the path received."""
    input_path, output_path = run_rpy_to_text(input_filename, output_filename, EN_RESTORE_CONFIG)
    print(f"Restored: {input_path} -> {output_path}")


def esp_rpy2txt(input_filename, output_filename=None):
    """Runs Spanish RPY -> TXT/Markdown using the path received."""
    input_path, output_path = run_rpy_to_text(input_filename, output_filename, ES_RESTORE_CONFIG)
    print(f"Restaurado: {input_path} -> {output_path}")


METHODS = {
    ("txt", "eng"): eng_txt2rpy,
    ("txt", "esp"): esp_txt2rpy,
    ("md", "eng"): eng_txt2rpy,
    ("md", "esp"): esp_txt2rpy,
    ("rpy", "eng"): eng_rpy2txt,
    ("rpy", "esp"): esp_rpy2txt,
}


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Convert between TXT and Ren'Py RPY files.",
        epilog=(
            "Examples:\n"
            "  python rpy_txt_conversor.py --language esp --file ejemplo.txt\n"
            "  python rpy_txt_conversor.py --language esp --file ejemplo.md\n"
            "  python rpy_txt_conversor.py --language eng --file example.rpy\n"
            "  python rpy_txt_conversor.py --language esp --file ejemplo.txt --output salida.rpy\n"
            "  python rpy_txt_conversor.py --language eng --file example.rpy --output restored.md"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--language", choices=("eng", "esp"), required=True)
    parser.add_argument("--file", required=True)
    parser.add_argument("--output", help="Output file name/path. RPY inputs generate .txt unless this ends with .md.")
    args = parser.parse_args(argv)

    input_type = args.file.rsplit(".", 1)[-1].lower()
    if input_type not in ("txt", "md", "rpy"):
        parser.error("--file must end with .txt, .md or .rpy")

    METHODS[(input_type, args.language)](args.file, output_filename=args.output)


if __name__ == "__main__":
    esp_txt2rpy("txt_to_renpy/ejemplo6.md")
    main()
