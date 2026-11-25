cd /Users/aysedemirelli/Desktop/akilli-kaynak-asistani
cat << 'EOF' > app.py
import json
import re
from collections import Counter
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import streamlit as st

st.set_page_config(
    page_title="Akıllı Kaynak & Metin Asistanı Pro++",
    page_icon="⚡",
    layout="wide",
)

STOP_WORDS = {
    "ve", "ile", "bir", "bu", "şu", "o", "için", "olan", "en", "az",
    "var", "yok", "gibi", "kadar", "da", "de", "ki", "hem", "ya",
    "ama", "ancak", "lakin", "fakat", "göre", "birlikte", "olarak",
    "daha", "çok", "ise", "mi", "mı", "mu", "mü", "the", "and", "of",
    "to", "in", "is", "for", "with", "on", "that", "as", "are", "from",
    "birçok", "bazı", "her", "tüm", "veya", "ya da", "çünkü", "sonra",
    "önce", "kendi", "bunu", "şunu", "ona", "buna", "şuna", "olarak",
}

POS_WORDS = {
    "başarılı", "hızlı", "verimli", "gelişmiş", "avantaj", "faydalı",
    "güvenli", "kolay", "etkili", "olumlu", "büyüme", "inovasyon",
    "çözüm", "iyileştirme", "doğru", "güçlü", "artış", "destek",
}

NEG_WORDS = {
    "sorun", "risk", "hata", "eksik", "yavaş", "kısıt", "zorluk",
    "olumsuz", "kayıp", "maliyet", "engelleme", "zayıf", "tehlike",
    "karmaşık", "gecikme", "bağımlılık", "engel", "başarısız",
}

DEFAULT_SOURCE_TEXT = (
    "Dijital kaynak tarama sistemleri uzun metinlerden hızlı bilgi çıkarmayı sağlar. "
    "Web sayfalarından BeautifulSoup ve Selenium yöntemleriyle elde edilen içerikler temizlenip "
    "tokenlara ayrıldığında analiz süreci daha güvenilir hale gelir. Otomatik özetleme ve anahtar "
    "kavram çıkarımı, kullanıcının metin içindeki kritik bilgileri saniyeler içinde bulmasına "
    "yardımcı olur. Ağ kısıtları, dinamik sayfa yüklemeleri ve yapı farklılıkları ise veri toplama "
    "adımlarında dikkat edilmesi gereken temel zorluklar arasındadır."
)

SAMPLE_ANNOUNCEMENT_TEXT = (
    "Başvuru ve değerlendirme sürecinde adayların belirlenen kriterleri eksiksiz sağlaması gerekir. "
    "Ön inceleme aşamasında eksik belge veya hatalı bilgi tespit edilmesi durumunda süreçte "
    "gecikme ve risk oluşabilir. Ancak düzenli planlama, net ölçütler ve zamanında takip ile "
    "süreç daha hızlı ve verimli şekilde tamamlanır."
)

SAMPLE_COMPARE_TEXT = (
    "Web kazıma ve metin madenciliği hatları, ham HTML içeriklerini temizleyerek anlamlı "
    "özetlere ve anahtar kavramlara dönüştürür. Farklı kazıma yöntemleri dinamik içerik, "
    "hız ve yapı ayrıştırma açısından kendi avantaj ve kısıtlarına sahiptir."
)

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
}


def tr_lower(text: str) -> str:
    return text.replace("İ", "i").replace("I", "ı").lower()


def extract_tokens(text: str, filter_stopwords: bool = True) -> list[str]:
    words = re.findall(r"\b[a-zçğıöşü0-9]+\b", tr_lower(text))
    cleaned = [w for w in words if len(w) > 2]
    if filter_stopwords:
        cleaned = [w for w in cleaned if w not in STOP_WORDS]
    return cleaned


def extract_ngrams(tokens: list[str], n: int = 2, limit: int = 8) -> list[tuple[str, int]]:
    if len(tokens) < n or n < 1:
        return []
    grams = [" ".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]
    return Counter(grams).most_common(limit)


def split_sentences(text: str) -> list[str]:
    # Nokta, ünlem, soru işareti veya satır sonlarına göre cümlelere ayır
    raw_lines = [line.strip() for line in text.splitlines() if line.strip()]
    sentences = []
    for line in raw_lines:
        parts = re.split(r"(?<=[.!?])\s+", line)
        for p in parts:
            cleaned = re.sub(r"\s+", " ", p).strip()
            if len(cleaned) >= 12:
                sentences.append(cleaned)
    return sentences


def fetch_web_content(url: str, scrape_method: str) -> dict:
    clean_url = url.strip()
    if not clean_url.startswith(("http://", "https://")):
        clean_url = "https://" + clean_url

    html_text = None
    note = None
    used_method = scrape_method

    if scrape_method == "Selenium (Dinamik Tarayıcı)":
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options

            opts = Options()
            opts.add_argument("--headless=new")
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-dev-shm-usage")
            driver = webdriver.Chrome(options=opts)
            try:
                driver.set_page_load_timeout(15)
                driver.get(clean_url)
                html_text = driver.page_source
            finally:
                driver.quit()
        except Exception as exc:
            note = f"Selenium kullanılamadı ({exc}); BeautifulSoup ile devam edildi."
            used_method = "BeautifulSoup (Fallback)"

    if html_text is None:
        try:
            res = requests.get(clean_url, headers=BROWSER_HEADERS, timeout=12)
            res.encoding = res.apparent_encoding or "utf-8"
            res.raise_for_status()
            html_text = res.text
        except Exception as exc:
            return {
                "title": "Erişim Hatası",
                "text": st.session_state.get("working_text", DEFAULT_SOURCE_TEXT),
                "method": "Bağlantı Engellendi",
                "note": f"URL çekilemedi ({exc}). Site bot koruması kullanıyor olabilir; sayfadaki metni kopyalayıp aşağıdaki kutuya yapıştırabilirsin.",
                "error": True,
                "headings_count": 0,
                "paragraphs_count": 0,
            }

    soup = BeautifulSoup(html_text, "html.parser")
    for tag in soup(["script", "style", "noscript", "nav", "footer", "aside", "header", "form"]):
        tag.decompose()

    title = soup.title.string.strip() if soup.title and soup.title.string else clean_url
    container = soup.find("article") or soup.find("main") or soup.body or soup

    all_headings = [
        h.get_text(" ", strip=True)
        for h in container.find_all(["h1", "h2", "h3"])
        if len(h.get_text(" ", strip=True)) > 3
    ]
    all_paras = [
        p.get_text(" ", strip=True)
        for p in container.find_all("p")
        if len(p.get_text(" ", strip=True)) > 25
    ]

    if scrape_method == "BeautifulSoup (Başlık + Yapı Odaklı)":
        blocks = [
            f"[{el.name.upper()}] {el.get_text(' ', strip=True)}"
            if el.name in {"h1", "h2", "h3"}
            else el.get_text(" ", strip=True)
            for el in container.find_all(["h1", "h2", "h3", "p", "li"])
            if len(el.get_text(" ", strip=True)) > 20
        ]
    else:
        blocks = all_paras

    # Eğer <p> etiketleri boşsa div/article içindeki düz paragraf bloklarını yakala
    if not blocks:
        fallback_lines = [
            line.strip()
            for line in container.get_text("\n").splitlines()
            if len(line.strip()) > 35
        ]
        blocks = fallback_lines[:40]

    # Tekrar eden satırları temizle
    seen = set()
    unique_blocks = []
    for b in blocks:
        if b not in seen:
            seen.add(b)
            unique_blocks.append(b)

    joined = "\n\n".join(unique_blocks[:45]).strip()
    if len(joined) < 40:
        return {
            "title": title,
            "text": st.session_state.get("working_text", DEFAULT_SOURCE_TEXT),
            "method": used_method,
            "note": "Bu sayfa içeriğini JavaScript ile sonradan yüklüyor olabilir (boş metin döndü). Metni kopyalayıp aşağıdaki kutuya yapıştırarak analiz edebilirsin.",
            "error": True,
            "headings_count": len(all_headings),
            "paragraphs_count": len(all_paras),
        }

    return {
        "title": title,
        "text": joined,
        "method": used_method,
        "note": note or f"'{title}' başarıyla çekildi ({len(joined)} karakter).",
        "error": False,
        "headings_count": len(all_headings),
        "paragraphs_count": len(all_paras),
    }


def score_sentences(text: str) -> list[dict]:
    sents = split_sentences(text)
    freq = Counter(extract_tokens(text, filter_stopwords=True))
    scored = []
    for idx, sent in enumerate(sents):
        s_tokens = extract_tokens(sent, filter_stopwords=True)
        if not s_tokens:
            continue
        # Uzun cümlelerin haksız puan şişirmesini önlemek için normalize skor
        base_score = sum(freq.get(tok, 0) for tok in s_tokens) / (len(s_tokens) ** 0.4)
        lead_bonus = 1.5 if idx == 0 else 0.0
        total = round(base_score + lead_bonus, 2)
        scored.append({"index": idx + 1, "score": total, "sentence": sent})
    return scored


def summarize_text(text: str, sentence_count: int = 2) -> str:
    clean = text.strip()
    if not clean:
        return "Özetlenecek metin bulunamadı."
    scored = score_sentences(clean)
    if not scored:
        return clean[:350] + ("..." if len(clean) > 350 else "")
    top_sents = sorted(scored, key=lambda x: (-x["score"], x["index"]))[:sentence_count]
    return " ".join(item["sentence"] for item in sorted(top_sents, key=lambda x: x["index"]))


def extract_key_bullets(text: str) -> list[str]:
    scored = score_sentences(text)
    if not scored:
        return [text[:200]] if text.strip() else []
    ranked = sorted(scored, key=lambda x: (-x["score"], x["index"]))[:4]
    return [item["sentence"] for item in sorted(ranked, key=lambda x: x["index"])]


def detect_tone_details(tokens: list[str]) -> tuple[str, list[str], list[str]]:
    pos_found = sorted({t for t in tokens if t in POS_WORDS})
    neg_found = sorted({t for t in tokens if t in NEG_WORDS})
    pos_score = sum(1 for t in tokens if t in POS_WORDS)
    neg_score = sum(1 for t in tokens if t in NEG_WORDS)
    if pos_score > neg_score:
        label = "Pozitif Eğilimli"
    elif neg_score > pos_score:
        label = "Risk / Sorun Odaklı"
    else:
        label = "Dengeli / Bilgilendirici"
    return label, pos_found, neg_found


def compare_two_texts(text_a: str, text_b: str, filter_sw: bool = True) -> dict:
    set_a = set(extract_tokens(text_a, filter_stopwords=filter_sw))
    set_b = set(extract_tokens(text_b, filter_stopwords=filter_sw))
    union = set_a.union(set_b)
    inter = sorted(set_a.intersection(set_b))
    only_a = sorted(set_a - set_b)
    only_b = sorted(set_b - set_a)
    jaccard = round((len(inter) / len(union)) * 100, 1) if union else 0.0
    return {
        "jaccard": jaccard,
        "common": inter[:15],
        "only_a": only_a[:12],
        "only_b": only_b[:12],
    }


def optional_llm_refine(prompt_text: str, api_key: str) -> str | None:
    if not api_key.strip():
        return None
    try:
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key.strip()}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "Kısa, net ve Türkçe yanıt ver."},
                    {"role": "user", "content": prompt_text[:3000]},
                ],
                "temperature": 0.3,
            },
            timeout=12,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


def answer_query(query: str, text: str, api_key: str = "") -> tuple[str, str]:
    llm_reply = optional_llm_refine(
        f"Şu metne dayanarak soruyu yanıtla:\nMetin:\n{text[:2500]}\n\nSoru: {query}",
        api_key,
    )
    if llm_reply:
        return llm_reply, "Harici LLM API"

    q_set = set(extract_tokens(query, filter_stopwords=True))
    if not q_set:
        return "Lütfen metinle ilgili en az bir anahtar kelime yaz.", "Yerel NLP Eşleştirme"
    scored_sents = []
    for sent in split_sentences(text):
        s_tokens = extract_tokens(sent, filter_stopwords=True)
        hits = len(q_set.intersection(s_tokens))
        if hits > 0:
            scored_sents.append((hits, sent))
    if not scored_sents:
        return "Bu soruya doğrudan karşılık veren bir cümle metinde bulunamadı.", "Yerel NLP Eşleştirme"
    scored_sents.sort(key=lambda x: -x[0])
    top_matches = [s for _, s in scored_sents[:2]]
    return " ".join(top_matches), "Yerel NLP Eşleştirme"


def search_in_text(keyword: str, text: str) -> list[dict]:
    q_clean = tr_lower(keyword.strip())
    if not q_clean:
        return []
    results = []
    for idx, sent in enumerate(split_sentences(text), start=1):
        count = tr_lower(sent).count(q_clean)
        if count > 0:
            results.append({"Cümle No": idx, "Eşleşme": count, "Cümle": sent})
    results.sort(key=lambda x: (-x["Eşleşme"], x["Cümle No"]))
    return results


def build_markdown_report(
    title: str,
    method: str,
    tone: str,
    summary: str,
    keywords: list[tuple[str, int]],
    bigrams: list[tuple[str, int]],
    trigrams: list[tuple[str, int]],
    qa_list: list[tuple[str, str]],
) -> str:
    lines = [
        f"# Kaynak Analiz Raporu: {title}",
        f"- **Tarih:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"- **Kullanılan Kazıma Yöntemi:** {method}",
        f"- **Genel Metin Tonu:** {tone}",
        "",
        "## Otomatik Özet",
        summary,
        "",
        "## Öne Çıkan Anahtar Kelimeler",
        ", ".join(f"{w} ({c})" for w, c in keywords) if keywords else "Bulunamadı",
        "",
        "## İkili Kavram Öbekleri (Bigram)",
        ", ".join(f"{b} ({c})" for b, c in bigrams) if bigrams else "Bulunamadı",
        "",
        "## Üçlü Kavram Öbekleri (Trigram)",
        ", ".join(f"{t} ({c})" for t, c in trigrams) if trigrams else "Bulunamadı",
    ]
    if qa_list:
        lines.extend(["", "## Soru & Cevap Geçmişi"])
        for q, a in qa_list:
            lines.append(f"- **Soru:** {q}\n  - **Yanıt:** {a}")
    return "\n".join(lines)


st.title("⚡ Akıllı Kaynak & Metin Asistanı")
st.caption("Web scraping, NLP ön işleme ve bağlamsal analiz altyapısıyla çalışan çok yönlü kaynak asistanı")

if "assistant_data" not in st.session_state:
    st.session_state["assistant_data"] = {
        "title": "Başlangıç Kaynağı",
        "text": DEFAULT_SOURCE_TEXT,
        "method": "Örnek Metin",
        "note": None,
        "error": False,
        "headings_count": 0,
        "paragraphs_count": 1,
    }
if "working_text" not in st.session_state:
    st.session_state["working_text"] = DEFAULT_SOURCE_TEXT
if "history" not in st.session_state:
    st.session_state["history"] = []
if "qa_history" not in st.session_state:
    st.session_state["qa_history"] = []
if "ab_comparison" not in st.session_state:
    st.session_state["ab_comparison"] = None

with st.sidebar:
    st.subheader("Kazıma & Analiz Ayarları")
    scrape_method = st.radio(
        "Veri Toplama Yöntemi",
        [
            "BeautifulSoup (Paragraf Odaklı)",
            "BeautifulSoup (Başlık + Yapı Odaklı)",
            "Selenium (Dinamik Tarayıcı)",
        ],
    )
    apply_stopwords = st.checkbox("Stop-words temizliği uygula", value=True)
    summary_len = st.slider("Özet cümle sayısı", 1, 5, 2)
    top_n = st.slider("Anahtar kelime adedi", 5, 15, 8)

    st.markdown("---")
    st.subheader("Hızlı Senaryo Metinleri")
    if st.button("Teknik Kaynak Örneği", use_container_width=True):
        st.session_state["assistant_data"] = {
            "title": "Teknik Kaynak Senaryosu",
            "text": DEFAULT_SOURCE_TEXT,
            "method": "Hazır Örnek",
            "note": "Teknik kaynak örnek metni yüklendi.",
            "error": False,
            "headings_count": 1,
            "paragraphs_count": 2,
        }
        st.session_state["working_text"] = DEFAULT_SOURCE_TEXT
        st.rerun()

    if st.button("Duyuru / Süreç Örneği", use_container_width=True):
        st.session_state["assistant_data"] = {
            "title": "Duyuru & Kriter Senaryosu",
            "text": SAMPLE_ANNOUNCEMENT_TEXT,
            "method": "Hazır Örnek",
            "note": "Duyuru ve kriter örnek metni yüklendi.",
            "error": False,
            "headings_count": 1,
            "paragraphs_count": 1,
        }
        st.session_state["working_text"] = SAMPLE_ANNOUNCEMENT_TEXT
        st.rerun()

    with st.expander("İsteğe Bağlı Harici LLM API"):
        api_key_input = st.text_input("OpenAI API Key (Opsiyonel)", type="password")
        st.caption("Boş bırakılırsa tüm analizler yerel NLP motoruyla anında çalışır.")

    if st.session_state["history"]:
        st.markdown("---")
        st.subheader("Oturum Geçmişi")
        for idx, item in enumerate(reversed(st.session_state["history"][-5:])):
            if st.button(f"📄 {item['title'][:24]}", key=f"hist_{idx}"):
                st.session_state["assistant_data"] = item
                st.session_state["working_text"] = item["text"]
                st.rerun()

url_col, btn_col1, btn_col2 = st.columns([3.5, 1.2, 1.3])
with url_col:
    url_val = st.text_input(
        "Web Sayfası Bağlantısı (URL)",
        value="https://tr.wikipedia.org/wiki/Yapay_zek%C3%A2",
        placeholder="https://...",
    )
with btn_col1:
    st.write("")
    st.write("")
    fetch_clicked = st.button("Kaynağı Çek", type="primary", use_container_width=True)
with btn_col2:
    st.write("")
    st.write("")
    ab_clicked = st.button("A/B Yöntem Kıyasla", use_container_width=True)

if fetch_clicked and url_val.strip():
    with st.spinner("Web sayfasından içerik çekiliyor..."):
        fetched_dict = fetch_web_content(url_val, scrape_method)
    st.session_state["assistant_data"] = fetched_dict
    if not fetched_dict.get("error"):
        st.session_state["working_text"] = fetched_dict["text"]
        st.session_state["history"].append(fetched_dict)
    st.rerun()

if ab_clicked and url_val.strip():
    with st.spinner("İki kazıma yöntemi karşılaştırılıyor..."):
        res_p = fetch_web_content(url_val, "BeautifulSoup (Paragraf Odaklı)")
        res_h = fetch_web_content(url_val, "BeautifulSoup (Başlık + Yapı Odaklı)")
    st.session_state["ab_comparison"] = {"para": res_p, "head": res_h}

current = st.session_state["assistant_data"]
status_msg = current.get("note")

if status_msg:
    if current.get("error"):
        st.warning(status_msg)
    else:
        st.success(status_msg)

if st.session_state["ab_comparison"]:
    ab_p = st.session_state["ab_comparison"]["para"]
    ab_h = st.session_state["ab_comparison"]["head"]
    with st.expander("⚖️ A/B Kazıma Yöntemi Karşılaştırma Sonucu", expanded=True):
        ab_c1, ab_c2 = st.columns(2)
        with ab_c1:
            st.markdown("**Paragraf Odaklı (`p`)**")
            st.caption(f"Karakter: {len(ab_p['text'])} | Token: {len(extract_tokens(ab_p['text'], apply_stopwords))}")
            st.write(summarize_text(ab_p["text"], sentence_count=2))
        with ab_c2:
            st.markdown("**Başlık + Yapı Odaklı (`h1-h3` + `p`)**")
            st.caption(f"Karakter: {len(ab_h['text'])} | Token: {len(extract_tokens(ab_h['text'], apply_stopwords))}")
            st.write(summarize_text(ab_h["text"], sentence_count=2))

with st.form("text_analysis_form", clear_on_submit=False):
    text_box_val = st.text_area(
        "Çalışma Metni (Paragrafını buraya yapıştırıp aşağıdaki 'Metni Analiz Et & Özetle' butonuna bas)",
        value=st.session_state["working_text"],
        height=190,
    )
    f_col1, f_col2 = st.columns([1.4, 3.6])
    with f_col1:
        analyze_submitted = st.form_submit_button("✨ Metni Analiz Et & Özetle", type="primary", use_container_width=True)
    with f_col2:
        st.caption("İpucu: URL çekemediğin korumalı sayfalardaki metni buraya yapıştırıp doğrudan özetleyebilirsin.")

if analyze_submitted:
    st.session_state["working_text"] = text_box_val
    st.session_state["assistant_data"]["title"] = "Manuel Yapıştırılan Metin"
    st.session_state["assistant_data"]["method"] = "Doğrudan Metin Girişi"
    st.session_state["assistant_data"]["note"] = "Yapıştırdığın metin analiz edildi ve özet güncellendi."
    st.session_state["assistant_data"]["error"] = False
    st.rerun()

active_text = st.session_state["working_text"]
src_title = current["title"]
active_method = current["method"]

raw_words = extract_tokens(active_text, filter_stopwords=False)
tokens = extract_tokens(active_text, filter_stopwords=apply_stopwords)
freq = Counter(tokens)
bigrams = extract_ngrams(tokens, n=2, limit=8)
trigrams = extract_ngrams(tokens, n=3, limit=6)
tone_label, pos_hits_list, neg_hits_list = detect_tone_details(tokens)
vocab_richness = round((len(set(tokens)) / len(tokens)) * 100, 1) if tokens else 0.0
read_seconds = max(1, round(len(raw_words) / 3.2))

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Kaynak", src_title[:22] + ("..." if len(src_title) > 22 else ""))
m2.metric("Yöntem", active_method.split()[0])
m3.metric("İşlenen Token", len(tokens))
m4.metric("Kelime Çeşitliliği", f"%{vocab_richness}")
m5.metric("Genel Ton", tone_label)

summary_output = summarize_text(active_text, sentence_count=summary_len)
top_words = freq.most_common(top_n)

# Özeti sekmelerin de üstünde hemen görünür kılalım
st.subheader("📌 Anlık Otomatik Özet")
st.info(summary_output)

tab_ozet, tab_analiz, tab_soru, tab_arka_plan = st.tabs([
    "🎯 Kritik Maddeler & Ton",
    "📊 Kavram, N-Gram & Benzerlik",
    "💬 Akıllı Soru-Cevap",
    "🛠️ Arka Plan NLP & Kazıma",
])

with tab_ozet:
    st.subheader("Öne Çıkan Kritik Noktalar")
    for bullet in extract_key_bullets(active_text):
        st.markdown(f"- {bullet}")

    st.caption(
        f"Tahmini okuma süresi: ~{read_seconds} saniye | "
        f"Başlık etiketi: {current.get('headings_count', 0)} | "
        f"Paragraf etiketi: {current.get('paragraphs_count', 0)}"
    )
    st.caption(
        f"Pozitif ipuçları: {', '.join(pos_hits_list) if pos_hits_list else 'Yok'} | "
        f"Risk/Negatif ipuçları: {', '.join(neg_hits_list) if neg_hits_list else 'Yok'}"
    )

with tab_analiz:
    c_left, c_mid, c_right = st.columns(3)
    with c_left:
        st.subheader("Anahtar Kelimeler")
        if top_words:
            st.dataframe(
                [{"Kelime": w, "Frekans": c} for w, c in top_words],
                use_container_width=True,
                hide_index=True,
            )
    with c_mid:
        st.subheader("İkili Öbekler (Bigram)")
        if bigrams:
            st.dataframe(
                [{"Bigram": b, "Tekrar": c} for b, c in bigrams],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.write("Yeterli ikili öbek bulunamadı.")
    with c_right:
        st.subheader("Üçlü Öbekler (Trigram)")
        if trigrams:
            st.dataframe(
                [{"Trigram": t, "Tekrar": c} for t, c in trigrams],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.write("Yeterli üçlü öbek bulunamadı.")

    st.markdown("---")
    st.subheader("Metin İçi Kavram / Kelime Arama")
    search_term = st.text_input("Metin içinde ara:", placeholder="Örn: veri, model, analiz...")
    if search_term.strip():
        matches = search_in_text(search_term, active_text)
        if matches:
            st.dataframe(matches, use_container_width=True, hide_index=True)
        else:
            st.write("Bu ifadeyi içeren cümle bulunamadı.")

    st.markdown("---")
    st.subheader("İkinci Kaynak / Metin ile Benzerlik Analizi")
    compare_input = st.text_area("Karşılaştırılacak İkinci Metin:", value=SAMPLE_COMPARE_TEXT, height=110)
    if compare_input.strip():
        cmp_res = compare_two_texts(active_text, compare_input, filter_sw=apply_stopwords)
        st.metric("Jaccard Kelime Benzerliği", f"%{cmp_res['jaccard']}")
        st.write("**Ortak Kavramlar:**", ", ".join(cmp_res["common"]) if cmp_res["common"] else "Ortak terim yok.")
        st.write("**Yalnızca Mevcut Metinde:**", ", ".join(cmp_res["only_a"]) if cmp_res["only_a"] else "Yok.")
        st.write("**Yalnızca İkinci Metinde:**", ", ".join(cmp_res["only_b"]) if cmp_res["only_b"] else "Yok.")

with tab_soru:
    st.subheader("Metin Üzerinden Soru-Cevap")
    q_cols = st.columns([1.2, 1.2, 1.2, 1])
    preset_q = None
    if q_cols[0].button("Ana amaç nedir?"):
        preset_q = "Bu metnin temel amacı ve sağladığı fayda nedir?"
    if q_cols[1].button("Hangi yöntemler geçiyor?"):
        preset_q = "Metinde hangi araçlar ve yöntemler kullanılıyor?"
    if q_cols[2].button("Zorluk ve riskler neler?"):
        preset_q = "Karşılaşılan temel zorluklar ve riskler nelerdir?"
    if q_cols[3].button("Geçmişi Temizle"):
        st.session_state["qa_history"] = []

    user_question = st.text_input(
        "Kendi sorunu yaz:",
        value=preset_q or "",
        placeholder="Örn: Veri toplama adımlarında nelere dikkat edilmeli?",
    )
    if user_question.strip():
        ans, engine_used = answer_query(user_question, active_text, api_key_input)
        st.info(ans)
        st.caption(f"Yanıt motoru: {engine_used}")
        if not st.session_state["qa_history"] or st.session_state["qa_history"][-1][0] != user_question.strip():
            st.session_state["qa_history"].append((user_question.strip(), ans))

    if st.session_state["qa_history"]:
        with st.expander("Son Sorulan Sorular"):
            for q_item, a_item in reversed(st.session_state["qa_history"][-5:]):
                st.markdown(f"**S:** {q_item}\n\n**C:** {a_item}\n---")

with tab_arka_plan:
    st.subheader("Arka Plan NLP Ön İşleme & Cümle Skorları")
    st.write(
        f"**Aktif Kazıma Modu:** `{active_method}` | "
        f"**Karakter:** `{len(active_text)}` | "
        f"**Ham Kelime:** `{len(raw_words)}` | "
        f"**Filtrelenmiş Token:** `{len(tokens)}`"
    )
    st.write(", ".join(f"`{t}`" for t in tokens[:60]) if tokens else "Token bulunamadı.")

    scored_rows = score_sentences(active_text)
    if scored_rows:
        st.markdown("**Cümle Önem Puanları (Özet Seçim Kriteri):**")
        st.dataframe(scored_rows[:10], use_container_width=True, hide_index=True)

    report_md = build_markdown_report(
        title=src_title,
        method=active_method,
        tone=tone_label,
        summary=summary_output,
        keywords=top_words,
        bigrams=bigrams,
        trigrams=trigrams,
        qa_list=st.session_state["qa_history"],
    )
    report_json = json.dumps(
        {
            "generated_at": datetime.now().isoformat(),
            "title": src_title,
            "method": active_method,
            "summary": summary_output,
            "tone": tone_label,
            "positive_hints": pos_hits_list,
            "negative_hints": neg_hits_list,
            "keywords": [{"word": w, "count": c} for w, c in top_words],
            "bigrams": [{"ngram": b, "count": c} for b, c in bigrams],
            "trigrams": [{"ngram": t, "count": c} for t, c in trigrams],
            "qa_history": [{"question": q, "answer": a} for q, a in st.session_state["qa_history"]],
        },
        ensure_ascii=False,
        indent=2,
    )

    dl1, dl2 = st.columns(2)
    with dl1:
        st.download_button(
            label="📥 Raporu İndir (.md)",
            data=report_md,
            file_name="kaynak_analiz_raporu.md",
            mime="text/markdown",
            use_container_width=True,
        )
    with dl2:
        st.download_button(
            label="📦 Veriyi İndir (.json)",
            data=report_json,
            file_name="kaynak_analiz_verisi.json",
            mime="application/json",
            use_container_width=True,
        )
EOF
