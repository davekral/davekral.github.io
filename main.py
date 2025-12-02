import feedparser
from google import genai
import requests
import os
import datetime
import subprocess
import urllib.parse

# ==========================================
# 1. NASTAVENÍ
# ==========================================

# Tvůj API klíč
GOOGLE_API_KEY = "AIzaSyCgrDvW9O8R_TLmrBvbtYOqGxyE6GNnjzs"

# Zdroj zpráv (TechCrunch AI)
RSS_URL = "https://techcrunch.com/category/artificial-intelligence/feed/"

# Cesty k souborům
REPO_CESTA = "."
HTML_SOUBOR = "index.html"
SLOZKA_OBRAZKU = "img"
ZNACKA_PRO_VLOZENI = "<!-- NOVINKY ZDE -->"

# Inicializace nového klienta pro Gemini 2.5
client = genai.Client(api_key=GOOGLE_API_KEY)


# ==========================================
# 2. FUNKCE
# ==========================================

def stahnout_zpravu():
    """Stáhne nejnovější článek z RSS."""
    print("1. 📡 Stahuji RSS kanál...")
    feed = feedparser.parse(RSS_URL)
    if feed.entries:
        print(f"   - Nalezen článek: {feed.entries[0].title}")
        return feed.entries[0]
    else:
        print("   - ❌ Žádné články nenalezeny.")
        return None

def generovat_clanek(novinka):
    """Vytvoří článek pomocí Gemini 2.5 Flash."""
    print("2. 🧠 Gemini 2.5 píše článek...")
    
    prompt = f"""
    Přečti si tento text z RSS:
    Titulek: "{novinka.title}"
    Obsah: "{novinka.summary}"

    ÚKOL:
    Napiš krátký, čtivý blogový příspěvek v ČEŠTINĚ.
    Musí to znít jako novinka ze světa technologií, buď vtipný.
    
    FORMÁT (HTML):
    Použij <h2> pro nadpis.
    Použij <p> pro odstavce.
    Nepoužívej <html>, <body> ani značky ```html.
    Jen čistý text obsahu.
    """
    
    # Nová syntaxe pro google-genai (verze 2.5)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    
    # Očištění od případného formátování
    if response.text:
        cisty_text = response.text.replace("```html", "").replace("```", "").strip()
        return cisty_text
    return "Chyba: Gemini nevygeneroval text."

def stahnout_obrazek(tema_clanku):
    """Vygeneruje obrázek přes Pollinations.ai."""
    print("3. 🎨 Generuji obrázek (Pollinations)...")
    
    # 1. Necháme Gemini vymyslet prompt
    prompt_zadani = f"Vymysli VELMI KRÁTKÝ (max 5 slov) anglický popis obrázku k tématu: '{tema_clanku}'. Styl: cyberpunk, futuristic, 8k."
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt_zadani
    )
    
    if response.text:
        image_prompt = response.text.strip()
    else:
        image_prompt = "Futuristic AI technology, cyberpunk style" # Fallback
        
    print(f"   - Prompt: {image_prompt}")

    # 2. Sestavíme URL pro Pollinations
    encoded_prompt = urllib.parse.quote(image_prompt)
    seed = int(datetime.datetime.now().timestamp())
    
    # OPRAVENO: Odstraněna chyba s dvojitým odkazem
    image_url = f"[https://image.pollinations.ai/prompt/](https://image.pollinations.ai/prompt/){encoded_prompt}?seed={seed}&nologo=true"
    
    # 3. Stažení
    try:
        response = requests.get(image_url, timeout=20)
        
        # Vytvoření složky img, pokud neexistuje
        full_img_path = os.path.join(REPO_CESTA, SLOZKA_OBRAZKU)
        if not os.path.exists(full_img_path):
            os.makedirs(full_img_path)

        nazev_souboru = f"img_{seed}.jpg"
        cesta_k_ulozeni = os.path.join(full_img_path, nazev_souboru)
        
        if response.status_code == 200:
            with open(cesta_k_ulozeni, 'wb') as f:
                f.write(response.content)
            print("   - Obrázek stažen.")
            return f"{SLOZKA_OBRAZKU}/{nazev_souboru}"
        else:
            print("   - Chyba při stahování obrázku.")
            return None
    except Exception as e:
        print(f"   - Chyba obrázku: {e}")
        return None

def aktualizovat_html(clanek_html, obrazek_cesta):
    """Vloží nový článek do index.html."""
    print("4. 📝 Zapisuji do index.html...")
    datum = datetime.datetime.now().strftime("%d. %m. %Y %H:%M")
    
    img_tag = f'<img src="{obrazek_cesta}" alt="Ilustrace">' if obrazek_cesta else ""

    novy_html_blok = f"""
    <!-- ČLÁNEK START -->
    <div class="article">
        <span class="date">📅 {datum}</span>
        {clanek_html}
        {img_tag}
    </div>
    <!-- ČLÁNEK END -->
    {ZNACKA_PRO_VLOZENI}
    """
    
    try:
        with open(HTML_SOUBOR, "r", encoding="utf-8") as f:
            obsah = f.read()
        
        if ZNACKA_PRO_VLOZENI in obsah:
            novy_obsah = obsah.replace(ZNACKA_PRO_VLOZENI, novy_html_blok)
            with open(HTML_SOUBOR, "w", encoding="utf-8") as f:
                f.write(novy_obsah)
            print("   - HTML aktualizováno.")
        else:
            print(f"❌ CHYBA: V souboru {HTML_SOUBOR} chybí značka {ZNACKA_PRO_VLOZENI}.")
            
    except FileNotFoundError:
        print(f"❌ CHYBA: Soubor {HTML_SOUBOR} neexistuje!")

def pushnout_na_github():
    """Odešle změny na internet."""
    print("5. 🚀 Nahrávám na GitHub...")
    try:
        os.chdir(REPO_CESTA)
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", "Automatická aktualizace"], check=True)
        subprocess.run(["git", "push"], check=True)
        print("✅ HOTOVO! Web je aktualizován.")
    except Exception as e:
        print(f"❌ Chyba Gitu: {e}")


# ==========================================
# 3. SPUŠTĚNÍ
# ==========================================
if __name__ == "__main__":
    zprava = stahnout_zpravu()
    
    if zprava:
        try:
            # 1. Text
            text_clanku = generovat_clanek(zprava)
            # 2. Obrázek
            obrazek = stahnout_obrazek(zprava.title)
            # 3. Uložení
            aktualizovat_html(text_clanku, obrazek)
            # 4. Publikace
            pushnout_na_github()
            
        except Exception as e:
            print(f"❌ Nastala neočekávaná chyba: {e}")