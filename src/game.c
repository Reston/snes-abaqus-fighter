/* Abaqus: After Hours — native SNES fighting game.
 * Original game code; PVSnesLib supplies hardware, input and SPC services.
 * Logic runs at the NTSC vertical blank cadence. All coordinates are 12.4 fixed point.
 */
#include <snes.h>
#include "assets.h"
#include "characters.h"
#include "menu_portraits.h"

#define TITLE 0
#define SELECT 1
#define ARENA 2
#define FIGHT 3
#define RESULT 4
#define HP_MAX 128
#define ENERGY_MAX 96
#define FLOOR 201
#define PUNCHES (KEY_Y|KEY_X|KEY_L)
#define ATTACKS (PUNCHES|KEY_B|KEY_A|KEY_R)
#define TRACE ((volatile u16 *)0x7fff00)

/* Native fighter render contract (shared with tools/fighter_assets.py). */
#define ACTOR_FRAME_W 96
#define ACTOR_FRAME_H 80
#define ACTOR_ROW_BYTES 384
#define ACTOR_ROW_STRIDE_BYTES 512
#define ACTOR_POSE_BYTES 3840
#define ACTOR_VRAM0 0x6000
#define ACTOR_VRAM1 0x6a00
#define ACTOR_OAM0 0
#define ACTOR_OAM1 128
#define OAM_SHADOW_BASE 256
#define OAM_EFFECT_BASE 276
#define OAM_WAVE_BASE 280

typedef struct {
    s16 x, y, vy;
    u16 keys, oldkeys;
    u8 id, face, hp, energy, action, tick, connected;
    u8 hurt, guard, duck, walking, pose, oldpose, won;
    u8 motion, downbuffer, combo, combotime, counter;
} Fighter;
typedef struct { s16 x,y; u8 active,face,life,owner,speed,low; } Wave;

Fighter fighters[2];
Wave waves[2];
/* Cached for the live match; menu/trace code still resolves IDs explicitly. */
const CharacterProfile *combatProfiles[2];
u16 ui[1024];
u16 frame, randomseed, pad0, pad1, edge0, edge1;
u8 screen, mode, difficulty, menu, selected, selected2, selectPlayer, arena;
u8 arcade, roundNumber, seconds, secondTick, intro, roundEnd, winner, paused;
u8 hitstop, shake, flash, fxLife, fxX, fxY, fxType, resultWin, champion;
u8 hudDirty, bannerDirty, fullDirty, musicIndex, musicOn;
u8 cpuTick;
u8 portraitDirty, portraitId;
u8 actorUploadDirty;
u8 *actorUploadSource;
u16 actorUploadDestination;
u8 hudHp[2], hudEnergy[2], hudWins[2], hudSeconds;
brrsamples sounds[4];
extern char SOUNDBANK__;
extern void drawActorFast(u16 byteSlot,s16 x,s16 y,u8 flip,u8 palette);
extern void uploadActor(u8 *source,u16 destination);

const char arenaNames[3][12] = {"LAS CONDES","EL CASTILLO","LA OFICINA"};
const u8 power[12] = {3,4,2,3,5,4,4,4,2,3,3,4};
const u8 startup[10] = {0,4,6,9,5,7,10,10,6,4};
const u8 active[10] = {0,3,4,5,4,5,6,1,8,1};
const u8 recovery[10] = {0,9,12,18,10,15,21,23,24,20};
const u8 damage[10] = {0,7,10,15,8,12,16,15,18,18};
const u8 reach[10] = {0,28,33,38,35,41,46,0,31,22};

const CharacterProfile *profileFor(u8 id) {
    /* Keep profile selection explicit for 816-tcc and for trace readability. */
    switch(id) {
    case 0:return &characterProfiles[0];
    case 1:return &characterProfiles[1];
    case 2:return &characterProfiles[2];
    case 3:return &characterProfiles[3];
    case 4:return &characterProfiles[4];
    case 5:return &characterProfiles[5];
    case 6:return &characterProfiles[6];
    case 7:return &characterProfiles[7];
    case 8:return &characterProfiles[8];
    case 9:return &characterProfiles[9];
    case 10:return &characterProfiles[10];
    default:return &characterProfiles[11];
    }
}

u8 attackStartup(const CharacterProfile *c,u8 action) {
    if(action==7)return c->specialStartup;
    if(action>=1 && action<=6)return c->normalStartup[action-1];
    return startup[action];
}
u8 attackActive(const CharacterProfile *c,u8 action) {
    if(action==7)return c->specialActive;
    return active[action];
}
u8 attackRecovery(const CharacterProfile *c,u8 action) {
    if(action==7)return c->specialRecovery;
    if(action>=1 && action<=6)return c->normalRecovery[action-1];
    return recovery[action];
}
u8 attackDamage(const CharacterProfile *c,u8 id,u8 action) {
    if(action==7)return c->specialDamage+power[id]-2;
    if(action==9)return c->throwDamage+power[id]-2;
    if(action>=1 && action<=6)return c->normalDamage[action-1]+power[id]-2;
    return damage[action]+power[id]-2;
}
u8 attackReach(const CharacterProfile *c,u8 action) {
    if(action==7)return c->specialReach;
    if(action==9)return c->throwRange;
    if(action>=1 && action<=6)return c->normalReach[action-1];
    return reach[action];
}

u16 rng(void) { randomseed = randomseed * 109 + 89; return randomseed; }
s16 abs16(s16 v) { return v<0 ? -v:v; }
u8 *fighterData(u8 id) {
    switch(id) {
    case 0:return &fighter00; case 1:return &fighter01; case 2:return &fighter02;
    case 3:return &fighter03; case 4:return &fighter04; case 5:return &fighter05;
    case 6:return &fighter06; case 7:return &fighter07; case 8:return &fighter08;
    case 9:return &fighter09; case 10:return &fighter10; default:return &fighter11;
    }
}
u8 *fighterPalette(u8 id) {
    switch(id) {
    case 0:return &fighter00_pal; case 1:return &fighter01_pal; case 2:return &fighter02_pal;
    case 3:return &fighter03_pal; case 4:return &fighter04_pal; case 5:return &fighter05_pal;
    case 6:return &fighter06_pal; case 7:return &fighter07_pal; case 8:return &fighter08_pal;
    case 9:return &fighter09_pal; case 10:return &fighter10_pal; default:return &fighter11_pal;
    }
}
u8 *fighterDataB(u8 id) {
    switch(id) {
    case 0:return &fighter00b; case 1:return &fighter01b; case 2:return &fighter02b;
    case 3:return &fighter03b; case 4:return &fighter04b; case 5:return &fighter05b;
    case 6:return &fighter06b; case 7:return &fighter07b; case 8:return &fighter08b;
    case 9:return &fighter09b; case 10:return &fighter10b; default:return &fighter11b;
    }
}

void put(u8 x,u8 y,u16 t) { if(x<32 && y<32) ui[(u16)y*32+x]=t|0x2000; }
void word(u8 x,u8 y,const char *s) { while(*s && x<32) put(x++,y,*s++); }
void center(u8 y,const char *s) { u8 n=0; const char *p=s; while(*p++)n++; word((32-n)/2,y,s); }
void number(u8 x,u8 y,u8 n) { put(x,y,'0'+n/10); put(x+1,y,'0'+n%10); }
void clearUi(void) { u16 i; for(i=0;i<1024;i++)ui[i]=0; fullDirty=1; }
void clearBanner(void) { u16 i; for(i=9*32;i<14*32;i++)ui[i]=0; bannerDirty=1; }
void panel(u8 y,u8 rows) { u16 i; for(i=(u16)y*32;i<(u16)(y+rows)*32;i++)ui[i]=128|0x2000; }
void cursor(u8 x,u8 y,u8 w,u8 h) {
    u8 i;
    put(x,y,149);put(x+w-1,y,150);put(x,y+h-1,151);put(x+w-1,y+h-1,152);
    for(i=1;i<w-1;i++){put(x+i,y,154);put(x+i,y+h-1,154|0x8000);}
    for(i=1;i<h-1;i++){put(x,y+i,153);put(x+w-1,y+i,153|0x4000);}
}
void sound(u8 n) { if(musicOn)spcPlaySound(n); }
void music(u8 index) {
    if(musicIndex==index)return;
    spcStop();spcLoad(index);spcSetModuleVolume(86);spcPlay(0);musicIndex=index;
}
void commonScreen(void) {
    portraitDirty=0;
    actorUploadDirty=0;
    oamClear(0,128);
    dmaCopyVram(&ui_tiles,0x4000,UI_TILES_SIZE);
    dmaCopyCGram(&ui_pal,0,UI_PAL_SIZE);
    bgSetGfxPtr(0,0x0000);bgSetMapPtr(0,0x3800,SC_32x32);
    bgSetGfxPtr(1,0x4000);bgSetMapPtr(1,0x5800,SC_32x32);
    setMode(BG_MODE1,0);bgSetEnable(0);bgSetEnable(1);bgSetDisable(2);
    /* SNES display begins on scanline 1: offset -1 preserves the top glyph row. */
    bgSetScroll(0,0,511);bgSetScroll(1,0,511);
    clearUi();
}
void loadBackground(u8 which) {
    switch(which) {
    case 0:dmaCopyVram(&stage0_tiles,0,STAGE0_TILES_SIZE);dmaCopyVram(&stage0_map,0x3800,2048);dmaCopyCGram(&stage0_pal,32,192);break;
    case 1:dmaCopyVram(&stage1_tiles,0,STAGE1_TILES_SIZE);dmaCopyVram(&stage1_map,0x3800,2048);dmaCopyCGram(&stage1_pal,32,192);break;
    case 2:dmaCopyVram(&stage2_tiles,0,STAGE2_TILES_SIZE);dmaCopyVram(&stage2_map,0x3800,2048);dmaCopyCGram(&stage2_pal,32,192);break;
    case 3:dmaCopyVram(&title_tiles,0,TITLE_TILES_SIZE);dmaCopyVram(&title_map,0x3800,2048);dmaCopyCGram(&title_pal,32,192);break;
    case 4:dmaCopyVram(&select_tiles,0,SELECT_TILES_SIZE);dmaCopyVram(&select_map,0x3800,2048);dmaCopyCGram(&select_pal,32,192);break;
    default:dmaCopyVram(&arenas_tiles,0,ARENAS_TILES_SIZE);dmaCopyVram(&arenas_map,0x3800,2048);dmaCopyCGram(&arenas_pal,32,192);break;
    }
}
void finishScreen(void) { dmaCopyVram((u8 *)ui,0x5800,2048);fullDirty=0;setScreenOn(); }
void drawTitle(void) {
    clearUi();
    word(9,20,"ARCADE SHIFT");word(9,22,"LOCAL VERSUS");word(9,24,"TRAINING");
    word(7,20+menu*2,">");word(3,25,"L/R LEVEL");put(13,25,'1'+difficulty);
    word(18,25,difficulty==0?"EASY":(difficulty==1?"NORMAL":"HARD"));
}
void showTitle(void) {
    setScreenOff();screen=TITLE;commonScreen();loadBackground(3);paused=0;
    drawTitle();
    music(0);finishScreen();
}
void drawSelect(void) {
    u8 id,x,y,family;
    clearUi();id=selectPlayer ? selected2:selected;
    cursor(1+(id%4)*5,6+(id/4)*6,5,6);
    /* Dedicated source-master portrait: eight by ten BG2 tiles. */
    for(y=0;y<10;y++)for(x=0;x<8;x++)
        ui[(u16)(y+6)*32+x+23]=(160+(u16)y*8+x)|0x2400;
    word(1,5,selectPlayer ? "PLAYER 2":"PLAYER 1");
    word(22,17,characterNames[id]);
    family=profileFor(id)->specialFamily;
    if(family==SPECIAL_PROJECTILE)word(22,19,"PROJECTILE");
    else if(family==SPECIAL_RUSH)word(22,19,"RUSH");
    else if(family==SPECIAL_GROUNDWAVE)word(22,19,"LOW WAVE");
    else word(22,19,"RISING");
    word(22,21,"POWER");put(29,21,'0'+power[id]);
    word(22,23,"SPEED");number(29,23,profileFor(id)->walkSpeed);
    center(25,characterSpecialNames[id]);
    center(27,"D-PAD SELECT  A OK  B BACK");
    portraitId=id;portraitDirty=1;fullDirty=1;
}
void uploadMenuPortrait(void) {
    dmaCopyVram(menuPortraitTiles(portraitId),0x4a00,2560);
    dmaCopyCGram(menuPortraitPalette(portraitId),16,32);
    portraitDirty=0;
}
void showSelect(void) {
    setScreenOff();screen=SELECT;arcade=0;champion=0;commonScreen();loadBackground(4);selectPlayer=0;drawSelect();uploadMenuPortrait();music(0);finishScreen();
}
void drawArenas(void) { clearUi();cursor(1,5+arena*7,30,7);fullDirty=1; }
void showArenas(void) { setScreenOff();screen=ARENA;commonScreen();loadBackground(5);drawArenas();finishScreen(); }

void hud(void) {
    u8 p,i,filled,amount,x,first,last,old;
    if(hudSeconds!=seconds){number(15,0,seconds);hudSeconds=seconds;hudDirty=1;}
    for(p=0;p<2;p++) {
        if(hudHp[p]!=fighters[p].hp) {
            hudHp[p]=fighters[p].hp;
            amount=((u16)fighters[p].hp*88)>>7;
            for(i=0;i<11;i++) {
                filled=amount>8 ? 8:amount;
                x=p ? 30-i:1+i;
                ui[32+x]=(129+filled)|(p ? 0x6000:0x2000);
                amount-=filled;
            }
            hudDirty=1;
        }
        amount=fighters[p].energy;
        old=hudEnergy[p];
        if(old!=amount) {
            /* Regeneration usually changes one partial tile. Avoid rebuilding
             * two complete bars on every sixteenth simulation tick. */
            if(old==255){first=0;last=11;}
            else {
                first=(old<amount?old:amount)>>3;
                last=(old>amount?old:amount)>>3;
                if(last>11)last=11;
            }
            hudEnergy[p]=amount;
            for(i=first;i<=last;i++) {
                filled=amount>i*8?amount-i*8:0;
                if(filled>8)filled=8;
                ui[96+(p ? 30-i:1+i)]=(138+filled)|(p ? 0x6000:0x2000);
            }
            hudDirty=1;
        }
        if(hudWins[p]!=fighters[p].won) {
            hudWins[p]=fighters[p].won;
            ui[64+(p?29:1)]=(fighters[p].won>0?147:148)|0x2000;ui[64+(p?30:2)]=(fighters[p].won>1?147:148)|0x2000;
            hudDirty=1;
        }
    }
}
void resetRound(void) {
    u8 p;
    for(p=0;p<2;p++) {
        fighters[p].x=(p ? 190:66)*16;fighters[p].y=0;fighters[p].vy=0;
        fighters[p].hp=HP_MAX;fighters[p].energy=64;fighters[p].face=p?0:1;
        fighters[p].action=0;fighters[p].tick=0;fighters[p].connected=0;
        fighters[p].hurt=0;fighters[p].guard=0;fighters[p].duck=0;fighters[p].walking=0;
        fighters[p].oldpose=255;fighters[p].pose=0;fighters[p].combo=0;fighters[p].combotime=0;
        fighters[p].motion=0;fighters[p].downbuffer=0;fighters[p].keys=0;fighters[p].oldkeys=0;
        waves[p].active=0;waves[p].low=0;waves[p].speed=0;
    }
    seconds=99;secondTick=0;intro=110;roundEnd=0;hitstop=0;shake=0;fxLife=0;
    hudHp[0]=255;hudHp[1]=255;hudEnergy[0]=255;hudEnergy[1]=255;
    hudWins[0]=255;hudWins[1]=255;hudSeconds=255;
    panel(0,5);word(1,0,characterNames[fighters[0].id]);word(20,0,characterNames[fighters[1].id]);
    put(15,1,'K');put(16,1,'O');word(13,2,"ROUND");put(19,2,'0'+roundNumber);
    if(mode==2)word(12,4,"TRAINING");
    else word(12,4,mode==1 ? "P1 VS P2":"P1 VS CPU");
    clearBanner();panel(10,3);center(10,"GET READY");center(12,arenaNames[arena]);hud();
}
void beginMatch(void) {
    u8 i;
    setScreenOff();screen=FIGHT;commonScreen();loadBackground(arena);
    fighters[0].id=selected;
    fighters[1].id=mode==0 ? (selected+1+arcade)%12:selected2;
    combatProfiles[0]=profileFor(fighters[0].id);combatProfiles[1]=profileFor(fighters[1].id);
    fighters[0].won=0;fighters[1].won=0;roundNumber=1;paused=0;
    dmaCopyCGram(fighterPalette(fighters[0].id),128,32);dmaCopyCGram(fighterPalette(fighters[1].id),144,32);
    dmaCopyCGram(&effects_pal,160,32);dmaCopyVram(&effects,0x7800,EFFECTS_SIZE);
    oamInitGfxAttr(0x6000,OBJ_SIZE8_L16);
    /* Clear the sixteen packed high-table bytes covering both padded actor
     * blocks.  drawActorFast restores the 16x16 size bit and signed X9 bit
     * for each of the thirty live entries on every render. */
    for(i=0;i<16;i++)oamMemory[512+i]=0;
    resetRound();panel(26,2);center(26,"6 BUTTONS / DOWN+P: SPECIAL");center(27,"BACK GUARD   START PAUSE");
    music(arena+1);finishScreen();
}
void showResult(u8 won) {
    setScreenOff();screen=RESULT;resultWin=won;commonScreen();loadBackground(arena);
    panel(7,15);
    center(8,champion?"OFFICE CHAMPION":(won?"SHIFT COMPLETE":"SHIFT OVER"));
    center(11,characterNames[won ? fighters[0].id:fighters[1].id]);center(13,"WINS THE MATCH");
    center(16,characterQuotes[won ? fighters[0].id:fighters[1].id]);
    center(19,mode==0 && !champion ? (won?"A: NEXT CHALLENGER":"A: CONTINUE"):"A: REMATCH");
    center(21,"B: CHARACTER SELECT");sound(3);finishScreen();
}

u16 cpuKeys(void) {
    s16 distance;
    u16 k=0,forward,back;
    u8 chance;
    Fighter *f=&fighters[1];Fighter *enemy=&fighters[0];
    if(mode==2)return 0;
    forward=f->face?KEY_RIGHT:KEY_LEFT;back=f->face?KEY_LEFT:KEY_RIGHT;
    distance=abs16(f->x-enemy->x)>>4;
    chance=(rng()>>8)&31;
    if(enemy->action && distance<64 && chance<8+difficulty*6)return back | ((enemy->duck)?KEY_DOWN:0);
    if(waves[0].active && distance>60 && chance<18)return back;
    if(distance>46) {
        k=forward;
        if(distance>95 && f->energy>=32 && ((frame+f->id*13)%97==0))k=KEY_DOWN|KEY_X;
        if(distance>65 && difficulty>0 && (frame%143==0))k|=KEY_UP;
    } else if(!f->action && !f->hurt && frame%(23-difficulty*5)==0) {
        chance=chance%6;
        if(chance==0)k=KEY_Y;else if(chance==1)k=KEY_X;else if(chance==2)k=KEY_L;
        else if(chance==3)k=KEY_B;else if(chance==4)k=KEY_A;else k=KEY_R;
        if(distance<26 && difficulty>0)k=forward|KEY_L;
        else if(chance==3)k|=KEY_DOWN;
    } else if(distance<29 && chance<12)k=back;
    return k;
}

void attackStart(Fighter *f,u8 a,const CharacterProfile *c) {
    f->action=a;f->tick=0;f->connected=0;f->guard=0;f->counter=0;
    if(a==7) {
        f->energy-=32;f->motion=0;f->downbuffer=0;
        if(c->specialFamily==SPECIAL_RISING){f->vy=c->specialVy;f->y=-1;f->duck=0;}
        sound(2);
    }
    else if(a==8) {f->vy=c->uppercutVy;f->y=-1;sound(0);}
    else sound(0);
}
void controls(u8 p,u16 keys) {
    Fighter *f=&fighters[p];Fighter *enemy=&fighters[1-p];
    const CharacterProfile *c;
    u16 edge,forward,back;
    u8 a;
    c=combatProfiles[p];
    f->oldkeys=f->keys;f->keys=keys;edge=keys & ~f->oldkeys;
    f->walking=0;
    if(f->motion)f->motion--;
    if(f->downbuffer)f->downbuffer--;
    if(f->hurt || !f->hp)return;
    f->guard=0;
    if(!f->action)f->face=f->x<enemy->x?1:0;
    forward=f->face?KEY_RIGHT:KEY_LEFT;back=f->face?KEY_LEFT:KEY_RIGHT;
    if(keys&KEY_DOWN)f->downbuffer=20;
    if((keys&forward) && f->downbuffer)f->motion=14;
    if(f->action) {
        /* Confirmed light/medium attacks can cancel upward into heavier normals. */
        if(f->connected && (((edge&(KEY_X|KEY_L)) && f->action<3) || ((edge&(KEY_A|KEY_R)) && f->action>=4 && f->action<6)))f->action=0;
        else return;
    }
    f->duck=(keys&KEY_DOWN) && !f->y;
    f->guard=(keys&back) && !f->y;
    if((edge&KEY_UP) && !f->y) {f->vy=c->jumpVy;f->y=-1;f->duck=0;}
    if(edge&ATTACKS) {
        if((edge&PUNCHES) && (f->motion || (keys&KEY_DOWN)) && f->energy>=32 && !f->y && !(edge&KEY_L))a=7;
        else if((edge&KEY_L) && (keys&KEY_DOWN) && !f->y)a=8;
        else if((edge&KEY_L) && (keys&forward) && !f->y && !enemy->y && abs16(f->x-enemy->x)<c->throwRange*16)a=9;
        else if(edge&KEY_L)a=3;
        else if(edge&KEY_R)a=6;
        else if(edge&KEY_X)a=2;
        else if(edge&KEY_A)a=5;
        else if(edge&KEY_Y)a=1;
        else a=4;
        attackStart(f,a,c);
    } else if(!(keys&KEY_DOWN) || f->y) {
        if(keys&forward){f->x+=f->face?c->walkSpeed:-c->walkSpeed;f->walking=1;}
        else if(keys&back){f->x+=f->face?-c->backSpeed:c->backSpeed;f->walking=1;}
    }
}

void hurt(u8 attacker,u8 defender,u8 dmg,u8 low,u8 air,u8 unblockable) {
    Fighter *a=&fighters[attacker];Fighter *d=&fighters[defender];
    const CharacterProfile *dc=combatProfiles[defender];
    u16 back;
    u8 blocked;
    back=d->face?KEY_LEFT:KEY_RIGHT;
    blocked=(d->keys&back) && !d->y && !d->action && !unblockable;
    if(air && d->duck)blocked=0;
    if(low && !d->duck)blocked=0;
    if(blocked) {
        d->guard=1;d->hurt=10;dmg=dmg>14?1:0;fxType=1;hitstop=3;
    } else {
        if(d->action && d->tick<attackStartup(dc,d->action)) {dmg+=3;a->counter=1;}
        if(a->combotime)a->combo++;else a->combo=1;
        a->combotime=45;d->hurt=12+dmg/3;d->action=0;d->tick=0;d->guard=0;
        fxType=0;hitstop=5;shake=6;
        a->energy=a->energy+8>ENERGY_MAX?ENERGY_MAX:a->energy+8;
        if(a->combo>1 || a->counter){clearBanner();word(attacker?20:2,9,a->counter?"COUNTER!":"COMBO!");if(a->combo>1)put(attacker?28:10,9,'0'+(a->combo%10));}
    }
    if(dmg>=d->hp)d->hp=0;else d->hp-=dmg;
    d->x+=a->face?32:-32;
    fxX=(d->x>>4)+(a->face?-12:6);fxY=FLOOR+(d->y>>4)-(low?22:53);fxLife=10;
    sound(1);hud();
}

void updateFighter(u8 p) {
    Fighter *f=&fighters[p];Wave *w=&waves[p];
    const CharacterProfile *c=combatProfiles[p];
    if(f->combotime) {f->combotime--;if(!f->combotime){f->combo=0;f->counter=0;clearBanner();}}
    if(f->hurt) {
        f->hurt--;
        if(!f->guard)f->x+=fighters[1-p].face?9:-9;
        if(!f->hurt)f->guard=0;
    }
    if(f->y || f->vy) {
        f->y+=f->vy;f->vy+=c->gravity;
        if(f->y>=0){f->y=0;f->vy=0;if(f->action==8)f->action=0;}
    }
    if(f->action) {
        f->tick++;
        if(f->action==7 && c->specialFamily==SPECIAL_RUSH && f->tick<=c->specialStartup+c->specialActive) {
            f->x+=f->face?c->specialSpeed:-c->specialSpeed;
        }
        if(f->action==7 && (c->specialFamily==SPECIAL_PROJECTILE || c->specialFamily==SPECIAL_GROUNDWAVE) && f->tick==c->specialStartup && !w->active) {
            w->active=1;w->owner=p;w->face=f->face;w->speed=c->specialSpeed;w->low=c->specialFamily==SPECIAL_GROUNDWAVE;
            w->x=f->x+(f->face?22*16:-22*16);w->y=w->low?FLOOR-18:FLOOR-39;w->life=c->specialLife;
        }
        if(f->action==6 && f->tick<attackStartup(c,6))f->x+=f->face?16:-16;
        if(f->tick>=attackStartup(c,f->action)+attackActive(c,f->action)+attackRecovery(c,f->action)) {f->action=0;f->tick=0;f->duck=0;}
    }
    if((frame&15)==0 && f->energy<ENERGY_MAX){f->energy++;hudDirty=1;}
    if(f->x<24*16)f->x=24*16;if(f->x>232*16)f->x=232*16;
}
u8 canHit(u8 p) {
    Fighter *f=&fighters[p];Fighter *d=&fighters[1-p];
    const CharacterProfile *c=combatProfiles[p];
    if(!f->action)return 0;
    if(f->action==7 && (c->specialFamily==SPECIAL_PROJECTILE || c->specialFamily==SPECIAL_GROUNDWAVE))return 0;
    if(f->connected)return 0;
    if(f->hurt)return 0;
    if(!d->hp)return 0;
    if(f->tick<attackStartup(c,f->action) || f->tick>=attackStartup(c,f->action)+attackActive(c,f->action))return 0;
    if((d->x>f->x) != (f->face!=0))return 0;
    if(abs16(f->x-d->x)>(attackReach(c,f->action)+10)*16)return 0;
    if(abs16(f->y-d->y)>38*16)return 0;
    if(f->action==9 && (d->y || d->hurt))return 0;
    return 1;
}
void combat(void) {
    u8 a0,a1,m0,m1,p,finished,low0,low1,air0,air1;
    s16 distance;
    const CharacterProfile *c0,*c1,*cw;
    controls(0,pad0);controls(1,mode==1?pad1:cpuKeys());
    updateFighter(0);updateFighter(1);
    distance=fighters[1].x-fighters[0].x;
    if(abs16(distance)<22*16 && abs16(fighters[0].y-fighters[1].y)<50*16) {
        if(distance>=0){fighters[0].x-=12;fighters[1].x+=12;}else{fighters[0].x+=12;fighters[1].x-=12;}
    }
    a0=canHit(0);a1=canHit(1);m0=fighters[0].action;m1=fighters[1].action;
    c0=combatProfiles[0];c1=combatProfiles[1];
    low0=(m0==7)?(c0->specialFamily==SPECIAL_GROUNDWAVE):(fighters[0].duck && m0>=4);
    low1=(m1==7)?(c1->specialFamily==SPECIAL_GROUNDWAVE):(fighters[1].duck && m1>=4);
    air0=(m0==7)?(c0->specialFamily==SPECIAL_RISING):(fighters[0].y<0);
    air1=(m1==7)?(c1->specialFamily==SPECIAL_RISING):(fighters[1].y<0);
    if(a0){fighters[0].connected=1;hurt(0,1,attackDamage(c0,fighters[0].id,m0),low0,air0,m0==9);}
    if(a1){fighters[1].connected=1;hurt(1,0,attackDamage(c1,fighters[1].id,m1),low1,air1,m1==9);}
    for(p=0;p<2;p++) {
        if(waves[p].active) {
            cw=p?c1:c0;
            waves[p].x+=waves[p].face?waves[p].speed:-waves[p].speed;
            waves[p].life--;
            if(!waves[p].life || waves[p].x<0 || waves[p].x>256*16){waves[p].active=0;waves[p].low=0;waves[p].speed=0;}
            else if(abs16(waves[p].x-fighters[1-p].x)<(cw->specialReach+4)*16 && fighters[1-p].y>-40*16) {
                hurt(p,1-p,attackDamage(cw,fighters[p].id,7),waves[p].low,0,0);waves[p].active=0;waves[p].low=0;waves[p].speed=0;
            }
        }
    }
    if(waves[0].active && waves[1].active && abs16(waves[0].x-waves[1].x)<16*16) {
        fxX=waves[0].x>>4;fxY=waves[0].y;fxLife=10;fxType=0;
        waves[0].active=0;waves[1].active=0;waves[0].low=0;waves[1].low=0;waves[0].speed=0;waves[1].speed=0;sound(1);
    }
    if(mode==2) {
        seconds=99;
        if(!fighters[1].hp || (!fighters[1].hurt && frame%120==0)){fighters[1].hp=HP_MAX;hud();}
        if(!fighters[0].hp)fighters[0].hp=HP_MAX;
    } else {
        secondTick++;if(secondTick>=60){secondTick=0;if(seconds)seconds--;hud();}
        /* 816-tcc cannot safely lower three chained negated OR operands. */
        finished=0;
        if(fighters[0].hp==0)finished=1;
        if(fighters[1].hp==0)finished=1;
        if(seconds==0)finished=1;
        if(finished) {
            roundEnd=180;waves[0].active=0;waves[1].active=0;
            waves[0].low=0;waves[1].low=0;waves[0].speed=0;waves[1].speed=0;
            if(fighters[0].hp==fighters[1].hp)winner=2;
            else winner=fighters[0].hp>fighters[1].hp?0:1;
            if(winner<2)fighters[winner].won++;
            clearBanner();panel(10,3);center(10,seconds?"K.O.":"TIME OVER");
            if(winner<2){center(12,characterNames[fighters[winner].id]);}else center(12,"DOUBLE K.O.");
            shake=10;sound(3);hud();
        }
    }
}

u8 poseFor(u8 p) {
    Fighter *f=&fighters[p];
    const CharacterProfile *c=combatProfiles[p];
    if(roundEnd) {if(!f->hp)return 14;if(winner==p)return 11;return 10;}
    if(f->hurt)return f->guard?9:10;
    if(f->action) {
        switch(f->action) {
        case 1:return f->tick<3?0:5;
        case 2:return f->tick<4?0:6;
        case 3:return f->tick<6?0:6;
        case 4:case 5:case 6:return f->tick<4?0:(f->duck?8:7);
        case 7:
            if(c->specialFamily==SPECIAL_RUSH)return 15;
            if(c->specialFamily==SPECIAL_RISING)return 13;
            return 12;
        case 8:return 13;
        default:return 15;
        }
    }
    if(f->y)return 4;if(f->duck)return 3;if(f->guard)return 9;
    if(f->walking)return ((frame>>3)&1)?1:2;
    return 0;
}
void drawFighter(u8 p) {
    Fighter *f=&fighters[p];
    s16 x,y;
    f->pose=poseFor(p);
    /* The gameplay pivot is the center of a uniform 96x80 canvas.  Keep the
     * signed left edge intact so the ninth OAM X bit can wrap a whole body
     * cleanly at either screen edge. */
    x=(f->x>>4)-(ACTOR_FRAME_W/2);y=FLOOR+(f->y>>4)-ACTOR_FRAME_H;
    if(!f->action && !f->hurt && !roundEnd && !f->y && !f->duck)y-=((frame>>4)&1);
    drawActorFast(p ? ACTOR_OAM1:ACTOR_OAM0,x,y,f->face?0:1,p);
    oamSet(OAM_SHADOW_BASE+p*8,(f->x>>4)-12,FLOOR-5,0,0,0,430,2);oamSetEx(OAM_SHADOW_BASE+p*8,1,OBJ_SHOW);
    oamSet(OAM_SHADOW_BASE+4+p*8,(f->x>>4),FLOOR-5,0,1,0,430,2);oamSetEx(OAM_SHADOW_BASE+4+p*8,1,OBJ_SHOW);
}
void drawFight(void) {
    u8 p;
    drawFighter(0);drawFighter(1);
    if(fxLife) {
        fxLife--;oamSet(OAM_EFFECT_BASE,fxX-8,fxY-8,3,frame&1,0,384+(fxType?6:(fxLife&3)*2),2);oamSetEx(OAM_EFFECT_BASE,1,OBJ_SHOW);
    } else oamSetVisible(OAM_EFFECT_BASE,OBJ_HIDE);
    for(p=0;p<2;p++) {
        if(waves[p].active){oamSet(OAM_WAVE_BASE+p*4,(waves[p].x>>4)-8,waves[p].y,2,waves[p].face?0:1,0,392+(frame%3)*2,2);oamSetEx(OAM_WAVE_BASE+p*4,1,OBJ_SHOW);}
        else oamSetVisible(OAM_WAVE_BASE+p*4,OBJ_HIDE);
    }
}
void queueFighter(u8 p) {
    Fighter *f=&fighters[p];
    if(f->pose==f->oldpose)return;
    actorUploadSource=f->pose<8 ? fighterData(f->id)+(u16)f->pose*ACTOR_POSE_BYTES : fighterDataB(f->id)+(u16)(f->pose-8)*ACTOR_POSE_BYTES;
    actorUploadDestination=p ? ACTOR_VRAM1:ACTOR_VRAM0;
    actorUploadDirty=1;
    f->oldpose=f->pose;
}

void fightTick(void) {
    if((edge0|edge1)&KEY_START) {
        paused=!paused;clearBanner();
        if(paused){panel(10,4);center(10,"PAUSED");center(12,"A RESUME   B ROSTER");}
        sound(0);
    }
    if(paused) {
        if(edge0&KEY_A){paused=0;clearBanner();}
        if(edge0&KEY_B){showSelect();return;}
        drawFight();return;
    }
    if(roundEnd) {
        roundEnd--;
        if(roundEnd==100) {clearBanner();panel(10,3);center(10,winner<2?characterNames[fighters[winner].id]:"DRAW");center(12,winner<2?"WINS THE ROUND":"TRY AGAIN");}
        if(!roundEnd) {
            if(fighters[0].won>=2 || fighters[1].won>=2) {
                resultWin=fighters[0].won>=2;
                champion=mode==0 && resultWin && arcade>=10;
                showResult(resultWin);return;
            }
            if(winner<2)roundNumber++;
            resetRound();
        }
    } else if(intro) {
        intro--;
        if(intro==50){clearBanner();panel(10,3);center(11,"FIGHT!");sound(3);}
        if(!intro)clearBanner();
    } else if(hitstop)hitstop--;
    else combat();
    if((frame&15)==0)hud();
    drawFight();
}
void menuTick(void) {
    u8 *choice;
    if(screen==TITLE) {
        if(edge0&KEY_DOWN){menu=(menu+1)%3;sound(0);drawTitle();}
        if(edge0&KEY_UP){menu=(menu+2)%3;sound(0);drawTitle();}
        if(edge0&KEY_L){difficulty=(difficulty+2)%3;sound(0);drawTitle();}
        if(edge0&KEY_R){difficulty=(difficulty+1)%3;sound(0);drawTitle();}
        if(edge0&(KEY_START|KEY_A)){mode=menu;arcade=0;champion=0;sound(3);showSelect();}
    } else if(screen==SELECT) {
        if(selectPlayer)edge0|=edge1;
        choice=selectPlayer?&selected2:&selected;
        if(edge0&KEY_RIGHT)*choice=(*choice+1)%12;
        if(edge0&KEY_LEFT)*choice=(*choice+11)%12;
        if(edge0&KEY_UP)*choice=(*choice+8)%12;
        if(edge0&KEY_DOWN)*choice=(*choice+4)%12;
        if(edge0&(KEY_RIGHT|KEY_LEFT|KEY_UP|KEY_DOWN)){sound(0);drawSelect();}
        if(edge0&KEY_B){if(selectPlayer){selectPlayer=0;drawSelect();}else showTitle();}
        if(edge0&(KEY_A|KEY_START)) {
            sound(3);
            if(mode==1 && !selectPlayer){selectPlayer=1;drawSelect();}
            else {if(mode!=1)selected2=(selected+1)%12;showArenas();}
        }
    } else if(screen==ARENA) {
        if(edge0&KEY_DOWN){arena=(arena+1)%3;sound(0);drawArenas();}
        if(edge0&KEY_UP){arena=(arena+2)%3;sound(0);drawArenas();}
        if(edge0&KEY_B)showSelect();
        if(edge0&(KEY_A|KEY_START)){sound(3);beginMatch();}
    } else if(screen==RESULT) {
        if(edge0&KEY_B)showSelect();
        if(edge0&(KEY_A|KEY_START)) {
            if(mode==0 && resultWin && !champion){arcade++;arena=(arena+1)%3;}
            else if(champion){arcade=0;champion=0;showTitle();return;}
            beginMatch();
        }
    }
}

void trace(void) {
    const CharacterProfile *c0,*c1;
    if(screen==FIGHT){c0=combatProfiles[0];c1=combatProfiles[1];}
    else {c0=profileFor(fighters[0].id);c1=profileFor(fighters[1].id);}
    TRACE[0]=0xaaba;TRACE[1]=screen;TRACE[2]=frame;TRACE[3]=mode;
    TRACE[4]=fighters[0].hp;TRACE[5]=fighters[1].hp;
    TRACE[6]=fighters[0].x;TRACE[7]=fighters[1].x;
    TRACE[8]=fighters[0].y;TRACE[9]=fighters[1].y;
    TRACE[10]=fighters[0].action;TRACE[11]=fighters[1].action;
    TRACE[12]=fighters[0].won;TRACE[13]=fighters[1].won;
    TRACE[14]=arena;TRACE[15]=roundNumber;TRACE[16]=intro;TRACE[17]=paused;
    TRACE[18]=fighters[0].energy;TRACE[19]=fighters[1].energy;
    TRACE[20]=waves[0].active;TRACE[21]=waves[1].active;
    TRACE[22]=selected;TRACE[23]=selected2;TRACE[24]=arcade;TRACE[25]=seconds;
    TRACE[26]=fighters[0].pose;TRACE[27]=fighters[1].pose;
    TRACE[28]=roundEnd;TRACE[29]=hitstop;TRACE[30]=fighters[0].combo;
    TRACE[31]=champion;
    /* Character contract for headless roster verification. */
    TRACE[32]=fighters[0].id;TRACE[33]=fighters[1].id;
    TRACE[34]=c0->specialFamily;TRACE[35]=c1->specialFamily;
    TRACE[36]=c0->walkSpeed;TRACE[37]=c1->walkSpeed;
    TRACE[38]=c0->jumpVy;TRACE[39]=c1->jumpVy;
    TRACE[40]=fighters[0].face;TRACE[41]=fighters[1].face;
    /* Additional tuning/state fields are kept after the stable contract. */
    TRACE[42]=c0->backSpeed;TRACE[43]=c1->backSpeed;
    TRACE[44]=c0->specialStartup;TRACE[45]=c1->specialStartup;
    TRACE[46]=c0->specialActive;TRACE[47]=c1->specialActive;
    TRACE[48]=c0->specialRecovery;TRACE[49]=c1->specialRecovery;
    TRACE[50]=c0->specialDamage;TRACE[51]=c1->specialDamage;
    TRACE[52]=c0->specialReach;TRACE[53]=c1->specialReach;
    TRACE[54]=c0->throwRange;TRACE[55]=c1->throwRange;
    TRACE[56]=waves[0].low;TRACE[57]=waves[1].low;
    TRACE[58]=waves[0].speed;TRACE[59]=waves[1].speed;
    TRACE[60]=waves[0].life;TRACE[61]=waves[1].life;
}
int main(void) {
    u8 sx;
    randomseed=0xABA;frame=0;menu=0;mode=0;difficulty=1;selected=0;selected2=1;arena=0;
    combatProfiles[0]=&characterProfiles[0];combatProfiles[1]=&characterProfiles[0];
    musicIndex=255;musicOn=1;
    spcBoot();spcSetBank(&SOUNDBANK__);spcAllocateSoundRegion(24);
    spcSetSoundEntry(8,8,4,SFX0_SIZE,&sfx0,&sounds[0]);
    spcSetSoundEntry(13,8,4,SFX1_SIZE,&sfx1,&sounds[1]);
    spcSetSoundEntry(10,8,4,SFX2_SIZE,&sfx2,&sounds[2]);
    spcSetSoundEntry(9,8,4,SFX3_SIZE,&sfx3,&sounds[3]);
    spcSetSoundTableEntry(&sounds[0]);
    oamInit();showTitle();
    while(1) {
        pad0=padsCurrent(0);pad1=padsCurrent(1);edge0=padsDown(0);edge1=padsDown(1);
        if(screen==FIGHT)fightTick();else menuTick();
        if(screen==FIGHT) {
            /* Resolve bank pointers and pose offsets during active display.
             * Vblank only executes the already prepared 3840-byte upload. */
            sx=frame&1;
            if(fighters[sx].pose!=fighters[sx].oldpose)queueFighter(sx);
            else queueFighter(1-sx);
        }
        trace();spcProcess();WaitForVBlank();
        if(actorUploadDirty){uploadActor(actorUploadSource,actorUploadDestination);actorUploadDirty=0;}
        if(screen==SELECT && portraitDirty)uploadMenuPortrait();
        if(fullDirty){dmaCopyVram((u8*)ui,0x5800,2048);fullDirty=0;hudDirty=0;bannerDirty=0;}
        else {
            if(hudDirty){dmaCopyVram((u8*)ui,0x5800,320);hudDirty=0;}
            if(bannerDirty){dmaCopyVram((u8*)&ui[9*32],0x5800+9*32,320);bannerDirty=0;}
        }
        if(shake && screen==FIGHT){shake--;sx=shake&1?2:254;bgSetScroll(0,sx==254?510:2,511);}
        else bgSetScroll(0,0,511);
        frame++;
    }
    return 0;
}
