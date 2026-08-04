import re
import unicodedata
from pathlib import Path

MAX_LINE_CHARS = 120
USE_TWO_CHARACTER_ALTERNATION = True
FIRST_PERSON = True

DEFAULT_NAME, DEFAULT_ID = "Character", "character"
NARRATOR_NAME, NARRATOR_ID = "Narrator", "narrator"
VERBS_3P = "said|replied|answered|asked|exclaimed|whispered|shouted|cried|muttered"
VERBS_1P = "said|replied|answered|asked|exclaimed|whispered|shouted|cried|muttered"
PRONOUNS = "he|she|they|we|it|i|you"


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
    name = re.sub(r"\b(with|without|while|when|because|but|and|calmly|quietly|softly|loudly|slowly)\b.*$", "", name.strip(" .,:;!?"))
    name = re.sub(r"^(the|a|an)\s+", "", name, flags=re.I).strip()
    return name[:1].upper() + name[1:] if name else DEFAULT_NAME


def after_quote(line):
    """Returns the attribution text after a quoted dialogue, if present."""
    match = re.match(r'^\s*["“](.*?)["”]\s*,?\s*(.*)$', line)
    return match.group(2).strip() if match else ""


def speaker(line):
    """Finds the speaker name from English dialogue attribution, if any."""
    tail = after_quote(line)
    if re.match(rf"i\s+(?:{VERBS_1P})(?:\b|\s)", tail, flags=re.I):
        return NARRATOR_NAME

    match = re.match(rf"(.+?)\s+(?:{VERBS_3P})(?:\b|\s)", tail, flags=re.I)
    if not match:
        return None

    name = clean_name(match.group(1))
    return None if name.lower() in PRONOUNS or name == DEFAULT_NAME else name


def spoken(line):
    """Extracts the actual spoken text from a quoted or dash dialogue line."""
    quote = re.match(r'^\s*["“](.*?)["”]', line)
    if quote:
        return quote.group(1).strip()
    return line[1:].strip() if line.startswith(("—", "-")) else None


def expression(line):
    """Extracts a Ren'Py show expression from a 'with ...' attribution."""
    match = re.search(r"\bwith\s+([^.—\"”]+)", after_quote(line), flags=re.I)
    if not match:
        return "normal"
    text = re.sub(r"^(a|an|the)\s+", "", match.group(1).lower().strip(" .,:;!?"))
    text = re.sub(r"[^a-zA-Z0-9_ ]+", "", text)
    text = re.sub(r"\s+", " ", text.strip(" .,:;!?")).strip()
    return text.replace(" ", "_") if text else "normal"


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


def convert(input_path, output_path, max_line_chars=MAX_LINE_CHARS, use_two_character_alternation=USE_TWO_CHARACTER_ALTERNATION, first_person=FIRST_PERSON):
    """Converts an English TXT file into a Ren'Py .rpy script."""
    lines = [line.strip() for line in input_path.read_text(encoding="utf-8-sig").splitlines()]
    chars = characters_from(lines)
    out = ["# Automatically generated from txt_to_renpy_eng.py"]
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
        if ident != visible and not (first_person and ident == NARRATOR_ID):
            out += ([f"    hide {visible}"] if visible else []) + [f"    show {ident} {expression(line)}"]
            visible = ident
        out += [f'    {ident} "{esc(end_dialogue(part))}"' for part in split_text(text, max_line_chars)]
        previous = ident

    output_path.write_text("\n".join(out + ["", "    return", ""]), encoding="utf-8")


def txt2rpy(input_filename, max_line_chars=MAX_LINE_CHARS, use_two_character_alternation=USE_TWO_CHARACTER_ALTERNATION, first_person=FIRST_PERSON):
    """Runs TXT -> RPY using the path received."""
    input_path = Path(input_filename)
    if not input_path.is_file():
        raise FileNotFoundError(f"TXT file not found: {input_path}")
    output_path = input_path.with_suffix(".rpy")
    convert(input_path, output_path, max_line_chars, use_two_character_alternation, first_person)
    print(f"Converted: {input_path} -> {output_path}")


if __name__ == "__main__":
    txt2rpy("txt_to_renpy/example.txt")
