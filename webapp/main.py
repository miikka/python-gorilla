from fasthtml.common import *
import re
import python_gorilla

app, rt = fast_app(
    hdrs=(
        Link(
            rel="stylesheet",
            href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.colors.min.css",
        ),
    )
)


def compute_steps(values):
    pack = python_gorilla.bitstring.pack
    count_leading = python_gorilla.count_leading
    count_trailing = python_gorilla.count_trailing
    steps = []
    if not values:
        return steps
    prev_leading = 64
    prev_trailing = 0
    first = values[0]
    prev_bits = pack("float:64", first)
    stream = prev_bits.bin
    steps.append(
        {
            "index": 0,
            "current": first,
            "prev_bits": "",
            "current_bits": prev_bits.bin,
            "xor_bits": "",
            "operation": "first",
            "prev_leading_pre": None,
            "prev_trailing_pre": None,
            "current_leading": None,
            "current_trailing": None,
            "meaningful_bits": "",
            "inserted_bits": prev_bits.bin,
            "stream_bits": stream,
            "prev_leading_post": prev_leading,
            "prev_trailing_post": prev_trailing,
            "control": None,
        }
    )
    for i, val in enumerate(values[1:], start=1):
        prev_leading_pre = prev_leading
        prev_trailing_pre = prev_trailing
        curr_bits = pack("float:64", val)
        xor = curr_bits ^ prev_bits
        if xor.all(0):
            op = "identical (control 0)"
            control = "0"
            leading = None
            trailing = None
            meaningful = ""
            ins = "0"
        else:
            op0 = "1"
            leading = count_leading(xor)
            trailing = count_trailing(xor)
            if leading >= prev_leading_pre and trailing == prev_trailing_pre:
                op = "fits the previous meaningful bits (control 10)"
                meaningful = xor[prev_leading_pre : 64 - prev_trailing_pre].bin
                ins = op0 + "0" + meaningful
                control = "10"
            else:
                op = "new (control 11)"
                meaningful = xor[leading : 64 - trailing].bin
                cb = pack("uint:5", leading).bin
                mb = pack("uint:6", (64 - leading - trailing) - 1).bin
                ins = op0 + "1" + cb + mb + meaningful
                prev_leading = leading
                prev_trailing = trailing
                control = "11"
        stream += ins
        steps.append(
            {
                "index": i,
                "current": val,
                "prev_bits": prev_bits.bin,
                "current_bits": curr_bits.bin,
                "xor_bits": xor.bin,
                "operation": op,
                "prev_leading_pre": prev_leading_pre,
                "prev_trailing_pre": prev_trailing_pre,
                "current_leading": leading,
                "current_trailing": trailing,
                "meaningful_bits": meaningful,
                "inserted_bits": ins,
                "stream_bits": stream,
                "prev_leading_post": prev_leading,
                "prev_trailing_post": prev_trailing,
                "control": control,
            }
        )
        prev_bits = curr_bits
    return steps


def bitmark(content: str, **kwargs) -> Mark:
    return Mark(
        content,
        style="padding: 0; border-radius: 0;",
        **kwargs,
    )


def highlight_meaningful(bin_str: str, meaningful: str, lead: int) -> Code:
    return Code(
        bin_str[:lead],
        bitmark(meaningful, title="Meaningful bits"),
        bin_str[lead + len(meaningful) :],
    )


@rt("/")
def index(floats: str = "", step: int = 0):
    header = H1("Gorilla Encoding Playground")
    form = Form(
        Textarea(
            name="floats", rows=3, cols=60, placeholder="e.g. 1.0 2.0 3.0", value=floats
        ),
        Input(type="hidden", name="step", value="0"),
        Button("Start", type="submit"),
        method="get",
    )
    page = Div(header, form)
    if floats:
        items = [f for f in re.split(r"[\s,]+", floats.strip()) if f]
        try:
            values = [float(f) for f in items]
        except ValueError:
            page.append(Div(P("Invalid float list"), A("Back", href="/")))
            return page
        steps = compute_steps(values)
        total = len(steps) - 1
        idx = max(0, min(step, total))
        info = steps[idx]
        bit_keys = {
            "prev_bits",
            "current_bits",
            "xor_bits",
            "meaningful_bits",
            "inserted_bits",
            "stream_bits",
        }
        first_col_style = "width: 16ch; white-space: nowrap;"
        rows = []
        for key, label in [
            ("operation", "Operation"),
            ("current", "Current value"),
            ("prev_bits", "Previous bits"),
            ("current_bits", "Current bits"),
            ("xor_bits", "XOR bits"),
            ("prev_leading_pre", "Prev leading"),
            ("prev_trailing_pre", "Prev trailing"),
            ("current_leading", "Curr leading"),
            ("current_trailing", "Curr trailing"),
            ("meaningful_bits", "Meaningful bits"),
            ("inserted_bits", "Inserted bits"),
        ]:
            val = info.get(key)
            if val in (None, ""):
                continue
            if key == "xor_bits" and info.get("meaningful_bits"):
                bin_str = val
                lead = info.get("current_leading") or 0
                cell = highlight_meaningful(bin_str, info["meaningful_bits"], lead)
            else:
                cell = Code(val) if key in bit_keys else str(val)
            rows.append(Tr(Th(label, style=first_col_style), Td(cell)))
        table = Table(*rows)
        top_nav = Div(
            Form(
                Input(type="hidden", name="floats", value=floats),
                Input(type="hidden", name="step", value=str(idx - 1)),
                Button("Prev"),
                method="get",
            )
            if idx > 0
            else "",
            Form(
                Input(type="hidden", name="floats", value=floats),
                Input(type="hidden", name="step", value=str(idx + 1)),
                Button("Next"),
                method="get",
            )
            if idx < total
            else "",
            style="display:flex; gap:0.5em;",
        )
        header_nav = Div(
            header,
            top_nav,
            style="display:flex; align-items:center; justify-content:space-between;",
        )
        step_div = Div(table, id="step")

        preview_rows = [
            Tr(Th("Value"), Th("Binary representation"), Th("Inserted bits"))
        ]
        for i, f in enumerate(items):
            bin_str = steps[i]["current_bits"] if i == 0 else steps[i]["xor_bits"]
            m = steps[i]["meaningful_bits"]
            if m:
                if steps[i]["control"] == "10":
                    start = steps[i]["prev_leading_pre"] or 0
                else:
                    start = steps[i]["current_leading"] or 0
                bin_code = highlight_meaningful(bin_str, m, start)
            else:
                bin_code = Code(bin_str)
            ins = steps[i]["inserted_bits"]
            ctrl_raw = steps[i]["control"]
            if ctrl_raw is None:
                # initial step: show full inserted bits
                ins_code = Code(ins)
            else:
                ctrl = ctrl_raw or ""
                rest = ins[len(ctrl) :]
                ins_children = []
                # control (op) bits: default mark highlight
                if ctrl:
                    ins_children.append(
                        bitmark(ctrl, title="Control bits", cls="pico-background-jade-150")
                    )
                if ctrl == "11":
                    cb = rest[:5]
                    mb = rest[5:11]
                    meaningful = rest[11:]
                    ins_children.append(
                        bitmark(
                            cb,
                            cls="pico-background-pumpkin-150",
                            title=f"Leading zero count: {int(cb, 2)}",
                        )
                    )
                    ins_children.append(
                        bitmark(
                            mb,
                            cls="pico-background-violet-150",
                            title=f"Meaningful bit count: {int(mb, 2) + 1}",
                        )
                    )
                    if meaningful:
                        ins_children.append(
                            bitmark(
                                meaningful,
                                title="Meaningful bits",
                            )
                        )
                elif ctrl == "10":
                    # fits previous bits: rest is meaningful bits
                    if rest:
                        ins_children.append(
                            bitmark(
                                rest,
                                title="Meaningful bits",
                            )
                        )
                ins_code = Code(*ins_children)
            if i > idx:
                preview_rows.append(
                    Tr(
                        Td(Span(f)),
                        Td(bin_code, style="visibility:hidden"),
                        Td(ins_code, style="visibility:hidden"),
                    )
                )
                continue
            bin_cell = Strong(bin_code) if i == idx else bin_code
            ins_cell = Strong(ins_code) if i == idx else ins_code
            preview_rows.append(
                Tr(
                    Td(Strong(f) if i == idx else Span(f)),
                    Td(bin_cell),
                    Td(ins_cell),
                )
            )
        preview_table = Table(*preview_rows)

        nvalues = idx + 1
        total_bits = len(steps[idx]["stream_bits"])
        bits_per_value = total_bits / nvalues
        compression_ratio = 64 / bits_per_value
        stats_table = Table(
            Tr(Th("Bits per value"), Td(f"{bits_per_value:.2f}")),
            Tr(Th("Compression ratio"), Td(f"{compression_ratio:.2f}")),
        )

        page = Div(header_nav, preview_table, stats_table, step_div)
    return Title("Gorilla Encoding Playground"), page


serve()
