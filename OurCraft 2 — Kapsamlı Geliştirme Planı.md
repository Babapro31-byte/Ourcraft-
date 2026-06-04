OurCraft 2 — Kapsamlı Geliştirme Planı
🚨 ACİL: Render Emergency — KESİN ÇÖZÜM (Atlas Y-Flip Uyumsuzluğu)
Context (Neden + Tanılama yolculuğu)
Kullanıcı çoklu testlerden sonra siyah blok problemini sürdüren bir hata bildirdi. Aşamalı diagnostic'lerle eledik:

Lighting hipotezi (önceki plan) → uygulandı, sonuç değişmedi → eleminize.
rgb = texel.rgb * v_tint testi → hala siyah. v_tint mesh build'de en kötü ihtimalle (0.55, 0.85, 0.55) (swamp biome, chunk.py:208), asla 0 değil. Yani texel.rgb = 0.
UV diagnostic (rgb = vec3(v_uv.x*8, v_uv.y*2, 0.5)) → ekranda sarı/yeşil bantlar görünüyor. Yani UV verisi GPU'ya doğru ulaşıyor, ama bu UV'larla atlas örneklenince hep siyah çıkıyor.
Hotbar doğru görünüyor argümanı YANLIŞ — texture_manager.py:119 ui_icons[n] = tex[n] ile orijinal pygame surface'lerini saklıyor. UI tarafı ui_icons üzerinden pygame surface'i direkt blit ediyor; GL atlas'a hiç dokunmuyor. Yani hotbar atlas'ı kanıtlamıyor.
Kök Sebep (Tek hata)
texture_manager.py:111-121 içinde çift Y-flip var:

v0_img = y / size               # pygame image-space (top-down, y=0 = top)
v1_img = (y + tile) / size
v0 = 1.0 - v1_img               # ←  UV-space flip
v1 = 1.0 - v0_img               # ←  UV-space flip
...
rgba_bytes = pygame.image.tobytes(atlas, "RGBA", False)   # ← byte order DOĞAL (top-down)
ModernGL ctx.texture(size, 4, data) (renderer.py:113) glTexImage2D'yi default ile çağırır — yani data byte sırası ne ise o şekilde texel grid'e yazar. tobytes(False) ile pygame row 0 (üst satır) = GL texel row 0 = v=0 örneklendiğinde dönen satır.

Yani GL convention'da v=0 → pygame üst (orijinal görüntünün üstü). Doğru UV grass_top için (pygame y=1-17) v ∈ [0.007, 0.118] olmalı. Ama kod v = 1 - v_img ile çevirir → v ∈ [0.882, 0.993] → bu da pygame row 127-143 = atlas grid row 7'yi (stone_hoe, iron_hoe, diamond_hoe, ve 5 boş hücre — SRCALPHA surface boş hücreleri RGBA=0,0,0,0 yapar) örnekler.

Sonuç: çoğu blok yüzü RGBA=(0,0,0,0) örnekler → opaque pass'te framebuffer'a (0,0,0,0) yazılır → ekranda SİYAH.

Çözüm (Tek satır değişikliği)
ourcraft2/texture_manager.py:121 — atlas byte'larını yüklerken Y-flip yap:

# ÖNCE:
rgba_bytes = pygame.image.tobytes(atlas, "RGBA", False)

# SONRA:
rgba_bytes = pygame.image.tobytes(atlas, "RGBA", True)
Bu, GL upload'da byte'ları dikey çevirir → pygame row 143 (alt) → GL v=0, pygame row 0 (üst) → GL v=1. Mevcut UV formülü (v0 = 1 - v1_img) bunu zaten bu konvansiyona göre hesaplıyor → uyum sağlanır.

Neden bu seçim? Alternatif (UV flip'i kaldırıp tobytes(False) bırakmak) da çalışır ama:

UV map çiplari çoklu yerde override edebiliyor (özel UV hesaplamaları)
tobytes(True) değişikliği shader/mesh/vertex pipeline'ında hiç değişiklik gerektirmiyor — sadece upload-time bit-flip
1 karakter (False → True)
Diagnostic shader'ı eski haline getir
ourcraft2/shaders/block.frag şu an UV-görselleştirme modunda. Atlas fix sonrası proper lighting shader'a geri dön:

#version 330

uniform sampler2D u_atlas;
uniform int u_cutout;
uniform vec3 u_sun_dir;
uniform vec3 u_sky_color;
uniform float u_time;

in vec3 v_normal;
in vec2 v_uv;
in float v_ao;
in float v_light;
in float v_fog;
in vec3 v_tint;
in float v_anim;

out vec4 f_color;

void main() {
    vec2 uv = v_uv;
    if (v_anim > 0.5) {
        uv.x = uv.x + sin(u_time * 0.6 + v_uv.y * 12.0) * 0.008;
        uv.y = uv.y + cos(u_time * 0.5 + v_uv.x * 12.0) * 0.008;
    }
    vec4 texel = texture(u_atlas, uv);
    if (u_cutout == 1 && texel.a < 0.10) {
        discard;
    }

    float ndl = max(dot(normalize(v_normal), normalize(u_sun_dir)), 0.0);
    float ambient = 0.42 + 0.58 * ndl;
    ambient *= v_light;
    ambient = max(ambient, 0.25);
    vec3 rgb = texel.rgb * v_tint * ambient * v_ao;

    rgb = mix(rgb, u_sky_color, v_fog);

    float alpha = texel.a;
    if (v_fog > 0.5) {
        alpha *= (1.0 - (v_fog - 0.5) * 0.4);
    }

    f_color = vec4(rgb, alpha);
}
Önceki lighting fix'lerinin durumu
chunk.py içindeki iki düzeltme (sky-light incoming propagation + komşu blok ışık örnekleme) uygulanmış kalsın — bunlar gerçekten doğru fix'lerdi, sadece görsel etkileri atlas fix'i olmadan görünmüyordu. Atlas fix'ten sonra lighting de doğru çalışacak. world.py neighbor-dirty fix de korunsun.

Doğrulama
python -m ourcraft2.main çalıştır
Mevcut dünyaya gir veya yeni dünya yarat
Beklenen: çimen yeşil, dirt kahverengi, stone gri, sand bej — gerçek texture'lar görünmeli
Yere bak → toprak texture'ları, hava boşluğu yok
Ağaca bak → log/leaves doğru görünmeli (leaves cutout, arkası görünebilir)
Su/lav → animasyonlu UV scroll
Mağaraya gir → karanlık (doğru sky=0)
Yere düşen blok kırma overlay'i → bloğa hizalı kalmalı
Context (Önceki Hedef)
Kullanıcının mevcut OurCraft 2 projesinde 3 ana sıkıntı var:

X-ray bug: Aşağı bakınca zemin parçalanıyor, arasından gökyüzü görünüyor (ekran görüntüsü FPS 46, Y +84, çayır biyomu).
Texture'lar Minecraft hissi vermiyor: Anti-aliased font + mipmap blur + flat procedural çizimler.
Mevcut özellikler eksik UI ile dolu: Creative/Survival modları kod olarak yazılı (player.py:162-166, F4/G ile toggle) ama hiçbir görsel akış göstermiyor; tuş atamaları tamamen hard-coded.
Hedef: 5 faza bölünmüş, sırayla doğrulanabilir bir geliştirme dizisi. Her faz çalışan oyunla bitsin, sonraki başlasın.

Faz A — Render Hatalarını Düzelt (X-ray + atlas filter + near plane)
Tahmini boyut: Çok küçük (~15 satır toplam), izole, en yüksek görsel etki/efor oranı.

Kök sebep
Tall grass + çiçekler chunk.py:436-441'de is_transparent() üzerinden trans_verts'e (alpha-blend) yönlendiriliyor. Translucent draw path (renderer.py:580-587) iki şeyi yapmıyor:

ctx.depth_mask = False ayarlamıyor → yarı saydam fragment'ler depth buffer'a yanlış değer yazıyor
u_cutout = 0 çünkü block.frag:27-28'deki texel.a < 0.10 discard'ı atlanıyor
Sonuç: ekrandan aşağı bakınca yakındaki cross-billboard çimenlerin yazdığı depth, arkalarındaki zemin yüzeylerini occlude ediyor → X-ray.

Değişiklikler
1. chunk.py:436-441 — Tall grass ve çiçekleri cutout sınıfına taşı:

# Önce:
if bid in (BLOCK_LEAVES, BLOCK_GLASS):
    tgt = cutout_verts
elif is_transparent(bid):
    tgt = trans_verts

# Sonra:
if bid in (BLOCK_LEAVES, BLOCK_GLASS, BLOCK_TALL_GRASS, BLOCK_FLOWER_RED, BLOCK_FLOWER_YELLOW):
    tgt = cutout_verts
elif is_transparent(bid):
    tgt = trans_verts
2. renderer.py:580-587 — Translucent çevresinde depth-write korumalı:

if trans_draw:
    self.ctx.enable(moderngl.BLEND)
    self.ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)
    self.ctx.depth_mask = False           # YENİ
    self.program_block["u_cutout"].value = 0
    trans_draw.sort(key=lambda t: t[0], reverse=True)
    for _, vao in trans_draw:
        vao.render(mode=moderngl.TRIANGLES)
    self.ctx.depth_mask = True            # YENİ
    self.ctx.disable(moderngl.BLEND)
3. renderer.py:114 — Atlas filter'ı pure NEAREST:

# Önce:
self.atlas.filter = (moderngl.NEAREST_MIPMAP_LINEAR, moderngl.NEAREST)
# Sonra (Minecraft-pixelated hissi için):
self.atlas.filter = (moderngl.NEAREST_MIPMAP_NEAREST, moderngl.NEAREST)
(Mipmap'i komple kapatmıyoruz — uzak chunk'larda shimmer artar. NEAREST_MIPMAP_NEAREST Minecraft Java'nın varsayılan davranışı.)

4. renderer.py:516 — Near plane 0.05 → 0.1 (depth precision):

proj = perspective(math.radians(self.fov), aspect, 0.1, 1200.0)
Doğrulama
python -m ourcraft2.main çalıştır, var olan bir dünyaya gir.
Çayır biyomunda Y+84 civarında düz aşağı bak → zemin sağlam görünmeli, çimenler arasından gök görünmemeli.
Camdan ve yapraktan bak → hala şeffaf (regresyon kontrolü).
Su altında bak → su yarı şeffaf kalmalı, dipte zemin doğru görünmeli.
Faz B — Texture & Font Overhaul (CC0 pack + pixel font)
Tahmini boyut: Orta. Tek tek dosya yönetimi, kod değişikliği az.

Texture pack stratejisi
Kullanıcı CC0 hazır pack istedi. Lisans temiz olması için kandidatlar:

Pack	Kaynak	Lisans	Not
Pixel Perfection	XSSheep, Planet Minecraft	MIT	16×16, Minecraft-stili, en yakın görsel
Kenney Voxel Pack	kenney.nl/assets/voxel-pack	CC0	Daha stilize, %100 güvenli
OpenGameArt 16×16 cc0	opengameart.org filtre cc0	CC0	Karışık kalite, en güvenli
Önerilen: Pixel Perfection (MIT) birincil, Kenney Voxel yedek. İmplementasyon başında pack URL'sini son kez doğrula.

Yapılacaklar
1. Pack indirme & yerleştirme

ourcraft2/textures/pack/ alt klasörü oluştur (mevcut textures/*.png'leri silme — fallback olarak kalsın).
Pack içinden chunk.py'deki block ID'lere karşılık gelen 27 block + 30+ item dosyasını isim eşle:
grass_block_top.png       → grass_top.png
grass_block_side.png      → grass_side.png
oak_log.png               → wood_log_side.png
oak_log_top.png           → wood_log_top.png
oak_planks.png            → planks.png
... (texture_manager.py:114-232 listesi referans)
LICENSE-TEXTURES.txt ekle: pack adı, kaynak URL, lisans metni.
2. texture_manager.py loader güncellemesi

Yeni dosyaları okuma sırası: önce textures/pack/<name>.png, yoksa textures/<name>.png (mevcut procedural fallback).
5-10 satır değişiklik, texture_manager.py:114-232 etrafında.
3. Pixel font ekleme

Font kandidatları (lisans güvenli):
VT323 (Google Fonts, OFL) — yaygın, ücretsiz embed
Press Start 2P (Google Fonts, OFL) — daha kalın
Pixelify Sans (Google Fonts, OFL) — modern pixel
Önerilen: VT323 — Minecraft'ın "Mojangles" fontuna yakın hissi.
ourcraft2/fonts/VT323-Regular.ttf koy.
ui.py:24 etrafındaki font seçimini düzenle:
FONT_PATH = os.path.join(os.path.dirname(__file__), "fonts", "VT323-Regular.ttf")
# _get_font() içinde:
if os.path.exists(FONT_PATH):
    return pygame.font.Font(FONT_PATH, size)
# else mevcut fallback
Tüm _draw_text() çağrılarında font değişiminden etkilenen layout'ları gözden geçir — sliderlar, slot sayıları, FPS panel.
4. HUD küçük cilalar

Hotbar arkaplanı (8,10,20,200) → daha Minecraft'a yakın (60,60,60,180) koyu gri.
Crosshair şu an 11px arms — Minecraft'ta 7px. Küçült.
Health/hunger bar boyutları Minecraft'a yakın olsun: 10 ikon ×8px (mevcut "❤ N/20" text yerine ikon dizisi). Opsiyonel, zamana göre.
Doğrulama
Oyunu aç, ana ekran fontu pixelated görünmeli.
Çimene/taşa yaklaş — net pixel kenarları.
Uzağa bak — chunk'lar arasında shimmer yok.
Eski procedural fallback hala çalışıyor mu test: pack/ klasörünü geçici sil, oyun yine açılsın.
Faz C — Keybinds Konfigürasyon Sistemi ve Menü
Tahmini boyut: En büyük yapısal değişiklik. 3 dosya, ~150-200 satır net ekleme.

Mevcut durum
Tüm tuşlar game.py:1071-1144, game.py:1202-1207'de hard-coded pygame.K_*. config.py:13-18 sadece render_distance, fov, sensitivity, brightness tutuyor.

Yapılacaklar
1. config.py — keybinds şeması ekle

DEFAULT_KEYBINDS: Dict[str, int] = {
    "move_forward": pygame.K_w,
    "move_back":    pygame.K_s,
    "move_left":    pygame.K_a,
    "move_right":   pygame.K_d,
    "jump":         pygame.K_SPACE,
    "sneak":        pygame.K_LSHIFT,
    "sprint":       pygame.K_LCTRL,
    "inventory":    pygame.K_e,
    "pause":        pygame.K_ESCAPE,
    "debug":        pygame.K_F3,
    "toggle_creative": pygame.K_F4,
    "drop_item":    pygame.K_q,
    # hotbar_1..9 ayrı slot
    **{f"hotbar_{i+1}": getattr(pygame, f"K_{i+1}") for i in range(9)},
}
DEFAULTS["keybinds"] = DEFAULT_KEYBINDS
load_config()'da eksik action'lara default doldur (forward compatible).
save_config() int olarak yazsın (pygame.K_* zaten int).
2. game.py event/key refactor

Sınıf seviyesinde helper:
def _key(self, action: str) -> int:
    return self.cfg["keybinds"].get(action, DEFAULT_KEYBINDS[action])
game.py:1071-1144 tüm event.key == pygame.K_X karşılaştırmalarını event.key == self._key("name") yap.
game.py:1202-1207 keys[pygame.K_W] → keys[self._key("move_forward")].
Hotbar 1-9 döngü ile: for i in range(9): if event.key == self._key(f"hotbar_{i+1}"): self.player.active_slot = i.
3. ui.py — Settings menüsü ile Keybinds alt-menüsü

Pause menüde ui.py:640-757 mevcut sliderlara ek "⚙ Controls" butonu.
Yeni _draw_keybinds_menu(): 2 sütunlu liste (action label sol, atanmış tuş adı sağ).
pygame.key.name(keycode) ile insan-okunur isim ("space", "left shift", "f4").
Her satır click edilir → "Press any key..." moduna girer.
Sonraki keydown'da o action'a ata, çakışan varsa eskisini boşalt.
"Reset to defaults" butonu altta.
Yeni UIState field: rebinding_action: Optional[str], keybinds_scroll: int.
4. Yeni game_state: "keybinds_menu"

Pause'dan "⚙ Controls" → state değiştir.
ESC ile pause'a dön.
Rebinding modunda ESC iptal eder, atama yapmaz.
5. Çakışma uyarısı

Aynı tuş iki action'a atanırsa kırmızıyla işaretle (engelleme yok, sadece uyar).
Doğrulama
Pause aç → ⚙ Controls → "Forward" satırına tıkla → R bas → W'nin yerine R atanmalı.
Oyuna dön, R ile ileri git → çalışsın.
Quit + restart → R kalıcı mı (config dosyasına yazıldı mı).
Reset to defaults → W geri gelmeli.
Hotbar 5 rebind → numpad'e atayıp test.
Faz D — Game Mode UX (Creative/Survival görsel akış)
Tahmini boyut: Küçük-orta. Mekanik kod zaten yazılı; sadece UI surface'i ekliyoruz.

Mevcut durum
player.py:162-166 — game_mode = "survival" field var.
player.py:243-252 — Çift Space ile uçma toggle (creative'de).
player.py:297-304 — Creative'de gravity yok.
game.py:1132-1140 — F4 toggle creative anywhere.
save_manager.py:128, 166-167 — player.json'da mode saklanıyor.
Yapılacaklar
1. Yeni dünya yaratma ekranında mode seçimi

ui.py:241-315 title → seed input flow'una ek satır.
Seed input modal altına 2 buton: [ ⛏ Survival ] [ ✨ Creative ] — radyo gibi.
UIState.new_world_mode: str = "survival" field ekle.
Game.py: yeni dünya yaratınca game.py:219 çevresinde self.player.game_mode = ui_state.new_world_mode.
Save'e ilk yazımda mode bu olur.
2. Pause menüde gerçek mode değiştirici

ui.py:714-719 mevcut "SURVIVAL/CREATIVE" badge'i clickable butona dönüştür.
Tıklayınca toggle (mevcut F4 mantığını kullan, game.py:1132-1140 içindeki fonksiyonu çağır).
Badge yanına küçük "(F4)" yaz — kısayolu öğret.
3. HUD'da mode göstergesi (sadece creative ise)

Creative'de sol-alt köşeye küçük "✨ CREATIVE" yazısı (cyan renk).
Survival'da hiçbir şey gösterme (Minecraft davranışı).
4. Creative-only kısayollar belirginleştir

Çift Space uçma → debug overlay'inde "FLY: ON/OFF" satırı.
Creative'de envanter açıkken tüm bloklar erişilebilir olmalı (bonus, opsiyonel) — mevcut envanter sadece toplananları gösteriyor; "creative tab" ekleme büyük iş, Faz E'ye ertelenir.
Doğrulama
Title → Singleplayer → seed gir → "Creative" seç → New World.
Oyunda Space×2 → uçabilmeli, gravity kapanmalı.
F4 bas → survival'a dön, düşmeli.
Pause aç → badge'e tıkla → mode değişmeli.
Quit + reload → seçilen mode hatırlanmalı.
Faz E — Genel Cila ve Mevcut Özellikleri Güçlendirme
Tahmini boyut: Esnek. Aşağıdaki maddelerden öncelik sırasına göre yapılır, zaman/onay yetince durulur.

Sıralı liste (yüksek değer → düşük)
E1. Ses sistemi (handover'da Faz 3 olarak planlı)

pygame.mixer.init() başta.
ourcraft2/audio.py zaten dosya var (Glob sonucu gösterdi) — boş mu, içerikli mi gözlem yapıp tamamla.
Olaylar: blok kır, blok koy, ayak sesi (hareket halinde, yere göre — taş/çim/kum), zıplama, hasar, yemek ye, fırın aktif.
CC0 ses kaynakları: opengameart.org, freesound.org (CC0 filtreli).
E2. Performans — threaded mesh building (handover Faz 6)

Mevcut: ana thread'de chunk mesh hesabı → fark edilir takılma.
Çözüm: concurrent.futures.ThreadPoolExecutor ile 2-4 worker, mesh build'i thread havuzuna at, sonuçları main thread queue'sundan GL upload.
Risk: GL context tek thread'de. Sadece CPU mesh array'leri thread'lerde, upload main'de.
E3. Dropped item entities

Şu an blok kırınca direkt envantere giriyor.
Minecraft'ta yere düşer, üzerinden geçince toplanır (gerçek hissi).
entity.py'de yeni ItemEntity tipi, world'de fizik (basit gravity), oyuncuya yakınsa magnetism + collect.
E4. Gökyüzü gradient + günün saatleri

renderer.py:404 sky color tek renk.
Gradient (üst koyu mavi → alt soluk) + world.time_of_day ile gece/gündüz interpolation.
Mevcut world.json time_of_day field'ı zaten kayıtlı.
E5. Düşme hasarı + can yenilenme

Düşme hızı > 1.5 m/s × her metre 1 hasar (Minecraft formülü).
Hunger > 18 ise saniyede 1 can geri gel (Minecraft'ta yarım kalp/saniye).
E6. Smooth biome blending

Mevcut: biyom rengi sert geçişli.
Biome map'inde komşu örnekle ortalama (world.py'deki biome lookup'ı).
E7. F5 third-person kamera

Player pozisyonundan ~3m geri offset.
Sadece görsel değişiklik (player render'ı için entity shader zaten var).
E8. Drop on death + respawn cila

Mevcut death var, "YOU DIED!" var.
Respawn'da envanter sıfırlanmıyor — Minecraft'ta düşer. Survival'a uygun davranış ekle.
Doğrulama
Her madde tamamlanırken oyunu çalıştırıp ilgili özellik test edilir. E maddesi açık-uçludur; kullanıcı "yeter" deyince durur.

Kritik dosyalar (özet)
Dosya	Faz	Değişiklik tipi
chunk.py	A	Cutout sınıfı genişletme
renderer.py	A, B	depth_mask, atlas filter, near plane
texture_manager.py	B	Pack klasör fallback loader
ui.py	B, C, D	Font, keybind menüsü, mode butonu
config.py	C	keybinds dict + load/save
game.py	C, D, E	Keybind lookup, mode UX, ses
save_manager.py	D	(mevcut yeterli)
audio.py	E1	Mevcut/eksik kontrol et
entity.py	E3	ItemEntity ekle
world.py	E4, E6	Time, biome blending
textures/pack/	B	Yeni klasör + LICENSE
fonts/VT323-Regular.ttf	B	Yeni dosya
Onay akışı
Her faz bitince:

python -m ourcraft2.main çalıştır
İlgili faz doğrulama testlerini geç
Kullanıcı onayla → sonraki faz başlasın
Reddederse o fazda iterasyon
Toplam tahmini efor: Faz A günler-saatler, B-D yarım gün her biri, E açık uçlu.