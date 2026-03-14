#!/usr/bin/env python3
"""
PDF → Soru Bankası İşleyici
Gemini AI ile PDF dosyalarından çoktan seçmeli sorular çıkarır.
"""

import os
import json
import glob
import sys

try:
    import pdfplumber
except ImportError:
    print("pdfplumber yüklü değil. pip install pdfplumber çalıştırın.")
    sys.exit(1)

try:
    import google.generativeai as genai
except ImportError:
    print("google-generativeai yüklü değil.")
    sys.exit(1)

# --- Ayarlar ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("HATA: GEMINI_API_KEY çevre değişkeni tanımlı değil!")
    sys.exit(1)

PDF_FOLDER = "pdfs"
OUTPUT_FILE = "questions.json"
MAX_CHARS = 30000  # Gemini token limiti için

# --- Gemini Kurulum ---
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")


def extract_text_from_pdf(pdf_path: str) -> str:
    """PDF dosyasından metin çıkarır."""
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"  UYARI: {pdf_path} okunamadı: {e}")
    return text.strip()


def parse_questions_with_ai(text: str, pdf_name: str) -> list:
    """Gemini AI ile metinden soru çıkarır."""
    if not text or len(text) < 50:
        print(f"  ATLANDI: {pdf_name} - Yeterli metin yok ({len(text)} karakter).")
        return []

    # Çok uzun metni kırp
    text_to_send = text[:MAX_CHARS] + "\n\n[...metnin geri kalanı kırpıldı...]" if len(text) > MAX_CHARS else text

    prompt = f"""Sen bir uzman eğitim asistanısın. Aşağıdaki metin bir sınav/test kitabından alınmıştır.
Bu metindeki TÜM çoktan seçmeli soruları bul ve çıkar.

KURALLAR:
1. Her sorunun "q" (soru metni) alanını bul. Soruyu tam ve anlaşılır şekilde yaz.
2. Sorunun şıklarını "options" adında bir array olarak çıkar. Sadece 4 veya 5 string olsun (A, B, C, D harfleri OLMADAN).
3. Doğru cevabı bul ve şıkkın İÇERİĞİNİ "a" alanına yaz.
4. Her soruya benzersiz bir "id" numarası ver (rastgele büyük sayı, çakışmaları önlemek için).
5. "source" alanına PDF dosya adını yaz: "{pdf_name}"
6. Sadece JSON array döndür. Başka hiçbir açıklama yazma!

JSON FORMAT:
[
  {{
    "id": 1001,
    "q": "Soru metni buraya...",
    "options": ["şık1", "şık2", "şık3", "şık4"],
    "a": "doğru şıkkın içeriği",
    "source": "{pdf_name}"
  }}
]

İŞTE METİN:
{text_to_send}"""

    try:
        response = model.generate_content(prompt)
        raw = response.text.strip()

        # Markdown code block temizle
        if raw.startswith("```json"):
            raw = raw.replace("```json", "", 1).rstrip("`").strip()
        elif raw.startswith("```"):
            raw = raw.lstrip("`").rstrip("`").strip()

        questions = json.loads(raw)
        if not isinstance(questions, list):
            print(f"  HATA: {pdf_name} - Geçersiz format, liste bekleniyor.")
            return []

        print(f"  ✅ {pdf_name}: {len(questions)} soru bulundu.")
        return questions

    except json.JSONDecodeError as e:
        print(f"  HATA: {pdf_name} - JSON parse hatası: {e}")
        return []
    except Exception as e:
        print(f"  HATA: {pdf_name} - Gemini hatası: {e}")
        return []


def load_existing_questions() -> list:
    """Mevcut questions.json dosyasını yükler."""
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def get_processed_sources(questions: list) -> set:
    """Daha önce işlenmiş PDF isimlerini döndürür."""
    return {q.get("source", "") for q in questions if q.get("source")}


def save_questions(questions: list):
    """Soruları questions.json'a kaydeder."""
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Toplam {len(questions)} soru kaydedildi → {OUTPUT_FILE}")


def main():
    pdf_files = glob.glob(os.path.join(PDF_FOLDER, "*.pdf"))

    if not pdf_files:
        print(f"'{PDF_FOLDER}' klasöründe PDF bulunamadı. Çıkılıyor.")
        return

    print(f"🔍 {len(pdf_files)} PDF bulundu:\n")

    existing_questions = load_existing_questions()
    processed = get_processed_sources(existing_questions)
    all_questions = list(existing_questions)
    next_id = max((q.get("id", 0) for q in all_questions), default=0) + 1

    new_pdfs = [f for f in pdf_files if os.path.basename(f) not in processed]

    if not new_pdfs:
        print("⏭️  Yeni PDF yok, hepsi zaten işlenmiş.")
        return

    for pdf_path in new_pdfs:
        pdf_name = os.path.basename(pdf_path)
        print(f"📄 İşleniyor: {pdf_name}")

        text = extract_text_from_pdf(pdf_path)
        questions = parse_questions_with_ai(text, pdf_name)

        for q in questions:
            q["id"] = next_id
            next_id += 1
            all_questions.append(q)

    save_questions(all_questions)


if __name__ == "__main__":
    main()
