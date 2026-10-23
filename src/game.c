/* Abaqus: After Hours — native SNES fighting game.
 * Original game code; PVSnesLib supplies hardware, input and SPC services.
 * Logic runs at the NTSC vertical blank cadence. All coordinates are 12.4 fixed point.
 */
#include <snes.h>
#include "assets.h"
#include "soundbank.h"
#include "characters.h"
#include "menu_portraits.h"
#include "version.h"

#if MOD_EFFECTS != 0 || MOD_MUSIC0 != 1 || MOD_MUSIC1 != 2 || MOD_MUSIC2 != 3 || MOD_MUSIC3 != 4 || MOD_MUSIC4 != 5
#error Regenerate the resident effects-first soundbank with Build.cmd --assets
#endif

#define TITLE 0
#define SELECT 1
#define ARENA 2
#define FIGHT 3
#define RESULT 4
#define HP_MAX 128
#define ENERGY_MAX 96
#define FLOOR 201
#define PUNCHES (KEY_Y|KEY_X)
#define ATTACKS (PUNCHES|KEY_B|KEY_A)
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
#define AMBIENT_VRAM 0x3c00
#define AMBIENT_BYTES 256
#define INPUT_BUFFER_TICKS 6
#define BODY_HALF_WIDTH 10
#define DOWN_FREE 0
#define DOWN_LIFT 1
#define DOWN_FLIGHT 2
#define DOWN_FLOOR 3
#define DOWN_RISE 4
#define DOWN_WAKE 5

/* refreshFighterOam and drawShadowsFast encode this fixed native geometry. */
typedef char NativeOamGeometryMustMatch[(ACTOR_FRAME_W==96 && ACTOR_FRAME_H==80 && FLOOR==201)?1:-1];

typedef struct {
    s16 x, y, vy, vx;
    u16 keys, oldkeys;
    u8 id, face, hp, energy, action, tick, connected;
    u8 hurt, guard, duck, walking, pose, actionStartup, won;
    u8 motion, downbuffer, combo, combotime, counter;
    u16 rawKeys, inputEdge, bufferKeys, stride;
    u8 bufferedAction, bufferAge, jumpBuffer, landing;
    u8 animFrame, oldFrame, animState, animTick;
    u8 downState, downTick, invuln, downDamage, downOwner, throwVictim, airAction;
    u8 wakeAction, wakeAge, wakeJump, wakeLock, wakeJust;
    u16 wakeKeys;
    /* 64-byte stride lets 816-tcc index actors with shifts, not soft multiply. */
    u8 actionEnd,actionActiveEnd;
} Fighter;
typedef char FighterStrideMustBe64[sizeof(Fighter)==64?1:-1];
typedef struct { s16 x,y; u8 active,face,life,owner,speed,low,reserved[6]; } Wave;
typedef char WaveStrideMustBe16[sizeof(Wave)==16?1:-1];
/* The native trace/bar routines use these offsets; fail the C build on drift. */
#define CHECK_OFFSET(type,field,offset) typedef char type##_##field##_offset[((u16)&(((type *)0)->field)==offset)?1:-1]
CHECK_OFFSET(Fighter,hp,14);
CHECK_OFFSET(Fighter,energy,15);
CHECK_OFFSET(Fighter,x,0);CHECK_OFFSET(Fighter,y,2);CHECK_OFFSET(Fighter,vx,6);
CHECK_OFFSET(Fighter,id,12);CHECK_OFFSET(Fighter,face,13);CHECK_OFFSET(Fighter,action,16);
CHECK_OFFSET(Fighter,connected,18);CHECK_OFFSET(Fighter,hurt,19);CHECK_OFFSET(Fighter,guard,20);
CHECK_OFFSET(Fighter,pose,23);CHECK_OFFSET(Fighter,won,25);CHECK_OFFSET(Fighter,motion,26);
CHECK_OFFSET(Fighter,combo,28);CHECK_OFFSET(Fighter,combotime,29);CHECK_OFFSET(Fighter,counter,30);
CHECK_OFFSET(Fighter,rawKeys,32);
CHECK_OFFSET(Fighter,bufferKeys,36);
CHECK_OFFSET(Fighter,bufferedAction,40);CHECK_OFFSET(Fighter,bufferAge,41);
CHECK_OFFSET(Fighter,jumpBuffer,42);CHECK_OFFSET(Fighter,landing,43);
CHECK_OFFSET(Fighter,animFrame,44);
CHECK_OFFSET(Fighter,animState,46);CHECK_OFFSET(Fighter,animTick,47);
CHECK_OFFSET(Fighter,downState,48);
CHECK_OFFSET(Fighter,downTick,49);CHECK_OFFSET(Fighter,invuln,50);CHECK_OFFSET(Fighter,downDamage,51);
CHECK_OFFSET(Fighter,downOwner,52);CHECK_OFFSET(Fighter,throwVictim,53);CHECK_OFFSET(Fighter,airAction,54);
CHECK_OFFSET(Fighter,wakeAction,55);CHECK_OFFSET(Fighter,wakeAge,56);CHECK_OFFSET(Fighter,wakeJump,57);
CHECK_OFFSET(Fighter,wakeKeys,60);
CHECK_OFFSET(Fighter,actionEnd,62);
CHECK_OFFSET(Wave,active,4);
CHECK_OFFSET(Wave,face,5);
CHECK_OFFSET(Wave,life,6);
CHECK_OFFSET(Wave,low,9);
CHECK_OFFSET(Wave,speed,8);

Fighter fighters[2];
Wave waves[2];
/* Cached for the live match; menu/trace code still resolves IDs explicitly. */
const CharacterProfile *combatProfiles[2];
u8 *actorBanks[16];
const u16 actorFrameOffsets[8]={0,3840,7680,11520,15360,19200,23040,26880};
u8 matchStartup[32],matchActiveEnd[32],matchActionEnd[32];
s16 actorRenderX[2],actorRenderY[2];
u8 actorRenderFace[2],actorRenderValid[2];
u16 ui[1024];
u16 frame, randomseed, pad0, pad1, edge0, edge1;
u8 screen, mode, difficulty, menu, selected, selected2, selectPlayer, arena;
u8 arcade, roundNumber, seconds, secondTick, intro, roundEnd, winner, paused;
u8 pausePage,guideBuild,guideDirty,trainingDummy;
u8 pauseHudPending;
/* Reuse the previously unused flash byte for private rear-kick recoil:
 * bits 0..1 = P1, 2..3 = P2; 0 legacy drift, 1 left, 2 right.
 * Keep the contact direction through landing/trades without adding fields,
 * WRAM storage or trace words. */
u8 hitstop, shake, rearKickRecoil, fxLife, fxX, fxY, fxType, resultWin, champion;
u8 hudDirty, bannerDirty, footerDirty, fullDirty, musicIndex, musicOn;
u8 impactHudPending,impactBannerPending;
u8 impactBannerPlayer,impactBannerCombo,impactBannerCounter;
u8 impactSettle,resetFooterPending;
u8 roundBannerPending;
u8 pendingSound;
u8 cpuTick;
u8 portraitDirty, portraitId;
u8 actorUploadDirty;
u8 *actorUploadSource;
u16 actorUploadDestination;
u8 hudHp[2], hudEnergy[2], hudWins[2], hudSeconds;
u8 animationAdvance;
u16 fightClock;
/* Eight BG1 tiles animate independently of OBJ and actor pose uploads. */
u8 *ambientData,*ambientUploadSource;
u16 ambientClock;
u8 ambientPhase,ambientWanted,ambientAge;
u8 roundUiPending;
const u8 effectVolpan[4]={0x88,0xd8,0xa8,0x98};
extern char SOUNDBANK__;
extern void drawActorFast(u16 byteSlot,s16 x,s16 y,u8 flip,u8 palette);
extern void drawShadowsFast(u16 byteSlot,s16 centerX);
extern void refreshFighterOam(u8 player);
extern void queueFighter(u8 player);
extern void processResidentAudioReady(void);
extern void uploadActor(u8 *source,u16 destination);
extern void traceActorsFast(void);
extern void clearBanner(void);
extern void clearUi(void);
extern void clearFightHint(void);
extern void fillBannerPanel(void);
extern void fillPausePanel(void);
extern void fillGuidePanel(void);
extern void clearGuidePanel(void);
extern void drawGuideWord(u16 byteOffset,const char *text);
extern void applyHitReaction(u8 defender,u8 damage);
extern void refreshHealthBar(u8 player);
extern void refreshEnergyBar(u8 player);
void releaseHeldVictim(u8 owner);
void traceProfiles(void);

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
#include "animation_banks.h"

void put(u8 x,u8 y,u16 t) {
    /* A panel tile behind a transparent letter is replaced by that letter,
     * so its holes otherwise reveal BG1. Reuse the existing opaque glyph
     * bank for fight/result text; tile zero and menu cursor tiles stay clear. */
    if(screen>=FIGHT) {
        if(t>=32 && t<128)t+=256;
    }
    if(x<32 && y<32)ui[(u16)y*32+x]=t|0x2000;
}
void word(u8 x,u8 y,const char *s) { while(*s && x<32) put(x++,y,*s++); }
void center(u8 y,const char *s) { u8 n=0; const char *p=s; while(*p++)n++; word((32-n)/2,y,s); }
void number(u8 x,u8 y,u8 n) { put(x,y,'0'+n/10); put(x+1,y,'0'+n%10); }
#include "training_tools.h"
void panel(u8 y,u8 rows) { u16 i; for(i=(u16)y*32;i<(u16)(y+rows)*32;i++)ui[i]=128|0x2000; }
void cursor(u8 x,u8 y,u8 w,u8 h) {
    u8 i;
    put(x,y,149);put(x+w-1,y,150);put(x,y+h-1,151);put(x+w-1,y+h-1,152);
    for(i=1;i<w-1;i++){put(x+i,y,154);put(x+i,y+h-1,154|0x8000);}
    for(i=1;i<h-1;i++){put(x,y+i,153);put(x+w-1,y+i,153|0x4000);}
}
void sound(u8 n) {
    /* One SPC trigger per tick: duplicate same-frame cues share a voice.
     * Round cues > impact > special > swing. Never stall twice on the port. */
    if(!musicOn)return;
    if(!pendingSound)pendingSound=n+1;
    if(n==3)pendingSound=4;
    else if(n==1 && pendingSound!=4)pendingSound=2;
    else if(n==2 && pendingSound==1)pendingSound=3;
}
void music(u8 index) {
    u8 effect;
    if(index>4)return;
    if(musicIndex==index)return;
    spcStop();spcLoad(MOD_MUSIC0+index);
    for(effect=0;effect<4;effect++)spcLoadEffect(effect);
    spcSetModuleVolume(86);spcPlay(0);musicIndex=index;
}
void commonScreen(void) {
    if(mode==2)trainingNewMatch();
    pausePage=0;guideBuild=0;guideDirty=0;trainingDummy=0;pauseHudPending=0;
    portraitDirty=0;
    actorUploadDirty=0;
    ambientClock=0;ambientPhase=0;ambientWanted=255;ambientAge=0;
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
    if(which<3) {
        if(which==0)ambientData=&stage0_ambient;
        else if(which==1)ambientData=&stage1_ambient;
        else ambientData=&stage2_ambient;
        dmaCopyVram(ambientData,AMBIENT_VRAM,AMBIENT_BYTES);
    }
}
void finishScreen(void) { dmaCopyVram((u8 *)ui,0x5800,2048);fullDirty=0;footerDirty=0;setScreenOn(); }
void drawTitle(void) {
    clearUi();
    word(9,20,"ARCADE SHIFT");word(9,22,"LOCAL VERSUS");word(9,24,"TRAINING");
    word(7,20+menu*2,">");word(3,25,"L/R LEVEL");put(13,25,'1'+difficulty);
    word(18,25,difficulty==0?"EASY":(difficulty==1?"NORMAL":"HARD"));
    word(24,27,"V" ABAQUS_GAME_VERSION);
}
void showTitle(void) {
    setScreenOff();screen=TITLE;commonScreen();loadBackground(3);paused=0;
    drawTitle();
    music(0);finishScreen();
}
void drawSelect(void) {
    u8 id,x,y;
    clearUi();id=selectPlayer ? selected2:selected;
    cursor(1+(id%4)*5,6+(id/4)*6,5,6);
    /* Dedicated source-master portrait: eight by ten BG2 tiles. */
    for(y=0;y<10;y++)for(x=0;x<8;x++)
        ui[(u16)(y+6)*32+x+23]=(160+(u16)y*8+x)|0x2400;
    if(mode==2 && selectPlayer)word(23,4,"DUMMY");
    else word(23,4,selectPlayer ? "PLAYER 2":"PLAYER 1");
    word(22,17,characterNames[id]);
    center(27,"D-PAD SELECT A/START OK B BACK");
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
void drawArenas(void) {
    clearUi();cursor(1,5+arena*7,30,7);
    /* Cover only the raster footer below the three unchanged choice rows.
     * Opaque original glyphs keep the old lettering from showing through. */
    panel(26,2);drawGuideWord((27*32+3)*2,"UP/DOWN A/START OK B BACK");
    fullDirty=1;
}
void showArenas(void) { setScreenOff();screen=ARENA;commonScreen();loadBackground(5);drawArenas();finishScreen(); }

void hud(void) {
    u8 p;
    Fighter *f;
    /* A recovery refresh can precede the periodic refresh in the same tick.
     * Check direct fields before entering the indexed changed-field path. */
    if(hudSeconds==seconds && hudHp[0]==fighters[0].hp && hudHp[1]==fighters[1].hp &&
       hudEnergy[0]==fighters[0].energy && hudEnergy[1]==fighters[1].energy &&
       hudWins[0]==fighters[0].won && hudWins[1]==fighters[1].won)return;
    if(hudSeconds!=seconds){number(15,0,seconds);hudSeconds=seconds;hudDirty=1;}
    for(p=0;p<2;p++) {
        f=&fighters[p];
        if(hudHp[p]!=f->hp) {
            hudHp[p]=f->hp;
            refreshHealthBar(p);
            hudDirty=1;
        }
        if(hudEnergy[p]!=f->energy) {
            hudEnergy[p]=f->energy;
            refreshEnergyBar(p);
            hudDirty=1;
        }
        if(hudWins[p]!=f->won) {
            hudWins[p]=f->won;
            ui[64+(p?29:1)]=(f->won>0?147:148)|0x2000;ui[64+(p?30:2)]=(f->won>1?147:148)|0x2000;
            hudDirty=1;
        }
    }
}
void resetRoundState(void) {
    u8 p;
    for(p=0;p<2;p++) {
        fighters[p].x=(p ? 190:66)*16;fighters[p].y=0;fighters[p].vy=0;fighters[p].vx=0;
        fighters[p].hp=HP_MAX;fighters[p].energy=64;fighters[p].face=p?0:1;
        fighters[p].action=0;fighters[p].tick=0;fighters[p].connected=0;
        fighters[p].hurt=0;fighters[p].guard=0;fighters[p].duck=0;fighters[p].walking=0;
        fighters[p].actionStartup=0;fighters[p].actionActiveEnd=0;fighters[p].actionEnd=0;
        fighters[p].pose=0;fighters[p].combo=0;fighters[p].combotime=0;fighters[p].counter=0;
        fighters[p].motion=0;fighters[p].downbuffer=0;fighters[p].keys=0;fighters[p].oldkeys=0;
        fighters[p].rawKeys=0;fighters[p].inputEdge=0;fighters[p].bufferKeys=0;
        fighters[p].bufferedAction=0;fighters[p].bufferAge=0;fighters[p].jumpBuffer=0;
        fighters[p].landing=0;fighters[p].stride=0;
        fighters[p].animFrame=0;fighters[p].oldFrame=255;
        fighters[p].animState=255;fighters[p].animTick=0;
        actorRenderValid[p]=0;
        fighters[p].downState=0;fighters[p].downTick=0;fighters[p].invuln=0;
        fighters[p].downDamage=0;fighters[p].downOwner=255;fighters[p].throwVictim=255;
        fighters[p].airAction=0;fighters[p].wakeAction=0;fighters[p].wakeAge=0;
        fighters[p].wakeJump=0;fighters[p].wakeKeys=0;fighters[p].wakeLock=0;fighters[p].wakeJust=0;
        waves[p].active=0;waves[p].low=0;waves[p].speed=0;waves[p].life=0;
        waves[p].x=0;waves[p].y=0;waves[p].face=0;waves[p].owner=p;
    }
    seconds=99;secondTick=0;intro=110;roundEnd=0;hitstop=0;shake=0;fxLife=0;
    rearKickRecoil=0;
    fightClock=0;
    impactHudPending=0;impactBannerPending=0;roundBannerPending=0;
    impactBannerPlayer=0;impactBannerCombo=0;impactBannerCounter=0;
    impactSettle=0;resetFooterPending=0;roundUiPending=0;
    pendingSound=0;
    pauseHudPending=0;
    hudHp[0]=255;hudHp[1]=255;hudEnergy[0]=255;hudEnergy[1]=255;
    hudWins[0]=255;hudWins[1]=255;hudSeconds=255;
    if(mode==2)trainingReset();
}
void resetRound(void) {
    u8 x;
    resetRoundState();
    panel(0,5);word(1,0,characterNames[fighters[0].id]);word(20,0,characterNames[fighters[1].id]);
    /* Gold nameplates and a quiet bottom rule stay inside the existing
     * five-row, 320-byte HUD transfer. Palette 1 is reset for each scene. */
    for(x=0;x<32;x++){ui[x]|=0x0400;ui[128+x]=158|0x2000;}
    ui[32]=155|0x2000;ui[44]=155|0x6000;
    ui[51]=155|0x2000;ui[63]=155|0x6000;
    ui[96]=157|0x2000;ui[109]=157|0x6000;
    ui[114]=157|0x2000;ui[127]=157|0x6000;
    ui[14]=156|0x2400;ui[17]=156|0x6400;
    ui[46]=156|0x2400;ui[49]=156|0x6400;
    put(15,1,'K');put(16,1,'O');word(13,2,"ROUND");put(19,2,'0'+roundNumber);
    ui[47]|=0x0400;ui[48]|=0x0400;
    word(4,2,"WINS");word(24,2,"WINS");
    if(mode==2)word(12,4,"TRAINING");
    else word(12,4,mode==1 ? "P1 VS P2":"P1 VS CPU");
    clearBanner();fillBannerPanel();center(10,"GET READY");center(12,arenaNames[arena]);hud();
}
void beginMatch(void) {
    u8 i;
    setScreenOff();screen=FIGHT;commonScreen();loadBackground(arena);
    fighters[0].id=selected;
    fighters[1].id=mode==0 ? (selected+1+arcade)%12:selected2;
    combatProfiles[0]=profileFor(fighters[0].id);combatProfiles[1]=profileFor(fighters[1].id);
    traceProfiles();
    for(i=0;i<8;i++) {
        actorBanks[i]=fighterFrameBank(fighters[0].id,i);
        actorBanks[8+i]=fighterFrameBank(fighters[1].id,i);
    }
    for(i=0;i<10;i++) {
        matchStartup[i]=attackStartup(combatProfiles[0],i);
        matchActiveEnd[i]=matchStartup[i]+attackActive(combatProfiles[0],i);
        matchActionEnd[i]=matchActiveEnd[i]+attackRecovery(combatProfiles[0],i);
        matchStartup[16+i]=attackStartup(combatProfiles[1],i);
        matchActiveEnd[16+i]=matchStartup[16+i]+attackActive(combatProfiles[1],i);
        matchActionEnd[16+i]=matchActiveEnd[16+i]+attackRecovery(combatProfiles[1],i);
    }
    fighters[0].won=0;fighters[1].won=0;roundNumber=1;paused=0;
    dmaCopyCGram(fighterPalette(fighters[0].id),128,32);dmaCopyCGram(fighterPalette(fighters[1].id),144,32);
    dmaCopyCGram(&effects_pal,160,32);dmaCopyVram(&effects,0x7800,EFFECTS_SIZE);
    oamInitGfxAttr(0x6000,OBJ_SIZE8_L16);
    /* Clear the sixteen packed high-table bytes covering both padded actor
     * blocks.  drawActorFast restores the 16x16 size bit and signed X9 bit
     * for each of the thirty live entries on every render. */
    for(i=0;i<16;i++)oamMemory[512+i]=0;
    resetRound();panel(26,2);center(26,"Y/X/L PUNCH   B/A/R KICK");center(27,"START PAUSE > SELECT GUIDE");
    music(arena+1);finishScreen();
}
void loadChampionEnding(u8 id) {
    u8 x,y;
    /* Only called inside the screen-off result transition. BG1 uses the
     * existing six scene palettes; the portrait keeps its BG2 page/palette. */
    dmaCopyVram(&champion_tiles,0,CHAMPION_TILES_SIZE);
    dmaCopyVram(&champion_map,0x3800,2048);
    dmaCopyCGram(&champion_pal,32,192);
    portraitId=id;uploadMenuPortrait();
    center(2,"OFFICE CHAMPION");
    for(x=3;x<29;x++)put(x,4,154);
    cursor(20,6,10,12);
    for(y=0;y<10;y++)for(x=0;x<8;x++)
        ui[(u16)(y+7)*32+x+21]=(160+(u16)y*8+x)|0x2400;
    word(21,18,characterNames[id]);
    word(21,19,"P1 2-0 P2");
    put(24,19,'0'+fighters[0].won);put(26,19,'0'+fighters[1].won);
    word(22,20,"ALL 11");word(21,21,"DEFEATED");
    /* The trophy's keyboard/plinth ends at y175. Only the footer is filled. */
    panel(22,6);center(22,characterQuotes[id]);
    center(24,"A/START: TITLE");center(26,"B: CHARACTER SELECT");
}
void showResult(u8 won) {
    u8 id,x,y;
    setScreenOff();screen=RESULT;resultWin=won;commonScreen();
    if(champion) {
        loadChampionEnding(won?fighters[0].id:fighters[1].id);
        music(4);
        sound(3);finishScreen();return;
    }
    loadBackground(arena);
    panel(4,23);
    if(mode==1)center(5,"MATCH COMPLETE");
    else center(5,won?"SHIFT COMPLETE":"SHIFT OVER");
    for(x=3;x<29;x++)put(x,7,154);
    id=won?fighters[0].id:fighters[1].id;
    /* Result scenes are loaded with the screen off. Reuse the existing
     * portrait page and palette; combat's per-vblank actor budget is intact. */
    portraitId=id;uploadMenuPortrait();cursor(3,8,10,12);
    for(y=0;y<10;y++)for(x=0;x<8;x++)
        ui[(u16)(y+9)*32+x+4]=(160+(u16)y*8+x)|0x2400;
    word(15,9,characterNames[id]);word(15,11,"WINS THE MATCH");
    word(16,13,"ROUND WINS");word(15,14,"P1  0 - 0  P2");
    put(19,14,'0'+fighters[0].won);put(23,14,'0'+fighters[1].won);
    word(15,17,mode==0?"ARCADE SHIFT":"LOCAL VERSUS");
    center(21,characterQuotes[id]);
    if(mode==0)center(24,won?"A/START: NEXT CHALLENGER":"A/START: CONTINUE");
    else center(24,"A/START: REMATCH");
    center(26,"B: CHARACTER SELECT");sound(3);finishScreen();
}

#include "pause_guide.h"
#define ABAQUS_TRAINING_TOOLS_IMPLEMENTATION
#include "training_tools.h"
#undef ABAQUS_TRAINING_TOOLS_IMPLEMENTATION

u16 cpuKeys(void) {
    s16 distance;
    u16 k=0,forward,back,waveDistance,specialMax;
    u8 chance,enemyActive,waveApproaching;
    Fighter *f=&fighters[1];Fighter *enemy=&fighters[0];
    const CharacterProfile *c=combatProfiles[1];
    if(mode==2 && trainingDummy<4)return trainingKeys();
    if(!enemy->hp)return 0;
    if(f->downState && f->downState!=DOWN_WAKE)return 0;
    /* Wake input is a single edge at the start of the six-tick wake window.
     * captureInput() owns the buffer and applies it after DOWN_WAKE exits. */
    if(f->downState==DOWN_WAKE) {
        if(difficulty>0 && f->downTick==0)return KEY_UP;
        return 0;
    }
    forward=f->face?KEY_RIGHT:KEY_LEFT;back=f->face?KEY_LEFT:KEY_RIGHT;
    distance=abs16(f->x-enemy->x)>>4;
    chance=(rng()>>8)&31;
    enemyActive=0;
    /* Pads are sampled before updateFighter advances the attack clock.
     * Guard the contact window of the upcoming tick, including its first
     * active frame, rather than reacting one simulation tick too late. */
    if(enemy->action && enemy->tick+1>=enemy->actionStartup) {
        if(enemy->tick+1<enemy->actionActiveEnd)enemyActive=1;
    }
    /* React to an incoming wave before ordinary attack guarding.  The
     * direction test prevents a wave that has already passed from pinning
     * the CPU, while the 96px window gives the slower low wave time to guard. */
    waveApproaching=0;
    if(waves[0].active && waves[0].face && waves[0].x<f->x)waveApproaching=1;
    if(waves[0].active && !waves[0].face && waves[0].x>f->x)waveApproaching=1;
    if(waveApproaching) {
        waveDistance=abs16(waves[0].x-f->x)>>4;
        if(waveDistance<96) {
            if(waves[0].low) {
                if(difficulty>0 || chance<10)return back|KEY_DOWN;
            } else if(chance<18)return back;
        }
    }
    if(enemyActive && distance<64 && chance<8+difficulty*6)
        return back | (enemy->duck?KEY_DOWN:0);
    /* A special is only issued while the CPU is grounded and free.  The
     * family bands avoid sending rush/rising attacks from projectile range. */
    if(!f->action && !f->hurt && !f->y && f->energy>=32) {
        if(c->specialFamily==SPECIAL_PROJECTILE || c->specialFamily==SPECIAL_GROUNDWAVE) {
            /* Do not walk out of the opening band while waiting for the
             * global cadence. The meter cost makes this opening cast one-shot. */
            if(!waves[1].active) {
                if(distance>110 && f->energy>=64)return KEY_DOWN|KEY_Y;
                if(distance>95 && ((frame+f->id*13)%97==0))return KEY_DOWN|KEY_Y;
            }
        } else if((frame+f->id*13)%97==0) {
            if(c->specialFamily==SPECIAL_RUSH) {
                specialMax=c->specialReach+BODY_HALF_WIDTH;
                specialMax+=((u16)c->specialSpeed*c->specialActive)>>4;
                if(specialMax>90)specialMax=90;
                if(distance>=45 && distance<=specialMax)return KEY_DOWN|KEY_Y;
            } else if(c->specialFamily==SPECIAL_RISING) {
                if(distance<=c->specialReach+BODY_HALF_WIDTH &&
                   (enemy->y<0 || enemyActive))return KEY_DOWN|KEY_Y;
            }
        }
    }
    /* A visible near jump can invite the universal uppercut, after wave
     * defense and the signature special have had first choice. Native
     * controller probes put useful six-tick starts inside 40px at 12..56px
     * height. The sampled cadence/chance can miss that window or commit to
     * a whiff; no opponent input or future contact is consulted. */
    if(difficulty>0 && !hitstop && f->hp) {
        if(!f->action && !f->hurt && !f->y) {
            if(!enemy->hurt && !enemy->downState && distance<=40) {
                if(enemy->y<=-12*16 && enemy->y>=-56*16) {
                    if((enemy->x>f->x)==f->face &&
                       (frame+f->id*13)%(difficulty==2?6:10)==0 &&
                       chance<(difficulty==2?24:16))return KEY_DOWN|KEY_X;
                }
            }
        }
    }
    if(distance>46) {
        k=forward;
        if(distance>65 && difficulty>0 && (frame%143==0))k|=KEY_UP;
    } else if(!f->action && !f->hurt && frame%(23-difficulty*5)==0) {
        chance=chance&3;
        if(chance==0)k=KEY_Y;else if(chance==1)k=KEY_X;
        else if(chance==2)k=KEY_B;else k=KEY_A;
        if(distance<c->throwRange && difficulty>0)k=forward|KEY_X;
        else if(chance==3)k|=KEY_DOWN;
    } else if(!f->action && !f->hurt && distance>=29) {
        k=forward;
    } else if(distance<29 && chance<12)k=back;
    return k;
}

void attackStart(u8 p,u8 a) {
    Fighter *f=&fighters[p];
    const CharacterProfile *c=combatProfiles[p];
    u8 index=(p<<4)+a;
    f->action=a;f->tick=0;f->connected=0;f->guard=0;f->counter=0;
    f->actionStartup=matchStartup[index];
    f->actionActiveEnd=matchActiveEnd[index];
    f->actionEnd=matchActionEnd[index];
    f->airAction=0;
    if(f->y && a>=1 && a<=6)f->airAction=1;
    f->bufferedAction=0;f->bufferAge=0;f->bufferKeys=0;
    if(a==7) {
        f->energy-=32;f->motion=0;f->downbuffer=0;f->duck=0;
        if(c->specialFamily==SPECIAL_RISING){f->vy=c->specialVy;f->vx=0;f->y=-1;f->duck=0;}
        sound(2);
    }
    else if(a==8) {f->vy=c->uppercutVy;f->vx=0;f->y=-1;f->duck=0;sound(0);}
    else sound(0);
    if(mode==2)trainingStarted(p,a);
}
u16 cleanDirections(u16 keys) {
    if((keys&(KEY_LEFT|KEY_RIGHT))==(KEY_LEFT|KEY_RIGHT))keys&=~(KEY_LEFT|KEY_RIGHT);
    if((keys&(KEY_UP|KEY_DOWN))==(KEY_UP|KEY_DOWN))keys&=~(KEY_UP|KEY_DOWN);
    return keys;
}
void discardFighterInput(Fighter *f) {
    f->bufferedAction=0;f->bufferAge=0;f->bufferKeys=0;f->jumpBuffer=0;
}
u8 actionForInput(u8 p,u16 keys,u16 edge) {
    Fighter *f=&fighters[p];Fighter *enemy=&fighters[1-p];
    const CharacterProfile *c=combatProfiles[p];
    u16 forward,back;
    forward=f->face?KEY_RIGHT:KEY_LEFT;back=f->face?KEY_LEFT:KEY_RIGHT;
    /* Four face buttons only. Directional variants retain the existing
     * native throw, uppercut and sweep actions without shoulder attacks. */
    if(!(keys&back) && !f->y) {
        if((edge&KEY_X) && (keys&KEY_DOWN))return 8;
        if((edge&PUNCHES) && f->energy>=32) {
            if(f->motion==3)return 7;
            if((edge&KEY_Y) && (keys&KEY_DOWN))return 7;
        }
    }
    if((edge&KEY_X) && (keys&forward) && !f->y && !enemy->y) {
        if(abs16(f->x-enemy->x)<c->throwRange*16)return 9;
    }
    if(edge&KEY_X)return 3;
    if(edge&KEY_A){if((keys&KEY_DOWN) && !f->y)return 6;return 5;}
    if(edge&KEY_Y)return 1;
    if(edge&KEY_B)return 4;
    return 0;
}
void captureInput(u8 p,u16 raw,u8 live) {
    Fighter *f=&fighters[p];
    u16 keys,edge,forward,back;
    keys=cleanDirections(raw);
    f->rawKeys=raw;f->oldkeys=f->keys;f->keys=keys;
    edge=keys&~f->oldkeys;f->inputEdge=edge;
    if(!live) {
        f->bufferedAction=0;f->bufferAge=0;f->jumpBuffer=0;
        f->motion=0;f->downbuffer=0;return;
    }
    if(f->downState && f->downState!=DOWN_WAKE) {
        discardFighterInput(f);f->motion=0;f->downbuffer=0;return;
    }
    /* Hitstop samples the pad but freezes expiry, movement and animation. */
    if(!hitstop) {
        if(f->bufferAge){f->bufferAge--;if(!f->bufferAge)f->bufferedAction=0;}
        if(f->jumpBuffer)f->jumpBuffer--;
        if(f->downbuffer){f->downbuffer--;if(!f->downbuffer)f->motion=0;}
        if(f->wakeAge){f->wakeAge--;if(!f->wakeAge)f->wakeAction=0;}
        if(f->wakeJump)f->wakeJump--;
    }
    if(f->downState==DOWN_WAKE)f->face=f->x<fighters[1-p].x?1:0;
    else if(!f->action && !f->hurt && !f->y && !f->downState)f->face=f->x<fighters[1-p].x?1:0;
    forward=f->face?KEY_RIGHT:KEY_LEFT;back=f->face?KEY_LEFT:KEY_RIGHT;
    if(keys&back){f->motion=0;f->downbuffer=0;}
    else if(keys&KEY_DOWN) {
        if(keys&forward) {
            if(f->motion==1){f->motion=2;f->downbuffer=12;}
        } else {f->motion=1;f->downbuffer=12;}
    } else if((keys&forward) && f->motion==2) {f->motion=3;f->downbuffer=12;}
    if(f->downState==DOWN_WAKE) {
        /* Wake accepts attack/jump edges only.  Directional motion sampled
         * during wake must not become a post-wake special command. */
        discardFighterInput(f);
        f->motion=0;f->downbuffer=0;
        if(edge&KEY_UP)f->wakeJump=INPUT_BUFFER_TICKS;
        if(edge&ATTACKS) {
            f->wakeKeys=keys;f->wakeAction=actionForInput(p,keys,edge);
            f->wakeAge=INPUT_BUFFER_TICKS;
        }
        return;
    }
    if(!(keys&KEY_UP))f->wakeLock=0;
    if(edge&KEY_UP){f->jumpBuffer=INPUT_BUFFER_TICKS;f->wakeLock=0;}
    if(edge&ATTACKS) {
        f->bufferKeys=keys;
        f->bufferedAction=actionForInput(p,keys,edge);
        f->bufferAge=INPUT_BUFFER_TICKS;
    }
}
void captureFightInputs(void) {
    u8 live=1;
    u16 second;
    if(intro)live=0;
    if(roundEnd)live=0;
    if(paused)live=0;
    if((edge0|edge1)&KEY_START)live=0;
    captureInput(0,pad0,live);
    if(mode==2 && live)trainingCapture(fighters[0].keys);
    if(mode==1)second=pad1;
    else {
        if(!fighters[1].action && !fighters[1].hurt && !fighters[1].y && !fighters[1].downState)
            fighters[1].face=fighters[1].x<fighters[0].x?1:0;
        second=live?cpuKeys():0;
    }
    captureInput(1,second,live);
}
void controls(u8 p) {
    Fighter *f=&fighters[p];Fighter *enemy=&fighters[1-p];
    const CharacterProfile *c;
    u16 keys,forward,back;
    u8 a,cancel;
    c=combatProfiles[p];
    keys=f->keys;
    f->walking=0;
    /* Three chained OR operands are mislowered by this 816-tcc build. */
    if(f->hurt)return;
    if(f->downState)return;
    if(!f->hp)return;
    f->guard=0;
    if(!f->action && !f->y)f->face=f->x<enemy->x?1:0;
    forward=f->face?KEY_RIGHT:KEY_LEFT;back=f->face?KEY_LEFT:KEY_RIGHT;
    a=f->bufferedAction;
    if(f->action) {
        cancel=0;
        if(f->connected==2 && a) {
            if(a==7 && f->tick<f->actionActiveEnd+5) {
                if(f->action==1 || f->action==2)cancel=1;
                if(f->action==4 || f->action==5)cancel=1;
            }
            if(f->tick<f->actionActiveEnd+5) {
                if(f->action<3 && a>f->action && a<=3)cancel=1;
                if(f->action>=4 && f->action<6 && a>f->action && a<=6)cancel=1;
            }
        }
        if(cancel)f->action=0;else return;
    }
    f->duck=(keys&KEY_DOWN) && !f->y;
    f->guard=(keys&back) && !f->y;
    /* Guard dummies hold their position rather than walking away. Recoil,
     * separation, jump and downed physics still use the ordinary rules. */
    if(mode==2 && p==1) {
        if(trainingDummy==1 || trainingDummy==2)return;
    }
    if(a<7 && !f->y) {
        if(((keys&KEY_UP) && !f->wakeLock) || f->jumpBuffer) {
            f->vy=c->jumpVy;f->y=-1;f->duck=0;f->jumpBuffer=0;f->landing=0;
            f->vx=0;
            if(keys&KEY_RIGHT)f->vx=c->walkSpeed+8;
            else if(keys&KEY_LEFT)f->vx=-(c->walkSpeed+8);
        }
    }
    if(a) {
        f->duck=(f->bufferKeys&KEY_DOWN) && !f->y;
        if(a==7 && (f->y || f->energy<32))a=2;
        if(a==8 && f->y)a=3;
        if(a==9) {
            if(f->y || enemy->y)a=3;
            else if(abs16(f->x-enemy->x)>=c->throwRange*16)a=3;
        }
        attackStart(p,a);
    } else if(!f->y && !(keys&KEY_DOWN)) {
        if(keys&forward){f->x+=f->face?c->walkSpeed:-c->walkSpeed;f->walking=1;f->stride+=c->walkSpeed;}
        else if(keys&back){f->x+=f->face?-c->backSpeed:c->backSpeed;f->walking=2;f->stride+=c->backSpeed;}
    }
}

u8 hurtWithRecoil(u8 attacker,u8 defender,u8 dmg,u8 low,u8 air,u8 unblockable,u8 rearRecoil) {
    Fighter *a=&fighters[attacker];Fighter *d=&fighters[defender];
    u16 back;
    u8 blocked,direction;
    direction=rearRecoil?rearRecoil-1:a->face;
    back=d->face?KEY_LEFT:KEY_RIGHT;
    blocked=(d->keys&back) && !d->y && !d->action && !unblockable && (!d->hurt || d->guard);
    if(air && d->duck)blocked=0;
    if(low && !d->duck)blocked=0;
    if(blocked) {
        d->guard=1;d->hurt=8;dmg=dmg>14?1:0;fxType=1;hitstop=3;
        a->combo=0;a->combotime=0;a->counter=0;
        impactBannerCombo=0;impactBannerCounter=0;
    } else {
        a->counter=0;
        /* The empty-link case only writes 255 back to the same field. */
        if(d->throwVictim!=255)releaseHeldVictim(defender);
        if(d->action && d->tick<d->actionStartup) {dmg+=3;a->counter=1;}
        /* Only an uninterrupted hit reaction links a true combo.  The
         * display timer is cosmetic and must never establish a link. */
        if(d->hurt && !d->guard && a->combo)a->combo++;else a->combo=1;
        a->combotime=45;applyHitReaction(defender,dmg);
        fxType=0;hitstop=5;shake=6;
        back=a->energy+8;
        a->energy=back>ENERGY_MAX?ENERGY_MAX:back;
        impactBannerCombo=a->combo;impactBannerCounter=a->counter;
    }
    /* Snapshot feedback now; construct its tilemap after the first frozen
     * HUD tick, away from contact physics and the new actor pose uploads. */
    impactBannerPlayer=attacker;impactBannerPending=1;impactSettle=1;
    back=d->hp;
    if(dmg>=back)d->hp=0;else d->hp=back-dmg;
    if(mode==2)trainingContact(attacker,blocked,low,back-d->hp);
    rearKickRecoil&=defender?3:12;
    if(!blocked) {
        if(defender)rearRecoil<<=2;
        rearKickRecoil|=rearRecoil;
    }
    if(blocked)d->x+=direction?16:-16;
    else d->x+=direction?32:-32;
    fxX=(d->x>>4)+(direction?-12:6);fxY=FLOOR+(d->y>>4)-(low?22:53);fxLife=10;
    /* Rebuild changed bars on the first frozen impact tick, leaving the
     * contact frame's CPU budget for physics, effects and actor streams. */
    sound(1);impactHudPending=1;return blocked?1:2;
}
/* Projectiles and delayed throw damage retain their original facing rule. */
u8 hurt(u8 attacker,u8 defender,u8 dmg,u8 low,u8 air,u8 unblockable) {
    return hurtWithRecoil(attacker,defender,dmg,low,air,unblockable,0);
}

#include "knockdown.h"

void updateFighter(u8 p) {
    Fighter *f=&fighters[p];Wave *w=&waves[p];
    const CharacterProfile *c=combatProfiles[p];
    u8 rearRecoil,action,tick;
    if(f->landing)f->landing--;
    if(f->combotime) {f->combotime--;if(!f->combotime){f->combo=0;f->counter=0;clearBanner();}}
    if(f->wakeJust)f->wakeJust=0;
    else if(f->invuln)f->invuln--;
    if(f->downState){updateDowned(p);return;}
    if(f->hurt) {
        f->hurt--;
        if(!f->guard) {
            rearRecoil=p?(rearKickRecoil>>2):(rearKickRecoil&3);
            if(rearRecoil)f->x+=rearRecoil==2?9:-9;
            else f->x+=fighters[1-p].face?9:-9;
        }
        if(!f->hurt){f->guard=0;rearKickRecoil&=p?3:12;}
    }
    if(f->y || f->vy) {
        f->x+=f->vx;
        f->y+=f->vy;f->vy+=c->gravity;
        if(f->y>=0) {
            f->y=0;f->vy=0;f->vx=0;f->landing=3;
            if(f->action==8)f->action=0;
            if(f->airAction){f->action=0;f->tick=0;f->connected=0;f->airAction=0;}
        }
    }
    if(f->action) {
        action=f->action;tick=f->tick+1;f->tick=tick;
        if(action==7 && c->specialFamily==SPECIAL_RUSH && tick<=c->specialStartup+c->specialActive) {
            f->x+=f->face?c->specialSpeed:-c->specialSpeed;
        }
        if(action==7 && (c->specialFamily==SPECIAL_PROJECTILE || c->specialFamily==SPECIAL_GROUNDWAVE) && tick==c->specialStartup && !w->active) {
            w->active=1;w->owner=p;w->face=f->face;w->speed=c->specialSpeed;w->low=c->specialFamily==SPECIAL_GROUNDWAVE;
            w->x=f->x+(f->face?22*16:-22*16);w->y=w->low?FLOOR-18:FLOOR-39;w->life=c->specialLife;
        }
        if(action==6 && !f->y && tick<f->actionStartup)f->x+=f->face?16:-16;
        if(tick>=f->actionEnd) {f->action=0;f->tick=0;f->duck=0;f->airAction=0;}
    }
    if((frame&15)==0 && f->energy<ENERGY_MAX){f->energy++;hudDirty=1;}
    if(f->x<24*16)f->x=24*16;if(f->x>232*16)f->x=232*16;
}
/* Compact gameplay rectangles are independent of the illustrated canvas.
 * Edges use the same feet-relative 12.4 units as fighter positions. */
u8 verticalContact(Fighter *d,s16 top,s16 bottom) {
    s16 bodyTop,bodyBottom;
    bodyTop=d->y-(d->y?48*16:(d->duck?40*16:66*16));bodyBottom=d->y-4*16;
    if(bottom<bodyTop)return 0;
    if(top>bodyBottom)return 0;
    return 1;
}
u8 canHit(u8 p) {
    Fighter *f=&fighters[p];Fighter *d=&fighters[1-p];
    const CharacterProfile *c=combatProfiles[p];
    s16 top,bottom,dx;
    u8 rear;
    if(!f->action)return 0;
    if(f->action==7 && (c->specialFamily==SPECIAL_PROJECTILE || c->specialFamily==SPECIAL_GROUNDWAVE))return 0;
    if(f->connected)return 0;
    if(f->hurt)return 0;
    if(f->downState)return 0;
    if(d->downState)return 0;
    if(d->invuln)return 0;
    if(!d->hp)return 0;
    if(f->tick<f->actionStartup || f->tick>=f->actionActiveEnd)return 0;
    dx=d->x-f->x;
    rear=0;
    if(dx>0 && !f->face)rear=1;
    if(dx<0 && f->face)rear=1;
    if(rear) {
        /* Only the airborne medium kick reaches behind its locked facing.
         * Its short rear box is independent of the normal front reach. */
        if(f->action!=5)return 0;
        if(!f->airAction)return 0;
        if(abs16(dx)>(16+BODY_HALF_WIDTH)*16)return 0;
    }
    if(f->action==9) {
        if(f->y)return 0;
        if(d->y)return 0;
        if(d->hurt)return 0;
        return abs16(dx)<c->throwRange*16;
    }
    if(!rear && abs16(dx)>(attackReach(c,f->action)+BODY_HALF_WIDTH)*16)return 0;
    top=f->y-52*16;bottom=f->y-28*16;
    if(f->action>=4 && f->action<=6) {
        if(f->duck){top=f->y-20*16;bottom=f->y;}
        else {top=f->y-60*16;bottom=f->y-20*16;}
    } else if(f->duck){top=f->y-32*16;bottom=f->y-12*16;}
    if(f->action==7){top=f->y-58*16;bottom=f->y-12*16;}
    if(f->action==8 || (f->action==7 && c->specialFamily==SPECIAL_RISING))
        {top=f->y-72*16;bottom=f->y-12*16;}
    return verticalContact(d,top,bottom);
}
void combat(void) {
    u8 a0,a1,m0,m1,p,finished,low0,low1,air0,air1,face0,face1,k0,k1,expired,rear0,rear1,contact;
    s16 distance;
    const CharacterProfile *c0,*c1,*cw;
    controls(0);controls(1);
    updateFighter(0);updateFighter(1);
    distance=fighters[1].x-fighters[0].x;
    if(!fighters[0].downState && !fighters[1].downState && abs16(distance)<22*16 && abs16(fighters[0].y-fighters[1].y)<50*16) {
        if(distance>=0){fighters[0].x-=12;fighters[1].x+=12;}else{fighters[0].x+=12;fighters[1].x-=12;}
    }
    /* canHit() sees post-separation positions, including coincident centers. */
    distance=fighters[1].x-fighters[0].x;
    a0=canHit(0);a1=canHit(1);m0=fighters[0].action;m1=fighters[1].action;
    c0=combatProfiles[0];c1=combatProfiles[1];
    low0=(m0==7)?(c0->specialFamily==SPECIAL_GROUNDWAVE):(fighters[0].duck && m0>=4);
    low1=(m1==7)?(c1->specialFamily==SPECIAL_GROUNDWAVE):(fighters[1].duck && m1>=4);
    air0=(m0==7)?(c0->specialFamily==SPECIAL_RISING):(fighters[0].y<0);
    air1=(m1==7)?(c1->specialFamily==SPECIAL_RISING):(fighters[1].y<0);
    face0=fighters[0].face;face1=fighters[1].face;k0=0;k1=0;
    /* Snapshot rear recoil before either hurt() can cancel the other action.
     * Action 5 is never a knockdown; launch direction stays facing-based. */
    rear0=0;rear1=0;
    if(air0 && m0==5) {
        if(distance<0 && face0)rear0=1;
        if(distance>0 && !face0)rear0=2;
    }
    if(air1 && m1==5) {
        if(distance>0 && face1)rear1=1;
        if(distance<0 && !face1)rear1=2;
    }
    /* Resolve the contact snapshot atomically: mutual throws tech, throws
     * beat normals, active specials beat throws, and strikes may trade. */
    if(a0 && a1 && m0==9 && m1==9){throwTech();a0=0;a1=0;}
    else if(a0 && m0==9) {
        if(a1 && m1>=7 && m1<=8)a0=0;
        else {beginThrow(0,1);a0=0;a1=0;}
    } else if(a1 && m1==9) {
        if(a0 && m0>=7 && m0<=8)a1=0;
        else {beginThrow(1,0);a0=0;a1=0;}
    }
    if(a0) {
        fighters[0].connected=hurtWithRecoil(0,1,attackDamage(c0,fighters[0].id,m0),low0,air0,0,rear0);
        if(mode==2)trainingMoveContact(m0,air0,rear0,fighters[0].connected);
        if(fighters[0].connected==2 && knockdownAttack(0,m0,low0))k0=1;
    }
    if(a1) {
        fighters[1].connected=hurtWithRecoil(1,0,attackDamage(c1,fighters[1].id,m1),low1,air1,0,rear1);
        if(fighters[1].connected==2 && knockdownAttack(1,m1,low1))k1=1;
    }
    if(k0)beginKnockdown(0,1,face0);
    if(k1)beginKnockdown(1,0,face1);
    for(p=0;p<2;p++) {
        if(waves[p].active) {
            cw=p?c1:c0;
            waves[p].x+=waves[p].face?waves[p].speed:-waves[p].speed;
            waves[p].life--;
            expired=0;
            if(!waves[p].life)expired=1;
            if(waves[p].x<0)expired=1;
            if(waves[p].x>256*16)expired=1;
            if(expired){waves[p].active=0;waves[p].low=0;waves[p].speed=0;}
            else if(!fighters[1-p].downState && !fighters[1-p].invuln && fighters[1-p].hp &&
                    abs16(waves[p].x-fighters[1-p].x)<(cw->specialReach+BODY_HALF_WIDTH-6)*16 &&
                    verticalContact(&fighters[1-p],((s16)waves[p].y-FLOOR-6)*16,((s16)waves[p].y-FLOOR+6)*16)) {
                contact=hurt(p,1-p,attackDamage(cw,fighters[p].id,7),waves[p].low,0,0);
                if(mode==2 && !p)trainingMoveContact(7,0,0,contact);
                waves[p].active=0;waves[p].low=0;waves[p].speed=0;
            }
        }
    }
    if(waves[0].active && waves[1].active && abs16(waves[0].x-waves[1].x)<16*16) {
        fxX=waves[0].x>>4;fxY=waves[0].y;fxLife=10;fxType=0;
        waves[0].active=0;waves[1].active=0;waves[0].low=0;waves[1].low=0;waves[0].speed=0;waves[1].speed=0;sound(1);
    }
    /* Hit recoil and body separation follow movement; clamp their result too. */
    if(fighters[0].x<24*16)fighters[0].x=24*16;if(fighters[0].x>232*16)fighters[0].x=232*16;
    if(fighters[1].x<24*16)fighters[1].x=24*16;if(fighters[1].x>232*16)fighters[1].x=232*16;
    if(mode==2) {
        seconds=99;
        /* Direct accesses avoid the far-pointer/index loop on contact ticks.
         * 120 is divisible by 8: reject other ticks before software division.
         * Share the lazy timer (2 = unevaluated) and retain full-health HUD. */
        finished=2;expired=0;
        if(!fighters[0].downState && !fighters[0].invuln && !fighters[0].hurt) {
            finished=0;if(!(frame&7))finished=frame%120==0;
            if(!fighters[0].hp || finished){fighters[0].hp=HP_MAX;expired=1;}
        }
        if(!fighters[1].downState && !fighters[1].invuln && !fighters[1].hurt) {
            if(finished==2) {
                finished=0;if(!(frame&7))finished=frame%120==0;
            }
            if(!fighters[1].hp || finished){fighters[1].hp=HP_MAX;expired=1;}
        }
        if(expired)hud();
    } else {
        secondTick++;if(secondTick>=60){secondTick=0;if(seconds)seconds--;hud();}
        /* 816-tcc cannot safely lower three chained negated OR operands. */
        finished=0;
        if(fighters[0].hp==0)finished=1;
        if(fighters[1].hp==0)finished=1;
        if(seconds==0)finished=1;
        /* Let a committed lift/flight finish before a KO or timeout card. */
        if(fighters[0].downState==DOWN_LIFT || fighters[0].downState==DOWN_FLIGHT)finished=0;
        if(fighters[1].downState==DOWN_LIFT || fighters[1].downState==DOWN_FLIGHT)finished=0;
        if(finished) {
            clearThrowLinks();
            roundEnd=180;waves[0].active=0;waves[1].active=0;
            waves[0].low=0;waves[1].low=0;waves[0].speed=0;waves[1].speed=0;
            if(fighters[0].hp==fighters[1].hp)winner=2;
            else winner=fighters[0].hp>fighters[1].hp?0:1;
            if(winner<2)fighters[winner].won++;
            /* Resolve the result now, but build its panel on the next
             * frozen tick so KO contact and pose DMA keep their budget. */
            roundBannerPending=2;impactHudPending=0;impactBannerPending=0;
            shake=10;sound(3);
        }
    }
}

u8 poseFor(u8 p) {
    Fighter *f=&fighters[p];
    const CharacterProfile *c=combatProfiles[p];
    if(roundEnd) {if(!f->hp)return 14;if(winner==p)return 11;return 10;}
    if(f->downState)return f->downState==DOWN_WAKE?9:10;
    if(f->hurt)return f->guard?9:10;
    if(f->action) {
        switch(f->action) {
        case 1:return f->tick<f->actionStartup?0:5;
        case 2:return f->tick<f->actionStartup?0:6;
        case 3:return f->tick<f->actionStartup?0:6;
        case 4:case 5:case 6:return f->tick<f->actionStartup?0:(f->duck?8:7);
        case 7:
            if(c->specialFamily==SPECIAL_RUSH)return 15;
            if(c->specialFamily==SPECIAL_RISING)return 13;
            return 12;
        case 8:return 13;
        default:return 15;
        }
    }
    if(f->y)return 4;if(f->duck)return 3;
    if(f->walking)return f->walking==1?1:2;
    if(f->guard)return 9;
    return 0;
}
void animateFighter(u8 p) {
    Fighter *f=&fighters[p];
    const CharacterProfile *c=combatProfiles[p];
    u8 state,start,end,recover,hold,action=f->action,tick;
    if(roundEnd) {
        if(!f->hp)state=9;
        else if(winner==p)state=8;
        else state=7;
    } else if(f->downState)state=9+f->downState;
    else if(f->hurt)state=f->guard?6:7;
    else if(action)state=5;
    else if(f->y || f->landing)state=4;
    else if(f->duck)state=3;
    else if(f->walking)state=f->walking==1?1:2;
    else if(f->guard)state=6;
    else state=0;
    if(f->animState!=state) {
        f->animState=state;f->animTick=state==0?(f->id*3)&63:0;
        if(state==1 || state==2)f->stride=0;
    }
    if(state==0) {
        f->animFrame=16+(f->animTick>>4);
        f->animTick++;if(f->animTick>=64)f->animTick=0;
        return;
    }
    if(state==1)f->animFrame=20+((f->stride>>7)&3);
    else if(state==2)f->animFrame=24+((f->stride>>6)&3);
    else if(state==3)f->animFrame=f->animTick<4?28:3;
    else if(state==4) {
        if(f->landing)f->animFrame=31;
        else if(f->animTick<2)f->animFrame=29;
        else if(f->animTick<6)f->animFrame=30;
        else if(f->vy>32 && f->y>-24*16)f->animFrame=31;
        else f->animFrame=55;
    } else if(state==6) {
        /* A low guard keeps the crouched body and raised hands; standing
         * guard art would contradict the low hurtbox during blockstun. */
        if(f->duck)f->animFrame=3;
        else f->animFrame=f->animTick<3?40:9;
    }
    else if(state==7)f->animFrame=f->animTick<6?10:41;
    else if(state==8)f->animFrame=(f->animTick%40)<10?46:11;
    else if(state==9) {
        if(f->downState==DOWN_FLOOR)f->animFrame=59;
        else f->animFrame=f->animTick<12?47:59;
    }
    else if(state==10)f->animFrame=58;
    else if(state==11)f->animFrame=f->downTick<6?60:61;
    else if(state==12)f->animFrame=59;
    else if(state==13)f->animFrame=62;
    else if(state==14)f->animFrame=63;
    else {
        start=f->actionStartup;end=f->actionActiveEnd;
        tick=f->tick;hold=tick<start;
        recover=tick>=end;
        if(f->airAction)f->animFrame=action<=3?(hold?49:(recover?51:50)):(hold?52:(recover?54:53));
        else if(action==1)f->animFrame=hold?32:(recover?33:5);
        else if(action==2 || action==3)f->animFrame=hold?34:(recover?35:6);
        else if(action>=4 && action<=6) {
            if(f->duck)f->animFrame=hold?38:(recover?39:8);
            else f->animFrame=hold?36:(recover?37:7);
        } else if(action==7) {
            if(c->specialFamily==SPECIAL_RUSH)f->animFrame=tick<2?32:(recover?33:15);
            else if(c->specialFamily==SPECIAL_RISING)f->animFrame=tick<3?44:(recover?45:13);
            else f->animFrame=hold?42:(tick<end+7?12:43);
        } else if(action==8)f->animFrame=hold?44:(recover?45:13);
        else if(action==9)f->animFrame=hold?56:(tick<start+8?57:48);
        else f->animFrame=hold?34:(recover?35:15);
    }
    if(f->animTick<200)f->animTick++;
}
void drawFighter(u8 p) {
    Fighter *f=&fighters[p];
    f->pose=poseFor(p);
    if(animationAdvance)animateFighter(p);
    /* Signed geometry and the unchanged-position cache are native hot paths.
     * Pose selection and the independent VRAM queue retain their contracts. */
    refreshFighterOam(p);
}
void drawFight(void) {
    u8 p,phase;
    drawFighter(0);drawFighter(1);
    if(fxLife) {
        if(animationAdvance)fxLife--;
        phase=(10-fxLife)>>1;if(phase>3)phase=3;
        oamSet(OAM_EFFECT_BASE,fxX-8,fxY-8,3,fightClock&1,0,fxType?(fxLife>4?416:418):384+(phase<<1),2);oamSetEx(OAM_EFFECT_BASE,1,OBJ_SHOW);
    } else oamSetVisible(OAM_EFFECT_BASE,OBJ_HIDE);
    for(p=0;p<2;p++) {
        if(waves[p].active){oamSet(OAM_WAVE_BASE+p*4,(waves[p].x>>4)-8,waves[p].y,2,waves[p].face?0:1,0,(waves[p].low?420:392)+(fightClock%3)*2,2);oamSetEx(OAM_WAVE_BASE+p*4,1,OBJ_SHOW);}
        else oamSetVisible(OAM_WAVE_BASE+p*4,OBJ_HIDE);
    }
}
void fightTick(void) {
    u16 pauseKeys=edge0|edge1,pauseDirections;
    animationAdvance=0;
    if(pauseKeys&KEY_START) {
        paused=!paused;impactBannerPending=0;clearBanner();
        if(paused){pausePage=0;guideBuild=0;pauseHudPending=1;clearFightHint();drawPauseCard();}
        else {closePauseGuide();settlePausedHud();}
        sound(0);
    }
    if(paused) {
        pauseDirections=cleanDirections(pad0|pad1)&pauseKeys;
        if(!(pauseKeys&KEY_START))settlePausedHud();
        fighters[0].bufferedAction=0;fighters[0].bufferAge=0;fighters[0].jumpBuffer=0;
        fighters[1].bufferedAction=0;fighters[1].bufferAge=0;fighters[1].jumpBuffer=0;
        if(!(pauseKeys&KEY_START)) {
            if(pauseKeys&KEY_B){closePauseGuide();showSelect();return;}
            if(pauseKeys&KEY_A){paused=0;closePauseGuide();clearBanner();}
            else if(pauseKeys&KEY_SELECT) {
                if(pausePage==(mode==2?3:2)){closePauseGuide();drawPauseCard();}
                else openPauseGuide(pausePage+1);
                sound(0);
            } else if(pausePage) {
                if(pauseDirections&(KEY_LEFT|KEY_RIGHT)) {
                    if(mode==2) {
                        if(pauseDirections&KEY_RIGHT)openPauseGuide(pausePage==3?1:pausePage+1);
                        else openPauseGuide(pausePage==1?3:pausePage-1);
                    } else openPauseGuide(pausePage==1?2:1);
                    sound(0);
                } else if(mode==2 && pausePage==3) {
                    if(pauseDirections&KEY_UP) {
                        trainingVisible=!trainingVisible;trainingRestore=1;openPauseGuide(3);sound(0);
                    } else if(pauseDirections&KEY_DOWN) {
                        trainingChooseChallenge();openPauseGuide(3);sound(0);
                    }
                }
            } else if(mode==2 && (pauseDirections&(KEY_UP|KEY_DOWN))) {
                if(pauseDirections&KEY_DOWN)trainingDummy=(trainingDummy+1)%5;
                else trainingDummy=(trainingDummy+4)%5;
                drawPauseCard();sound(0);
            } else if(mode==2 && trainingDummy==4) {
                /* Shoulders adjust only the CPU's existing home level.
                 * Opposite held shoulders cancel, including across pads. */
                pauseDirections=pauseKeys&(KEY_L|KEY_R);
                if(((pad0|pad1)&(KEY_L|KEY_R))==(KEY_L|KEY_R))pauseDirections=0;
                if(pauseDirections) {
                    if(pauseDirections&KEY_R)difficulty=(difficulty+1)%3;
                    else difficulty=(difficulty+2)%3;
                    drawPauseCard();sound(0);
                }
            }
        }
        if(paused && guideBuild)buildPauseGuide();
        drawFight();return;
    }
    /* Either pad's Start owns this sample, including the resumed live tick. */
    if(!(pauseKeys&KEY_START)) {
        if(mode==2 && (edge0&KEY_SELECT)) {
            /* The same actors and labels remain loaded. Reset their simulation
             * now and let the two idle uploads settle before rebuilding bars. */
            resetRoundState();intro=0;hitstop=3;impactSettle=1;
            impactHudPending=1;impactBannerPending=1;resetFooterPending=1;
            animationAdvance=1;drawFight();return;
        }
    }
    if(roundEnd) {
        animationAdvance=1;
        if(roundBannerPending>1)roundBannerPending--;
        else if(roundBannerPending) {
            roundBannerPending=0;clearBanner();fillBannerPanel();
            center(10,seconds?"K.O.":"TIME OVER");
            if(winner<2)center(12,characterNames[fighters[winner].id]);
            else center(12,seconds?"DOUBLE K.O.":"DRAW");
            hud();
        }
        roundEnd--;
        if(roundEnd==100) {clearBanner();fillBannerPanel();center(10,winner<2?characterNames[fighters[winner].id]:"DRAW");center(12,winner<2?"WINS THE ROUND":"TRY AGAIN");}
        if(!roundEnd) {
            if(fighters[0].won>=2 || fighters[1].won>=2) {
                resultWin=fighters[0].won>=2;
                champion=mode==0 && resultWin && arcade>=10;
                showResult(resultWin);return;
            }
            if(winner<2)roundNumber++;
            /* Two idle uploads precede the next round's panel. The labels
             * and backdrop stay loaded; expensive UI work belongs to intro. */
            resetRoundState();roundUiPending=1;impactHudPending=1;
        }
    } else if(intro) {
        intro--;
        if(roundUiPending==1 && intro==108) {
            clearBanner();fillBannerPanel();center(10,"GET READY");center(12,arenaNames[arena]);
            put(19,2,'0'+roundNumber);hudDirty=1;roundUiPending=2;
        } else if(roundUiPending==2 && intro==107) {
            hud();impactHudPending=0;roundUiPending=0;
        }
        if(intro==50){clearBanner();fillBannerPanel();center(11,"FIGHT!");sound(3);}
        if(!intro){clearBanner();clearFightHint();}
    } else if(hitstop) {
        if(impactSettle)impactSettle=0;
        else {
            /* Both actor uploads have settled. Build the small interface
             * ranges together so the banner is visible within hitstop. */
            if(impactHudPending){hud();impactHudPending=0;}
            if(impactBannerPending) {
                clearBanner();impactBannerPending=0;
                if(impactBannerCombo>1 || impactBannerCounter) {
                    word(impactBannerPlayer?20:2,9,impactBannerCounter?"COUNTER!":"COMBO!");
                    if(impactBannerCombo>1)put(impactBannerPlayer?28:10,9,'0'+(impactBannerCombo%10));
                }
                if(resetFooterPending){clearFightHint();resetFooterPending=0;}
            }
        }
        hitstop--;
    }
    else {
        combat();animationAdvance=1;
        /* Four restrained phases, one beat per sixteen live fight ticks.
         * Intro, pause, impact freeze and round results keep the scene still. */
        ambientClock++;
        if(ambientWanted<4 && ambientAge<255)ambientAge++;
        if(((ambientClock>>4)&3)!=ambientPhase)ambientWanted=(ambientClock>>4)&3;
        else {ambientWanted=255;ambientAge=0;}
    }
    if(animationAdvance)fightClock++;
    if((frame&15)==0 && !impactHudPending && !roundBannerPending)hud();
    if(mode==2 && !intro && !roundEnd) {trainingObserve();trainingService();}
    drawFight();
}
void menuTick(void) {
    u8 *choice;
    u16 keys,held,directions;
    keys=edge0;held=pad0;
    if(screen==SELECT && selectPlayer){keys|=edge1;held|=pad1;}
    directions=cleanDirections(held)&keys;
    directions&=KEY_RIGHT|KEY_LEFT|KEY_UP|KEY_DOWN;
    /* One menu action per sample. Match pause: Start, then Back, then A.
     * Clean held directions before masking edges, so an opposite held on
     * either participating pad cannot turn a new edge into cursor movement. */
    if(keys&KEY_START)keys&=~(KEY_A|KEY_B);
    else if(keys&KEY_B)keys&=~KEY_A;
    if(screen==TITLE) {
        if(directions&KEY_DOWN){menu=(menu+1)%3;sound(0);drawTitle();}
        if(directions&KEY_UP){menu=(menu+2)%3;sound(0);drawTitle();}
        if(keys&KEY_L){difficulty=(difficulty+2)%3;sound(0);drawTitle();}
        if(keys&KEY_R){difficulty=(difficulty+1)%3;sound(0);drawTitle();}
        if(keys&(KEY_START|KEY_A)){mode=menu;arcade=0;champion=0;sound(3);showSelect();}
    } else if(screen==SELECT) {
        choice=selectPlayer?&selected2:&selected;
        if(directions&KEY_RIGHT)*choice=(*choice+1)%12;
        if(directions&KEY_LEFT)*choice=(*choice+11)%12;
        if(directions&KEY_UP)*choice=(*choice+8)%12;
        if(directions&KEY_DOWN)*choice=(*choice+4)%12;
        if(directions){sound(0);drawSelect();}
        if(keys&KEY_B){if(selectPlayer){selectPlayer=0;drawSelect();}else showTitle();return;}
        if(keys&(KEY_A|KEY_START)) {
            sound(3);
            if(mode!=0 && !selectPlayer){
                if(mode==2)selected2=(selected+1)%12;
                selectPlayer=1;drawSelect();
            }
            else {if(mode==0)selected2=(selected+1)%12;showArenas();}
        }
    } else if(screen==ARENA) {
        if(directions&KEY_DOWN){arena=(arena+1)%3;sound(0);drawArenas();}
        if(directions&KEY_UP){arena=(arena+2)%3;sound(0);drawArenas();}
        if(keys&KEY_B){showSelect();return;}
        if(keys&(KEY_A|KEY_START)){sound(3);beginMatch();}
    } else if(screen==RESULT) {
        if(keys&KEY_B){showSelect();return;}
        if(keys&(KEY_A|KEY_START)) {
            if(mode==0 && resultWin && !champion){arcade++;arena=(arena+1)%3;}
            else if(champion){arcade=0;champion=0;showTitle();return;}
            beginMatch();
        }
    }
}

void traceProfiles(void) {
    const CharacterProfile *c0=combatProfiles[0];
    const CharacterProfile *c1=combatProfiles[1];
    TRACE[34]=c0->specialFamily;TRACE[35]=c1->specialFamily;
    TRACE[36]=c0->walkSpeed;TRACE[37]=c1->walkSpeed;
    TRACE[38]=c0->jumpVy;TRACE[39]=c1->jumpVy;
    TRACE[42]=c0->backSpeed;TRACE[43]=c1->backSpeed;
    TRACE[44]=c0->specialStartup;TRACE[45]=c1->specialStartup;
    TRACE[46]=c0->specialActive;TRACE[47]=c1->specialActive;
    TRACE[48]=c0->specialRecovery;TRACE[49]=c1->specialRecovery;
    TRACE[50]=c0->specialDamage;TRACE[51]=c1->specialDamage;
    TRACE[52]=c0->specialReach;TRACE[53]=c1->specialReach;
    TRACE[54]=c0->throwRange;TRACE[55]=c1->throwRange;
}
int main(void) {
    u8 sx,actorTransferred,interfaceTransferred,ambientReady;
    randomseed=0xABA;frame=0;menu=0;mode=0;difficulty=1;selected=0;selected2=1;arena=0;
    combatProfiles[0]=&characterProfiles[0];combatProfiles[1]=&characterProfiles[0];
    traceProfiles();
    musicIndex=255;musicOn=1;
    pendingSound=0;
    spcBoot();spcSetBank(&SOUNDBANK__);spcAllocateSoundRegion(0);
    oamInit();showTitle();
    while(1) {
        pad0=padsCurrent(0);pad1=padsCurrent(1);edge0=padsDown(0);edge1=padsDown(1);
        if(screen==FIGHT){captureFightInputs();fightTick();}else menuTick();
        if(screen==FIGHT) {
            /* Resolve bank pointers and pose offsets during active display.
             * Vblank only executes the already prepared 3840-byte upload. */
            sx=frame&1;
            if(fighters[sx].animFrame!=fighters[sx].oldFrame)queueFighter(sx);
            else queueFighter(1-sx);
        }
        ambientReady=0;
        if(screen==FIGHT && !paused) {
            if(!hitstop && !roundEnd) {
                if(ambientWanted<4 && animationAdvance && !intro) {
                    ambientUploadSource=ambientData+((u16)ambientWanted<<8);
                    ambientReady=1;
                }
            }
        }
        traceActorsFast();
        if(pendingSound){spcEffect(2,pendingSound-1,effectVolpan[pendingSound-1]);pendingSound=0;}
        processResidentAudioReady();WaitForVBlank();
        /* STAT77 retains the completed picture's OBJ overflow flags until
         * the end of vblank. Read it before DMA; the host never pokes PPU. */
        TRACE[114]=REG_STAT77;
        actorTransferred=actorUploadDirty;
        interfaceTransferred=fullDirty|hudDirty|bannerDirty|footerDirty|guideDirty;
        if(actorUploadDirty){uploadActor(actorUploadSource,actorUploadDestination);actorUploadDirty=0;}
        if(screen==SELECT && portraitDirty)uploadMenuPortrait();
        if(fullDirty){dmaCopyVram((u8*)ui,0x5800,2048);fullDirty=0;hudDirty=0;bannerDirty=0;footerDirty=0;}
        else if(!actorTransferred) {
            if(guideDirty) {
                dmaCopyVram((u8*)&ui[5*32],0x5800+5*32,1472);
                guideDirty=0;bannerDirty=0;footerDirty=0;
            } else {
                /* Keep interface DMAs out of the 3840-byte actor-upload blank.
                 * Dirty ranges remain queued; hitstop flushes impact bars/text. */
                if(hudDirty){dmaCopyVram((u8*)ui,0x5800,320);hudDirty=0;}
                if(bannerDirty){dmaCopyVram((u8*)&ui[9*32],0x5800+9*32,320);bannerDirty=0;}
                if(footerDirty){dmaCopyVram((u8*)&ui[26*32],0x5800+26*32,128);footerDirty=0;}
            }
        }
        if(ambientReady && !actorTransferred && !interfaceTransferred) {
            dmaCopyVram(ambientUploadSource,AMBIENT_VRAM,AMBIENT_BYTES);
            ambientPhase=ambientWanted;ambientWanted=255;ambientAge=0;
            /* Publish completed transfer ownership with the actual VRAM. */
            TRACE[115]=ambientPhase;TRACE[117]=255;TRACE[118]=0;
        }
        if(shake && screen==FIGHT){if(!paused)shake--;sx=shake&1?2:254;bgSetScroll(0,sx==254?510:2,511);}
        else bgSetScroll(0,0,511);
        frame++;
    }
    return 0;
}
