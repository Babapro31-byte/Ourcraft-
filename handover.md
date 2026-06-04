# OurCraft 2 - Proje El Kitabı (Handover)

Bu dosya, OurCraft 2 projesinin mimarisi, özellikleri ve geliştirme detayları hakkında kapsamlı bilgi içerir.

## 🚀 Proje Hakkında
OurCraft 2, Python ve OpenGL (ModernGL) kullanılarak geliştirilmiş, Minecraft tarzı bir voxel oyun motorudur. Performans odaklı teknikler (Chunking, Face Culling, AO) ve modern bir renderer yapısı ile inşa edilmiştir.

## 🛠 Teknoloji Yığını
- **Dil:** Python 3.11+
- **Rendering:** [moderngl](https://github.com/moderngl/moderngl) (OpenGL 3.3+)
- **Pencere/Input:** [pygame-ce](https://pygameloop.github.io/pygame-ce/)
- **Matematik:** `numpy`
- **Gürültü (Noise):** `noise` (Perlin noise kütüphanesi)

## 🎯 Faz 2 Tamamlandı (2026-05-17)

Aşağıdaki özellikler başarıyla uygulandı:

- ✅ **Faz 2A:** Shift-Click Inventory (Hotbar ↔ Main stack taşıma)
- ✅ **Faz 2B:** Furnace + Smelting (5 tarifi, 4 fuel type, UI, save/load)
- ✅ **Faz 2C:** Chest + Storage (27 slot, UI, save/load)
- ✅ **Faz 2D:** Food Consumption (Raw/Cooked Beef, açlık yönetimi)
- ✅ **Bonus:** Tool Durability (Alet aşınması), Lava Damage (Su gibi lava hasarı)

**Dosya Değişiklikleri:** 9 dosya güncellendi. Tüm syntax kontrolleri ve runtime testler geçti.

## 📁 Proje Yapısı ve Dosyalar
- [main.py](file:///c:/Ourcraft%202/ourcraft2/main.py): Giriş noktası. Seed yönetimi ve oyun başlatma.
- [game.py](file:///c:/Ourcraft%202/ourcraft2/game.py): Ana oyun döngüsü, input yönetimi, crafting, fırın/sandık sistemi, shift-click inventory, yemek yeme mekanikleri.
- [world.py](file:///c:/Ourcraft%202/ourcraft2/world.py): Seed tabanlı arazi üretimi (Heightmap, Biomes, Trees, Caves). Entity yönetimi.
- [chunk.py](file:///c:/Ourcraft%202/ourcraft2/chunk.py): 16x16x256 blok verisi, mesh oluşturma, Face Culling ve Ambient Occlusion (AO). BLOCK_FURNACE (25) ve BLOCK_CHEST (26) defineleri.
- [player.py](file:///c:/Ourcraft%202/ourcraft2/player.py): WASD hareket, mouse-look, yerçekimi, AABB collision, raycast, blok kırma (durability), lava hasarı, yemek açlık yönetimi.
- [inventory.py](file:///c:/Ourcraft%202/ourcraft2/inventory.py): Hotbar (9 slot) + Main (27 slot) + Crafting grid'leri. ItemStack yönetimi, shift-move desteği.
- [recipes.py](file:///c:/Ourcraft%202/ourcraft2/recipes.py): 2×2 ve 3×3 crafting recipe'leri. SMELT_RECIPES (5 smelting) ve FUEL_VALUES (4 fuel type).
- [items.py](file:///c:/Ourcraft%202/ourcraft2/items.py): Item ID'leri (64+), tool tier'ları, durability. FOODS dict (Raw Beef, Cooked Beef).
- [save_manager.py](file:///c:/Ourcraft%202/ourcraft2/save_manager.py): Player, meta, chunk, entity, chest, furnace kayıt/yükleme. JSON + NPZ formats.
- [renderer.py](file:///c:/Ourcraft%202/ourcraft2/renderer.py): OpenGL renderer. Frustum culling, shader yönetimi, UI rendering.
- [texture_manager.py](file:///c:/Ourcraft%202/ourcraft2/texture_manager.py): PNG dosyalarını Texture Atlas'a dönüştürme, 1px padding ile mipmap bleeding önleme, UV haritalama.
- [ui.py](file:///c:/Ourcraft%202/ourcraft2/ui.py): Minecraft tarzı HUD. Inventory, Crafting Table, Furnace, Chest arayüzleri. Title screen.
- [shaders/](file:///c:/Ourcraft%202/ourcraft2/shaders/): GLSL shader dosyaları (Block, UI, Overlay).
- [textures/](file:///c:/Ourcraft%202/ourcraft2/textures/): 16x16 piksel blok texture dosyaları (24 blok tipi).

## ✨ Temel Özellikler
1.  **Rendering Optimizasyonu:**
    - **Face Culling:** Sadece görünür yüzler mesh'e eklenir.
    - **Frustum Culling:** Kamera açısı dışındaki chunk'lar GPU'ya gönderilmez.
    - **Ambient Occlusion:** Köşelerde blokların derinlik hissini artıran gölge efekti.
    - **Mipmap Bleeding Fix:** Atlas'ta 1px padding ile texture kenar kaymalarını önleme.
2.  **Dünya Üretimi:**
    - **Chunk Streaming:** Oyuncu hareket ettikçe dinamik chunk yükleme/boşaltma.
    - **Biyomlar:** Grass, Desert ve Snow bölgeleri.
    - **Mağaralar:** 3D Noise ile oyulmuş yer altı sistemleri.
3.  **Etkileşim:**
    - Sol Tık: Blok kır (animasyonlu).
    - Sağ Tık: Elindeki bloğu koy / Fırın/Sandık aç / Yemek ye.
    - Orta Tık: Baktığın bloğu hotbar'a seç (Pick Block).
    - Shift+Sol Tık (Envanter): Stack'ı hotbar ↔ ana envanterye taşı.
    - Hotbar (1-9): Bloklar arası geçiş.
4.  **Crafting Sistemi:**
    - **2×2 Crafting (E tuşu):** Planks, Sticks, Crafting Table, Torches.
    - **3×3 Crafting Table:** Pickaxe, Axe, Shovel, Sword ve diğer araçlar.
    - **Furnace:** Demir cevheri → Demir çubuk, Kumdan cam, Taş, Hamam cevheri → Pişmiş dişi.
5.  **Depolama ve Yönetim:**
    - **Sandık:** 27 slot depolama (3×9 grid). Sağ tıkla aç.
    - **Fırın:** Giriş, yakıt, çıkış slotu. 10 saniyede 1 cevheri pişirme.
    - **Yemek Sistemi:** Hamam dişi ve Pişmiş Hamam dişi tüketimi. Sağ tık ile ye, açlık barı dolsun.
    - **Araç Dayanıklılığı (Durability):** Blok kırınca aletler aşınır. Max dayanıklılığa ulaştığında kırılır.

## ⌨️ Kontroller
- **WASD:** Hareket
- **Space:** Zıplama
- **Shift:** Çömelme (Crouch) / Shift+Sol Tık: Stack Taşı (Envanter)
- **Ctrl:** Koşma (Sprint)
- **E:** Envanter Aç/Kapat / Fırın/Sandık Kapat
- **Esc:** Pause / Mouse Serbest Bırak / Fırın/Sandık/Envanter Kapat
- **F3:** Debug Bilgileri (FPS, XYZ, Look Target)
- **Sol Tık:** Blok Kır
- **Sağ Tık:** Blok Koy / Fırın/Sandık Aç / Yemek Ye (aktif item food ise)
- **Orta Tık:** Pick Block (hotbar'a bloğu seç)

## ⚙️ Kurulum ve Çalıştırma
Gereksinimleri kurun:
```bash
pip install -r requirements.txt
```

Oyunu başlatın:
```bash
            python -m ourcraft2.main
## 🔧 Yeni Özellikler (Faz 2) — Crafting ve Depolama

### Fırın Sistemi (Furnace)
- **Blok ID:** 25
- **Crafting:** 8 cobblestone ring pattern (3×3)
- **Mekanik:** Input → pişirme 10 saniye → Output
- **Yakıt:** Coal (80s), Log (15s), Planks (7.5s), Stick (2.5s)
- **Tarifler:** Iron Ore→Iron Ingot, Gold Ore→Gold Ingot, Sand→Glass, Cobblestone→Stone, Raw Beef→Cooked Beef
- **Arayüz:** Input slot (sol-üst) + Fuel slot (sol-alt) + Progress bar + Output slot (sağ)
- **Kayıt:** `furnaces.json` - Fırın state'i (progress, fuel_left) her frame kaydedilir

### Sandık Sistemi (Chest)
- **Blok ID:** 26
- **Crafting:** 8 planks ring pattern (3×3)
- **Kapasitesi:** 27 slot (3×9 grid)
- **Mekanik:** Sağ tıkla aç, hotbar + main envantere taşıyabilir
- **Kayıt:** `chests.json` - Her sandığın konumu ve içeriği kaydedilir

### Envanter İyileştirmeleri
- **Shift+Sol Tık:** Hotbar → Main veya Main → Hotbar'a stack taşı
- **Slot Yönetimi:** "fi", "ff", "fo" (furnace slots), "ch0"-"ch26" (chest slots)

### Yemek ve Beslenme
- **Yemek Öğeleri:** Raw Beef (3 hunger, 1.8 sat), Cooked Beef (8 hunger, 12.8 sat)
- **Mekanik:** Sağ tık ile ye, açlık < 20 ise tüket, item count azal
- **Lava Hasarı:** Su gibi lava'da 4 hasar/saniye

### Araç Dayanıklılığı (Durability)
- **Sistem:** Blok kırma sırasında aletler aşınır (1 point per block)
- **Tiering:** Wooden (60), Stone (132), Iron (251), Diamond (1562)
- **Max Ulaşılınca:** Alet otomatik break olur, inventory serbest kalır
- **Uygulama:** Crafting table, pickaxe, axe, shovel, sword, hoe tüm araçlarda

## 📝 İlaveten Kaydedilen Veriler
- **Chunk:** `.npz` (compressed numpy)
- **Player:** `player.json` (position, inventory, health, hunger, XP)
- **World:** `world.json` (seed, time_of_day)
- **Entities:** `entities.json` (mobs spawn points)
- **Furnaces:** `furnaces.json` (state per position) — Yeni
- **Chests:** `chests.json` (inventory per position) — Yeni

## 🔮 Gelecek Fazlar (Planlanan)

- **Faz 3:** Işık Sistemi (Block light, torch, sky light)
- **Faz 4:** Ses Sistemi (pygame.mixer, footsteps, mining, mob sounds)
- **Faz 5:** Mob İyileştirmeleri (sun burning, light-level spawn, creeper explosion)
- **Faz 6:** Performans (threaded mesh building, Numba JIT, greedy meshing)

## 📝 Genel Notlar
- Zemin sorunu için spawn bölgesine (0,0 chunk) otomatik bir çimen platform eklenmiştir.
- UI ters durma sorunu shader katmanında UV dikey flip edilerek çözülmüştür.
- Blok kırma hızı `player.py` içindeki `break_progress` mantığıyla yönetilir.
- Blok atlas'ında 1px padding ile mipmap bleeding (texture kenar kaymalarını) önlenir.
- Fırın ve sandıklar, oyun kaydedildiğinde JSON'a kaydedilir ve yüklendiğinde restore edilir.
- Yemek yeme mekanikleri sağ tıkla tetiklenir, açlık < 20 ise çalışır.
- Shift+Sol Tık inventory açıkken hotbar ve main arasında stack taşır.
- Fırın ve sandık UI'ları crafting table ile aynı pattern'i takip eder (modal ekranlar).
