import requests
import xml.etree.ElementTree as ET
from urllib.parse import quote
import re
import os
import unicodedata
from collections import defaultdict

OC = os.getenv("OC", "chetera")
BASE = "http://www.law.go.kr"

def get_law_list_from_api(query):
    exact_query = f'"{query}"'
    encoded_query = quote(exact_query)
    page = 1
    laws = []
    while True:
        url = f"{BASE}/DRF/lawSearch.do?OC={OC}&target=law&type=XML&display=100&page={page}&search=2&knd=A0002&query={encoded_query}"
        res = requests.get(url, timeout=10)
        res.encoding = 'utf-8'
        if res.status_code != 200:
            break
        root = ET.fromstring(res.content)
        for law in root.findall("law"):
            laws.append({
                "법령명": law.findtext("법령명한글", "").strip(),
                "MST": law.findtext("법령일련번호", "")
            })
        total_count = int(root.findtext("totalCnt", "0"))
        if len(laws) >= total_count:
            break
        page += 1
    return laws

def get_law_text_by_mst(mst):
    url = f"{BASE}/DRF/lawService.do?OC={OC}&target=law&MST={mst}&type=XML"
    try:
        res = requests.get(url, timeout=10)
        res.encoding = 'utf-8'
        return res.content if res.status_code == 200 else None
    except:
        return None

def clean(text):
    return re.sub(r"\s+", "", text or "")

def 조사_을를(word):
    if not word:
        return "을"
    code = ord(word[-1]) - 0xAC00
    jong = code % 28
    return "를" if jong == 0 else "을"

def 조사_으로로(word):
    if not word:
        return "으로"
    code = ord(word[-1]) - 0xAC00
    jong = code % 28
    return "로" if jong == 0 or jong == 8 else "으로"

def highlight(text, keyword):
    return text.replace(keyword, f"<span style='color:red'>{keyword}</span>") if text else ""

def remove_unicode_number_prefix(text):
    return re.sub(r"^[①-⑳]+", "", text)

def normalize_number(text):
    try:
        return str(int(unicodedata.numeric(text)))
    except:
        return text

def make_article_number(조문번호, 조문가지번호):
    if 조문가지번호 and 조문가지번호 != "0":
        return f"제{조문번호}조의{조문가지번호}"
    else:
        return f"제{조문번호}조"

def extract_chunks(text, keyword):
    match = re.search(rf"(\w*{keyword}\w*)", text)
    return match.group(1) if match else None

def extract_locations(xml_data, keyword):
    tree = ET.fromstring(xml_data)
    articles = tree.findall(".//조문단위")
    keyword_clean = clean(keyword)
    locations = []

    for article in articles:
        조번호 = article.findtext("조문번호", "").strip()
        조가지번호 = article.findtext("조문가지번호", "").strip()
        조제목 = article.findtext("조문제목", "") or ""
        조내용 = article.findtext("조문내용", "") or ""

        조식별 = make_article_number(조번호, 조가지번호)

        if keyword_clean in clean(조제목):
            locations.append((조식별, None, None, None, 조제목.strip()))
        if keyword_clean in clean(조내용):
            locations.append((조식별, None, None, None, 조내용.strip()))

        for 항 in article.findall("항"):
            항번호 = normalize_number(항.findtext("항번호", "").strip())
            항내용 = 항.findtext("항내용") or ""
            has_항번호 = 항번호.isdigit()
            if keyword_clean in clean(항내용) and has_항번호:
                locations.append((조식별, 항번호, None, None, 항내용.strip()))
            for 호 in 항.findall("호"):
                raw_호번호 = 호.findtext("호번호", "").strip().replace(".", "")
                호내용 = 호.findtext("호내용") or ""
                if keyword_clean in clean(호내용):
                    locations.append((조식별, 항번호, raw_호번호, None, 호내용.strip()))
                for 목 in 호.findall("목"):
                    raw_목번호 = 목.findtext("목번호", "").strip().replace(".", "")
                    목내용 = 목.findtext("목내용") or ""
                    if keyword_clean in clean(목내용):
                        locations.append((조식별, 항번호, raw_호번호, raw_목번호, 목내용.strip()))

    return locations

def format_location(loc):
    조, 항, 호, 목, 텍스트 = loc
    parts = [조]
    if 항:
        parts.append(f"제{항}항")
    if 호:
        parts.append(f"제{호}호")
    if 목:
        parts.append(f"제{목}목")
    return "".join(parts)

def run_search_logic(query, unit):
    result_dict = {}
    keyword_clean = clean(query)

    for law in get_law_list_from_api(query):
        mst = law["MST"]
        xml_data = get_law_text_by_mst(mst)
        if not xml_data:
            continue

        tree = ET.fromstring(xml_data)
        articles = tree.findall(".//조문단위")
        law_results = []

        for article in articles:
            조내용 = article.findtext("조문내용") or ""
            항들 = article.findall("항")
            출력덩어리 = []
            조출력됨 = False

            if 조내용:
                출력덩어리.append(highlight(조내용, query))
                조출력됨 = True

            for 항 in 항들:
                항내용 = 항.findtext("항내용") or ""
                if 항내용:
                    출력덩어리.append(highlight(항내용, query))

                for 호 in 항.findall("호"):
                    호내용 = 호.findtext("호내용") or ""
                    if 호내용:
                        출력덩어리.append(highlight(호내용, query))

                    for 목 in 호.findall("목"):
                        목내용_list = 목.findall("목내용")
                        if 목내용_list:
                            for m in 목내용_list:
                                if m.text:
                                    for line in m.text.splitlines():
                                        if line.strip():
                                            출력덩어리.append(highlight(line.strip(), query))

            if 출력덩어리 and 조출력됨:
                law_results.append("<br>".join(출력덩어리))

        if law_results:
            result_dict[law["법령명"]] = law_results

    return result_dict

def run_amendment_logic(find_word, replace_word):
    을를 = 조사_을를(find_word)
    으로로 = 조사_으로로(replace_word)
    amendment_results = []

    for idx, law in enumerate(get_law_list_from_api(find_word)):
        law_name = law["법령명"]
        mst = law["MST"]
        xml = get_law_text_by_mst(mst)
        if not xml:
            continue

        locations = extract_locations(xml, find_word)
        if not locations:
            continue

        문장들 = []
        덩어리별 = defaultdict(list)

        for loc in locations:
            조, 항, 호, 목, 텍스트 = loc
            덩어리 = extract_chunks(텍스트, find_word)
            if 덩어리:
                덩어리별[덩어리].append(loc)

        for chunk, locs in 덩어리별.items():
            각각 = "각각 " if len(locs) > 1 else ""
            loc_str = ", ".join([format_location(l) for l in locs[:-1]]) + (" 및 " if len(locs) > 1 else "") + format_location(locs[-1])
            new_chunk = chunk.replace(find_word, replace_word)

            # 조사나 어미 무시 규칙 적용 (간단화 버전)
            chunk_core = re.sub(r"(에|에서|의|으로|로|과|와|을|를|이|가)$", "", chunk)
            new_chunk_core = re.sub(r"(에|에서|의|으로|로|과|와|을|를|이|가)$", "", new_chunk)

            if chunk_core != new_chunk_core:
                # 덩어리를 더 크게 잡아야 하는 경우
                문장들.append(f"{loc_str} 중 “{chunk}”{을를} {각각}“{new_chunk}”{으로로} 한다.")
            else:
                # 그냥 단어만 교체해도 되는 경우
                문장들.append(f"{loc_str} 중 “{find_word}”{을를} {각각}“{replace_word}”{으로로} 한다.")

        if 문장들:
            if idx < 20:
                amendment = f"{chr(9312 + idx)} {law_name} 일부를 다음과 같이 개정한다.<br>" + "<br>".join(문장들)
            else:
                amendment = f"{idx+1} {law_name} 일부를 다음과 같이 개정한다.<br>" + "<br>".join(문장들)
            amendment_results.append(amendment)

    return amendment_results if amendment_results else ["⚠️ 개정 대상 조문이 없습니다."]


