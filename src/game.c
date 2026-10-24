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
CHECK_OFFSET(Fighter,tick,17);
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
/* Existing recoil byte: one nibble per player, contact side + strength.
 * See pacing_recoil.h; no additional state or changed ABI. */
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

#include "stage_depth.h"

const char arenaNames[3][12] = {"LAS CONDES","EL CASTILLO","LA OFICINA"};
const u8 power[12] = {3,4,2,3,5,4,4,4,2,3,3,4};
const u8 startup[10] = {0,4,6,9,5,7,10,10,6,4};
/* Four-button roles: strong punch 4 active ticks; spacing light kick 3. */
const u8 active[10] = {0,3,4,4,3,5,6,1,8,1};
const u8 recovery[10] = {0,9,12,18,10,15,21,23,32,20};
const u8 damage[10] = {0,7,10,15,8,12,16,15,18,18};
const u8 reach[10] = {0,28,33,38,35,41,46,0,31,22};

#include "impact_presentation.h"

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
#include "audio_presentation.h"

void music(u8 index) {
    u8 effect;
    if(index>4)return;
    if(musicIndex==index)return;
    spcStop();spcLoad(MOD_MUSIC0+index);
    for(effect=0;effect<AUDIO_EFFECT_COUNT;effect++)spcLoadEffect(effect);
    audioSceneLoaded();spcPlay(0);musicIndex=index;
}
void commonScreen(void) {
    stageDepthReset();
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
    case 0:dmaCopyVram(&stage0_tiles,0,STAGE0_TILES_SIZE);dmaCopyVram(&stage0_map,0x3800,STAGE0_MAP_SIZE);dmaCopyCGram(&stage0_pal,32,192);break;
    case 1:dmaCopyVram(&stage1_tiles,0,STAGE1_TILES_SIZE);dmaCopyVram(&stage1_map,0x3800,STAGE1_MAP_SIZE);dmaCopyCGram(&stage1_pal,32,192);break;
    case 2:dmaCopyVram(&stage2_tiles,0,STAGE2_TILES_SIZE);dmaCopyVram(&stage2_map,0x3800,STAGE2_MAP_SIZE);dmaCopyCGram(&stage2_pal,32,192);break;
    case 3:dmaCopyVram(&title_tiles,0,TITLE_TILES_SIZE);dmaCopyVram(&title_map,0x3800,2048);dmaCopyCGram(&title_pal,32,192);break;
    case 4:dmaCopyVram(&select_tiles,0,SELECT_TILES_SIZE);dmaCopyVram(&select_map,0x3800,2048);dmaCopyCGram(&select_pal,32,192);break;
    default:dmaCopyVram(&arenas_tiles,0,ARENAS_TILES_SIZE);dmaCopyVram(&arenas_map,0x3800,2048);dmaCopyCGram(&arenas_pal,32,192);break;
    }
    if(which<3) {
        if(which==0)ambientData=&stage0_ambient;
        else if(which==1)ambientData=&stage1_ambient;
        else ambientData=&stage2_ambient;
        stageDepthLoad(which);
    }
}
void finishScreen(void) { dmaCopyVram((u8 *)ui,0x5800,2048);fullDirty=0;footerDirty=0;setScreenOn(); }
void drawTitle(void) {
    clearUi();
    word(9,20,"ARCADE SHIFT");word(9,22,"LOCAL 1V1 / 2P");word(9,24,"TRAINING");
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
    if(mode==1)drawGuideWord((26*32+5)*2,"LOCAL 1V1: EITHER PAD");
    fullDirty=1;
}
void showArenas(void) { setScreenOff();screen=ARENA;commonScreen();loadBackground(5);drawArenas();finishScreen(); }

#include "arcade_story.h"

void hud(void) {
    u8 p,x;
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
            refreshEnergyBar(p);
            /* Full gauge teaches the command in the existing bottom rule.
             * Only threshold transitions touch these nine cached cells. */
            if(f->energy==ENERGY_MAX) {
                word(p?22:1,4,"SUPER Y+B");
                for(x=p?22:1;x<(p?31:10);x++)ui[128+x]|=0x0400;
            } else if(hudEnergy[p]==ENERGY_MAX || hudEnergy[p]==255) {
                for(x=p?22:1;x<(p?31:10);x++)ui[128+x]=158|0x2000;
            }
            hudEnergy[p]=f->energy;
            hudDirty=1;
        }
        if(hudWins[p]!=f->won) {
            hudWins[p]=f->won;
            ui[64+(p?29:1)]=(f->won>0?147:148)|0x2000;ui[64+(p?30:2)]=(f->won>1?147:148)|0x2000;
            hudDirty=1;
        }
    }
}
#include "super_moves.h"

void resetRoundState(void) {
    u8 p;
    resetSupers();
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
    stageVictoryTick=0;stageVictoryPhase=255;
    stageDepthFar=0;stageDepthNear=0;
    fightClock=0;
    impactHudPending=0;impactBannerPending=0;roundBannerPending=0;
    impactBannerPlayer=0;impactBannerCombo=0;impactBannerCounter=0;
    impactSettle=0;resetFooterPending=0;roundUiPending=0;
    pendingSound=0;
    pauseHudPending=0;
    arcadeStoryTicks=0;
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
    resetRound();panel(26,2);center(26,"Y/X PUNCH     B/A KICK");center(27,"START PAUSE > SELECT GUIDE");
    arcadeStoryBegin();
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
    arcadeStoryEnding(id);
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
    panel(4,24);
    if(mode==1)center(5,"MATCH COMPLETE");
    else center(5,won?"SHIFT COMPLETE":"SHIFT OVER");
    for(x=3;x<29;x++)put(x,7,154);
    id=won?fighters[0].id:fighters[1].id;
    /* Result scenes are loaded with the screen off. Reuse the existing
     * portrait page and palette; combat's per-vblank actor budget is intact. */
    portraitId=id;uploadMenuPortrait();cursor(3,8,10,12);
    for(y=0;y<10;y++)for(x=0;x<8;x++)
        ui[(u16)(y+9)*32+x+4]=(160+(u16)y*8+x)|0x2400;
    word(15,9,characterNames[id]);
    if(mode==1)word(15,11,won?"PLAYER 1 WINS":"PLAYER 2 WINS");
    else word(15,11,"WINS THE MATCH");
    word(16,13,"ROUND WINS");word(15,14,"P1  0 - 0  P2");
    put(19,14,'0'+fighters[0].won);put(23,14,'0'+fighters[1].won);
    if(mode==0) {
        arcadeStoryProgress(15,17);
        word(15,19,won?"NEXT":"RETRY");
        word(21,19,characterNames[won?(selected+2+arcade)%12:fighters[1].id]);
    } else word(15,17,"LOCAL 1V1");
    center(21,mode==0?arcadeStoryWinnerQuotes[id]:characterQuotes[id]);
    if(mode==0)center(24,won?"A/START: NEXT CHALLENGER":"A/START: CONTINUE");
    else {center(23,"EITHER PLAYER");center(24,"A/START: REMATCH");}
    center(26,"B: CHARACTER SELECT");sound(3);finishScreen();
}

#include "pause_guide.h"
#define ABAQUS_TRAINING_TOOLS_IMPLEMENTATION
#include "training_tools.h"
#undef ABAQUS_TRAINING_TOOLS_IMPLEMENTATION

/* CPU decisions use ROM-only per-character habits and shared fair reactions. */
#include "cpu_personality.h"
#include "pacing_recoil.h"

void attackStart(u8 p,u8 a) {
    Fighter *f=&fighters[p];
    const CharacterProfile *c;
    u8 index=(p<<4)+a;
    f->action=a;f->tick=0;f->connected=0;f->guard=0;f->counter=0;
    f->actionStartup=matchStartup[index];
    f->actionActiveEnd=matchActiveEnd[index];
    f->actionEnd=matchActionEnd[index];
    f->airAction=0;
    if(f->y && a>=1 && a<=6)f->airAction=1;
    /* Added grounded heavy telegraph/recovery must not consume the short
     * rear-kick airborne contact window. Preserve all original air timings. */
    if(f->airAction && (a==3 || a>=5)) {
        f->actionStartup-=3;f->actionActiveEnd-=3;f->actionEnd-=7;
    }
    f->bufferedAction=0;f->bufferAge=0;f->bufferKeys=0;
    if(a==7) {
        c=combatProfiles[p];
        f->energy-=32;f->motion=0;f->downbuffer=0;f->duck=0;
        /* Rising specials prepare on the ground. Launch with the active
         * fist, so a longer readable windup does not lift it over a close
         * crouching target before contact can begin. */
        if(c->specialFamily==SPECIAL_RISING){f->vx=0;f->duck=0;}
        sound(2);
    }
    else if(a==8) {c=combatProfiles[p];f->vy=c->uppercutVy;f->vx=0;f->y=-1;f->duck=0;audioCue(0,1);}
    else audioCue(0,1);
    if(mode==2 && a==7)trainingStarted(p,a);
}
u16 cleanDirections(u16 keys) {
    if((keys&(KEY_LEFT|KEY_RIGHT))==(KEY_LEFT|KEY_RIGHT))keys&=~(KEY_LEFT|KEY_RIGHT);
    if((keys&(KEY_UP|KEY_DOWN))==(KEY_UP|KEY_DOWN))keys&=~(KEY_UP|KEY_DOWN);
    return keys;
}
#include "menu_repeat.h"
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
    if(!live || superRequest[p]) {
        if(captureSuper(p,keys,edge,live)){f->motion=0;f->downbuffer=0;return;}
    } else if((keys&SUPER_CHORD)==SUPER_CHORD) {
        if(captureSuper(p,keys,edge,live)){f->motion=0;f->downbuffer=0;return;}
    }
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
    if(mode==2 && live) {
        if((fighters[0].keys&(KEY_UP|KEY_DOWN|KEY_LEFT|KEY_RIGHT|ATTACKS))!=trainingLastKeys)
            trainingCapture(fighters[0].keys);
    }
    if(mode==1)second=pad1;
    else if(mode==2 && trainingDummy==5)second=pad1;
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
    if(superRequest[p] && startSuper(p))return;
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
            if(keys&KEY_RIGHT)f->vx=pacingAirSpeed(f->id);
            else if(keys&KEY_LEFT)f->vx=-pacingAirSpeed(f->id);
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

/* 816-tcc rebuilds generic far pointers for every actor field. Specialize
 * the two ordinary player pairs to direct WRAM operands inside this existing
 * function section. One template retains the original contact operation order.
 * The original generic path remains for other pairs; no global cache is added. */
#define RESOLVE_CONTACT_AT(A,D,AI,DI) do { \
    direction=rearRecoil?rearRecoil-1:(A).face; \
    back=(D).face?KEY_LEFT:KEY_RIGHT; \
    blocked=((D).keys&back) && !(D).y && !(D).action && !unblockable && (!(D).hurt || (D).guard); \
    if(air && (D).duck)blocked=0; \
    if(low && !(D).duck)blocked=0; \
    if(blocked) { \
        (D).guard=1;(D).hurt=11;dmg=dmg>14?1:0; \
        (A).combo=0;(A).combotime=0;(A).counter=0; \
        impactBannerCombo=0;impactBannerCounter=0; \
    } else { \
        (A).counter=0;impactBannerCounter=0; \
        /* The empty-link case only writes 255 back to the same field. */ \
        if((D).throwVictim!=255)releaseHeldVictim(DI); \
        if((D).action) { \
            if((D).tick<(D).actionStartup) {dmg+=3;(A).counter=1;impactBannerCounter=1;} \
            else if((D).tick>=(D).actionActiveEnd)impactBannerCounter=2; \
        } \
        /* Only an uninterrupted hit reaction links a true combo.  The \
         * display timer is cosmetic and must never establish a link. */ \
        if((D).hurt && !(D).guard && (A).combo)(A).combo++;else (A).combo=1; \
        (A).combotime=45;applyHitReaction(DI,dmg); \
        back=(A).energy+8; \
        (A).energy=back>ENERGY_MAX?ENERGY_MAX:back; \
        impactBannerCombo=(A).combo; \
    } \
    /* Snapshot feedback now; construct its tilemap after the first frozen \
     * HUD tick, away from contact physics and the new actor pose uploads. */ \
    impactBannerPlayer=AI;impactBannerPending=1;impactSettle=1; \
    back=(D).hp; \
    if(dmg>=back)(D).hp=0;else (D).hp=back-dmg; \
    if(mode==2) { \
        back-=(D).hp; \
        if(!AI && !blocked)TRAINING_PLAYER_HIT(back); \
        else trainingContact(AI,blocked,low,back); \
    } \
    BEGIN_RECOIL_AT(&(D),DI,direction,impactAction,blocked); \
    if(beginImpact(impactAction,blocked,direction)) { \
        fxX=((D).x>>4)+(direction?-12:6); \
        fxY=FLOOR+((D).y>>4)-(low?22:((D).duck?32:53)); \
        /* Match the strongest owned trade effect with its one queued cue. */ \
        soundImpact(blocked?SOUND_GUARD:((impactAction==1 || impactAction==4)?SOUND_LIGHT:SOUND_STRONG)); \
    } \
    /* Rebuild changed bars on the first frozen impact tick, leaving the \
     * contact frame's CPU budget for physics, effects and actor streams. */ \
    impactHudPending=1;return blocked?1:2; \
} while(0)

u8 hurtWithRecoil(u8 attacker,u8 defender,u8 dmg,u8 low,u8 air,u8 unblockable,u8 rearRecoil,u8 impactAction) {
    Fighter *a,*d;
    u16 back;
    u8 blocked,direction;
    if(!attacker && defender==1) { RESOLVE_CONTACT_AT(fighters[0],fighters[1],0,1); }
    if(attacker==1 && !defender) { RESOLVE_CONTACT_AT(fighters[1],fighters[0],1,0); }
    a=&fighters[attacker];d=&fighters[defender];
    direction=rearRecoil?rearRecoil-1:a->face;
    back=d->face?KEY_LEFT:KEY_RIGHT;
    blocked=(d->keys&back) && !d->y && !d->action && !unblockable && (!d->hurt || d->guard);
    if(air && d->duck)blocked=0;
    if(low && !d->duck)blocked=0;
    if(blocked) {
        d->guard=1;d->hurt=11;dmg=dmg>14?1:0;
        a->combo=0;a->combotime=0;a->counter=0;
        impactBannerCombo=0;impactBannerCounter=0;
    } else {
        a->counter=0;impactBannerCounter=0;
        /* The empty-link case only writes 255 back to the same field. */
        if(d->throwVictim!=255)releaseHeldVictim(defender);
        if(d->action) {
            if(d->tick<d->actionStartup) {dmg+=3;a->counter=1;impactBannerCounter=1;}
            else if(d->tick>=d->actionActiveEnd)impactBannerCounter=2;
        }
        /* Only an uninterrupted hit reaction links a true combo.  The
         * display timer is cosmetic and must never establish a link. */
        if(d->hurt && !d->guard && a->combo)a->combo++;else a->combo=1;
        a->combotime=45;applyHitReaction(defender,dmg);
        back=a->energy+8;
        a->energy=back>ENERGY_MAX?ENERGY_MAX:back;
        impactBannerCombo=a->combo;
    }
    /* Snapshot feedback now; construct its tilemap after the first frozen
     * HUD tick, away from contact physics and the new actor pose uploads. */
    impactBannerPlayer=attacker;impactBannerPending=1;impactSettle=1;
    back=d->hp;
    if(dmg>=back)d->hp=0;else d->hp=back-dmg;
    if(mode==2) {
        back-=d->hp;
        if(!attacker && !blocked)TRAINING_PLAYER_HIT(back);
        else trainingContact(attacker,blocked,low,back);
    }
    BEGIN_RECOIL_AT(d,defender,direction,impactAction,blocked);
    if(beginImpact(impactAction,blocked,direction)) {
        fxX=(d->x>>4)+(direction?-12:6);
        fxY=FLOOR+(d->y>>4)-(low?22:(d->duck?32:53));
        /* Match the strongest owned trade effect with its one queued cue. */
        soundImpact(blocked?SOUND_GUARD:((impactAction==1 || impactAction==4)?SOUND_LIGHT:SOUND_STRONG));
    }
    /* Rebuild changed bars on the first frozen impact tick, leaving the
     * contact frame's CPU budget for physics, effects and actor streams. */
    impactHudPending=1;return blocked?1:2;
}
#undef RESOLVE_CONTACT_AT
/* A released wave keeps its own direction if its owner crosses or turns. */
u8 hurt(u8 attacker,u8 defender,u8 dmg,u8 low,u8 air,u8 unblockable) {
    u8 direction;
    direction=waves[attacker].active?waves[attacker].face:fighters[attacker].face;
    /* Delayed throw damage belongs to the victim's latched launch, even if
     * an unrelated owned wave is still traveling on the opposite side. */
    if(unblockable)direction=fighters[defender].face;
    return hurtWithRecoil(attacker,defender,dmg,low,air,unblockable,direction+1,7);
}

#include "knockdown.h"

/* Keep the original update order in one template. Direct actor operands avoid
 * rebuilding generic far pointers through simultaneous contact/launch ticks;
 * profile reads and all timers, helper calls and physics remain unchanged. */
#define UPDATE_FIGHTER_AT(F,W,P) do { \
    const CharacterProfile *c=combatProfiles[P]; \
    u8 action,tick; \
    syncSuper(P); \
    if((F).landing)(F).landing--; \
    if((F).combotime) {(F).combotime--;if(!(F).combotime){(F).combo=0;(F).counter=0;clearBanner();}} \
    if((F).wakeJust)(F).wakeJust=0; \
    else if((F).invuln)(F).invuln--; \
    if(!(F).hurt)clearRecoil(P); \
    if((F).downState){updateDowned(P);return;} \
    if((F).hurt) { \
        (F).hurt--; \
        updateRecoil(P); \
        if(!(F).hurt)(F).guard=0; \
    } \
    if((F).y || (F).vy) { \
        (F).x+=(F).vx; \
        (F).y+=(F).vy;(F).vy+=c->gravity; \
        if((F).y>=0) { \
            (F).y=0;(F).vy=0;(F).vx=0;(F).landing=3; \
            if((F).action==8)(F).action=0; \
            if((F).airAction){(F).action=0;(F).tick=0;(F).connected=0;(F).airAction=0;} \
        } \
    } \
    if((F).action) { \
        action=(F).action;tick=(F).tick+1;(F).tick=tick; \
        if(superActive[P])updateSuper(P); \
        else if(action==7 && c->specialFamily==SPECIAL_RISING && tick==c->specialStartup) { \
            (F).vy=c->specialVy;(F).y=-1;(F).duck=0; \
        } \
        else if(action==7 && c->specialFamily==SPECIAL_RUSH && tick>3 && tick<=c->specialStartup+c->specialActive) { \
            (F).x+=(F).face?c->specialSpeed:-c->specialSpeed; \
        } \
        if(!superActive[P] && action==7 && (c->specialFamily==SPECIAL_PROJECTILE || c->specialFamily==SPECIAL_GROUNDWAVE) && tick==c->specialStartup && !(W).active) { \
            superWaveDamage[P]=0;superWaveReach[P]=0; \
            (W).active=1;(W).owner=P;(W).face=(F).face;(W).speed=c->specialSpeed;(W).low=c->specialFamily==SPECIAL_GROUNDWAVE; \
            (W).x=(F).x+((F).face?22*16:-22*16);(W).y=(W).low?FLOOR-18:FLOOR-39;(W).life=c->specialLife; \
        } \
        if(action==6 && !(F).y && tick<(F).actionStartup)(F).x+=(F).face?16:-16; \
        if(tick>=(F).actionEnd) {(F).action=0;(F).tick=0;(F).duck=0;(F).airAction=0;superActive[P]=0;} \
    } \
    if(!superActive[P] && (frame&15)==0 && (F).energy<ENERGY_MAX){(F).energy++;hudDirty=1;} \
    if((F).x<24*16)(F).x=24*16;if((F).x>232*16)(F).x=232*16; \
} while(0)
void updateFighter(u8 p) {
    if(!p){UPDATE_FIGHTER_AT(fighters[0],waves[0],0);return;}
    UPDATE_FIGHTER_AT(fighters[1],waves[1],1);
}
#undef UPDATE_FIGHTER_AT
#include "contact_geometry.h"
/* Compatibility entry point for the legacy super helper. Live direct and
 * projectile contacts below evaluate BOTH axes against the pose geometry. */
u8 verticalContact(Fighter *d,s16 top,s16 bottom) {
    const ContactPose *body=contactBody(d==&fighters[0]?0:1);
    if(bottom<=d->y+((s16)body->upper.top-78)*16)return 0;
    if(top>=d->y+((s16)body->lower.bottom-78)*16)return 0;
    return 1;
}
/* As with hurtWithRecoil, select the actor pair once. Keep the paired ABI
 * reads, gates and geometry calls in their original order; no query cache
 * survives a call or crosses the atomic contact snapshot. */
#define CAN_HIT_AT(F,D,P) do { \
    const CharacterProfile *c=combatProfiles[P]; \
    s16 dx; \
    u8 rear; \
    u16 actionTick,action,tick; \
    actionTick=((u16 *)&(F))[8];action=actionTick&255; \
    if(!action)return 0; \
    if(((u16 *)&(F))[9])return 0; /* connected or hurt */ \
    if((F).downState)return 0; \
    if((D).downState)return 0; \
    if((D).invuln)return 0; \
    if(!(D).hp)return 0; \
    dx=(D).x-(F).x; \
    rear=0; \
    if(dx>0 && !(F).face)rear=1; \
    if(dx<0 && (F).face)rear=1; \
    if(superActive[P]) { \
        if(superProfiles[(F).id].family==SUPER_VOLLEY)return 0; \
        if(!superPhase[P])return 0; \
        if((F).tick>=superContactEnd[P])return 0; \
        if(rear)return 0; \
        if(dx>=ACTOR_FRAME_W*16)return 0; \
        if(dx<=-ACTOR_FRAME_W*16)return 0; \
        return contactStrike(P,0); \
    } \
    if(action==7 && (c->specialFamily==SPECIAL_PROJECTILE || c->specialFamily==SPECIAL_GROUNDWAVE))return 0; \
    tick=actionTick>>8; \
    if(tick<(F).actionStartup || tick>=(F).actionActiveEnd)return 0; \
    if(rear) { \
        if(action!=5)return 0; \
        if(!(F).airAction)return 0; \
        if(abs16(dx)>(16+BODY_HALF_WIDTH)*16)return 0; \
    } \
    if(action==9) { \
        if((F).y)return 0; \
        if((D).y)return 0; \
        if((D).hurt)return 0; \
        return abs16(dx)<c->throwRange*16; \
    } \
    /* Half-open ordinary pose canvases cannot intersect at 96px separation.
     * The independent profile-based throw has already returned above. */ \
    if(dx>=ACTOR_FRAME_W*16)return 0; \
    if(dx<=-ACTOR_FRAME_W*16)return 0; \
    return contactStrike(P,rear); \
} while(0)
u8 canHit(u8 p) {
    if(!p){CAN_HIT_AT(fighters[0],fighters[1],0);}
    CAN_HIT_AT(fighters[1],fighters[0],1);
}
#undef CAN_HIT_AT
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
    /* Snapshot both contact sides before either trade cancels an action.
     * Knockdown launch retains its existing independent facing snapshot. */
    rear0=distance<0?1:2;rear1=distance>0?1:2;
    /* Equal horizontal centers have no geometric side. Preserve each
     * attack's facing snapshot instead of introducing a rightward bias. */
    if(!distance){rear0=face0+1;rear1=face1+1;}
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
        contact=attackDamage(c0,fighters[0].id,m0);
        if(superActive[0])contact=superDamage(0,contact);
        fighters[0].connected=hurtWithRecoil(0,1,contact,low0,air0,0,rear0,m0);
        if(mode==2 && !superActive[0]) {
            /* The drill observer has no transition for uppercut action 8. */
            if(m0<8)trainingMoveContact(m0,air0,(rear0-1)!=face0,fighters[0].connected);
        }
        if(fighters[0].connected==2) {
            if(superActive[0])k0=superKnockdown(0);
            else if(knockdownAttack(0,m0,low0))k0=1;
        }
    }
    if(a1) {
        contact=attackDamage(c1,fighters[1].id,m1);
        if(superActive[1])contact=superDamage(1,contact);
        fighters[1].connected=hurtWithRecoil(1,0,contact,low1,air1,0,rear1,m1);
        if(fighters[1].connected==2) {
            if(superActive[1])k1=superKnockdown(1);
            else if(knockdownAttack(1,m1,low1))k1=1;
        }
    }
    if(k0) {
        if(fighters[1].throwVictim==255)BEGIN_UNLINKED_KNOCKDOWN(1,face0);
        else beginKnockdown(0,1,face0);
    }
    if(k1) {
        if(fighters[0].throwVictim==255)BEGIN_UNLINKED_KNOCKDOWN(0,face1);
        else beginKnockdown(1,0,face1);
    }
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
                    contactWave(p)) {
                contact=hurt(p,1-p,superWaveDamage[p]?superWaveDamage[p]:attackDamage(cw,fighters[p].id,7),waves[p].low,0,0);
                if(mode==2 && !p && !superWaveDamage[p])trainingMoveContact(7,0,0,contact);
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
#include "fighter_personality.h"
/* Presentation sequencing; combat poseFor and physics remain independent. */
#include "animation_weight.h"
void drawFighter(u8 p) {
    Fighter *f=&fighters[p];
    if(!intro && !roundEnd && f->downState==DOWN_FLIGHT) {
        /* Same flight branch as poseFor/animateFighter, without their scans. */
        f->pose=10;
        if(animationAdvance) {
            if(f->animState!=11){f->animState=11;f->animTick=0;}
            if(f->vy<0)f->animFrame=f->downOwner<2?58:60;
            else f->animFrame=61;
            if(f->animTick<200)f->animTick++;
        }
    } else {
        f->pose=poseFor(p);
        if(intro)f->animFrame=personalityIntroFrame(f->id);
        else if(animationAdvance)animateFighter(p);
    }
    /* Signed geometry and the unchanged-position cache are native hot paths.
     * Pose selection and the independent VRAM queue retain their contracts. */
    refreshFighterOam(p);
}
void drawFight(void) {
    u8 p;
    drawFighter(0);drawFighter(1);
    if(fxLife)drawImpact();
    else if(!personalityAccent())oamSetVisible(OAM_EFFECT_BASE,OBJ_HIDE);
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
        else {closePauseGuide();settlePausedHud();if(arcadeStoryTicks)arcadeStoryDraw();}
        sound(0);
    }
    if(paused) {
        pauseDirections=cleanDirections(pad0|pad1)&pauseKeys;
        if(!(pauseKeys&KEY_START))settlePausedHud();
        fighters[0].bufferedAction=0;fighters[0].bufferAge=0;fighters[0].jumpBuffer=0;
        fighters[1].bufferedAction=0;fighters[1].bufferAge=0;fighters[1].jumpBuffer=0;
        if(!(pauseKeys&KEY_START)) {
            if(pauseKeys&KEY_B){closePauseGuide();showSelect();return;}
            if(pauseKeys&KEY_A){paused=0;closePauseGuide();clearBanner();if(arcadeStoryTicks)arcadeStoryDraw();}
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
                    if(pauseKeys&KEY_X) {
                        /* Retry in place in the guide, with the same actors,
                         * selected drill and difficulty. No scene reload. */
                        trainingPrepareChallenge();resetRoundState();intro=0;
                        pauseHudPending=1;openPauseGuide(3);sound(0);
                        /* Reset and guide-panel construction each have their
                         * own frame; actor uploads already serialize below. */
                        drawFight();return;
                    } else if(pauseDirections&KEY_UP) {
                        trainingVisible=!trainingVisible;trainingRestore=1;openPauseGuide(3);sound(0);
                    } else if(pauseDirections&KEY_DOWN) {
                        trainingChooseChallenge();openPauseGuide(3);sound(0);
                    }
                }
            } else if(mode==2 && (pauseKeys&KEY_X)) {
                /* Manual practice is explicit; the original five-choice
                 * dummy cycle and quick Up-to-CPU shortcut stay intact. */
                trainingDummy=trainingDummy==5?0:5;drawPauseCard();sound(0);
            } else if(mode==2 && (pauseDirections&(KEY_UP|KEY_DOWN))) {
                if(trainingDummy==5)trainingDummy=(pauseDirections&KEY_DOWN)?0:4;
                else if(pauseDirections&KEY_DOWN)trainingDummy=(trainingDummy+1)%5;
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
    /* Story uses the existing intro freeze and banner/footer DMA ranges. */
    if(arcadeStoryTicks){arcadeStoryTick();drawFight();return;}
    if(roundEnd) {
        animationAdvance=1;
        stageDepthVictory();
        if(roundBannerPending>1)roundBannerPending--;
        else if(roundBannerPending) {
            roundBannerPending=0;clearBanner();fillBannerPanel();
            center(10,seconds?"K.O.":"TIME OVER");
            if(winner<2) {
                center(11,winner?(mode==1?"PLAYER 2":"CPU"):"PLAYER 1");
                center(12,characterNames[fighters[winner].id]);
            }
            else center(12,seconds?"DOUBLE K.O.":"DRAW");
            hud();
        }
        roundEnd--;
        if(roundEnd==100) {
            clearBanner();fillBannerPanel();center(10,winner<2?characterNames[fighters[winner].id]:"DRAW");
            if(!winner)center(12,"P1 WINS THE ROUND");
            else if(winner==1)center(12,mode==1?"P2 WINS THE ROUND":"CPU WINS THE ROUND");
            else center(12,"TRY AGAIN");
        }
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
                    if(impactBannerCounter==2)word(impactBannerPlayer?20:2,9,"PUNISH!");
                    else word(impactBannerPlayer?20:2,9,impactBannerCounter?"COUNTER!":"COMBO!");
                    if(impactBannerCombo>1)put(impactBannerPlayer?28:10,9,'0'+(impactBannerCombo%10));
                }
                if(resetFooterPending){clearFightHint();resetFooterPending=0;}
            }
        }
        hitstop--;
    }
    else {
        combat();animationAdvance=1;
        stageDepthTrack();
        /* v0.24 planes are static art: only the bounded scenery look moves.
         * The old ambient destination is now the wide BG1 map's right half.
         * Keep its trace fields quiet instead of requesting an unsafe DMA. */
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
    /* Local matches belong to both players, including the rematch card.
     * Merge participating inputs before applying the shared menu priority. */
    if(screen==RESULT && mode==1){keys|=edge1;held|=pad1;}
    if(screen==ARENA && mode==1){keys|=edge1;held|=pad1;}
    directions=menuDirectionEdges(held,keys);
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
        if(keys&KEY_B){if(selectPlayer){selectPlayer=0;resetMenuRepeat();drawSelect();}else showTitle();return;}
        if(keys&(KEY_A|KEY_START)) {
            sound(3);
            if(mode!=0 && !selectPlayer){
                if(mode==2)selected2=(selected+1)%12;
                selectPlayer=1;resetMenuRepeat();drawSelect();
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
    u16 scroll;
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
        if(stageDepthAmbientReady()) {
            ambientUploadSource=ambientData+((u16)ambientWanted<<8);
            ambientReady=1;
        }
        traceActorsFast();
        audioPresentationTick();
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
        publishImpactPriority();
        scroll=0;
        if(shake && screen==FIGHT){if(!paused)shake--;scroll=impactScroll();}
        bgSetScroll(0,scroll,511);
        stageDepthPublish(scroll);
        frame++;
    }
    return 0;
}

#include "audio_presentation_state.h"
