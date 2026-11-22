"""Download public-domain children's books from Project Gutenberg and save them
as Read with Puck story files in ../stories.

Run by .github/workflows/import-books.yml (Actions tab -> Import books -> Run workflow).
Every book here was published before 1929 and is public domain in the US.
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "stories")

BOOKS = [
    {"id": 14642, "slug": "mcguffey", "kind": "mcguffey", "title": "McGuffey Primer"},
    {"id": 14838, "slug": "peter-rabbit", "kind": "single", "title": "The Tale of Peter Rabbit"},
    {"id": 61852, "slug": "kittens-and-cats", "kind": "kittens", "title": "Kittens and Cats"},
    {"id": 67098, "slug": "pooh-1", "kind": "chapters", "title": "Winnie-the-Pooh"},
    {"id": 73011, "slug": "pooh-2", "kind": "chapters", "title": "The House at Pooh Corner"},
]


def mirror_dir(book_id):
    s = str(book_id)
    return "/".join(s[:-1]) + "/" + s if len(s) > 1 else "0/" + s


def fetch(book_id):
    d = mirror_dir(book_id)
    names = [f"{book_id}-0.txt", f"{book_id}.txt", f"{book_id}-8.txt"]
    bases = [
        "https://mirror.csclub.uwaterloo.ca/gutenberg/",
        "https://gutenberg.readingroo.ms/",
        "http://gutenberg.pglaf.org/",
        "http://aleph.gutenberg.org/",
        "https://www.gutenberg.org/files/" + str(book_id) + "/",
    ]
    urls = []
    for b in bases:
        for n in names:
            urls.append(b + n if b.endswith(f"/{book_id}/") else b + d + "/" + n)
    urls += [
        f"https://www.gutenberg.org/cache/epub/{book_id}/pg{book_id}.txt",
        f"http://aleph.gutenberg.org/cache/epub/{book_id}/pg{book_id}.txt",
    ]
    for url in urls:
        for attempt in range(2):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (read-with-puck importer)"})
                with urllib.request.urlopen(req, timeout=60) as r:
                    data = r.read()
                for enc in ("utf-8-sig", "latin-1"):
                    try:
                        text = data.decode(enc)
                        break
                    except UnicodeDecodeError:
                        continue
                if "START OF" in text:
                    print(f"  got {book_id} from {url}")
                    return text
                break
            except urllib.error.HTTPError as e:
                print(f"  {url}: {e}")
                if e.code == 404:
                    break
                time.sleep(2)
            except Exception as e:
                print(f"  {url}: {e}")
                time.sleep(2)
    raise SystemExit(f"Could not download book {book_id}")


def body_of(text):
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    m = re.search(r"\*\*\*\s*START OF[^\n]*\*\*\*", text)
    if m:
        text = text[m.end():]
    m = re.search(r"\*\*\*\s*END OF[^\n]*\*\*\*", text)
    if m:
        text = text[:m.start()]
    m = re.search(r"\n\s*End of (the )?Project Gutenberg", text, re.I)
    if m:
        text = text[:m.start()]
    # illustrations, transcriber notes, italics/bold markers
    text = re.sub(r"\[Illustration[^\]]*\]", "", text, flags=re.S)
    text = re.sub(r"\[Transcriber[^\]]*\]", "", text, flags=re.S | re.I)
    text = re.sub(r"\[(Pg|Page)?\s*[ivxlc\d]+\]", "", text, flags=re.I)
    text = re.sub(r"\{[ivxlc\d]+\}", "", text, flags=re.I)
    text = text.replace("_", "").replace("=", "")
    text = re.sub(r"^\s*Produced by.*?\n\n", "", text, flags=re.S | re.I)
    return text


def paragraphs(text):
    return [p for p in re.split(r"\n\s*\n", text) if p.strip()]


def tidy_para(p, keep_lines=False):
    lines = [l.rstrip() for l in p.split("\n") if l.strip()]
    if not lines:
        return ""
    indented = sum(1 for l in lines if re.match(r"^\s{2,}\S", l))
    if keep_lines or (len(lines) > 1 and indented >= len(lines) / 2):
        return "\n".join(re.sub(r"\s+", " ", l.strip()) for l in lines)  # poem / list: keep lines
    return re.sub(r"\s+", " ", " ".join(l.strip() for l in lines))  # prose: unwrap


SMALL = {"a", "an", "and", "the", "to", "of", "in", "on", "at", "for", "but", "or", "is", "by", "with", "as"}


def title_case(s):
    s = re.sub(r"\s+", " ", s.strip().rstrip("."))
    if s != s.upper():
        return s
    out = []
    for i, w in enumerate(s.lower().split(" ")):
        parts = w.split("-")
        parts = [pp if (j > 0 and pp in SMALL) else (pp[:1].upper() + pp[1:]) for j, pp in enumerate(parts)]
        w2 = "-".join(parts)
        if i > 0 and w in SMALL:
            w2 = w
        out.append(w2)
    return " ".join(out)


def roman(s):
    vals = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}
    total, prev = 0, 0
    for ch in reversed(s.upper()):
        v = vals.get(ch, 0)
        total += -v if v < prev else v
        prev = max(prev, v)
    return total


def write_story(name, title, pages):
    pages = [p for p in pages if p.strip()]
    if not pages:
        return None
    path = os.path.join(OUT, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(title.strip() + "\n\n" + "\n\n".join(pages).strip() + "\n")
    print(f"  wrote {name} ({sum(len(p.split()) for p in pages)} words)")
    return name


def do_single(book, body):
    paras = [tidy_para(p) for p in paragraphs(body)]
    paras = [p for p in paras if not re.search(r"(Printed|Copyright|Published|Produced|All rights|London|New York)", p)]
    # drop front matter up to the first real sentence of the story
    start = next((i for i, p in enumerate(paras) if len(p.split()) > 8), 0)
    paras = [p for p in paras[start:] if p and p.strip().upper() != "THE END"]
    return [write_story(f"{book['slug']}.txt", book["title"], paras)]


def do_chapters(book, body):
    lines = body.split("\n")
    heads = [i for i, l in enumerate(lines) if re.match(r"^\s*CHAPTER\s+[IVXL]+\.?\s*$", l)]
    if not heads:
        raise SystemExit(f"No chapters found in {book['title']}")
    names = []
    for n, h in enumerate(heads):
        end = heads[n + 1] if n + 1 < len(heads) else len(lines)
        chunk = "\n".join(lines[h + 1:end])
        chunk = re.split(r"\n\s*THE END\s*\n", chunk)[0]
        paras = paragraphs(chunk)
        # title = first paragraph(s) starting with "IN WHICH"
        title_bits = []
        while paras and (not title_bits or len(" ".join(title_bits).split()) < 4) and len(paras[0].split()) < 30:
            title_bits.append(paras.pop(0))
            if re.match(r"\s*IN WHICH", " ".join(title_bits), re.I):
                break
        t = re.sub(r"^\s*IN WHICH\s*", "", re.sub(r"\s+", " ", " ".join(title_bits)), flags=re.I)
        t = title_case(t)
        t = t[:1].upper() + t[1:]
        t = re.sub(r"\bls\b", "Is", t).replace("Organdized", "Organized")
        num = roman(re.search(r"CHAPTER\s+([IVXL]+)", lines[h]).group(1))
        pages = [tidy_para(p) for p in paras]
        pages = [p for p in pages if p and not re.match(r"^(THE HOUSE AT POOH CORNER|WINNIE-THE-POOH)$", p.strip())]
        names.append(write_story(f"{book['slug']}-{num:02d}.txt", f"{book['title']} {num}: {t}", pages))
    return names


def do_mcguffey(book, body):
    lines = body.split("\n")
    heads = [i for i, l in enumerate(lines) if re.match(r"^\s*LESSON\s+([IVXL]+|\d+)\b", l, re.I)]
    lessons = []
    alpha = [i for i, l in enumerate(lines) if "ALPHABET" in l and (not heads or i < heads[0])]
    if alpha:
        rows = [l.strip() for l in lines[alpha[0]:heads[0] if heads else len(lines)] if re.fullmatch(r"([A-Za-z]\s+)*[A-Za-z]", l.strip())]
        if rows:
            lessons.append((0, "The Alphabet\n" + "\n".join(rows)))
    for n, h in enumerate(heads):
        end = heads[n + 1] if n + 1 < len(heads) else len(lines)
        tok = re.search(r"LESSON\s+([IVXL]+|\d+)", lines[h], re.I).group(1)
        num = int(tok) if tok.isdigit() else roman(tok)
        kept = []
        for l in lines[h + 1:end]:
            s = l.strip()
            if not s:
                continue
            if re.search(r"(ECLECTIC SERIES|McGUFFEY'?S PRIMER)", s, re.I) and len(s) < 40:
                continue  # running page headers
            if re.fullmatch(r"[\divxlc.()\s]+", s, re.I):
                continue  # page numbers
            if re.match(r"^(Script|Slate|\(Script|\[Script)", s, re.I):
                continue
            kept.append(re.sub(r"\s{2,}", "   ", s))
        review = " (review)" if re.search(r"REVIEW", lines[h], re.I) else ""
        if kept:
            lessons.append((num, f"Lesson {num}{review}\n" + "\n".join(kept)))
    if not lessons:
        raise SystemExit("No lessons found in McGuffey")
    names = []
    group = 4
    for i in range(0, len(lessons), group):
        part = lessons[i:i + group]
        a, b = max(1, part[0][0]), part[-1][0]
        names.append(write_story(f"{book['slug']}-{a:02d}.txt", f"{book['title']}, Lessons {a} to {b}", [p[1] for p in part]))
    return names


def do_kittens(book, body):
    lines = body.split("\n")
    # stories start after the last "KITTENS AND CATS" half-title line
    idx = max((i for i, l in enumerate(lines) if l.strip().upper() == "KITTENS AND CATS"), default=0)
    lines = lines[idx + 1:]
    stop = next((i for i, l in enumerate(lines) if re.search(r"WORD TO THE TEACHER|^\s*SUGGESTIONS\s*$", l, re.I)), len(lines))
    lines = lines[:stop]
    tales, cur_title, cur = [], None, []

    def is_title(s):
        return bool(re.search(r"[A-Z]", s)) and s == s.upper() and len(s) < 45 and not re.search(r"[a-z]", s) and len(s.split()) <= 7

    buf = []
    for l in lines + [""]:
        if l.strip():
            buf.append(l)
            continue
        if not buf:
            continue
        p = "\n".join(buf)
        buf = []
        s = re.sub(r"\s+", " ", p.strip())
        if is_title(s) and s.upper() != "THE END":
            if cur_title and cur:
                tales.append((cur_title, cur))
            cur_title, cur = title_case(s), []
        elif cur_title:
            cur.append(tidy_para(p, keep_lines=True))
    if cur_title and cur:
        tales.append((cur_title, cur))
    if not tales:
        raise SystemExit("No tales found in Kittens and Cats")
    pages = [t + "\n" + "\n".join(body) for t, body in tales]
    names = []
    per = 12
    for k, i in enumerate(range(0, len(pages), per), start=1):
        names.append(write_story(f"{book['slug']}-{k}.txt", f"{book['title']}, Part {k}", pages[i:i + per]))
    return names


def main():
    os.makedirs(OUT, exist_ok=True)
    only = set(sys.argv[1:])
    for book in BOOKS:
        if only and book["slug"] not in only:
            continue
        print(f"{book['title']}:")
        for f in os.listdir(OUT):
            if f.startswith(book["slug"] + "-") or f == book["slug"] + ".txt":
                os.remove(os.path.join(OUT, f))
        body = body_of(fetch(book["id"]))
        {"single": do_single, "chapters": do_chapters, "mcguffey": do_mcguffey, "kittens": do_kittens}[book["kind"]](book, body)
    names = sorted(f for f in os.listdir(OUT) if f.endswith(".txt"))
    with open(os.path.join(OUT, "index.json"), "w") as f:
        json.dump(names, f, indent=0)
    print(f"{len(names)} story files")


if __name__ == "__main__":
    main()
