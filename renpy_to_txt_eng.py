import re
from pathlib import Path

MAX_LINE_CHARS = 120
USE_TWO_CHARACTER_ALTERNATION = True
FIRST_PERSON = True


def unesc(text):
    """Unescapes the small subset of Ren'Py string escapes this project writes."""
    return text.replace('\\"', '"').replace("\\\\", "\\")


def restored_path(input_path):
    """Builds XXX_restored.txt next to the source .rpy file."""
    return input_path.with_name(f"{input_path.stem}_restored.txt")


def character_map(lines):
    """Reads Ren'Py Character definitions as identifier -> display name."""
    chars = {}
    for line in lines:
        match = re.match(r'\s*define\s+(\w+)\s*=\s*Character\("((?:\\"|[^"])*)"\)', line)
        if match:
            chars[match.group(1)] = unesc(match.group(2))
    return chars


def quoted_text(line):
    """Extracts the last quoted string from a Ren'Py narration or dialogue line."""
    matches = re.findall(r'"((?:\\"|[^"])*)"', line)
    return unesc(matches[-1]) if matches else None


def show_state(line):
    """Returns the shown character id and expression from a show command."""
    match = re.match(r"\s*show\s+(\w+)\s*(.*)$", line)
    if not match:
        return None, None
    expression = match.group(2).strip()
    return match.group(1), expression if expression and expression != "normal" else None


def text_before_attribution(text):
    """Removes a final dot before attribution, but keeps !, ? and ellipsis."""
    return text[:-1] if text.endswith(".") and not text.endswith("...") else text


def readable_expression(expression):
    """Converts a Ren'Py image attribute back into English attribution text."""
    return expression.replace("_", " ") if expression else None


def quote_for_attribution(text):
    """Adds a comma only when English attribution needs one."""
    return f'"{text}"' if text.endswith(("!", "?", "...")) else f'"{text},"'


def dialogue_parts(line, chars):
    """Returns the speaker id and text from a Ren'Py dialogue line."""
    match = re.match(r"\s*(\w+)\s+\"((?:\\\"|[^\"])*)\"", line)
    if not match or match.group(1) not in chars:
        return None

    return match.group(1), unesc(match.group(2))


def is_identified_speaker(speaker_id, chars):
    """Checks whether a speaker should have consecutive dialogue lines merged."""
    return chars[speaker_id].lower() != "character"


def dialogue(speaker_id, text, chars, expression):
    """Converts English dialogue data into prose dialogue."""
    text = text_before_attribution(text)
    name = chars[speaker_id]
    expression = readable_expression(expression)

    if name.lower() == "narrator":
        return f"{quote_for_attribution(text)} I said"
    if name.lower() == "character":
        return f"{quote_for_attribution(text)} said with {expression}" if expression else f'"{text}"'

    suffix = f" with {expression}" if expression else ""
    return f"{quote_for_attribution(text)} {name} said{suffix}"


def is_control(line):
    """Detects Ren'Py lines that should not be restored as TXT."""
    stripped = line.strip()
    return stripped.startswith("#") or stripped.startswith(("define ", "label ", "return", "hide "))


def convert(input_path, output_path, max_line_chars=MAX_LINE_CHARS, use_two_character_alternation=USE_TWO_CHARACTER_ALTERNATION, first_person=FIRST_PERSON):
    """Converts a Ren'Py .rpy script back into a readable English TXT."""
    lines = input_path.read_text(encoding="utf-8-sig").splitlines()
    chars = character_map(lines)
    out, visible_expr = [], {}
    pending_dialogue = None

    def flush_dialogue():
        nonlocal pending_dialogue
        if not pending_dialogue:
            return
        speaker_id, parts, expression = pending_dialogue
        out.append(dialogue(speaker_id, " ".join(parts), chars, expression))
        pending_dialogue = None

    for line in lines:
        shown_id, expr = show_state(line)
        if shown_id:
            if pending_dialogue and pending_dialogue[0] == shown_id and pending_dialogue[2] != expr:
                flush_dialogue()
            visible_expr[shown_id] = expr
            continue
        if not line.strip():
            flush_dialogue()
            if out and out[-1]:
                out.append("")
            continue
        if is_control(line):
            flush_dialogue()
            continue

        parts = dialogue_parts(line, chars)
        if parts:
            speaker_id, text = parts
            expression = visible_expr.get(speaker_id)
            if is_identified_speaker(speaker_id, chars):
                if pending_dialogue and pending_dialogue[0] == speaker_id and pending_dialogue[2] == expression:
                    pending_dialogue[1].append(text)
                else:
                    flush_dialogue()
                    pending_dialogue = (speaker_id, [text], expression)
            else:
                flush_dialogue()
                out.append(dialogue(speaker_id, text, chars, expression))
            continue

        flush_dialogue()
        text = quoted_text(line)
        if text:
            out.append(text)

    flush_dialogue()
    while out and not out[-1]:
        out.pop()
    output_path.write_text("\n".join(out) + "\n", encoding="utf-8")


def rpy2txt(input_filename, output_filename=None, max_line_chars=MAX_LINE_CHARS, use_two_character_alternation=USE_TWO_CHARACTER_ALTERNATION, first_person=FIRST_PERSON):
    """Runs RPY -> TXT using the path received."""
    input_path = Path(input_filename)
    if not input_path.is_file():
        raise FileNotFoundError(f"RPY file not found: {input_path}")

    output_path = Path(output_filename) if output_filename else restored_path(input_path)
    convert(input_path, output_path, max_line_chars, use_two_character_alternation, first_person)
    print(f"Restored: {input_path} -> {output_path}")


if __name__ == "__main__":
    rpy2txt("txt_to_renpy/example1.rpy")
