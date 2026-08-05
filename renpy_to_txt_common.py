import re
from pathlib import Path

from commons import renpy_to_markdown, unesc


def character_map(lines):
    chars = {}
    for line in lines:
        match = re.match(r'\s*define\s+(\w+)\s*=\s*Character\("((?:\\"|[^"])*)"\)', line)
        if match:
            chars[match.group(1)] = unesc(match.group(2))
    return chars


def quoted_text(line):
    matches = re.findall(r'"((?:\\"|[^"])*)"', line)
    return unesc(matches[-1]) if matches else None


def show_state(line):
    match = re.match(r"\s*show\s+(\w+)\s*(.*)$", line)
    if not match:
        return None, None
    expression = match.group(2).strip()
    return match.group(1), expression if expression and expression != "normal" else None


def dialogue_parts(line, chars):
    match = re.match(r"\s*(\w+)\s+\"((?:\\\"|[^\"])*)\"", line)
    if not match or match.group(1) not in chars:
        return None
    return match.group(1), unesc(match.group(2))


def is_control(line):
    stripped = line.strip()
    return stripped.startswith("#") or stripped.startswith(("define ", "label ", "return", "hide "))


def output_text_path(input_path, output_filename, restored_suffix):
    if output_filename:
        output_path = Path(output_filename)
        return output_path if output_path.suffix.lower() == ".md" else output_path.with_suffix(".txt")
    return input_path.with_name(f"{input_path.stem}{restored_suffix}.txt")


def convert_renpy_to_text(input_path, output_path, config):
    lines = input_path.read_text(encoding="utf-8-sig").splitlines()
    chars = character_map(lines)
    use_markdown = output_path.suffix.lower() == ".md"
    out, visible_expr = [], {}
    pending_dialogue = None

    def emit(text):
        out.append(renpy_to_markdown(text) if use_markdown else text)

    def flush_dialogue():
        nonlocal pending_dialogue
        if not pending_dialogue:
            return
        speaker_id, parts, expression = pending_dialogue
        emit(config.format_dialogue(speaker_id, " ".join(parts), chars, expression))
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
            if chars[speaker_id].lower() != config.generic_name.lower():
                if pending_dialogue and pending_dialogue[0] == speaker_id and pending_dialogue[2] == expression:
                    pending_dialogue[1].append(text)
                else:
                    flush_dialogue()
                    pending_dialogue = (speaker_id, [text], expression)
            else:
                flush_dialogue()
                emit(config.format_dialogue(speaker_id, text, chars, expression))
            continue

        flush_dialogue()
        text = quoted_text(line)
        if text:
            emit(text)

    flush_dialogue()
    while out and not out[-1]:
        out.pop()
    output_path.write_text("\n".join(out) + "\n", encoding="utf-8")


def run_rpy_to_text(input_filename, output_filename, config):
    input_path = Path(input_filename)
    if not input_path.is_file():
        raise FileNotFoundError(f"RPY file not found: {input_path}")
    output_path = output_text_path(input_path, output_filename, config.restored_suffix)
    convert_renpy_to_text(input_path, output_path, config)
    return input_path, output_path
