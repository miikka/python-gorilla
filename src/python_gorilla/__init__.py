import bitstring
from bitstring import BitStream, Bits


def count_leading(x: Bits) -> int:
    """Returns the number of leading zeros, up to 31, in the input."""
    if pos := x.find(Bits("0b1"), end=31):
        return pos[0]
    return 31


def count_trailing(x: Bits) -> int:
    if pos := x.rfind(Bits("0b1")):
        return len(x) - pos[0] - 1
    assert False, "There must be at least one non-zero bit in the xor result"


def encode(input: list[float]) -> Bits:
    stream = BitStream()

    if len(input) == 0:
        return stream

    # Store the first value as-is
    prev_bits = bitstring.pack("float:64", input[0])
    stream.insert(prev_bits)

    prev_leading = 64
    prev_trailing = 0

    for current_float in input[1:]:
        current_bits = bitstring.pack("float:64", current_float)

        xor_result = current_bits ^ prev_bits

        if xor_result.all(0):
            stream.insert(Bits("0b0"))
        else:
            stream.insert(Bits("0b1"))

            current_leading = count_leading(xor_result)
            current_trailing = count_trailing(xor_result)

            if current_leading >= prev_leading and current_trailing == prev_trailing:
                stream.insert(Bits("0b0"))
                stream.insert(xor_result[prev_leading : (64 - prev_trailing)])
            else:
                stream.insert(Bits("0b1"))
                stream.insert(bitstring.pack("uint:5", current_leading))
                meaningful_count = 64 - current_leading - current_trailing
                assert meaningful_count > 0, (
                    f"meaningful count must be non-zero, got {meaningful_count}"
                )

                # meaningful_count is biased by one so that we can fit 1-64 in 6 bits
                stream.insert(bitstring.pack("uint:6", meaningful_count - 1))
                stream.insert(xor_result[current_leading : (64 - current_trailing)])
                prev_leading = current_leading
                prev_trailing = current_trailing

        prev_bits = current_bits

    return stream


def decode(input: Bits) -> list[float]:
    if len(input) == 0:
        return []

    result = []
    stream = BitStream(input)

    prev_bits = stream.read("bits:64")
    result.append(prev_bits.float)

    prev_leading = 0
    prev_trailing = 0

    while stream.pos < stream.length:
        if stream.read("bool") is False:
            current_bits = prev_bits
        elif stream.read("bool") is False:
            meaningful_count = 64 - prev_leading - prev_trailing
            meaningful_bits = stream.read(meaningful_count)

            xor_result = Bits(prev_leading) + meaningful_bits + Bits(prev_trailing)
            current_bits = prev_bits ^ xor_result
        else:
            current_leading = stream.read("uint:5")
            meaningful_count = stream.read("uint:6") + 1
            meaningful_bits = stream.read(meaningful_count)

            current_trailing = 64 - current_leading - meaningful_count
            xor_result = (
                Bits(current_leading) + meaningful_bits + Bits(current_trailing)
            )
            current_bits = prev_bits ^ xor_result

            prev_leading = current_leading
            prev_trailing = current_trailing

        result.append(current_bits.float)
        prev_bits = current_bits

    return result
