#ifndef ABAQUS_PAUSE_GUIDE_H
#define ABAQUS_PAUSE_GUIDE_H

/* A guide is an overlay on the frozen fight, not a scene reload. Build its
 * text over three ticks, then publish one bounded BG2 range after actor DMA. */
const char trainingDummyNames[4][18] = {
    "DUMMY: STAND", "DUMMY: GUARD HIGH", "DUMMY: GUARD LOW", "DUMMY: JUMP"
};
const char specialGuideTypes[4][19] = {
    "PROJECTILE", "RUSH", "LOW WAVE", "RISING"
};

void guideWord(u8 x,u8 y,const char *text) {
    drawGuideWord(((u16)y<<6)+((u16)x<<1),text);
}

void guideCenter(u8 y,const char *text) {
    u8 n=0;
    const char *p=text;
    while(*p++)n++;
    drawGuideWord(((u16)y<<6)+(((32-n)>>1)<<1),text);
}

void guideTwoDigits(u8 x,u8 y,u8 value) {
    char text[3];
    text[0]='0'+value/10;text[1]='0'+value%10;text[2]=0;
    guideWord(x,y,text);
}

void guideNormalRow(u8 action,u8 y) {
    u8 index=action,player=stageDepthTable[3]-1;
    if(player)index+=16;
    if(action==1)guideWord(3,y,"Y LIGHT PUNCH");
    else if(action==3)guideWord(3,y,"X HEAVY PUNCH");
    else if(action==4)guideWord(3,y,"B LIGHT KICK");
    else guideWord(3,y,"A HEAVY KICK");
    guideTwoDigits(18,y,matchStartup[index]);
    guideTwoDigits(21,y,matchActiveEnd[index]-matchStartup[index]);
    guideTwoDigits(24,y,matchActionEnd[index]-matchActiveEnd[index]);
}

void guideBestCombo(void) {
    char text[18];
    u16 damage=stageDepthTable[5]+((u16)stageDepthTable[6]<<8);
    /* Paused-only formatting. The live contact path performs no divides. */
    text[0]='B';text[1]='E';text[2]='S';text[3]='T';text[4]=' ';
    text[5]='0'+stageDepthTable[4]/10;text[6]='0'+stageDepthTable[4]%10;
    text[7]='H';text[8]=' ';text[9]='0'+damage/100;
    text[10]='0'+(damage/10)%10;text[11]='0'+damage%10;
    text[12]='D';text[13]=0;guideCenter(19,text);
}

void settlePausedHud(void) {
    if(pauseHudPending) {
        /* A pause directly after contact must not leave yesterday's HP bar
         * on screen while hitstop is frozen. This changes only cached UI. */
        hud();pauseHudPending=0;impactHudPending=0;
    }
}

void drawPauseCard(void) {
    clearBanner();fillPausePanel();guideCenter(10,"PAUSED - Y SOUND");
    guideWord(3,12,"A/START RESUME B ROSTER");
    if(mode==2) {
        if(trainingDummy==4) {
            if(difficulty==0)guideCenter(11,"DUMMY: CPU EASY");
            else if(difficulty==1)guideCenter(11,"DUMMY: CPU NORMAL");
            else guideCenter(11,"DUMMY: CPU HARD");
        } else if(trainingDummy==5)guideCenter(11,"DUMMY: P2 CONTROLLER");
        else if(trainingDummy==6)guideCenter(11,"DUMMY: GUARD AFTER HIT");
        else guideCenter(11,trainingDummyNames[trainingDummy]);
        if(trainingDummy==4)guideWord(3,13,"U/D DUMMY L/R LEVEL SEL GUIDE");
        else guideWord(3,13,trainingDummy==5?"X STAND U/D DUMMY SEL GUIDE":"X P2 PAD U/D DUMMY SEL GUIDE");
    } else {
        if(mode==0) {
            if(difficulty==0)guideCenter(11,"CPU: EASY");
            else if(difficulty==1)guideCenter(11,"CPU: NORMAL");
            else guideCenter(11,"CPU: HARD");
        } else guideCenter(11,"LOCAL 1V1");
        guideWord(3,13,"SELECT HELP");
    }
}

void closePauseGuide(void) {
    if(pausePage || guideBuild)clearGuidePanel();
    pausePage=0;guideBuild=0;
    if(mode==2)trainingRestore=1;
}

void openPauseGuide(u8 page) {
    pausePage=page;guideBuild=1;
    /* Do not publish a partially constructed card. Its eventual full range
     * subsumes the old banner and footer without touching the top HUD. */
    guideDirty=0;bannerDirty=0;footerDirty=0;
}

#include "audio29_ui.h"

void buildPauseGuide(void) {
    if(pausePage==AUDIO29_PAGE){audio29Draw();return;}
    if(guideBuild==1) {
        fillGuidePanel();
        if(mode==2) {
            if(pausePage==1)guideCenter(6,"CONTROLS 1/3");
            else if(pausePage==2)guideCenter(6,stageDepthTable[3]?"NORMAL TIMING 2/3":"MOVE LIST 2/3");
            else guideCenter(6,"TRAINING 3/3");
        } else if(pausePage==1)guideCenter(6,"CONTROLS 1/2");
        else guideCenter(6,stageDepthTable[3]?"NORMAL TIMING 2/2":"MOVE LIST 2/2");
        guideWord(3,24,"A/START RESUME  B ROSTER");
        guideWord(3,8,"Y SOUND LEVELS");
        guideWord(3,25,musicOn?"L MUSIC ON":"L MUSIC OFF");
        guideWord(3,27,stageDepthTable[9]?"R SCENERY STILL":"R SCENERY MOVING");
        guideWord(3,26,pausePage==(mode==2?3:2)?"SELECT CLOSE GUIDE":"SELECT NEXT PAGE");
        guideBuild=2;
    } else if(guideBuild==2) {
        if(pausePage==1) {
            guideWord(3,9,"WALK          LEFT / RIGHT");
            guideWord(3,10,"JUMP          UP");
            guideWord(3,11,"STAND GUARD   AWAY");
            guideWord(3,12,"LOW GUARD     DOWN + AWAY");
        } else if(pausePage==2 && stageDepthTable[3]) {
            guideWord(3,9,stageDepthTable[3]==1?"P1":"P2");
            guideWord(7,9,characterNames[fighters[stageDepthTable[3]-1].id]);
            guideWord(18,11,"S  A  R");
            guideNormalRow(1,12);guideNormalRow(3,13);
        } else if(pausePage==2) {
            guideWord(3,9,"P1");guideWord(7,9,characterNames[fighters[0].id]);
            guideWord(7,10,characterSpecialNames[fighters[0].id]);
            guideWord(7,11,specialGuideTypes[combatProfiles[0]->specialFamily]);
            guideWord(3,12,"P2");guideWord(7,12,characterNames[fighters[1].id]);
            guideWord(7,13,characterSpecialNames[fighters[1].id]);
            guideWord(7,14,specialGuideTypes[combatProfiles[1]->specialFamily]);
        } else {
            guideWord(3,9,trainingVisible?"UP DISPLAY ON":"UP DISPLAY OFF");
            guideWord(3,10,"DOWN NEXT DRILL");
            guideWord(3,11,"X RETRY");
            guideCenter(12,trainingChallengeNames[trainingChallenge]);
            if(trainingChallenge==0) {
                guideWord(3,14,"COMBO Y > X OR B > A");
                guideWord(3,15,"OR LINK A SPECIAL");
                guideWord(3,16,"");
            } else if(trainingChallenge==1) {
                guideWord(3,14,"BLOCK THE CPU LOW");
                guideWord(3,15,"HOLD DOWN + AWAY");
                guideWord(3,16,"");
            } else {
                guideWord(3,14,"JUMP PAST, THEN A");
                guideWord(3,15,"HIT FROM BEHIND");
                guideWord(3,16,"");
            }
        }
        guideBuild=3;
    } else if(guideBuild==3) {
        if(pausePage==1) {
            guideWord(3,14,"PUNCH         Y LIGHT X STRONG");
            guideWord(3,15,"KICK          B LIGHT A STRONG");
            guideWord(3,16,"SWEEP         DOWN + A");
            guideWord(3,18,"THROW         TOWARD + X");
            guideWord(3,19,"UPPERCUT      DOWN + X");
            guideWord(3,20,"THROW TECH    BOTH THROW");
            guideWord(3,21,"CONFIRM LIGHT > STRONG");
            guideWord(3,22,"CROSS-UP: JUMP PAST + A");
        } else if(pausePage==2 && stageDepthTable[3]) {
            guideNormalRow(4,14);guideNormalRow(5,15);
            guideWord(3,17,"S STARTUP A ACTIVE R RECOVERY");
            guideWord(3,18,"STANDING ATTACKS - TICKS");
            guideWord(3,19,"HITSTOP IS EXTRA");
            guideWord(3,21,"");
            guideWord(3,22,stageDepthTable[3]==1?"UP P2 TIMING":"UP SPECIALS");
        } else if(pausePage==2) {
            guideWord(3,15,"QUICK: DOWN + Y");
            guideWord(3,17,"MOTION: D, D+F, F + Y/X");
            guideWord(3,18,"D=DOWN  F=TOWARD OPPONENT");
            guideWord(3,19,"12 TICKS PER STEP");
            guideWord(3,20,"32 ENERGY");
            guideWord(3,22,"PUNCH WITH FINAL TOWARD");
            drawSuperGuide();
            guideWord(3,23,"UP NORMAL TIMING");
        } else {
            trainingMakeStatus();guideWord(0,18,trainingStatusText);
            guideBestCombo();
            guideWord(3,20,"H HITS  D DAMAGE");
            guideWord(3,21,"INPUT: DIR + YXBA");
            guideWord(3,22,"");
            guideWord(3,23,"P1 SELECT RETRY");
        }
        guideBuild=0;guideDirty=1;
    }
}

u16 trainingKeys(void) {
    Fighter *f=&fighters[1];
    u16 back=f->face?KEY_LEFT:KEY_RIGHT;
    if(!f->hp)return 0;
    if(f->downState)return 0;
    if(trainingDummy==1)return back;
    if(trainingDummy==2)return back|KEY_DOWN;
    if(trainingDummy==3 && !f->y && !f->hurt)return KEY_UP;
    if(trainingDummy==6) {
        /* Stand for the opener, then guard the first legal recovery tick.
         * Real hit-stun links still connect through the held back input. */
        if(fighters[0].combotime || f->hurt)return back;
    }
    return 0;
}

void trainingCycleDummy(u8 down) {
    /* Preserve the indexed CPU value4 and the Stand->CPU Up shortcut.
     * Manual value5 remains an explicit X toggle, outside this cycle. */
    if(trainingDummy==5)trainingDummy=down?0:4;
    else if(down) {
        if(trainingDummy==3)trainingDummy=6;
        else if(trainingDummy==6)trainingDummy=4;
        else if(trainingDummy==4)trainingDummy=0;
        else trainingDummy++;
    } else {
        if(!trainingDummy)trainingDummy=4;
        else if(trainingDummy==4)trainingDummy=6;
        else if(trainingDummy==6)trainingDummy=3;
        else trainingDummy--;
    }
}

#endif
