import hashlib
from pathlib import Path

import renpy_to_txt_eng
import renpy_to_txt_esp
import txt_to_renpy_eng
import txt_to_renpy_esp


ROOT_DIR = Path(__file__).resolve().parent
BASE_DIR = ROOT_DIR / "txt_to_renpy"


def sha256(path):
    """Returns the SHA-256 hash of a file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(label, source_txt, first_rpy, restored_txt, second_rpy, txt_to_rpy, rpy_to_txt):
    """Runs TXT -> RPY -> TXT -> RPY and checks byte-for-byte convergence."""
    txt_to_rpy.txt2rpy(source_txt.name)
    source_txt.with_suffix(".rpy").replace(first_rpy)
    rpy_to_txt.rpy2txt(first_rpy.name)
    rpy_to_txt.restored_path(first_rpy).replace(restored_txt)
    txt_to_rpy.txt2rpy(restored_txt.name)
    restored_txt.with_suffix(".rpy").replace(second_rpy)

    first_hash = sha256(first_rpy)
    second_hash = sha256(second_rpy)
    same = first_rpy.read_bytes() == second_rpy.read_bytes()

    print(f"[{label}]")
    print(f"Primer RPY:     {first_rpy}")
    print(f"TXT restaurado: {restored_txt}")
    print(f"Segundo RPY:    {second_rpy}")
    print(f"SHA256 primero: {first_hash}")
    print(f"SHA256 segundo: {second_hash}")
    print(f"Byte a byte:    {'OK' if same else 'DIFERENTE'}")
    print()
    return same


def main():
    """Runs Spanish and English convergence tests."""
    checks = [
        check(
            "ESP",
            BASE_DIR / "ejemplo.txt",
            BASE_DIR / "ejemplo_primero.rpy",
            BASE_DIR / "ejemplo_restaurado.txt",
            BASE_DIR / "ejemplo_restaurado.rpy",
            txt_to_renpy_esp,
            renpy_to_txt_esp,
        ),
        check(
            "ENG",
            BASE_DIR / "example.txt",
            BASE_DIR / "example_first.rpy",
            BASE_DIR / "example_restored.txt",
            BASE_DIR / "example_restored.rpy",
            txt_to_renpy_eng,
            renpy_to_txt_eng,
        ),
    ]

    if not all(checks):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
