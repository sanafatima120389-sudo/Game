import pygame, random, math, json, os, sys

pygame.init()
AUDIO_OK = False

def make_tone(freq=440, duration=.1, volume=.2, sweep=0):
    if not AUDIO_OK:
        return None
    import array
    rate = 22050
    n = max(1, int(rate * duration))
    buf = array.array("h")
    for i in range(n):
        t = i / rate
        env = min(1, i / 450) * min(1, (n - i) / 900)
        f = freq + sweep * t
        buf.append(int(32767 * volume * env * math.sin(2 * math.pi * f * t)))
    try:
        return pygame.mixer.Sound(buffer=buf.tobytes())
    except Exception:
        return None

def make_music():
    return None

def play_sfx(s):
    try:
        if s:
            s.play()
    except Exception:
        pass

SFX_SHOT = make_tone(850, .055, .18, -4200)
SFX_HIT = make_tone(170, .11, .22, 700)
SFX_BUY = make_tone(500, .1, .18, 600)
SFX_BOSS = make_tone(70, .3, .22, -10)
MENU_MUSIC = None

try:
    screen = pygame.display.set_mode((720, 1280))
except Exception:
    screen = pygame.display.set_mode((405, 720))

W, H = screen.get_size()
clock = pygame.time.Clock()
pygame.display.set_caption("Battle Zone")

WHITE=(245,245,245); BLACK=(12,15,19)
GREEN=(55,210,95); RED=(225,65,65); BLUE=(55,140,235)
YELLOW=(245,205,55); PURPLE=(175,75,220)
ORANGE=(240,145,55); GRASS=(38,95,57)
GRID=(48,112,67); PANEL=(25,30,37); GRAY=(95,100,110)
CYAN=(180,245,245)

S = min(W/405, H/720)
def sc(x):
    return max(1, int(x*S))

font = pygame.font.Font(None, max(28, sc(28)))
small = pygame.font.Font(None, max(21, sc(21)))
big = pygame.font.Font(None, max(46, sc(46)))
title = pygame.font.Font(None, max(62, sc(62)))

SAVE_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "battle_zone_save.json"
)

def load_save():
    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)

        u = max(1, min(100, int(d.get("unlocked", 1))))
        m = max(0, int(d.get("money", 0)))
        o = set(int(x) for x in d.get("owned", [0]) if 0 <= int(x) < 21)
        if not o:
            o = {0}

        gi = max(0, min(20, int(d.get("gun_index", 0))))
        if gi not in o:
            gi = 0

        op = set(int(x) for x in d.get("owned_players", [0]) if 0 <= int(x) < 5)
        if not op:
            op = {0}

        pi = max(0, min(4, int(d.get("player_index", 0))))
        if pi not in op:
            pi = 0

        return u, m, o, gi, op, pi
    except Exception:
        return 1, 0, {0}, 0, {0}, 0

unlocked, money, owned, gun_index, owned_players, player_index = load_save()

sfx_enabled = True
vfx_enabled = True

def save_game():
    try:
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "unlocked": unlocked,
                "money": money,
                "owned": sorted(owned),
                "gun_index": gun_index,
                "owned_players": sorted(owned_players),
                "player_index": player_index,
                "sfx_enabled": sfx_enabled,
                "vfx_enabled": vfx_enabled
            }, f)
    except Exception:
        pass

guns = [
    ("PISTOL",0,12,7),("SMG",40,16,8),("BURST RIFLE",80,18,10),
    ("ASSAULT RIFLE",120,20,12),("CARBINE",160,24,12),
    ("TACTICAL SMG",210,28,13),("RANGER",260,32,14),
    ("SCOUT RIFLE",320,36,15),("VECTOR",390,40,16),
    ("AK STYLE",470,45,17),("M4 STYLE",560,50,18),
    ("FAL STYLE",660,56,19),("BULLPUP",780,62,20),
    ("MARKSMAN",910,69,21),("HEAVY RIFLE",1050,76,22),
    ("LASER RIFLE",1200,84,23),("PLASMA",1370,93,24),
    ("PULSE GUN",1550,103,26),("RAIL GUN",1750,115,28),
    ("ULTIMATE",1950,130,31),("ADMIN GUN",0,800,460)
]

players = [
    ("RECRUIT",0,3.2),
    ("SCOUT",500,3.7),
    ("RUNNER",1000,4.2),
    ("SWIFT",1750,4.8),
    ("PHANTOM",3000,5.5),
]

START="start"; MENU="menu"; PLAY="play"; SHOP="shop"
SETTINGS="settings"; COMPLETE="complete"; OVER="over"

state = START
settings_confirm = None
level = 1
level_page = 1
total = 2
spawned = 0
spawn_timer = .3

base = pygame.Vector2(W/2, H/2)
base_r = int(min(W,H)*.34)
tower = base.copy()
tower_hp = 500
player = pygame.Vector2(W/2, H/2 + sc(105))
player_hp = 100
ammo = 50
speed = 3.2
kills = 0

enemies = []
bullets = []
powers = []
power_spawn_timer = random.uniform(10.0,15.0)
fire_wait = 0
aim_dir = pygame.Vector2(0,-1)

joy = pygame.Vector2(sc(72), H-sc(80))
joy_knob = joy.copy()
fire_btn = pygame.Rect(W-sc(105), H-sc(125), sc(78), sc(78))
jump_btn = pygame.Rect(W-sc(205), H-sc(105), sc(68), sc(58))
shop_btn = pygame.Rect(W-sc(110), sc(8), sc(60), sc(42))
menu_close_btn = pygame.Rect(W-sc(58), sc(10), sc(45), sc(45))
settings_rect = pygame.Rect(W//2-sc(110), H//2+sc(198), sc(220), sc(55))

shop_popup_gun = None
shop_page = 0
shop_popup_player = None
last_boss_reward = 0
joystick_active = False
fire_held = False
jump_timer = 0.0
jump_velocity = pygame.Vector2()
touch_roles = {}
particles = []
muzzle_timer = 0.0
recoil = 0.0
menu_time = 0.0

def level_enemies(n):
    return round(2 + (n-1)*78/99)

def is_boss_level(n):
    return n % 10 == 0

def boss_hp_for_level(n):
    return 300 + ((n//10)-1)*200

def boss_damage_for_level(n):
    return 35

def boss_reward_for_level(n):
    if n == 100:
        return 300
    if 1 <= n <= 30:
        return 100
    if 31 <= n <= 60:
        return 150
    if 61 <= n <= 90:
        return 170
    if 91 <= n <= 100:
        return 500
    return 100

def player_speed_for_index(i):
    return players[max(0,min(4,i))][2]

def admin_unlocked():
    return unlocked >= 100

def draw_skull(center_pos, size, color=RED):
    x, y = center_pos
    r = max(4, size//3)
    pygame.draw.circle(screen, color, (x, y-r//2), r)
    pygame.draw.rect(
        screen, color,
        (x-r//2, y-r//4, r, max(2,r*2)),
        border_radius=max(2,size//8)
    )
    pygame.draw.circle(screen, BLACK, (x-r//3,y-r//2), max(2,r//5))
    pygame.draw.circle(screen, BLACK, (x+r//3,y-r//2), max(2,r//5))
    pygame.draw.rect(screen, BLACK, (x-r//3,y+r//8,2*r//3,max(2,r//6)))

def spawn_outside():
    side = random.randrange(4)
    if side == 0:
        return pygame.Vector2(random.randint(sc(20),W-sc(20)), sc(75))
    if side == 1:
        return pygame.Vector2(random.randint(sc(20),W-sc(20)), H-sc(145))
    if side == 2:
        return pygame.Vector2(sc(18),random.randint(sc(75),H-sc(145)))
    return pygame.Vector2(W-sc(18),random.randint(sc(75),H-sc(145)))

def spawn_inside_base():
    a = random.random()*math.tau
    r = random.uniform(sc(25),base_r-sc(25))
    return base + pygame.Vector2(math.cos(a)*r, math.sin(a)*r)

def start_level(n):
    global level,total,spawned,spawn_timer,tower_hp,player_hp,ammo
    global power_spawn_timer,speed,last_boss_reward,jump_timer
    global jump_velocity,fire_held,joystick_active

    level = n
    total = level_enemies(n)
    spawned = 0
    spawn_timer = .1
    tower_hp = 500
    player_hp = 100
    ammo = 50
    speed = player_speed_for_index(player_index)
    last_boss_reward = 0
    power_spawn_timer = random.uniform(10.0,15.0)
    enemies.clear()
    bullets.clear()
    powers.clear()
    joy_knob.xy = joy.xy
    jump_timer = 0.0
    jump_velocity.xy = (0,0)
    fire_held = False
    joystick_active = False

def draw_button(rect,text):
    pygame.draw.rect(screen,(22,30,35),rect,border_radius=sc(12))
    pygame.draw.rect(screen,GRAY,rect,sc(2),border_radius=sc(12))
    t = small.render(text,True,WHITE)
    screen.blit(t,t.get_rect(center=rect.center))

def center(text,y,f=font,col=WHITE):
    t = f.render(text,True,col)
    screen.blit(t,(W//2-t.get_width()//2,y))

def shoot():
    global ammo,fire_wait,muzzle_timer,recoil
    if ammo <= 0 or fire_wait > 0:
        return

    ammo -= 1
    fire_wait = max(0.025,0.18-guns[gun_index][3]/1000)
    d = aim_dir.copy()

    if d.length():
        d.normalize_ip()
        bullets.append([
            player+d*sc(22),
            d*8,
            guns[gun_index][2]
        ])
        muzzle_timer = 0.09
        recoil = 1.0

    if sfx_enabled:
        play_sfx(SFX_SHOT)

def do_jump():
    global jump_timer,jump_velocity
    d = aim_dir.copy()
    if d.length() == 0:
        d = pygame.Vector2(0,-1)
    d.normalize_ip()
    jump_velocity = d*sc(280)
    jump_timer = .18

def reset_all():
    global unlocked,money,owned,gun_index,owned_players,player_index
    global level,level_page
    unlocked=1
    money=0
    owned={0}
    gun_index=0
    owned_players={0}
    player_index=0
    level=1
    level_page=1
    save_game()

def draw_settings_screen():
    screen.fill((12,10,14))

    for yy in range(H):
        q = yy/max(1,H)
        c = (int(12+18*q),int(7+3*q),int(12+5*q))
        pygame.draw.line(screen,c,(0,yy),(W,yy))

    center("SETTINGS",sc(30),big,WHITE)
    center("GAME CONTROLS & OPTIONS",sc(78),small,CYAN)

    items=[
        ("SFX", "ON" if sfx_enabled else "OFF"),
        ("VFX", "ON" if vfx_enabled else "OFF"),
        ("FULLSCREEN", "ON"),
        ("FPS", "60"),
        ("RESET ALL", "RESET ALL"),
    ]

    top=sc(125)
    bh=sc(50)
    gap=sc(12)

    for i,(name,val) in enumerate(items):
        r=pygame.Rect(sc(35),top+i*(bh+gap),W-sc(70),bh)
        pygame.draw.rect(screen,(25,30,37),r,border_radius=sc(10))
        pygame.draw.rect(
            screen,
            RED if name=="RESET ALL" else GRAY,
            r,sc(2),border_radius=sc(10)
        )
        screen.blit(
            small.render(name,True,WHITE),
            (r.x+sc(14),r.centery-sc(10))
        )
        vr=pygame.Rect(r.right-sc(105),r.y+sc(8),sc(90),sc(34))
        pygame.draw.rect(
            screen,
            GREEN if val!="RESET ALL" else RED,
            vr,border_radius=sc(7)
        )
        t=small.render(val,True,WHITE)
        screen.blit(t,t.get_rect(center=vr.center))

    back=pygame.Rect(sc(35),H-sc(65),sc(150),sc(45))
    draw_button(back,"BACK")

    if settings_confirm:
        ov=pygame.Surface((W,H),pygame.SRCALPHA)
        ov.fill((0,0,0,185))
        screen.blit(ov,(0,0))

        pop=pygame.Rect(sc(35),H//2-sc(105),W-sc(70),sc(210))
        pygame.draw.rect(screen,PANEL,pop,border_radius=sc(16))
        pygame.draw.rect(screen,RED,pop,sc(3),border_radius=sc(16))

        center("ARE YOU SURE?",pop.y+sc(28),font,WHITE)
        center(settings_confirm,pop.y+sc(70),small,YELLOW)

        yes=pygame.Rect(W//2-sc(100),pop.y+sc(112),sc(85),sc(42))
        close=pygame.Rect(W//2+sc(15),pop.y+sc(112),sc(85),sc(42))

        pygame.draw.rect(screen,RED,yes,border_radius=sc(8))
        pygame.draw.rect(screen,GREEN,close,border_radius=sc(8))

        yt=small.render("YES",True,WHITE)
        ct=small.render("CLOSE",True,WHITE)
        screen.blit(yt,yt.get_rect(center=yes.center))
        screen.blit(ct,ct.get_rect(center=close.center))

def handle_android_back():
    global state,shop_popup_gun,shop_popup_player,settings_confirm

    if settings_confirm:
        settings_confirm=None
        return

    if state==PLAY:
        state=MENU
    elif state==SHOP:
        shop_popup_gun=None
        shop_popup_player=None
        state=START
    elif state==SETTINGS:
        state=START
    elif state==MENU:
        state=START
    elif state in (COMPLETE,OVER):
        state=MENU
    elif state==START:
        state=START

def draw_shop_screen(dt):
    global menu_time

    prev_r=pygame.Rect(sc(12),H-sc(58),sc(95),sc(42))
    next_r=pygame.Rect(W-sc(107),H-sc(58),sc(95),sc(42))

    menu_time += dt
    screen.fill((8,8,12))

    for yy in range(H):
        q=yy/max(1,H)
        c=(int(8+18*q),int(7+3*q),int(11+5*q))
        pygame.draw.line(screen,c,(0,yy),(W,yy))

    shift=int((menu_time*sc(24))%sc(150))
    for k in range(-H,W+H,sc(78)):
        pygame.draw.line(
            screen,(72,10,20),
            (k+shift,0),(k-H+shift,H),sc(2)
        )

    ov=pygame.Surface((W,H),pygame.SRCALPHA)
    ov.fill((0,0,0,165))
    screen.blit(ov,(0,0))

    pygame.draw.rect(
        screen,PANEL,(sc(7),sc(55),W-sc(14),H-sc(70)),
        border_radius=sc(18)
    )

    title_text=["GUN SHOP","PLAYER SHOP"][min(shop_page,1)]
    screen.blit(big.render(title_text,True,WHITE),(sc(15),sc(68)))
    screen.blit(small.render(f"MONEY: {money}",True,YELLOW),(sc(15),sc(105)))
    draw_button(pygame.Rect(W-sc(58),sc(60),sc(45),sc(45)),"X")

    if shop_page==0:
        admin_msg = (
            "ADMIN GUN: UNLOCKED"
            if admin_unlocked()
            else "ADMIN GUN: LOCKED — CLEAR LV 100"
        )
        screen.blit(
            small.render(
                admin_msg,True,
                GREEN if admin_unlocked() else GRAY
            ),
            (sc(15),sc(125))
        )

        top=sc(145)
        row=sc(48)
        colw=(W-sc(30))//2

        for i,g in enumerate(guns):
            c=i%2
            r=i//2
            rr=pygame.Rect(
                sc(10)+c*colw,
                top+r*row,
                colw-sc(8),
                row-sc(6)
            )

            is_admin=(i==20)
            admin_ok=admin_unlocked()
            owned_now=(i in owned)
            selected=(gun_index==i)

            pygame.draw.rect(screen,(43,48,58),rr,border_radius=sc(8))

            border = (
                BLACK if (is_admin and not admin_ok)
                else (GREEN if owned_now else GRAY)
            )
            pygame.draw.rect(screen,border,rr,sc(2),border_radius=sc(8))

            screen.blit(
                small.render(f"{g[0]}  ${g[1]}",True,WHITE),
                (rr.x+sc(7),rr.y+sc(4))
            )
            screen.blit(
                small.render(f"DMG {g[2]}  SPD {g[3]}",True,YELLOW),
                (rr.x+sc(7),rr.y+sc(26))
            )

            status = (
                "LOCKED" if (is_admin and not admin_ok)
                else ("EQUIPPED" if selected
                      else ("OWNED" if owned_now else "BUY"))
            )
            status_col = (
                BLACK if (is_admin and not admin_ok)
                else (GREEN if selected or owned_now else RED)
            )

            status_r=pygame.Rect(
                rr.right-sc(58),rr.y+sc(5),sc(52),sc(20)
            )
            pygame.draw.rect(
                screen,status_col,status_r,border_radius=sc(5)
            )
            pygame.draw.rect(
                screen,
                WHITE if status_col!=BLACK else GRAY,
                status_r,sc(1),border_radius=sc(5)
            )

            ct=pygame.font.Font(None,max(13,sc(13))).render(
                status,True,WHITE
            )
            screen.blit(ct,ct.get_rect(center=status_r.center))

    else:
        center("5 PLAYER VERSIONS • SPEED",sc(130),small,CYAN)
        top=sc(150)
        row=sc(78)

        for i,(name,price,spd) in enumerate(players):
            rr=pygame.Rect(
                sc(18),top+i*row,W-sc(36),row-sc(10)
            )
            own=i in owned_players
            sel=i==player_index

            pygame.draw.rect(
                screen,(43,48,58),rr,border_radius=sc(10)
            )
            pygame.draw.rect(
                screen,GREEN if own else GRAY,
                rr,sc(2),border_radius=sc(10)
            )

            screen.blit(
                small.render(f"{name}   ${price}",True,WHITE),
                (rr.x+sc(10),rr.y+sc(8))
            )
            screen.blit(
                small.render(f"SPEED {spd:.1f}",True,YELLOW),
                (rr.x+sc(10),rr.y+sc(36))
            )

            status="EQUIPPED" if sel else ("OWNED" if own else "BUY")
            col=GREEN if own else RED

            sr=pygame.Rect(
                rr.right-sc(72),rr.y+sc(13),sc(62),sc(25)
            )
            pygame.draw.rect(screen,col,sr,border_radius=sc(6))
            tt=small.render(status,True,WHITE)
            screen.blit(tt,tt.get_rect(center=sr.center))

    if shop_popup_gun is not None:
        pg=shop_popup_gun
        g=guns[pg]

        ov2=pygame.Surface((W,H),pygame.SRCALPHA)
        ov2.fill((0,0,0,150))
        screen.blit(ov2,(0,0))

        popup=pygame.Rect(
            sc(28),H//2-sc(105),W-sc(56),sc(210)
        )
        pygame.draw.rect(
            screen,(28,34,42),popup,border_radius=sc(18)
        )
        pygame.draw.rect(
            screen,
            GREEN if pg in owned else (BLACK if pg==20 else RED),
            popup,sc(3),border_radius=sc(18)
        )

        center(g[0],popup.y+sc(18),font,WHITE)
        center(
            f"DMG {g[2]}   SPD {g[3]}",
            popup.y+sc(58),small,YELLOW
        )

        if pg==20 and not admin_unlocked():
            center(
                "LOCKED — COMPLETE LV 100",
                popup.y+sc(88),small,GRAY
            )
            lock_r=pygame.Rect(
                W//2-sc(105),H//2-sc(5),sc(210),sc(48)
            )
            pygame.draw.rect(screen,BLACK,lock_r,border_radius=sc(9))
            pygame.draw.rect(
                screen,GRAY,lock_r,sc(2),border_radius=sc(9)
            )
            t=small.render("LOCKED",True,GRAY)
            screen.blit(t,t.get_rect(center=lock_r.center))

        elif pg not in owned:
            buy_r=pygame.Rect(
                W//2-sc(72),H//2-sc(3),sc(144),sc(40)
            )
            pygame.draw.rect(screen,RED,buy_r,border_radius=sc(8))
            t=small.render(f"BUY ${g[1]}",True,WHITE)
            screen.blit(t,t.get_rect(center=buy_r.center))

        else:
            equip_r=pygame.Rect(
                W//2-sc(82),H//2-sc(3),sc(76),sc(40)
            )
            unequip_r=pygame.Rect(
                W//2+sc(6),H//2-sc(3),sc(76),sc(40)
            )
            for br,bc,bt in [
                (equip_r,GREEN,"EQUIP"),
                (unequip_r,RED,"UNEQUIP")
            ]:
                pygame.draw.rect(screen,bc,br,border_radius=sc(9))
                t=small.render(bt,True,WHITE)
                screen.blit(t,t.get_rect(center=br.center))

        center(
            "Tap outside to close",
            popup.bottom-sc(35),small,CYAN
        )

    if shop_popup_player is not None:
        pp=shop_popup_player
        name,price,spd=players[pp]

        popup=pygame.Rect(
            sc(28),H//2-sc(105),W-sc(56),sc(210)
        )
        pygame.draw.rect(
            screen,(28,34,42),popup,border_radius=sc(18)
        )
        pygame.draw.rect(
            screen,
            GREEN if pp in owned_players else RED,
            popup,sc(3),border_radius=sc(18)
        )

        center(name,popup.y+sc(20),font,WHITE)
        center(
            f"PRICE ${price}   SPEED {spd:.1f}",
            popup.y+sc(65),small,YELLOW
        )

        if pp not in owned_players:
            br=pygame.Rect(
                W//2-sc(72),H//2-sc(3),sc(144),sc(40)
            )
            pygame.draw.rect(screen,RED,br,border_radius=sc(8))
            t=small.render(f"BUY ${price}",True,WHITE)
            screen.blit(t,t.get_rect(center=br.center))
        else:
            er=pygame.Rect(
                W//2-sc(82),H//2-sc(3),sc(76),sc(40)
            )
            ur=pygame.Rect(
                W//2+sc(6),H//2-sc(3),sc(76),sc(40)
            )
            for br,bc,bt in [
                (er,GREEN,"EQUIP"),
                (ur,RED,"UNEQUIP")
            ]:
                pygame.draw.rect(screen,bc,br,border_radius=sc(9))
                t=small.render(bt,True,WHITE)
                screen.blit(t,t.get_rect(center=br.center))

        center(
            "Tap outside to close",
            popup.bottom-sc(35),small,CYAN
        )

    if shop_popup_gun is None and shop_popup_player is None:
        draw_button(prev_r,"BACK")
        draw_button(next_r,"NEXT")
        center(
            ["GUNS","PLAYERS"][min(shop_page,1)],
            H-sc(58),small,CYAN
        )

running=True

try:
    if MENU_MUSIC:
        MENU_MUSIC.play(loops=-1)
except Exception:
    pass

while running:
    dt=clock.tick(60)/1000
    fire_wait=max(0,fire_wait-dt)
    muzzle_timer=max(0,muzzle_timer-dt)
    recoil=max(0,recoil-dt*7)

    for fx in particles[:]:
        fx[0]+=fx[1]
        fx[1]*=.92
        fx[2]-=dt
        if fx[2]<=0:
            particles.remove(fx)

    for ev in pygame.event.get():

        if ev.type==pygame.QUIT:
            save_game()
            running=False

        if ev.type==pygame.KEYDOWN:
            if ev.key==pygame.K_ESCAPE:
                handle_android_back()
            if ev.key==pygame.K_SPACE and state==PLAY:
                shoot()
            if ev.key==pygame.K_r and state==OVER:
                start_level(level)
                state=PLAY

        if ev.type==pygame.FINGERDOWN and state==PLAY:
            pos=pygame.Vector2(ev.x*W,ev.y*H)

            if fire_btn.collidepoint(pos):
                touch_roles[ev.finger_id]='fire'
                fire_held=True
                shoot()

            elif jump_btn.collidepoint(pos):
                touch_roles[ev.finger_id]='jump'
                do_jump()

            elif pos.distance_to(joy)<sc(75):
                touch_roles[ev.finger_id]='joy'
                joystick_active=True
                joy_knob=pos

        if ev.type==pygame.FINGERMOTION and state==PLAY and ev.finger_id in touch_roles:
            pos=pygame.Vector2(ev.x*W,ev.y*H)

            if touch_roles[ev.finger_id]=='joy':
                v=pos-joy
                if v.length()>sc(45):
                    v.scale_to_length(sc(45))
                joy_knob=joy+v

        if ev.type==pygame.FINGERUP:
            role=touch_roles.pop(ev.finger_id,None)

            if role=='joy':
                joystick_active=any(
                    v=='joy' for v in touch_roles.values()
                )
                if not joystick_active:
                    joy_knob=joy.copy()

            elif role=='fire':
                fire_held=any(
                    v=='fire' for v in touch_roles.values()
                )

        if ev.type==pygame.MOUSEBUTTONDOWN:
            pos=pygame.Vector2(ev.pos)

            if state==START:
                start_rect=pygame.Rect(
                    W//2-sc(110),H//2-sc(20),sc(220),sc(65)
                )
                quit_rect=pygame.Rect(
                    W//2-sc(110),H//2+sc(55),sc(220),sc(55)
                )
                shop_rect=pygame.Rect(
                    W//2-sc(110),H//2+sc(125),sc(220),sc(55)
                )
                settings_rect=pygame.Rect(
                    W//2-sc(110),shop_rect.bottom+sc(18),
                    sc(220),sc(55)
                )

                if start_rect.collidepoint(pos):
                    level_page=max(
                        1,min(4,(max(1,unlocked)-1)//30+1)
                    )
                    state=MENU

                elif quit_rect.collidepoint(pos):
                    save_game()
                    running=False

                elif shop_rect.collidepoint(pos):
                    state=SHOP
                    shop_page=0
                    shop_popup_gun=None
                    shop_popup_player=None

                elif settings_rect.collidepoint(pos):
                    state=SETTINGS

            elif state==SETTINGS:
                if settings_confirm:
                    pop=pygame.Rect(
                        sc(35),H//2-sc(105),
                        W-sc(70),sc(210)
                    )
                    yes=pygame.Rect(
                        W//2-sc(100),pop.y+sc(112),
                        sc(85),sc(42)
                    )
                    close=pygame.Rect(
                        W//2+sc(15),pop.y+sc(112),
                        sc(85),sc(42)
                    )

                    if yes.collidepoint(pos):
                        action=settings_confirm
                        settings_confirm=None
                        if action=="RESET ALL DATA?":
                            reset_all()
                            state=START

                    elif close.collidepoint(pos):
                        settings_confirm=None

                else:
                    top=sc(125)
                    bh=sc(50)
                    gap=sc(12)

                    for i in range(5):
                        r=pygame.Rect(
                            sc(35),top+i*(bh+gap),
                            W-sc(70),bh
                        )

                        if r.collidepoint(pos):
                            if i==0:
                                sfx_enabled=not sfx_enabled
                            elif i==1:
                                vfx_enabled=not vfx_enabled
                            elif i==4:
                                settings_confirm="RESET ALL DATA?"
                            save_game()
                            break

                    back=pygame.Rect(
                        sc(35),H-sc(65),sc(150),sc(45)
                    )
                    if back.collidepoint(pos):
                        state=START

            elif state==MENU:
                if menu_close_btn.collidepoint(pos):
                    state=START
                    continue

                margin=sc(12)
                gap=sc(6)
                top=sc(118)
                bw=(W-margin*2-gap*2)//3
                bh=sc(42)

                page_start=(level_page-1)*30+1
                page_end=min(100,page_start+29)

                for i in range(page_start,page_end+1):
                    idx=i-page_start
                    lv=i
                    c=idx%3
                    r=idx//3

                    rr=pygame.Rect(
                        margin+c*(bw+gap),
                        top+r*(bh+gap),
                        bw,bh
                    )

                    if rr.collidepoint(pos) and lv<=unlocked:
                        start_level(lv)
                        state=PLAY
                        break

                back_r=pygame.Rect(
                    sc(18),H-sc(58),sc(110),sc(42)
                )
                next_r=pygame.Rect(
                    W-sc(128),H-sc(58),sc(110),sc(42)
                )

                if back_r.collidepoint(pos) and level_page>1:
                    level_page-=1
                elif next_r.collidepoint(pos) and level_page<4:
                    level_page+=1

            elif state==PLAY:
                if fire_btn.collidepoint(pos):
                    fire_held=True
                    shoot()

                elif jump_btn.collidepoint(pos):
                    do_jump()

                elif pos.distance_to(joy)<sc(65):
                    joystick_active=True
                    joy_knob=pos

            elif state==SHOP:
                close=pygame.Rect(
                    W-sc(58),sc(60),sc(45),sc(45)
                )
                prev_r=pygame.Rect(
                    sc(12),H-sc(58),sc(95),sc(42)
                )
                next_r=pygame.Rect(
                    W-sc(107),H-sc(58),sc(95),sc(42)
                )

                if shop_popup_gun is not None:
                    pg=shop_popup_gun
                    g=guns[pg]
                    popup=pygame.Rect(
                        sc(28),H//2-sc(105),
                        W-sc(56),sc(210)
                    )

                    if not popup.collidepoint(pos):
                        shop_popup_gun=None
                    else:
                        equip_r=pygame.Rect(
                            W//2-sc(82),H//2-sc(3),
                            sc(76),sc(40)
                        )
                        unequip_r=pygame.Rect(
                            W//2+sc(6),H//2-sc(3),
                            sc(76),sc(40)
                        )
                        buy_r=pygame.Rect(
                            W//2-sc(72),H//2-sc(3),
                            sc(144),sc(40)
                        )

                        if pg==20 and not admin_unlocked():
                            pass

                        elif pg not in owned and buy_r.collidepoint(pos) and money>=g[1]:
                            money-=g[1]
                            owned.add(pg)
                            gun_index=pg
                            save_game()
                            shop_popup_gun=None
                            if sfx_enabled:
                                play_sfx(SFX_BUY)

                        elif pg in owned and equip_r.collidepoint(pos):
                            gun_index=pg
                            save_game()
                            shop_popup_gun=None
                            if sfx_enabled:
                                play_sfx(SFX_BUY)

                        elif pg in owned and unequip_r.collidepoint(pos):
                            if gun_index==pg:
                                gun_index=0
                                save_game()
                            shop_popup_gun=None

                elif shop_popup_player is not None:
                    pp=shop_popup_player
                    pr=pygame.Rect(
                        sc(28),H//2-sc(105),
                        W-sc(56),sc(210)
                    )

                    if not pr.collidepoint(pos):
                        shop_popup_player=None
                    else:
                        buy_r=pygame.Rect(
                            W//2-sc(72),H//2-sc(3),
                            sc(144),sc(40)
                        )
                        equip_r=pygame.Rect(
                            W//2-sc(82),H//2-sc(3),
                            sc(76),sc(40)
                        )
                        unequip_r=pygame.Rect(
                            W//2+sc(6),H//2-sc(3),
                            sc(76),sc(40)
                        )
                        price=players[pp][1]

                        if pp not in owned_players and buy_r.collidepoint(pos) and money>=price:
                            money-=price
                            owned_players.add(pp)
                            player_index=pp
                            speed=player_speed_for_index(pp)
                            save_game()
                            shop_popup_player=None
                            if sfx_enabled:
                                play_sfx(SFX_BUY)

                        elif pp in owned_players and equip_r.collidepoint(pos):
                            player_index=pp
                            speed=player_speed_for_index(pp)
                            save_game()
                            shop_popup_player=None
                            if sfx_enabled:
                                play_sfx(SFX_BUY)

                        elif pp in owned_players and unequip_r.collidepoint(pos):
                            if player_index==pp:
                                player_index=0
                                speed=player_speed_for_index(0)
                                save_game()
                            shop_popup_player=None

                elif close.collidepoint(pos):
                    state=START

                elif prev_r.collidepoint(pos) and shop_page>0:
                    shop_page-=1

                elif next_r.collidepoint(pos) and shop_page<1:
                    shop_page+=1

                elif shop_page==0:
                    top=sc(145)
                    row=sc(48)
                    colw=(W-sc(30))//2

                    for i,g in enumerate(guns):
                        c=i%2
                        r=i//2
                        rr=pygame.Rect(
                            sc(10)+c*colw,
                            top+r*row,
                            colw-sc(8),
                            row-sc(6)
                        )
                        if rr.collidepoint(pos):
                            shop_popup_gun=i
                            break

                elif shop_page==1:
                    top=sc(150)
                    row=sc(78)

                    for i,_pl in enumerate(players):
                        rr=pygame.Rect(
                            sc(18),top+i*row,
                            W-sc(36),row-sc(10)
                        )
                        if rr.collidepoint(pos):
                            shop_popup_player=i
                            break

            elif state==COMPLETE:
                next_r=pygame.Rect(
                    W//2-sc(105),H//2+sc(10),
                    sc(210),sc(55)
                )
                restart_r=pygame.Rect(
                    W//2-sc(105),H//2+sc(75),
                    sc(210),sc(50)
                )
                menu_r=pygame.Rect(
                    W//2-sc(105),H//2+sc(135),
                    sc(210),sc(50)
                )

                if next_r.collidepoint(pos):
                    if level<100:
                        unlocked=max(unlocked,level+1)
                        save_game()
                        start_level(level+1)
                        state=PLAY
                    else:
                        state=MENU

                elif restart_r.collidepoint(pos):
                    start_level(level)
                    state=PLAY

                elif menu_r.collidepoint(pos):
                    state=MENU

            elif state==OVER:
                restart_r=pygame.Rect(
                    W//2-sc(105),H//2+sc(25),
                    sc(210),sc(58)
                )
                menu_r=pygame.Rect(
                    W//2-sc(105),H//2+sc(95),
                    sc(210),sc(50)
                )

                if restart_r.collidepoint(pos):
                    start_level(level)
                    state=PLAY
                elif menu_r.collidepoint(pos):
                    state=MENU

        if ev.type==pygame.MOUSEBUTTONUP:
            fire_held=False
            joy_knob=joy.copy()
            joystick_active=False

        if ev.type==pygame.MOUSEMOTION and ev.buttons[0] and state==PLAY and joystick_active:
            v=pygame.Vector2(ev.pos)-joy
            if v.length()>sc(45):
                v.scale_to_length(sc(45))
            joy_knob=joy+v

    if state==PLAY:
        if fire_held:
            shoot()

        if jump_timer>0:
            player+=jump_velocity*dt
            jump_timer=max(0.0,jump_timer-dt)

        move=pygame.Vector2()
        keys=pygame.key.get_pressed()

        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            move.x-=1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            move.x+=1
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            move.y-=1
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            move.y+=1

        j=joy_knob-joy
        if j.length()>sc(5):
            move=j/sc(45)

        if move.length()>1:
            move.normalize_ip()

        if move.length()>0.05:
            aim_dir=move.normalize()

        player+=move*speed
        player.x=max(sc(18),min(W-sc(18),player.x))
        player.y=max(sc(70),min(H-sc(145),player.y))

        spawn_timer-=dt

        if is_boss_level(level):
            if spawned==0 and not enemies and spawn_timer<=0:
                bhp=boss_hp_for_level(level)
                enemies.append({
                    "p":spawn_outside(),
                    "role":"boss",
                    "cd":0,
                    "hp":bhp,
                    "max_hp":bhp,
                    "damage":boss_damage_for_level(level)
                })
                spawned=1

        elif spawned<total and not enemies and spawn_timer<=0:
            amount=min(random.randint(3,4),total-spawned)

            for _ in range(amount):
                enemies.append({
                    "p":spawn_outside(),
                    "role":random.choice(["tower","tower","player"]),
                    "cd":0
                })

            spawned+=amount
            spawn_timer=2.8

        for e in enemies:
            e["cd"]-=dt

            if e["role"]=="boss":
                d=tower-e["p"]

                if d.length()>sc(32):
                    e["p"]+=d.normalize()*(1.15+level*.018)
                elif e["cd"]<=0:
                    tower_hp=max(0,tower_hp-e["damage"])
                    e["cd"]=.75

            elif e["role"]=="tower":
                d=tower-e["p"]

                if d.length()>sc(28):
                    e["p"]+=d.normalize()*(1.05+level*.018)
                elif e["cd"]<=0:
                    tower_hp=max(0,tower_hp-10)
                    e["cd"]=.8

            else:
                d=player-e["p"]

                if d.length()>sc(28):
                    e["p"]+=d.normalize()*(1.08+level*.01)
                elif e["cd"]<=0:
                    player_hp=max(0,player_hp-8)
                    e["cd"]=1.0

        for b in bullets[:]:
            b[0]+=b[1]

            if not pygame.Rect(
                0,sc(65),W,H-sc(145)
            ).collidepoint(b[0]):
                bullets.remove(b)
                continue

            hit=None

            for e in enemies:
                if b[0].distance_to(e["p"])<sc(18):
                    hit=e
                    break

            if hit:
                bullets.remove(b)

                if vfx_enabled:
                    for _ in range(10 if hit.get("role")=="boss" else 6):
                        a=random.random()*math.tau
                        sp=random.uniform(1.5,4.0)
                        particles.append([
                            hit["p"].copy(),
                            pygame.Vector2(
                                math.cos(a)*sp,
                                math.sin(a)*sp
                            ),
                            random.uniform(.25,.5),
                            RED if hit.get("role")=="boss" else YELLOW
                        ])

                if sfx_enabled:
                    play_sfx(
                        SFX_BOSS if hit.get("role")=="boss"
                        else SFX_HIT
                    )

                damage=guns[gun_index][2]

                if hit.get("role")=="boss":
                    hit["hp"]-=damage

                    if hit["hp"]<=0:
                        enemies.remove(hit)
                        boss_reward=boss_reward_for_level(level)
                        last_boss_reward=boss_reward
                        money+=boss_reward
                        kills+=1

                else:
                    enemies.remove(hit)
                    money+=25
                    kills+=1

                speed=player_speed_for_index(player_index)
                save_game()

        power_spawn_timer-=dt

        if power_spawn_timer<=0:
            if not powers:
                powers.append([
                    spawn_inside_base(),
                    random.choice(["green","yellow","purple"])
                ])
            power_spawn_timer=random.uniform(10.0,15.0)

        for po in powers[:]:
            if player.distance_to(po[0])<sc(30):
                if po[1]=="green":
                    player_hp=100
                elif po[1]=="yellow":
                    ammo=50
                else:
                    tower_hp=500
                powers.remove(po)

        if player_hp<=0 or tower_hp<=0:
            state=OVER

        elif spawned>=total and not enemies:
            if level<100:
                unlocked=max(unlocked,level+1)
            else:
                owned.add(20)
                gun_index=20

            save_game()
            state=COMPLETE

    if state==START:
        menu_time += dt
        screen.fill((7,7,10))

        for yy in range(H):
            q=yy/max(1,H)
            c=(int(7+20*q),int(5+3*q),int(9+5*q))
            pygame.draw.line(screen,c,(0,yy),(W,yy))

        shift=int((menu_time*sc(34))%sc(160))

        for k in range(-H,W+H,sc(90)):
            pygame.draw.line(
                screen,(80,10,20),
                (k+shift,0),(k-H+shift,H),sc(3)
            )

        pygame.draw.circle(
            screen,(90,15,25),
            (W//2,H//2-sc(70)),sc(125),sc(3)
        )
        pygame.draw.circle(
            screen,(35,8,14),
            (W//2,H//2-sc(70)),sc(92)
        )

        for i in range(30):
            x=(i*97+int(menu_time*22))%W
            y=(i*53)%H
            pygame.draw.circle(screen,(120,28,38),(x,y),sc(2))

        center("BATTLE ZONE",H//2-sc(170),title,WHITE)
        center("BASE DEFENSE",H//2-sc(105),font,GREEN)
        center(
            f"Saved Money: {money}",
            H//2-sc(72),small,YELLOW
        )

        start_r=pygame.Rect(
            W//2-sc(110),H//2-sc(20),sc(220),sc(65)
        )
        quit_r=pygame.Rect(
            W//2-sc(110),H//2+sc(55),sc(220),sc(55)
        )
        shop_r=pygame.Rect(
            W//2-sc(110),H//2+sc(125),sc(220),sc(55)
        )
        settings_rect=pygame.Rect(
            W//2-sc(110),shop_r.bottom+sc(18),
            sc(220),sc(55)
        )

        draw_button(start_r,"PLAY")
        draw_button(quit_r,"QUIT")
        draw_button(shop_r,"SHOP")
        draw_button(settings_rect,"SETTINGS")

        t=small.render("Made by Arhaan Alam",True,YELLOW)
        screen.blit(
            t,t.get_rect(
                center=(W//2,settings_rect.bottom+sc(20))
            )
        )

    elif state==SHOP:
        draw_shop_screen(dt)

    elif state==SETTINGS:
        draw_settings_screen()

    elif state==MENU:
        screen.fill((18,24,29))

        center("BATTLE ZONE",sc(18),big,WHITE)
        center("LEVEL MENU",sc(58),font,GREEN)
        center(
            f"MONEY SAVED: {money}",
            sc(88),small,YELLOW
        )
        center(
            f"PAGE {level_page}/4  •  100 LEVELS",
            sc(108),small,CYAN
        )

        pygame.draw.circle(
            screen,RED,
            (menu_close_btn.centerx,menu_close_btn.centery),
            sc(20)
        )
        pygame.draw.line(
            screen,WHITE,
            (menu_close_btn.x+sc(13),menu_close_btn.y+sc(13)),
            (menu_close_btn.right-sc(13),menu_close_btn.bottom-sc(13)),
            sc(4)
        )
        pygame.draw.line(
            screen,WHITE,
            (menu_close_btn.right-sc(13),menu_close_btn.y+sc(13)),
            (menu_close_btn.x+sc(13),menu_close_btn.bottom-sc(13)),
            sc(4)
        )

        margin=sc(12)
        gap=sc(6)
        top=sc(130)
        bw=(W-margin*2-gap*2)//3
        bh=sc(42)

        page_start=(level_page-1)*30+1
        page_end=min(100,page_start+29)

        for lv in range(page_start,page_end+1):
            idx=lv-page_start
            c=idx%3
            r=idx//3

            rr=pygame.Rect(
                margin+c*(bw+gap),
                top+r*(bh+gap),
                bw,bh
            )

            boss=is_boss_level(lv)

            if lv<=unlocked:
                pygame.draw.rect(
                    screen,(45,105,65),rr,border_radius=sc(8)
                )
                pygame.draw.rect(
                    screen,
                    RED if boss else GREEN,
                    rr,sc(3 if boss else 2),
                    border_radius=sc(8)
                )
                txt=f"LV {lv}" + (" ✓" if lv<unlocked else "")
                col=WHITE
            else:
                pygame.draw.rect(
                    screen,(45,48,54),rr,border_radius=sc(8)
                )
                pygame.draw.rect(
                    screen,
                    RED if boss else GRAY,
                    rr,sc(2),border_radius=sc(8)
                )
                txt=f"LV {lv} LOCK"
                col=GRAY

            t=small.render(txt,True,col)
            screen.blit(
                t,
                t.get_rect(
                    center=(
                        rr.centerx,
                        rr.centery-sc(4) if boss else rr.centery
                    )
                )
            )

            if boss:
                dtxt=small.render("DANGER",True,RED)
                screen.blit(
                    dtxt,
                    dtxt.get_rect(
                        center=(rr.centerx,rr.bottom-sc(10))
                    )
                )

        back_r=pygame.Rect(
            sc(18),H-sc(58),sc(110),sc(42)
        )
        next_r=pygame.Rect(
            W-sc(128),H-sc(58),sc(110),sc(42)
        )

        draw_button(back_r,"BACK")
        draw_button(next_r,"NEXT")
        center(
            f"LEVELS {page_start}-{page_end}",
            H-sc(58),small,CYAN
        )

    else:
        screen.fill(GRASS)

        random.seed(1200+level)
        for _ in range(280):
            gx=random.randrange(W)
            gy=random.randrange(sc(70),H-sc(145))
            pygame.draw.line(
                screen,(45,112,64),
                (gx,gy),
                (gx+random.randint(-2,2),gy-sc(random.randint(2,6))),
                1
            )
        random.seed()

        for x in range(0,W,sc(45)):
            pygame.draw.line(
                screen,GRID,
                (x,sc(65)),(x,H-sc(145))
            )

        for y in range(sc(70),H-sc(145),sc(45)):
            pygame.draw.line(
                screen,GRID,
                (0,y),(W,y)
            )

        pygame.draw.circle(
            screen,(58,128,76),
            (int(base.x),int(base.y)),base_r
        )
        pygame.draw.circle(
            screen,(88,165,98),
            (int(base.x),int(base.y)),
            base_r-sc(9),sc(3)
        )
        pygame.draw.circle(
            screen,(35,82,48),
            (int(base.x),int(base.y)),
            base_r-sc(22),sc(3)
        )

        for a in range(0,360,30):
            rad=math.radians(a)
            bx=base.x+math.cos(rad)*(base_r-sc(13))
            by=base.y+math.sin(rad)*(base_r-sc(13))
            pygame.draw.circle(
                screen,(120,185,115),
                (int(bx),int(by)),sc(3)
            )

        pygame.draw.circle(
            screen,(220,225,230),
            (int(tower.x),int(tower.y)),sc(38)
        )
        pygame.draw.circle(
            screen,(250,250,250),
            (int(tower.x),int(tower.y)),sc(30)
        )
        pygame.draw.rect(
            screen,(190,195,200),
            (tower.x-sc(12),tower.y-sc(35),sc(24),sc(70)),
            border_radius=sc(4)
        )
        pygame.draw.rect(
            screen,(245,245,245),
            (tower.x-sc(8),tower.y-sc(29),sc(16),sc(58)),
            border_radius=sc(3)
        )
        pygame.draw.circle(
            screen,(150,155,160),
            (int(tower.x),int(tower.y)),sc(9)
        )

        bar=pygame.Rect(
            tower.x-sc(55),tower.y-sc(62),sc(110),sc(10)
        )
        pygame.draw.rect(screen,BLACK,bar)
        pygame.draw.rect(
            screen,RED,
            (
                bar.x+sc(2),
                bar.y+sc(2),
                int((bar.w-sc(4))*tower_hp/500),
                sc(6)
            )
        )
        center(
            f"TOWER {tower_hp}/500",
            int(tower.y)+sc(42),small,WHITE
        )

        for po in powers:
            col={
                "green":GREEN,
                "yellow":YELLOW,
                "purple":PURPLE
            }[po[1]]

            pygame.draw.circle(
                screen,col,
                (int(po[0].x),int(po[0].y)),sc(15)
            )
            pygame.draw.circle(
                screen,WHITE,
                (int(po[0].x),int(po[0].y)),sc(5)
            )

        for e in enemies:
            if e.get("role")=="boss":
                bx,by=int(e["p"].x),int(e["p"].y)
                pygame.draw.circle(
                    screen,(90,18,25),(bx,by),sc(27)
                )
                pygame.draw.circle(
                    screen,RED,(bx,by),sc(22),sc(3)
                )
                draw_skull((bx,by),sc(24),WHITE)

                hb=pygame.Rect(
                    bx-sc(32),by-sc(40),sc(64),sc(7)
                )
                pygame.draw.rect(screen,BLACK,hb,border_radius=sc(3))
                pygame.draw.rect(
                    screen,RED,
                    (
                        hb.x+1,hb.y+1,
                        max(1,int(
                            (hb.w-2)*e["hp"]/e["max_hp"]
                        )),
                        hb.h-2
                    ),
                    border_radius=sc(2)
                )
            else:
                col=RED if e["role"]=="tower" else ORANGE
                pygame.draw.circle(
                    screen,col,
                    (int(e["p"].x),int(e["p"].y)),sc(15)
                )

        for b in bullets:
            pygame.draw.circle(
                screen,YELLOW,
                (int(b[0].x),int(b[0].y)),sc(5)
            )

        if jump_timer>0:
            pygame.draw.circle(
                screen,CYAN,
                (int(player.x),int(player.y)),sc(27),sc(2)
            )

        pygame.draw.circle(
            screen,BLUE,
            (int(player.x),int(player.y)),sc(18)
        )
        pygame.draw.circle(
            screen,(180,220,255),
            (int(player.x-sc(5)),int(player.y-sc(6))),sc(6)
        )

        d=aim_dir.copy()
        if d.length()==0:
            d=pygame.Vector2(0,-1)
        d.normalize_ip()

        perp=pygame.Vector2(-d.y,d.x)
        tail=player+d*sc(18)
        tip=player+d*sc(36)

        pygame.draw.line(
            screen,RED,
            (int(tail.x),int(tail.y)),
            (int(tip.x),int(tip.y)),sc(4)
        )

        left=tip-d*sc(9)+perp*sc(7)
        right=tip-d*sc(9)-perp*sc(7)

        pygame.draw.polygon(
            screen,RED,
            [
                (int(tip.x),int(tip.y)),
                (int(left.x),int(left.y)),
                (int(right.x),int(right.y))
            ]
        )

        if vfx_enabled:
            for fx in particles:
                pygame.draw.circle(
                    screen,fx[3],
                    (int(fx[0].x),int(fx[0].y)),
                    max(1,sc(int(4*min(1,fx[2]*3))))
                )

        d=aim_dir.copy()
        if d.length()==0:
            d=pygame.Vector2(0,-1)
        d.normalize_ip()

        gs=player+d*sc(8)
        ge=player+d*sc(max(24,28-int(recoil*7)))

        pygame.draw.line(
            screen,(20,22,26),
            (int(gs.x),int(gs.y)),
            (int(ge.x),int(ge.y)),sc(8)
        )

        if muzzle_timer>0 and vfx_enabled:
            tip=player+d*sc(32)
            pygame.draw.circle(
                screen,YELLOW,
                (int(tip.x),int(tip.y)),sc(9)
            )
            pygame.draw.circle(
                screen,WHITE,
                (int(tip.x),int(tip.y)),sc(4)
            )

        pygame.draw.rect(
            screen,(15,19,24),
            (0,0,W,sc(65))
        )

        screen.blit(
            small.render(f"LV {level}/100",True,WHITE),
            (sc(8),sc(7))
        )
        screen.blit(
            small.render(f"HP {player_hp}/100",True,WHITE),
            (sc(8),sc(35))
        )
        screen.blit(
            small.render(f"MONEY {money}",True,YELLOW),
            (sc(105),sc(7))
        )
        screen.blit(
            small.render(f"AMMO {ammo}",True,WHITE),
            (sc(105),sc(35))
        )
        screen.blit(
            small.render(f"ENEMIES {len(enemies)}",True,WHITE),
            (sc(205),sc(35))
        )

        if is_boss_level(level):
            boss=next(
                (e for e in enemies if e.get("role")=="boss"),
                None
            )
            bhp=boss["hp"] if boss else 0
            bmax=boss["max_hp"] if boss else boss_hp_for_level(level)

            label=small.render(
                f"☠ BOSS  HP {bhp}/{bmax}  DMG 35",
                True,RED
            )
            screen.blit(
                label,
                label.get_rect(center=(W//2,sc(82)))
            )

            bar=pygame.Rect(
                sc(45),sc(101),W-sc(90),sc(10)
            )
            pygame.draw.rect(
                screen,BLACK,bar,border_radius=sc(5)
            )

            fill=max(
                0,
                int((bar.w-sc(4))*bhp/max(1,bmax))
            )
            pygame.draw.rect(
                screen,RED,
                (bar.x+sc(2),bar.y+sc(2),fill,sc(6)),
                border_radius=sc(3)
            )

        pygame.draw.circle(
            screen,(25,29,35),
            (int(joy.x),int(joy.y)),sc(55)
        )
        pygame.draw.circle(
            screen,(75,80,90),
            (int(joy_knob.x),int(joy_knob.y)),sc(24)
        )

        draw_button(fire_btn,"FIRE")
        draw_button(jump_btn,"JUMP")

        if state==COMPLETE:
            ov=pygame.Surface((W,H),pygame.SRCALPHA)
            ov.fill((0,0,0,175))
            screen.blit(ov,(0,0))

            center(
                "LEVEL COMPLETE!",
                H//2-sc(110),big,GREEN
            )
            center(
                f"LV {level} CLEARED",
                H//2-sc(58),font,WHITE
            )

            if last_boss_reward>0:
                center(
                    f"BOSS REWARD +{last_boss_reward} GOLD",
                    H//2-sc(25),small,YELLOW
                )

            if level==100:
                center(
                    "ADMIN GUN UNLOCKED!",
                    H//2-sc(25),small,YELLOW
                )

            if level<100:
                draw_button(
                    pygame.Rect(
                        W//2-sc(105),H//2+sc(10),
                        sc(210),sc(55)
                    ),
                    "NEXT GAME"
                )
            else:
                draw_button(
                    pygame.Rect(
                        W//2-sc(105),H//2+sc(10),
                        sc(210),sc(55)
                    ),
                    "FINISH"
                )

            draw_button(
                pygame.Rect(
                    W//2-sc(105),H//2+sc(75),
                    sc(210),sc(50)
                ),
                "RESET ALL"
            )
            draw_button(
                pygame.Rect(
                    W//2-sc(105),H//2+sc(135),
                    sc(210),sc(50)
                ),
                "LEVEL MENU"
            )

        if state==OVER:
            ov=pygame.Surface((W,H),pygame.SRCALPHA)
            ov.fill((0,0,0,175))
            screen.blit(ov,(0,0))

            center(
                "GAME OVER",
                H//2-sc(105),big,RED
            )
            center(
                "PLAYER OR TOWER DEFEATED",
                H//2-sc(55),small,WHITE
            )

            draw_button(
                pygame.Rect(
                    W//2-sc(105),H//2+sc(25),
                    sc(210),sc(58)
                ),
                "RESET ALL"
            )
            draw_button(
                pygame.Rect(
                    W//2-sc(105),H//2+sc(95),
                    sc(210),sc(50)
                ),
                "LEVEL MENU"
            )

    save_game()
    pygame.display.flip()

try:
    if MENU_MUSIC:
        MENU_MUSIC.stop()
except Exception:
    pass

pygame.quit()
sys.exit()
