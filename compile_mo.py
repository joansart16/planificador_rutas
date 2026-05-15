"""One-off script to compile the Catalan .po to .mo."""
import struct
import array


def unescape(s: str) -> str:
    return (
        s.replace(r'\\', '\x00BACKSLASH\x00')
         .replace(r'\n', '\n')
         .replace(r'\t', '\t')
         .replace(r'\"', '"')
         .replace('\x00BACKSLASH\x00', '\\')
    )


def compile_po(po_path: str, mo_path: str) -> None:
    messages: dict[str, str] = {}
    msgid: str | None = None
    msgstr: str | None = None
    in_msgid = False
    in_msgstr = False

    def flush() -> None:
        nonlocal msgid, msgstr, in_msgid, in_msgstr
        if msgid is not None and msgstr is not None:
            messages[unescape(msgid)] = unescape(msgstr)
        msgid = msgstr = None
        in_msgid = in_msgstr = False

    with open(po_path, encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\r\n')
            if not line.strip() or line.startswith('#'):
                if not line.strip():
                    flush()
                continue
            if line.startswith('msgid '):
                flush()
                msgid = line[6:].strip().strip('"')
                in_msgid = True
                in_msgstr = False
            elif line.startswith('msgstr '):
                msgstr = line[7:].strip().strip('"')
                in_msgid = False
                in_msgstr = True
            elif line.startswith('"'):
                val = line.strip().strip('"')
                if in_msgid:
                    msgid = (msgid or '') + val
                elif in_msgstr:
                    msgstr = (msgstr or '') + val
    flush()

    # Drop untranslated entries (msgstr == '')
    messages = {k: v for k, v in messages.items() if v}

    ids = sorted(messages.keys())
    strs = [messages[k] for k in ids]

    ids_data = b''
    strs_data = b''
    offsets = []
    for id_, str_ in zip(ids, strs):
        ib = id_.encode('utf-8') + b'\x00'
        sb = str_.encode('utf-8') + b'\x00'
        offsets.append((len(ids_data), len(ib) - 1, len(strs_data), len(sb) - 1))
        ids_data += ib
        strs_data += sb

    n = len(ids)
    # Header: magic, revision, n_strings, off_originals, off_translations, hash_size, hash_off
    header_size = 7 * 4
    orig_table_off = header_size
    trans_table_off = header_size + n * 8
    strings_off = header_size + n * 16

    output = struct.pack(
        '<Iiiiiii',
        0x950412de, 0, n,
        orig_table_off, trans_table_off,
        0, strings_off + len(ids_data) + len(strs_data),
    )

    for i, o in enumerate(offsets):
        output += struct.pack('<ii', o[1], o[0] + strings_off)
    for i, o in enumerate(offsets):
        output += struct.pack('<ii', o[3], o[2] + strings_off + len(ids_data))

    output += ids_data + strs_data

    with open(mo_path, 'wb') as f:
        f.write(output)
    print(f'Compiled {n} entries to {mo_path}')


if __name__ == '__main__':
    compile_po(
        'locale/ca/LC_MESSAGES/django.po',
        'locale/ca/LC_MESSAGES/django.mo',
    )
