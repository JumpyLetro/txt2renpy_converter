import argparse

from renpy_to_txt_eng import rpy2txt as eng_rpy2txt
from renpy_to_txt_esp import rpy2txt as esp_rpy2txt
from txt_to_renpy_eng import txt2rpy as eng_txt2rpy
from txt_to_renpy_esp import txt2rpy as esp_txt2rpy


METHODS = {
    ("txt", "eng"): eng_txt2rpy,
    ("txt", "esp"): esp_txt2rpy,
    ("rpy", "eng"): eng_rpy2txt,
    ("rpy", "esp"): esp_rpy2txt,
}


def main():
    parser = argparse.ArgumentParser(
        description="Convert between TXT and Ren'Py RPY files.",
        epilog=(
            "Examples:\n"
            "  python rpy_txt_conversor.py --language esp --file ejemplo.txt\n"
            "  python rpy_txt_conversor.py --language eng --file example.rpy"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--language", choices=("eng", "esp"), required=True)
    parser.add_argument("--file", required=True)
    args = parser.parse_args()

    input_type = args.file.rsplit(".", 1)[-1].lower()
    if input_type not in ("txt", "rpy"):
        parser.error("--file must end with .txt or .rpy")

    METHODS[(input_type, args.language)](args.file)


if __name__ == "__main__":
    main()
