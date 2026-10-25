#ifndef ABAQUS_BONUS29_H
#define ABAQUS_BONUS29_H

/* BONUS owns only this feature's reserved bytes. Fighter/Wave and the
 * normal simulation remain untouched while the opponent page is borrowed.
 * Byte 0 survives continue/handoff and clears only on a new roster run. */
#define BONUS 5
#define bonus29Seen       v29BonusState[0]
#define bonus29Variant    v29BonusState[1]
#define bonus29Result     v29BonusState[2]
#define bonus29Paused     v29BonusState[3]
#define bonus29Seconds    v29BonusState[4]
#define bonus29Subtick    v29BonusState[5]
#define bonus29Progress   v29BonusState[6]
#define bonus29TargetX    v29BonusState[7]
#define bonus29Action     v29BonusState[8]
#define bonus29Tick       v29BonusState[9]
#define bonus29Connected  v29BonusState[10]
#define bonus29Pose       v29BonusState[11]
#define bonus29OldPose    v29BonusState[12]
#define bonus29Walk       v29BonusState[13]
#define bonus29Flash      v29BonusState[14]
#define bonus29Face       v29BonusState[15]
#define bonus29X          (*(s16 *)&v29BonusState[16])
#define bonus29Y          (*(s16 *)&v29BonusState[18])
#define bonus29Vy         (*(s16 *)&v29BonusState[20])
#define bonus29ResultTick v29BonusState[22]
#define bonus29Goal       v29BonusState[23]
#define bonus29Stage      v29BonusState[24]
#define bonus29Hits       v29BonusState[25]
#define bonus29Buttons    v29BonusState[26]
#define bonus29Armed      v29BonusState[27]
#define bonus29TargetGoal v29BonusState[28]

/* A distinct attack edge is required. Heavy buttons buy two points at the
 * cost of longer ordinary anticipation/recovery; all four retain their role. */
const u8 bonus29Starts[6]={0,4,7,0,5,8};
const u8 bonus29Ends[6]={0,20,28,0,23,32};

void bonus29Hud(void) {
    u8 x,filled;
    number(6,2,bonus29Seconds);number(19,2,bonus29Progress);
    number(22,2,bonus29Goal);
    filled=bonus29Progress;
    if(!bonus29Variant)filled+=bonus29Progress>>1;
    for(x=0;x<18;x++)ui[3*32+7+x]=(x<filled?146:148)|0x2400;
    hudDirty=1;
}

void bonus29Card(void) {
    clearBanner();
    if(bonus29Paused) {
        fillBannerPanel();arcadeStoryCenter(10,"BONUS PAUSED");
        arcadeStoryCenter(12,"START RESUME   SELECT SKIP");
    } else if(bonus29Result) {
        fillBannerPanel();
        if(bonus29Result==1)arcadeStoryCenter(10,bonus29Variant?"INBOX ZERO!":"JAM CLEARED!");
        else arcadeStoryCenter(10,bonus29Result==2?"TIME! THE SHIFT GOES ON":"SKIPPED - ONWARD!");
        arcadeStoryCenter(11,"NEXT CHALLENGER");
        arcadeStoryCenter(12,characterNames[(selected+2+arcade)%12]);
    }
}

void bonus29Finish(u8 result) {
    bonus29Result=result;bonus29ResultTick=90;bonus29Action=0;
    bonus29Y=0;bonus29Vy=0;
    bonus29Pose=result==1?11:16;
    bonus29Card();sound(result==1?3:0);
}

void bonus29Queue(void) {
    if(bonus29Pose==bonus29OldPose)return;
    actorUploadSource=fighterFrameBank(selected,bonus29Pose>>3)+actorFrameOffsets[bonus29Pose&7];
    actorUploadDestination=ACTOR_VRAM0;actorUploadDirty=1;
    bonus29OldPose=bonus29Pose;
}

void bonus29Draw(void) {
    s16 x;
    x=bonus29TargetX-48;
    if(bonus29Flash&2)x+=2;
    drawActorFast(ACTOR_OAM0,(bonus29X>>4)-48,121+(bonus29Y>>4),bonus29Face?0:1,0);
    drawActorFast(ACTOR_OAM1,x,121,0,1);
    drawShadowsFast(OAM_SHADOW_BASE,bonus29X>>4);
    drawShadowsFast(OAM_SHADOW_BASE+8,bonus29TargetX);
}

void bonus29Begin(u8 variant) {
    u8 i;
    for(i=1;i<64;i++)v29BonusState[i]=0;
    bonus29Variant=variant;bonus29Seconds=variant?15:12;
    bonus29Goal=variant?18:12;bonus29TargetX=202;bonus29TargetGoal=202;
    bonus29X=50*16;bonus29Face=1;bonus29Pose=16;bonus29OldPose=255;
    setScreenOff();screen=BONUS;commonScreen();loadBackground(2);
    /* The office's approved connected floor is reused byte-for-byte. The
     * ordinary fight camera must not overwrite its fixed gutter offset. */
    bgSetScroll(0,16,511);
    oamInitGfxAttr(ACTOR_VRAM0,OBJ_SIZE8_L16);
    for(i=0;i<16;i++)oamMemory[512+i]=0;
    dmaCopyCGram(fighterPalette(selected),128,32);
    dmaCopyCGram(&effects_pal,160,32);dmaCopyVram(&effects,0x7800,EFFECTS_SIZE);
    if(variant) {
        uploadActor(&bonus29_inbox,ACTOR_VRAM1);dmaCopyCGram(&bonus29_inbox_pal,144,32);
    } else {
        uploadActor(&bonus29_printer,ACTOR_VRAM1);dmaCopyCGram(&bonus29_printer_pal,144,32);
    }
    bonus29Queue();uploadActor(actorUploadSource,actorUploadDestination);actorUploadDirty=0;
    panel(0,5);center(0,"OFFICE BONUS");center(1,variant?"INBOX OVERLOAD":"PRINTER JAM");
    word(1,2,"TIME");word(12,2,"CLEAR");put(21,2,'/');
    center(4,"CHASE IT! X/A = 2  Y/B = 1");bonus29Hud();
    panel(26,2);center(26,"MOVE + Y/X PUNCH B/A KICK");center(27,"START PAUSE  SELECT SKIP");
    bonus29Draw();music(3);finishScreen();hudDirty=0;bannerDirty=0;
}

/* Hook for RESULT and the automatic-start feature. Call exactly before a
 * successful result increments arcade. Returns 1 when BONUS owns handoff. */
u8 bonus29TryBegin(void) {
    u8 bit,variant;
    if(mode!=0)return 0;
    if(!resultWin)return 0;
    if(champion)return 0;
    if(arcade==2){bit=1;variant=0;}
    else if(arcade==6){bit=2;variant=1;}
    else return 0;
    if(bonus29Seen&bit)return 0;
    bonus29Seen|=bit;bonus29Begin(variant);return 1;
}

void bonus29TickLive(void) {
    const CharacterProfile *c=combatProfiles[0];
    u16 keys,pauseKeys;
    u8 start,end,step,pose,moving=0;
    s16 distance;
    pauseKeys=edge0|edge1;
    if(pauseKeys&KEY_START) {
        bonus29Paused=!bonus29Paused;bonus29Armed=0;bonus29Card();sound(0);return;
    }
    if(pauseKeys&KEY_SELECT) {
        if(!bonus29Result){bonus29Paused=0;bonus29Finish(3);}
        return;
    }
    if(bonus29Paused)return;
    if(bonus29Result) {
        bonus29ResultTick--;
        if(!bonus29ResultTick){arcade++;arena=(arena+1)%3;beginMatch();}
        return;
    }
    bonus29Subtick++;
    if(bonus29Subtick==60) {
        bonus29Subtick=0;bonus29Seconds--;bonus29Hud();
        if(!bonus29Seconds){bonus29Finish(2);return;}
    }
    if(bonus29Flash)bonus29Flash--;
    if(bonus29TargetX<bonus29TargetGoal) {
        step=bonus29TargetGoal-bonus29TargetX;
        bonus29TargetX+=step>3?3:step;
    } else if(bonus29TargetX>bonus29TargetGoal) {
        step=bonus29TargetX-bonus29TargetGoal;
        bonus29TargetX-=step>3?3:step;
    }
    if(!(pad0&ATTACKS))bonus29Armed=1;
    keys=bonus29Armed?edge0:0;
    if(!bonus29Action) {
        if(keys&KEY_X)bonus29Action=2;
        else if(keys&KEY_A)bonus29Action=5;
        else if(keys&KEY_Y)bonus29Action=1;
        else if(keys&KEY_B)bonus29Action=4;
        if(bonus29Action) {
            bonus29Tick=0;bonus29Connected=0;
            if(bonus29Action==1)bonus29Buttons|=1;
            else if(bonus29Action==2)bonus29Buttons|=2;
            else if(bonus29Action==4)bonus29Buttons|=4;
            else bonus29Buttons|=8;
        } else {
            if((pad0&(KEY_LEFT|KEY_RIGHT))==KEY_LEFT){bonus29X-=c->walkSpeed;moving=1;}
            else if((pad0&(KEY_LEFT|KEY_RIGHT))==KEY_RIGHT){bonus29X+=c->walkSpeed;moving=1;}
            if(bonus29X<24*16)bonus29X=24*16;
            if(bonus29X>232*16)bonus29X=232*16;
            if((keys&KEY_UP) && !bonus29Y){bonus29Y=-1;bonus29Vy=c->jumpVy;}
        }
    }
    if(bonus29Y) {
        bonus29Y+=bonus29Vy;bonus29Vy+=c->gravity;
        if(bonus29Y>=0){bonus29Y=0;bonus29Vy=0;}
    }
    bonus29Face=(bonus29X>>4)<bonus29TargetX;
    if(bonus29Action) {
        start=bonus29Starts[bonus29Action];end=bonus29Ends[bonus29Action];
        if(bonus29Tick==start && !bonus29Connected) {
            bonus29Connected=1;distance=abs16((bonus29X>>4)-bonus29TargetX);
            if(distance<=62 && bonus29Y>=-20*16) {
                step=(bonus29Action==2 || bonus29Action==5)?2:1;
                bonus29Progress+=step;if(bonus29Progress>bonus29Goal)bonus29Progress=bonus29Goal;
                bonus29Hits++;bonus29Flash=12;sound(1);bonus29Hud();
                if(bonus29Progress==bonus29Goal){bonus29Finish(1);return;}
                step=bonus29Variant?6:4;
                if(bonus29Progress>=step*(bonus29Stage+1) && bonus29Stage<2) {
                    bonus29Stage++;bonus29TargetGoal=bonus29Stage==1?54:202;
                }
            }
        }
        if(bonus29Action<=2)pose=bonus29Tick<start?32:(bonus29Tick<start+3?(bonus29Action==1?5:6):33);
        else pose=bonus29Tick<start?36:(bonus29Tick<start+3?7:37);
        if(bonus29Y)pose=bonus29Action<=2?(bonus29Tick<start?49:50):(bonus29Tick<start?52:53);
        bonus29Pose=pose;bonus29Tick++;
        if(bonus29Tick>=end)bonus29Action=0;
    } else if(bonus29Y)bonus29Pose=bonus29Vy<0?30:54;
    else if(pad0&KEY_DOWN)bonus29Pose=3;
    else if(moving){bonus29Walk++;bonus29Pose=20+((bonus29Walk>>2)&7);}
    else bonus29Pose=16+((frame>>5)&3);
}

void bonus29TickFrame(void) {
    bonus29TickLive();
    if(screen!=BONUS)return;
    bonus29Draw();bonus29Queue();
}

#endif
