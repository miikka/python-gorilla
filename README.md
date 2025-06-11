# python-gorilla

A Python implementation of the [Gorilla algorithm] for compressing floating point data.

[Gorilla algorithm]: https://www.vldb.org/pvldb/vol8/p1816-teller.pdf

On 2025-06-11, I ([Miikka Koskinen](https://miikka.me/)) gave a talk about the algorithm and showed the playground app in this repo.
[The slides](./slides.pdf) are available.

## Notes

- I used [bitstring](https://bitstring.readthedocs.io/en/stable/) library, but
  I think the code would have been cleaner by doing the bit twiddling with ints
  and implementing bit-aligned IO by hand.

## Playground

Under `webapp`, there's a simple web app that allows you to step through the encoding process.

> [!WARNING]
> The web app was generated using OpenAI's Codex tool and the code quality is YOLO.
> The actual algorithm was handcrafted though.

```bash
uv run python3 webapp/main.py
# go to http://localhost:5001/
```
