/* v0.25: BG1 is one connected 288px scenery AND detailed ground plane.
 * BG3 is disabled. No scanline bands, wrapping, HDMA, OBJ or live DMA.
 * Keep the historical sixteen-byte reservation and every following address. */
u8 stageDepthTable[10];
s16 stageDepthFar,stageDepthNear;
u8 stageVictoryTick,stageVictoryPhase;

void stageDepthReset(void) {
    REG_HDMAEN=0;
    stageDepthTable[0]=0;stageDepthTable[1]=0;stageDepthTable[2]=0;stageDepthTable[3]=0;
    stageDepthFar=0;stageDepthNear=0;
}

void stageDepthLoad(u8 which) {
    if(which>=3)return;
    /* Word addresses, audited against the actual current actor/effect map:
     * BG1 gfx 0000..37ff, BG1 64x32 map
     * 3800..3fff, BG3 32x32 map 5c00..5fff. UI/OBJ are untouched.
     * The old ambient window 3c00 is now the right BG1 map screen. */
    bgSetMapPtr(0,0x3800,SC_64x32);
    bgSetScroll(0,16,511);bgSetDisable(2);
    stageDepthTable[0]=1;
    ambientWanted=255;ambientPhase=0;ambientAge=0;
}

void stageDepthTrack(void) {
    /* Actors remain in screen space. Their midpoint suggests a bounded
     * background look, not a camera that moves feet or changes collision.
     * 16 authored pixels at either edge exceed the maximum eight-pixel look.
     * Called only after live combat: intro/pause/hitstop/results freeze it. */
    stageDepthNear=((fighters[0].x+fighters[1].x-4096)>>7);
    if(stageDepthNear < -8)stageDepthNear=-8;
    if(stageDepthNear > 8)stageDepthNear=8;
    if(stageDepthFar < stageDepthNear)stageDepthFar++;
    else if(stageDepthFar > stageDepthNear)stageDepthFar--;
}

#define stageDepthVictory() do { } while(0)

void stageDepthPublish(u16 scroll) {
    if(screen!=FIGHT)return;
    if(!stageDepthTable[0])return;
    /* Impact shake composes once on the complete scenery/ground plane. Shake
     * policy freezes when paused; floor and scenery always move together. */
    bgSetScroll(0,16+stageDepthFar+scroll,511);
}

u8 stageDepthAmbientReady(void) {
    /* No ambient upload may overwrite the widened BG1 map at $3c00. The
     * old ambient sources remain preserved historical assets, never read. */
    return 0;
}
