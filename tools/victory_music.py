"""Original Office Champion score, using the title's exact synthesized timbres.

No new samples or RNG calls: extract the five authored instruments and PCM
waves from music0.it after all four legacy scores have been generated.
"""
from pathlib import Path
import struct


def soundbank_budget(path: Path) -> dict:
    """Validate SMConv's LoROM bank and simultaneous module/effect residency.

    The pinned SNESMod loads module data at $1A00, then its BRR sources,
    then spcLoadEffect's four sources. Transfers round up to whole words.
    This project has no echo or separate streaming allocation.
    """
    raw = path.read_bytes()
    if not 388 <= len(raw) <= 32768:
        raise ValueError("Effects plus five scores must remain in LoROM bank 24")
    sources, modules = struct.unpack_from("<HH", raw)
    if not 4 <= sources <= 64 or modules != 6:
        raise ValueError("Soundbank requires effects-first plus five music modules")

    def pointer(table: int, index: int) -> int:
        address, bank = struct.unpack_from("<HB", raw, table+index*3)
        if not 0x8000 <= address <= 0xffff or bank != 0:
            raise ValueError("Soundbank pointer escaped its single LoROM bank")
        return address-0x8000

    sample_bytes = []
    for index in range(sources):
        offset = pointer(388, index)
        size = struct.unpack_from("<H", raw, offset)[0]
        if not size or offset+4+size > len(raw):
            raise ValueError("Soundbank source length exceeds bank data")
        sample_bytes.append((size+1) & ~1)
    resident_bytes = sum(sample_bytes[:4])
    budgets = []
    for index in range(modules):
        offset = pointer(4, index)
        words, count = struct.unpack_from("<HH", raw, offset)
        if not 0 < count <= 64:
            raise ValueError("Soundbank module has an invalid source list")
        source_list = struct.unpack_from("<"+str(count)+"H", raw, offset+4)
        start = offset+4+count*2
        if not words or start+words*2 > len(raw) or any(i >= sources for i in source_list):
            raise ValueError("Soundbank module data exceeds bank data")
        if raw[start+21] != 0:
            raise ValueError("Champion audio budget requires the existing zero-echo contract")
        source_bytes = sum(sample_bytes[i] for i in source_list)
        end = 0x1a00+words*2+source_bytes+resident_bytes
        if end > 0x10000:
            raise ValueError("Score plus all four resident cues exceeds SPC RAM")
        budgets.append({"module_id": index, "module_bytes": words*2,
                        "music_brr_bytes": source_bytes, "source_indices": list(source_list),
                        "resident_cue_bytes": resident_bytes, "spc_end_exclusive": end,
                        "spc_free_bytes": 0x10000-end})
    if budgets[0]["source_indices"] != [0, 1, 2, 3]:
        raise ValueError("Resident cue identity/order is no longer effects-first")
    return {"soundbank_bytes": len(raw), "lorom_bank": 24,
            "lorom_free_bytes": 32768-len(raw), "module_base": 0x1a00,
            "source_count": sources, "module_count": modules,
            "streaming_bytes": 0, "echo_bytes": 0, "modules": budgets}


def make_victory_it(path: Path, title: Path) -> None:
    source = title.read_bytes()
    if source[:4] != b"IMPM" or struct.unpack_from("<4H", source, 32) != (5, 5, 5, 4):
        raise ValueError("Victory timbres require the original five-sample title IT")
    instrument_offsets = struct.unpack_from("<5I", source, 197)
    sample_offsets = struct.unpack_from("<5I", source, 217)
    instruments = [source[offset:offset+554] for offset in instrument_offsets]
    sample_headers = [bytearray(source[offset:offset+80]) for offset in sample_offsets]
    sample_data = []
    for header in sample_headers:
        size = struct.unpack_from("<I", header, 48)[0]
        offset = struct.unpack_from("<I", header, 72)[0]
        if header[:4] != b"IMPS" or not 0 < size <= 1200 or offset+size > len(source):
            raise ValueError("Victory source sample is outside the bounded synth format")
        sample_data.append(source[offset:offset+size])

    # Sixteen 4/4 bars, four tracker rows per beat, 112 BPM. A rising
    # root/fifth/octave call opens over C, followed by a quieter answering
    # phrase. The final ii-V-I resolves to C before the fanfare repeats.
    roots = [48, 48, 53, 55, 57, 53, 50, 55,
             52, 53, 55, 55, 53, 50, 55, 48]
    lead = [
        [(0, 60), (3, 67), (6, 72), (8, 76), (12, 74)],
        [(0, 72), (6, 67), (8, 64), (12, 67)],
        [(0, 69), (4, 72), (8, 77), (12, 76)],
        [(0, 74), (6, 71), (8, 67), (12, 254)],
        [(0, 72), (4, 76), (8, 79), (12, 76)],
        [(0, 77), (6, 76), (8, 72), (12, 69)],
        [(0, 74), (4, 77), (8, 76), (12, 74)],
        [(0, 71), (6, 74), (8, 67), (12, 254)],
        [(0, 64), (4, 67), (8, 72), (12, 67)],
        [(0, 65), (4, 69), (8, 72), (12, 69)],
        [(0, 67), (4, 72), (8, 76), (12, 72)],
        [(0, 74), (6, 72), (8, 71), (12, 67)],
        [(0, 69), (8, 72), (12, 69)],
        [(0, 65), (8, 69), (12, 74)],
        [(0, 71), (4, 74), (8, 79), (12, 71)],
        [(0, 72), (8, 67), (12, 60)],
    ]
    patterns = []
    for phrase in range(4):
        rows = bytearray()
        for row in range(64):
            bar, beatrow = phrase*4+row//16, row % 16
            events = []
            for position, note in lead[bar]:
                if beatrow == position:
                    events.append((0, note, 1, 44 if bar < 4 else (34 if bar >= 12 else 39)))
            if beatrow % 4 == 0:
                # Quiet octave pulse keeps the closing tonic present without
                # a long silent gap; the two melodic channels retain decay.
                note = roots[bar] + (12 if beatrow == 12 else 0)
                events.append((1, note, 2, 34 if bar >= 12 else 39))
            if beatrow in (0, 8):
                events.append((2, 60, 3, 38 if bar >= 12 else 46))
            if beatrow in (4, 12):
                events.append((2, 60, 4, 23 if bar >= 12 else 29))
            if beatrow % 4 == 2:
                events.append((3, 60, 5, 14 if bar >= 12 else 19))
            for channel, note, sample, volume in events:
                if not (0 <= channel < 4 and (0 <= note < 120 or note == 254)
                        and 1 <= sample <= 5 and 0 <= volume <= 64):
                    raise ValueError("Victory event exceeds four-voice tracker bounds")
                rows.extend((0x81+channel, 7, note, sample, volume))
            rows.append(0)
        if len(rows) > 65535:
            raise ValueError("Victory packed pattern exceeds IT length field")
        patterns.append(struct.pack("<HHI", len(rows), 64, 0)+rows)

    header = bytearray(source[:192])
    header[4:30] = b"Office Champion".ljust(26, b"\0")
    header[51] = 112
    position = 192+5+5*4+5*4+4*4
    ins_offsets = [position+i*554 for i in range(5)]
    position += 5*554
    smp_offsets = [position+i*80 for i in range(5)]
    position += 5*80
    pat_offsets = []
    for pattern in patterns:
        pat_offsets.append(position)
        position += len(pattern)
    for header_sample, data in zip(sample_headers, sample_data):
        struct.pack_into("<I", header_sample, 72, position)
        position += len(data)
    if position >= 32768:
        raise ValueError("Victory IT exceeds its bounded 32 KiB source budget")
    result = (header+bytes((0, 1, 2, 3, 255))
              +struct.pack("<5I", *ins_offsets)+struct.pack("<5I", *smp_offsets)
              +struct.pack("<4I", *pat_offsets)+b"".join(instruments)
              +b"".join(sample_headers)+b"".join(patterns)+b"".join(sample_data))
    if len(result) != position:
        raise ValueError("Victory IT offsets do not match serialized data")
    path.write_bytes(result)
