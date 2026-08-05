from pathlib import Path

from commons import (
    MAX_LINE_CHARS,
    USE_TWO_CHARACTER_ALTERNATION,
    end_dialogue,
    esc,
    markdown_to_renpy,
    slug,
    split_text,
)


def characters_from(lines, config):
    chars, used = {config.default_name: config.default_id}, {config.default_id}
    for name in filter(None, map(config.speaker, lines)):
        if name in chars:
            continue
        base = config.narrator_id if name == config.narrator_name else slug(name, config.default_id)
        ident, n = base, 2
        while ident in used:
            ident, n = f"{base}_{n}", n + 1
        chars[name] = ident
        used.add(ident)
    return chars


def resolve_speaker(name, chars, previous, config, use_two_character_alternation):
    if name in chars:
        return chars[name]
    real = [ident for name, ident in chars.items() if name != config.default_name]
    if use_two_character_alternation and len(real) == 2 and previous in real:
        return real[0] if previous == real[1] else real[1]
    return config.default_id


def emit_narration(out, text, max_line_chars):
    out.extend(f'    "{esc(markdown_to_renpy(part))}"' for part in split_text(text, max_line_chars))


def emit_dialogue(out, ident, text, expr, visible, config, max_line_chars):
    if ident != visible and not (config.first_person and ident == config.narrator_id):
        out.extend(([f"    hide {visible}"] if visible else []) + [f"    show {ident} {expr}"])
        visible = ident
    out.extend(
        f'    {ident} "{esc(markdown_to_renpy(end_dialogue(part)))}"'
        for part in split_text(text, max_line_chars)
    )
    return visible


def convert_text_to_renpy(
    input_path,
    output_path,
    config,
    max_line_chars=MAX_LINE_CHARS,
    use_two_character_alternation=USE_TWO_CHARACTER_ALTERNATION,
):
    lines = [line.strip() for line in input_path.read_text(encoding="utf-8-sig").splitlines()]
    chars = characters_from(lines, config)
    out = [config.header]
    out += [f'define {ident} = Character("{esc(name)}")' for name, ident in chars.items()]
    out += ["", "label start:"]
    previous = visible = None

    index = 0
    while index < len(lines):
        line = lines[index]
        if not line:
            if out[-1]:
                out.append("")
            index += 1
            continue

        if config.spoken(line) is None:
            emit_narration(out, line, max_line_chars)
            index += 1
            continue

        block, index = config.block(lines, index)
        explicit_speaker = next((config.speaker(line) for line in reversed(block) if config.speaker(line)), None)
        ident = resolve_speaker(explicit_speaker, chars, previous, config, use_two_character_alternation)
        speaker_line = next((line for line in reversed(block) if config.speaker(line)), block[0])
        expr = config.expression(speaker_line)
        for block_line in block:
            visible = emit_dialogue(out, ident, config.spoken(block_line), expr, visible, config, max_line_chars)
        previous = ident

    while out and not out[-1]:
        out.pop()
    output_path.write_text("\n".join(out + ["", "    return", ""]), encoding="utf-8")


def run_txt_to_rpy(input_filename, output_filename, config, max_line_chars, use_two_character_alternation):
    input_path = Path(input_filename)
    if not input_path.is_file():
        raise FileNotFoundError(f"TXT/Markdown file not found: {input_path}")
    output_path = Path(output_filename) if output_filename else input_path.with_suffix(".rpy")
    convert_text_to_renpy(input_path, output_path, config, max_line_chars, use_two_character_alternation)
    return input_path, output_path
