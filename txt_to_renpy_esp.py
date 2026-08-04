import re
import unicodedata
from pathlib import Path

MAX_LINE_CHARS = 120
USE_TWO_CHARACTER_ALTERNATION = True
PRIMERA_PERSONA = True

DEFAULT_NAME, DEFAULT_ID = "Personaje", "personaje"
NARRATOR_NAME, NARRATOR_ID = "Narrador", "narrador"
VERBS_3P = "dijo|respondio|respondió|contesto|contestó|pregunto|preguntó|exclamo|exclamó|susurro|susurró|grito|gritó"
VERBS_1P = "dije|respondi|respondí|conteste|contesté|pregunte|pregunté|exclame|exclamé|susurre|susurré|grite|grité"
ACCENTS = "áéíóúÁÉÍÓÚñÑüÜ"


def esc(text):
    """Escapes text so it is safe inside Ren'Py quotes."""
    return text.replace("\\", "\\\\").replace('"', '\\"')


def slug(name):
    """Builds a valid Ren'Py identifier from a character name."""
    raw = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    ident = re.sub(r"\W+", "_", raw.lower()).strip("_") or DEFAULT_ID
    return f"p_{ident}" if ident[0].isdigit() else ident


def clean_name(name):
    """Cleans an inferred speaker name from dialogue attribution text."""
    name = re.sub(r"\b(con|sin|mientras|cuando|porque|pero|y)\b.*$", "", name.strip(" .,:;!?¡¿"), flags=re.I)
    name = re.sub(r"^(el|la|los|las|un|una|unos|unas)\s+", "", name, flags=re.I).strip()
    return name[:1].upper() + name[1:] if name else DEFAULT_NAME


def speaker(line):
    """Finds the speaker name from dialogue attribution, if any."""
    if re.search(rf"[—-]\s*(?:{VERBS_1P})(?:\b|\s)", line, flags=re.I):
        return NARRATOR_NAME
    match = re.search(rf"[—-]\s*(?:{VERBS_3P})\s+([^.—-]+)", line, flags=re.I)
    name = clean_name(match.group(1)) if match else DEFAULT_NAME
    return name if name != DEFAULT_NAME else None


def spoken(line):
    """Extracts the actual spoken text from a dialogue line."""
    if not line.startswith(("—", "-")):
        return None
    text = line[1:].strip()
    cut = re.search(rf"\s+[—-]\s*[a-zA-Z{ACCENTS}]", text)
    return text[:cut.start()].strip() if cut else text


def expression(line):
    """Extracts a Ren'Py show expression from a 'con ...' attribution."""
    match = re.search(r"\bcon\s+([^.—-]+)", line, flags=re.I)
    if not match:
        return "normal"
    text = re.sub(rf"[^a-zA-Z0-9{ACCENTS}_ ]+", "", match.group(1).lower())
    text = re.sub(r"\s+", " ", text.strip(" .,:;!?¡¿")).strip()
    return f"con {text}" if text else "normal"


def split_text(text, max_line_chars=MAX_LINE_CHARS):
    """Splits long text by periods when it exceeds MAX_LINE_CHARS."""
    return [text] if len(text) <= max_line_chars else [p.strip() for p in re.findall(r"[^.]+(?:\.|$)", text) if p.strip()] or [text]


def end_dialogue(text):
    """Ensures a Ren'Py dialogue line ends with ., ! or ?."""
    text = text.rstrip()
    return text if text.endswith((".", "!", "?")) else text.rstrip(",;:") + "."


def characters_from(lines):
    """Detects all named characters and assigns Ren'Py identifiers."""
    chars, used = {DEFAULT_NAME: DEFAULT_ID}, {DEFAULT_ID}
    for name in filter(None, map(speaker, lines)):
        if name in chars:
            continue
        base, n = (NARRATOR_ID if name == NARRATOR_NAME else slug(name)), 2
        ident = base
        while ident in used:
            ident, n = f"{base}_{n}", n + 1
        chars[name] = ident
        used.add(ident)
    return chars


def resolve(name, chars, previous, use_two_character_alternation=USE_TWO_CHARACTER_ALTERNATION):
    """Resolves unknown speakers using the two-character alternation heuristic."""
    if name in chars:
        return chars[name]
    real = [ident for name, ident in chars.items() if name != DEFAULT_NAME]
    if use_two_character_alternation and len(real) == 2 and previous in real:
        return real[0] if previous == real[1] else real[1]
    return DEFAULT_ID


def convert(input_path, output_path, max_line_chars=MAX_LINE_CHARS, use_two_character_alternation=USE_TWO_CHARACTER_ALTERNATION, primera_persona=PRIMERA_PERSONA):
    """Converts a TXT file into a Ren'Py .rpy script."""
    lines = [line.strip() for line in input_path.read_text(encoding="utf-8-sig").splitlines()]
    chars = characters_from(lines)
    out = ["# Archivo generado automaticamente desde txt_to_renpy.py"]
    out += [f'define {ident} = Character("{esc(name)}")' for name, ident in chars.items()]
    out += ["", "label start:"]
    previous = visible = None

    for line in lines:
        if not line:
            if out[-1]:
                out.append("")
            continue
        text = spoken(line)
        if text is None:
            out += [f'    "{esc(part)}"' for part in split_text(line, max_line_chars)]
            continue
        ident = resolve(speaker(line), chars, previous, use_two_character_alternation)
        if ident != visible and not (primera_persona and ident == NARRATOR_ID):
            out += ([f"    hide {visible}"] if visible else []) + [f"    show {ident} {expression(line)}"]
            visible = ident
        out += [f'    {ident} "{esc(end_dialogue(part))}"' for part in split_text(text, max_line_chars)]
        previous = ident

    output_path.write_text("\n".join(out + ["", "    return", ""]), encoding="utf-8")


def txt2rpy(input_filename, max_line_chars=MAX_LINE_CHARS, use_two_character_alternation=USE_TWO_CHARACTER_ALTERNATION, primera_persona=PRIMERA_PERSONA):
    """Runs TXT -> RPY using the path received."""
    input_path = Path(input_filename)
    if not input_path.is_file():
        raise FileNotFoundError(f"No existe el archivo TXT: {input_path}")
    output_path = input_path.with_suffix(".rpy")
    convert(input_path, output_path, max_line_chars, use_two_character_alternation, primera_persona)
    print(f"Convertido: {input_path} -> {output_path}")


if __name__ == "__main__":
    txt2rpy("txt_to_renpy/ejemplo.txt")
