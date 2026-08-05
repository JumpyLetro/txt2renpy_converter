import contextlib
import io
import re
from pathlib import Path

import rpy_txt_conversor


ROOT_DIR = Path(__file__).resolve().parent
BASE_DIR = ROOT_DIR / "txt_to_renpy"
EXAMPLE_COUNT = 5


def run_conversion(language, source_file, output_file):
    """Runs the public converter entry point with an explicit output file."""
    with contextlib.redirect_stdout(io.StringIO()):
        rpy_txt_conversor.main([
            "--language",
            language,
            "--file",
            str(source_file),
            "--output",
            str(output_file),
        ])


def check(language, source_txt):
    """Runs TXT -> RPY -> TXT -> RPY and checks byte-for-byte convergence."""
    first_rpy = source_txt.with_name(f"{source_txt.stem}_test.rpy")
    restored_txt = source_txt.with_name(f"{source_txt.stem}_restored_test.txt")
    second_rpy = source_txt.with_name(f"{source_txt.stem}_restored_test.rpy")
    generated_files = (first_rpy, restored_txt, second_rpy)

    try:
        run_conversion(language, source_txt, first_rpy)
        run_conversion(language, first_rpy, restored_txt)
        run_conversion(language, restored_txt, second_rpy)

        return first_rpy.read_bytes() == second_rpy.read_bytes()
    finally:
        for generated_file in generated_files:
            generated_file.unlink(missing_ok=True)


def character_block_count(rpy_file):
    """Counts consecutive Ren'Py dialogue lines from the same character as one block."""
    count = 0
    previous_character = None
    for line in rpy_file.read_text(encoding="utf-8").splitlines():
        match = re.match(r'\s*(\w+)\s+"', line)
        if not match:
            previous_character = None
            continue

        character = match.group(1)
        if character != previous_character:
            count += 1
        previous_character = character
    return count


def check_language_similarity(index):
    """Checks whether matching Spanish and English examples produce the same number of character blocks."""
    spanish_rpy = BASE_DIR / f"ejemplo{index}_similarity_test.rpy"
    english_rpy = BASE_DIR / f"example{index}_similarity_test.rpy"
    generated_files = (spanish_rpy, english_rpy)

    try:
        run_conversion("esp", BASE_DIR / f"ejemplo{index}.txt", spanish_rpy)
        run_conversion("eng", BASE_DIR / f"example{index}.txt", english_rpy)
        return character_block_count(spanish_rpy) == character_block_count(english_rpy)
    finally:
        for generated_file in generated_files:
            generated_file.unlink(missing_ok=True)


def main():
    """Runs convergence and cross-language similarity tests."""
    spanish_checks = []
    english_checks = []
    similarity_checks = []
    for index in range(1, EXAMPLE_COUNT + 1):
        spanish_checks.append(check("esp", BASE_DIR / f"ejemplo{index}.txt"))
        english_checks.append(check("eng", BASE_DIR / f"example{index}.txt"))
        similarity_checks.append(check_language_similarity(index))

    print(f"TEST convergencia: superado en {sum(spanish_checks)}/{len(spanish_checks)} archivos en español.")
    print(f"TEST convergencia: superado en {sum(english_checks)}/{len(english_checks)} archivos en inglés.")
    print(f"TEST similitud líneas idiomas: superado en {sum(similarity_checks)}/{len(similarity_checks)} pares de archivos.")

    if not all(spanish_checks + english_checks + similarity_checks):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
