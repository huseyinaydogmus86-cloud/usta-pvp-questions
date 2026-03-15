#!/usr/bin/env python3
"""
PDF → Soru Bankası İşleyici
Gemini AI ile PDF dosyalarından çoktan seçmeli sorular çıkarır.
(Yenilenmiş Sürüm: PDF'i doğrudan Gemini'ye yükler, böylece bozuk fontları ve görselleri bile okur!)
"""

import os
import json
import glob
import sys
import time

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

# --- Gemini Kurulum ---
genai.configure(api_key=GEMINI_API_KEY)
# Yeni, gorsel destekleyen hizli model
model = genai.GenerativeModel("gemini-2.0-flash")


def process_pdf_with_gemini(pdf_path: str, pdf_name: str) -> list:
    """PDF'i doğrudan Google sunucularına geçici olarak yükleyerek soruları çıkarır."""
    print(f"  Yukleniyor: {pdf_name} (Bu islem dosya boyutuna gore 1-2 dakika surebilir...)")
    
    try:
        # PDF'i doğrudan yükle
        uploaded_file = genai.upload_file(path=pdf_path)
    except Exception as e:
        print(f"  HATA: Dosya yuklenirken hata olustu: {e}")
        return []

    # API'nin dosyayı veritabanında hazır hale getirmesi için biraz bekliyoruz (ÖNEMLİ)
    time.sleep(8) 

    prompt = f"""Sen bir uzman eğitim asistanısın. Ekte gönderilen bu belge bir deneme sınavından / soru bankasından alınmıştır.
Lütfen bu PDF dosyasını İyice GÖZDEN GEÇİR (görsel ve metinleri), tüm sayfaları oku ve içindeki BÜTÜN çoktan seçmeli soruları çıkar.

KURALLAR:
1. Her sorunun "q" (soru metni) alanını çıkar. Eğer yazılar resim şeklindeyse kendi gelişmiş okuma yeteneğinle OCR yaparak metne çevir. Soru metnini anlaşılır şekilde yaz.
2. Sorunun şıklarını "options" adında bir array (liste) olarak çıkar. Şıklarda sadece metin olsun, (A, B, C, D) harflerini Puanlara ekleme, doğrudan şıkkın metnini veya sayısını koy.
3. Doğru cevabı veya en mantıklı cevabı bulup İÇERİĞİNİ "a" alanına yaz. Eğer bulamıyorsan options'taki A şıkkının içeriğini yazabilirsin. Cevap anahtarı varsa ondan yararlan.
4. Her soruya benzersiz, rastgele büyük bir "id" numarası (örneğin 1001, 1002, 1003 vb.) ver.
5. "source" alanına sadece "{pdf_name}" yaz.
6. SADECE aşağidaki JSON Array formatında dönüş yapmalısın. Geriye hiçbir ekstra metin veya Markdown açıklaması döndürme. SADECE JSON dön.

JSON FORMAT:
[
  {{
    "id": 1001,
    "q": "Soru metni...",
    "options": ["cevap 1", "cevap 2", "cevap 3", "cevap 4"],
    "a": "doğru cevabın kendisi",
    "source": "{pdf_name}"
  }}
]
"""
    try:
        # Model'e PDF dosyasını ve prompt'u besle
        response = model.generate_content([uploaded_file, prompt])
        raw = response.text.strip()

        # Clean markdown code blocks
        if raw.startswith("```json"):
            raw = raw.replace("```json", "", 1).rstrip("`").strip()
        elif raw.startswith("```"):
            raw = raw.lstrip("`").rstrip("`").strip()

        questions = json.loads(raw)
        
        # Dosyayı Google'ın geçici sunucusundan sil (Temizlik)
        try:
            genai.delete_file(uploaded_file.name)
        except:
            pass

        if not isinstance(questions, list):
            print(f"  HATA: {pdf_name} - Beklenmeyen cevap. JSON Array degil.")
            return []

        print(f"  ✅ {pdf_name}: {len(questions)} soru basariyla cikarildi!")
        return questions

    except json.JSONDecodeError as e:
        print(f"  HATA: {pdf_name} - PDF okundu ama AI sorulari bulamadi veya JSON olusturamadi. HATA: {e}")
        try: genai.delete_file(uploaded_file.name)
        except: pass
        return []
    except Exception as e:
        print(f"  HATA: {pdf_name} - Gemini yanit verirken hata olustu. Icerik kurallari veya dosya isleme: {e}")
        try: genai.delete_file(uploaded_file.name)
        except: pass
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

        # Gemini Native PDF okuyucu fonksiyonunu çağır
        questions = process_pdf_with_gemini(pdf_path, pdf_name)

        if questions:
            for q in questions:
                q["id"] = next_id
                next_id += 1
                all_questions.append(q)

    # Güncellenmiş soruları kaydet (yeni soru eklenmese bile, e.g boş dönerse boş kaydeder)
    save_questions(all_questions)


if __name__ == "__main__":
    main()
