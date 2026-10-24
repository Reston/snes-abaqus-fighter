#ifndef ABAQUS_PAUSE_GUIDE_H
#define ABAQUS_PAUSE_GUIDE_H

/* A guide is an overlay on the frozen fight, not a scene reload. Build its
 * text over three ticks, then publish one bounded BG2 range after actor DMA. */
const char trainingDummyNames[4][18] = {
    "DUMMY: STAND", "DUMMY: GUARD HIGH", "DUMMY: GUARD LOW", "DUMMY: JUMP"
};
const char specialGuideTypes[4][19] = {
    "FORWARD PROJECTILE", "ADVANCING STRIKE", "LOW SHOCKWAVE", "RISING STRIKE"
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

void settlePausedHud(void) {
    if(pauseHudPending) {
        /* A pause directly after contact must not leave yesterday's HP bar
         * on screen while hitstop is frozen. This changes only cached UI. */
        hud();pauseHudPending=0;impactHudPending=0;
    }
}

void drawPauseCard(void) {
    clearBanner();fillPausePanel();guideCenter(10,"PAUSED");
    guideCenter(12,"A/START RESUME B ROSTER");
    if(mode==2) {
        if(trainingDummy==4) {
            if(difficulty==0)guideCenter(11,"DUMMY: CPU EASY");
            else if(difficulty==1)guideCenter(11,"DUMMY: CPU NORMAL");
            else guideCenter(11,"DUMMY: CPU HARD");
        } else if(trainingDummy==5)guideCenter(11,"DUMMY: P2 CONTROLLER");
        else if(trainingDummy==6)guideCenter(11,"DUMMY: GUARD AFTER HIT");
        else guideCenter(11,trainingDummyNames[trainingDummy]);
        if(trainingDummy==4)guideCenter(13,"U/D DUMMY L/R LEVEL SEL GUIDE");
        else guideCenter(13,trainingDummy==5?"X STAND U/D DUMMY SEL GUIDE":"X P2 PAD U/D DUMMY SEL GUIDE");
    } else {
        if(mode==0) {
            if(difficulty==0)guideCenter(11,"CPU: EASY");
            else if(difficulty==1)guideCenter(11,"CPU: NORMAL");
            else guideCenter(11,"CPU: HARD");
        } else guideCenter(11,"LOCAL 1V1");
        guideCenter(13,"SELECT MOVE GUIDE");
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

void buildPauseGuide(void) {
    if(guideBuild==1) {
        fillGuidePanel();
        if(mode==2) {
            if(pausePage==1)guideCenter(6,"HOW TO PLAY 1/3");
            else if(pausePage==2)guideCenter(6,"MOVE LIST 2/3");
            else guideCenter(6,"TRAINING TOOLS 3/3");
        } else guideCenter(6,pausePage==1?"HOW TO PLAY 1/2":"MOVE LIST 2/2");
        guideCenter(24,"A / START RESUME");
        guideCenter(25,musicOn?"MUSIC ON  L TO MUTE":"MUSIC OFF L TO PLAY");
        guideCenter(26,pausePage==(mode==2?3:2)?"B ROSTER   SELECT BACK":"B ROSTER   SELECT NEXT");
        guideBuild=2;
    } else if(guideBuild==2) {
        if(pausePage==1) {
            guideWord(3,9,"WALK          LEFT / RIGHT");
            guideWord(3,10,"JUMP          UP");
            guideWord(3,11,"STAND GUARD   AWAY");
            guideWord(3,12,"LOW GUARD     DOWN + AWAY");
        } else if(pausePage==2) {
            guideWord(3,9,"P1");guideWord(7,9,characterNames[fighters[0].id]);
            guideWord(7,10,characterSpecialNames[fighters[0].id]);
            guideWord(7,11,specialGuideTypes[combatProfiles[0]->specialFamily]);
            guideWord(3,12,"P2");guideWord(7,12,characterNames[fighters[1].id]);
            guideWord(7,13,characterSpecialNames[fighters[1].id]);
            guideWord(7,14,specialGuideTypes[combatProfiles[1]->specialFamily]);
        } else {
            guideCenter(9,trainingVisible?"UP: LIVE DISPLAY ON":"UP: LIVE DISPLAY OFF");
            guideCenter(10,"DOWN: NEXT CHALLENGE");
            guideCenter(11,"X: RESTART DRILL");
            guideCenter(12,trainingChallengeNames[trainingChallenge]);
            if(trainingChallenge==0) {
                guideCenter(14,"LAND LIGHT, THEN PRESS STRONG");
                guideCenter(15,"Y->X  B->A  OR LINK SPECIAL");
                guideCenter(16,"SECOND MOVE MUST TRULY COMBO");
            } else if(trainingChallenge==1) {
                guideCenter(14,"CPU DUMMY: WAIT FOR A LOW");
                guideCenter(15,"HOLD DOWN + AWAY TO BLOCK");
                guideCenter(16,"HIGH BLOCK DOES NOT COUNT");
            } else {
                guideCenter(14,"STAND DUMMY: JUMP PAST");
                guideCenter(15,"PRESS A JUST AFTER CROSSING");
                guideCenter(16,"REAR AIR KICK MUST HIT");
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
            guideCenter(21,"AFTER A HIT: PRESS HEAVIER");
            guideCenter(22,"CROSS-UP: JUMP PAST + A");
        } else if(pausePage==2) {
            guideWord(3,15,"QUICK: DOWN + Y");
            guideWord(3,17,"MOTION: D, D+F, F + Y/X");
            guideWord(3,18,"D=DOWN  F=TOWARD OPPONENT");
            guideWord(3,19,"12-TICK WINDOW PER STEP");
            guideWord(3,20,"COST: 32 ENERGY");
            guideWord(3,22,"PRESS PUNCH WITH FINAL TOWARD");
            drawSuperGuide();
        } else {
            trainingMakeStatus();guideWord(0,18,trainingStatusText);
            guideCenter(20,"H HITS D DAMAGE SP! EXECUTED");
            guideCenter(21,"INPUT: DIRECTION THEN YXBA");
            guideCenter(22,"123 DOWN 456 LEVEL 789 UP");
            guideCenter(23,"LIVE SELECT RESETS PROGRESS");
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
