/* Stage depth owns HDMA channel 3, mode 2 -> BG1HOFS ($210D).
 * Three non-repeating records cover 224 lines: six PPU bytes/frame.
 * No VRAM, palette, OBJ, SPC or general DMA channel is added. Table writes
 * happen ONLY after WaitForVBlank; active-display HDMA never sees a torn word.
 * These globals follow all pre-existing game globals; Fighter/Wave stay exact.
 */
u8 stageDepthTable[10];
s16 stageDepthFar,stageDepthNear;
u8 stageVictoryTick,stageVictoryPhase;

void stageDepthReset(void) {
    /* HDMAEN is write-only. This feature is the game's sole HDMA owner;
     * integration must compose a software mask if another owner is added. */
    REG_HDMAEN=0;
    stageDepthFar=0;stageDepthNear=0;
    stageVictoryTick=0;stageVictoryPhase=255;
}

/* Called once for a live simulation sample, after combat. Positions are the
 * camera's focus: the two fighters' midpoint. Truncate magnitude symmetrically
 * so left/right have identical pixel thresholds. The floor never follows it.
 * At the arena limits the far plate moves at most 3px and the near plate 6px.
 * Positive HOFS moves scenery left as the view follows fighters to the right.
 */
void stageDepthTrack(void) {
    s16 focus;
    focus=((fighters[0].x+fighters[1].x)>>5)-128;
    if(focus<0) {
        stageDepthFar=-((-focus)>>5);stageDepthNear=-((-focus)>>4);
    } else {
        stageDepthFar=focus>>5;stageDepthNear=focus>>4;
    }
}

/* A real winner receives two short four-phase cheers, then a neutral settle.
 * The ordinary ambient clock remains frozen throughout round-end. Reuse the
 * SAME 4x256 bytes and yielding transfer path; draws receive no celebration.
 * Delay past the KO actor and banner work. Pausing never advances this clock.
 */
void stageDepthVictory(void) {
    u8 phase;
    if(winner>=2)return;
    if(stageVictoryTick>=96)return;
    stageVictoryTick++;
    if(stageVictoryTick<16)return;
    if(stageVictoryTick<80)phase=((stageVictoryTick-16)>>3)&3;
    else phase=0;
    if(stageVictoryPhase==phase)return;
    stageVictoryPhase=phase;
    ambientWanted=phase;ambientAge=0;
}

/* Vblank-only hook. Architectural seams: glass/roof/ceiling, then the fixed
 * plaza/grass/desk floor. Each HDMA line count is 1..127, followed by a zero
 * terminator. BG2 is never a destination. Existing impact shake is additive
 * to every band; paused shake and depth offsets retain their exact values.
 */
void stageDepthPublish(s16 impactScroll) {
    u16 farScroll,nearScroll;
    if(screen!=FIGHT)return;
    farScroll=(stageDepthFar+impactScroll)&511;
    nearScroll=(stageDepthNear+impactScroll)&511;
    if(arena==0) {stageDepthTable[0]=48;stageDepthTable[3]=104;stageDepthTable[6]=72;}
    else if(arena==1) {stageDepthTable[0]=40;stageDepthTable[3]=104;stageDepthTable[6]=80;}
    else {stageDepthTable[0]=32;stageDepthTable[3]=120;stageDepthTable[6]=72;}
    stageDepthTable[1]=farScroll;stageDepthTable[2]=farScroll>>8;
    stageDepthTable[4]=nearScroll;stageDepthTable[5]=nearScroll>>8;
    stageDepthTable[7]=impactScroll;stageDepthTable[8]=(impactScroll>>8)&1;
    stageDepthTable[9]=0;
    REG_DMAP3=2;REG_BBAD3=0x0d;
    /* Appended uninitialized game globals live in bank $7E, checked by proof. */
    REG_A1T3LH=(u16)stageDepthTable;REG_A1B3=0x7e;
    REG_HDMAEN=HDMA_CHANNEL3;
}

u8 stageDepthAmbientReady(void) {
    if(screen!=FIGHT || paused)return 0;
    if(intro)return 0;
    if(ambientWanted>=4)return 0;
    if(roundEnd) {
        /* Round-end owns simulation before the hitstop branch. A KO may
         * retain its final contact's hitstop value; it must not suppress
         * the separate, delayed victory reaction for the entire round. */
        if(stageVictoryTick<16)return 0;
        return stageVictoryTick<=96;
    }
    if(hitstop)return 0;
    return animationAdvance;
}
