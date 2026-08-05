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
OPEN_QUOTE_MARKERS = ('"', "“", "``", "''")
CLOSE_QUOTE_MARKERS = ('"', "”", "''", "\u00b4\u00b4")


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


def quote_marker(line):
    """Returns the opening quote marker used by a line, if any."""
    stripped = line.lstrip()
    return next((marker for marker in OPEN_QUOTE_MARKERS if stripped.startswith(marker)), None)


def quoted_parts(line):
    """Extracts quoted text, attribution tail and whether the quote closes."""
    stripped = line.lstrip()
    opening = quote_marker(stripped)
    if not opening:
        return None, "", False

    text = stripped[len(opening):]
    closing_positions = [
        (index, marker)
        for marker in CLOSE_QUOTE_MARKERS
        if (index := text.find(marker)) != -1
    ]
    if not closing_positions:
        return text.strip(), "", False

    close_index, closing = min(closing_positions)
    tail = text[close_index + len(closing):].lstrip(" ,")
    return text[:close_index].strip(), tail.strip(), True


def after_quote(line):
    """Returns the attribution text after a quoted dialogue, if present."""
    _, tail, closed = quoted_parts(line)
    return tail if closed else ""


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
    quote_text, _, _ = quoted_parts(line)
    if quote_text is not None:
        return quote_text
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

    def emit_dialogue(ident, text, expr):
        nonlocal visible
        if ident != visible and not (first_person and ident == NARRATOR_ID):
            out.extend(([f"    hide {visible}"] if visible else []) + [f"    show {ident} {expr}"])
            visible = ident
        out.extend(f'    {ident} "{esc(end_dialogue(part))}"' for part in split_text(text, max_line_chars))

    index = 0
    while index < len(lines):
        line = lines[index]
        if not line:
            if out[-1]:
                out.append("")
            index += 1
            continue
        text = spoken(line)
        if text is None:
            out += [f'    "{esc(part)}"' for part in split_text(line, max_line_chars)]
            index += 1
            continue

        block = [line]
        _, _, quote_closed = quoted_parts(line)
        index += 1
        while not quote_closed and index < len(lines):
            next_index = index
            while next_index < len(lines) and not lines[next_index]:
                next_index += 1
            if next_index >= len(lines) or not quote_marker(lines[next_index]):
                break
            block.append(lines[next_index])
            _, _, quote_closed = quoted_parts(lines[next_index])
            index = next_index + 1

        block_speakers = [speaker(block_line) for block_line in block]
        explicit_speaker = next((name for name in reversed(block_speakers) if name), None)
        if explicit_speaker:
            ident = resolve(explicit_speaker, chars, previous, use_two_character_alternation)
        else:
            ident = resolve(None, chars, previous, use_two_character_alternation)

        expr = expression(next((block_line for block_line in reversed(block) if speaker(block_line)), block[0]))
        for block_line in block:
            emit_dialogue(ident, spoken(block_line), expr)
        previous = ident

    while out and not out[-1]:
        out.pop()
    output_path.write_text("\n".join(out + ["", "    return", ""]), encoding="utf-8")


def txt2rpy(input_filename, output_filename=None, max_line_chars=MAX_LINE_CHARS, use_two_character_alternation=USE_TWO_CHARACTER_ALTERNATION, first_person=FIRST_PERSON):
    """Runs TXT -> RPY using the path received."""
    input_path = Path(input_filename)
    if not input_path.is_file():
        raise FileNotFoundError(f"TXT file not found: {input_path}")
    output_path = Path(output_filename) if output_filename else input_path.with_suffix(".rpy")
    convert(input_path, output_path, max_line_chars, use_two_character_alternation, first_person)
    print(f"Converted: {input_path} -> {output_path}")


if __name__ == "__main__":
    txt2rpy("txt_to_renpy/example2.txt")
