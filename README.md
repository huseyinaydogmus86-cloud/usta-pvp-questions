# 📚 usta-pvp-questions

Bu repo, **Usta Yapay Zeka** platformunun PvP arena soru bankasını otomatik olarak yönetir.

## Nasıl Çalışır?

1. `pdfs/` klasörüne bir PDF dosyası push'la
2. GitHub Actions otomatik tetiklenir
3. Gemini AI ile sorular çıkarılır
4. `questions.json` güncellendi ve commit edilir
5. Ana uygulama bu dosyayı GitHub Raw URL üzerinden okur

## Kullanım

```bash
# PDF ekle
cp sinav.pdf pdfs/
git add pdfs/sinav.pdf
git commit -m "Yeni sınav soruları eklendi"
git push
```

Birkaç dakika içinde Actions çalışır ve `questions.json` güncellenir.

## Soru Formatı

```json
[
  {
    "id": 1,
    "q": "Soru metni",
    "options": ["A şıkkı", "B şıkkı", "C şıkkı", "D şıkkı"],
    "a": "Doğru şık",
    "source": "sinav.pdf"
  }
]
```

## Kurulum (İlk Kez)

GitHub reposunda **Settings → Secrets → Actions** bölümünden şunu ekle:

| Secret Adı | Değer |
|---|---|
| `GEMINI_API_KEY` | Google AI Studio'dan aldığın yeni key |

> ⚠️ Eski API key'leri iptal et! [Google AI Studio](https://aistudio.google.com)

## Dosya Yapısı

```
usta-pvp-questions/
├── .github/
│   └── workflows/
│       └── process-pdfs.yml   # Otomatik pipeline
├── pdfs/                       # PDF'leri buraya ekle
├── process_pdfs.py             # İşleme scripti
├── questions.json              # Otomatik oluşturulan çıktı
└── README.md
```
