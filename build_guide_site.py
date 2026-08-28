#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
311_사용자조사_세팅가이드_v1.00.md -> 연속 스크롤 문서 사이트 생성기 (v2, 배포용 패키지)
- 좌측 목차는 스크롤 위치에 따라 자동으로 활성 항목이 바뀜(scrollspy)
- 장표(페이지 번호, 낱장 전환) 요소 제거 — 이어지는 하나의 문서로 구성
- 타이포그래피/레이아웃을 크게 키워 가독성 강화 (Apple 스타일)
- 단순 2열 매핑표는 표 대신 큰 목록형으로 표시
- v2.70부터는 md 파일 자체가 최신 콘텐츠의 원본(source of truth)이라, 텍스트/제목을
  바꿔치기하던 override 딕셔너리는 대부분 제거했음. 남은 override는 순수 "레이아웃 로직"
  (페이지 번호 기반 컴포넌트 선택, 라벨 분리 규칙과 충돌하는 극소수 목차 라벨 등)뿐.
- 이 폴더(330_배포용)는 md·이미지·스크립트·결과 html이 전부 한 폴더에 있는 독립 배포판.
  이 폴더째로 복사/다운로드해서 열어도 그대로 동작함(경로가 전부 이 폴더 기준 상대경로).
"""
import re
import html
import json
import os

# 이 스크립트가 놓인 폴더 기준 상대경로 — md/이미지/결과 html이 전부 같은 폴더에 있음.
# 폴더째로 옮기거나 다른 사람에게 그대로 전달해도 동일하게 동작함.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE_DIR, "311_사용자조사_세팅가이드_v1.00.md")
OUT = os.path.join(BASE_DIR, "index.html")

with open(SRC, encoding="utf-8") as f:
    raw = f.read()

# ---------------------------------------------------------------
# 1. PAGE_SCHEMA v0.30 파싱
#    ````[header][masgTitle]```` / [pageTitle] / [masgSubText] / [cont] / ````[masgType][pageNumber]````
# ---------------------------------------------------------------
PAGE_RE = re.compile(
    r"````\n\[header\](?P<header>.*?)\n\[masgTitle\](?P<masgTitle>.*?)\n````\n\n"
    r"\[pageTitle\]\n#(?P<pageTitle>.*?)\n\n"
    r"\[masgSubText\](?P<masgSubText>.*?)\n\[cont\]\n(?P<cont>.*?)\n"
    r"````\n\[masgType\](?P<masgType>.*?)\n\[pageNumber\](?P<pageNumber>.*?)\n````",
    re.DOTALL,
)

pages = []
for m in PAGE_RE.finditer(raw):
    pages.append({
        "header": m.group("header").strip(),
        "masgTitle": m.group("masgTitle").strip(),
        "pageTitle": m.group("pageTitle").strip(),
        "masgSubText": m.group("masgSubText").strip(),
        "cont": m.group("cont").strip("\n"),
        "masgType": m.group("masgType").strip(),
        "pageNumber": m.group("pageNumber").strip(),
    })
print(f"파싱된 페이지 수: {len(pages)}")

# 목차(사이드바) 하위 항목 라벨 — "장비 세팅" 그룹 하위 항목(09~14)은 라벨 분리 규칙이
# em대시/hyphen 뒤쪽을 취하는데, 원하는 라벨 자체에 "-"가 들어가 있어 pageTitle만으로는
# 정확히 표현할 수 없다. 이 6개만 예외적으로 코드에 직접 지정한다.
NAV_LABEL_OVERRIDES = {
    "10": "조사실 - 영상·오디오 연결",
    "11": "조사실 - 인물 카메라",
    "12": "조사실 - 시료 카메라",
    "13": "조사실 - 무선 마이크",
    "14": "관찰실",
    "15": "장비 체크리스트",
}

# 회색 박스 보충설명과 같은 레벨(16px)로 낮추는 소제목 — 원문 강조 표기 그대로 매칭
NOTE_LEVEL_HEADINGS = {
    "**포트 매핑 (= 4층 TV 4분할 위치)**",
    "**TV 4분할 레이아웃**",
    "**컨택가이드 예시**",
    "**확정 문자 예시**",
    "**리마인딩 문자 예시**",
    "**사례비 안내 문자 예시**",
    "**사내 공지 문자 예시**",
    "**개인정보 수집·이용 및 제3자 제공 동의서 양식**",
    "**비밀유지서약서 양식**",
    "**사례비 지급을 위한 개인정보 활용 동의서 양식**",
    "**개인정보 수집·이용 동의서 양식**",
    "**통역사 비밀유지서약서 양식**",
    "**통역사 개인정보 취급 확인서 양식**",
}

# 참여자 컨택 프로세스 — 스텝 하단 부가/조건부 설명 불렛을 서브 리스트 레벨로 낮추는 페이지
SUB_BULLET_PAGES = {"26", "27"}

PAGETITLE_NUM_RE = re.compile(r"^(\d+(?:\.\d+)*)\.\s*(.*)$")


def split_number_prefix(pageTitle):
    m = PAGETITLE_NUM_RE.match(pageTitle.strip())
    if m:
        return m.group(1), m.group(2).strip()
    return "", pageTitle.strip()


def group_key_of(num_prefix):
    parts = num_prefix.split(".")
    return ".".join(parts[:2]) if len(parts) >= 2 else num_prefix


LEAF_SPLIT_RE = re.compile(r"\s*[—–-]\s*")


def short_leaf_label(remainder):
    parts = LEAF_SPLIT_RE.split(remainder, maxsplit=1)
    return parts[0].strip()


def short_leaf_label_suffix(remainder):
    """그룹 하위 항목 라벨 — 대시가 있으면 뒤쪽(구체적 구분자)을, 없으면 전체를 사용."""
    parts = LEAF_SPLIT_RE.split(remainder, maxsplit=1)
    return parts[-1].strip()


# ---------------------------------------------------------------
# 2. 목차(## 목차) 섹션에서 Part -> Group -> Item 구조 추출
# ---------------------------------------------------------------
toc_m = re.search(r"## 목차\n(.*?)\n---", raw, re.DOTALL)
toc_text = toc_m.group(1) if toc_m else ""

pages_by_title = {p["pageTitle"]: p for p in pages}

WIKILINK_RE = re.compile(r"\[\[#(.*?)\]\]")
BOLD_HEADER_RE = re.compile(r"^\*\*(.+?)\*\*$")


def resolve_wikilink_target(inner):
    # "#pageTitle" 또는 "#pageTitle|별칭" 형태
    target = inner.split("|")[0].strip()
    return target


toc_parts = []  # [{header, entries:[{label, refs:[pageTitle,...]}]}]
cur_part = None
cur_entry = None
for line in toc_text.split("\n"):
    if not line.strip():
        continue
    bm = BOLD_HEADER_RE.match(line.strip())
    if bm:
        cur_part = {"header": bm.group(1).strip(), "entries": []}
        toc_parts.append(cur_part)
        cur_entry = None
        continue
    if cur_part is None:
        continue
    indent = len(line) - len(line.lstrip(" "))
    stripped = line.strip()
    if not stripped.startswith("-"):
        continue
    body = stripped[1:].strip()
    wm = WIKILINK_RE.search(body)
    ref = resolve_wikilink_target(wm.group(1)) if wm else None
    if indent == 0:
        if ref:
            cur_entry = {"label": None, "refs": [ref]}
            cur_part["entries"].append(cur_entry)
        else:
            label = re.sub(r"^\d+(?:\.\d+)*\.\s*", "", body).strip()
            cur_entry = {"label": label, "refs": []}
            cur_part["entries"].append(cur_entry)
    else:
        if ref and cur_entry is not None:
            cur_entry["refs"].append(ref)

parts = []
DIVIDER_LABEL_LINE_RE = re.compile(r"^(?:\d+\.|-)\s+(.*)$")


def parse_divider_group_labels(masgTitle):
    """디바이더(강조형) 페이지의 masgTitle에 있는 'N. 텍스트' 또는 '- 텍스트' 번호/불릿 목록에서
    각 그룹의 정식 라벨을 순서대로 뽑아낸다. ('**Appendix**' 같은 굵게 표시된 안내 줄은 건너뜀)"""
    labels = []
    for line in masgTitle.split("\n"):
        line = line.strip()
        if not line:
            continue
        m = DIVIDER_LABEL_LINE_RE.match(line)
        if m:
            labels.append(m.group(1).strip())
    return labels


for tp in toc_parts:
    entries = tp["entries"]
    divider = None
    groups = []
    for e in entries:
        target_pages = [pages_by_title[r] for r in e["refs"] if r in pages_by_title]
        if not target_pages:
            continue
        if (
            divider is None
            and len(target_pages) == 1
            and target_pages[0]["masgType"] == "강조형"
            and "(간지)" in target_pages[0]["pageTitle"]
        ):
            divider = target_pages[0]
            continue
        groups.append({"label": e["label"], "items": target_pages})

    # 그룹 라벨의 정본은 디바이더 페이지 masgTitle의 번호/불릿 목록(순서대로 대응).
    # 디바이더가 없거나 목록이 없으면(예: V장) 단일 항목 그룹은 그 페이지 자신의 masgTitle로 대체.
    divider_labels = parse_divider_group_labels(divider["masgTitle"]) if divider else []
    if divider_labels and len(divider_labels) == len(groups):
        for g, lbl in zip(groups, divider_labels):
            g["label"] = lbl
    else:
        for g in groups:
            if len(g["items"]) == 1:
                _, g["label"] = split_number_prefix(g["items"][0]["masgTitle"])

    parts.append({"header": tp["header"], "divider": divider, "groups": groups})


def pagetitle_kicker(pageTitle):
    num, remainder = split_number_prefix(pageTitle)
    return num, remainder


def split_header(header):
    m = re.match(r"^([IVX]+)\.\s*(.*)$", header.strip())
    if m:
        return m.group(1), m.group(2).strip()
    return "", header.strip()


# ---------------------------------------------------------------
# 3. 본문(cont) 렌더러
# ---------------------------------------------------------------
IMG_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
CODE_RE = re.compile(r"`([^`]+)`")


def img_tag(alt, src):
    src = src.split("/")[-1]
    alt_esc = html.escape(alt)
    return f'<figure class="cont-fig"><img src="assets/{src}" alt="{alt_esc}" loading="lazy"></figure>'


def inline(text, strip_bold=False):
    if text is None:
        return ""
    out = IMG_RE.sub(lambda m: img_tag(m.group(1), m.group(2)), text)
    if strip_bold:
        out = out.replace("**", "")
    else:
        out = BOLD_RE.sub(r"<strong>\1</strong>", out)
        out = out.replace("**", "")
    out = CODE_RE.sub(r"<code>\1</code>", out)
    return out


CONFIRM_RE = re.compile(r"^\[확인\s*필요[:：]?\s*(.*)\]$")

# 사이트에서는 노출하지 않기로 한 "[확인 필요: ...]" 참조 노트 (원본 md는 그대로 둠)
SUPPRESSED_CONFIRM_NOTES = {
    "위 포트 매핑은 UT 기준(탑뷰 존재)입니다. FGI Case 포트 매핑 표를 아래 내용으로 추가해주세요 — 1번 참여자그룹 / 2번 참여자그룹 / 3번 전경 / 4번 PC (HTML 가이드 사이트에는 UT Case 옆에 이미 반영되어 있음, 원문에만 반영 필요)",
    "FGI Case TV 4분할 레이아웃 표를 아래 내용으로 추가해주세요 — 1번 참여자그룹 / 2번 참여자그룹 / 3번 전경 / 4번 PC (HTML 가이드 사이트에는 UT Case 옆에 이미 반영되어 있음, 원문에만 반영 필요)",
}


def render_confirm(line):
    m = CONFIRM_RE.match(line.strip())
    body = m.group(1) if m else line.strip("[]")
    if body in SUPPRESSED_CONFIRM_NOTES:
        return ""
    return f'<div class="callout callout-warn"><i>확인 필요</i><span>{inline(body)}</span></div>'


def render_cont(cont: str, quickfind_mode=False, col_widths=None, demote_bullets=False) -> str:
    blocks = render_cont_blocks(cont, quickfind_mode=quickfind_mode, col_widths=col_widths, demote_bullets=demote_bullets)
    return "\n".join(wrap_example_boxes(wrap_note_asides(blocks)))


H4_HASH_RE = re.compile(r"^-\s*#{2,4}\s+")


def render_cont_blocks(cont: str, quickfind_mode=False, col_widths=None, step_style="stepper", demote_bullets=False) -> list:
    lines = [l for l in cont.split("\n") if not re.match(r"^\s*%%.*%%\s*$", l)]
    out = []
    i = 0
    n = len(lines)

    def is_blank(s):
        return s.strip() == ""

    while i < n:
        line = lines[i]
        stripped = line.strip()

        if is_blank(line):
            i += 1
            continue

        if stripped.startswith("```"):
            i += 1
            buf = []
            while i < n and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1
            code = html.escape("\n".join(buf))
            out.append(f'<pre class="cont-code"><code>{code}</code></pre>')
            continue

        if stripped.startswith(">"):
            buf = []
            while i < n and lines[i].strip().startswith(">"):
                buf.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            title = "note"
            body_lines = buf
            m = re.match(r"^\[!(\w+)\]\s*(.*)$", buf[0]) if buf else None
            if m:
                title = m.group(2) or m.group(1)
                body_lines = buf[1:]
            body = " ".join(b for b in body_lines if b.strip())
            out.append(
                f'<div class="callout callout-note"><i>{inline(title)}</i><span>{inline(body)}</span></div>'
            )
            continue

        if stripped.startswith("[확인 필요"):
            confirm_html = render_confirm(stripped)
            if confirm_html:
                out.append(confirm_html)
            i += 1
            continue

        if stripped.startswith("!["):
            out.append(f'<div class="cont-img-solo">{inline(stripped)}</div>')
            i += 1
            continue

        if stripped.startswith("|"):
            table_lines = []
            while i < n:
                s = lines[i].strip()
                if s.startswith("|") or s.startswith("!["):
                    table_lines.append(s)
                    i += 1
                else:
                    break
            out.append(render_table(table_lines, quickfind_mode=quickfind_mode, col_widths=col_widths))
            continue

        if re.match(r"^-\s*\[\s?\]\s+", stripped):
            items = []
            while i < n and re.match(r"^-\s*\[\s?\]\s+", lines[i].strip()):
                text = re.sub(r"^-\s*\[\s?\]\s+", "", lines[i].strip())
                check_icon = (
                    '<span class="box" aria-hidden="true">'
                    '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" '
                    'stroke-width="3" stroke-linecap="round" stroke-linejoin="round">'
                    '<polyline points="20 6 9 17 4 12"></polyline></svg></span>'
                )
                items.append(f'<li class="check">{check_icon}{inline(text, strip_bold=True)}</li>')
                i += 1
            out.append(f'<ul class="cont-checklist">{"".join(items)}</ul>')
            continue

        if H4_HASH_RE.match(stripped):
            text = H4_HASH_RE.sub("", stripped)
            out.append(f"<h4>{inline(text, strip_bold=True)}</h4>")
            i += 1
            continue

        if stripped.startswith("**") and not re.match(r"^-\s", stripped):
            h4_text = inline(stripped, strip_bold=True)
            cls = ' class="h4-note"' if stripped in NOTE_LEVEL_HEADINGS else ""
            out.append(f"<h4{cls}>{h4_text}</h4>")
            i += 1
            continue

        if re.match(r"^\d+\.\s+", stripped):
            items_html = []
            step_idx = 0
            while True:
                # 스텝 사이 빈 줄은 허용 — 다음 비어있지 않은 줄이 번호가 아니면 그때 목록 종료
                while i < n and is_blank(lines[i]):
                    i += 1
                if i >= n or not re.match(r"^\d+\.\s+", lines[i].strip()):
                    break
                step_idx += 1
                first = re.sub(r"^\d+\.\s+", "", lines[i].strip())
                text_parts = [f'<span class="step-main">{inline(first, strip_bold=True)}</span>']
                img_parts = []
                i += 1
                while i < n:
                    cur = lines[i]
                    if is_blank(cur):
                        break
                    indent = len(cur) - len(cur.lstrip())
                    cs = cur.strip()
                    if indent == 0 and not (cs.startswith("→") or cs.startswith("-")):
                        break
                    if re.match(r"^\d+\.\s+", cs):
                        break
                    if cs.startswith("- "):
                        sub_items = []
                        while i < n and lines[i].strip().startswith("- "):
                            sub_items.append(f"<li>{inline(lines[i].strip()[2:], strip_bold=True)}</li>")
                            i += 1
                        text_parts.append(f'<ul class="sub">{"".join(sub_items)}</ul>')
                        continue
                    elif cs.startswith("!["):
                        img_parts.append(inline(cs))
                        i += 1
                    else:
                        text_parts.append(f'<span class="step-note">{inline(cs, strip_bold=True)}</span>')
                        i += 1
                # 번호 -> 구분선 -> 텍스트 -> 이미지(항상 맨 아래) 순으로 고정
                img_html = "".join(img_parts)
                if step_style in ("bullet", "numbered"):
                    desc_html = "<br>".join(text_parts[1:])
                    desc_block = f'<div class="bullet-desc">{desc_html}</div>' if desc_html else ""
                    marker = f'<span class="num-marker">{step_idx}.</span>' if step_style == "numbered" else ""
                    items_html.append(f"<li>{marker}{text_parts[0]}{desc_block}{img_html}</li>")
                else:
                    text_html = "<br>".join(text_parts)
                    items_html.append(
                        f'<li><span class="step-num">{step_idx}</span><div class="step-rule"></div>'
                        f'<div class="step-text">{text_html}</div>{img_html}</li>'
                    )
            if step_style == "bullet":
                out.append(f'<ul class="cont-bullets">{"".join(items_html)}</ul>')
            elif step_style == "numbered":
                out.append(f'<ul class="cont-bullets cont-numbered">{"".join(items_html)}</ul>')
            else:
                out.append(f'<ol class="cont-steps">{"".join(items_html)}</ol>')
            continue

        if stripped.startswith("- "):
            items = []
            while i < n and lines[i].strip().startswith("- ") and not re.match(r"^-\s*\[\s?\]\s+", lines[i].strip()) and not re.match(r"^-\s*#{2,4}\s+", lines[i].strip()):
                items.append(f"<li>{inline(lines[i].strip()[2:])}</li>")
                i += 1
            list_cls = "sub" if demote_bullets else "cont-list"
            out.append(f'<ul class="{list_cls}">{"".join(items)}</ul>')
            continue

        buf = [stripped]
        i += 1
        while i < n and not is_blank(lines[i]) and not re.match(
            r"^(```|>|\||!\[|-\s|\d+\.\s|\[확인 필요|\*\*)", lines[i].strip()
        ):
            buf.append(lines[i].strip())
            i += 1
        line_htmls = []
        for b in buf:
            is_footnote = b.startswith("※") or (b.startswith("*") and not b.startswith("**"))
            line_html = inline(b)
            line_htmls.append(f'<span class="footnote">{line_html}</span>' if is_footnote else line_html)
        out.append(f"<p>{'<br>'.join(line_htmls)}</p>")

    return out


def linkify_cell_as_jump(cell_text, page_ref_text):
    """첫 칸(cell_text)을 page_ref_text에서 뽑아낸 페이지로 이동하는 링크로 감싼다."""
    m = PAGE_JUMP_RE.search(page_ref_text)
    inner = inline(cell_text)
    if not m:
        return inner
    return f'<a class="jump-link" href="#p{m.group(1)}">{inner}</a>'


PAGE_JUMP_RE = re.compile(r"(\d+)")
QUAD_TERM_RE = re.compile(r"^(\d)번$")


def render_table(table_lines, quickfind_mode=False, col_widths=None):
    header_cells = None
    body_entries = []
    for tl in table_lines:
        if tl.startswith("!["):
            body_entries.append(("img", inline(tl)))
            continue
        if re.match(r"^\|[\s:\-|]+\|$", tl):
            continue
        cells = [c.strip() for c in tl.strip("|").split("|")]
        if header_cells is None:
            header_cells = cells
        else:
            body_entries.append(("row", cells))

    ncol = len(header_cells) if header_cells else 0
    has_img = any(k == "img" for k, _ in body_entries)
    row_count = sum(1 for k, _ in body_entries if k == "row")

    # 빠른 찾기 표: 마지막(페이지) 열은 삭제하고, 그 정보로 첫 열을 바로가기 링크화
    if quickfind_mode:
        new_header = ["구분"] + header_cells[1:-1]
        thead = "<tr>" + "".join(f"<th>{inline(c)}</th>" for c in new_header) + "</tr>"
        tbody_parts = []
        for kind, val in body_entries:
            if kind != "row":
                continue
            first_html = linkify_cell_as_jump(val[0], val[-1])
            mid_html = "".join(f"<td>{inline(c)}</td>" for c in val[1:-1])
            tbody_parts.append(f"<tr><td>{first_html}</td>{mid_html}</tr>")
        return (
            '<div class="cont-table-wrap"><table class="cont-table">'
            f"<thead>{thead}</thead><tbody>{''.join(tbody_parts)}</tbody></table></div>"
        )

    # TV 4분할류: '1번~4번' -> 화면 위치 매핑은 실제 분할 화면처럼 2x2 그리드로
    row_cells_only = [cells for kind, cells in body_entries if kind == "row"]
    quad_terms = [QUAD_TERM_RE.match(c[0].strip()) for c in row_cells_only]
    if ncol == 2 and len(row_cells_only) == 4 and all(quad_terms):
        cells_html = "".join(
            f'<div class="quad-cell"><span class="quad-num">{m.group(1)}</span>'
            f'<span class="quad-label">{inline(c[1])}</span></div>'
            for m, c in zip(quad_terms, row_cells_only)
        )
        return f'<div class="quad-grid">{cells_html}</div>'

    # 단순 2열 매핑(예: 포트 번호 -> 장비, 구분 -> 설명) 표는 큰 목록형으로
    if ncol == 2 and row_count <= 6 and not has_img:
        rows_html = []
        for kind, cells in body_entries:
            if kind != "row":
                continue
            rows_html.append(
                f'<div class="def-row"><span class="def-term">{inline(cells[0])}</span>'
                f'<span class="def-desc">{inline(cells[1])}</span></div>'
            )
        return f'<div class="def-list">{"".join(rows_html)}</div>'

    thead = "<tr>" + "".join(f"<th>{inline(c)}</th>" for c in header_cells) + "</tr>"
    tbody_parts = []
    for kind, val in body_entries:
        if kind == "row":
            cells_html = "".join(f"<td>{inline(c)}</td>" for c in val)
            tbody_parts.append(f"<tr>{cells_html}</tr>")
        else:
            tbody_parts.append(f'<tr class="img-row"><td colspan="{ncol}">{val}</td></tr>')
    colgroup = ""
    table_style = ""
    if col_widths and len(col_widths) == ncol:
        colgroup = "<colgroup>" + "".join(f'<col style="width:{w}">' for w in col_widths) + "</colgroup>"
        table_style = ' style="table-layout:fixed"'
    return (
        '<div class="cont-table-wrap"><table class="cont-table"'
        f"{table_style}>{colgroup}"
        f"<thead>{thead}</thead><tbody>{''.join(tbody_parts)}</tbody></table></div>"
    )


QUAD_GRID_BLOCK_RE = re.compile(
    r'<div class="quad-grid">(?:<div class="quad-cell">.*?</div>){4}</div>', re.DOTALL
)


def render_quad_grid_cells(labels):
    cells_html = "".join(
        f'<div class="quad-cell"><span class="quad-num">{i}</span>'
        f'<span class="quad-label">{inline(label)}</span></div>'
        for i, label in enumerate(labels, start=1)
    )
    return f'<div class="quad-grid">{cells_html}</div>'


# 원문에는 UT Case 포트 매핑만 있고 FGI Case는 없어서(원문에도 "확정 필요"로 남아있던 항목),
# 사용자가 준 참고 이미지 내용을 그대로 옆에 나란히 추가한다.
QUAD_GRID_EXTRA = {
    "10": {
        "ut_label": "UT Case",
        "fgi_label": "FGI Case",
        "fgi_items": ["참여자그룹", "참여자그룹", "전경", "PC"],
    },
    "14": {
        "ut_label": "UT Case",
        "fgi_label": "FGI Case",
        "fgi_items": ["참여자그룹", "참여자그룹", "전경", "PC"],
    },
}


def render_split_image_layout(cont):
    blocks = render_cont_blocks(cont)
    image_blocks = [b for b in blocks if b.startswith('<div class="cont-img-solo"')]
    table_blocks = [b for b in blocks if b.startswith('<div class="cont-table-wrap"')]
    other_blocks = [b for b in blocks if b not in image_blocks and b not in table_blocks]
    return (
        '<div class="split-layout">'
        f'<div class="split-image">{"".join(image_blocks)}</div>'
        '<div class="split-right">'
        f'<div class="split-table">{"".join(table_blocks)}</div>'
        f'<div class="split-box">{"".join(other_blocks)}</div>'
        "</div></div>"
    )


def render_two_col_cards(cards):
    cols = "".join(
        f'<div class="two-card"><h4>{c["title"]}</h4>{c["body"]}</div>' for c in cards
    )
    return f'<div class="two-col-cards">{cols}</div>'


H4_BLOCK_RE = re.compile(r"^<h4>(.*?)</h4>$")


def render_h4_card_layout(cont, boundary_titles=None, step_style="bullet"):
    blocks = render_cont_blocks(cont, step_style=step_style)
    cards = []
    cur_title, cur_body = None, []
    for b in blocks:
        m = H4_BLOCK_RE.match(b)
        is_boundary = bool(m) and (boundary_titles is None or m.group(1) in boundary_titles)
        if is_boundary:
            if cur_title is not None:
                cards.append({"title": cur_title, "body": "".join(cur_body)})
            cur_title, cur_body = m.group(1), []
        elif m:
            cur_body.append(f"<p>{m.group(1)}</p>")
        else:
            cur_body.append(b)
    if cur_title is not None:
        cards.append({"title": cur_title, "body": "".join(cur_body)})
    return render_two_col_cards(cards)


CIRCLED_NUM_STRIP_RE = re.compile(r"^[①②③④⑤⑥⑦⑧⑨⑩]\s*")


def render_stepper_group_layout(cont, boundary_titles):
    """h4 그룹(①②③ 등) 자체를 스테퍼의 단계로 사용. 그룹 내부 번호 목록은 일반 번호(1.2.3.)로,
    스테퍼-안-스테퍼로 겹치지 않도록 함."""
    blocks = render_cont_blocks(cont, step_style="numbered")
    groups = []
    cur_title, cur_body = None, []
    for b in blocks:
        m = H4_BLOCK_RE.match(b)
        is_boundary = bool(m) and m.group(1) in boundary_titles
        if is_boundary:
            if cur_title is not None:
                groups.append((cur_title, cur_body))
            cur_title, cur_body = m.group(1), []
        elif m:
            cur_body.append(f"<p>{m.group(1)}</p>")
        else:
            cur_body.append(b)
    if cur_title is not None:
        groups.append((cur_title, cur_body))

    items_html = []
    for idx, (title, body_blocks) in enumerate(groups, start=1):
        clean_title = CIRCLED_NUM_STRIP_RE.sub("", title)
        body_html = "".join(body_blocks)
        items_html.append(
            f'<li><span class="step-num">{idx}</span><div class="step-rule"></div>'
            f'<div class="step-text"><span class="step-main">{clean_title}</span>{body_html}</div></li>'
        )
    return f'<ol class="cont-steps cont-steps-wide">{"".join(items_html)}</ol>'


# 참여자 컨택 프로세스 등 "- ### N. 제목" 형태의 숫자 스텝을 스테퍼 컴포넌트로 변환.
# 그룹 순번이 아니라 원문 숫자를 그대로 써서 페이지가 나뉘어도(25p 1~3, 26p 4~6) 번호가 이어진다.
STEP_GROUP_PAGES = {"09", "26", "27", "28", "29", "30"}
NUM_TITLE_RE = re.compile(r"^(\d+)\.\s*(.*)$")


def render_step_group_layout(cont):
    blocks = render_cont_blocks(cont, step_style="numbered", demote_bullets=True)
    groups = []
    cur_num, cur_title, cur_body = None, None, []
    for b in blocks:
        m = H4_BLOCK_RE.match(b)
        nm = NUM_TITLE_RE.match(m.group(1)) if m else None
        if nm:
            if cur_title is not None:
                groups.append((cur_num, cur_title, cur_body))
            cur_num, cur_title, cur_body = nm.group(1), nm.group(2), []
        else:
            cur_body.append(b)
    if cur_title is not None:
        groups.append((cur_num, cur_title, cur_body))

    items_html = []
    for num, title, body_blocks in groups:
        body_html = "".join(wrap_example_boxes(wrap_note_asides(body_blocks)))
        items_html.append(
            f'<li><span class="step-num">{num}</span><div class="step-rule"></div>'
            f'<div class="step-text"><span class="step-main">{title}</span>{body_html}</div></li>'
        )
    return f'<ol class="cont-steps cont-steps-wide">{"".join(items_html)}</ol>'


TEXT_IMAGE_BOX_PAGES = {"32"}  # 상단: 텍스트-이미지 좌우 배치 / 하단: 표를 박스로


def render_text_image_box_layout(cont):
    blocks = render_cont_blocks(cont)
    img_idx = next(i for i, b in enumerate(blocks) if b.startswith('<div class="cont-img-solo"'))
    img_block = blocks[img_idx]
    remaining = blocks[:img_idx] + blocks[img_idx + 1 :]
    h4_indices = [i for i, b in enumerate(remaining) if b.startswith("<h4")]

    if h4_indices and h4_indices[0] == 0:
        top_heading = remaining[0]
        rest = remaining[1:]
        h4_indices = [i - 1 for i in h4_indices[1:]]
    else:
        top_heading = ""
        rest = remaining

    if h4_indices:
        split = h4_indices[0]
        text_blocks, box_blocks = rest[:split], rest[split:]
    else:
        text_blocks, box_blocks = rest, []

    img_block_large = img_block.replace('class="cont-img-solo"', 'class="cont-img-solo cont-img-large"')
    top_html = top_heading + "".join(text_blocks) + img_block_large
    box_html = f'<div class="table-box">{"".join(box_blocks)}</div>' if box_blocks else ""
    return top_html + box_html


# 영상·음향 신호 흐름 페이지: 전체구조는 3단 플로우 다이어그램으로, 트랙별 설명은 박스로,
# 여유 채널 콜아웃은 각주로 낮춰 음향 트랙 박스 아래에 붙인다.
SIGNAL_FLOW_PAGES = {
    "23": {
        "stages": [
            {"label": "1층 · 촬영·녹음", "items": ["카메라 3대 (참여자뷰·시료탑뷰·전경CCTV)", "마이크 7대 (유선5+무선2)"]},
            {"label": "장거리 전송", "items": ["영상: HDMI over Cat5 (익스텐더)", "음향: XLR 아날로그 직결"]},
            {"label": "4층 · 관찰·청취", "items": ["멀티뷰 TV (3~4분할)", "앰프 + 별도 스피커"]},
        ],
    },
}

FLOW_CODE_P_RE = re.compile(r"^<p><code>(.*)</code></p>$", re.DOTALL)
FLOW_CALLOUT_RE = re.compile(
    r'^<div class="callout callout-note"><i>(.*?)</i><span>(.*?)</span></div>$', re.DOTALL
)


def render_signal_flow_layout(cont, cfg):
    blocks = render_cont_blocks(cont)

    stage_cards = []
    for s in cfg["stages"]:
        items_html = "".join(f"<li>{inline(it)}</li>" for it in s["items"])
        stage_cards.append(
            '<div class="flow-stage">'
            '<div class="flow-node" aria-hidden="true"></div>'
            f'<div class="flow-stage-label">{inline(s["label"])}</div>'
            f'<ul class="flow-stage-items">{items_html}</ul>'
            "</div>"
        )
    structure_html = f'<h4>전체구조</h4><div class="flow-diagram">{"".join(stage_cards)}</div>'

    def track_text(idx):
        if idx >= len(blocks):
            return ""
        m = FLOW_CODE_P_RE.match(blocks[idx])
        return m.group(1) if m else blocks[idx]

    video_text = track_text(3)
    audio_text = track_text(5)

    footnote_html = ""
    if len(blocks) > 6:
        m = FLOW_CALLOUT_RE.match(blocks[6])
        if m:
            footnote_html = f'<p class="footnote">※ {m.group(1)} — {m.group(2)}</p>'

    video_box = f'<div class="table-box"><h4 class="h4-note">영상 트랙</h4><p class="flow-track-text">{video_text}</p></div>'
    audio_box = (
        '<div class="table-box"><h4 class="h4-note">음향 트랙</h4>'
        f'<p class="flow-track-text">{audio_text}</p>{footnote_html}</div>'
    )
    return structure_html + video_box + audio_box


H4_CARD_PAGES = {
    "12": None,  # 카메라 설치 / 촬영 영역 표시 -> 좌우 카드
}
STEPPER_GROUP_PAGES = {
    "20": {"① 기본 설정 (모든 외국어 세션 공통)", "② 실시간 번역 큰 글씨 모드", "③ 오류 발생 시"},
    "21": {"① 영상 파일 추출", "② 음성 파일 추출 (Mac 기준)", "③ 스크립트(STT) 변환"},
}
TABLE_CARD_PAGES = {"11"}  # 참여자뷰 / 전경 CCTV -> 좌우 카드
TABLE_COL_WIDTHS = {"04": ["24%", "22%", "12%", "42%"]}
SPLIT_IMAGE_LAYOUT_PAGES = {"07", "08"}  # 배치도 페이지: 이미지 좌측 / 표+박스 우측
TABLE_BOX_PAGES = set()  # 표 + 각주를 박스로 감싸는 페이지 (각주는 표 마지막 행으로 병합) — 현재 해당 페이지 없음
FOOTNOTE_P_RE = re.compile(r'^<p><span class="footnote">(.*)</span></p>$', re.DOTALL)


def render_table_box_layout(cont, col_widths=None, heading_html=""):
    blocks = render_cont_blocks(cont, col_widths=col_widths)
    if blocks and blocks[-1].startswith("<p>"):
        footnote_block = blocks.pop()
        m = FOOTNOTE_P_RE.match(footnote_block)
        note_text = m.group(1) if m else footnote_block
        ncol = blocks[0].count("<th>") if blocks else 1
        note_row = f'<tr class="note-row"><td colspan="{ncol}">{note_text}</td></tr>'
        blocks[0] = blocks[0].replace("</tbody>", note_row + "</tbody>")
    return f'<div class="table-box">{heading_html}{"".join(blocks)}</div>'


SPEC_GRID_PAGES = {"24", "25"}


def render_spec_card_grid(cont):
    rows = []
    header_seen = False
    for raw_line in cont.split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("|"):
            if re.match(r"^\|[\s:\-|]+\|$", line):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if not header_seen:
                header_seen = True
                continue
            rows.append({"cat": cells[0], "name": cells[1], "spec": cells[2], "img": None})
            continue
        im = IMG_RE.match(line)
        if im and rows:
            rows[-1]["img"] = (im.group(1), im.group(2))
    cards = []
    for r in rows:
        if r["img"]:
            alt, src = r["img"]
            fname = src.split("/")[-1]
            img_html = f'<img src="assets/{fname}" alt="{html.escape(alt)}" loading="lazy">'
        else:
            img_html = ""
        cards.append(
            f'<div class="spec-card">{img_html}'
            f'<div class="spec-card-body">'
            f'<div class="spec-cat">{inline(r["cat"])}</div>'
            f'<div class="spec-name">{inline(r["name"])}</div>'
            f'<div class="spec-desc">{inline(r["spec"])}</div>'
            "</div></div>"
        )
    return f'<div class="spec-grid">{"".join(cards)}</div>'


def render_table_note_layout(cont):
    blocks = render_cont_blocks(cont)
    table_blocks = [b for b in blocks if b.startswith('<div class="cont-table-wrap"')]
    other_blocks = [b for b in blocks if b not in table_blocks]
    return (
        '<div class="table-note-layout">'
        f'{"".join(table_blocks)}'
        f'<div class="split-box">{"".join(other_blocks)}</div>'
        "</div>"
    )


TABLE_NOTE_LAYOUT_PAGES = {"17"}
CHECKLIST_REORDER_PAGES = set()


def render_checklist_reorder_layout(cont):
    return render_cont(cont)


# ---------------------------------------------------------------
# 4. masgTitle(헤드라인) 렌더러
# ---------------------------------------------------------------
def render_masgtitle(masgTitle, masgType, tag="h1"):
    lines = [l.strip() for l in masgTitle.split("\n") if l.strip()]
    if not lines:
        return ""
    if masgType == "강조형":
        if all(re.match(r"^\d+\.\s", l.strip()) for l in lines):
            NUM_PREFIX = re.compile(r"^\d+\.\s+")
            item_strs = [f"<li>{inline(NUM_PREFIX.sub('', l.strip()))}</li>" for l in lines]
            return f'<ol class="divider-list">{"".join(item_strs)}</ol>'
        return f"<{tag}>" + "<br>".join(inline(l) for l in lines) + f"</{tag}>"
    joined = " ".join(lines)
    m = PAGETITLE_NUM_RE.match(joined)
    if m:
        joined = m.group(2)
    return f"<{tag}>" + inline(joined) + f"</{tag}>"


def slugify(pageNumber):
    return f"p{pageNumber}"


cover = pages[0]
rest = pages[1:]

NOTE_ASIDE_RE = re.compile(r"^<h4>(.*확인\s*필요.*)</h4>$")


def wrap_note_asides(blocks):
    out = []
    i = 0
    while i < len(blocks):
        b = blocks[i]
        m = NOTE_ASIDE_RE.match(b)
        if m and i + 1 < len(blocks) and blocks[i + 1].startswith("<p"):
            out.append(f'<div class="note-aside">{b}{blocks[i + 1]}</div>')
            i += 2
            continue
        out.append(b)
        i += 1
    return out


EXAMPLE_BOX_RE = re.compile(r'^<h4 class="h4-note">.*</h4>$')


def wrap_example_boxes(blocks):
    """박스형 소제목(h4-note) 바로 뒤에 오는 예시 코드블록을 하나의 박스로 묶는다."""
    out = []
    i = 0
    while i < len(blocks):
        b = blocks[i]
        if EXAMPLE_BOX_RE.match(b) and i + 1 < len(blocks) and blocks[i + 1].startswith('<pre class="cont-code">'):
            out.append(f'<div class="example-box">{b}{blocks[i + 1]}</div>')
            i += 2
            continue
        out.append(b)
        i += 1
    return out


def render_item(p, show_full_label):
    pid = slugify(p["pageNumber"])
    quickfind = p["pageNumber"] == "03"
    col_widths = TABLE_COL_WIDTHS.get(p["pageNumber"])
    if show_full_label:
        masgtitle_html = render_masgtitle(p["masgTitle"], p["masgType"], tag="h2")
    else:
        _, remainder = split_number_prefix(p["pageTitle"])
        leaf_label = NAV_LABEL_OVERRIDES.get(p["pageNumber"]) or short_leaf_label_suffix(remainder)
        masgtitle_html = f'<h2 class="leaf-pill">{inline(leaf_label)}</h2>'
    box_heading_html = ""
    if p["pageNumber"] in TABLE_BOX_PAGES:
        box_heading_html = render_masgtitle(p["masgTitle"], p["masgType"], tag="h4").replace(
            "<h4>", '<h4 class="h4-note">', 1
        )
        masgtitle_html = ""
    # masgSubText는 "본문 설명\n\n※ 참고 각주" 형태로 두 문단이 들어있을 수 있음 —
    # 뒷문단(※로 시작)은 각주 레벨(page-subtext footnote)로 따로 렌더링한다.
    subtext_paras = p["masgSubText"].split("\n\n", 1) if p["masgSubText"] else []
    subtext_html = f'<p class="page-subtext">{inline(subtext_paras[0], strip_bold=True)}</p>' if subtext_paras else ""
    if len(subtext_paras) > 1 and subtext_paras[1].strip():
        subtext_html += f'<p class="page-subtext footnote">{inline(subtext_paras[1].strip())}</p>'
    if p["pageNumber"] in SPLIT_IMAGE_LAYOUT_PAGES:
        cont_html = render_split_image_layout(p["cont"])
    elif p["pageNumber"] in H4_CARD_PAGES:
        cont_html = render_h4_card_layout(p["cont"], boundary_titles=H4_CARD_PAGES[p["pageNumber"]])
    elif p["pageNumber"] in STEPPER_GROUP_PAGES:
        cont_html = render_stepper_group_layout(p["cont"], STEPPER_GROUP_PAGES[p["pageNumber"]])
    elif p["pageNumber"] in STEP_GROUP_PAGES:
        cont_html = render_step_group_layout(p["cont"])
    elif p["pageNumber"] in TABLE_CARD_PAGES:
        cont_html = render_table_card_layout(p["cont"])
    elif p["pageNumber"] in SPEC_GRID_PAGES:
        cont_html = render_spec_card_grid(p["cont"])
    elif p["pageNumber"] in TABLE_NOTE_LAYOUT_PAGES:
        cont_html = render_table_note_layout(p["cont"])
    elif p["pageNumber"] in CHECKLIST_REORDER_PAGES:
        cont_html = render_checklist_reorder_layout(p["cont"])
    elif p["pageNumber"] in TABLE_BOX_PAGES:
        cont_html = render_table_box_layout(p["cont"], col_widths=col_widths, heading_html=box_heading_html)
    elif p["pageNumber"] in TEXT_IMAGE_BOX_PAGES:
        cont_html = render_text_image_box_layout(p["cont"])
    elif p["pageNumber"] in SIGNAL_FLOW_PAGES:
        cont_html = render_signal_flow_layout(p["cont"], SIGNAL_FLOW_PAGES[p["pageNumber"]])
    else:
        cont_html = render_cont(
            p["cont"], quickfind_mode=quickfind, col_widths=col_widths,
            demote_bullets=p["pageNumber"] in SUB_BULLET_PAGES,
        )
    if p["pageNumber"] in QUAD_GRID_EXTRA:
        cfg = QUAD_GRID_EXTRA[p["pageNumber"]]
        m = QUAD_GRID_BLOCK_RE.search(cont_html)
        if m:
            fgi_grid = render_quad_grid_cells(cfg["fgi_items"])
            replacement = (
                '<div class="quad-grid-row">'
                f'<div class="quad-grid-item"><div class="quad-case-label">{cfg["ut_label"]}</div>{m.group(0)}</div>'
                f'<div class="quad-grid-item"><div class="quad-case-label">{cfg["fgi_label"]}</div>{fgi_grid}</div>'
                "</div>"
            )
            cont_html = cont_html[: m.start()] + replacement + cont_html[m.end() :]
    return (
        f'<section class="subpage" id="{pid}" data-page="{pid}">'
        f"{masgtitle_html}{subtext_html}"
        f'<div class="page-cont">{cont_html}</div>'
        f"</section>"
    )


TABLE_ROW_RE = re.compile(r"^\|\s*\*\*(.+?)\*\*\s*\|(.+)\|(.+)\|$")


def render_table_card_layout(cont):
    """단일 행짜리 표 여러 개(제목|설명|기준 목록<br>구분)를 좌우 카드로 렌더링. (page 10)"""
    lines = [l.strip() for l in cont.split("\n") if l.strip() and not re.match(r"^%%.*%%$", l.strip())]
    n = len(lines)
    i = 0
    cards_html = []
    while i < n:
        line = lines[i]
        if re.match(r"^\|[\s:\-|]+\|$", line):
            i += 1
            continue
        m = TABLE_ROW_RE.match(line)
        if not m:
            i += 1
            continue
        title = m.group(1).strip()
        desc = m.group(2).strip()
        criteria = [c.strip() for c in m.group(3).split("<br>") if c.strip()]
        i += 1
        img_html = ""
        if i < n and lines[i].startswith("!["):
            img_html = inline(lines[i])
            i += 1
        items_html = "".join(f"<li>{inline(c)}</li>" for c in criteria)
        cards_html.append(
            f"<div class=\"two-card\"><h4>{inline(title, strip_bold=True)}</h4>"
            f"<p>{inline(desc)}</p>"
            f'<ul class="cont-list check-marks">{items_html}</ul>'
            f"{img_html}</div>"
        )
    return f'<div class="two-col-cards">{"".join(cards_html)}</div>'




# ---------------------------------------------------------------
# 5. 본문 body 조립
# ---------------------------------------------------------------
body_parts = []
body_parts.append(
    f'<section class="hero-cover" id="{slugify(cover["pageNumber"])}" data-page="{slugify(cover["pageNumber"])}">'
    f'<div class="hero-cover-brand">VINYLC</div>'
    f"<h1>사용자 조사 환경<br>세팅 실행 가이드</h1>"
    f'<div class="hero-cover-sub">2026.08 / V1.00</div>'
    f"</section>"
)

for part in parts:
    header, divider, group_defs = part["header"], part["divider"], part["groups"]
    kicker, title = split_header(header)

    if divider:
        intro_html = render_cont(divider["cont"])
        body_parts.append(
            f'<section class="part-hero" id="{slugify(divider["pageNumber"])}" data-page="{slugify(divider["pageNumber"])}">'
            f'<div class="part-kicker">{html.escape(kicker)}</div>'
            f'<h1 class="part-title">{html.escape(title)}</h1>'
            f'<div class="part-intro">{intro_html}</div>'
            f"</section>"
        )
    else:
        first_id = slugify(group_defs[0]["items"][0]["pageNumber"]) if group_defs else ""
        body_parts.append(
            f'<div class="part-label-only" id="{first_id}" data-page="{first_id}">'
            f'<div class="part-kicker">{html.escape(kicker)}</div>'
            f'<h2 class="part-title-sm">{html.escape(title)}</h2></div>'
        )

    for g in group_defs:
        if len(g["items"]) > 1 and g["label"]:
            body_parts.append(f'<h3 class="group-title">{html.escape(g["label"])}</h3>')
            for p in g["items"]:
                body_parts.append(render_item(p, show_full_label=False))
        else:
            body_parts.append(render_item(g["items"][0], show_full_label=True))

# 문서 자체의 개정 이력(md 최하단 "## 변경 이력" 표) — 가이드 콘텐츠가 아닌 문서 메타정보라
# 사이드바 목차/스크롤스파이 대상에는 포함하지 않고, 스크롤 맨 끝에 조용한 푸터로만 노출한다.
CHANGELOG_RE = re.compile(
    r"## 변경 이력\n\n(?P<table>\|.*\|(?:\n\|.*\|)*)\n*(?P<note>※.*)?",
    re.DOTALL,
)
changelog_html = ""
m = CHANGELOG_RE.search(raw)
if m:
    table_lines = [l for l in m.group("table").strip("\n").split("\n") if l.strip()]
    rows = []
    for line in table_lines[2:]:  # 헤더 행 + 구분선 행 스킵
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 4:
            rows.append(cells[:4])
    if rows:
        head_html = "".join(f"<th>{html.escape(h)}</th>" for h in ["버전", "날짜", "작성자", "변경 내용"])
        body_html = "".join(
            "<tr>" + "".join(f"<td>{inline(c)}</td>" for c in row) + "</tr>" for row in rows
        )
        note = (m.group("note") or "").strip()
        note_html = f'<p class="changelog-note">{inline(note)}</p>' if note else ""
        changelog_html = (
            '<section class="changelog-footer">'
            '<h3 class="changelog-title">변경 이력</h3>'
            '<div class="cont-table-wrap">'
            f'<table class="changelog-table"><thead><tr>{head_html}</tr></thead>'
            f"<tbody>{body_html}</tbody></table>"
            "</div>"
            f"{note_html}"
            "</section>"
        )
if changelog_html:
    body_parts.append(changelog_html)

pages_html = "\n".join(body_parts)

all_ids = [slugify(cover["pageNumber"])]
for part in parts:
    if part["divider"]:
        all_ids.append(slugify(part["divider"]["pageNumber"]))
    for g in part["groups"]:
        for p in g["items"]:
            all_ids.append(slugify(p["pageNumber"]))
nav_data = json.dumps(all_ids)

# ---------------------------------------------------------------
# 6. 사이드바 nav 조립
# ---------------------------------------------------------------
nav_parts = [f'<a href="#{slugify(cover["pageNumber"])}" class="nav-cover" data-page="{slugify(cover["pageNumber"])}">표지</a>']

for part in parts:
    header, divider, group_defs = part["header"], part["divider"], part["groups"]
    first_item_id = slugify(group_defs[0]["items"][0]["pageNumber"]) if group_defs else ""
    anchor_target = slugify(divider["pageNumber"]) if divider else first_item_id
    nav_parts.append(
        f'<a href="#{anchor_target}" class="nav-section-label" data-page="{anchor_target}">{html.escape(header)}</a>'
    )
    for g in group_defs:
        if len(g["items"]) > 1 and g["label"]:
            g_anchor = slugify(g["items"][0]["pageNumber"])
            children_html = []
            for p in g["items"]:
                _, remainder = split_number_prefix(p["pageTitle"])
                label = NAV_LABEL_OVERRIDES.get(p["pageNumber"]) or short_leaf_label_suffix(remainder)
                children_html.append(
                    f'<a href="#{slugify(p["pageNumber"])}" class="nav-item nav-item-sub" data-page="{slugify(p["pageNumber"])}">{html.escape(label)}</a>'
                )
            nav_parts.append(
                '<div class="nav-group-block">'
                f'<a href="#{g_anchor}" class="nav-group" data-page="{g_anchor}">'
                f'<span class="nav-group-label">{html.escape(g["label"])}</span>'
                '<span class="nav-chevron" aria-hidden="true">'
                '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" '
                'stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>'
                "</span>"
                "</a>"
                f'<div class="nav-group-children">{"".join(children_html)}</div>'
                "</div>"
            )
        else:
            p = g["items"][0]
            label = g["label"]
            nav_parts.append(
                f'<a href="#{slugify(p["pageNumber"])}" class="nav-item" data-page="{slugify(p["pageNumber"])}">{html.escape(label)}</a>'
            )
nav_html = "\n".join(nav_parts)

# ---------------------------------------------------------------
# 7. CSS
# ---------------------------------------------------------------
CSS = """
:root{
  --bg:#ffffff; --bg-sub:#f5f5f3; --border:#e6e4dd; --border-strong:#d4d1c6;
  --text:#1d1d1b; --text-sub:#6e6d66; --text-muted:#9b9a92;
  --accent:#0c447c; --accent-bg:#eaf3fb;
  --warn:#7a4a0a; --warn-bg:#faf0dd;
  --radius:10px; --sidebar-w:380px;
  font-family:'Pretendard',-apple-system,BlinkMacSystemFont,'Malgun Gothic','Apple SD Gothic Neo',sans-serif;
}
*{box-sizing:border-box;}
html{scroll-behavior:smooth;}
html,body{margin:0;padding:0;background:var(--bg);color:var(--text);}
body{display:flex;min-height:100vh;font-size:19px;line-height:1.65;word-break:keep-all;}

/* ---- 사이드바 ---- */
#sidebar{
  width:var(--sidebar-w);flex-shrink:0;border-right:1px solid var(--border);
  background:var(--bg-sub);height:100vh;position:sticky;top:0;overflow-y:auto;
  padding:28px 18px 60px;
}
#sidebar .brand{font-size:15px;font-weight:600;padding:4px 10px 18px;color:var(--text);letter-spacing:-0.01em;}
#sidebar .brand small{display:block;font-weight:400;color:var(--text-sub);font-size:12.5px;margin-top:3px;}
#search{
  width:100%;padding:10px 12px;margin-bottom:16px;border:1px solid var(--border-strong);
  border-radius:var(--radius);font-size:14px;background:#fff;color:var(--text);
}
#search:focus{outline:2px solid #85b7eb;outline-offset:0;}
.nav-cover{
  display:block;padding:8px 10px;border-radius:7px;
  color:var(--text);text-decoration:none;font-size:14px;font-weight:600;margin-bottom:12px;
}
.nav-cover:hover{background:var(--bg);}
.nav-section-label{
  display:block;font-size:12px;font-weight:600;color:var(--text-muted);text-transform:uppercase;
  letter-spacing:.04em;padding:16px 10px 5px;text-decoration:none;
}
.nav-section-label:hover{color:var(--text-sub);}
.nav-item{
  display:block;padding:6.5px 10px 6.5px 18px;border-radius:7px;color:var(--text-sub);
  text-decoration:none;font-size:14px;line-height:1.5;
}
.nav-item:hover{background:var(--bg);color:var(--text);}
.nav-group{
  display:flex;align-items:center;gap:4px;
  padding:6.5px 10px 6.5px 18px;border-radius:7px;color:var(--text-sub);
  text-decoration:none;font-size:14px;font-weight:400;line-height:1.5;
}
.nav-group:hover{background:var(--bg);color:var(--text);}
.nav-chevron{
  flex-shrink:0;width:20px;height:20px;display:inline-flex;align-items:center;justify-content:center;
  color:var(--text-muted);transition:transform .15s ease;cursor:pointer;
}
.nav-chevron svg{width:100%;height:100%;}
.nav-group-block.expanded > .nav-group .nav-chevron{transform:rotate(180deg);}
.nav-group-children{display:none;}
.nav-group-block.expanded > .nav-group-children{display:block;}
.nav-item-sub{padding-left:44px;font-size:13.5px;}
.nav-item.active,.nav-section-label.active,.nav-group.active{background:var(--accent-bg);color:var(--accent);font-weight:600;}

/* ---- 본문 공통 ---- */
#main{flex:1;min-width:0;padding:0 80px 200px;}
.hero-cover{padding:22vh 0 14vh;text-align:left;border-bottom:1px solid var(--border);margin-bottom:10vh;}
.hero-cover-brand{font-size:15px;font-weight:600;color:var(--accent);letter-spacing:.1em;margin-bottom:18px;}
.hero-cover h1{font-size:88px;font-weight:600;line-height:1.12;margin:0 0 28px;letter-spacing:-0.02em;max-width:1100px;}
.hero-cover-sub{font-size:18px;color:var(--text-sub);}

.part-hero,.part-label-only{padding:20vh 0 10vh;}
.part-hero{border-top:1px solid var(--border);margin-top:8vh;}
.part-kicker{font-size:14px;font-weight:600;color:var(--accent);letter-spacing:.06em;margin-bottom:14px;}
.part-title{font-size:56px;font-weight:600;line-height:1.15;margin:0 0 22px;letter-spacing:-0.015em;max-width:1100px;}
.part-title-sm{font-size:56px;font-weight:600;line-height:1.15;margin:0;letter-spacing:-0.015em;max-width:1100px;}
.part-intro{font-size:22px;color:var(--text-sub);max-width:1000px;line-height:1.55;margin-bottom:8px;}
.part-intro p{margin:0;}
.divider-list{margin:24px 0 0;padding-left:0;list-style:none;font-size:19px;color:var(--text);max-width:520px;}
.divider-list li{padding:12px 0;border-top:1px solid var(--border);}
.divider-list li:last-child{border-bottom:1px solid var(--border);}

.group-title{font-size:28px;font-weight:600;margin:12vh 0 0;letter-spacing:-0.01em;color:var(--text);}

.subpage{padding-top:12vh;scroll-margin-top:24px;}
.group-title + .subpage{padding-top:4vh;}
.subpage h2{font-size:26px;font-weight:600;margin:0 0 14px;line-height:1.35;letter-spacing:-0.01em;max-width:1000px;}
.subpage h2.leaf-pill{
  display:inline-block;font-size:17px;font-weight:600;padding:9px 22px;
  border-radius:999px;background:var(--text);border:1px solid var(--text);
  color:var(--bg);margin:0 0 18px;letter-spacing:.01em;
}
.page-subtext{font-size:20px;color:var(--text-sub);margin:0 0 40px;max-width:1000px;line-height:1.55;text-wrap:balance;word-break:keep-all;}
.page-subtext.footnote{font-size:13px;font-style:italic;color:var(--text-muted);margin-top:-24px;}
.tag-pill{display:inline-block;font-size:12px;font-weight:600;padding:4px 13px;border-radius:999px;margin-right:10px;letter-spacing:.02em;white-space:nowrap;vertical-align:2px;}
.tag-pill.tag-issue{background:var(--warn-bg);color:var(--warn);}
.tag-pill.tag-idea{background:var(--accent-bg);color:var(--accent);}

.page-cont p{margin:0 0 24px;font-size:16px;max-width:1000px;}
.page-cont .footnote,.split-box .footnote{font-size:13px;font-style:italic;color:var(--text-muted);}
.page-cont h4{font-size:19px;font-weight:600;margin:36px 0 14px;color:var(--text);max-width:1000px;}
.page-cont h4.h4-note{font-size:16px;}
.step-main{font-weight:500;display:inline-block;text-wrap:balance;word-break:keep-all;}
.step-note{color:var(--text-sub);font-size:15px;font-weight:300;}

ul.cont-list,ul.sub{margin:0 0 24px;padding-left:24px;font-size:16px;max-width:1000px;}
ul.cont-list li,ul.sub li{margin-bottom:8px;line-height:1.55;}
ul.sub{margin-top:10px;font-size:15px;color:var(--text-sub);font-weight:300;list-style-type:disc;}

/* 순서 있는 절차: 번호 -> 구분선 -> 텍스트 -> 이미지(항상 맨 아래) */
ol.cont-steps{display:flex;flex-wrap:wrap;gap:40px 24px;list-style:none;margin:0 0 32px;padding:0;max-width:none;}
ol.cont-steps > li{flex:1 0 220px;max-width:400px;margin-bottom:0;padding-left:0;}
ol.cont-steps > li > .step-num{
  display:flex;align-items:center;justify-content:center;flex-shrink:0;
  width:32px;height:32px;border-radius:50%;background:transparent;color:var(--text-sub);
  border:1.5px solid var(--border-strong);font-size:13px;font-weight:600;margin-bottom:16px;
}
ol.cont-steps > li > .step-rule{border-top:2px solid var(--border-strong);margin-bottom:16px;}
ol.cont-steps > li > .step-text{font-size:16px;line-height:1.6;color:var(--text);}
ol.cont-steps > li > .cont-fig{margin:16px 0 0;}

/* 그룹(①②③ 등) 자체가 스텝인 경우 — 안에 목록/이미지가 들어가므로 훨씬 넓게 */
ol.cont-steps.cont-steps-wide{gap:48px 40px;}
ol.cont-steps.cont-steps-wide > li{flex:1 1 340px;max-width:560px;}
ol.cont-steps.cont-steps-wide > li > .step-text > .step-main{display:block;font-size:19px;font-weight:600;margin-bottom:16px;}
ol.cont-steps.cont-steps-wide > li > .step-text p{font-size:16px;line-height:1.6;color:var(--text);margin:0 0 16px;}

ul.cont-checklist{list-style:none;margin:0 0 24px;padding:0;max-width:1000px;}
ul.cont-checklist li.check{display:flex;align-items:flex-start;gap:12px;font-size:16px;padding:8px 0;border-bottom:1px solid var(--border);}
ul.cont-checklist li.check:first-child{border-top:1px solid var(--border);}
ul.cont-checklist .box{
  width:20px;height:20px;color:var(--text-sub);
  margin-top:2px;flex-shrink:0;display:inline-flex;align-items:center;justify-content:center;
}

/* 절차의 단순 불릿 버전 (카드 안 등 스테퍼가 과한 곳에서 사용) */
ul.cont-bullets{list-style:none;margin:0 0 24px;padding:0;max-width:1000px;font-size:16px;line-height:1.6;color:var(--text);}
ul.cont-bullets > li{position:relative;padding-left:20px;margin-bottom:24px;}
ul.cont-bullets > li::before{content:"•";position:absolute;left:2px;top:0;color:var(--text-sub);}
ul.cont-bullets .bullet-desc{margin-top:6px;}
ul.cont-bullets .cont-fig{margin-top:12px;}
ul.cont-bullets.cont-numbered > li::before{content:none;}
ul.cont-bullets.cont-numbered > li{padding-left:26px;}
ul.cont-bullets.cont-numbered .num-marker{position:absolute;left:0;top:0;color:var(--text-sub);font-weight:600;}

/* TV 4분할처럼 실제 화면 위치가 있는 매핑은 2x2 그리드로 */
.quad-grid{
  display:grid;grid-template-columns:1fr 1fr;grid-template-rows:1fr 1fr;
  gap:1px;background:var(--border);border:1px solid var(--border);
  border-radius:12px;overflow:hidden;max-width:420px;aspect-ratio:16/9;margin:0 0 24px;
}
.quad-cell{
  background:var(--bg-sub);display:flex;flex-direction:column;align-items:flex-start;
  justify-content:center;gap:8px;padding:16px 20px;
}
.quad-num{
  display:flex;align-items:center;justify-content:center;flex-shrink:0;
  width:24px;height:24px;border-radius:50%;background:var(--text);color:var(--bg);
  font-size:12px;font-weight:600;
}
.quad-label{font-size:14px;font-weight:500;color:var(--text-sub);}
.quad-grid-row{display:flex;flex-wrap:wrap;gap:32px;margin-bottom:8px;}
.quad-grid-item{flex:0 1 420px;}
.quad-grid-item .quad-grid{margin-bottom:0;}
.quad-case-label{font-size:13px;font-weight:600;color:var(--text-sub);margin-bottom:10px;}

/* 장비/저장매체 사양표 -> 사진 카드 그리드 (세로 스크롤 과다 방지) */
.spec-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:24px;margin-bottom:8px;max-width:1400px;}
.spec-card{border:1px solid var(--border);border-radius:12px;overflow:hidden;background:var(--bg-sub);}
.spec-card img{width:100%;height:170px;object-fit:cover;display:block;}
.spec-card-body{padding:14px 16px 18px;}
.spec-cat{font-size:12px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.03em;margin-bottom:6px;}
.spec-name{font-size:15px;font-weight:600;color:var(--text);margin-bottom:6px;line-height:1.4;}
.spec-desc{font-size:13px;color:var(--text-sub);line-height:1.5;}

/* 큰 정의형 목록 (단순 2열 표 대체) */
.def-list{
  margin:0 0 24px;max-width:820px;border:1px solid var(--border);
  border-radius:12px;padding:2px 20px;background:var(--bg-sub);
}
.def-row{display:flex;gap:20px;padding:10px 0;border-bottom:1px solid var(--border);align-items:baseline;}
.def-row:first-child{border-top:none;}
.def-row:last-child{border-bottom:none;}
.def-term{font-size:14px;font-weight:600;flex:0 0 88px;color:var(--text-sub);}
.def-desc{font-size:15px;color:var(--text-sub);line-height:1.5;}

.cont-table-wrap{overflow-x:auto;margin:0 0 32px;}
table.cont-table{border-collapse:collapse;width:100%;font-size:16px;max-width:1120px;}
table.cont-table th,table.cont-table td{
  border-bottom:1px solid var(--border);padding:16px 18px 16px 0;text-align:left;vertical-align:top;
}
table.cont-table th{font-weight:600;color:var(--text-muted);font-size:12px;text-transform:uppercase;letter-spacing:.03em;border-bottom:1px solid var(--border-strong);}
table.cont-table tr:last-child td{border-bottom:none;}
table.cont-table tr.img-row td{padding:14px 0 26px;}

.changelog-footer{border-top:1px solid var(--border);margin-top:14vh;padding:48px 0 10vh;}
.changelog-title{font-size:13px;font-weight:600;color:var(--text-muted);letter-spacing:.04em;margin:0 0 18px;}
table.changelog-table{border-collapse:collapse;width:100%;font-size:13px;max-width:1120px;color:var(--text-sub);}
table.changelog-table th,table.changelog-table td{
  border-bottom:1px solid var(--border);padding:10px 16px 10px 0;text-align:left;vertical-align:top;
}
table.changelog-table th{font-weight:600;color:var(--text-muted);font-size:11px;text-transform:uppercase;letter-spacing:.03em;border-bottom:1px solid var(--border-strong);}
table.changelog-table td:first-child,table.changelog-table th:first-child{white-space:nowrap;}
table.changelog-table td:nth-child(2),table.changelog-table th:nth-child(2){white-space:nowrap;}
table.changelog-table tr:last-child td{border-bottom:none;}
.changelog-note{font-size:12px;font-style:italic;color:var(--text-muted);margin:18px 0 0;}
a.jump-link{color:var(--accent);text-decoration:none;font-weight:600;}
a.jump-link:hover{text-decoration:underline;}

.cont-fig{margin:16px 0;display:block;max-width:350px;}
.cont-fig img{max-width:min(350px,100%);max-height:350px;width:auto;height:auto;border-radius:12px;display:block;}
.cont-fig figcaption{font-size:13px;color:var(--text-muted);margin-top:8px;}
.cont-img-solo{margin:24px 0;max-width:350px;}

.cont-code{
  background:var(--bg-sub);border:1px solid var(--border);border-radius:12px;
  padding:20px 22px;font-size:14.5px;line-height:1.75;overflow-x:auto;white-space:pre-wrap;
  font-family:'SF Mono',ui-monospace,Consolas,monospace;color:var(--text);margin:0 0 24px;max-width:820px;
}
code{font-family:'SF Mono',ui-monospace,Consolas,monospace;font-size:0.9em;background:var(--bg-sub);padding:2px 6px;border-radius:5px;}

.callout{display:flex;gap:12px;align-items:flex-start;padding:16px 20px;border-radius:var(--radius);margin:0 0 24px;font-size:16px;max-width:900px;}
.callout i{font-style:normal;font-weight:600;flex-shrink:0;}
.callout-warn{background:var(--warn-bg);color:var(--warn);}
.callout-note{background:var(--accent-bg);color:var(--accent);}

/* 배치도 페이지: 이미지 좌측 / 표+박스 우측 2단 레이아웃 */
.split-layout{display:grid;grid-template-columns:minmax(0,560px) minmax(0,1fr);gap:64px;align-items:start;margin-bottom:8px;max-width:1400px;}
.split-image .cont-fig,.split-image .cont-img-solo{max-width:100%;margin:0;}
.split-image img{width:100%;max-width:100%;max-height:none;height:auto;}
.split-right{display:flex;flex-direction:column;gap:24px;min-width:0;}
.split-table .cont-table-wrap{margin-bottom:0;}
.split-table table.cont-table{max-width:100%;}
.split-box{border:1px solid var(--border);border-radius:12px;padding:24px 28px;background:var(--bg-sub);}
.example-box{border:1px solid var(--border);border-radius:12px;padding:24px 28px;background:var(--bg-sub);margin:0 0 24px;max-width:820px;}
.example-box h4.h4-note{margin:0 0 14px;}
.example-box pre.cont-code{background:transparent;border:none;padding:0;margin:0;max-width:none;}
.table-box{border:1px solid var(--border);border-radius:12px;padding:24px 28px;background:var(--bg-sub);margin:0 0 24px;max-width:1100px;}
.table-box .cont-table-wrap{margin-bottom:0;}
.table-box table.cont-table{max-width:100%;}
.table-box p:last-child{margin:16px 0 0;}
.table-box h4:first-child{margin-top:0;}
.table-box tr.note-row td{font-size:13px;font-style:italic;color:var(--text-muted);padding-top:16px;border-bottom:none;}
.flow-diagram{position:relative;display:flex;gap:32px;margin:0 0 32px;max-width:1120px;}
.flow-diagram::before{content:"";position:absolute;top:6px;left:7px;right:7px;height:2px;background:var(--border-strong);}
.flow-stage{position:relative;flex:1 1 0;min-width:0;}
.flow-node{width:14px;height:14px;border-radius:50%;background:var(--text);position:relative;margin-bottom:16px;}
.flow-stage-label{font-size:13px;font-weight:600;color:var(--text-sub);margin-bottom:10px;}
.flow-stage-items{list-style:none;margin:0;padding:0;font-size:15px;color:var(--text);line-height:1.6;}
.flow-stage-items li{margin-bottom:6px;}
.flow-stage-items li:last-child{margin-bottom:0;}
.flow-track-text{font-size:15px;line-height:1.7;color:var(--text);margin:0;}
.cont-img-large{max-width:700px;}
.cont-img-large .cont-fig{max-width:100%;}
.cont-img-large .cont-fig img{max-width:100%;max-height:none;width:100%;height:auto;}
.split-box h4{font-size:16px;font-weight:600;margin:0 0 12px;}
.split-box p,.split-box ul.cont-list li{font-size:16px;color:var(--text-sub);}
.split-box p:last-child,.split-box ul:last-child{margin-bottom:0;}
.split-box > h4:not(:first-child){margin-top:28px;padding-top:24px;border-top:1px solid var(--border);}

/* 표 좌측 / 보충 노트 박스 우측 (역할표 등) */
.table-note-layout{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,680px);gap:56px;align-items:start;margin-bottom:8px;max-width:1600px;}

/* 좌우 2단 카드 (참여자뷰/전경CCTV, 카메라 설치/촬영영역 표시 등) */
.two-col-cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:40px;margin-bottom:8px;max-width:1700px;}
.two-card{
  min-width:0;border:1px solid var(--border);border-radius:12px;
  background:var(--bg-sub);padding:28px 32px;
}
.two-card h4{margin-top:0;}
.two-card p{font-weight:500;}
.two-card ul.cont-list li{font-weight:300;}
ul.check-marks{list-style:none;padding-left:0;}
ul.check-marks li{position:relative;padding-left:26px;}
ul.check-marks li::before{content:"✓";position:absolute;left:0;top:0;color:var(--text-sub);font-weight:600;}

/* 참고성 코멘트 — 본문과 분리된 작은 박스 */
.note-aside{
  border:1px solid var(--border);border-radius:12px;padding:18px 22px;
  background:var(--bg-sub);max-width:640px;margin:8px 0 24px;
}
.note-aside h4{font-size:14px;margin:0 0 8px;color:var(--text-sub);}
.note-aside p{font-size:14px;color:var(--text-sub);margin:0;max-width:100%;}

@media (max-width:900px){
  body{flex-direction:column;font-size:17px;}
  #sidebar{position:relative;width:100%;height:auto;max-height:44vh;}
  #main{padding:0 24px 120px;max-width:100%;}
  .part-title{font-size:38px;}
  .subpage h2{font-size:22px;}
  .hero-cover h1{font-size:32px;}
  .split-layout{grid-template-columns:1fr;gap:24px;}
  .two-col-cards{grid-template-columns:1fr;gap:32px;}
  .table-note-layout{grid-template-columns:1fr;gap:24px;}
  .flow-diagram{flex-direction:column;gap:20px;}
  .flow-diagram::before{display:none;}
}
"""

TEMPLATE = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>사용자 조사 환경 셋팅 가이드</title>
<style>__CSS__</style>
</head>
<body>

<nav id="sidebar">
  <div class="brand">사용자 조사 환경 셋팅 가이드<small>바이널씨 · v1.00</small></div>
  <input id="search" type="text" placeholder="검색 (예: 마이크, 체크리스트)">
  __NAV__
</nav>

<main id="main">
  __PAGES__
</main>

<script>
const pageIds = __NAV_DATA__;
const navLinks = Array.from(document.querySelectorAll('#sidebar a[data-page]'));
const sections = pageIds.map(id => document.querySelector('[data-page="' + id + '"]')).filter(Boolean);
const linkById = {};
navLinks.forEach(a => { linkById[a.dataset.page] = a; });

function expandGroupOf(id){
  const el = linkById[id];
  const block = el && el.closest('.nav-group-block');
  if(block) block.classList.add('expanded');
}

function setActive(id){
  navLinks.forEach(a => a.classList.toggle('active', a.dataset.page === id));
  const active = linkById[id];
  if(active) active.scrollIntoView({block:'nearest'});
  expandGroupOf(id);
}

const io = new IntersectionObserver((entries) => {
  let best = null, bestTop = Infinity;
  entries.forEach(e => {
    if(e.isIntersecting){
      const top = Math.abs(e.boundingClientRect.top);
      if(top < bestTop){ bestTop = top; best = e.target; }
    }
  });
  if(best) setActive(best.dataset.page);
}, { rootMargin: '-10% 0px -70% 0px', threshold: [0, 0.1, 0.5] });

sections.forEach(s => io.observe(s));

navLinks.forEach(a=>{
  a.addEventListener('click', ()=> setActive(a.dataset.page));
});

document.querySelectorAll('.nav-chevron').forEach(ch=>{
  ch.addEventListener('click', e=>{
    e.preventDefault();
    e.stopPropagation();
    const block = ch.closest('.nav-group-block');
    if(block) block.classList.toggle('expanded');
  });
});

document.getElementById('search').addEventListener('input', e=>{
  const q = e.target.value.trim().toLowerCase();
  document.querySelectorAll('#sidebar .nav-item, #sidebar .nav-cover, #sidebar .nav-group').forEach(a=>{
    a.style.display = (!q || a.textContent.toLowerCase().includes(q)) ? '' : 'none';
  });
  document.querySelectorAll('#sidebar .nav-section-label').forEach(l=>{
    l.style.display = q ? 'none' : '';
  });
  document.querySelectorAll('.nav-group-block').forEach(block=>{
    block.classList.toggle('expanded', !!q);
  });
  if(!q){
    const active = navLinks.find(a => a.classList.contains('active'));
    if(active) expandGroupOf(active.dataset.page);
  }
});

if(pageIds.length) setActive(pageIds[0]);
</script>
</body>
</html>
"""

final_html = (
    TEMPLATE.replace("__CSS__", CSS)
    .replace("__NAV__", nav_html)
    .replace("__PAGES__", pages_html)
    .replace("__NAV_DATA__", nav_data)
)

with open(OUT, "w", encoding="utf-8") as f:
    f.write(final_html)

print(f"완료: {OUT}")
print(f"총 {len(final_html):,}자")
