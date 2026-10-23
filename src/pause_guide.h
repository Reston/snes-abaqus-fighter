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
        } else guideCenter(11,trainingDummyNames[trainingDummy]);
        guideCenter(13,trainingDummy==4?"U/D DUMMY L/R LEVEL SEL GUIDE":"UP/DOWN DUMMY  SELECT GUIDE");
    } else guideCenter(13,"SELECT MOVE GUIDE");
}

void closePauseGuide(void) {
    if(pausePage || guideBuild)clearGuidePanel();
    pausePage=0;guideBuild=0;
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
        guideCenter(6,pausePage==1?"HOW TO PLAY 1/2":"MOVE LIST 2/2");
        guideCenter(24,"A / START RESUME");
        guideCenter(26,pausePage==1?"B ROSTER   SELECT NEXT":"B ROSTER   SELECT BACK");
        guideBuild=2;
    } else if(guideBuild==2) {
        if(pausePage==1) {
            guideWord(3,9,"WALK          LEFT / RIGHT");
            guideWord(3,10,"JUMP          UP");
            guideWord(3,11,"STAND GUARD   AWAY");
            guideWord(3,12,"LOW GUARD     DOWN + AWAY");
        } else {
            guideWord(3,9,"P1");guideWord(7,9,characterNames[fighters[0].id]);
            guideWord(7,10,characterSpecialNames[fighters[0].id]);
            guideWord(7,11,specialGuideTypes[combatProfiles[0]->specialFamily]);
            guideWord(3,12,"P2");guideWord(7,12,characterNames[fighters[1].id]);
            guideWord(7,13,characterSpecialNames[fighters[1].id]);
            guideWord(7,14,specialGuideTypes[combatProfiles[1]->specialFamily]);
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
        } else {
            guideWord(3,15,"QUICK: DOWN + Y");
            guideWord(3,17,"MOTION: D, D+F, F + Y/X");
            guideWord(3,18,"D=DOWN  F=TOWARD OPPONENT");
            guideWord(3,19,"12-TICK WINDOW PER STEP");
            guideWord(3,20,"COST: 32 ENERGY");
            guideWord(3,22,"PRESS PUNCH WITH FINAL TOWARD");
            drawSuperGuide();
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
    return 0;
}

#endif
